import os, sys 
#
curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
par_dir = os.path.join(curr_dir, os.pardir)
#
sys.path.insert(0, par_dir)
import srmem as srmem
from util import *
import buffer as buffer
#
import copy
import numpy as np

class logical_measurement_unit:
    def __init__(self, unit_stat, config):
        self.config = config
        #
        self.unit_stat = unit_stat
        self.init_stats()
        # Wires
        ## Input wires
        ### stall
        self.input_pchwr_stall = None
        ### from qid
        self.input_to_lqmeas = None # (measflags, lpplist, mregdst, last_flag)
        self.input_lqmeasbuf_empty = None
        self.input_a_taken = None
        ### from piu to pchinfo_srmem
        self.input_pchinfo = None
        self.input_tolmu_valid = None
        self.input_last_pchinfo = None
        ### from tcu
        self.input_opcode = None
        self.input_opcode_valid = None
        ### from edu
        self.input_aqmeas_array = None
        self.input_aqmeas_valid = None
        ### from qxu
        self.input_dqmeas_array = None
        self.input_dqmeas_valid = None
        ### from pfu
        self.input_pf_array = None
        self.input_pf_valid = None
        ## Intermediate wires
        ### from lqsign_gen
        self.lqsign_valid_idx = None
        self.lqsign_valid = None
        self.lqsignZ_temp_list = None
        self.lqsignX_temp_list = None
        ### from selective_meas
        self.initial_meas = None
        ### from interpret
        self.lpplist = None
        self.merged_lqsign = None
        self.not_commute = None
        self.mregdst = None
        self.final_meas = None   
        self.next_byproduct = None 
        ### from control
        self.next_state = None
        self.new_array_ing = None
        self.all_input_ready = None
        self.is_measpp = None
        self.sel_meas = None
        self.initmeas_wren = None
        self.initmeas_rst = None
        self.pchinfo_pop = None
        self.flip_initmeas_wr = None
        self.flip_initmeas_rd = None
        self.instinfo_pop = None
        self.finmeas_wren = None 
        self.byproduct_wren = None
        self.abcd_rst = None
        self.meas_sign = None
        self.byproduct_regwren = None
        self.byproduct_check = None
        self.abcd_wren = None
        self.abcd_addr = None
        self.lqsign_temp_wren = None
        self.lqsign_temp_rst = None
        self.lqsign_acc_wren = None
        ### from instinfo_srmem
        self.instinfo = None # single rdport
        self.instinfo_full = None
        self.instinfo_valid = None
        self.instinfo_nextready = None
        self.instinfo_rdlast = None
        ### from pchinfo_srmem 
        self.pchinfo = None # single rdport
        self.pchinfo_full = None
        self.pchinfo_valid = None
        self.pchinfo_nextready = None
        self.pchinfo_rdlast = None
        ### from measop_buf
        self.measop = None
        ## Output wires
        self.output_xorz = None # from interpret
        self.output_finmeas_reg_val = None
        self.output_finmeas_reg_valid = None
        ## 
        self.done = None

        # Registers
        ## Input registers
        self.dqmeas_ready = False
        self.aqmeas_ready = False
        self.pf_ready = False
        self.dqmeas_array_reg = np.zeros((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), dtype=int)
        self.aqmeas_array_reg = np.zeros((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), dtype=int)
        self.pf_array_reg = np.full((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), 'i',dtype='U8')
        ## Internal registers
        self.dqmeas_array_ing = np.zeros((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), dtype=int)
        self.aqmeas_array_ing = np.zeros((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), dtype=int)
        self.pf_array_ing = np.full((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), 'i',dtype='U8')
        #
        self.sel_initmeas_wr = 0
        self.sel_initmeas_rd = 0
        #
        self.byproduct_reg = np.full((self.config.num_lq), 'I', dtype='U8')
        self.byproduct = np.full((self.config.num_lq), 'I', dtype='U8')
        self.a_taken = False
        self.a_sign = '-'
        #
        self.prev_opcode = '1'*self.config.opcode_bw
        ## State
        self.state = "ready"

        # instinfo_srmem
        # NOTE: num_rd/wr_port = 1
        self.instinfo_srmem = srmem.srmem_double("instinfo_srmem_lmu", 1, self.config.num_lq)
        # pchinfo_srmem 
        # NOTE: num_rd/wr_port = 1
        self.pchinfo_srmem = srmem.srmem_double("pchinfo_srmem_lmu", 1, self.config.num_pch)
        # initmeas_reg
        # NOTE: two registers, 2 wr_port, 1 rd_port
        self.initmeas_reg = [np.zeros((self.config.num_lq), dtype=int), np.zeros((self.config.num_lq), dtype=int)]
        # finmeas_reg
        self.finmeas_reg = []
        for i in range(self.config.num_lq):
            self.finmeas_reg.append({'val':0, 'valid':False})
        # abcd_reg
        self.abcd_reg = []
        for i in range(4):
            self.abcd_reg.append({'val':0, 'valid':False})
        # measop_buf
        self.measop_buf = buffer.buffer("lmu_opbuf", 10)

        # lqsign_temp_reg
        self.lqsign_temp_reg = []
        for i in range(self.config.num_lq):
            self.lqsign_temp_reg.append({'signX':0, 'signZ':0, 'valid':False})

        # lqsign_acc_reg
        self.lqsign_acc_reg = []
        for i in range(self.config.num_lq):
            self.lqsign_acc_reg.append({'signX':0, 'signZ':0})

        self.byproduct_list = list()
        self.lqsign_acc_x = list()
        self.lqsign_acc_z = list()
        self.first_save_flag = True
                
    def init_stats(self):
        self.unit_stat.num_acc_cyc = 0
        self.unit_stat.num_update_cyc = 0
        return

    def update_stats(self, sim_cycle):
        self.unit_stat.num_update_cyc += 1
        # num_acc_cyc
        if self.state != "ready":
            self.unit_stat.num_acc_cyc += 1
        else:
            pass
        return
        
    def transfer(self):
        self.transfer_instinfo_srmem()
        self.transfer_pchinfo_srmem()
        self.transfer_measop_buf()
        self.transfer_control()
        self.transfer_instinfo_srmem()
        self.transfer_pchinfo_srmem()
        self.transfer_control()
        self.transfer_selective_meas()
        self.transfer_lqsign_gen()
        self.transfer_interpret()
        self.transfer_finmeas()
        if self.state == 'ready' and not self.instinfo_valid:
            self.done = True
        else:
            self.done = False
        return

    
    def transfer_lqsign_gen(self):
        # input: pchinfo
        # output: lqsign_valid_idx, lqsign_valid, lqsignZ_temp_list, lqsignX_temp_list
        if self.config.block_type == "Distillation":
            if self.pchinfo_valid:
                pchop = self.pchinfo['data']['pchop']
                pchidx = self.pchinfo['data']['pchidx']
                pchtype = self.pchinfo['data']['pchtype']
                (facebd_w, facebd_n, facebd_e, facebd_s) = self.pchinfo['data']['facebd']
                pchrow, pchcol = divmod(pchidx, self.config.num_pchcol)
                # lqidx generation: reverse of pchmap table
                if pchcol == 0 and (pchrow == 0 or pchrow == 1):
                    lqidx = 0
                elif pchcol == 1 and (pchrow == 0 or pchrow == 1):
                    lqidx = 1
                elif pchrow == 0:
                    lqidx = (pchcol-1) * 2
                elif pchrow == 2:
                    lqidx = (pchcol-1) * 2 + 1
                elif pchrow == 1 and (pchcol == self.config.num_pchcol-1):
                    lqidx = self.config.num_lq - 1
                else: # ancilla or invalid
                    lqidx = -1

                # only for measpp followed by meas_split
                if pchop[0] == self.config.PPM_INTERPRET_opcode \
                or pchop[1] == self.config.PPM_INTERPRET_opcode:
                    # lqsign_valid, lqsign_valid_idx
                    if pchtype in ['zb', 'm', 'x']:
                        self.lqsign_valid = True
                        self.lqsign_valid_idx = lqidx
                    else:
                        self.lqsign_valid = False
                        self.lqsign_valid_idx = 0

                    # lqsign_temp_list
                    dqmeas_array_pch = copy.deepcopy(self.dqmeas_array_ing[pchrow][pchcol])
                    pf_array_pch = copy.deepcopy(self.pf_array_ing[pchrow][pchcol])

                    self.lqsignZ_temp_list = [0]*self.config.num_lq
                    self.lqsignX_temp_list = [0]*self.config.num_lq
                    if pchtype == 'mb':
                        # mb's product affect lq0's signZ/signX
                        dqmeas_product = 0
                        pf_product = 0
                        for (ucrow, uccol, qbidx), _ in np.ndenumerate(dqmeas_array_pch):
                            dqmeas = dqmeas_array_pch[ucrow][uccol][qbidx]
                            pf = pf_array_pch[ucrow][uccol][qbidx]

                            if uccol == 0:
                                if ucrow == 0:
                                    if qbidx == 2:
                                        dqmeas_product ^= dqmeas
                                        pf_product ^= int(pf=='z' or pf=='y')
                                    else:
                                        pass
                                else:
                                    if qbidx in [0, 2]:
                                        dqmeas_product ^= dqmeas
                                        pf_product ^= int(pf=='z' or pf=='y')
                                    else:
                                        pass
                            else:
                                pass
                        sign_product = dqmeas_product ^ pf_product
                        self.lqsignZ_temp_list[0] = sign_product
                        self.lqsignX_temp_list[0] = sign_product

                    elif pchtype == 'm' and facebd_n == 'pp': 
                        # only one dq/pf affect its own lq's signX
                        ucrow = 0
                        uccol = 0
                        qbidx = 1
                        dqmeas = dqmeas_array_pch[ucrow][uccol][qbidx]
                        pf = pf_array_pch[ucrow][uccol][qbidx]
                        sign_product = dqmeas ^ int(pf=='z' or pf=='y')
                        self.lqsignX_temp_list[lqidx] = sign_product

                    elif pchtype == 'x':
                        # only one dq/pf affect its won lq's sign
                        ucrow = self.config.num_ucrow-1
                        uccol = 0
                        qbidx = 2
                        dqmeas = dqmeas_array_pch[ucrow][uccol][qbidx]
                        pf = pf_array_pch[ucrow][uccol][qbidx]
                        sign_product = dqmeas ^ int(pf=='z' or pf=='y')
                        self.lqsignX_temp_list[lqidx] = sign_product
                    elif 'a' in pchtype:
                        # ancilla patches can affect several logical qubits in three different ways
                        ## point -> 'm'-type patch below
                        dqmeas_product_point = 0
                        pf_product_point = 0
                        ## vert -> 'm'-type patch above
                        dqmeas_product_vert = 0
                        pf_product_vert = 0
                        ## horz -> all patches on the right
                        dqmeas_product_horz = 0
                        pf_product_horz = 0
                        
                        ## get products
                        for (ucrow, uccol, qbidx), _ in np.ndenumerate(dqmeas_array_pch):
                            dqmeas = dqmeas_array_pch[ucrow][uccol][qbidx]
                            pf = pf_array_pch[ucrow][uccol][qbidx]

                            ## product_point
                            if (ucrow == self.config.num_ucrow-1) \
                            and (uccol == 0) \
                            and (qbidx == 2):
                                dqmeas_product_point ^= dqmeas
                                pf_product_point ^= int(pf=='z' or pf=='y')
                            else:
                                pass
                            
                            ## product_vert
                            if uccol == 0 :
                                if ucrow == self.config.num_ucrow-1:
                                    if qbidx in [1, 2, 3]:
                                        dqmeas_product_vert ^= dqmeas
                                        pf_product_vert ^= int(pf=='z' or pf=='y')
                                    else:
                                        pass
                                else:
                                    if qbidx in [1, 3]:
                                        dqmeas_product_vert ^= dqmeas
                                        pf_product_vert ^= int(pf=='z' or pf=='y')
                                    else:
                                        pass
                            else:
                                pass

                            ## product_horz
                            if ucrow == self.config.num_ucrow-1:
                                if qbidx in [2, 3]:
                                    dqmeas_product_horz ^= dqmeas
                                    pf_product_horz ^= int(pf=='z' or pf=='y')
                                else:
                                    pass
                            else:
                                pass
                        sign_product_point = dqmeas_product_point ^ pf_product_point
                        sign_product_vert = dqmeas_product_vert ^ pf_product_vert
                        sign_product_horz = dqmeas_product_horz ^ pf_product_horz
                        ## get target lqlists

                        lqlist_point = [0] * self.config.num_lq
                        lqlist_vert = [0] * self.config.num_lq
                        lqlist_horz = [0] * self.config.num_lq
                        
                        lqlist_point[(pchcol-1)*2+1] = 1
                        lqlist_vert[(pchcol-1)*2] = 1
                        for i, _ in enumerate(lqlist_horz):
                            if i >= pchcol*2:
                                lqlist_horz[i] = 1

                        ## set lqsign_temp_list
                        lqsign_point_list = [(idx&sign_product_point) for idx in lqlist_point]
                        lqsign_vert_list = [(idx&sign_product_vert) for idx in lqlist_vert]
                        lqsign_horz_list = [(idx&sign_product_horz) for idx in lqlist_horz]

                        for i in range(self.config.num_lq):
                            self.lqsignX_temp_list[i] = lqsign_point_list[i] | lqsign_vert_list[i] | lqsign_horz_list[i]
                    else: # other patch types
                        pass
                else: # for LQMs
                    if pchtype in ['zb', 'm', 'x']: 
                        self.lqsign_valid = True
                        self.lqsign_valid_idx = lqidx
                        self.lqsignZ_temp_list = [self.lqsign_acc_reg[i]['signZ'] if i == lqidx else 0 for i in range(self.config.num_lq)]
                        self.lqsignX_temp_list = [self.lqsign_acc_reg[i]['signX'] if i == lqidx else 0 for i in range(self.config.num_lq)]
                    else: 
                        self.lqsign_valid = False
                        self.lqsign_valid_idx = 0
                        self.lqsignZ_temp_list = [0]*self.config.num_lq
                        self.lqsignX_temp_list = [0]*self.config.num_lq

            else: # invalid pchinfo
                self.lqsign_valid = False
                self.lqsign_valid_idx = 0
                self.lqsignZ_temp_list = [0]*self.config.num_lq
                self.lqsignX_temp_list = [0]*self.config.num_lq

        else: # unsupported block type
            raise Exception("logical_measure_unit - transfer_lqsign_gen: block_type {} is currently not supported".format(self.config.block_type))
        return


    def transfer_measop_buf(self):
        # connect input
        measop_list = []
        measop_list.append(self.config.LQI_opcode)
        measop_list.append(self.config.INIT_INTMD_opcode)
        measop_list.append(self.config.MEAS_INTMD_opcode)
        measop_list.append(self.config.LQM_X_opcode)
        measop_list.append(self.config.LQM_Y_opcode)
        measop_list.append(self.config.LQM_Z_opcode)
        if self.input_opcode_valid and \
           self.input_opcode in measop_list and \
           self.input_opcode != self.prev_opcode:
            self.measop_buf.input_data = self.input_opcode
        else:
            self.measop_buf.input_data = None
        self.measop_buf.input_ready = self.input_dqmeas_valid
        # transfer
        self.measop_buf.transfer()
        # connect output
        self.measop = self.measop_buf.head
        return

    def transfer_interpret(self):
        if self.instinfo_valid:
            try:
                self.lpplist = self.instinfo['data']['lpplist']
            except:
                print("self.instinfo: {}".format(self.instinfo))
                self.debug()
                raise Exception()
            self.mregdst = self.instinfo['data']['mregdst']
        else:
            self.lpplist = ['I'] * self.config.num_lq
            self.mregdst = 0

        ## merged_lqsign
        self.merged_lqsign = 0
        for i in range(self.config.num_lq):
            lpp = self.lpplist[i] 
            signX = self.lqsign_acc_reg[i]['signX']
            signZ = self.lqsign_acc_reg[i]['signZ']
            
            if lpp in ['X', 'Y']:
                self.merged_lqsign ^= signX
            
            if lpp in ['Z', 'Y']:
                self.merged_lqsign ^= signZ

        if self.merged_lqsign == 0:
            self.merged_lqsign = '+'
        else:
            self.merged_lqsign = '-'

        ## not_commute
        self.not_commute = 0
        for i in range(self.config.num_lq):
            lpp = self.lpplist[i]
            bpp = self.byproduct[i]
            if lpp != bpp and lpp != 'I' and bpp != 'I':
                self.not_commute ^= 1
        self.not_commute = bool(self.not_commute)
        ## init_meas
        init_meas = self.initmeas_reg[self.sel_initmeas_rd][self.mregdst]

        ## final_meas
        self.final_meas = init_meas
        if self.not_commute and self.byproduct_check:
            self.final_meas ^= 1
        if self.meas_sign == '-':
            self.final_meas ^= 1
        if self.merged_lqsign == '-':
            self.final_meas ^= 1

        # next_byproduct
        self.next_byproduct = []
        for i in range(self.config.num_lq):
            bp = self.byproduct[i]
            if bp == 'X':
                bp = '01'
            elif bp == 'Y':
                bp = '11'
            elif bp == 'Z':
                bp = '10'
            elif bp == 'I':
                bp = '00'
            else:
                sys.exit()

            bpreg = self.byproduct_reg[i]
            if bpreg == 'X':
                bpreg = '01'
            elif bpreg == 'Y':
                bpreg = '11'
            elif bpreg == 'Z':
                bpreg = '10'
            elif bpreg == 'I':
                bpreg = '00'
            else:
                sys.exit()

            nextbp = format(int(bp, 2) ^ int(bpreg, 2), "b").zfill(2)
            if nextbp == '01':
                nextbp = 'X'
            elif nextbp == '11':
                nextbp = 'Y'
            elif nextbp == '10':
                nextbp = 'Z'
            elif nextbp == '00':
                nextbp = 'I'
            else:
                sys.exit()
            self.next_byproduct.append(nextbp)
        # output_xorz
        if self.abcd_reg[0]['valid'] and not self.a_taken:
            a = self.abcd_reg[0]['val']
            if (a == 1 and self.a_sign == '+') \
            or (a == 0 and self.a_sign == '-'):
                self.output_xorz = 'x'
            elif (a == 1 and self.a_sign == '-') \
            or (a == 0 and self.a_sign == '+'):
                self.output_xorz = 'z'
            else:
                sys.exit()
            
        else:
            self.output_xorz = None
        return


    def transfer_selective_meas(self):
        if self.config.block_type == "Distillation":
            self.initial_meas = []
            for i in range(2):
                debug_sel_meas_array = np.full((self.config.num_pchrow, self.config.num_pchcol,
                                                  self.config.num_ucrow, self.config.num_uccol,
                                                  int(self.config.num_qb_per_uc)), '-', dtype='U1')
                if self.sel_meas[i]['valid']:
                    pchrow, pchcol = divmod(self.pchinfo['data']['pchidx'], self.config.num_pchcol)
                    dqmeas_array_pch = copy.deepcopy(self.dqmeas_array_ing[pchrow][pchcol]) 
                    aqmeas_array_pch = copy.deepcopy(self.aqmeas_array_ing[pchrow][pchcol])
                    pf_array_pch = copy.deepcopy(self.pf_array_ing[pchrow][pchcol])
                    ##
                    meas_product = 0
                    pf_product = 0
                    for (ucrow, uccol, qbidx), _ in np.ndenumerate(pf_array_pch):
                        #
                        dqmeas = dqmeas_array_pch[ucrow][uccol][qbidx]
                        aqmeas = aqmeas_array_pch[ucrow][uccol][qbidx]
                        pf = pf_array_pch[ucrow][uccol][qbidx]
                        #
                        uc_west = (uccol == 0)
                        uc_north = (ucrow == 0)
                        uc_east = (uccol == (self.config.num_uccol-1))
                        uc_south = (ucrow == (self.config.num_ucrow-1))                
                        # 
                        sel_loc = self.sel_meas[i]['sel_loc']
                        sel_dqaq = self.sel_meas[i]['sel_dqaq']
                        sel_xz = self.sel_meas[i]['sel_xz']
                        reverse = self.sel_meas[i]['reverse']
                        #
                        if sel_dqaq == 'dq': 
                            if (sel_loc == 'e'): # zt & LQM_X/Y
                                if (uc_east and uc_north):
                                    if qbidx == 3:
                                        meas_product ^= dqmeas
                                        pf_product ^= int(pf=='z' or pf=='y')

                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                                elif (uc_east):
                                    if qbidx in [1,3]:
                                        meas_product ^= dqmeas
                                        pf_product ^= int(pf=='z' or pf=='y')
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                            elif (sel_loc == 'ne'): # zb & LQM_X
                                if (uc_east and uc_north):
                                    if qbidx == 1:
                                        meas_product ^= dqmeas
                                        pf_product ^= int(pf=='z' or pf=='y')
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                            elif (sel_loc == 's'): 
                                # mb & LQM_X, x & LQM_X - sel_xz: x
                                # m & LQM_Z - sel_xz: z
                                if (uc_west and uc_south):
                                    if qbidx == 3:
                                        meas_product ^= dqmeas
                                        if sel_xz == 'x':
                                            pf_product ^= int(pf=='z' or pf=='y')
                                        else:
                                            pf_product ^= int(pf=='x' or pf=='y')
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                                elif (uc_south):
                                    if qbidx in [2,3]:
                                        meas_product ^= dqmeas
                                        if sel_xz == 'x':
                                            pf_product ^= int(pf=='z' or pf=='y')
                                        else:
                                            pf_product ^= int(pf=='x' or pf=='y')
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                            elif (sel_loc == 'w'): 
                                # mt & LQM_Z, mb & LQM_Z, x & LQM_Z - sel_xz: z
                                # m & LQM_X - sel_xz: x
                                if (uc_west and uc_north):
                                    if qbidx == 3:
                                        meas_product ^= dqmeas
                                        if sel_xz == 'x':
                                            pf_product ^= int(pf=='z' or pf=='y')
                                        else:
                                            pf_product ^= int(pf=='x' or pf=='y')
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                                elif (uc_west):
                                    if qbidx in [1,3]:
                                        meas_product ^= dqmeas
                                        if sel_xz == 'x':
                                            pf_product ^= int(pf=='z' or pf=='y')
                                        else:
                                            pf_product ^= int(pf=='x' or pf=='y')
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                            elif (sel_loc == 'ex-e'): # zb & LQM_Y/Z
                                # dqmeas
                                if (uc_east):
                                    if qbidx in [1,3]:
                                        meas_product ^= dqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                                    else:
                                        pass
                                else:
                                    pass
                                # pf
                                if (uc_east and uc_north):
                                    if qbidx == 1:
                                        if sel_xz == 'x': # LQM_Y
                                            pf_product ^= int(pf=='x' or pf=='z')
                                        else: # 'z' - LQM_Z
                                            pf_product ^= int(pf=='x' or pf=='y')
                                    elif qbidx == 3:
                                        pf_product ^= int(pf=='x' or pf=='y')
                                    else:
                                        pass
                                elif (uc_east):
                                    if qbidx in [1,3]:
                                        pf_product ^= int(pf=='x' or pf=='y')
                                    else:
                                        pass
                                else:
                                    pass
                            elif (sel_loc == 'w-s'):
                                if (uc_west and uc_north):
                                    if qbidx == 3:
                                        meas_product ^= dqmeas
                                        pf_product ^= int(pf=='x' or pf=='y')
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                                elif (uc_west):
                                    if qbidx in [1,3]:
                                        meas_product ^= dqmeas
                                        pf_product ^= int(pf=='x' or pf=='y')
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                                elif (uc_south):
                                    if qbidx in [2,3]:
                                        meas_product ^= dqmeas
                                        pf_product ^= int(pf=='x' or pf=='y')
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx] = dqmeas
                            elif (sel_loc == 'i'): 
                                # zt & LQM_Z
                                # mt & LQM_X
                                pass
                            else:
                                pass
                        elif sel_dqaq == 'aq':
                            if sel_loc == 'e':
                                if sel_xz == 'x' and not reverse: # zt
                                    # aqmeas_product
                                    if uc_east and qbidx == 1:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    else:
                                        pass
                                    # pf_product
                                    if (uc_east and uc_north) and qbidx == 3:
                                        pf_product ^= int(pf == 'z' or pf == 'y')
                                    elif uc_east and qbidx in [1, 3]:
                                        pf_product ^= int(pf == 'z' or pf == 'y')
                                    else:
                                        pass
                                else: # mb [1]
                                    pass
                            elif sel_loc == 'ex-e':
                                if sel_xz == 'z' and not reverse: # zb
                                    # aqmeas_product
                                    if uc_east and qbidx == 2:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    else:
                                        pass
                                    # pf_product
                                    if (uc_east and uc_north) and qbidx == 1:
                                        pf_product ^= int(pf=='z' or pf=='x')
                                    elif (uc_east and uc_north) and qbidx == 3:
                                        pf_product ^= int(pf=='x' or pf=='y')
                                    elif uc_east and qbidx in [1, 3]:
                                        pf_product ^= int(pf=='x' or pf=='y')
                                    else:
                                        pass
                                else:
                                    pass
                            elif sel_loc == 'w':
                                if sel_xz == 'z' and reverse: # mt
                                    # aqmeas_product
                                    if uc_west and qbidx == 0:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    else:
                                        pass
                                    # pf_product
                                    if (uc_west and uc_north) and qbidx == 3:
                                        pf_product ^= int(pf == 'x' or pf == 'y')
                                    elif uc_west and qbidx in [1, 3]:
                                        pf_product ^= int(pf == 'x' or pf == 'y')
                                    else:
                                        pass
                                elif sel_xz == 'z' and not reverse: # x, mb
                                    # aqmeas_product
                                    if uc_west and qbidx == 3:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    else:
                                        pass
                                    # pf_product
                                    if (uc_west and uc_north) and qbidx == 3:
                                        pf_product ^= int(pf == 'x' or pf == 'y')
                                    elif uc_west and qbidx in [1, 3]:
                                        pf_product ^= int(pf == 'x' or pf == 'y')
                                    else:
                                        pass
                                else: 
                                    pass
                            elif sel_loc == 'w_inv':
                                if sel_xz == 'z' and reverse: # mt
                                    # aqmeas_product
                                    if uc_west and qbidx == 1:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    elif (not uc_west) and qbidx in [0,1]:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    else:
                                        pass
                                    # pf_product
                                    if (uc_west and uc_north) and qbidx == 3:
                                        pf_product ^= int(pf == 'x' or pf == 'y')
                                    elif uc_west and qbidx in [1, 3]:
                                        pf_product ^= int(pf == 'x' or pf == 'y')
                                    else:
                                        pass
                                elif sel_xz == 'z' and not reverse: # mb
                                    # aqmeas_product
                                    if uc_west and qbidx == 2:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    elif (not uc_west) and qbidx in [2,3]:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    else:
                                        pass
                                    # pf_product
                                    if (uc_west and uc_north) and qbidx == 3:
                                        pf_product ^= int(pf == 'x' or pf == 'y')
                                    elif uc_west and qbidx in [1, 3]:
                                        pf_product ^= int(pf == 'x' or pf == 'y')
                                    else:
                                        pass
                            elif sel_loc == 's_inv':
                                if sel_xz == 'z' and not reverse: # m, pp north
                                    # aqmeas_product
                                    if uc_south and qbidx == 2:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    elif (not uc_south) and qbidx in [2,3]:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    else:
                                        pass
                                    # pf_product
                                    if (uc_west and uc_south) and qbidx == 3:
                                        pf_product ^= int(pf=='x' or pf=='y')
                                    elif uc_south and qbidx in [2, 3]:
                                        pf_product ^= int(pf=='x' or pf=='y')
                                    else:
                                        pass
                                else:
                                    pass
                            elif sel_loc == 's':
                                if sel_xz == 'z' and not reverse: # m, pp south
                                    # aqmeas_product
                                    if uc_south and qbidx == 3:
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    else:
                                        pass
                                    # pf_product
                                    if (uc_west and uc_south) and qbidx == 3:
                                        pf_product ^= int(pf=='x' or pf=='y')
                                    elif uc_south and qbidx in [2, 3]:
                                        pf_product ^= int(pf=='x' or pf=='y')
                                    else:
                                        pass
                                else:
                                    pass
                            elif sel_loc == 'all': # ancilla
                                if sel_xz == 'z' and not reverse:
                                    # aqmeas_product
                                    if qbidx in [2, 3]: 
                                        meas_product ^= aqmeas
                                        debug_sel_meas_array[pchrow][pchcol][ucrow][uccol][qbidx+4] = aqmeas
                                    else:
                                        pass
                                    # pf_product
                                else:
                                    pass
                            else:
                                pass
                        else:
                            pass
                else:
                    meas_product = 0
                    pf_product = 0
                self.initial_meas.append(pf_product ^ meas_product)
        else:
            raise Exception("logical_measure_unit - transfer_selective_meas: block_type {} is currently not supported".format(self.config.block_type))
        return 


    def transfer_control(self):
        if self.pchinfo_valid:
            pchop = self.pchinfo['data']['pchop']
            if pchop[0] in [self.config.LQM_X_opcode, self.config.LQM_Y_opcode, self.config.LQM_Z_opcode] \
            or pchop[1] in [self.config.LQM_X_opcode, self.config.LQM_Y_opcode, self.config.LQM_Z_opcode]:
                self.all_input_ready = self.dqmeas_ready and self.pf_ready
                self.is_measpp = False
            elif pchop[0] == self.config.PPM_INTERPRET_opcode \
              or pchop[1] == self.config.PPM_INTERPRET_opcode:
                self.all_input_ready = self.aqmeas_ready and self.pf_ready and self.dqmeas_ready
                self.is_measpp = True
            else:
                self.all_input_ready = False
                self.is_measpp = False
        else:
            self.all_input_ready = False
            self.is_measpp = False
        # next_state
        if self.state == "ready":
            if self.all_input_ready: 
                self.next_state = "producting"
            else:
                self.next_state = "ready"
        elif self.state == "producting":
            if self.pchinfo_rdlast:
                self.next_state = "interpreting"
            else:
                self.next_state = "producting"
        elif self.state == "interpreting":
            if self.instinfo_rdlast:
                self.next_state = "bpupdating" 
            else:
                self.next_state = "interpreting"
        elif self.state == "bpupdating":
            self.next_state = "ready"
        else:
            sys.exit()

        # new_array_ing
        if self.state == "ready" and self.next_state == "producting":
            self.new_array_ing = True
        else:
            self.new_array_ing = False

        # sel_meas
        if self.config.block_type == "Distillation":
            self.sel_meas = []
            for i in range(2):
                if self.pchinfo_valid:
                    pchop = self.pchinfo['data']['pchop'][i]
                    pchtype = self.pchinfo['data']['pchtype']
                    (facebd_w, facebd_n, facebd_e, facebd_s) = self.pchinfo['data']['facebd']
                    
                    ### sel_loc
                    if pchop == self.config.PPM_INTERPRET_opcode:
                        if pchtype == 'zt':
                            sel_loc = 'e'
                        elif pchtype == 'zb':
                            sel_loc = 'ex-e'
                        elif pchtype == 'mt':
                            if i == 0:
                                sel_loc = 'w'
                            else:
                                sel_loc = 'w_inv' # inverse of w: all except w
                        elif pchtype == 'mb':
                            if i == 0:
                                sel_loc = 'w'
                            else:
                                sel_loc = 'w_inv' # inverse of w: all except w
                        elif pchtype == 'm':
                            if facebd_n == 'pp':
                                sel_loc = 's_inv' # inverse of s: all except s
                            else:
                                sel_loc = 's'
                        elif pchtype == 'x':
                            sel_loc = 'w'
                        elif 'a' in pchtype:
                            sel_loc = 'all'
                        else:
                            sel_loc = 'all'
                    elif pchop in [self.config.LQM_X_opcode]:
                        if pchtype == 'zt':
                            sel_loc = 'e'
                        elif pchtype == 'zb':
                            sel_loc = 'ne'
                        elif pchtype == 'mt':
                            sel_loc = 'i'
                        elif pchtype == 'mb':
                            sel_loc = 's'
                        elif pchtype == 'm':
                            sel_loc = 'w'
                        elif pchtype == 'x':
                            sel_loc = 's'
                        else:
                            sel_loc = 'i'
                    elif pchop in [self.config.LQM_Y_opcode]: 
                        if pchtype == 'zt':
                            sel_loc = 'e'
                        elif pchtype == 'zb':
                            sel_loc = 'ex-e'
                        elif pchtype == 'mt':
                            sel_loc = 'w'
                        elif pchtype == 'mb':
                            sel_loc = 'w-s'
                        elif pchtype == 'm':
                            sel_loc = 'w-s'
                        elif pchtype == 'x':
                            sel_loc = 'w-s'
                        else:
                            sel_loc = 'i'
                    elif pchop in [self.config.LQM_Z_opcode]:
                        if pchtype == 'zt':
                            sel_loc = 'i'
                        elif pchtype == 'zb':
                            sel_loc = 'ex-e'
                        elif pchtype == 'mt':
                            sel_loc = 'w'
                        elif pchtype == 'mb':
                            sel_loc = 'w'
                        elif pchtype == 'm':
                            sel_loc = 's'
                        elif pchtype == 'x':
                            sel_loc = 'w'
                        else:
                            sel_loc = 'i'
                    else:
                        sel_loc = 'all'
                    ### sel_dqaq
                    if pchop == self.config.PPM_INTERPRET_opcode:
                        sel_dqaq = 'aq'
                    else:
                        sel_dqaq = 'dq'
                    ### sel_xz
                    if pchop == self.config.PPM_INTERPRET_opcode:
                        if pchtype == 'zt':
                            sel_xz = 'x'
                        else:
                            sel_xz = 'z'
                    elif pchop == self.config.LQM_X_opcode:
                        if pchtype == 'x' or pchtype == 'mb' or pchtype == 'm':
                            sel_xz = 'x'
                        else:
                            sel_xz = 'z'
                    elif pchop == self.config.LQM_Y_opcode: 
                        if pchtype == 'zb':
                            sel_xz = 'x'
                        else:
                            sel_xz = 'z'
                    elif pchop == self.config.LQM_Z_opcode: 
                        sel_xz = 'z'
                    else:
                        sel_xz = 'z'
                    ### reverse
                    if pchtype == 'mt':
                        reverse = True
                    else:
                        reverse = False
                    ### valid
                    if pchop in [self.config.LQM_X_opcode, self.config.LQM_Y_opcode, self.config.LQM_Z_opcode, self.config.PPM_INTERPRET_opcode]:
                        valid = True
                    else:
                        valid = False
                else:
                    sel_loc = 'all'
                    sel_dqaq = 'dq'
                    sel_xz = 'z'
                    reverse = False
                    valid = False

                self.sel_meas.append({'sel_loc':sel_loc, 'sel_dqaq':sel_dqaq, 'sel_xz':sel_xz, 'reverse':reverse, 'valid':valid})
        else:
            raise Exception("logical_measure_unit - transfer_control: block_type {} is currently not supported".format(self.config.block_type))

        # initmeas_wren 
        self.initmeas_wren = []
        for i in range(2):
            if self.state == 'producting' and self.sel_meas[i]['valid']:
                wren = True
            else:
                wren = False
            self.initmeas_wren.append(wren)
        # initmeas_rst
        if self.state == 'interpreting' and self.next_state != 'interpreting':
            self.initmeas_rst = True
        else:
            self.initmeas_rst = False
        # pchinfo_pop
        if self.state == 'producting':
            self.pchinfo_pop = True
        else:
            self.pchinfo_pop = False
        # flip_initmeas_wr
        if (self.state == 'producting' and self.next_state != 'producting'): 
            self.flip_initmeas_wr = True
        else:
            self.flip_initmeas_wr = False
        # flip_initmeas_rd
        if (self.state == 'interpreting' and self.next_state != 'interpreting'):
            self.flip_initmeas_rd = True
        else:
            self.flip_initmeas_rd = False
        # instinfo_pop/finmeas_wren 
        if self.state == 'interpreting':
            self.instinfo_pop = True
            self.finmeas_wren = True
        else:
            self.instinfo_pop = False
            self.finmeas_wren = False
        # byproduct_wren/abcd_rst
        valid = True
        for i in range(len(self.abcd_reg)):
            valid = valid and self.abcd_reg[i]['valid']
            val = self.abcd_reg[i]['val']
            if i == 0:
                a = val
            elif i == 1:
                b = val
            elif i == 2:
                c = val
            elif i == 3:
                d = val
            else:
                sys.exit()
        bpgen_condition = (a == 0 and bool(c^d)) or (a == 1 and bool(b^c^d))
        if self.state == "bpupdating":
            self.byproduct_wren = (valid and bpgen_condition)
        else:
            self.byproduct_wren = False
        self.abcd_rst = valid
        # byproduct_regwren/abcd_wren/abcd_addr
        if self.state == 'interpreting':
            measflags = self.instinfo['data']['measflags']
            if measflags[0] == '0':
                self.meas_sign = '+'
            else:
                self.meas_sign = '-'
            self.byproduct_regwren = bool(int(measflags[1]))
            self.byproduct_check =  bool(int(measflags[2]))
            self.abcd_wren = bool(int(measflags[3]))
            self.abcd_addr = int(measflags[4:6], 2)
        else:
            self.meas_sign = '+'
            self.byproduct_regwren = False
            self.byproduct_check = False
            self.abcd_wren = False
            self.abcd_addr = 0

        # lqsign_temp_wren
        self.lqsign_temp_wren = (self.state == "producting")
        
        # lqsign_acc_wren/lqsign_temp_rst
        self.lqsign_acc_wren = self.lqsign_temp_rst = (self.state == "bpupdating")

        return


    def transfer_instinfo_srmem(self):
        # connect input
        self.instinfo_srmem.input_valid = (not self.input_lqmeasbuf_empty)
        if self.input_lqmeasbuf_empty is False:
            self.instinfo_srmem.input_data = {"measflags":self.input_to_lqmeas[0], "lpplist":self.input_to_lqmeas[1], "mregdst":self.input_to_lqmeas[2]}
            self.instinfo_srmem.input_last_data = self.input_to_lqmeas[3]
        else:
            self.instinfo_srmem.input_data = None
            self.instinfo_srmem.input_last_data = False
        self.instinfo_srmem.input_pop = self.instinfo_pop
        self.instinfo_srmem.input_new_data = True
        # transfer
        self.instinfo_srmem.transfer()
        # connect output
        self.instinfo = self.instinfo_srmem.output_data[0]
        self.instinfo_full = self.instinfo_srmem.output_wrfull
        self.instinfo_valid = self.instinfo_srmem.output_rdvalid
        self.instinfo_nextready = self.instinfo_srmem.output_nextready 
        self.instinfo_rdlast = self.instinfo_srmem.output_rdlastinfo
        return


    def transfer_pchinfo_srmem(self):
        # connect input
        self.pchinfo_srmem.input_valid = self.input_tolmu_valid and (not self.input_pchwr_stall)
        self.pchinfo_srmem.input_data = self.input_pchinfo
        self.pchinfo_srmem.input_last_data = self.input_last_pchinfo
        self.pchinfo_srmem.input_pop = self.pchinfo_pop
        self.pchinfo_srmem.input_new_data = True
        # transfer
        self.pchinfo_srmem.transfer()
        # connect output
        self.pchinfo = self.pchinfo_srmem.output_data[0]
        self.pchinfo_full = self.pchinfo_srmem.output_wrfull
        self.pchinfo_valid = self.pchinfo_srmem.output_rdvalid
        self.pchinfo_nextready = self.pchinfo_srmem.output_nextready 
        self.pchinfo_rdlast = self.pchinfo_srmem.output_rdlastinfo
        return

    def transfer_finmeas(self):
        self.output_finmeas_reg_val = np.full(self.config.num_lq, 0, dtype=int) 
        self.output_finmeas_reg_valid = np.full(self.config.num_lq, False, dtype=bool)

        for i in range(self.config.num_lq):
            self.output_finmeas_reg_val[i] = self.finmeas_reg[i]['val']
            self.output_finmeas_reg_valid[i] = self.finmeas_reg[i]['valid']

        return

    def update(self, sim_cycle=0):
        self.update_stats(sim_cycle)
        

        self.instinfo_srmem.update()
        self.pchinfo_srmem.update()
        self.measop_buf.update()
        self.update_measreg()
        self.update_registers()
        self.state = self.next_state
        return


    def update_measreg(self):
        # finmeas_reg
        if self.finmeas_wren:
            self.finmeas_reg[self.mregdst]['val'] = self.final_meas
            self.finmeas_reg[self.mregdst]['valid'] = True
        if self.input_lqmeasbuf_empty is False and not self.instinfo_full:
            self.finmeas_reg[self.input_to_lqmeas[2]]['valid'] = False
        
        # abcd_reg
        if self.abcd_wren:
            self.abcd_reg[self.abcd_addr]['val'] = self.final_meas
            self.abcd_reg[self.abcd_addr]['valid'] = True
            if self.abcd_addr == 0:
                self.a_sign = self.meas_sign
        elif self.abcd_rst:
            for i in range(len(self.abcd_reg)):
                self.abcd_reg[i]['valid'] = False

        # initmeas_reg
        for i in range(2):
            if self.initmeas_wren[i]:
                mregdst = self.pchinfo['data']['pchmreg'][i]
                self.initmeas_reg[self.sel_initmeas_wr][mregdst] ^= self.initial_meas[i]
        if self.initmeas_rst:
            for i in range(self.config.num_lq):
                self.initmeas_reg[self.sel_initmeas_rd][i] = 0
        return


    def update_registers(self):
        # a_taken
        if self.input_a_taken:
            self.a_taken = True
        if self.abcd_rst:
            self.a_taken = False

        # byproduct
        if self.byproduct_wren:
            self.byproduct = self.next_byproduct

        # byproduct_reg 
        if self.byproduct_regwren:
            self.byproduct_reg = self.lpplist

        # sel_initmeas_wr/rd
        if self.flip_initmeas_wr:
            self.sel_initmeas_wr ^= 1
        if self.flip_initmeas_rd:
            self.sel_initmeas_rd ^= 1

        # array_ing
        if self.new_array_ing: 
            self.aqmeas_array_ing = copy.deepcopy(self.aqmeas_array_reg)
            self.dqmeas_array_ing = copy.deepcopy(self.dqmeas_array_reg)
            self.pf_array_ing = copy.deepcopy(self.pf_array_reg)
            self.aqmeas_ready = False
            self.dqmeas_ready = False
            self.pf_ready = False

        # input registers
        if self.input_aqmeas_valid:
            self.aqmeas_ready = True
            self.aqmeas_array_reg = copy.deepcopy(self.input_aqmeas_array)
        else:
            pass
        if self.input_dqmeas_valid and \
           self.measop in [self.config.LQM_X_opcode, self.config.LQM_Y_opcode, self.config.LQM_Z_opcode, self.config.MEAS_INTMD_opcode]:
            self.dqmeas_ready = True
            self.dqmeas_array_reg = copy.deepcopy(self.input_dqmeas_array)
        else:
            pass
        if self.input_pf_valid:
            self.pf_ready = True
            self.pf_array_reg = copy.deepcopy(self.input_pf_array)
        else:
            pass

        # prev_opcode
        if self.input_opcode_valid: 
            self.prev_opcode = self.input_opcode
        
        # lqsign_acc_reg
        if self.lqsign_acc_wren:
            if self.config.block_type == "Distillation":
                for i in range(self.config.num_lq):
                    temp_valid = self.lqsign_temp_reg[i]['valid']
                    if temp_valid:
                        acc_lqsignZ = self.lqsign_acc_reg[i]['signZ']
                        temp_lqsignZ = self.lqsign_temp_reg[i]['signZ']
                        acc_lqsignX = self.lqsign_acc_reg[i]['signX']
                        temp_lqsignX = self.lqsign_temp_reg[i]['signX']
                        self.lqsign_acc_reg[i]['signZ'] = acc_lqsignZ ^ temp_lqsignZ
                        self.lqsign_acc_reg[i]['signX'] = acc_lqsignX ^ temp_lqsignX
                    else:
                        pass
            else:
                raise Exception("logical_measure_unit - update_register: block_type {} is currently not supported".format(self.config.block_type))
        # lqsign_temp_reg
        if self.lqsign_temp_wren:
            if self.config.block_type == "Distillation":
                # set valid
                if self.lqsign_valid:
                    self.lqsign_temp_reg[self.lqsign_valid_idx]['valid'] = True
                
                for i in range(self.config.num_lq):
                    curr_lqsignZ = self.lqsign_temp_reg[i]['signZ']
                    temp_lqsignZ = self.lqsignZ_temp_list[i]
                    self.lqsign_temp_reg[i]['signZ'] = curr_lqsignZ ^ temp_lqsignZ
                    curr_lqsignX = self.lqsign_temp_reg[i]['signX']
                    temp_lqsignX = self.lqsignX_temp_list[i]
                    self.lqsign_temp_reg[i]['signX'] = curr_lqsignX ^ temp_lqsignX
            else:
                raise Exception("logical_measure_unit - update_register: block_type {} is currently not supported".format(self.config.block_type))

        elif self.lqsign_temp_rst:
            self.lqsign_temp_reg = []
            for i in range(self.config.num_lq):
                self.lqsign_temp_reg.append({'signX':0, 'signZ':0, 'valid':False})
    
        return
    
    def debug(self):
        # Add variables to check in the debugging mode
        if self.state == "producting":
            pchrow, pchcol = divmod(self.pchinfo['data']['pchidx'], self.config.num_pchcol)
            if self.is_measpp:
                print("lmu.aqmeas_patch_ing: ")
                debug_patch(self.config, self.aqmeas_array_ing[pchrow][pchcol], 'aq')
            print("lmu.pf_patch_ing: ")
            debug_patch(self.config, self.pf_array_ing[pchrow][pchcol])
            print("lmu.dqmeas_patch_ing: ")
            debug_patch(self.config, self.dqmeas_array_ing[pchrow][pchcol])
        return
    
    def save_internal_value(self):
        save_cond = all([meas_reg['valid'] for meas_reg in self.abcd_reg])
        save_cond = save_cond or self.first_save_flag

        if self.first_save_flag:
            self.first_save_flag = False
        
        if save_cond:
            # Get byproduct and lqsign

            if self.byproduct_wren:
                self.byproduct_list.append(
                    copy.deepcopy(self.next_byproduct)
                )
            else:
                self.byproduct_list.append(
                    copy.deepcopy(self.byproduct)
                )

            self.lqsign_acc_x.append(
                ['+' if s['signX'] == 0 else '-' for s in self.lqsign_acc_reg]
            )
            self.lqsign_acc_z.append(
                ['+' if s['signZ'] == 0 else '-' for s in self.lqsign_acc_reg]
            )
        return
