import numpy as np
import math
import sys
import buffer as buffer
import copy 

class quantum_instruction_decoder:
    def __init__(self, unit_stat, config):
        # 
        self.config = config
        #
        self.unit_stat = unit_stat
        self.init_stats()
        # Wires
        ## Input wire
        self.input_inst = None # from qif
        self.input_instbuf_empty = None # from qif
        self.input_qifdone = None # from qif
        self.input_pchdecbuf_ready = None # from later stages 
        self.input_lqmeasbuf_ready = None # from later stages 
        self.input_xorz = None  # from lmu 
        ## Output wire
        self.output_to_pchdec = None
        self.output_to_lqmeas = None
        self.output_pchdecbuf_empty = None
        self.output_lqmeasbuf_empty = None
        self.output_instdec_stall = None # to qif's input_instbuf_ready
        self.output_a_taken = None
        ## Intermediate wire
        ### from decoder to locator and regs
        self.opcode = None 
        self.measflags = None 
        self.mregdst = None 
        self.lqdix_offset = None
        self.lpplist = None
        ### from locator to accs
        self.opcode_loc = None
        self.mregdst_loc = None
        self.lpplist_loc = None
        self.lqlist_loc = None
        ### delimiter's output
        self.to_pchdec_valid = None # same as last acc flag
        self.to_lqmeas_valid = None
        ### data to buffers
        self.to_pchdec_data = None
        self.to_lqmeas_data = None
        ## Done wire
        self.done = None


        # Registers
        ## Intermediate registers
        self.opcode_reg = "1"*self.config.opcode_bw
        self.measflags_reg = "0"*self.config.meas_flag_bw 
        self.mregdst_reg = 0
        ###
        self.opcode_acc = ["1"*self.config.opcode_bw] * self.config.num_lq
        self.mregdst_acc = [0] * self.config.num_lq
        self.lpplist_acc_pdu = ["I"] * self.config.num_lq
        self.lpplist_acc_lmu = ["I"] * self.config.num_lq
        self.lqlist_acc = [0] * self.config.num_lq

        # Buffers
        self.to_pchdec_buf = buffer.buffer("to_pchdec_buf", self.config.to_pdubuf_sz)
        self.to_lqmeas_buf = buffer.buffer("to_lqmeas_buf", self.config.to_lmubuf_sz)
        # Done register
        self.all_decoded = False

    def init_stats(self):
        # Data tranfser
        ### to PDU
        self.unit_stat.data_transfer["PDU"] = {
                "num_eff": [], 
                "num_max": [], 
                "cycle": [],
                "bw": self.config.qid2pdu_bw,
                "last_cyc": 0
                }
        ### to LMU
        self.unit_stat.data_transfer["LMU"] = {
                "num_eff": [], 
                "num_max": [], 
                "cycle": [],
                "bw": self.config.qid2lmu_bw, 
                "last_cyc": 0
                }
        #
        self.unit_stat.num_acc_cyc = 0
        self.unit_stat.num_update_cyc = 0


    def update_stats(self, sim_cycle):
        self.unit_stat.num_update_cyc += 1
        # num_acc_cyc
        if self.output_instdec_stall:
            pass
        else: 
            self.unit_stat.num_acc_cyc += 1

        # data_transfer
        if self.input_pchdecbuf_ready and not self.to_pchdec_buf.empty:
            cycle = sim_cycle - self.unit_stat.data_transfer["PDU"]["last_cyc"]
            self.unit_stat.data_transfer["PDU"]["num_eff"].append(1)
            self.unit_stat.data_transfer["PDU"]["num_max"].append(1)
            self.unit_stat.data_transfer["PDU"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["PDU"]["last_cyc"] = sim_cycle
        if self.input_lqmeasbuf_ready and not self.to_lqmeas_buf.empty:
            cycle = sim_cycle - self.unit_stat.data_transfer["LMU"]["last_cyc"]
            self.unit_stat.data_transfer["LMU"]["num_eff"].append(1)
            self.unit_stat.data_transfer["LMU"]["num_max"].append(1)
            self.unit_stat.data_transfer["LMU"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["LMU"]["last_cyc"] = sim_cycle
        else:
            pass

    def transfer(self):
        self.transfer_decoder()
        self.transfer_locator()
        self.transfer_delimiter()
        self.transfer_buffer()
        if self.all_decoded and \
           self.to_pchdec_buf.empty and \
           self.to_lqmeas_buf.empty:
            self.done = True
        else:
            self.done = False
        return 

    def transfer_decoder(self):
        if self.input_instbuf_empty is False:
            inst_bstr = ""
            for byte in self.input_inst:
                bstr = format(int.from_bytes(byte, byteorder="big"), "08b")
                inst_bstr += bstr
            offset = 0
            self.opcode = inst_bstr[offset:self.config.opcode_bw]
       
            offset += self.config.opcode_bw
            self.measflags = inst_bstr[offset:(offset + self.config.meas_flag_bw)]
            
            offset += self.config.meas_flag_bw
            self.mregdst = int(inst_bstr[offset:(offset + self.config.mreg_dst_bw)], 2)

            offset += self.config.mreg_dst_bw
            self.lqidx_offset = int(inst_bstr[offset:(offset + self.config.lq_addr_offset_bw)], 2)

            offset += self.config.lq_addr_offset_bw
            self.lpplist = inst_bstr[offset:(offset + self.config.target_bw)]

            # LQM_FB handling
            if self.opcode == self.config.LQM_FB_opcode:
                if self.input_xorz == 'x':
                    self.opcode = self.config.LQM_X_opcode
                    self.output_a_taken = True
                elif self.input_xorz == 'z':
                    self.opcode = self.config.LQM_Z_opcode
                    self.output_a_taken = True
                else: # should wait for the valid input_xorz
                    self.output_a_taken = False
            else:
                self.output_a_taken = False
        else:
            self.opcode = None
            self.measflags = None
            self.mregdst = None
            self.lqidx_offset = None
            self.lpplist = None
            self.output_a_taken = False
        return


    def transfer_locator(self):
        if self.input_instbuf_empty is False:
            self.opcode_loc = ["1"*self.config.opcode_bw] * self.config.num_lq
            self.mregdst_loc = [0] * self.config.num_lq
            self.lpplist_loc = ["I"] * self.config.num_lq
            self.lqlist_loc = [0] * self.config.num_lq

            # lpplist_loc & lqlist_loc
            lpplist = []
            lqlist = []
            for i in range(len(self.lpplist)-1, 0, -2):
                if self.lpplist[i-1:i+1] == "00": 
                    pauli = "I"
                    lqlist.append(0)
                elif self.lpplist[i-1:i+1] == "01":
                    pauli = "X"
                    lqlist.append(1)
                elif self.lpplist[i-1:i+1] == "10":
                    pauli = "Z"
                    lqlist.append(1)
                elif self.lpplist[i-1:i+1] == "11":
                    pauli = "Y"
                    lqlist.append(1)
                else:
                    print("Invalid pauli in qid.locator: ", lpplist[i-1:i+1])
                    sys.exit()
                lpplist.append(pauli)
            
            if self.config.num_lq <= int(self.config.target_bw/2):
                self.lpplist_loc = lpplist[0:self.config.num_lq]
                self.lqlist_loc = lqlist[0:self.config.num_lq]
            else:
                start_idx = self.lqidx_offset * int(self.config.target_bw/2)
                self.lpplist_loc[start_idx:start_idx+int(self.config.target_bw/2)] = lpplist[:]
                self.lqlist_loc[start_idx:start_idx+int(self.config.target_bw/2)] = lqlist[:]
            
            # opcode_loc & mregdst_loc
            for i in range(self.config.num_lq):
                if self.lqlist_loc[i] == 1:
                    self.opcode_loc[i] = self.opcode
                    self.mregdst_loc[i] = self.mregdst
        else:
            self.opcode_loc = None
            self.mregdst_loc = None
            self.lpplist_loc = None
            self.lqlist_loc = None
        return 


    def transfer_delimiter(self):
        # last_acc (to_pchdec_valid)
        if self.opcode is not None and self.opcode_reg is not None:
            if self.opcode_reg == self.config.LQI_opcode and self.opcode == self.config.LQI_opcode:
                self.to_pchdec_valid = False
            elif self.opcode_reg == self.config.MERGE_INFO_opcode and self.opcode == self.config.MERGE_INFO_opcode:
                self.to_pchdec_valid = False
            elif self.opcode_reg == self.config.PPM_INTERPRET_opcode and self.opcode == self.config.PPM_INTERPRET_opcode:
                self.to_pchdec_valid = False
            elif (self.opcode_reg == self.config.LQM_X_opcode or self.opcode_reg == self.config.LQM_Z_opcode or self.opcode_reg == self.config.LQM_Y_opcode)\
             and (self.opcode == self.config.LQM_X_opcode or self.opcode == self.config.LQM_Z_opcode or self.opcode == self.config.LQM_Y_opcode):
                self.to_pchdec_valid = False
            elif self.opcode_reg == "1"*self.config.opcode_bw:
                # initialized invalid opcode_reg
                self.to_pchdec_valid = False
            else:
                self.to_pchdec_valid = True

        elif self.opcode is None and self.opcode_reg is not None:
            if self.input_qifdone and not self.all_decoded:
                self.to_pchdec_valid = True
            else:
                self.to_pchdec_valid = False
        else:
            self.to_pchdec_valid = False


        # to_lqmeas_valid
        ## single qubit measurement
        if self.opcode_reg == self.config.LQM_X_opcode \
        or self.opcode_reg == self.config.LQM_Z_opcode \
        or self.opcode_reg == self.config.LQM_Y_opcode:
            if not self.all_decoded:
                self.to_lqmeas_valid = True
            else:
                self.to_lqmeas_valid = False

        ## pauli-product measurement
        elif self.opcode_reg == self.config.PPM_INTERPRET_opcode:
            if self.mregdst is not None and self.mregdst_reg is not None:
                if self.opcode == self.config.PPM_INTERPRET_opcode:
                    if self.mregdst != self.mregdst_reg:
                        self.to_lqmeas_valid = True
                    else:
                        self.to_lqmeas_valid = False
                else:
                    self.to_lqmeas_valid = True
            elif self.mregdst is None and self.mregdst_reg is not None:
                if self.input_qifdone and not self.all_decoded:
                    self.to_lqmeas_valid = True
                else:
                    self.to_lqmeas_valid = False
            else:
                self.to_lqmeas_valid = False
        else:
            self.to_lqmeas_valid = False
        return

    def transfer_buffer(self):
        # stall signal
        self.output_instdec_stall = (self.to_pchdec_buf.full or self.to_lqmeas_buf.full) or \
                (self.opcode == self.config.LQM_FB_opcode)

        # input data
        if not self.output_instdec_stall:
            if self.to_pchdec_valid: 
                self.to_pchdec_data = (self.opcode_reg, self.lqlist_acc, self.lpplist_acc_pdu, self.opcode_acc, self.mregdst_acc)
            else:
                self.to_pchdec_data = None

            if self.to_lqmeas_valid:
                last_flag = self.to_pchdec_valid
                self.to_lqmeas_data = (self.measflags_reg, self.lpplist_acc_lmu, self.mregdst_reg, last_flag)
            else:
                self.to_lqmeas_data = None
        else:
            self.to_pchdec_data = None
            self.to_lqmeas_data = None

        # connection 
        self.to_pchdec_buf.input_data = self.to_pchdec_data
        self.to_pchdec_buf.input_ready = self.input_pchdecbuf_ready
        self.to_lqmeas_buf.input_data = self.to_lqmeas_data 
        self.to_lqmeas_buf.input_ready = self.input_lqmeasbuf_ready
        self.to_pchdec_buf.transfer()
        self.to_lqmeas_buf.transfer()
        self.output_to_pchdec = self.to_pchdec_buf.head
        self.output_to_lqmeas = self.to_lqmeas_buf.head
        self.output_pchdecbuf_empty = self.to_pchdec_buf.empty
        self.output_lqmeasbuf_empty = self.to_lqmeas_buf.empty


    def update(self, sim_cycle=0):
        self.update_stats(sim_cycle)

        # buffer update
        self.to_pchdec_buf.update()
        self.to_lqmeas_buf.update()

        if self.output_instdec_stall:
            return

        if self.input_instbuf_empty is False:
            # accs
            if self.to_pchdec_valid:
                 #print("to_pchdec_valid True: ", self.opcode_loc)
                self.opcode_acc = copy.deepcopy(self.opcode_loc)
                self.mregdst_acc = copy.deepcopy(self.mregdst_loc)
                self.lpplist_acc_pdu = copy.deepcopy(self.lpplist_loc)
                self.lqlist_acc = copy.deepcopy(self.lqlist_loc)
            else:
                #print("to_pchdec_valid False: ", self.opcode_loc)
                for i in range(self.config.num_lq):
                    if self.lqlist_loc[i] == 1:
                        self.opcode_acc[i] = self.opcode_loc[i]
                        self.mregdst_acc[i] = self.mregdst_loc[i]
                        self.lpplist_acc_pdu[i] = self.lpplist_loc[i]
                        self.lqlist_acc[i] = self.lqlist_loc[i]

            if self.to_lqmeas_valid or self.to_pchdec_valid:
                self.lpplist_acc_lmu = copy.deepcopy(self.lpplist_loc)
            else:
                 for i in range(self.config.num_lq):
                    if self.lqlist_loc[i] == 1:
                        self.lpplist_acc_lmu[i] = self.lpplist_loc[i]

            # regs
            self.opcode_reg = self.opcode 
            self.measflags_reg = self.measflags
            self.mregdst_reg = self.mregdst

        elif self.input_qifdone:
            self.all_decoded = True

    def debug(self):
        # Add variables to check in the debugging mode
        print("qid.to_pchdec_valid: {}".format(self.to_pchdec_valid))
        print("qid.to_lqmeas_valid: {}".format(self.to_lqmeas_valid))
        print("qid.to_pchdec_data: {}".format(self.to_pchdec_data))
        print("qid.to_lqmeas_data: {}".format(self.to_lqmeas_data))
        print()
        return

