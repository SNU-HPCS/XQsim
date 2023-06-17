import os, sys 
#
curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
par_dir = os.path.join(curr_dir, os.pardir)
#
sys.path.insert(0, par_dir)
from util import *
import srmem as srmem
import buffer as buffer
#
from math import *
import numpy as np
import copy
import pandas as pd

class physical_schedule_unit:
    def __init__(self, unit_stat, config):
        #
        self.config = config
        # 
        self.unit_stat = unit_stat
        ###
        # Wires
        ## Input wires
        self.input_topsu_valid = None
        self.input_pchinfo = None
        self.input_opcode = None
        self.input_last_pchinfo = None
        self.input_cwdgen_stall = None # for the cwdarray gen
        self.input_pchwr_stall = None # for the pchinfo srmem filling
        self.input_timebuf_full = None
        ## Intermediate wires
        ### from opcode_buf 
        self.opcode_running = None
        ### from pchinfo_srmem
        self.pchinfo_list = None
        self.pchinfo_full = None
        self.pchinfo_valid = None
        self.pchinfo_nextready = None
        self.pchinfo_rdlast = None
        ### from cwdNtime_srmem
        self.cwd = None
        self.cwdsp = None
        self.cwdsp_2 = None
        self.timing = None
        self.id_len = None
        ### from maskgen_array
        self.mask_array = None
        self.special_array = None
        self.special_2_array = None
        ### from targetgen_array 
        ### NOTE: targetget_array is not a physical wire but a conceptual one
        self.target_array = None
        ### from control
        self.sel_cwdNtime = None
        self.flush_output = None
        self.next_qb = None
        self.next_uc = None
        self.next_pch = None
        self.next_id = None
        self.next_round = None
        self.next_opcode = None
        self.next_state = None

        # Registers
        ## Output registers
        self.output_valid = False
        self.output_cwdarray = np.full((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, self.config.num_qb_per_uc), "", dtype='U8')
        self.output_timing = 0
        self.output_opcode = '1'*self.config.opcode_bw

        ## counters 
        self.qb_counter = [i for i in range(self.config.num_qbctrl)]
        self.uc_counter = [i for i in range(self.config.num_ucc)]
        self.id_counter = 0
        self.esm_counter = 0
        ## State registers
        self.state = "ready"
        ## Pipelining registers
        self.mask_gen_reg = np.zeros((self.config.num_pcu, self.config.num_ucc, self.config.num_qbctrl), dtype=int)
        self.special_gen_reg = np.zeros((self.config.num_pcu, self.config.num_ucc, self.config.num_qbctrl), dtype=int)
        self.special2_gen_reg = np.zeros((self.config.num_pcu, self.config.num_ucc, self.config.num_qbctrl), dtype=int)
        self.target_gen_reg = np.full((self.config.num_pcu, self.config.num_ucc, self.config.num_qbctrl), np.nan)
        self.pchinfo_list_reg = []
        for i in range(self.config.num_pcu):
            self.pchinfo_list_reg.append({'data': None, 'valid': False})
        self.qb_counter_reg = [i for i in range(self.config.num_qbctrl)]
        self.uc_counter_reg = [i for i in range(self.config.num_ucc)]
        self.cwd_reg =  None
        self.cwdsp_reg = None
        self.cwdsp2_reg = None
        self.timing_reg = 0
        self.opcode_reg = '1'*self.config.opcode_bw
        self.valid_reg = False


        # opcode_buf
        self.opcode_buf = buffer.buffer("psu_opbuf", 2)

        # cwdNtime_srmem
        self.cwdNtime_srmem = dict()
        self.init_cwdNtime_srmem()
        
        # pchinfo_srmem
        self.pchinfo_srmem = srmem.srmem_double("pchinfo_srmem_psu", self.config.num_pcu, ceil(self.config.num_pch/self.config.num_pcu))

        # maskgen_array
        self.maskgen_array = np.empty((self.config.num_pcu, self.config.num_ucc, self.config.num_qbctrl), dtype=object)
        # targetgen_array 
        # NOTE: target_generator is not a physical hardware but a conceptual one
        self.targetgen_array = np.empty((self.config.num_pcu, self.config.num_ucc, self.config.num_qbctrl), dtype=object)
        for (i, j, k), _ in np.ndenumerate(self.maskgen_array):
            self.maskgen_array[i][j][k] = mask_generator(self.config)
            self.targetgen_array[i][j][k] = target_generator(self.config)
        #
        self.init_stats()
    

    def init_cwdNtime_srmem(self):
        sqgate_cyc = int(self.config.sqgate_ns)
        tqgate_cyc = int(self.config.tqgate_ns)
        meas_cyc = int(self.config.meas_ns)

        self.cwdNtime_srmem["INIT"] = []
        self.cwdNtime_srmem["INIT"].append((meas_cyc, 'meas', None, None))
        self.cwdNtime_srmem["INIT"].append((sqgate_cyc, 'cx', None, None))
        self.cwdNtime_srmem["INIT"].append((sqgate_cyc, 'h', 'm', None))

        self.cwdNtime_srmem["MEAS"] = []
        self.cwdNtime_srmem["MEAS"].append((sqgate_cyc, 'h', 'sdag_h', None))
        self.cwdNtime_srmem["MEAS"].append((meas_cyc, 'meas', None, None))
        
        self.cwdNtime_srmem["RESM"] = []
        self.cwdNtime_srmem["RESM"].append((sqgate_cyc, 'h', None, None))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', None, None))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', None, None))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', None, None))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', None, None))
        ###
        self.cwdNtime_srmem["RESM"].append((sqgate_cyc, 'h', 'sdag_h', None))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', 'cz', None))
        self.cwdNtime_srmem["RESM"].append((sqgate_cyc, 'h', 'h_s', None))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', None, None))
        self.cwdNtime_srmem["RESM"].append((sqgate_cyc, 'h', None, None))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', None, None))
        self.cwdNtime_srmem["RESM"].append((sqgate_cyc, 'h', 'sdag_h', 'h_sdag_h'))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', 'cz', 'cz'))
        self.cwdNtime_srmem["RESM"].append((sqgate_cyc, 'h', 'h_s', 'h_s'))
        ###
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', None, None))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', None, None))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', None, None))
        self.cwdNtime_srmem["RESM"].append((tqgate_cyc, 'cz', None, None))
        self.cwdNtime_srmem["RESM"].append((sqgate_cyc, 'h', None, None))
        ###
        self.cwdNtime_srmem["RESM"].append((meas_cyc, 'meas', None, None))

        self.cwdNtime_srmem["INVALID"] = []
        self.cwdNtime_srmem["INVALID"].append((0, None, None, None))
        return


    def transfer(self):
        self.transfer_opcode_buf()
        self.transfer_control() # for sel_cwdNtime, next_pch
        self.transfer_pchinfo_srmem()
        self.transfer_control()  
        self.transfer_pchinfo_srmem()
        self.transfer_control()  
        self.transfer_opcode_buf()
        self.transfer_cwdNtime_srmem()
        self.transfer_maskgen_array()
        self.transfer_maskext_array()
        return

    def transfer_opcode_buf(self):
        # connect input
        if (not self.input_pchwr_stall) and self.input_topsu_valid and self.input_last_pchinfo:
            self.opcode_buf.input_data = self.input_opcode
        else:
            self.opcode_buf.input_data = None
        self.opcode_buf.input_ready = self.next_opcode and (not self.input_cwdgen_stall)
        # transfer
        self.opcode_buf.transfer()
        # connect output
        self.opcode_running = self.opcode_buf.head
        return


    def transfer_pchinfo_srmem(self):
        # connect input
        self.pchinfo_srmem.input_valid = self.input_topsu_valid and (not self.input_pchwr_stall)
        self.pchinfo_srmem.input_data = self.input_pchinfo
        self.pchinfo_srmem.input_last_data = self.input_last_pchinfo
        self.pchinfo_srmem.input_pop = self.next_pch and (not self.input_cwdgen_stall)
        self.pchinfo_srmem.input_new_data = self.next_opcode and (not self.input_cwdgen_stall)
        # transfer
        self.pchinfo_srmem.transfer()
        # connect output
        self.pchinfo_list = copy.deepcopy(self.pchinfo_srmem.output_data)
        self.pchinfo_full = self.pchinfo_srmem.output_wrfull
        self.pchinfo_valid = self.pchinfo_srmem.output_rdvalid
        self.pchinfo_nextready = self.pchinfo_srmem.output_nextready
        self.pchinfo_rdlast = self.pchinfo_srmem.output_rdlastinfo
        return

    
    def transfer_control(self):
        # sel_cwdNtime
        if self.opcode_running == self.config.LQI_opcode \
        or self.opcode_running == self.config.INIT_INTMD_opcode:
            self.sel_cwdNtime = "INIT"
        elif self.opcode_running == self.config.LQM_Z_opcode \
        or self.opcode_running == self.config.LQM_X_opcode \
        or self.opcode_running == self.config.LQM_Y_opcode \
        or self.opcode_running == self.config.MEAS_INTMD_opcode:
            self.sel_cwdNtime = "MEAS"
        elif self.opcode_running == self.config.RUN_ESM_opcode:
            self.sel_cwdNtime = "RESM"
        else:
            self.sel_cwdNtime = "INVALID"

        # flush_output
        self.flush_output = self.output_valid

        # next_counters
        if self.state == "running":
            self.next_qb = True
            if self.next_qb and (self.qb_counter[0] + self.config.num_qbctrl) >= self.config.num_qb_per_uc:
                self.next_uc = True
            else:
                self.next_uc = False
            if self.next_uc and (self.uc_counter[0] + self.config.num_ucc) >= self.config.num_uc:
                self.next_pch = True
            else:
                self.next_pch = False
            if self.next_pch and self.pchinfo_rdlast:
                self.next_id = True
            else:
                self.next_id = False
            if self.next_id and self.id_counter == self.id_len-1:
                self.next_round = True
            else:
                self.next_round = False
            if self.next_round:
                if self.opcode_running == self.config.RUN_ESM_opcode:
                    if self.esm_counter == (self.config.code_dist-1):
                        self.next_opcode = True
                    else:
                        self.next_opcode = False
                else:
                    self.next_opcode = True
            else:
                self.next_opcode = False
        else:
            self.next_qb = False
            self.next_uc = False
            self.next_pch = False
            self.next_id = False
            self.next_round = False
            self.next_opcode = False

        # next_state 
        if self.state == "ready":
            if self.pchinfo_valid:
                self.next_state = "running"
            else:
                self.next_state = "ready"
        elif self.state == "running":
            if self.next_id: 
                if self.pchinfo_nextready:
                    self.next_state = "running"
                else:
                    self.next_state = "ready"
            else:
                self.next_state = "running"
        else:
            sys.exit()

        return 


    def transfer_cwdNtime_srmem(self):
        self.timing, self.cwd, self.cwdsp, self.cwdsp_2 = self.cwdNtime_srmem[self.sel_cwdNtime][0]
        self.id_len = len(self.cwdNtime_srmem[self.sel_cwdNtime])
        return


    def transfer_maskgen_array(self):
        # connect input & transfer
        for (i, j, k), maskgen in np.ndenumerate(self.maskgen_array):
            # pchinfo_valid, pchypte, facebd
            pchinfo_valid = self.pchinfo_list[i]['valid']
            if pchinfo_valid:
                pchtype = self.pchinfo_list[i]['data']['pchtype']
                facebd = self.pchinfo_list[i]['data']['facebd']
                cornerbd = self.pchinfo_list[i]['data']['cornerbd']
            else:
                pchtype = None
                facebd = None
                cornerbd = None
            maskgen.input_pchinfo_valid = pchinfo_valid
            maskgen.input_pchtype = pchtype
            maskgen.input_facebd = facebd
            maskgen.input_cornerbd = cornerbd

            ## opcode
            if pchinfo_valid:
                if self.opcode_running == self.config.LQM_X_opcode \
                or self.opcode_running == self.config.LQM_Y_opcode \
                or self.opcode_running == self.config.LQM_Z_opcode:
                    pchops = self.pchinfo_list[i]['data']['pchop']
                    meas_opcode = format(int(pchops[0], 2) & int(pchops[1], 2), "b").zfill(self.config.opcode_bw)
                    maskgen.input_opcode = meas_opcode
                else:
                    maskgen.input_opcode = self.opcode_running
            else:
                maskgen.input_opcode = self.opcode_running
            ## id
            maskgen.input_id =self.id_counter
            ## qbidx
            maskgen.input_qbidx = self.qb_counter[k]
            ## ucloc: (w, n, e, s, low, up, diag)
            ucidx = self.uc_counter[j]
            if ucidx >= self.config.num_uc: 
                maskgen.input_ucloc = (False, False, False, False, False, False, False, False)
            else:
                ucrow, uccol = divmod(ucidx, self.config.num_uccol)
                is_west = (uccol == 0)
                is_north = (ucrow == 0)
                is_east = (uccol == (self.config.num_uccol-1))
                is_south = (ucrow == (self.config.num_ucrow-1))
                is_lowtri = ((ucrow+uccol) > self.config.num_ucrow)
                is_uppertri = ((ucrow+uccol) < self.config.num_ucrow-1)
                is_leftdiag = ((ucrow+uccol) == self.config.num_ucrow-1)
                is_rightdiag = ((ucrow+uccol) == self.config.num_ucrow)
                # is_secondrow = (ucrow == 1)
                maskgen.input_ucloc = (is_west, is_north, is_east, is_south, is_lowtri, is_uppertri, is_leftdiag, is_rightdiag)
            #
            maskgen.transfer()
        
        # connect input & transfer
        for (i, j, k), targetgen in np.ndenumerate(self.targetgen_array):
            ## opcode
            targetgen.input_opcode = self.opcode_running
            ## id
            targetgen.input_id = self.id_counter
            ## qbidx
            targetgen.input_qbidx = self.qb_counter[k]
            ## 
            targetgen.transfer()
        return


    def transfer_maskext_array(self):
        # mask_array, special_array
        self.mask_array = np.zeros((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, self.config.num_qb_per_uc), dtype=int)
        self.special_array = np.zeros((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, self.config.num_qb_per_uc), dtype=int)
        self.special_2_array = np.zeros((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, self.config.num_qb_per_uc), dtype=int)
        # target_array
        self.target_array = np.full((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, self.config.num_qb_per_uc), np.nan)

        # maskgen ext
        for (i, j, k), _ in np.ndenumerate(self.mask_gen_reg):
            pchinfo_valid = self.pchinfo_list_reg[i]['valid']
            if pchinfo_valid:
                pchrow, pchcol = divmod(self.pchinfo_list_reg[i]['data']['pchidx'], self.config.num_pchcol)
                ucrow, uccol = divmod(self.uc_counter_reg[j], self.config.num_uccol)
                qbidx = self.qb_counter_reg[k]

                if ucrow >= self.config.num_ucrow or uccol >= self.config.num_uccol or qbidx >= self.config.num_qb_per_uc:
                    continue
                self.mask_array[pchrow][pchcol][ucrow][uccol][qbidx] = self.mask_gen_reg[i][j][k]
                self.special_array[pchrow][pchcol][ucrow][uccol][qbidx] = self.special_gen_reg[i][j][k]
                self.special_2_array[pchrow][pchcol][ucrow][uccol][qbidx] = self.special2_gen_reg[i][j][k]
                self.target_array[pchrow][pchcol][ucrow][uccol][qbidx] = self.target_gen_reg[i][j][k]
            else:
                pass
        return

    def update(self, sim_cycle=0):
        self.update_stats(sim_cycle)

        self.opcode_buf.update()
        self.pchinfo_srmem.update()

        if self.input_cwdgen_stall: 
            return 

        self.update_cwdNtime_srmem()
        self.update_output()
        self.update_pipe()
        self.update_counters()
        self.state = self.next_state 

        return


    def update_cwdNtime_srmem(self):
        srmem = self.cwdNtime_srmem[self.sel_cwdNtime]
        if self.next_id:
            head = srmem[0]
            for i in range(0, self.id_len-1):
                srmem[i] = srmem[i+1]
            srmem[self.id_len-1] = head
        self.cwdNtime_srmem[self.sel_cwdNtime] = srmem
        return

    def update_counters(self):
        # qb_counter
        self.qb_counter_reg = self.qb_counter[:]
        if self.next_uc: 
            self.qb_counter = [i for i in range(self.config.num_qbctrl)]
        elif self.next_qb:
            for i in range(self.config.num_qbctrl):
                self.qb_counter[i] += self.config.num_qbctrl
        else:
            pass
        # uc_counter
        self.uc_counter_reg = self.uc_counter[:]
        if self.next_pch:
            self.uc_counter = [i for i in range(self.config.num_ucc)]
        elif self.next_uc:
            for i in range(self.config.num_ucc):
                self.uc_counter[i] += self.config.num_ucc
        else:
            pass
        # id_counter 
        if self.next_round:
            self.id_counter = 0
        elif self.next_id:
            self.id_counter += 1
        else:
            pass
        # esm_counter
        if self.next_opcode:
            self.esm_counter = 0
        elif self.next_round:
            self.esm_counter += 1
        else:
            pass

    def update_output(self):
        # output_valid, output_timing, output_opcode
        self.output_valid = self.valid_reg
        self.output_timing = self.timing_reg
        self.output_opcode = self.opcode_reg

        # output_cwdarray
        for (i, j, k, l, m), entry in np.ndenumerate(self.output_cwdarray):
            if self.special_2_array[i][j][k][l][m] == 1:
                final_cwd = self.cwdsp2_reg
            elif self.special_array[i][j][k][l][m] == 1:
                final_cwd = self.cwdsp_reg
            else:
                final_cwd = self.cwd_reg

            if not np.isnan(self.target_array[i][j][k][l][m]):
                final_cwd += str(int(self.target_array[i][j][k][l][m]))
            else:
                pass

            if self.mask_array[i][j][k][l][m] == 1:
                entry = final_cwd
            else:
                if self.flush_output:
                    entry = ''
                else:
                    pass
            self.output_cwdarray[i][j][k][l][m] = entry

        return 


    def update_pipe(self):
        #
        self.pchinfo_list_reg = copy.deepcopy(self.pchinfo_list)
        #
        for (i, j, k), maskgen in np.ndenumerate(self.maskgen_array): 
            self.mask_gen_reg[i][j][k] = maskgen.output_mask
            self.special_gen_reg[i][j][k] = maskgen.output_special
            self.special2_gen_reg[i][j][k] = maskgen.output_special_2
        #
        for (i, j, k), targetgen in np.ndenumerate(self.targetgen_array): 
            self.target_gen_reg[i][j][k] = targetgen.output_target

        #
        if self.next_id:
            self.valid_reg = True
            self.timing_reg = self.timing
            self.opcode_reg = self.opcode_running 
        else:
            self.valid_reg = False

        #
        self.cwd_reg = self.cwd
        self.cwdsp_reg = self.cwdsp
        self.cwdsp2_reg = self.cwdsp_2
        return


    def debug(self):
        # Add variables to check in the debugging mode
        if self.output_valid and not self.input_cwdgen_stall:
            print("psu.output_valid: {}".format(self.output_valid))
            print("psu.output_timing: {}".format(self.output_timing))
            print("psu.output_opcode: {}".format(self.output_opcode))
            print("psu.output_cwdarray: ")
            debug_array(self.config, self.output_cwdarray)
        return

    def init_stats(self):
        # Data transfer
        ### to TCU
        self.unit_stat.data_transfer["TCU"] = {
                "num_eff": [],
                "num_max": [], 
                "cycle": [],
                "bw": self.config.cwd_bw,
                "last_cyc": 0
                }
        self.unit_stat.num_acc_cyc = 0
        self.unit_stat.num_update_cyc = 0

        return

    def update_stats(self, sim_cycle):
        self.unit_stat.num_update_cyc += 1
        # num_acc_cyc
        if self.input_cwdgen_stall: 
            pass
        else: 
            self.unit_stat.num_acc_cyc += 1
        # data_transfer
        if self.output_valid and not self.input_timebuf_full:
            cycle = sim_cycle - self.unit_stat.data_transfer["TCU"]["last_cyc"]
            self.unit_stat.data_transfer["TCU"]["num_max"].append(self.config.num_pq_eff)
            #
            num_scheduled_cwd = 0
            for _, op in np.ndenumerate(self.output_cwdarray):
                if len(op) != 0:
                    num_scheduled_cwd += 1
                else:
                    pass
            self.unit_stat.data_transfer["TCU"]["num_eff"].append(num_scheduled_cwd)
            #
            self.unit_stat.data_transfer["TCU"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["TCU"]["last_cyc"] = sim_cycle
        else:
            pass

        return


class mask_generator:
    def __init__(self, param):
        self.config = param
        # Wires
        ## Input wire
        self.input_opcode = None
        self.input_id = None
        self.input_qbidx = None
        self.input_ucloc = None
        self.input_pchinfo_valid = None
        self.input_pchtype = None #static
        self.input_facebd = None
        self.input_cornerbd = None

        ## Output wire
        self.output_mask = None
        self.output_special = None
        self.output_special_2 = None

    def transfer(self):
        if self.input_pchinfo_valid:
            if self.input_opcode == self.config.LQI_opcode:
                self.transfer_init()
            elif self.input_opcode == self.config.LQM_Z_opcode \
              or self.input_opcode == self.config.LQM_X_opcode \
              or self.input_opcode == self.config.LQM_Y_opcode:
                self.transfer_meas()
            elif self.input_opcode == self.config.INIT_INTMD_opcode:
                self.transfer_initmerge()
            elif self.input_opcode == self.config.MEAS_INTMD_opcode:
                self.transfer_meassplit()
            elif self.input_opcode == self.config.RUN_ESM_opcode:
                self.transfer_esm()
            else:
                self.output_mask = 0
                self.output_special = 0
                self.output_special_2 = 0
        else:
            self.output_mask = 0
            self.output_special = 0
            self.output_special_2 = 0


    def transfer_init(self):
        (uc_west, uc_north, uc_east, uc_south, uc_lowtri, uc_uppertri, uc_leftdiag, uc_rightdiag) = self.input_ucloc
        (facebd_w, facebd_n, facebd_e, facebd_s) = self.input_facebd
        (cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se) = self.input_cornerbd
        uc_valid = False
        for loc in self.input_ucloc:
            uc_valid = uc_valid or loc

        if self.config.block_type == "Distillation":
            ## INIT-mask
            if self.input_qbidx >= 4:
                mask = 0
            else: # for dq
                if self.input_pchtype == 'zt': # INIT: PCHTYPE-ZT
                    if (self.input_id == 2): 
                        mask = 0
                            
                    else: # self.input_id == 0, 1
                        if (uc_west and uc_north): # NW
                            mask = 0
                        elif (uc_north):      # N, NE
                        
                            if (self.input_qbidx == 2 or self.input_qbidx == 3):
                                mask = 1
                            else:
                                mask = 0
                        elif (uc_west): # W, SW
                            if (self.input_qbidx == 1 or self.input_qbidx == 3):
                                mask = 1
                            else:
                                mask = 0
                        elif (uc_valid): # C, E, S, SE
                            mask = 1
                        else: # INVALID UC
                            mask = 0
                
                elif self.input_pchtype == 'zb': # INIT: PCHTYPE-ZB
                    if (self.input_id == 2):
                        mask = 0
                    else: # self.input_id == 0, 1
                        if (uc_west and not uc_south): # NW, W
                            if (self.input_qbidx == 1 or self.input_qbidx == 3):
                                mask = 1
                            else:
                                mask = 0
                        elif (uc_west): # SW
                            if (self.input_qbidx == 1):
                                mask = 1
                            else:
                                mask = 0
                        elif (uc_valid): # N, NE, C, E, S, SE
                            mask = 1
                        else: # INVALID UC
                            mask = 0
                    
                
                elif self.input_pchtype == 'mb': # INIT: PCHTYPE-MB
                    if (self.input_id == 2):
                        if (uc_rightdiag or uc_lowtri):
                            mask = 1
                        elif (uc_leftdiag):
                        
                            if (self.input_qbidx == 3):
                                mask = 1
                            else:
                                mask = 0
                        else:
                            mask = 0
                    
                    else: # self.input_id == 0, 1
                        if (uc_north and uc_west): # NW
                        
                            if (self.input_qbidx == 3):
                                mask = 1
                            else:
                                mask = 0
                        elif (uc_north): # N, NE
                            if (self.input_qbidx == 2 or self.input_qbidx == 3):
                                mask = 1
                            else:
                                mask = 0
                        elif (uc_west): # W, SW
                            if (self.input_qbidx == 1 or self.input_qbidx == 3):
                                mask = 1
                            else:
                                mask = 0
                        elif (uc_valid): # C, E, S, SE
                            mask = 1
                        else: # INVALID UC
                            mask = 0
                    
                elif self.input_pchtype == 'm': # INIT: PCHTYPE-M
                    if (uc_uppertri or uc_leftdiag):
                     # for self.input_id == 0, 1, 2
                        if (uc_north and uc_west): # NW
                            if (self.input_qbidx == 3):
                                mask = 1
                            else:
                                mask = 0
                        elif (uc_north): # N, NE
                            if (self.input_qbidx == 2 or self.input_qbidx == 3):
                                mask = 1
                            else:
                                mask = 0
                        elif (uc_west): # W, SW
                            if (self.input_qbidx == 1 or self.input_qbidx == 3):
                                mask = 1
                            else:
                                mask = 0
                        else: # OTHER UCs in left-top
                            mask = 1
                    elif (uc_rightdiag):
                        if (self.input_id == 2):
                            if (self.input_qbidx == 0):
                                mask = 1
                            else:
                                mask = 0
                        else: # self.input_id == 0, 1
                            mask = 1
                    elif (uc_valid): # uc_lowtri
                        if (self.input_id == 2):
                            mask = 0
                        else: # self.input_id == 0, 1
                            mask = 1
                    else: # INVALID UC
                        mask = 0
                
                elif self.input_pchtype == 'x':
                    #self.input_id == 0, 1, 2
                    if (uc_west and uc_north): # NW
                        if (self.input_qbidx == 3):
                            mask = 1
                        else:
                            mask = 0
                    elif (uc_north): # N, NE
                        if (self.input_qbidx == 2 or self.input_qbidx == 3):
                            mask = 1
                        else:
                            mask = 0
                    elif (uc_west): # W, SW
                        if (self.input_qbidx == 1 or self.input_qbidx == 3):
                            mask = 1
                        else:
                            mask = 0
                    elif (uc_valid): # C, E, S, SE
                        mask = 1
                    else: # INVALID UC
                        mask = 0
                else: # INIT: PCHTYPE-OTHERS
                    mask = 0
                
            ## INIT-special
            if self.input_pchtype == 'm' or self.input_pchtype == 'mb':
                if self.input_id == 2:
                    if uc_west and uc_south:
                        if self.input_qbidx == 3:
                            special = 1
                        else:
                            special = 0
                    else:
                        special = 0
                else:
                    special = 0
            else:
                special = 0
            special_2 = 0

            # output
            self.output_mask = int(mask)
            self.output_special = int(special)
            self.output_special_2 = int(special_2)
        else:
            raise Exception("mask_generator - transfer_init: block_type {} is currently not supported".format(self.config.block_type))
        return

    def transfer_meas(self):
        (uc_west, uc_north, uc_east, uc_south, uc_lowtri, uc_uppertri, uc_leftdiag, uc_rightdiag) = self.input_ucloc
        uc_valid = False
        for loc in self.input_ucloc:
            uc_valid = uc_valid or loc
        (facebd_w, facebd_n, facebd_e, facebd_s) = self.input_facebd
        (cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se) = self.input_cornerbd
        is_measx = (self.input_opcode == self.config.LQM_X_opcode)
        is_measz = (self.input_opcode == self.config.LQM_Z_opcode)
        is_measy = (self.input_opcode == self.config.LQM_Y_opcode)

        if self.config.block_type == "Distillation":
            #*** MEAS-mask ***#
            if is_measz:
                meas_mask = (self.input_id == 1)
            else:
                meas_mask = True
            if (self.input_qbidx >= 4):
                mask = 0
            else: # for dq
                if (uc_west and uc_north): # NW
                    if (facebd_n == 'pp'): # only for ZB
                        if (self.input_qbidx == 1 or self.input_qbidx == 3):
                            mask = meas_mask
                        else:
                            mask = 0
                    else: # other patches
                        if (cornerbd_nw != 'c'): # except for ZT
                            if (self.input_qbidx == 3):
                                mask = meas_mask
                            else:
                                mask = 0
                        else: # only for ZT
                            mask = 0
                
                elif (uc_north): # N, NE
                    if (facebd_n == 'pp'): # only for ZB
                        mask = meas_mask
                    else: # other patches
                        if (self.input_qbidx == 2 or self.input_qbidx == 3):
                            mask = meas_mask
                        else:
                            mask = 0
                
                elif (uc_west): # W, SW
                    if (uc_south and cornerbd_sw == 'c'): # only for ZB's SW
                        if (self.input_qbidx == 1):
                            mask = meas_mask
                        else:
                            mask = 0
                    else: # others
                        if (self.input_qbidx == 1 or self.input_qbidx == 3):
                            mask = meas_mask
                        else:
                            mask = 0
                
                elif (uc_valid): # C, E, S, SE
                    mask = meas_mask
                else: # INVALID UC
                    mask = 0
             # MEAS-mask 

            #*** MEAS-special ***#
            if (is_measy and self.input_id == 0):
                special = 1
            else:
                special = 0

            special_2 = 0

            # output
            self.output_mask = int(mask)
            self.output_special = int(special)
            self.output_special_2 = int(special_2)
        else:
            raise Exception("mask_generator - transfer_meas: block_type {} is currently not supported".format(self.config.block_type))
        return

    def transfer_initmerge(self):
        (uc_west, uc_north, uc_east, uc_south, uc_lowtri, uc_uppertri, uc_leftdiag, uc_rightdiag) = self.input_ucloc
        (facebd_w, facebd_n, facebd_e, facebd_s) = self.input_facebd
        (cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se) = self.input_cornerbd
        uc_valid = False
        for loc in self.input_ucloc:
            uc_valid = uc_valid or loc
        anc_pchtype = ('a' in self.input_pchtype)
        

        if self.config.block_type == "Distillation":
            #*** INIT_MERGE-mask ***#
            if (self.input_qbidx >= 4):
                mask = 0
            else:
                if (uc_west and uc_north): # NW
                    if (self.input_qbidx == 0): # for entdq
                        mask = 0
                    elif (self.input_qbidx == 1):
                        if (facebd_n == 'pp' and not self.input_pchtype == 'zb'):
                            mask = 1
                        else:
                            mask = 0
                    elif (self.input_qbidx == 2):
                        mask = (facebd_w == 'mp' or facebd_w == 'pp')
                    else: # self.input_qbidx == 3
                        if (self.input_pchtype == 'mt'):
                            mask = (self.input_id <= 1)
                        elif (anc_pchtype):
                            mask = 1
                        else:
                            mask = 0
                
                elif (uc_north): # N, NE
                    if (self.input_qbidx == 0 or self.input_qbidx == 1):
                        if (facebd_n == 'pp' and not self.input_pchtype == 'zb'):
                            mask = 1
                        else:
                            mask = 0
                    else: # self.input_qbidx == 2, 3
                        if (self.input_pchtype == 'mt'):
                            mask = (self.input_id <= 1)
                        elif (anc_pchtype):
                            mask = 1
                        else:
                            mask = 0
                elif (uc_west): # W, SW
                    if (self.input_qbidx == 1 or self.input_qbidx == 3):
                        if (self.input_pchtype == 'mt'):
                            mask = (self.input_id <= 1)
                        elif (anc_pchtype):
                            mask = 1
                        else:
                            mask = 0
                    else: # self.input_qbidx == 0, 2
                        mask = (facebd_w == 'mp' or facebd_w == 'pp')
                elif (uc_valid):# C, E, S, SE
                    if (self.input_pchtype == 'mt'):
                        mask = (self.input_id <= 1)
                    elif (anc_pchtype):
                        mask = 1
                    else:
                        mask = 0
                else: # INVALID UC
                    mask = 0
            #*** INIT_MERGE-special ***#
            special = 0
            special_2 = 0

            # output
            self.output_mask = int(mask) 
            self.output_special = int(special)
            self.output_special_2 = int(special_2)
        else:
            raise Exception("mask_generator - transfer_initmerge: block_type {} is currently not supported".format(self.config.block_type))
        return


    def transfer_meassplit(self):
        (uc_west, uc_north, uc_east, uc_south, uc_lowtri, uc_uppertri, uc_leftdiag, uc_rightdiag) = self.input_ucloc
        (facebd_w, facebd_n, facebd_e, facebd_s) = self.input_facebd
        uc_valid = False
        for loc in self.input_ucloc:
            uc_valid = uc_valid or loc

        anc_pchtype = ('a' in self.input_pchtype)

        if self.config.block_type == "Distillation":
            #*** MEAS_SPLIT-mask ***#
            if (self.input_qbidx >= 4):
                mask = 0;
            else:
                if (uc_west and uc_north): # NW
                    if (self.input_qbidx == 1):
                        mask = (facebd_n == 'pp' and self.input_pchtype != 'zb')
                    elif (self.input_qbidx == 2):
                        mask = (facebd_w == 'mp' or facebd_w == 'pp')
                    elif (self.input_qbidx == 3):
                        mask = (anc_pchtype)
                    else:
                        mask = 0;
                elif (uc_north): # N, NE
                    if (self.input_qbidx == 0 or self.input_qbidx == 1):
                        mask = (facebd_n == 'pp' and self.input_pchtype != 'zb')
                    else: # self.input_qbidx == 2, 3
                        mask = (anc_pchtype)
                elif (uc_west): # W, SW
                    if (self.input_qbidx == 1 or self.input_qbidx == 3):
                        mask = (anc_pchtype)
                    else: # self.input_qbidx == 0, 2
                        mask = (facebd_w == 'mp' or facebd_w == 'pp')
                elif (uc_valid):# C, E, S, SE
                    mask = (anc_pchtype)
                else: # INVALID UC
                    mask = 0;
            #*** MEAS_SPLIT-special ***#
            special = 0;
            special_2 = 0

            # output
            self.output_mask = int(mask)
            self.output_special = int(special)
            self.output_special_2 = int(special_2)
        else:
            raise Exception("mask_generator - transfer_meassplit: block_type {} is currently not supported".format(self.config.block_type))
        return

    
    def transfer_esm(self):
        if self.config.block_type == "Distillation":
            # common wire setup
            (uc_west, uc_north, uc_east, uc_south, uc_lowtri, uc_uppertri, uc_leftdiag, uc_rightdiag) = self.input_ucloc
            uc_valid = False
            for loc in self.input_ucloc:
                uc_valid = uc_valid or loc


            (facebd_w, facebd_n, facebd_e, facebd_s) = self.input_facebd
            (cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se) = self.input_cornerbd

            is_entq4id = (self.input_id in [0, 2, 16, 18])
            is_entq5id = (self.input_id in [0, 1, 17, 18])
            is_entq6id = is_entq4id
            is_entq7id = is_entq5id
            is_normaqid = (self.input_id in [5, 6, 8, 10, 12, 13, 19])
            is_entdqid = (self.input_id in [0, 1, 2, 16, 17, 18, 19])
            # reverse or not
            if self.input_pchtype == 'mt':
                is_q0q4id = int(self.input_id in [8]) 
                is_q0q5id = int(self.input_id in [10])
                is_q0q6id = int(self.input_id in [5, 6, 7])
                is_q0q7id = int(self.input_id in [11, 12, 13])
                is_q1q4id = int(self.input_id in [6])
                is_q1q5id = int(self.input_id in [12])
                is_q1q6id = int(self.input_id in [9, 10, 11])
                is_q1q7id = int(self.input_id in [7, 8, 9])
                is_q2q4id = int(self.input_id in [12])
                is_q2q5id = int(self.input_id in [6])
                is_q2q6id = int(self.input_id in [7, 8, 9])
                is_q2q7id = int(self.input_id in [9, 10, 11])
                is_q3q4id = int(self.input_id in [10])
                is_q3q5id = int(self.input_id in [8])
                is_q3q6id = int(self.input_id in [11, 12, 13])
                is_q3q7id = int(self.input_id in [5, 6, 7])
            else: # zt, zb, mt, mb, m , x, aint(aw, ac, ae, awe)
                is_q0q4id = int(self.input_id in [7, 8, 9]) 
                is_q0q5id = int(self.input_id in [9, 10, 11])
                is_q0q6id = int(self.input_id in [6])
                is_q0q7id = int(self.input_id in [12])
                is_q1q4id = int(self.input_id in [5, 6, 7])
                is_q1q5id = int(self.input_id in [11, 12, 13])
                is_q1q6id = int(self.input_id in [10])
                is_q1q7id = int(self.input_id in [8])
                is_q2q4id = int(self.input_id in [11, 12, 13])
                is_q2q5id = int(self.input_id in [5, 6, 7])
                is_q2q6id = int(self.input_id in [8])
                is_q2q7id = int(self.input_id in [10])
                is_q3q4id = int(self.input_id in [9, 10, 11])
                is_q3q5id = int(self.input_id in [7, 8, 9])
                is_q3q6id = int(self.input_id in [12])
                is_q3q7id = int(self.input_id in [6])
           
            is_q0q45id = int(is_q0q4id ^ is_q0q5id)
            is_q0q46id = int(is_q0q4id ^ is_q0q6id)
            is_q0q47id = int(is_q0q4id ^ is_q0q7id)
            is_q0q56id = int(is_q0q5id ^ is_q0q6id)
            is_q0q57id = int(is_q0q5id ^ is_q0q7id)
            is_q0q67id = int(is_q0q6id ^ is_q0q7id)
            is_q1q45id = int(is_q1q4id ^ is_q1q5id)
            is_q1q46id = int(is_q1q4id ^ is_q1q6id)
            is_q1q47id = int(is_q1q4id ^ is_q1q7id)
            is_q1q56id = int(is_q1q5id ^ is_q1q6id)
            is_q1q57id = int(is_q1q5id ^ is_q1q7id)
            is_q1q67id = int(is_q1q6id ^ is_q1q7id)
            is_q2q45id = int(is_q2q4id ^ is_q2q5id)
            is_q2q46id = int(is_q2q4id ^ is_q2q6id)
            is_q2q47id = int(is_q2q4id ^ is_q2q7id)
            is_q2q56id = int(is_q2q5id ^ is_q2q6id)
            is_q2q57id = int(is_q2q5id ^ is_q2q7id)
            is_q2q67id = int(is_q2q6id ^ is_q2q7id)
            is_q3q45id = int(is_q3q4id ^ is_q3q5id)
            is_q3q46id = int(is_q3q4id ^ is_q3q6id)
            is_q3q47id = int(is_q3q4id ^ is_q3q7id)
            is_q3q56id = int(is_q3q5id ^ is_q3q6id)
            is_q3q57id = int(is_q3q5id ^ is_q3q7id)
            is_q3q67id = int(is_q3q6id ^ is_q3q7id)

            is_q0q456id = int(is_q0q4id ^ is_q0q5id ^ is_q0q6id)
            is_q0q457id = int(is_q0q4id ^ is_q0q5id ^ is_q0q7id)
            is_q0q467id = int(is_q0q4id ^ is_q0q6id ^ is_q0q7id)
            is_q0q567id = int(is_q0q5id ^ is_q0q6id ^ is_q0q7id)
            is_q1q456id = int(is_q1q4id ^ is_q1q5id ^ is_q1q6id)
            is_q1q457id = int(is_q1q4id ^ is_q1q5id ^ is_q1q7id)
            is_q1q467id = int(is_q1q4id ^ is_q1q6id ^ is_q1q7id)
            is_q1q567id = int(is_q1q5id ^ is_q1q6id ^ is_q1q7id)
            is_q2q456id = int(is_q2q4id ^ is_q2q5id ^ is_q2q6id)
            is_q2q457id = int(is_q2q4id ^ is_q2q5id ^ is_q2q7id)
            is_q2q467id = int(is_q2q4id ^ is_q2q6id ^ is_q2q7id)
            is_q2q567id = int(is_q2q5id ^ is_q2q6id ^ is_q2q7id)
            is_q3q456id = int(is_q3q4id ^ is_q3q5id ^ is_q3q6id)
            is_q3q457id = int(is_q3q4id ^ is_q3q5id ^ is_q3q7id)
            is_q3q467id = int(is_q3q4id ^ is_q3q6id ^ is_q3q7id)
            is_q3q567id = int(is_q3q5id ^ is_q3q6id ^ is_q3q7id)

            is_q0allid = int(is_q0q4id ^ is_q0q5id ^ is_q0q6id ^ is_q0q7id)
            is_q1allid = int(is_q1q4id ^ is_q1q5id ^ is_q1q6id ^ is_q1q7id)
            is_q2allid = int(is_q2q4id ^ is_q2q5id ^ is_q2q6id ^ is_q2q7id)
            is_q3allid = int(is_q3q4id ^ is_q3q5id ^ is_q3q6id ^ is_q3q7id)

            reverse = (self.input_pchtype == 'mt')
            anc_pchtype = ('a' in self.input_pchtype)

            #*** RESM-mask ***#
            if (uc_west and uc_north): # RESM-NW
                if(self.input_qbidx == 0): 
                    # PCHTYPE-MB, MERGED
                    if (cornerbd_nw == 'ye'):
                        mask = is_entdqid
                    # PCHTYPE-AW, MERGED
                    elif (cornerbd_nw == 'ie' or cornerbd_nw == 'ze'):
                        mask = is_entdqid
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 1): 
                    if (facebd_n == 'pp'):
                    
                        # PCHTYPE-M, BOTTOM, MERGED
                        # PCHTYPE-A, MERGED with above M
                        if (cornerbd_nw == 'z' or cornerbd_nw == 'ze'):
                            mask = is_q1q567id
                        # PCHTYPE-ZB
                        else:
                            mask = is_q1q56id
                    
                    # PCHTYPE-MB, SPLIT, MERGED
                    elif (facebd_n == 'lp'):
                        mask = is_entdqid
                    # 
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 2): 
                    if (facebd_w == 'pp'):
                    
                        # PCHTYPE-MB, MERGED
                        if (cornerbd_nw == 'ye'):
                            mask = is_q2allid
                        # PCHTYPE-A, ALWAYS
                        # PCHTYPE-X, MERGED
                        else:
                            mask = is_q2q567id
                    
                    elif (facebd_w == 'mp'):
                    
                        # PCHTYPE-MT, MERGED
                        mask = is_q2q457id
                    
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 3): 
                    if (facebd_w == 'pp'):
                    
                        # PCHTYPE-MB, MERGED
                        if (cornerbd_nw == 'ye'):
                            mask = is_q3allid
                        # PCHTYPE-A, ALWAYS
                        # PCHTYPE-X, MERGED
                        else:
                            mask = is_q3q567id
                    
                    # PCHTYPE-MT, MERGED
                    elif (facebd_w == 'mp'):
                    
                        mask = is_q3q457id
                    
                    # PCHTYPE-M, MERGED (with top)
                    # PCHTYPE-ZB, ALWAYS
                    elif (facebd_n == 'pp'):
                    
                        mask = is_q3q567id
                    
                    # PCHTYPE-MB, SPLIT
                    elif (facebd_n == 'lp'):
                    
                        mask = is_q3q456id
                    
                    elif (facebd_n == 'x'):
                        # PCHTYPE-M, not MERGED with top
                        if (cornerbd_nw != 'c'):
                            mask = is_q3q57id
                        # PCHTYPE-ZT
                        else:
                            mask = 0
                    
                    elif (facebd_n == 'z'):
                        # PCHTYPE-MT, SPLIT
                        if (reverse):
                            mask = is_q3q57id
                        # PCHTYPE-X, PS
                        # PCHTYPE-MP, P
                        else:
                            mask = is_q3q56id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 4): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq4id):
                    
                        # PCHTYPE-MB, SM
                        mask = (facebd_n == 'lp')
                    
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 5): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 6): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq6id):
                    
                        # PCHTYPE-MB, SM
                        mask = (facebd_n == 'lp')
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 7): 
                    mask = is_normaqid
                
                else: 
                    mask = 0
                    
            
            elif (uc_north and not uc_east): # RESM-N
                if(self.input_qbidx == 0): 
                    if (facebd_n == 'pp'):
                        mask = is_q0allid
                    elif (facebd_n == 'lp'):
                        mask = is_entdqid
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 1): 
                    if (facebd_n == 'pp'):
                        mask = is_q1allid
                    elif (facebd_n == 'lp'):
                        mask = is_entdqid
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 2): 
                    if (facebd_n == 'pp' or facebd_n == 'lp'):
                        mask = is_q2allid
                    elif (facebd_n == 'x'):
                        mask = is_q2q457id
                    elif (facebd_n == 'z'):
                        if (reverse):
                            mask = is_q2q457id
                        else:
                            mask = is_q2q567id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 3): 
                    if (facebd_n == 'pp' or facebd_n == 'lp'):
                        mask = is_q3allid
                    elif (facebd_n == 'x'):
                        mask = is_q3q457id
                    elif (facebd_n == 'z'):
                    
                        if (reverse):
                            mask = is_q3q457id
                        else:
                            mask = is_q3q567id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 4): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq4id):
                        mask = (facebd_n == 'lp')
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 5): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 6): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq6id):
                        mask = (facebd_n == 'lp')
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 7): 
                    mask = is_normaqid
                
                else: 
                    mask = 0
                
            elif (uc_north): # RESM-NE
                if(self.input_qbidx == 0): 
                    if (facebd_n == 'lp'):
                        mask = is_entdqid
                    elif (facebd_n == 'pp'):
                        mask = is_q0allid
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 1): 
                    if (facebd_n == 'lp'):
                        mask = is_entdqid
                    elif (facebd_n == 'pp'):
                    
                        if (facebd_w == 'pp' or (facebd_w == 'z' and facebd_e == 'z')):
                            mask = is_q1q467id
                        elif (facebd_w == 'z' and facebd_e == 'x'):
                            mask = is_q1q47id
                        elif (facebd_w == 'z' and facebd_e == 'pp'):
                            mask = is_q1q457id
                        else:
                            mask = 0
                    
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 2): 
                    if (facebd_n == 'pp' or facebd_n == 'lp'):
                        mask = is_q2allid
                    elif (facebd_n == 'x'):
                        mask = is_q2q457id
                    elif (facebd_n == 'z'):
                    
                        if (reverse):
                            mask = is_q2q457id
                        else:
                            mask = is_q2q567id
                    
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 3): 
                    if (facebd_n == 'z' and facebd_e == 'z'):
                    
                        if (reverse):
                            mask = is_q3q457id
                        else:
                            mask = 0
                    
                    elif (facebd_n == 'z' and facebd_e == 'x'):
                        mask = is_q3q57id
                    elif (facebd_n == 'x' and facebd_e == 'z'):
                        mask = is_q3q47id
                    elif (facebd_n == 'pp' or facebd_n == 'lp'):
                    
                        if (facebd_e == 'pp'):
                            mask = is_q3allid
                        elif (facebd_e == 'z'):
                            mask = is_q3q467id
                        elif (facebd_e == 'x'):
                            mask = is_q3q457id
                        else:
                            mask = 0
                    elif (facebd_n == 'z' and facebd_e == 'pp'):
                        mask = is_q3allid
                    elif (facebd_e == 'mp'):
                        mask = is_q3q457id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 4): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq4id):
                        mask = (facebd_n == 'lp')
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 5): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 6): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq6id):
                        mask = (cornerbd_ne == 'y' or cornerbd_nw == 'ye')
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 7): 
                    mask = is_normaqid
                
                else: 
                    mask = 0
            
            elif (uc_west and not uc_south): # RESM-W
                if(self.input_qbidx == 0): 
                    if (facebd_w == 'mp' or facebd_w == 'pp'):
                        mask = is_q0allid
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 1): 
                    if (facebd_w == 'mp' or facebd_w == 'pp'):
                        mask = is_q1allid
                    elif (facebd_w == 'x'):
                    
                        if (reverse):
                            mask = is_q1q567id
                        else:
                            mask = is_q1q456id
                    
                    elif (facebd_w == 'z'):
                        mask = is_q1q567id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 2): 
                    if (facebd_w == 'mp' or facebd_w == 'pp'):
                        mask = is_q2allid
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 3): 
                    if (facebd_w == 'mp' or facebd_w == 'pp'):
                        mask = is_q3allid
                    elif (facebd_w == 'x'):
                    
                        if (reverse):
                            mask = is_q3q567id
                        else:
                            mask = is_q3q456id
                    
                    elif (facebd_w == 'z'):
                        mask = is_q3q567id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 4): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 5): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 6): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 7): 
                    mask = is_normaqid
                
                else: 
                    mask = 0
            
            elif (uc_east and not uc_south): # RESM-E
                if(self.input_qbidx == 0): 
                    mask = is_q0allid
                
                elif(self.input_qbidx == 1): 
                    if (facebd_e == 'pp' or facebd_e == 'mp'):
                        mask = is_q1allid
                    elif (facebd_e == 'z'):
                    
                        if (reverse):
                            mask = is_q1q457id
                        else:
                            mask = is_q1q467id
                    
                    elif (facebd_e == 'x'):
                        mask = is_q1q457id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 2): 
                    mask = is_q2allid
                
                elif(self.input_qbidx == 3): 
                    if (facebd_e == 'pp' or facebd_e == 'mp'):
                        mask = is_q3allid
                    elif (facebd_e == 'z'):
                    
                        if (reverse):
                            mask = is_q3q457id
                        else:
                            mask = is_q3q467id
                    
                    elif (facebd_e == 'x'):
                        mask = is_q3q457id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 4): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 5): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 6): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 7): 
                    mask = is_normaqid
                
                else: 
                    mask = 0
            
            elif (uc_south and uc_west): # RESM-SW
                if(self.input_qbidx == 0): 
                    if (facebd_w == 'pp' or facebd_w == 'mp'):
                        mask = is_q0allid
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 1): 
                    if (facebd_w == 'pp' or facebd_w == 'mp'):
                        mask = is_q1allid
                    elif (facebd_w == 'x'):
                    
                        if (reverse):
                            mask = is_q1q567id
                        else:
                            mask = is_q1q456id
                    
                    elif (facebd_w == 'z'):
                        mask = is_q1q567id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 2): 
                    if (facebd_w == 'pp'):
                        mask = is_q2q467id
                    elif (facebd_w == 'mp'):
                        mask = is_q2allid
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 3): 
                    if (facebd_s == 'pp' or facebd_s == 'lp'):
                    
                        if (facebd_w == 'pp' or facebd_w == 'mp'):
                            mask = is_q3allid
                        elif (facebd_w == 'x'):
                        
                            if (reverse):
                                mask = is_q3q567id
                            else:
                                mask = is_q3q456id
                        
                        elif (facebd_w == 'z'):
                            mask = is_q3q567id
                        else:
                            mask = 0
                    
                    elif (facebd_s == 'z'):
                    
                        if (facebd_w == 'pp'):
                            mask = is_q3q467id
                        elif (facebd_w == 'x'):
                            mask = is_q3q46id
                        else:
                            mask = 0
                    
                    elif (facebd_s == 'x'):
                        mask = is_q3q56id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 4): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 5): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq5id):
                        mask = (facebd_s == 'lp')
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 6): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 7): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq7id):
                        mask = (facebd_s == 'lp')
                    else:
                        mask = 0
                
                else: 
                    mask = 0
            
            elif (uc_south and not uc_east): # RESM-S
                if(self.input_qbidx == 0): 
                    mask = is_q0allid
                
                elif(self.input_qbidx == 1): 
                    mask = is_q1allid
                
                elif(self.input_qbidx == 2): 
                    if (facebd_s == 'pp' or facebd_s == 'lp'):
                        mask = is_q2allid
                    elif (facebd_s == 'z'):
                        mask = is_q2q467id
                    elif (facebd_s == 'x'):
                        mask = is_q2q456id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 3): 
                    if (facebd_s == 'pp' or facebd_s == 'lp'):
                        mask = is_q3allid
                    elif (facebd_s == 'z'):
                        mask = is_q3q467id
                    elif (facebd_s == 'x'):
                        mask = is_q3q456id
                    else:
                        mask = 0
                elif(self.input_qbidx == 4): 
                    mask = is_normaqid
                elif(self.input_qbidx == 5): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq5id):
                        mask = (facebd_s == 'lp')
                    else:
                        mask = 0
                elif(self.input_qbidx == 6): 
                    mask = is_normaqid
                elif(self.input_qbidx == 7): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq7id):
                        mask = (facebd_s == 'lp')
                    else:
                        mask = 0
                else: 
                    mask = 0
            
            elif (uc_south): # RESM-SE
                if(self.input_qbidx == 0): 
                    mask = is_q0allid
                elif(self.input_qbidx == 1): 
                    if (facebd_e == 'pp' or facebd_e == 'mp'):
                        mask = is_q1allid
                    elif (facebd_e == 'z'):
                        if (reverse):
                            mask = is_q1q457id
                        else:
                            mask = is_q1q467id
                    elif (facebd_e == 'x'):
                        mask = is_q1q457id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 2): 
                    if (facebd_s == 'pp' or facebd_s == 'lp'):
                        mask = is_q2allid
                    elif(facebd_s == 'z'):
                        mask = is_q2q467id
                    elif (facebd_s == 'x'):
                        mask = is_q2q456id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 3): 
                    if (facebd_e == 'mp'):
                        mask = is_q3allid
                    elif (facebd_e == 'pp' or facebd_s == 'pp'):
                        mask = is_q3q467id
                    elif (facebd_e == 'z' and facebd_s == 'z'):
                        mask = is_q3q467id
                    elif (facebd_s == 'lp'):
                        if (cornerbd_se == 'z'):
                            mask = is_q3q457id
                        else:
                            mask = is_q3q47id
                    elif (facebd_e == 'x' and facebd_s == 'z'):
                        mask = is_q3q47id
                    elif (facebd_e == 'z' and facebd_s == 'x'):
                        mask = is_q3q46id
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 4): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 5): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq5id):
                    
                        if (facebd_e == 'mp'):
                            mask = 1
                        elif (facebd_s == 'lp' and cornerbd_se == 'z'):
                            mask = 1
                        else:
                            mask = 0
                    
                    else:
                        mask = 0
                
                elif(self.input_qbidx == 6): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 7): 
                    if (is_normaqid):
                        mask = 1
                    elif (is_entq7id):
                        mask = (facebd_s == 'lp')
                    else:
                        mask = 0
                
                else: 
                    mask = 0
            
            elif (uc_valid): # RESM-C
                if(self.input_qbidx == 0): 
                    mask = is_q0allid
                
                elif(self.input_qbidx == 1): 
                    mask = is_q1allid
                
                elif(self.input_qbidx == 2): 
                    mask = is_q2allid
                
                elif(self.input_qbidx == 3): 
                    mask = is_q3allid
                
                elif(self.input_qbidx == 4): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 5): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 6): 
                    mask = is_normaqid
                
                elif(self.input_qbidx == 7): 
                    mask = is_normaqid
                
                else: 
                    mask = 0
            else: # RESM-INVALID UC
                mask = 0

            #*** RESM-special ***#
            if (self.input_pchtype == 'zb'):
            
                if (is_q1q5id and (uc_north and uc_east) and (self.input_qbidx == 1)):
                    special = (facebd_e == 'pp')
                else:
                    special = 0
            
            else:
                special = 0

            special_2 = 0
            # output
            self.output_mask = int(mask)
            self.output_special = int(special)
            self.output_special_2 = int(special_2)
        else:
            raise Exception("mask_generator - transfer_esm: block_type {} is currently not supported".format(self.config.block_type))

        return

class target_generator:
    def __init__(self, param):
        self.config = param
        # Parameter 
        # Wires
        ## Input wire
        self.input_opcode = None
        self.input_qbidx = None
        self.input_id = None
        ## Output wire 
        self.output_target = None

    def transfer(self): 
        if self.config.block_type == "Distillation":
            if self.input_opcode == self.config.RUN_ESM_opcode:
                if self.input_id == 1:
                    if self.input_qbidx == 0:
                        self.output_target = 5
                    elif self.input_qbidx == 1:
                        self.output_target = 7
                    elif self.input_qbidx == 5:
                        self.output_target = 0
                    elif self.input_qbidx == 7:
                        self.output_target = 1
                    else:
                        self.output_target = nan
                elif self.input_id == 2:
                    if self.input_qbidx == 0:
                        self.output_target = 6
                    elif self.input_qbidx == 1:
                        self.output_target = 4
                    elif self.input_qbidx == 4:
                        self.output_target = 1
                    elif self.input_qbidx == 6:
                        self.output_target = 0
                    else:
                        self.output_target = nan
                ######
                elif self.input_id == 6:
                    if self.input_qbidx == 0:
                        self.output_target = 6
                    elif self.input_qbidx == 1:
                        self.output_target = 4
                    elif self.input_qbidx == 2:
                        self.output_target = 5
                    elif self.input_qbidx == 3:
                        self.output_target = 7
                    elif self.input_qbidx == 4:
                        self.output_target = 1
                    elif self.input_qbidx == 5:
                        self.output_target = 2
                    elif self.input_qbidx == 6:
                        self.output_target = 0
                    elif self.input_qbidx == 7:
                        self.output_target = 3
                    else:
                        self.output_target = nan

                elif self.input_id == 8:
                    if self.input_qbidx == 0:
                        self.output_target = 4
                    elif self.input_qbidx == 1:
                        self.output_target = 7
                    elif self.input_qbidx == 2:
                        self.output_target = 6
                    elif self.input_qbidx == 3:
                        self.output_target = 5
                    elif self.input_qbidx == 4:
                        self.output_target = 0
                    elif self.input_qbidx == 5:
                        self.output_target = 3
                    elif self.input_qbidx == 6:
                        self.output_target = 2
                    elif self.input_qbidx == 7:
                        self.output_target = 1
                    else:
                        self.output_target = nan
                    
                elif self.input_id == 10:
                    if self.input_qbidx == 0:
                        self.output_target = 5
                    elif self.input_qbidx == 1:
                        self.output_target = 6
                    elif self.input_qbidx == 2:
                        self.output_target = 7
                    elif self.input_qbidx == 3:
                        self.output_target = 4
                    elif self.input_qbidx == 4:
                        self.output_target = 3
                    elif self.input_qbidx == 5:
                        self.output_target = 0
                    elif self.input_qbidx == 6:
                        self.output_target = 1
                    elif self.input_qbidx == 7:
                        self.output_target = 2
                    else:
                        self.output_target = nan
                   
                elif self.input_id == 12:
                    if self.input_qbidx == 0:
                        self.output_target = 7
                    elif self.input_qbidx == 1:
                        self.output_target = 5
                    elif self.input_qbidx == 2:
                        self.output_target = 4
                    elif self.input_qbidx == 3:
                        self.output_target = 6
                    elif self.input_qbidx == 4:
                        self.output_target = 2
                    elif self.input_qbidx == 5:
                        self.output_target = 1
                    elif self.input_qbidx == 6:
                        self.output_target = 3
                    elif self.input_qbidx == 7:
                        self.output_target = 0
                    else:
                        self.output_target = nan
                ######
                elif self.input_id == 16:
                    if self.input_qbidx == 0:
                        self.output_target = 6
                    elif self.input_qbidx == 1:
                        self.output_target = 4
                    elif self.input_qbidx == 4:
                        self.output_target = 1
                    elif self.input_qbidx == 6:
                        self.output_target = 0
                    else:
                        self.output_target = nan
                elif self.input_id == 17:
                    if self.input_qbidx == 0:
                        self.output_target = 5
                    elif self.input_qbidx == 1:
                        self.output_target = 7
                    elif self.input_qbidx == 5:
                        self.output_target = 0
                    elif self.input_qbidx == 7:
                        self.output_target = 1
                    else:
                        self.output_target = nan
                else:
                    self.output_target = nan
            else:
                self.output_target = nan
        else:
            raise Exception("target_generator - transfer: block_type {} is currently not supported".format(self.config.block_type))

        return
