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
import numpy as np
import copy
from math import *

class pauliframe_unit:
    def __init__ (self, unit_stat, config):
        # 
        self.config = config
        #
        self.unit_stat = unit_stat
        self.init_stats()
        # Wires 
        ## Input wire
        ### stall
        self.input_pchwr_stall = None 
        ### from piu
        #### to pchinfo_srmem
        self.input_pchinfo = None
        self.input_topsu_valid = None
        self.input_last_pchinfo = None
        #### to piu_opcode_buf
        self.input_piu_opcode = None
        ### from tcu
        self.input_tcu_valid = None
        self.input_tcu_opcode = None
        ### from edu
        self.input_error_array = None
        self.input_error_valid = None
        self.input_pfflag = None
        ## Intermediate wire
        ### from control
        self.next_state = None
        self.pisrmem_push = None
        self.pisrmem_pop = None
        self.opbuf_push = None
        self.opbuf_pop = None
        self.sel_cwd_err = None
        self.next_valid = None
        self.pf_wren = None
        ### from pchinfo_srmem
        self.pchinfo = None # single rdport
        self.pchinfo_full = None
        self.pchinfo_valid = None
        self.pchinfo_rdlast = None
        ### from piu_opcode_buf
        self.cwd_opcode = None
        ### from cwdpatch & array
        self.cwd_patch = None
        self.cwd_array = None
        ### from new_pfarray
        self.new_pfarray = None

        ## Output wire
        self.output_pfarray = None
        self.output_valid = None

        # Registers
        ## Input register
        self.tcu_opcode_reg = "1"*self.config.opcode_bw
        # Per-cell register
        self.pfarray_reg = np.full((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), 'i',dtype='U8')
        ## State
        self.state = "ready"
        ## 
        self.valid_reg = False
        
        # Microunit
        self.piu_opcode_buf = buffer.buffer("pfu_opbuf", 2)
        self.pchinfo_srmem = srmem.srmem_double("pchinfo_srmem_pfu", 1, self.config.num_pch)

        # Variables
        self.output_pfarray_list = list()
        self.pfarray_counter = 0

    def init_stats(self):
        # Data transfer 
        ### to LMU
        self.unit_stat.data_transfer["LMU"] = {
                "num_eff": [], 
                "num_max": [], 
                "cycle": [],
                "bw": 2, # PP
                "last_cyc": 0
                }
        #
        self.unit_stat.num_acc_cyc = 0
        self.unit_stat.num_update_cyc = 0
        return
        
    def update_stats(self, sim_cycle):
        self.unit_stat.num_update_cyc += 1
        # num_acc_cyc
        if self.pf_wren or self.output_valid:
            self.unit_stat.num_acc_cyc += 1
        else:
            pass
        # data_transfer
        if self.output_valid:
            cycle = sim_cycle - self.unit_stat.data_transfer["LMU"]["last_cyc"]
            self.unit_stat.data_transfer["LMU"]["num_eff"].append(ceil(self.config.num_pq_eff/2))
            self.unit_stat.data_transfer["LMU"]["num_max"].append(ceil(self.config.num_pq_eff/2))
            self.unit_stat.data_transfer["LMU"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["LMU"]["last_cyc"] = sim_cycle
        else:
            pass
        return


    def transfer(self):
        self.transfer_control()
        self.transfer_opbuf()
        self.transfer_pchinfo_srmem()
        self.transfer_cwdpatch()
        self.transfer_cwdarray()
        self.transfer_new_pfarray()
        self.transfer_output()
        return

    def transfer_control(self):
        ## next_state
        if self.state == "ready":
            if (self.tcu_opcode_reg == self.config.RUN_ESM_opcode):
                # Assumption: pchinfo_valid == True & cwd_opcode is not None
                # Assumption: Error decoding is finished during (or before) the next RUN_ESM
                self.next_state = "updating"
            else:
                self.next_state = "ready"
        elif self.state == "updating":
            if self.pchinfo_rdlast:
                self.next_state = "waiting"
            else:
                self.next_state = "updating"
        elif self.state == "waiting":
            if self.input_error_valid:
                self.next_state = "ready"
            else:
                self.next_state = "waiting"
        else:
            self.next_state == "ready"

        ## pisrmem_push 
        if (not self.input_pchwr_stall) and \
           (self.input_topsu_valid) and \
           (self.input_piu_opcode != self.config.RUN_ESM_opcode):
            self.pisrmem_push = True
        else:
            self.pisrmem_push = False
        ## pisrmem_pop 
        self.pisrmem_pop = (self.state == "updating")

        ## opbuf_push
        self.opbuf_push = (self.pisrmem_push and self.input_last_pchinfo)

        ## opbuf_pop
        if self.state == "updating" and self.next_state == "waiting":
            self.opbuf_pop = True
        else:
            self.opbuf_pop = False
        
        # sel_cwd_err
        if self.state == "updating":
            self.sel_cwd_err = 0 # for cwdarray
        else: 
            self.sel_cwd_err = 1 # for error

        # next_valid
        if self.state == "waiting" and \
           self.next_state == "ready" and \
           self.input_pfflag: 
            self.next_valid = True
        else:
            self.next_valid = False
        
        # pf_wren
        # Assumption: state == "waiting"
        self.pf_wren = (self.state == "updating" or (self.input_error_valid))

        return


    def transfer_opbuf(self):
        # connect input
        ## data (w/ push)
        if self.opbuf_push:
            self.piu_opcode_buf.input_data = self.input_piu_opcode
        else:
            self.piu_opcode_buf.input_data = None
        ## ready (pop)
        self.piu_opcode_buf.input_ready = self.opbuf_pop
        # transfer
        self.piu_opcode_buf.transfer()
        # connect output
        self.cwd_opcode = self.piu_opcode_buf.head
        return


    def transfer_pchinfo_srmem(self):
        # connect input
        self.pchinfo_srmem.input_valid = self.pisrmem_push
        self.pchinfo_srmem.input_data = self.input_pchinfo
        self.pchinfo_srmem.input_last_data = self.input_last_pchinfo
        self.pchinfo_srmem.input_pop = self.pisrmem_pop
        self.pchinfo_srmem.input_new_data = True
        # transfer
        self.pchinfo_srmem.transfer()
        # connect output
        self.pchinfo = self.pchinfo_srmem.output_data[0]
        self.pchinfo_full = self.pchinfo_srmem.output_wrfull
        self.pchinfo_valid = self.pchinfo_srmem.output_rdvalid
        self.pchinfo_rdlast = self.pchinfo_srmem.output_rdlastinfo
        return

    def transfer_cwdpatch(self):
        # input
        ## pchinfo - pchtype, facebd
        ## cwd_opcode
        # output
        ## cwd_patch - (num_ucrow, num_uccol, num_qb_per_uc/2)
        
        # mask_patch
        mask_patch = np.zeros((self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), dtype=int)
        if self.cwd_opcode is not None and self.pchinfo_valid:
            for (i, j, k), _ in np.ndenumerate(mask_patch):
                ## ucloc calculation
                uc_west = (j == 0)
                uc_north = (i == 0)
                uc_east = (j == self.config.num_uccol-1)
                uc_south = (i == self.config.num_ucrow-1)
                ##
                qbidx = k
                ## pchinfo decomposition
                pchtype = self.pchinfo['data']['pchtype']
                (facebd_w, facebd_n, facebd_e, facebd_s) = self.pchinfo['data']['facebd']
                (cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se) = self.pchinfo['data']['cornerbd']
                ##
                anc_pchtype = ('a' in pchtype) 

                ## for LQI & LQM
                if self.cwd_opcode in [
                        self.config.LQI_opcode,
                        self.config.LQM_X_opcode, 
                        self.config.LQM_Y_opcode, 
                        self.config.LQM_Z_opcode]:
                    if (self.cwd_opcode == self.config.LQI_opcode) and (pchtype == 'mt'):
                        mask = 0
                    else:
                        if self.config.block_type == "Distillation":
                            if (uc_west and uc_north): # NW
                                if (facebd_n == 'pp'): # only for ZB
                                    mask = (qbidx in [1, 3])
                                else: # other patches
                                    if (cornerbd_nw != 'c'):
                                        mask = (qbidx == 3)
                                    else:
                                        mask = 0
                            elif (uc_north): # N, NE
                                if (facebd_n == 'pp'): # only for ZB
                                    mask = 1
                                else: # other patches
                                    mask = (qbidx in [2, 3])
                            elif (uc_west): # W, SW
                                if (uc_south and cornerbd_sw == 'c'): # only for ZB
                                    mask = (qbidx == 1)
                                else: # other patches
                                    mask = (qbidx in [1, 3])

                            else: # C, E, S, SE
                                mask = 1

                        else: 
                            raise Exception("pauliframe_unit - transfer_cwdpatch: block_type {} is currently not supported".format(self.config.block_type))
                    
                ## for INIT/MEAS_INTMD
                elif self.cwd_opcode in [
                       self.config.INIT_INTMD_opcode, 
                       self.config.MEAS_INTMD_opcode]:
                    if self.config.block_type == "Distillation":
                        if (uc_west and uc_north): # NW
                            if (qbidx == 0):
                                mask = 0
                            elif (qbidx == 1):
                                mask = (facebd_n == 'pp' and pchtype != 'zb')
                            elif qbidx == 2:
                                mask = (facebd_w == 'mp' or facebd_w == 'pp')
                            else: #qbidx ==3 
                                if self.cwd_opcode == self.config.INIT_INTMD_opcode:
                                    mask = (pchtype == 'mt' or anc_pchtype)
                                else: # MEAS_INTMD
                                    mask = anc_pchtype
                        elif (uc_north): # N, NE
                            if qbidx in [0, 1]:
                                mask = (facebd_n == 'pp' and pchtype != 'zb')
                            else: # qbidx in [2, 3]
                                if self.cwd_opcode == self.config.INIT_INTMD_opcode:
                                    mask = (pchtype == 'mt' or anc_pchtype)
                                else: # MEAS_INTMD
                                    mask = anc_pchtype
                        elif (uc_west): # W, SW
                            if qbidx in [1, 3]:
                                if self.cwd_opcode == self.config.INIT_INTMD_opcode:
                                    mask = (pchtype == 'mt' or anc_pchtype)
                                else: # MEAS_INTMD
                                    mask = anc_pchtype
                            else: # qbidx in [0, 2]
                                mask = (facebd_w == 'mp' or facebd_w == 'pp')

                        else: # C, E, S, SE
                            if self.cwd_opcode == self.config.INIT_INTMD_opcode:
                                mask = (pchtype == 'mt' or anc_pchtype)
                            else: # MEAS_INTMD
                                mask = anc_pchtype
                    else: 
                        raise Exception("pauliframe_unit - transfer_cwdpatch: block_type {} is currently not supported".format(self.config.block_type))
                ## 
                else:
                    raise Exception("pauliframe_unit - transfer_cwdpatch: cwd_opcode {} is invalid".format(self.cwd_opcode))
                #
                mask_patch[i][j][k] = mask
        else:
            pass # all zeros

        # cwd 
        if self.cwd_opcode in [
                self.config.LQI_opcode, 
                self.config.INIT_INTMD_opcode]:
            cwd = 'cx'
        elif self.cwd_opcode in [
                self.config.LQM_X_opcode,
                self.config.MEAS_INTMD_opcode]: 
            cwd = 'h'
        elif self.cwd_opcode == self.config.LQM_Z_opcode:
            cwd = 'i'
        elif self.cwd_opcode == self.config.LQM_Y_opcode:
            cwd = 'sdag_h'
        else:
            cwd = 'i'

        # cwd_patch
        self.cwd_patch = np.empty((self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), dtype=object)
        for (i, j, k), mask in np.ndenumerate(mask_patch):
            if mask:
                self.cwd_patch[i][j][k] = cwd
            else:
                self.cwd_patch[i][j][k] = 'i'

        return

    def transfer_cwdarray(self): # demux
        self.cwd_array = np.full((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), 'i', dtype='U8')

        if self.pchinfo_valid: 
            # pchidx
            pchrow, pchcol = divmod(self.pchinfo['data']['pchidx'], self.config.num_pchcol)
            # set
            for (i, j, k), cwd in np.ndenumerate(self.cwd_patch):
                self.cwd_array[pchrow][pchcol][i][j][k] = cwd
        else:
            pass # all 'i'
        return
    
    def transfer_new_pfarray(self):
        self.new_pfarray = np.full((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), 'i', dtype='U8')

        for (i, j, k, l, m), curr_pf in np.ndenumerate(self.pfarray_reg):
            # cwd & error
            cwd = self.cwd_array[i][j][k][l][m]
            if self.input_error_valid:
                error = self.input_error_array[i][j][k][l][m]
            else:
                error = 'i'
            # to_pf 
            if (self.sel_cwd_err == 1):
                to_pf = error
            else:
                to_pf = cwd

            # new_pf 
            if to_pf == 'i':
                new_pf = curr_pf
            elif to_pf == 'x':
                if curr_pf == 'i':
                    new_pf = 'x'
                elif curr_pf == 'x':
                    new_pf = 'i'
                elif curr_pf == 'z':
                    new_pf = 'y'
                elif curr_pf == 'y':
                    new_pf = 'z'
                else:
                    new_pf = 'i'
            elif to_pf == 'z':
                if curr_pf == 'i':
                    new_pf = 'z'
                elif curr_pf == 'x':
                    new_pf = 'y'
                elif curr_pf == 'z':
                    new_pf = 'i'
                elif curr_pf == 'y':
                    new_pf = 'x'
                else:
                    new_pf = 'i'
            elif to_pf == 'y':
                if curr_pf == 'i':
                    new_pf = 'y'
                elif curr_pf == 'x':
                    new_pf = 'z'
                elif curr_pf == 'z':
                    new_pf = 'x'
                elif curr_pf == 'y':
                    new_pf = 'i'
                else:
                    new_pf = 'i'
            elif to_pf == 'h':
                if curr_pf == 'i':
                    new_pf = 'i'
                elif curr_pf == 'x':
                    new_pf = 'z'
                elif curr_pf == 'z':
                    new_pf = 'x'
                elif curr_pf == 'y':
                    new_pf = 'y'
                else:
                    new_pf = 'i'
            elif to_pf == 'cx':
                new_pf = 'i'
            elif to_pf == 'sdag_h':
                if curr_pf == 'i':
                    new_pf = 'i'
                elif curr_pf == 'x':
                    new_pf = 'y'
                elif curr_pf == 'z':
                    new_pf = 'x'
                elif curr_pf == 'y':
                    new_pf = 'z'
                else:
                    new_pf = 'i'
            else:
                print("Invalid to_pf in PFU: ", to_pf)
                sys.exit()

            # set
            self.new_pfarray[i][j][k][l][m] = new_pf
        return
    

    def transfer_output(self):
        # pfarray
        self.output_pfarray = np.full((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), 'i', dtype='U8')
        for (i, j, k, l, m), curr_pf in np.ndenumerate(self.pfarray_reg):
            self.output_pfarray[i][j][k][l][m] = curr_pf
        # valid
        self.output_valid = self.valid_reg

        return 

    
    def update(self, sim_cycle=0):
        self.update_stats(sim_cycle)

        self.pchinfo_srmem.update()
        self.piu_opcode_buf.update()
        self.update_registers()
        return
    
    def update_registers(self):
        ## tcu_opcode_reg
        if self.input_tcu_valid:
            self.tcu_opcode_reg = self.input_tcu_opcode

        ## pfarray_reg
        if self.pf_wren:
            for (i, j, k, l, m), _ in np.ndenumerate(self.pfarray_reg):
                new_pf = self.new_pfarray[i][j][k][l][m]
                self.pfarray_reg[i][j][k][l][m] = new_pf
        
        ## state 
        self.state = self.next_state

        ## valid_reg
        self.valid_reg = self.next_valid
        return

    def debug(self):
        # Add variables to check in the debugging mode
        if self.output_valid:
            print("pfu_fin.output_pfarray:")
            debug_array(self.config, self.output_pfarray)
        return

    def save_internal_value (self):
        if self.state == "waiting" and self.next_state == "ready":
            if self.pfarray_counter != 1:
                self.output_pfarray_list.append(copy.deepcopy(self.new_pfarray))

            self.pfarray_counter += 1
            self.pfarray_counter = self.pfarray_counter % 3

        return
