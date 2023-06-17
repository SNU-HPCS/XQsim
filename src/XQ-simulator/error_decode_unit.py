import os, sys
#
curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
par_dir = os.path.join(curr_dir, os.pardir)
#
sys.path.insert(0, par_dir)
from util import *
#
import numpy as np
import copy
import sys
import buffer as buffer

class error_decode_unit:
    def __init__(self, unit_stat, config, mode):
        self.config = config
        #
        self.unit_stat = unit_stat
        self.init_stats()
        # Wires
        ## Input wires
        self.input_pchwr_stall = None
        ### from piu
        self.input_pchinfo_valid = None
        self.input_pchinfo = None
        self.input_last_pchinfo = None
        self.input_piu_opcode = None
        ### from qxu
        self.input_aqmeas_valid = None
        self.input_aqmeas_array = None
        self.input_dqmeas_valid = None 
        self.input_dqmeas_array = None 
        ### from tcu
        self.input_tcu_opcode = None
        self.input_tcu_valid = None
        ## Intermediate wires
        ### from pchinfo_buf
        self.pchinfo_running = None 
        self.pchinfo_empty = None
        ### from token_setup
        self.row_tokens_out = None 
        self.token_set_array = None
        self.flag_set_array = None
        self.last_token = None
        self.next_rowidx = None
        ### from educell_array
        self.global_tokenmatch = None 
        self.global_errormatch = None
        self.global_measmatch = None 
        self.esmhead_exist = None 
        self.next_error_array = None
        self.eigen_array = np.full((self.config.num_dqrow, self.config.num_dqcol), 0)  
        ### from control
        self.token_finish = None
        self.layer_retry = None 
        self.layer_finish = None
        self.next_state = None
        self.wr_pireg = None 
        self.rst_pireg = None
        self.rst_first_token = None 
        self.shift_token = None
        self.wr_zeroesm = None 
        self.esm_finish = None
        self.up_timeout = None
        self.rst_timeout = None
        self.rst_cellstate = None
        self.next_valid = None
        self.set_measerr_flag = None
        self.set_last_measerr_flag = None 
        self.pop_aqmeasbuf = None 
        self.apply_aqmeas_flip = None 
        self.rst_token_pipe = None
        ### from last_aqmeas_flip
        self.last_aqmeas_flip_array = None 

        ## Output wires
        self.output_error_array = None 
        self.output_eigen_array = None 
        self.output_pfflag = None 
        ## Temporal
        self.possible_dir_array = None
        self.role_array = None
        self.syn_to_west_array = None
        self.syn_to_east_array = None
        self.first_aqmeas_flag_array = None
        self.esm_reg_array = None
        self.token_reg_array = None
        self.local_tokenmatch_array = None
        self.cellstate_array = None
        self.spikedir_reg_array = None
        self.syndir_reg_array = None
        self.spike_taken_array = None
        self.syndrome_taken_array = None
        self.local_errormatch_array = None
        self.local_measmatch_array = None
        ##
        
        # Registers
        ## State register
        self.state = "ready"  
        self.set_first_aqmeas = True 
        self.first_token = True 
        ## Constant register
        self.rowidx_regs = [i for i in range(self.config.num_aqrow+self.config.num_aqcol-1)] #
        ## Input register
        self.pchinfo_regs = [] #
        for i in range(self.config.num_pch):
            init_pchinfo = {'pchtype': 'i', 'facebd': ['i', 'i', 'i', 'i']}
            self.pchinfo_regs.append(init_pchinfo) 
        self.pchinfo_taken = False  
        self.opcode_reg = '1'*self.config.opcode_bw 
        ## Internal register
        self.timeout_th = 2
        self.timeout_counter = 0
        self.aqmeas_counter = 0 
        self.round_counter = 0 
        self.curr_rowidx_reg = 0 
        self.last_token_reg = 0 

        # Pipelining
        if "fast" in self.unit_stat.uarch:
            ## wire
            self.esmhead_rows = None 
            self.flag_out_rows = None 
            ### 0
            self.token_exist_rows_0 = None
            self.token_col_rows_0 = None
            ### 1
            self.token_exist_rows_1 = None
            self.token_exist_1 = None
            self.token_row_1 = None
            self.token_col_rows_1 = None
            ### 2
            self.token_set_rows_2 = None
            self.flag_set_rows_2 = None 
            ### out
            self.token_match = None

            ## reg
            ### 0
            self.token_exist_rows_0_reg = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=bool)
            self.token_col_rows_0_reg = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=int)
            self.token_valid_0_reg = False
            ### 1
            self.token_exist_rows_1_reg = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=bool)
            self.token_exist_1_reg = False
            self.token_row_1_reg = 0 
            self.token_col_rows_1_reg = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=bool)
            self.token_valid_1_reg = False
            ### 2
            self.token_match_reg = False

        ## Output register
        self.error_array_reg = np.full((self.config.num_dqrow, self.config.num_dqcol), 'i') 
        self.output_valid = False 
            
        # Microunits
        self.pchinfo_buf = buffer.buffer("edu_pibuf", 2)
        self.educell_array = np.empty((self.config.num_aqrow, self.config.num_aqcol), dtype=object)
        for (i, j), _ in np.ndenumerate(self.educell_array):
            self.educell_array[i][j] = edu_cell(self.config, i, j) 
        # 
        assert (mode in ["cycle", "layer"])
        self.mode = mode
            
    def init_stats(self):
        # Data transfer
        ### to PFU
        self.unit_stat.data_transfer["PFU"] = {
                "num_eff": [],
                "num_max": [],
                "cycle": [],
                "bw": ceil(self.config.num_pq_eff/2)*2,
                "last_cyc": 0
                }
        ### to LMU
        self.unit_stat.data_transfer["LMU"] = {
                "num_eff": [], 
                "num_max": [], 
                "cycle": [],
                "bw": ceil(self.config.num_pq_eff/2),
                "last_cyc": 0
                }
        # EDU cycle result
        self.unit_stat.edu_cycle_result = {
                "num_propagation_list": [],
                "num_token_setup_list": [],
                "num_error_match_list": [],
                "num_layer_retry_list": [],
                "cyc_edu_running_list": [],
                "cyc_token_setup_list": []
        }
        self.num_propagation = 0
        self.num_token_setup = 0
        self.num_error_match = 0
        self.num_layer_retry = 0
        self.cyc_edu_running = 0
        self.cyc_token_setup = 0

        #
        self.unit_stat.num_acc_cyc = 0
        self.unit_stat.num_update_cyc = 0
        return

    def update_stats (self, sim_cycle):
        self.unit_stat.num_update_cyc += 1
        # num_acc_cyc
        if self.state == 'ready' or self.state == 'waiting':
            pass
        else:
            self.unit_stat.num_acc_cyc += 1
        # data_transfer
        if self.output_valid: 
            cycle = sim_cycle - self.unit_stat.data_transfer["PFU"]["last_cyc"]
            self.unit_stat.data_transfer["PFU"]["num_eff"].append(1)
            self.unit_stat.data_transfer["PFU"]["num_max"].append(1)
            self.unit_stat.data_transfer["PFU"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["PFU"]["last_cyc"] = sim_cycle
            #
            cycle = sim_cycle - self.unit_stat.data_transfer["LMU"]["last_cyc"]
            self.unit_stat.data_transfer["LMU"]["num_eff"].append(1)
            self.unit_stat.data_transfer["LMU"]["num_max"].append(1)
            self.unit_stat.data_transfer["LMU"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["LMU"]["last_cyc"] = sim_cycle
        else:
            pass
        # edu_cycle_result
        ## num_propagation
        if self.state == "error_pairing" and not (self.global_errormatch or self.global_measmatch):
            self.num_propagation += 1
        ## num_token_setup
        if self.state == "token_allocate" and self.next_state == "error_pairing":
            self.num_token_setup += 1
        ## num_error_match
        if self.global_errormatch or self.global_measmatch: 
            self.num_error_match += 1
        ## num_layer_retry
        if self.layer_retry:
            self.num_layer_retry += 1
        ## cyc_edu_running
        if self.state != "ready" and self.state != "waiting":
            self.cyc_edu_running += 1
        ## cyc_token_setup
        if self.state == "token_allocate":
            self.cyc_token_setup += 1
        ## record & reset
        if self.layer_finish: 
            self.unit_stat.edu_cycle_result["num_propagation_list"].append(self.num_propagation)
            self.unit_stat.edu_cycle_result["num_token_setup_list"].append(self.num_token_setup)
            self.unit_stat.edu_cycle_result["num_error_match_list"].append(self.num_error_match)
            self.unit_stat.edu_cycle_result["num_layer_retry_list"].append(self.num_layer_retry)
            self.unit_stat.edu_cycle_result["cyc_edu_running_list"].append(self.cyc_edu_running)
            self.unit_stat.edu_cycle_result["cyc_token_setup_list"].append(self.cyc_token_setup)
            #
            self.num_propagation = 0
            self.num_token_setup = 0
            self.num_error_match = 0
            self.num_layer_retry = 0
            self.cyc_edu_running = 0
            self.cyc_token_setup = 0
        return

    def transfer(self):
        self.transfer_last_aqmeas_flip()
        self.transfer_pchinfobuf()
        self.transfer_educell_array()
        self.transfer_token_setup()
        self.transfer_control()
        self.transfer_pchinfobuf()
        self.transfer_educell_array()
        self.transfer_token_setup()
        self.transfer_control()
        self.transfer_output()
        return

    def transfer_last_aqmeas_flip(self):
        self.last_aqmeas_flip_array = np.zeros((self.config.num_aqrow, self.config.num_aqcol), dtype=int)
        if self.input_dqmeas_valid and (self.opcode_reg == self.config.MEAS_INTMD_opcode):
            for (pchrow, pchcol, ucrow, uccol, qbidx), dqmeas in np.ndenumerate(self.input_dqmeas_array):
                i = pchrow*(self.config.code_dist+1) + ucrow*2 + int(qbidx in [2, 3])
                j = pchcol*(self.config.code_dist+1) + uccol*2 + int(qbidx in [1, 3])
                if i != 0 and j != 0:
                    self.last_aqmeas_flip_array[i-1][j-1] ^= dqmeas
                if i != 0:
                    self.last_aqmeas_flip_array[i-1][j] ^= dqmeas
                if j != 0:
                    self.last_aqmeas_flip_array[i][j-1] ^= dqmeas
                self.last_aqmeas_flip_array[i][j] ^= dqmeas
        else:
            pass

        return 


    def transfer_control(self):
        # token_finish
        if self.state == 'token_allocate':
            if self.first_token and (not self.esmhead_exist):
                self.token_finish = True
            elif self.last_token_reg == 1:
                self.token_finish = True
            else:
                self.token_finish = False
        else:
            self.token_finish = False

        # layer_retry
        if self.token_finish and self.esmhead_exist:
            if self.round_counter not in range(self.config.code_dist-(self.config.aqmeas_th-1), self.config.code_dist):
                if self.config.timeout_limit > self.timeout_th: 
                    self.layer_retry = True
                else:
                    self.layer_retry = False
            else:
                if self.config.timeout_limit > self.timeout_th:
                    self.layer_retry = True
                else:
                    self.layer_retry = False
        else:
            self.layer_retry = False

        # layer finish
        if self.token_finish and not self.layer_retry:
            self.layer_finish = True
        else:
            self.layer_finish = False

        # next_state
        ## READY
        if self.state == 'ready':
            if self.aqmeas_counter == self.config.aqmeas_th:
                self.next_state = 'token_allocate'
            else:
                self.next_state = 'ready'
        ## TOKEN_ALLOCATE
        elif self.state == 'token_allocate':
            if self.global_tokenmatch:
                self.next_state = 'error_pairing'
            elif self.layer_finish:
                if self.round_counter < self.config.code_dist-self.config.aqmeas_th:
                    self.next_state = 'waiting'
                elif self.round_counter == self.config.code_dist-1:
                    self.next_state = 'ready'
                else:
                    self.next_state = 'token_allocate'
            elif self.layer_retry:
                self.next_state = 'token_allocate'
            else:
                self.next_state = 'token_allocate'
            
        ## ERROR_PAIRING
        elif self.state == 'error_pairing':
            if self.timeout_counter == self.timeout_th or self.global_errormatch or self.global_measmatch:
                self.next_state = 'token_allocate'
            else:
                self.next_state = 'error_pairing'
        ## WAITING
        elif self.state == 'waiting':
            #if self.input_aqmeas_valid:
            if self.aqmeas_counter == self.config.aqmeas_th:
                self.next_state = 'token_allocate'
            else:
                self.next_state = 'waiting'
        else:
            sys.exit()


        # wr_pireg #
        if self.input_pchinfo_valid and self.input_piu_opcode == self.config.RUN_ESM_opcode and (not self.input_pchwr_stall):
            self.wr_pireg = True
        else:
            self.wr_pireg = False

        # rst_pireg #
        self.rst_pireg = self.pchinfo_taken

        # rst_first_token
        self.rst_first_token = (self.state == 'token_allocate')

        # shift_token
        self.shift_token = (self.state == 'token_allocate')

        # wr_zeroesm
        if self.layer_finish and self.next_state == 'token_allocate':
            self.wr_zeroesm = True
        else:
            self.wr_zeroesm = False

        # esm_finish
        if self.layer_finish and self.next_state == 'ready':
            self.esm_finish = True
        else:
            self.esm_finish = False

        # up_timeout
        if self.state == 'error_pairing':
            self.up_timeout = True
        else:
            self.up_timeout = False

        # rst_timeout
        if self.state == 'error_pairing' and self.next_state != 'error_pairing':
            self.rst_timeout = True
        else:
            self.rst_timeout = False
       
        # rst_cellstate
        if self.state == 'error_pairing' and self.next_state == 'token_allocate':
            self.rst_cellstate = True
        else:
            self.rst_cellstate = False
        # next_valid
        if self.state == 'token_allocate' and self.next_state == 'ready':
            self.next_valid = True
        else:
            self.next_valid = False
        # set_measerr_flag
        if self.token_finish and self.esmhead_exist:
            if self.round_counter in range(self.config.code_dist - (self.config.aqmeas_th-1), self.config.code_dist):
                if self.config.timeout_limit <= self.timeout_th:
                    self.set_measerr_flag = True
                else:
                    self.set_measerr_flag = False
            else:
                self.set_measerr_flag = False
        else:
            self.set_measerr_flag = False
    
        # set_last_measerr_flag
        self.set_last_measerr_flag = (self.set_measerr_flag and (self.round_counter == self.config.code_dist-1))

        # pop_aqmeasbuf
        self.pop_aqmeasbuf = (self.state in ["ready", "waiting"])

        # apply_aqmeas_flip
        self.apply_aqmeas_flip = (self.next_state == "ready")

        # rst_token_pipe
        if self.state == 'token_allocate' and (self.global_tokenmatch or self.token_finish):
            self.rst_token_pipe = True
        else:
            self.rst_token_pipe = False

        return

    def transfer_pchinfobuf(self):
        # connect input #
        if self.rst_pireg: # self.pchinfo_taken
            self.pchinfo_buf.input_data = self.pchinfo_regs
        else:
            self.pchinfo_buf.input_data = None
        self.pchinfo_buf.input_ready = self.esm_finish
        # transfer #
        self.pchinfo_buf.transfer()
        # connect output #
        self.pchinfo_running = self.pchinfo_buf.head
        self.pchinfo_empty = self.pchinfo_buf.empty
        return

    def transfer_educell_array(self):
        # connect input 
        for (i, j), educell in np.ndenumerate(self.educell_array):
            ## last_aqmeas_flip 
            educell.input_last_aqmeas_flip = self.last_aqmeas_flip_array[i][j]
            ## first_aqmeas
            educell.input_set_first_aqmeas = self.set_first_aqmeas
            ## shift_token
            educell.input_shift_token = self.shift_token # transfer_control, self.state == 'token_allocate'
            ## global_tokenmatch 
            educell.input_global_tokenmatch = self.global_tokenmatch # 
            ## global_errormatch
            educell.input_global_errormatch = self.global_errormatch #
            ## global_measmatch
            educell.input_global_measmatch = self.global_measmatch #
            ## wr_zeroesm
            educell.input_wr_zeroesm = self.wr_zeroesm
            ## rst_cellstate
            educell.input_rst_cellstate = self.rst_cellstate
            ## token_finish
            educell.input_token_finish = self.token_finish
            ## set_measerr_flag
            educell.input_set_measerr_flag = self.set_measerr_flag
            ## set_last_measerr_flag
            educell.input_set_last_measerr_flag = self.set_last_measerr_flag
            educell.input_pop_aqmeasbuf = self.pop_aqmeasbuf
            educell.input_apply_aqmeas_flip = self.apply_aqmeas_flip
            ## aqmeas_valid
            educell.input_aqmeas_valid = self.input_aqmeas_valid
            ## aqmeas
            if self.input_aqmeas_array is not None:
                educell.input_aqmeas = self.input_aqmeas_array[i][j]
            else:
                educell.input_aqmeas = 0
            ## pchinfo #
            pchrow = int(i / (self.config.num_ucrow * 2))
            pchcol = int(j / (self.config.num_uccol * 2))
            pchidx = pchrow * self.config.num_pchcol + pchcol
            if not self.pchinfo_empty:
                educell.input_pchinfo = self.pchinfo_running[pchidx]
            else:
                educell.input_pchinfo = {'pchtype': 'i', 'facebd': ['i', 'i', 'i', 'i']}
            ## curr_rowidx
            educell.input_curr_rowidx = self.curr_rowidx_reg
            ## myrowidx
            educell.input_myrowidx = self.rowidx_regs[i+j]

        # transfer: outputs
        for _, educell in np.ndenumerate(self.educell_array):
            educell.transfer()
        
        # connect outputs
        if self.unit_stat.uarch == "fast":
            self.global_tokenmatch = self.token_match_reg
        else:
            self.global_tokenmatch = False
            for _, educell in np.ndenumerate(self.educell_array):
                if educell.output_local_tokenmatch and (self.state == 'token_allocate'):
                    self.global_tokenmatch = True
                    break
        ## global_errormatch
        self.global_errormatch = False
        for _, educell in np.ndenumerate(self.educell_array):
            if educell.output_local_errormatch:
                self.global_errormatch = True
                break
        ## global_measmatch
        self.global_measmatch = False
        for _, educell in np.ndenumerate(self.educell_array):
            if educell.output_local_measmatch:
                self.global_measmatch = True
                break
        ## esmhead_exist
        self.esmhead_exist = False
        for _, educell in np.ndenumerate(self.educell_array):
            if educell.output_esmhead_exist:
                self.esmhead_exist = True
                break

        ## next_error_array
        self.next_error_array = np.full((self.config.num_dqrow, self.config.num_dqcol), 'i')
        for (i, j), curr_err in np.ndenumerate(self.error_array_reg):
            if i == 0 or j == 0:
                syn_nw = 'i'
            else:
                syn_nw = self.educell_array[i-1][j-1].output_syndrome[3]
            if i == 0:
                syn_ne = 'i'
            else:
                syn_ne = self.educell_array[i-1][j].output_syndrome[2]
            if j == 0:
                syn_sw = 'i'
            else:
                syn_sw = self.educell_array[i][j-1].output_syndrome[1]
            syn_se = self.educell_array[i][j].output_syndrome[0]
            
            # next_error
            next_error = 0
            error_list = [curr_err, syn_nw, syn_ne, syn_sw, syn_se]
            for err in error_list:
                if err == 'i':
                    err = 0
                elif err == 'x':
                    err = 1
                elif err == 'z':
                    err = 2
                elif err == 'y':
                    err = 3 
                else:
                   print("invalid err")
                   sys.exit()
                next_error ^= err
            if next_error == 0:
                next_error = 'i'
            elif next_error == 1:
                next_error = 'x'
            elif next_error == 2:
                next_error = 'z'
            elif next_error == 3:
                next_error = 'y'
            else:
                print('invalid next_error')
                sys.exit()
            self.next_error_array[i][j] = next_error
        ## eigen_array
        self.eigen_array = np.full((self.config.num_dqrow, self.config.num_dqcol), 0) 
        for (i, j), educell in np.ndenumerate(self.educell_array):
            self.eigen_array[i][j] = educell.output_eigen

        ## connect input token/flag
        for (i, j), educell in np.ndenumerate(self.educell_array):
            if self.token_set_array is None:
                educell.input_token = 0
            else:
                educell.input_token = self.token_set_array[i][j]
            if self.flag_set_array is None:
                educell.input_flag = 0
            else:
                educell.input_flag = self.flag_set_array[i][j]

        # connect spike, syndrome
        for (i, j), educell in np.ndenumerate(self.educell_array):
            ## in_nw
            if i == 0 or j == 0:
                inspike_nw = 0
                insyndrome_nw = 'i'
            else:
                inspike_nw = self.educell_array[i-1][j-1].output_spike[3] # out_se
                insyndrome_nw = self.educell_array[i-1][j-1].output_syndrome[3] # out_se
            ## in_ne
            if i == 0 or j == self.config.num_aqcol-1:
                inspike_ne = 0
                insyndrome_ne = 'i'
            else:
                inspike_ne = self.educell_array[i-1][j+1].output_spike[2] # out_sw
                insyndrome_ne = self.educell_array[i-1][j+1].output_syndrome[2] # out_sw
            ## in_sw
            if i == self.config.num_aqrow-1 or j == 0:
                inspike_sw = 0
                insyndrome_sw = 'i'
            else:
                inspike_sw = self.educell_array[i+1][j-1].output_spike[1] # out_ne
                insyndrome_sw = self.educell_array[i+1][j-1].output_syndrome[1] # out_ne
            ## in_se 
            if i == self.config.num_aqrow-1 or j == self.config.num_aqcol-1:
                inspike_se = 0
                insyndrome_se = 'i'
            else:
                inspike_se = self.educell_array[i+1][j+1].output_spike[0] # out_nw
                insyndrome_se = self.educell_array[i+1][j+1].output_syndrome[0] # out_nw
            ## in_n
            if i == 0:
                inspike_n = 0
                insyndrome_n = 'i'
            else:
                inspike_n = self.educell_array[i-1][j].output_spike[5] # out_s
                insyndrome_n = self.educell_array[i-1][j].output_syndrome[5] # out_s
            ## in_s
            if i == self.config.num_aqrow-1:
                inspike_s = 0
                insyndrome_s = 'i'
            else:
                inspike_s = self.educell_array[i+1][j].output_spike[4] # out_n
                insyndrome_s = self.educell_array[i+1][j].output_syndrome[4] # out_n
            educell.input_spike = [inspike_nw, inspike_ne, inspike_sw, inspike_se, inspike_n, inspike_s]
            educell.input_syndrome = [insyndrome_nw, insyndrome_ne, insyndrome_sw, insyndrome_se, insyndrome_n, insyndrome_s]

        # transfer again
        for _, educell in np.ndenumerate(self.educell_array):
            educell.transfer()

        return

    
    def transfer_token_setup(self): 
        # RR (slow baseline) or PE (fast opt.)
        # Input
            # esmhead_array
            # flag_token_array
        # Output
            # token_set_array
            # flag_set_array
            # last_token
            # next_rowidx
            # token_match (fast opt.)

        if "fast" in self.unit_stat.uarch: #PE 
            # input_array -> input_rows
            self.esmhead_rows = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1, self.config.num_aqrow), dtype=int)
            self.flag_out_rows = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1, self.config.num_aqrow), dtype=int)
            for (i, j), educell in np.ndenumerate(self.educell_array):
                row = i+j
                if row >= self.config.num_aqrow:
                    col = j - (row-self.config.num_aqrow+1)
                else:
                    col = j
                self.esmhead_rows[row][col] = educell.output_esmhead_exist
                self.flag_out_rows[row][col] = educell.output_flag

            # token_setup
            ## 0
            self.token_exist_rows_0 = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=bool)
            self.token_col_rows_0 = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=int)
            for row in range(self.config.num_aqrow+self.config.num_aqcol-1):
                esmhead_row = self.esmhead_rows[row]
                flag_out_row = self.flag_out_rows[row]
                #
                token_exist_row_0 = False
                token_col_row_0 = 0
                for col in range(self.config.num_aqrow):
                    if esmhead_row[col] and not flag_out_row[col]:
                        token_exist_row_0 = True
                        token_col_row_0 = col
                        break
                self.token_exist_rows_0[row] = token_exist_row_0
                self.token_col_rows_0[row] = token_col_row_0
                   
            ## 1
            self.token_exist_rows_1 = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=bool)
            self.token_exist_1 = False
            self.token_row_1 = 0
            for row in range(self.config.num_aqrow+self.config.num_aqcol-1):
                if self.token_exist_rows_0_reg[row]:
                    self.token_exist_rows_1[row] = True
                    self.token_exist_1 = True
                    self.token_row_1 = row
                    break
            self.token_col_rows_1 = self.token_col_rows_0_reg.copy()

            ## 2
            self.token_set_rows_2 = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1, self.config.num_aqrow), dtype=int)
            self.flag_set_rows_2 = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1, self.config.num_aqrow), dtype=int)
            for row in range(self.config.num_aqrow+self.config.num_aqcol-1):
                token_exist_row_1_reg = self.token_exist_rows_1_reg[row]
                token_col_row_1_reg = self.token_col_rows_1_reg[row];
                token_set_row_2 = np.zeros((self.config.num_aqrow), dtype=int)
                flag_set_row_2 = np.zeros((self.config.num_aqrow), dtype=int)
                if token_exist_row_1_reg:
                    token_set_row_2[token_col_row_1_reg] = 1;
                    for col in range(token_col_row_1_reg+1):
                        flag_set_row_2[col] = 1;
                self.token_set_rows_2[row] = token_set_row_2
                self.flag_set_rows_2[row] = flag_set_row_2
            ## out
            self.token_set_array = np.zeros((self.config.num_aqrow, self.config.num_aqcol), dtype=int)
            self.flag_set_array = np.zeros((self.config.num_aqrow, self.config.num_aqcol), dtype=int)
            self.last_token = 0
            self.next_rowidx = 0
            self.token_match = False

            if not self.token_valid_1_reg:
                pass
            else:
                for (i, j), _ in np.ndenumerate(self.educell_array):
                    row = i+j
                    if row >= self.config.num_aqrow:
                        col = j - (row-self.config.num_aqrow+1)
                    else:
                        col = j
                    self.token_set_array[i][j] = self.token_set_rows_2[row][col]
                    self.flag_set_array[i][j] = self.flag_set_rows_2[row][col]

                if self.token_exist_1_reg:
                    self.last_token = 0
                    self.next_rowidx = self.token_row_1_reg
                    self.token_match = True
                else:
                    self.last_token = 1
                    self.next_rowidx = 0
                    self.token_match = False

        else: # RR
            ## row_tokens_out
            self.row_tokens_out = [0] * (self.config.num_aqrow + self.config.num_aqcol-1)
            for (i, j), educell in np.ndenumerate(self.educell_array):
                if i == 0 or j == self.config.num_aqcol-1:
                    self.row_tokens_out[i+j] = educell.output_token
            ## set outputs
            ### token_set_array & flag_set_array
            self.token_set_array = np.zeros((self.config.num_aqrow, self.config.num_aqcol), dtype=int)
            self.flag_set_array = np.zeros((self.config.num_aqrow, self.config.num_aqcol), dtype=int)
            for (i, j), educell in np.ndenumerate(self.educell_array):
                if j == 0 or i == self.config.num_aqrow-1: #first educell for each row
                    if i == 0: # first row
                        self.token_set_array[i][j] = int(self.first_token)
                        self.flag_set_array[i][j] = int(self.first_token)
                    else:
                        self.token_set_array[i][j] = self.row_tokens_out[i+j-1] 
                        self.flag_set_array[i][j] = self.row_tokens_out[i+j-1] 
                else:
                    self.token_set_array[i][j] = self.educell_array[i+1][j-1].output_token
                    self.flag_set_array[i][j] = self.educell_array[i+1][j-1].output_token
            ### last_token
            self.last_token = self.educell_array[-1][-1].output_token
            ### next_rowidx
            self.next_rowidx = self.curr_rowidx_reg
            for idx, val in enumerate(self.row_tokens_out):
                if val == 1:
                    self.next_rowidx = idx+1
                    break
        return


    def transfer_output(self):
        ## output_error_array
        self.output_error_array = np.full((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), 'i',dtype='U8')
        for (i, j), err in np.ndenumerate(self.error_array_reg):
            pchrow = int(i / (self.config.num_ucrow*2))
            pchcol = int(j / (self.config.num_uccol*2))
            ucrow = int((i % (self.config.num_ucrow*2))/2)
            uccol = int((j % (self.config.num_uccol*2))/2)
            if (i%2) == 0 and (j%2) == 0:
                qbidx = 0
            elif (i%2) == 0 and (j%2) == 1:
                qbidx = 1
            elif (i%2) == 1 and (j%2) == 0:
                qbidx = 2
            else:
                qbidx = 3
            self.output_error_array[pchrow][pchcol][ucrow][uccol][qbidx] = err
        ## output_eigen_array
        self.output_eigen_array = np.full((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, int(self.config.num_qb_per_uc/2)), 0)
        for (i, j), eigen in np.ndenumerate(self.eigen_array):
            pchrow = int(i / (self.config.num_ucrow*2))
            pchcol = int(j / (self.config.num_uccol*2))
            ucrow = int((i % (self.config.num_ucrow*2))/2)
            uccol = int((j % (self.config.num_uccol*2))/2)
            if (i%2) == 0 and (j%2) == 0:
                qbidx = 0
            elif (i%2) == 0 and (j%2) == 1:
                qbidx = 2
            elif (i%2) == 1 and (j%2) == 0:
                qbidx = 3
            else:
                qbidx = 1
            self.output_eigen_array[pchrow][pchcol][ucrow][uccol][qbidx] = eigen

        ## output_pfflag
        if self.output_valid and self.opcode_reg in [self.config.LQM_X_opcode, self.config.LQM_Y_opcode, self.config.LQM_Z_opcode, self.config.MEAS_INTMD_opcode]:
            self.output_pfflag = True
        else:
            self.output_pfflag = False

        return

    def update(self, sim_cycle=0):
        if self.mode == "cycle":
            self.update_cycle(sim_cycle)
        else: # layer
            if (self.state in ['ready', 'waiting']) and (self.next_state in ['token_allocate']):
                while ((self.state in ['error_pairing', 'token_allocate']) or (self.next_state in ['token_allocate'])):
                    self.transfer()
                    self.update_cycle(sim_cycle)
            else:
                self.update_cycle(sim_cycle)

    def update_cycle(self, sim_cycle):
        # stat
        self.update_stats(sim_cycle)
        # registers
        self.update_registers()
        # pchinfo_buf
        self.pchinfo_buf.update()
        # educell_array
        for _, educell in np.ndenumerate(self.educell_array):
            educell.update()
        return
    
    def update_registers(self):
        # pipelining
        if "fast" in self.unit_stat.uarch:
            if self.rst_token_pipe:
                # out
                self.token_match_reg = False
                # 1
                self.token_exist_rows_1_reg = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=bool)
                self.token_exist_1_reg = False
                self.token_row_1_reg = 0 
                self.token_col_rows_1_reg = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=bool)
                self.token_valid_1_reg = False
                # 0
                self.token_exist_rows_0_reg = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=bool)
                self.token_col_rows_0_reg = np.zeros((self.config.num_aqrow+self.config.num_aqcol-1), dtype=int)
                self.token_valid_0_reg = False
            elif self.shift_token:
                # out
                self.token_match_reg = self.token_match
                # 1
                self.token_exist_rows_1_reg = self.token_exist_rows_1.copy()
                self.token_exist_1_reg = self.token_exist_1
                self.token_row_1_reg = self.token_row_1
                self.token_col_rows_1_reg = self.token_col_rows_1.copy()
                self.token_valid_1_reg = self.token_valid_0_reg
                # 0
                self.token_exist_rows_0_reg = self.token_exist_rows_0.copy()
                self.token_col_rows_0_reg = self.token_col_rows_0.copy()
                self.token_valid_0_reg = True
        # state
        self.state = self.next_state

        # set_first_aqmeas
        if self.input_aqmeas_valid:
            self.set_first_aqmeas = False
        elif self.layer_finish and (self.round_counter == self.config.code_dist-1):
            self.set_first_aqmeas = True
            
        # first_token
        if self.token_finish:
            self.first_token = True
        elif self.rst_first_token:
            self.first_token = False
        # pchinfo_regs #
        if self.rst_pireg:
            self.pchinfo_regs = []
            for i in range(self.config.num_pch):
                init_pchinfo = {'pchtype': 'i', 'facebd': ['i', 'i', 'i', 'i']}
                self.pchinfo_regs.append(init_pchinfo)
        elif self.wr_pireg:
            pchidx = self.input_pchinfo['pchidx']
            pchtype = self.input_pchinfo['pchtype']
            facebd = self.input_pchinfo['facebd']
          
            self.pchinfo_regs[pchidx]['pchtype'] = pchtype
            self.pchinfo_regs[pchidx]['facebd'] = facebd
        # pchinfo_taken #
        self.pchinfo_taken = (not self.pchinfo_taken) and (self.input_last_pchinfo and self.input_piu_opcode == self.config.RUN_ESM_opcode)
        # opcode_reg
        if self.input_tcu_valid and self.input_tcu_opcode != self.config.RUN_ESM_opcode:
            self.opcode_reg = self.input_tcu_opcode

        # timeout_th
        if self.layer_finish:
            self.timeout_th = 2
        elif self.layer_retry:
            self.timeout_th += 2
            #self.timeout_th += 1
        # timeout_counter:
        if self.rst_timeout: 
            self.timeout_counter = 0
        elif self.up_timeout:
            self.timeout_counter += 1
        # aqmeas_counter
        #if self.input_aqmeas_valid:
        educell_00 = self.educell_array[0][0]
        if educell_00.aqmeasbuf_valid and self.pop_aqmeasbuf:
            self.aqmeas_counter += 1
        elif self.layer_finish:
            self.aqmeas_counter -= 1
        # round_counter 
        if self.esm_finish:
            self.round_counter = 0
        elif self.layer_finish:
            self.round_counter += 1
        # curr_rowidx_reg
        if self.token_finish:
            self.curr_rowidx_reg = 0
        elif self.shift_token:
            self.curr_rowidx_reg = self.next_rowidx
        # last_token_reg
        if self.token_finish:
            self.last_token_reg = 0
        elif self.shift_token:
            self.last_token_reg = self.last_token


        # error_array_reg
        if self.global_errormatch:
            self.error_array_reg = copy.deepcopy(self.next_error_array)
        elif self.output_valid:
            self.error_array_reg = np.full((self.config.num_dqrow, self.config.num_dqcol), 'i') 
        # output_valid
        self.output_valid = self.next_valid

        return


    def debug(self):
        # Add variables to check in the debugging mode
        if self.output_valid:
            print("edu.output_pfflag: {}".format(self.output_pfflag))
            print("edu.output_error_array")
            debug_array(self.config, self.output_error_array)
            print("edu.output_eigen_array")
            debug_array(self.config, self.output_eigen_array, 'aq')

###########################################################


class edu_cell:
    def __init__(self, config, aqrow, aqcol):
        self.config = config
        self.aqrow = aqrow
        self.aqcol = aqcol
        # Wires
        ## Input wires
        self.input_last_aqmeas_flip = None
        self.input_set_first_aqmeas = None 
        self.input_shift_token = None
        self.input_global_tokenmatch = None
        self.input_global_errormatch = None
        self.input_global_measmatch = None
        self.input_wr_zeroesm = None
        self.input_rst_cellstate = None
        self.input_token_finish = None
        self.input_set_measerr_flag = None
        self.input_set_last_measerr_flag = None
        self.input_pop_aqmeasbuf = None
        self.input_apply_aqmeas_flip = None
        self.input_aqmeas_valid = None
        self.input_aqmeas = None
        self.input_pchinfo = None
        self.input_curr_rowidx = None
        self.input_myrowidx = None
        self.input_token = None #
        self.input_flag = None
        self.input_spike = None # (nw, ne, sw, se, n, s) + (w, e)
        self.input_syndrome = None # (nw, ne, sw, se, n, s) + (w, e)
        ## Intermediate wires
        ## from predecoder
        self.role = None # active / boundary / inactive
        self.possible_dir = None # (nw, ne, sw, se, n, s) + (w, e)
        self.syn_to_west = None
        self.syn_to_east = None
        self.first_aqmeas_flag = None # True if every RESM on this educell has no previous aqmeas
        ## from esmval
        self.aqmeasbuf_valid = None # IK add
        self.aqmeasbuf_val = None # IK add
        self.esm_val = None
        ## from decoder
        self.next_state = None
        self.spike_dir = None
        ## from syndir
        self.syndir = None
        ## from spikegen
        self.output_spike = None # (nw, ne, sw, se, n, s) + (w, e)
        ## from syndromegen
        self.output_syndrome = None #  (nw, ne, sw, se, n, s) + (w, e)
        ## Output wires
        self.output_token = None # #no gate
        self.output_flag = None # no gate
        self.output_esmhead_exist = None # no gate
        self.output_local_tokenmatch = None # one and
        self.output_local_errormatch = None # one and 
        self.output_local_measmatch = None # one and + or 
        self.output_eigen = None #aqmeas # one xor
        
        # Registers
        ## State register
        self.state = "ready"
        ## Constant register
        self.location_reg = [False, False, False, False, False] # (even, west, north, east, south)
        ## Input register
        self.token_reg = 0 #
        self.flag_token = 0
        self.spike_taken = False
        self.syndrome_taken = False 
        ## Internal register
        self.prev_aqmeas_reg = [0, 0]
        self.esm_reg = [0] * self.config.aqmeas_th 
        self.esm_delay_reg = [] 
        for i in range(self.config.aqmeas_th):
            if i == 0:
                self.esm_delay_reg.append(None)
            else:
                self.esm_delay_reg.append([0]*i)
        self.bd_delay_reg = [0] * self.config.bd_delay
        self.spikedir_reg = 'i'
        self.syndir_reg = 'i'
        self.measerr_flag = 0 
        self.first_aqmeas = True 
        self.last_measerr_flag = 0 
        self.last_aqmeas_flip_reg = 0 
        self.aqmeas_buf = [{"valid": False, "val": 0}, {"valid": False, "val": 0}] 

        # Init constant reg
        self.init_location_reg(aqrow, aqcol) 

    def init_location_reg(self, aqrow, aqcol):
        # even 
        if (aqrow + aqcol) % 2 == 0:
            even = True
        else:
            even = False
        # west
        if (aqcol % (self.config.num_uccol*2) == 0):
            west = True
        else:
            west = False
        # north
        if (aqrow % (self.config.num_ucrow*2)) == 0: 
            north = True
        else:
            north = False
        # east
        if (aqcol % (self.config.num_uccol*2) == (self.config.num_uccol*2-1)):
            east = True
        else:
            east = False
        # south
        if (aqrow  % (self.config.num_ucrow*2) == (self.config.num_ucrow*2-1)):
            south = True
        else:
            south = False
        
        # north_2
        if (aqrow % (self.config.num_ucrow*2)) == 1: 
            north_2 = True
        else:
            north_2 = False
        # south_2
        if (aqrow  % (self.config.num_ucrow*2) == (self.config.num_ucrow*2-1-1)):
            south_2 = True
        else:
            south_2 = False
        
        self.location_reg = [even, west, north, east, south, north_2, south_2]
        return


    def transfer(self):
        self.transfer_predecoder()
        self.transfer_esmval()
        self.transfer_output()
        self.transfer_decoder()
        self.transfer_spikegen()
        self.transfer_syndir()
        self.transfer_syndromegen()
        self.transfer_output()
        return

    def transfer_predecoder(self):
        (even, west, north, east, south, north_2, south_2) = self.location_reg
        pchtype = self.input_pchinfo['pchtype']
        facebd = self.input_pchinfo['facebd']
        (facebd_w, facebd_n, facebd_e, facebd_s) = facebd
        ## role, possible_dir, first_aqmeas_flag
        if self.config.block_type == "Distillation":
            if pchtype == 'zt':
                # default first_aqmeas_flag
                self.first_aqmeas_flag = False
                
                if north and west: # NW
                    self.role = 'inactive'
                    self.possible_dir = (False, False, False, False, False, False)
                elif north and not east: # N
                    if even:
                        self.role = 'active'
                    else:
                        self.role = 'boundary'
                    self.possible_dir = (False, False, True, True, False, False)
                elif north and east: # NE
                    self.role = 'boundary'
                    if facebd_e == 'mp':
                        self.possible_dir = (False, False, True, True, False, False)
                    else:
                        self.possible_dir = (False, False, True, False, False, False)
                elif west and not south: # W
                    if even:
                        self.role = 'active'
                    else:
                        self.role = 'boundary'
                    self.possible_dir = (False, True, False, True, False, False)
                elif east and not south: # E
                    if facebd_e == 'mp':
                        if even:
                            self.first_aqmeas_flag = True
                        else:
                            self.first_aqmeas_flag = False
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                    else:
                        if even:
                            self.role = 'boundary'
                        else:
                            self.role = 'active'
                        self.possible_dir = (True, False, True, False, False, False)
                elif west and south: # SW
                    self.role = 'boundary'
                    self.possible_dir = (False, True, False, True, False, False)
                elif south and not east: # S
                    self.role = 'active'
                    self.possible_dir = (True, True, True, True, False, False)
                elif south and east: # SE
                    if facebd_e == 'mp':
                        self.first_aqmeas_flag = True
                        self.role = 'active'
                        self.possible_dir = (True, True, True, False, False, True)
                    else:
                        self.role = 'boundary'
                        self.possible_dir = (True, False, True, False, False, False)
                else: # C
                    self.role = 'active'
                    self.possible_dir = (True, True, True, True, False, False)
            elif pchtype == 'zb':
                # default first_aqmeas_flag
                self.first_aqmeas_flag = False
                
                if north and west: # NW
                    self.role = 'boundary'
                    self.possible_dir = (False, True, False, True, False, False)
                elif north and not east: # N
                    self.role = 'active'
                    self.possible_dir = (True, True, True, True, False, False)
                elif north and east: # NE
                    if facebd_e == 'pp':
                        self.first_aqmeas_flag = True
                        self.role = 'active'
                        self.possible_dir = (True, False, True, True, True, False)
                    else:
                        self.role = 'boundary'
                        self.possible_dir = (True, False, True, False, False, False)
                elif west and not south: # W
                    if even:
                        self.role = 'boundary'
                    else:
                        self.role = 'active'
                    self.possible_dir = (False, True, False, True, False, False)
                elif east and not south: # E
                    if facebd_e == 'pp':
                        if even:
                            self.first_aqmeas_flag = False
                        else:
                            self.first_aqmeas_flag = True
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                    else:
                        if even:
                            self.role = 'active'
                        else:
                            self.role = 'boundary'
                        self.possible_dir = (True, False, True, False, False, False)
                elif west and south: # SW
                    self.role = 'inactive'
                    self.possible_dir = (False, False, False, False, False, False)
                elif south and not east: # S
                    if even:
                        self.role = 'boundary'
                    else:
                        self.role = 'active'
                        
                    self.possible_dir = (True, True, False, False, False, False)
                elif south and east: # SE
                    self.role = 'boundary'
                    if facebd_e == 'pp':
                        self.possible_dir = (True, True, False, False, False, False)
                    else:
                        self.possible_dir = (True, False, False, False, False, False)
                else: # C
                    self.role = 'active'
                    self.possible_dir = (True, True, True, True, False, False)
            elif pchtype == 'mt':
                # default first_aqmeas_flag
                if facebd_w == 'mp':
                    self.first_aqmeas_flag = True
                else:
                    self.first_aqmeas_flag = False
                    
                if north and west: # NW
                    if facebd_w == 'mp':
                        self.role = 'active'
                    else:
                        self.role = 'boundary'
                    self.possible_dir = (False, False, True, True, False, False)
                elif north and not east: # N
                    if even:
                        self.role = 'active'
                    else:
                        self.role = 'boundary'
                        self.first_aqmeas_flag = False
                    self.possible_dir = (False, False, True, True, False, False)
                elif north and east: # NE
                    self.role = 'boundary'
                    self.possible_dir = (False, False, True, False, False, False)
                    self.first_aqmeas_flag = False
                elif west and not south: # W
                    if facebd_w == 'mp':
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                    else:
                        if even: 
                            self.role = 'boundary'
                        else:
                            self.role = 'active'
                        self.possible_dir = (False, True, False, True, False, False)
                elif east and not south: # E
                    if even:
                        self.role = 'active'
                    else:
                        self.role = 'boundary'
                        self.first_aqmeas_flag = False
                    self.possible_dir = (True, False, True, False, False, False)
                elif west and south: # SW
                    self.role = 'active'
                    if facebd_w == 'mp':
                        self.possible_dir = (True, True, False, False, False, True)
                    else:
                        self.possible_dir = (False, True, False, False, False, True)
                elif south and not east: # S
                    self.role = 'active'
                    self.possible_dir = (True, True, False, False, False, True)
                elif south and east: # SE
                    if facebd_w == 'mp':
                        self.role = 'active'
                        self.possible_dir = (True, False, False, False, False, True)
                    else:
                        self.role = 'boundary'
                        self.possible_dir = (True, False, False, False, False, False)
                else: # C
                    self.role = 'active'
                    self.possible_dir = (True, True, True, True, False, False)
            elif pchtype == 'mb':
                # default first_aqmeas_flag
                self.first_aqmeas_flag = False
                
                if north and west: # NW
                    if facebd_n == 'lp' and facebd_w == 'pp':
                        self.first_aqmeas_flag = True
                        self.role = 'active'
                        self.possible_dir = (False, False, True, True, True, False)
                    elif facebd_n == 'lp':
                        self.role = 'active'
                        self.possible_dir = (False, False, False, True, True, False)
                    else:
                        self.role = 'boundary'
                        self.possible_dir = (False, False, False, True, False, False)
                elif north and not east: # N
                    if even:
                        if facebd_n == 'lp' and facebd_w == 'pp':
                            self.first_aqmeas_flag = True
                        
                    if facebd_n == 'lp':
                        self.role = 'active'
                        self.possible_dir = (False, False, True, True, True, False)
                    else:
                        if even:
                            self.role = 'boundary'
                        else:
                            self.role = 'active'
                        self.possible_dir = (False, False, True, True, False, False)
                elif north and east: # NE
                    if facebd_n == 'lp' and facebd_w == 'pp':
                        self.first_aqmeas_flag = True

                    if facebd_e == 'pp':
                        self.role = 'active'
                        self.possible_dir = (False, False, True, True, True, False)
                    else:
                        self.role = 'boundary'
                        self.possible_dir = (False, False, True, False, False, False)
                elif west and not south: # W
                    if even:
                        pass
                    else:
                        if facebd_n == 'lp' and facebd_w == 'pp':
                            self.first_aqmeas_flag = True
                    
                    if facebd_w == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                    else:
                        if even:
                            self.role = 'active'
                        else:
                            self.role = 'boundary'
                        self.possible_dir = (False, True, False, True, False, False)
                elif east and not south: # E
                    if even:
                        pass
                    else:
                        if facebd_n == 'lp' and facebd_w == 'pp':
                            self.first_aqmeas_flag = True
                            
                    if facebd_e == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                    else:
                        if even:
                            self.role = 'active'
                        else:
                            self.role = 'boundary'
                        self.possible_dir = (True, False, True, False, False, False)
                elif west and south: # SW
                    if facebd_n == 'lp' and facebd_w == 'pp':
                        self.first_aqmeas_flag = True

                    if facebd_w == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, True, False, False, False, False)
                    else:
                        self.role = 'boundary'
                        self.possible_dir = (False, True, False, False, False, False)
                elif south and not east: # S
                    if even:
                        self.role = 'boundary'
                    else:
                        self.role = 'active'
                    self.possible_dir = (True, True, False, False, False, False)
                elif south and east: # SE
                    self.role = 'boundary'
                    if facebd_w == 'pp':
                        self.possible_dir = (True, True, False, False, False, False)
                    else:
                        self.possible_dir = (True, False, False, False, False, False)
                else: # C
                    self.role = 'active'
                    self.possible_dir = (True, True, True, True, False, False)
            elif pchtype == 'm':
                # default first_aqmeas_flag
                self.first_aqmeas_flag = False
                
                if north and west: # NW
                    self.role = 'boundary'
                    if facebd_n == 'pp':
                        self.possible_dir = (False, True, False, True, False, False)
                    else:
                        self.possible_dir = (False, False, False, True, False, False)
                elif north and not east: # N
                    if facebd_n == 'pp':
                        if even:
                            pass
                        else:
                            self.first_aqmeas_flag = True
                        
                    if facebd_n == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                    else:
                        if even:
                            self.role = 'active'
                        else:
                            self.role = 'boundary'
                        self.possible_dir = (False, False, True, True, False, False)
                elif north and east: # NE
                    if facebd_n == 'pp':
                        self.first_aqmeas_flag = True
                            
                    if facebd_n == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, False, True, False, False, False)
                    else:
                        self.role = 'boundary'
                        self.possible_dir = (False, False, True, False, False, False)
                elif west and not south: # W
                    if even:
                        self.role = 'boundary'
                    else:
                        self.role = 'active'
                    self.possible_dir = (False, True, False, True, False, False)
                elif east and not south: # E
                    if even:
                        self.role = 'boundary'
                    else:
                        self.role = 'active'
                    self.possible_dir = (True, False, True, False, False, False)
                elif west and south: # SW
                    if facebd_s == 'pp':
                        self.first_aqmeas_flag = True
                            
                    if facebd_s == 'pp':
                        self.role = 'active'
                        self.possible_dir = (False, True, False, True, False, False)
                    else:
                        self.role = 'boundary'
                        self.possible_dir = (False, True, False, False, False, False)
                elif south and not east: # S
                    if facebd_s == 'pp':
                        if even:
                            pass
                        else:
                            self.first_aqmeas_flag = True
                        
                    if facebd_s == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                    else:
                        if even:
                            self.role = 'active'
                        else:
                            self.role = 'boundary'
                        self.possible_dir = (True, True, False, False, False, False)
                elif south and east: # SE
                    self.role = 'boundary'
                    if facebd_s == 'pp':
                        self.possible_dir = (True, False, True, False, False, False)
                    else:
                        self.possible_dir = (True, False, False, False, False, False)
                else: # C
                    self.role = 'active'
                    self.possible_dir = (True, True, True, True, False, False)
            elif pchtype == 'x' or pchtype == 'z':
                # default first_aqmeas_flag
                self.first_aqmeas_flag = False
                
                if north and west: # NW
                    self.role = 'boundary'
                    self.possible_dir = (False, False, True, True, False, False)
                elif north and not east: # N
                    if even:
                        self.role = 'boundary'
                    else:
                        self.role = 'active'
                    self.possible_dir = (False, False, True, True, False, False)
                elif north and east: # NE
                    self.role = 'boundary'
                    self.possible_dir = (False, False, True, False, False, False)
                elif west and not south: # W
                    if facebd_w == 'pp':
                        if even:
                            pass
                        else:
                            self.first_aqmeas_flag = True
                            
                    if facebd_w == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                    else:
                        if even:
                            self.role = 'active'
                        else:
                            self.role = 'boundary'
                        self.possible_dir = (False, True, False, True, False, False)
                elif east and not south: # E
                    if even:
                        self.role = 'active'
                    else:
                        self.role = 'boundary'
                    self.possible_dir = (True, False, True, False, False, False)
                elif west and south: # SW
                    if facebd_w == 'pp':
                        self.first_aqmeas_flag = True
                        
                    if facebd_w == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, True, False, False, False, False)
                    else:
                        self.role = 'boundary'
                        self.possible_dir = (False, True, False, False, False, False)
                elif south and not east: # S
                    if even:
                        self.role = 'boundary'
                    else:
                        self.role = 'active'
                    self.possible_dir = (True, True, False, False, False, False)
                elif south and east: # SE
                    self.role = 'boundary'
                    self.possible_dir = (True, False, False, False, False, False)
                else: # C
                    self.role = 'active'
                    self.possible_dir = (True, True, True, True, False, False)
            elif 'a' in pchtype:
                # default first_aqmeas_flag
                self.first_aqmeas_flag = False
                if north and west: # NW
                    self.role = 'boundary'
                    if facebd_n == 'pp':
                        self.possible_dir = (False, True, True, True, False, False)
                    else:
                        self.possible_dir = (False, False, True, True, False, False)
                elif north and not east: # N
                                                
                    if facebd_n == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                        self.first_aqmeas_flag = True
                    else:
                        if even:
                            self.role = 'boundary'
                        else:
                            self.role = 'active'
                            self.first_aqmeas_flag = True
                        self.possible_dir = (False, False, True, True, False, False)
                elif north and east: # NE
                    if facebd_n == 'pp' and facebd_e == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, False, True, True, False, False)
                        self.first_aqmeas_flag = True
                    elif facebd_n == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, False, True, False, False, False)
                        self.first_aqmeas_flag = True
                    elif facebd_e == 'pp':
                        self.role = 'active'
                        self.possible_dir = (False, False, True, True, False, False)
                        self.first_aqmeas_flag = True
                    else:
                        self.role = 'inactive'
                        self.possible_dir = (False, False, False, False, False, False)
                elif west and not south: # W
                    self.role = 'active'
                    self.possible_dir = (True, True, True, True, False, False)
                    self.first_aqmeas_flag = True
                elif east and not south: # E
                    if facebd_e == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                        self.first_aqmeas_flag = True
                    else:
                        if even:
                            self.role = 'boundary'
                        else:
                            self.role = 'active'
                            self.first_aqmeas_flag = True
                        self.possible_dir = (True, False, True, False, False, False)
                elif west and south: # SW
                    self.role = 'active'
                    self.possible_dir = (True, True, False, True, False, False)
                    self.first_aqmeas_flag = True
                elif south and not east: # S
                    if facebd_s == 'pp':
                        self.role = 'active'
                        self.possible_dir = (True, True, True, True, False, False)
                        self.first_aqmeas_flag = True
                    else:
                        if even:
                            self.role = 'boundary'
                        else:
                            self.role = 'active'
                            self.first_aqmeas_flag = True
                        self.possible_dir = (True, True, False, False, False, False)
                elif south and east: # SE
                    self.role = 'boundary'
                    if facebd_s == 'pp' and facebd_e == 'pp':
                        self.possible_dir = (True, True, True, False, False, False)
                    elif facebd_s == 'pp':
                        self.possible_dir = (True, False, True, False, False, False)
                    elif facebd_e == 'pp':
                        self.possible_dir = (True, True, False, False, False, False)
                    else:
                        self.possible_dir = (True, False, False, False, False, False)
                else: # C
                    self.role = 'active'
                    self.possible_dir = (True, True, True, True, False, False)
                    self.first_aqmeas_flag = True
            else:
                self.role = 'inactive'
                self.possible_dir = (False, False, False, False, False, False)
                self.first_aqmeas_flag = False
            # syn_to_west/east
            if pchtype == 'zt':
                if east and (not north) and (not south):
                    if facebd_e == 'mp':
                        if even:
                            self.syn_to_west = 'z'
                            self.syn_to_east = 'x'
                        else:
                            self.syn_to_west = 'x'
                            self.syn_to_east = 'z'
                    else:
                        if even:
                            self.syn_to_west = 'z'
                            self.syn_to_east = 'i'
                        else:
                            self.syn_to_west = 'x'
                            self.syn_to_east = 'i'
                elif east and south:
                    if facebd_e == 'mp':
                        self.syn_to_west = 'z'
                        self.syn_to_east = 'x'
                    else:
                        self.syn_to_west = 'z'
                        self.syn_to_east = 'i'
                else:
                    if even:
                        self.syn_to_west = 'z'
                        self.syn_to_east = 'z'
                    else:
                        self.syn_to_west = 'x'
                        self.syn_to_east = 'x'
            elif pchtype == 'mt':
                if even:
                    self.syn_to_west = 'x'
                    self.syn_to_east = 'x'
                else:
                    self.syn_to_west = 'z'
                    self.syn_to_east = 'z'
            else:
                if even:
                    self.syn_to_west = 'z'
                    self.syn_to_east = 'z'
                else:
                    self.syn_to_west = 'x'
                    self.syn_to_east = 'x'
        else:
            raise Exception("error_decode_unit - transfer_predecoder: block_type {} is currently not supported".format(self.config.block_type))
        return

    def transfer_esmval(self):
        self.aqmeasbuf_valid = self.aqmeas_buf[0]['valid']
        self.aqmeasbuf_val = self.aqmeas_buf[0]['val']

        if self.first_aqmeas or self.input_wr_zeroesm:
            self.esm_val = 0
        elif self.aqmeasbuf_valid and self.role == 'active':
            self.esm_val = self.aqmeasbuf_val ^ self.prev_aqmeas_reg[0] ^ self.measerr_flag
        else:
            self.esm_val = 0

    def transfer_decoder(self):
        ## next_state
        if self.input_rst_cellstate:
            self.next_state = 'ready'
        else:
            esm_exist = sum(self.esm_reg) != 0
            if self.role == 'active':
                if self.output_local_tokenmatch:
                    self.next_state = 'synk'
                elif esm_exist:
                    self.next_state = 'source'
                else:
                    self.next_state = 'transmit'
            elif self.role == 'boundary':
                self.next_state = 'boundary'
            else:
                self.next_state = 'inactive'

        ## spike_dir
        ### expected_dir
        if self.input_myrowidx < self.input_curr_rowidx:
            expected_dir = 'se'
        elif self.input_myrowidx > self.input_curr_rowidx:
            expected_dir = 'nw'
        else: # same
            if self.flag_token == 1:
                expected_dir = 'ne'
            else: # flag_token == 0
                expected_dir = 'sw'
        if expected_dir == 'nw':
            if self.possible_dir[0]:
                self.spike_dir = 'nw'
            elif self.possible_dir[4]:
                self.spike_dir = 'n'
            else:
                self.spike_dir = 'i'
        elif expected_dir == 'ne':
            if self.possible_dir[1]:
                self.spike_dir = 'ne'
            elif self.possible_dir[4]:
                self.spike_dir = 'n'
            else:
                self.spike_dir = 'i'   
        elif expected_dir == 'sw':
            if self.possible_dir[2]:
                self.spike_dir = 'sw'
            elif self.possible_dir[5]:
                self.spike_dir = 's'
            else:
                self.spike_dir = 'i'
        else: # expected_dir == 'se'
            if self.possible_dir[3]:
                self.spike_dir = 'se'
            elif self.possible_dir[5]:
                self.spike_dir = 's'
            else:
                self.spike_dir = 'i'
        return


    def transfer_spikegen(self):
        ## spike_out
        spike_esm = 0
        for i in range(self.config.aqmeas_th):
            if i == 0:
                spike_esm = self.esm_reg[0]
            else:
                spike_esm |= self.esm_delay_reg[i][0]
        spike_bd = self.bd_delay_reg[0]
        spike_in = int(self.spike_taken)

        if self.state == 'source':
            spike_out = spike_esm
        elif self.state == 'boundary':
            spike_out = spike_bd
        elif self.state == 'transmit':
            spike_out = spike_in
        else:
            spike_out = 0

        ##  
        if self.spikedir_reg == 'nw':
            self.output_spike = [spike_out, 0, 0, 0, 0, 0]
        elif self.spikedir_reg == 'ne':
            self.output_spike = [0, spike_out, 0, 0, 0, 0]
        elif self.spikedir_reg == 'sw':
            self.output_spike = [0, 0, spike_out, 0, 0, 0]
        elif self.spikedir_reg == 'se':
            self.output_spike = [0, 0, 0, spike_out, 0, 0]
        elif self.spikedir_reg == 'n':
            self.output_spike = [0, 0, 0, 0, spike_out, 0]
        elif self.spikedir_reg == 's':
            self.output_spike = [0, 0, 0, 0, 0, spike_out]
        else:
            self.output_spike = [0, 0, 0, 0, 0, 0]

        return


    def transfer_syndir(self):
        self.syndir = 'i'
        if self.input_spike is None:
            return 

        # Set priority (Heuristic)
        priority = [5,4,3,2,1,0]
             
        syndir_list = ['nw','ne','sw','se','n','s']
        for i in priority:
            if self.input_spike[i] == 1:
                self.syndir = syndir_list[i]
                break
            
        return 


    def transfer_syndromegen(self):
        #
        if self.syndrome_taken and self.spike_taken:
            if self.state in ['source', 'boundary']: # output_local_errormatch
                syndrome_out = 'i'
            elif 'w' in self.syndir_reg:
                syndrome_out = self.syn_to_west
            elif 'e' in self.syndir_reg:
                syndrome_out = self.syn_to_east
            elif self.syndir_reg in ['n', 's']: # don't care
                syndrome_out = 'z'
            else:
                syndrome_out = 'i'
        else:
            syndrome_out = 'i'

        ##  
        if self.syndir_reg == 'nw':
            self.output_syndrome = [syndrome_out, 'i', 'i', 'i', 'i', 'i']
        elif self.syndir_reg == 'ne':
            self.output_syndrome = ['i', syndrome_out, 'i', 'i', 'i', 'i']
        elif self.syndir_reg == 'sw':
            self.output_syndrome = ['i', 'i', syndrome_out, 'i', 'i', 'i']
        elif self.syndir_reg == 'se':
            self.output_syndrome = ['i', 'i', 'i', syndrome_out, 'i', 'i']
        elif self.syndir_reg == 'n':
            self.output_syndrome = ['i', 'i', 'i', 'i', syndrome_out, 'i']
        elif self.syndir_reg == 's':
            self.output_syndrome = ['i', 'i', 'i', 'i', 'i', syndrome_out]
        else:
            self.output_syndrome = ['i', 'i', 'i', 'i', 'i', 'i']

        return

    def transfer_output(self):
        # output_token
        self.output_token = self.token_reg
        self.output_flag = self.flag_token
        # output_esmhead_exist
        self.output_esmhead_exist = self.esm_reg[0] != 0
        # output_local_tokenmatch
        self.output_local_tokenmatch = (self.role == 'active' and self.output_token == 1 and self.output_esmhead_exist)
        # output_local_errormatch
        if self.state in ['source', 'boundary'] and self.syndrome_taken:
            self.output_local_errormatch = True
        else:
            self.output_local_errormatch = False
        # output_local_measmatch
        if self.state == 'synk':
            self.output_local_measmatch = False
            for (i, reg) in enumerate(self.esm_delay_reg):
                if i == 0:
                    continue
                if reg[0] == 1:
                    self.output_local_measmatch = True
                    break
        else:
            self.output_local_measmatch = False
        # output_eigen
        self.output_eigen = self.last_measerr_flag ^ (self.prev_aqmeas_reg[1] ^ self.prev_aqmeas_reg[0])
        
        return


    def update(self):
        spike_taken = self.spike_taken
        esmhead = self.esm_reg[0]
        # token_reg
        if self.input_token_finish:
            self.token_reg = 0
        elif self.input_shift_token:
            self.token_reg = self.input_token
        # flag_token
        if self.input_token_finish:
            self.flag_token = 0
        elif self.input_shift_token and self.flag_token == 0:
            self.flag_token =  self.input_flag
        # spike_taken 
        if self.input_rst_cellstate:
            self.spike_taken = False
        elif self.state == 'source':
            self.spike_taken = True
        elif not self.spike_taken:
            self.spike_taken = sum(self.input_spike) != 0
        # syndrome_taken
        if self.input_rst_cellstate:
            self.syndrome_taken = False
        elif self.state == 'synk':
            self.syndrome_taken = True
        elif not self.syndrome_taken:
            for syndrome in self.input_syndrome:
                if syndrome != 'i':
                    self.syndrome_taken = True
        # prev_aqmeas_reg
        if self.input_pop_aqmeasbuf and self.aqmeasbuf_valid: 
            if self.first_aqmeas:
                self.prev_aqmeas_reg[0] = 0
            else:
                self.prev_aqmeas_reg[0] = self.prev_aqmeas_reg[1]
            self.prev_aqmeas_reg[1] = self.aqmeasbuf_val
        if self.input_apply_aqmeas_flip and self.last_aqmeas_flip_reg == 1:
            self.prev_aqmeas_reg[0] ^= 1

        # aqmeas_buf
        if self.input_aqmeas_valid or self.input_pop_aqmeasbuf:
            ## tail -> head
            self.aqmeas_buf[0] = self.aqmeas_buf[1]
            ## new -> tail
            if self.input_aqmeas_valid:
                try: 
                    self.input_aqmeas = int(self.input_aqmeas)
                except:
                    self.input_aqmeas = 0
                self.aqmeas_buf[1] = {"valid": True, "val": self.input_aqmeas}
            elif self.input_pop_aqmeasbuf:
                self.aqmeas_buf[1] = {"valid": False, "val": 0}

        
        # last_aqmeas_flip_reg
        if self.input_last_aqmeas_flip == 1:
            self.last_aqmeas_flip_reg = 1
        elif self.input_apply_aqmeas_flip:
            self.last_aqmeas_flip_reg = 0
                
        # esm_reg 
        if (self.aqmeasbuf_valid and self.input_pop_aqmeasbuf) or self.input_wr_zeroesm:
            for i in range(len(self.esm_reg)-1):
                self.esm_reg[i] = self.esm_reg[i+1]
            self.esm_reg[-1] = self.esm_val
        elif (self.role != 'active' and self.output_token and self.output_esmhead_exist):
            self.esm_reg[0] = 0
        elif self.input_global_errormatch:
            if self.state == 'synk':
                self.esm_reg[0] = 0
            elif self.state == 'source' and self.output_local_errormatch:
                for i in range(self.config.aqmeas_th):
                    if self.esm_reg[i] == 1:
                        self.esm_reg[i] = 0
                        break
        elif self.input_global_measmatch:
            if self.state == 'synk':
                self.esm_reg[0] = 0
                for (i, reg) in enumerate(self.esm_delay_reg):
                    if i == 0:
                        continue
                    if reg[0] == 1:
                        self.esm_reg[i] = 0
                        break
        # esm_delay_reg
        if self.input_rst_cellstate:
            self.esm_delay_reg = [] 
            for i in range(self.config.aqmeas_th):
                if i == 0:
                    self.esm_delay_reg.append(None)
                else:
                    self.esm_delay_reg.append([0]*i)
        elif self.state in ['source', 'synk']:
            for i in range(self.config.aqmeas_th):
                if i == 0:
                    pass
                else:
                    for j in range(len(self.esm_delay_reg[i])):
                        if j == len(self.esm_delay_reg[i])-1:
                            self.esm_delay_reg[i][j] = self.esm_reg[i]
                        else:
                            self.esm_delay_reg[i][j] = self.esm_delay_reg[i][j+1]
        # boundary_delay_reg
        if self.input_rst_cellstate:
            self.bd_delay_reg = [0] * self.config.bd_delay
        elif self.state == 'boundary':
            for i in range(len(self.bd_delay_reg)):
                if i == len(self.bd_delay_reg)-1:
                    self.bd_delay_reg[i] = 1
                else:
                    self.bd_delay_reg[i] = self.bd_delay_reg[i+1]

        # state
        if self.input_global_tokenmatch or self.input_rst_cellstate:
            self.state = self.next_state
        # spikedir_reg
        if self.input_rst_cellstate:
            self.spikedir_reg = 'i'
        elif self.input_global_tokenmatch:
            self.spikedir_reg = self.spike_dir
        # syndir_reg
        if self.input_rst_cellstate:
            self.syndir_reg = 'i'
        elif not spike_taken and sum(self.input_spike) != 0:
            self.syndir_reg = self.syndir
        # measerr_flag
        if self.input_set_measerr_flag:
            if esmhead == 1:
                self.measerr_flag = 1
        elif self.aqmeasbuf_valid and self.input_pop_aqmeasbuf:
            self.measerr_flag = 0
        # last_measerr_flag
        if self.input_set_last_measerr_flag:
            if esmhead == 1:
                self.last_measerr_flag = 1
        elif self.aqmeasbuf_valid and self.input_pop_aqmeasbuf:
            self.last_measerr_flag = 0
        # first_aqmeas
        if self.aqmeasbuf_valid and self.input_pop_aqmeasbuf:
            self.first_aqmeas = False
        elif self.input_set_first_aqmeas and self.first_aqmeas_flag:
            self.first_aqmeas = True
        return
