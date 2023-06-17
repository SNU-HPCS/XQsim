import sys

class patch_decode_unit:
    def __init__(self, unit_stat, config):
        # 
        self.config = config
        # 
        self.unit_stat = unit_stat
        self.init_stats()
        # Wires
        ## Input wires
        self.input_from_qid = None
        self.input_pchdecbuf_empty = None
        self.input_stall = None
        ## Intermediate wires
        ### from priority encoder
        self.lqidx = None
        self.next_lqlist = None
        ### from patch decoder
        self.pch_list_curr = None
        self.pchpp_list_curr = None
        self.pchop_list_curr = None
        self.pchmreg_list_curr = None
        ### from control logic
        self.last_lq = None
        self.even_lq = None
        self.take_input = None
        self.update_lqlist = None
        self.flush_output = None
        self.next_state = None

        # Registrers
        ## Input registers
        self.opcode_reg = "1" * self.config.opcode_bw
        self.lqlist_reg = [0] * self.config.num_lq
        self.lpplist_reg = ["I"] * self.config.num_lq
        self.oplist_reg = ["1"*self.config.opcode_bw] * self.config.num_lq
        self.mreglist_reg = [0] * self.config.num_lq
        ## Output registers
        self.output_valid = False
        self.output_opcode = "1" * self.config.opcode_bw
        self.output_pch_list = [0] * self.config.num_pch
        self.output_pchpp_list = [["I"] * self.config.num_pch] * 2
        self.output_pchop_list = [["1"*self.config.opcode_bw] * self.config.num_pch] * 2
        self.output_pchmreg_list = [[0] * self.config.num_pch] * 2
        ## State registers
        self.state = "empty"

        # Random access memory
        self.pch_maptable = [(None, None)] * self.config.num_lq
        self.init_pch_maptable()
    
    def init_pch_maptable(self):
        if self.config.block_type == "Distillation":
            assert self.config.num_lq % 2 == 1 or self.config.num_lq == 2
            for lqidx in range(0, self.config.num_lq):
                if lqidx == 0: # two-patch Z ancilla
                    self.pch_maptable[lqidx] = (0, self.config.num_pchcol)
                elif lqidx == 1: # two-patch M ancilla
                    self.pch_maptable[lqidx] = (1, self.config.num_pchcol+1)
                else:
                    if lqidx == self.config.num_lq-1:
                        pchidx = int(2*self.config.num_pchcol-1)
                    else:
                        if lqidx % 2 == 0:
                            pchidx = int((lqidx/2) + 1)
                        else:
                            pchidx = int(self.config.num_pchcol * (self.config.num_pchrow-1) + (lqidx+1)/2)
                    self.pch_maptable[lqidx] = (pchidx, pchidx)
        else:
            raise Exception("patch_decode_unit - init_pch_maptable: block_type {} is currently not supported".format(self.config.block_type))
        return
    
    def transfer(self):
        self.transfer_lqidx()
        self.transfer_pchdec()
        self.transfer_control()
        return 
    
    def transfer_lqidx(self):
        self.lqidx = 0
        for i in range(self.config.num_lq):
            if self.lqlist_reg[i] == 1:
                self.lqidx = i
                break
        self.next_lqlist = self.lqlist_reg[:]
        self.next_lqlist[self.lqidx] = 0
        return 

    def transfer_pchdec(self):
        pchidx_1, pchidx_2 = self.pch_maptable[self.lqidx]
        mreg = self.mreglist_reg[self.lqidx]
        opcode = self.oplist_reg[self.lqidx]
        lpp = self.lpplist_reg[self.lqidx]
        
        self.pch_list_curr = [0] * self.config.num_pch
        self.pchmreg_list_curr = [0] * self.config.num_pch
        self.pchop_list_curr = ["1"*self.config.opcode_bw] * self.config.num_pch
        self.pchpp_list_curr = ["I"] * self.config.num_pch

        for i in range(self.config.num_pch):
            if i == pchidx_1 or i == pchidx_2:
                self.pch_list_curr[i] = 1
                self.pchmreg_list_curr[i] = mreg
                self.pchop_list_curr[i] = opcode
                self.pchpp_list_curr[i] = lpp
        return


    
    def transfer_control(self):
        # control output logic
        ## last_lq
        if self.state == "running" or self.state == "output_running":
            if self.next_lqlist == ([0] * self.config.num_lq):
                self.last_lq = True
            else:
                self.last_lq = False
        else:
            self.last_lq = False
        ## even_lq
        if self.lqidx % 2 == 0:
            self.even_lq = True
        else:
            self.even_lq = False
        ## take_input
        if self.state == "empty" or self.state == "output_empty":
            if not self.input_pchdecbuf_empty:
                self.take_input = True
            else:
                self.take_input = False
        elif self.last_lq:
            if not self.input_pchdecbuf_empty:
                self.take_input = True
            else:
                self.take_input = False
        else:
            self.take_input = False
        ## update_lqlist
        if self.state == "running" or self.state == "output_running":
            if not self.last_lq:
                self.update_lqlist = True
            else:
                self.update_lqlist = False
        else:
            self.update_lqlist = False
        ## flush_output
        if self.state == "output_running" or self.state == "output_empty":
            self.flush_output = True
        else:
            self.flush_output = False

        # next state logic
        if self.state == "empty" or self.state == "output_empty":
            if not self.input_pchdecbuf_empty:
                self.next_state = "running"
            else:
                self.next_state = "empty"
        elif self.state == "running" or self.state == "output_running":
            if self.last_lq: 
                if not self.input_pchdecbuf_empty:
                    self.next_state = "output_running"
                else:
                    self.next_state = "output_empty"
            else:
                self.next_state = "running"
        else:
            print("invalid PDU state: ", self.state)
            sys.exit()
        return


    def update(self, sim_cycle=0):
        self.update_stats(sim_cycle)

        if self.input_stall:
            return

        # output regs
        if self.last_lq: 
            self.output_valid = True
        else:
            self.output_valid = False
        self.output_opcode = self.opcode_reg
        if self.flush_output:
            self.output_pch_list = self.pch_list_curr[:]
            if self.even_lq:
                self.output_pchpp_list[0] = self.pchpp_list_curr[:]
                self.output_pchop_list[0] = self.pchop_list_curr[:]
                self.output_pchmreg_list[0] = self.pchmreg_list_curr[:]
                self.output_pchpp_list[1] = ["I"] * self.config.num_pch
                self.output_pchop_list[1] = ["1"*self.config.opcode_bw] * self.config.num_pch
                self.output_pchmreg_list[1] = [0] * self.config.num_pch
            else:
                self.output_pchpp_list[1] = self.pchpp_list_curr[:]
                self.output_pchop_list[1] = self.pchop_list_curr[:]
                self.output_pchmreg_list[1] = self.pchmreg_list_curr[:]
                self.output_pchpp_list[0] = ["I"] * self.config.num_pch
                self.output_pchop_list[0] = ["1"*self.config.opcode_bw] * self.config.num_pch
                self.output_pchmreg_list[0] = [0] * self.config.num_pch
        else:
            for i in range(self.config.num_pch):
                if self.pch_list_curr[i] == 1:
                    self.output_pch_list[i] = self.pch_list_curr[i]
                    if self.even_lq:
                        self.output_pchpp_list[0][i] = self.pchpp_list_curr[i]
                        self.output_pchop_list[0][i] = self.pchop_list_curr[i]
                        self.output_pchmreg_list[0][i] = self.pchmreg_list_curr[i]
                    else:
                        self.output_pchpp_list[1][i] = self.pchpp_list_curr[i]
                        self.output_pchop_list[1][i] = self.pchop_list_curr[i]
                        self.output_pchmreg_list[1][i] = self.pchmreg_list_curr[i]

        # input regs
        if self.take_input:
            (opcode, lqlist, lpplist, oplist, mreglist) = self.input_from_qid
            self.opcode_reg = opcode
            self.lqlist_reg = lqlist
            self.lpplist_reg = lpplist
            self.oplist_reg = oplist
            self.mreglist_reg = mreglist
        elif self.update_lqlist:
            self.lqlist_reg = self.next_lqlist

        # state 
        self.state = self.next_state

        return

    def debug(self):
        # Add variables to check in the debugging mode
        print("pdu.state: {}".format(self.state))
        return

    # 
    def init_stats(self):
        # Data transfer
        ### to PIU
        self.unit_stat.data_transfer["PIU"] = {
                "num_eff": [],
                "num_max": [],
                "cycle": [],
                "bw": self.config.pdu2piu_bw,
                "last_cyc": 0
                }
        #
        self.unit_stat.num_acc_cyc = 0
        self.unit_stat.num_update_cyc = 0
        return

    #
    def update_stats (self, sim_cycle):
        self.unit_stat.num_update_cyc += 1
        # num_acc_cyc
        if self.state in ["running", "output_running"] and not self.input_stall: 
            self.unit_stat.num_acc_cyc += 1
        else: 
            pass
        # data_transfer
        if self.output_valid and not self.input_stall: 
            cycle = sim_cycle - self.unit_stat.data_transfer["PIU"]["last_cyc"]
            self.unit_stat.data_transfer["PIU"]["num_eff"].append(1)
            self.unit_stat.data_transfer["PIU"]["num_max"].append(1)
            self.unit_stat.data_transfer["PIU"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["PIU"]["last_cyc"] = sim_cycle
        else:
            pass

        return
