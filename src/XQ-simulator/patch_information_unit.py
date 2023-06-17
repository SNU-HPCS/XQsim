import sys
import copy

class patch_information_unit:
    def __init__(self, unit_stat, config):
        #
        self.config = config
        #
        self.unit_stat = unit_stat
        self.init_stats()
        # Wires
        ## Input wires
        self.input_pdu_valid = None
        self.input_opcode = None
        self.input_pch_list = None
        self.input_pchpp_list = None
        self.input_pchop_list = None
        self.input_pchmreg_list = None
        self.input_stall = None
        ## Intermediate wires
        ### from control logic
        self.last_pch = None
        self.take_input = None
        self.update_pchidx_src = None
        self.sel_pchidx_src = None
        self.next_state = None
        self.is_wrting = None
        self.prep_dyninfo = None
        self.split_dyninfo = None
        self.set_merged = None
        self.copy_merged = None
        self.topsu_valid = None
        self.tolmu_valid = None
        self.last_pachinfo = None
        ### from pchidx generator
        self.pchidx = None
        self.next_pchidx_src = None
        ### from pchdyn decoder
        self.wr_facebd = None
        self.wr_cornerbd = None
        ## Output wires
        self.output_pchinfo = None
        self.output_opcode = None
        self.output_topsu_valid = None
        self.output_tolmu_valid = None
        self.output_last_pchinfo = None

        # Registers
        ## Input registers
        self.opcode_reg = "1" * self.config.opcode_bw
        self.pch_list_reg = [0] * self.config.num_pch
        self.pchpp_list_reg = [["I"] * self.config.num_pch] * 2
        self.pchop_list_reg = [["1"*self.config.opcode_bw] * self.config.num_pch] * 2
        self.pchmreg_list_reg = [[0] * self.config.num_pch] * 2
        ## Internal registers
        self.esmon_reg = [0] * self.config.num_pch
        self.merged_reg = [0] * self.config.num_pch
        self.merged_mem = [0] * self.config.num_pch
        ## State registers
        self.state = "ready"
        ## Pipelining registers
        self.pchidx_reg = 0
        self.topsu_valid_reg = False
        self.tolmu_valid_reg = False
        self.last_pchinfo_reg = False 
        self.is_writing_reg = False
        self.opcode_reg_reg = "1" * self.config.opcode_bw
        self.pchpp_list_reg_reg = [["I"] * self.config.num_pch] * 2
        self.pchop_list_reg_reg = [["1"*self.config.opcode_bw] * self.config.num_pch] * 2
        self.pchmreg_list_reg_reg = [[0] * self.config.num_pch] * 2

        # Random access memory
        self.pchinfo_static_ram = [dict()] * self.config.num_pch
        self.init_pchinfo_static()
        self.facebd_ram = [['i', 'i', 'i', 'i']] * self.config.num_pch
        self.cornerbd_ram = [['i', 'i', 'i', 'i']] * self.config.num_pch

    def init_pchinfo_static(self):
        if self.config.block_type == "Distillation":
            assert self.config.num_lq % 2 == 1 or self.config.num_lq == 2
            for pchidx in range(self.config.num_pch):
                pchrow, pchcol = divmod(pchidx, self.config.num_pchcol)
                ret_dict = dict()
                if pchrow == 0 and pchcol == 0:
                    #zt
                    ret_dict['pchtype'] = 'zt'
                    ret_dict['z_bd'] = 'i'
                    ret_dict['x_bd'] = 'e'
                elif pchrow == 1 and pchcol == 0:
                    #zb
                    ret_dict['pchtype'] = 'zb'
                    ret_dict['z_bd'] = 'e'
                    ret_dict['x_bd'] = 'i'
                elif pchrow == 0 and pchcol == 1:
                    #mt
                    ret_dict['pchtype'] = 'mt'
                    ret_dict['z_bd'] = 'w'
                    ret_dict['x_bd'] = 'i'
                elif pchrow == 1 and pchcol == 1:
                    #mb
                    ret_dict['pchtype'] = 'mb'
                    ret_dict['z_bd'] = 'we'
                    ret_dict['x_bd'] = 'i'
                elif pchrow == 0 and pchcol != self.config.num_pchcol-1:
                    #m
                    ret_dict['pchtype'] = 'm'
                    ret_dict['z_bd'] = 's'
                    ret_dict['x_bd'] = 'i'
                elif pchrow == self.config.num_pchrow-1 and pchcol not in [0, 1, self.config.num_pchcol-1]:
                    #m
                    ret_dict['pchtype'] = 'm'
                    ret_dict['z_bd'] = 'n'
                    ret_dict['x_bd'] = 'i'
                elif pchrow == 1 and pchcol == self.config.num_pchcol-1:
                    #x
                    ret_dict['pchtype'] = 'x'
                    ret_dict['z_bd'] = 'w'
                    ret_dict['x_bd'] = 'i'
                elif pchrow == 1 and (pchcol == 2 and pchcol == self.config.num_pchcol-2):
                    #awe
                    ret_dict['pchtype'] = 'awe'
                    ret_dict['z_bd'] = 'i'
                    ret_dict['x_bd'] = 'i'
                elif pchrow == 1 and pchcol == 2:
                    #aw
                    ret_dict['pchtype'] = 'aw'
                    ret_dict['z_bd'] = 'i'
                    ret_dict['x_bd'] = 'i'
                elif pchrow == 1 and pchcol == self.config.num_pchcol-2:
                    #ae
                    ret_dict['pchtype'] = 'ae'
                    ret_dict['z_bd'] = 'i'
                    ret_dict['x_bd'] = 'i'
                elif pchrow == 1:
                    #ac
                    ret_dict['pchtype'] = 'ac'
                    ret_dict['z_bd'] = 'i'
                    ret_dict['x_bd'] = 'i'
                else:
                    #i
                    ret_dict['pchtype'] = 'i'
                    ret_dict['z_bd'] = 'i'
                    ret_dict['x_bd'] = 'i'

                self.pchinfo_static_ram[pchidx] = ret_dict
        else:
            raise Exception("patch_information_unit - init_pchinfo_static: block_type {} is currently not supported".format(self.config.block_type))
        return


    def transfer(self):
        self.transfer_control() # for sel_pchidx_src
        self.transfer_pchidx()
        self.transfer_pchinfo()
        self.transfer_dyndec()
        self.transfer_control() # for others
        self.output_opcode = self.opcode_reg_reg
        self.output_topsu_valid = self.topsu_valid_reg
        self.output_tolmu_valid = self.tolmu_valid_reg
        self.output_last_pchinfo = self.last_pchinfo_reg
        return

    def transfer_control(self):
        # last_pch
        if self.state == "reading" or self.state == "writing":
            if self.next_pchidx_src == ([0] * self.config.num_pch):
                self.last_pch = True
            else:
                self.last_pch = False
        else:
            self.last_pch = False

        # take_input
        if self.state == "ready" or self.state == "resetting":
            if self.input_pdu_valid:
                self.take_input = True
            else:
                self.take_input = False
        elif self.state == "reading" or self.state == "writing":
            if self.input_pdu_valid and self.last_pch:
                self.take_input = True
            else:
                self.take_input = False
        else:
            print("invalid PIU state: ", self.state)
            sys.exit()
        
        # update_pchidx_src
        if self.state == "reading" or self.state == "writing":
            if not self.last_pch:
                self.update_pchidx_src = True
            else:
                self.update_pchidx_src = False
        else:
            self.update_pchidx_src = False

        # sel_pchidx_src
        ## 0: pch_list_reg
        ## 1: esm_on
        ## 2: merged
        ## 3: invalid
        # topsu_valid/tolmu_valid
        if self.state == "reading":
            if self.opcode_reg == self.config.LQI_opcode:
                self.sel_pchidx_src = 0
                if self.config.block_type == "Distillation":
                    if self.pchidx == 1: # masking 'mt'
                        self.topsu_valid = False
                    else:
                        self.topsu_valid = True
                else:
                    raise Exception("patch_information_unit - transfer_control: block_type {} is currently not supported".format(self.config.block_type))
                self.tolmu_valid = False
            elif self.opcode_reg == self.config.LQM_X_opcode:
                self.sel_pchidx_src = 0
                self.topsu_valid = True
                self.tolmu_valid = True
            elif self.opcode_reg == self.config.LQM_Z_opcode:
                self.sel_pchidx_src = 0
                self.topsu_valid = True
                self.tolmu_valid = True
            elif self.opcode_reg == self.config.LQM_Y_opcode:
                self.sel_pchidx_src = 0
                self.topsu_valid = True
                self.tolmu_valid = True
            elif self.opcode_reg == self.config.RUN_ESM_opcode:
                self.sel_pchidx_src = 1
                self.topsu_valid = True
                self.tolmu_valid = False
            elif self.opcode_reg == self.config.INIT_INTMD_opcode:
                self.sel_pchidx_src = 2
                self.topsu_valid = True
                self.tolmu_valid = False
            elif self.opcode_reg == self.config.MEAS_INTMD_opcode:
                self.sel_pchidx_src = 2
                self.topsu_valid = True
                self.tolmu_valid = False
            elif self.opcode_reg == self.config.PPM_INTERPRET_opcode:
                self.sel_pchidx_src = 2
                self.topsu_valid = False
                self.tolmu_valid = True
            else:
                self.sel_pchidx_src = 3
                self.topsu_valid = False
                self.tolmu_valid = False

        elif self.state == "writing":
            if self.opcode_reg == self.config.MERGE_INFO_opcode:
                self.sel_pchidx_src = 2
                self.topsu_valid = False
                self.tolmu_valid = False
            else:
                self.sel_pchidx_src = 3
                self.topsu_valid = False
                self.tolmu_valid = False
        else:
            self.sel_pchidx_src = 3
            self.topsu_valid = False
            self.tolmu_valid = False

        # next_state
        if self.state == "ready" or self.state == "resetting":
            if self.input_pdu_valid: # input_opcode valid
                if self.input_opcode == self.config.MERGE_INFO_opcode:
                    self.next_state = "writing"
                elif self.input_opcode == self.config.PREP_INFO_opcode:
                    self.next_state = "resetting"
                elif self.input_opcode == self.config.SPLIT_INFO_opcode:
                    self.next_state = "resetting"
                else:
                    self.next_state = "reading"
            else:
                self.next_state = "ready"
        elif self.state == "reading":
            if self.last_pch:
                if self.input_pdu_valid: # input_opcode valid
                    if self.input_opcode == self.config.MERGE_INFO_opcode:
                        self.next_state = "writing"
                    elif self.input_opcode == self.config.PREP_INFO_opcode:
                        self.next_state = "resetting"
                    elif self.input_opcode == self.config.SPLIT_INFO_opcode:
                        self.next_state = "resetting"
                    else:
                        self.next_state = "reading"
                else:
                    self.next_state = "ready"
            else:
                self.next_state = "reading"
        elif self.state == "writing":
            if self.last_pch:
                if self.input_pdu_valid: # input_opcode valid
                    if self.input_opcode == self.config.MERGE_INFO_opcode:
                        self.next_state = "writing"
                    elif self.input_opcode == self.config.PREP_INFO_opcode:
                        self.next_state = "resetting"
                    elif self.input_opcode == self.config.SPLIT_INFO_opcode:
                        self.next_state = "resetting"
                    else:
                        self.next_state = "reading"
                else:
                    self.next_state = "ready"
            else:
                self.next_state = "writing"
        else:
            print("invalid PIU state: ", self.state)
            sys.exit()
       
        # is_writing
        if self.state == "writing":
            self.is_writing = True
        else:
            self.is_writing = False
        # prep_dyninfo 
        if self.state == "resetting" and self.opcode_reg == self.config.PREP_INFO_opcode:
            self.prep_dyninfo = True
        else:
            self.prep_dyninfo = False
        # split_dyninfo
        if self.state == "resetting" and self.opcode_reg == self.config.SPLIT_INFO_opcode:
            self.split_dyninfo = True
        else:
            self.split_dyninfo = False
        # set_merged
        if self.take_input and self.input_opcode == self.config.MERGE_INFO_opcode:
            self.set_merged = True
        else:
            self.set_merged = False
        # copy_merged
        if self.take_input and  (self.input_opcode == self.config.INIT_INTMD_opcode or self.input_opcode == self.config.MEAS_INTMD_opcode or self.input_opcode == self.config.PPM_INTERPRET_opcode):
            self.copy_merged = True
        else:
            self.copy_merged = False
        # last_pchinfo
        if self.state == 'reading' and self.last_pch: 
            self.last_pchinfo = True
        else:
            self.last_pchinfo = False

        return 


    def transfer_pchidx(self):
        # pchidx
        if self.sel_pchidx_src == 0:
            pchidx_src = self.pch_list_reg
        elif self.sel_pchidx_src == 1:
            pchidx_src = self.esmon_reg
        elif self.sel_pchidx_src == 2:
            pchidx_src = self.merged_reg
        else:
            pchidx_src = [0] * self.config.num_pch # invalid
    
        self.pchidx = 0
        for i in range(self.config.num_pch):
            if pchidx_src[i] == 1:
                self.pchidx = i
                break
        # next_pchidx_src 
        self.next_pchidx_src = pchidx_src[:]
        self.next_pchidx_src[self.pchidx] = 0
        return


    def transfer_pchinfo(self):
        rd_pchstat = self.pchinfo_static_ram[self.pchidx_reg]
        rd_facebd = self.facebd_ram[self.pchidx_reg]
        rd_cornerbd = self.cornerbd_ram[self.pchidx_reg]
        pchop = [self.pchop_list_reg_reg[0][self.pchidx_reg], self.pchop_list_reg_reg[1][self.pchidx_reg]]
        pchmreg = [self.pchmreg_list_reg_reg[0][self.pchidx_reg], self.pchmreg_list_reg_reg[1][self.pchidx_reg]]
        pchpp = [self.pchpp_list_reg_reg[0][self.pchidx_reg], self.pchpp_list_reg_reg[1][self.pchidx_reg]]
        if (rd_pchstat['pchtype'] == 'mt' or rd_pchstat['pchtype'] == 'mb') and self.opcode_reg == self.config.PPM_INTERPRET_opcode:
            pchop = [self.config.PPM_INTERPRET_opcode, self.config.PPM_INTERPRET_opcode]
            pchpp = ['Y', 'Z']

        if 'a' in rd_pchstat['pchtype'] and self.opcode_reg == self.config.PPM_INTERPRET_opcode:
            for mreg in (self.pchmreg_list_reg[0]+self.pchmreg_list_reg[1]):
                if mreg != 0:
                    pchop = [self.config.PPM_INTERPRET_opcode, '1'*self.config.opcode_bw]
                    pchmreg = [mreg, 0]
                    break

        self.output_pchinfo = copy.deepcopy(rd_pchstat)
        self.output_pchinfo["facebd"] = rd_facebd
        self.output_pchinfo["cornerbd"] = rd_cornerbd
        self.output_pchinfo["pchidx"] = self.pchidx_reg
        self.output_pchinfo["pchop"] = pchop 
        self.output_pchinfo["pchmreg"] = pchmreg
        self.output_pchinfo["pchpp"] = pchpp

        return


    def transfer_dyndec(self): # pchdyn_decoder
        if self.config.block_type == "Distillation":
            # input pchstat
            rd_pchstat = self.pchinfo_static_ram[self.pchidx_reg]
            pchtype = rd_pchstat["pchtype"]
            z_bd = rd_pchstat["z_bd"]
            
            # merge pchpp_list_reg into pchpp_list
            pchpp_list = []
            for i in range(self.config.num_pch):
                pchpp_even = self.pchpp_list_reg[0][i]
                pchpp_odd = self.pchpp_list_reg[1][i]
                if pchpp_even == 'I':
                    pchpp = pchpp_odd
                elif pchpp_odd == 'I':
                    pchpp = pchpp_even 
                else:
                    print("invalid pchpp in PIU.dyndec: ", pchpp_even, pchpp_odd)
                    sys.exit()
                pchpp_list.append(pchpp)
            
            # get north_pp/east_pp/south_pp
            pchrow, pchcol = divmod(self.pchidx_reg, self.config.num_pchcol)
            if pchrow != 0:
                north_idx = self.pchidx_reg - self.config.num_pchcol
                north_pp = pchpp_list[north_idx]
            else:
                north_pp = 'I'
            if pchcol != self.config.num_pchcol-1:  
                east_idx = self.pchidx_reg + 1
                east_pp = pchpp_list[east_idx]
            else:
                east_pp = 'I'
            if pchrow != self.config.num_pchrow-1:
                south_idx = self.pchidx_reg + self.config.num_pchcol
                south_pp = pchpp_list[south_idx]
            else:
                south_pp = 'I'

            # generate wr_facebd   
            if pchtype == 'zt':
                self.wr_facebd = ['x', 'x', 'mp', 'pp']
                self.wr_cornerbd = ['c', 'i', 'i', 'i']
            elif pchtype == 'zb':
                self.wr_facebd = ['z', 'pp', 'pp', 'z']
                self.wr_cornerbd = ['i', 'y', 'c', 'i']
            elif pchtype == 'mt':
                self.wr_facebd = ['mp', 'z', 'z', 'lp']
                self.wr_cornerbd = ['i', 'i', 'i', 'z']
            elif pchtype == 'mb':
                self.wr_facebd = ['pp', 'lp', 'pp', 'z'] 
                self.wr_cornerbd = ['ye', 'i', 'i', 'i']
            elif pchtype == 'm':
                if z_bd == 's':
                    self.wr_facebd = ['z', 'x', 'z', 'pp']
                    self.wr_cornerbd = ['i', 'i', 'i', 'i']
                elif z_bd == 'n':
                    self.wr_facebd = ['z', 'pp', 'z', 'x']
                    self.wr_cornerbd = ['z', 'i', 'i', 'i']
                else:
                    print("invalid z_bd in m-pch")
                    sys.exit()
            elif pchtype == 'x':
                self.wr_facebd = ['pp', 'z', 'x', 'z']
                self.wr_cornerbd = ['i', 'i', 'i', 'i']

            elif 'a' in pchtype:
                # west
                facebd_w = 'pp'
                # north
                if north_pp == 'Z':
                    facebd_n = 'pp'
                    if 'w' in pchtype:
                        cornerbd_nw = 'ze'
                    else:
                        cornerbd_nw = 'z'
                else:
                    facebd_n = 'z'
                    if 'w' in pchtype:
                        cornerbd_nw = 'ie'
                    else:
                        cornerbd_nw = 'i'
                # east
                if 'e' in pchtype:
                    if east_pp == 'Z':
                        facebd_e = 'pp'
                    else:
                        facebd_e = 'z'
                else:
                    facebd_e = 'pp'
                # south
                if south_pp == 'Z':
                    facebd_s = 'pp'
                else:
                    facebd_s = 'z'

                cornerbd_ne = 'i'
                cornerbd_sw = 'i'
                cornerbd_se = 'i'

                self.wr_facebd = [facebd_w, facebd_n, facebd_e, facebd_s]
                self.wr_cornerbd = [cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se]
            else:
                self.wr_facebd = ['i', 'i', 'i', 'i']
                self.wr_cornerbd = ['i', 'i', 'i', 'i']
        else:
            raise Exception("patch_information_unit - transfer_dyndec: block_type {} is currently not supported".format(self.config.block_type))
        return 


    def update(self, sim_cycle=0):
        self.update_stats(sim_cycle)

        if self.input_stall:
            return 

        # pchinfo_dynamic
        ## facebd_ram
        self.update_pchdyn()
        ## esmon_reg
        self.update_esmon()
        ## merged_mem/merged_reg
        self.update_merged()

        # pipeline
        self.pchidx_reg = self.pchidx
        self.topsu_valid_reg = self.topsu_valid
        self.tolmu_valid_reg = self.tolmu_valid
        self.last_pchinfo_reg = self.last_pchinfo
        self.is_writing_reg = self.is_writing
        self.opcode_reg_reg = self.opcode_reg
        self.pchpp_list_reg_reg = self.pchpp_list_reg[:]
        self.pchop_list_reg_reg = self.pchop_list_reg[:]
        self.pchmreg_list_reg_reg = self.pchmreg_list_reg[:]

        # pch_list_reg
        if self.take_input:
            self.pch_list_reg = self.input_pch_list[:]
        elif self.update_pchidx_src and self.sel_pchidx_src == 0:
            self.pch_list_reg = self.next_pchidx_src[:]

        # other input regs
        if self.take_input:
            self.opcode_reg = self.input_opcode
            self.pchpp_list_reg = self.input_pchpp_list[:]
            self.pchop_list_reg = self.input_pchop_list[:]
            self.pchmreg_list_reg = self.input_pchmreg_list[:]

        # state
        self.state = self.next_state

        return

    def update_pchdyn(self):
        if self.config.block_type == "Distillation":
            assert self.config.num_lq % 2 == 1
            # resets
            if self.prep_dyninfo or self.split_dyninfo:
                for pchidx in range(self.config.num_pch):
                    pchrow, pchcol = divmod(pchidx, self.config.num_pchcol)
                    if pchrow == 0 and pchcol == 0:
                        #zt
                        facebd = ['x', 'x', 'z', 'pp']
                        cornerbd = ['c', 'i', 'i', 'i']
                    elif pchrow == 1 and pchcol == 0:
                        #zb
                        facebd = ['z', 'pp', 'x', 'z']
                        cornerbd = ['i', 'i', 'c', 'i']
                    elif pchrow == 0 and pchcol == 1:
                        #mt
                        if self.prep_dyninfo:
                            facebd = ['i', 'i', 'i', 'i']
                            cornerbd = ['i', 'i', 'i', 'i']
                        else: # split
                            facebd = ['x', 'z', 'z', 'lp']
                            cornerbd = ['i', 'i', 'i', 'i']
                    elif pchrow == 1 and pchcol == 1:
                        #mb
                        if self.prep_dyninfo:
                            facebd = ['x', 'z', 'x', 'z']
                            cornerbd = ['i', 'i', 'i', 'i']
                        else: #split
                            facebd = ['x', 'lp', 'x', 'z']
                            cornerbd = ['i', 'i', 'i', 'i']
                    elif (pchrow == 0 and pchcol != self.config.num_pchcol-1) or \
                         (pchrow == self.config.num_pchrow-1 and pchcol not in [0, 1, self.config.num_pchcol-1]):
                        #m
                        facebd = ['z', 'x', 'z', 'x']
                        cornerbd = ['i', 'i', 'i', 'i']
                    elif pchrow == 1 and pchcol == self.config.num_pchcol-1:
                        #x
                        facebd = ['x', 'z', 'x', 'z']
                        cornerbd = ['i', 'i', 'i', 'i']
                    else:
                        #awe/aw/ae/ac/i
                        facebd = ['i', 'i', 'i', 'i']
                        cornerbd = ['i', 'i', 'i', 'i']
                    self.facebd_ram[pchidx] = facebd
                    self.cornerbd_ram[pchidx] = cornerbd
            # write for MERGE
            elif self.is_writing_reg:
                self.facebd_ram[self.pchidx_reg] = self.wr_facebd
                self.cornerbd_ram[self.pchidx_reg] = self.wr_cornerbd
            else:
                pass
        else:
            raise Exception("patch_information_unit - update_pchdyn: block_type {} is currently not supported".format(self.config.block_type))
        return


    def update_esmon(self):
        if self.config.block_type == "Distillation":
            assert self.config.num_lq % 2 == 1
            # reset: PREP, SPLIT
            if self.prep_dyninfo or self.split_dyninfo:
                for pchidx in range(self.config.num_pch):
                    pchrow, pchcol = divmod(pchidx, self.config.num_pchcol)
                    if pchrow == 0 and pchcol not in [1, self.config.num_pchcol-1]:
                        esmon = 1
                    elif pchrow == 1 and pchcol in [0, 1, self.config.num_pchcol-1]:
                        esmon = 1
                    elif pchrow == self.config.num_pchrow-1 and pchcol not in [0, 1, self.config.num_pchcol-1]:
                        esmon = 1
                    else:
                        esmon = 0
                    self.esmon_reg[pchidx] = esmon
                if self.split_dyninfo:
                    mt_idx = 1
                    self.esmon_reg[mt_idx] = 1
            # reset: MERGE
            elif self.set_merged:
                for pchidx in range(self.config.num_pch):
                    pchrow, pchcol = divmod(pchidx, self.config.num_pchcol)
                    if pchrow == 0 and pchcol != self.config.num_pchcol-1:
                        esmon = 1
                    elif pchrow == 1:
                        esmon = 1
                    elif pchrow == self.config.num_pchrow-1 and pchcol not in [0, 1, self.config.num_pchcol-1]:
                        esmon = 1
                    else:
                        esmon = 0
                    self.esmon_reg[pchidx] = esmon
            # update one by one
            elif self.update_pchidx_src and self.sel_pchidx_src == 1:
                self.esmon_reg = self.next_pchidx_src[:]
            else:
                pass
        else:
            raise Exception("patch_information_unit - update_esmon: block_type {} is currently not supported".format(self.config.block_type))

        return

    
    def update_merged(self):
        if self.config.block_type == "Distillation":
            assert self.config.num_lq % 2 == 1
            # reset: PREP, SPLIT
            if self.prep_dyninfo or self.split_dyninfo:
                self.merged_reg = [0] * self.config.num_pch
                self.merged_mem = [0] * self.config.num_pch

            # reset: MERGE
            elif self.set_merged:
                for pchidx in range(self.config.num_pch):
                    pchrow, pchcol = divmod(pchidx, self.config.num_pchcol)
                    if pchrow == 1 and pchcol not in [0, 1, self.config.num_pchcol-1]:
                        merged = 1
                    else:
                        merged = self.input_pch_list[pchidx]
                    self.merged_reg[pchidx] = merged
                    self.merged_mem[pchidx] = merged
            # copy from mem to reg
            elif self.copy_merged:
                self.merged_reg = self.merged_mem[:]

            # update reg one by one
            elif self.update_pchidx_src and self.sel_pchidx_src == 2:
                self.merged_reg = self.next_pchidx_src[:]
            else:
                pass
        else:
            raise Exception("patch_information_unit - update_merged: block_type {} is currently not supported".format(self.config.block_type))
        return

    def debug(self):
        # Add variables to check in the debugging mode
        if not self.input_stall:
            if self.output_topsu_valid or self.output_tolmu_valid:
                print("piu.output_opcode: {}".format(self.output_opcode))
                print("piu.output_last_pchinfo: {}".format(self.output_last_pchinfo))
                print("piu.output_topsu_valid: {}".format(self.output_topsu_valid))
                print("piu.output_tolmu_valid: {}".format(self.output_tolmu_valid))
                print("piu.output_pchinfo: {}".format(self.output_pchinfo))
        return

    def init_stats(self):
        # Data transfer 
        ### to PSU
        self.unit_stat.data_transfer["PSU"] = {
                "num_eff": [],
                "num_max": [],
                "cycle": [],
                "bw": self.config.piu2psu_bw,
                "last_cyc": 0
                }
        ### to EDU
        self.unit_stat.data_transfer["EDU"] = {
                "num_eff": [],
                "num_max": [],
                "cycle": [],
                "bw": self.config.piu2edu_bw,
                "last_cyc": 0
                }
        ### to lmu
        self.unit_stat.data_transfer["LMU"] = {
                "num_eff": [],
                "num_max": [],
                "cycle": [],
                "bw": self.config.piu2lmu_bw,
                "last_cyc": 0
                }
        #
        self.unit_stat.num_acc_cyc = 0
        self.unit_stat.num_update_cyc = 0
        return

    def update_stats(self, sim_cycle):
        self.unit_stat.num_update_cyc += 1
        # num_acc_cyc
        if self.input_stall: 
            pass
        else:
            self.unit_stat.num_acc_cyc += 1
        # data_transfer
        if self.input_stall:
            pass
        else:
            if self.output_topsu_valid:
                cycle = sim_cycle - self.unit_stat.data_transfer["PSU"]["last_cyc"]
                self.unit_stat.data_transfer["PSU"]["num_eff"].append(1)
                self.unit_stat.data_transfer["PSU"]["num_max"].append(1)
                self.unit_stat.data_transfer["PSU"]["cycle"].append(cycle)
                self.unit_stat.data_transfer["PSU"]["last_cyc"] = sim_cycle
                #
                cycle = sim_cycle - self.unit_stat.data_transfer["EDU"]["last_cyc"]
                self.unit_stat.data_transfer["EDU"]["num_eff"].append(1)
                self.unit_stat.data_transfer["EDU"]["num_max"].append(1)
                self.unit_stat.data_transfer["EDU"]["cycle"].append(cycle)
                self.unit_stat.data_transfer["EDU"]["last_cyc"] = sim_cycle

            if self.output_tolmu_valid:
                cycle = sim_cycle - self.unit_stat.data_transfer["LMU"]["last_cyc"]
                self.unit_stat.data_transfer["LMU"]["num_eff"].append(1)
                self.unit_stat.data_transfer["LMU"]["num_max"].append(1)
                self.unit_stat.data_transfer["LMU"]["cycle"].append(cycle)
                self.unit_stat.data_transfer["LMU"]["last_cyc"] = sim_cycle
            else:
                pass
        return
