import os, sys 
#
curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
par_dir = os.path.join(curr_dir, os.pardir)
#
sys.path.insert(0, par_dir)
from util import *
# General
import numpy as np
import math
# Submodule
import qc_compose_unit as qc_compose_unit
# ray
import ray

'''
# qtexec_unit emulates the qubit plane: 
# 1) run incoming operations from TCU 
# 2) inject errors that follows a configured error model
# 3) calculate actual measurement result using STIM

# [Ref.A] Byun, Ilkwon, et al. "XQsim: modeling cross-technology control processors for 10+ K qubit quantum computers." Proceedings of the 49th Annual International Symposium on Computer Architecture. 2022.
# [Ref.B] Litinski, Daniel. "A game of surface codes: Large-scale quantum computing with lattice surgery." Quantum 3 (2019): 128.
# [Ref.C] Bravyi, Sergey, Graeme Smith, and John A. Smolin. "Trading classical and quantum computational resources." Physical Review X 6.2 (2016): 021043.
# [Ref.D] Gidney, Craig. "Stim: a fast stabilizer circuit simulator." Quantum 5 (2021): 497.
'''

# Helper functions for emulate_mode
def merge_pauli(pauli_1, pauli_2):
    result = 'i'
    if pauli_1 == 'i' or pauli_1 == '-':
        if pauli_2 == 'i' or pauli_2 == '-':
            result = 'i'
        elif pauli_2 == 'x':
            result = 'x'
        elif pauli_2 == 'y':
            result = 'y'
        elif pauli_2 == 'z':
            result = 'z'
        else:
            pass
    elif pauli_1 == 'x':
        if pauli_2 == 'i' or pauli_2 == '-':
            result = 'x'
        elif pauli_2 == 'x':
            result = 'i'
        elif pauli_2 == 'y':
            result = 'z'
        elif pauli_2 == 'z':
            result = 'y'
        else:
            pass
    elif pauli_1 == 'y':
        if pauli_2 == 'i' or pauli_2 == '-':
            result = 'y'
        elif pauli_2 == 'x':
            result = 'z'
        elif pauli_2 == 'y':
            result = 'i'
        elif pauli_2 == 'z':
            result = 'x'
        else:
            pass
    elif pauli_1 == 'z':
        if pauli_2 == 'i' or pauli_2 == '-':
            result = 'z'
        elif pauli_2 == 'x':
            result = 'y'
        elif pauli_2 == 'y':
            result = 'x'
        elif pauli_2 == 'z':
            result = 'i'
        else:
            pass
    else:
        pass

    return result

def apply_commutation (op_type, target_pauli):
    if len(target_pauli) == 2:
        target_pauli = str(target_pauli[0]) + str(target_pauli[1])
        if target_pauli[0] == '-':
            target_pauli = 'i' + (target_pauli[1])
        if target_pauli[1] == '-':
            target_pauli = (target_pauli[0]) + 'i'
    elif len(target_pauli) == 1:
        if target_pauli == '-':
            target_pauli = 'i'

    if op_type == 'h':
        if target_pauli == 'x':
            result_pauli = 'z'
        elif target_pauli == 'z':
            result_pauli = 'x'
        else:
            result_pauli = target_pauli
    elif op_type == 's' or op_type == 'sdag':
        if target_pauli == 'x':
            result_pauli = 'y'
        elif target_pauli == 'y':
            result_pauli = 'x'
        else:
            result_pauli = target_pauli
    elif op_type == 'cz':
        target_pauli = target_pauli[0] + target_pauli[1]
        if target_pauli == 'xx':
            result_pauli = 'yy'
        elif target_pauli == 'xy':
            result_pauli = 'yz'
        elif target_pauli == 'xz':
            result_pauli = 'xi'
        elif target_pauli == 'xi':
            result_pauli = 'xz'

        elif target_pauli == 'yx':
            result_pauli = 'xy'
        elif target_pauli == 'yy':
            result_pauli = 'xx'
        elif target_pauli == 'yz':
            result_pauli = 'yi'
        elif target_pauli == 'yi':
            result_pauli = 'yz'

        elif target_pauli == 'zx':
            result_pauli = 'ix'
        elif target_pauli == 'zy':
            result_pauli = 'iy'
        elif target_pauli == 'zz':
            result_pauli = 'zz'
        elif target_pauli == 'zi':
            result_pauli = 'zi'

        elif target_pauli == 'ix':
            result_pauli = 'zx'
        elif target_pauli == 'iy':
            result_pauli = 'zy'
        elif target_pauli == 'iz':
            result_pauli = 'iz'
        elif target_pauli == 'ii':
            result_pauli = 'ii'
    elif op_type == 'cnot': # For CNOT: target_pauli=(control qubit, target qubit)
        target_pauli = target_pauli[0] + target_pauli[1]
        if target_pauli == 'xx':
            result_pauli = 'xi'
        elif target_pauli == 'xy':
            result_pauli = 'yz'
        elif target_pauli == 'xz':
            result_pauli = 'yy'
        elif target_pauli == 'xi':
            result_pauli = 'xx'

        elif target_pauli == 'yx':
            result_pauli = 'yi'
        elif target_pauli == 'yy':
            result_pauli = 'xz'
        elif target_pauli == 'yz':
            result_pauli = 'xy'
        elif target_pauli == 'yi':
            result_pauli = 'yx'

        elif target_pauli == 'zx':
            result_pauli = 'zx'
        elif target_pauli == 'zy':
            result_pauli = 'iy'
        elif target_pauli == 'zz':
            result_pauli = 'iz'
        elif target_pauli == 'zi':
            result_pauli = 'zi'

        elif target_pauli == 'ix':
            result_pauli = 'ix'
        elif target_pauli == 'iy':
            result_pauli = 'zy'
        elif target_pauli == 'iz':
            result_pauli = 'zz'
        elif target_pauli == 'ii':
            result_pauli = 'ii'
        else:
            pass
    else:
        pass # Add if needed

    return result_pauli


class qubit_plane_emulator:
    def __init__(self, config, emulate, num_shots):
        # Parameters
        self.config = config
        self.phy_err_rate   = float(config.phy_err_rate)
        self.code_dist      = config.code_dist 
        self.num_pchrow     = config.num_pchrow
        self.num_pchcol     = config.num_pchcol
        self.num_lq         = config.num_lq
        self.num_ucrow      = self.config.num_ucrow
        self.num_uccol      = self.config.num_uccol
        self.emulate_mode   = emulate
        self.num_shots      = num_shots
        
        # Variables
        self.latest_dq_meas_arr = None
        self.latest_aq_meas_arr = None
        self.op_trace           = None
        ## Stores every gate operations
        self.trace_buffer       = []
        ## Track measurement counts to determine each measurement type in qtexec_unit
        self.count = -1
        self.lq_prob_extract_timing = None
        self.mask_meas_list         = None
        self.inject_no_error_mask   = None

        # Predefined value
        self.ucl_len        = (self.code_dist +1) // 2 # per patch
        self.num_row_dq     = self.num_pchrow * (self.code_dist + 1) +1
        self.num_col_dq     = self.num_pchcol * (self.code_dist + 1) +1
        self.num_row_aq     = self.num_row_dq - 1
        self.num_col_aq     = self.num_col_dq - 1
        self.cx_op          = 'cx'    
        self.x_op           = 'x'    
        self.i_op           = 'i'    
        self.h_op           = 'h'
        self.m_op           = 'm'
        self.h_s_op         = 'h_s'     
        self.sdag_h_op      = 'sdag_h'     
        self.meas_op        = 'meas'  
        self.cz_op          = 'cz'
        self.h_sdag_h_op    = 'h_sdag_h'
        
        # Initialization
        self.cur_error_array_aq = self.build_error_array('aq')
        self.cur_error_array_dq = self.build_error_array('dq')
        self.qc_compose_unit = qc_compose_unit.qc_compose_unit(self.code_dist, self.num_pchrow, self.num_pchcol, self.phy_err_rate, self.emulate_mode)
        self.init_plane_info()
        self.init_mask_meas_list()
        self.init_logical_meas_timing_list()

    def build_error_array(self, qb_type):
        # Initialize error array
        if qb_type == 'aq':
            error_array = np.full((self.num_row_aq, self.num_col_aq), 'i')
        else:
            error_array = np.full((self.num_row_dq, self.num_col_dq), 'i')

        return error_array
    
    def merge_error_array(self, error_array_1_dq, error_array_1_aq, error_array_2_dq, error_array_2_aq):
        # Element-wise merge of two error arrays
        result_dq = self.build_error_array('dq')
        result_aq = self.build_error_array('aq')
        
        for i in range(self.num_row_dq):
            for j in range(self.num_col_dq):
                result_dq[i][j] = merge_pauli(error_array_1_dq[i][j], error_array_2_dq[i][j])

        for i in range(self.num_row_aq):
            for j in range(self.num_col_aq):
                result_aq[i][j] = merge_pauli(error_array_1_aq[i][j], error_array_2_aq[i][j])
                
        return result_dq, result_aq 

    def commute_error_array(self, trace_buffer, error_buffer, prev_error_dq = None, prev_error_aq = None):
        # Commute errors in the error_buffer through the codewords in the trace_buffer
        
        error_dq = error_buffer[0]
        error_aq = error_buffer[1]
        trace = trace_buffer
        if (prev_error_dq is None) and (prev_error_aq is None):
            start_idx = 1
            current_error_dq = error_dq[0]
            current_error_aq = error_aq[0]
        else:
            start_idx = 0
            current_error_dq = prev_error_dq
            current_error_aq = prev_error_aq
        
        for i in range(start_idx, len(trace)-1):
            for op in trace[i]:
                op_type = op[0]
                q1_qb_type = op[1]
                q1_idx = op[2]
                q2_qb_type = op[3]
                q2_idx = op[4]

                if q1_qb_type == 'dq':
                    q1_target_array = current_error_dq
                else:
                    q1_target_array = current_error_aq
                if q2_qb_type == 'dq':
                    q2_target_array = current_error_dq
                else:
                    q2_target_array = current_error_aq

                if op_type == 'cz':
                    target_pauli = apply_commutation('cz', (q1_target_array[q1_idx], q2_target_array[q2_idx]))
                    q1_target_array[q1_idx] = target_pauli[0]
                    q2_target_array[q2_idx] = target_pauli[1]
                    
                elif op_type == 'cnot':
                    if q1_qb_type == 'aq':
                        target_pauli = apply_commutation('cnot', (q1_target_array[q1_idx], q2_target_array[q2_idx]))
                        q1_target_array[q1_idx] = target_pauli[0]
                        q2_target_array[q2_idx] = target_pauli[1]
                    else:
                        target_pauli = apply_commutation('cnot', (q2_target_array[q2_idx], q1_target_array[q1_idx]))
                        q1_target_array[q1_idx] = target_pauli[1]
                        q2_target_array[q2_idx] = target_pauli[0]
                elif op_type == 'cx':
                    pass
                elif op_type == 'x':
                    q1_target_array[q1_idx] = 'i'
                elif op_type == 'i':
                    q1_target_array[q1_idx] = 'i'
                elif op_type == 'h':
                    q1_target_array[q1_idx] = apply_commutation('h', q1_target_array[q1_idx])
                elif op_type == 'h_t':
                    q1_target_array[q1_idx] = apply_commutation('h', q1_target_array[q1_idx])
                    if q1_target_array[q1_idx] == 'x' or q1_target_array[q1_idx] == 'y':
                        raise Exception ("Cannot commute h_t with x or y within Clifford set")
                elif op_type == 'h_s':
                    q1_target_array[q1_idx] = apply_commutation('h', q1_target_array[q1_idx])
                    q1_target_array[q1_idx] = apply_commutation('s', q1_target_array[q1_idx])
                elif op_type == 'sdag_h':
                    q1_target_array[q1_idx] = apply_commutation('sdag', q1_target_array[q1_idx])
                    q1_target_array[q1_idx] = apply_commutation('h', q1_target_array[q1_idx])
                elif op_type == 'meas':
                    pass
                else:
                    pass # Add if needed
            
            current_error_dq, current_error_aq = self.merge_error_array(current_error_dq, current_error_aq, error_dq[i], error_aq[i])

        current_error_dq, current_error_aq = self.merge_error_array(current_error_dq, current_error_aq, error_dq[len(trace)-1], error_aq[len(trace)-1]) # Measurement error
        current_error_dq, current_error_aq = self.merge_error_array(current_error_dq, current_error_aq, error_dq[len(trace)-0], error_aq[len(trace)-0]) # Decoherence error
        
        return current_error_dq, current_error_aq

    def build_result_array(self, qb_type):
        # Initialize measurement result array
        if qb_type == 'aq':
            meas_result_array = np.full((self.num_row_aq, self.num_col_aq), '-')
        else:
            meas_result_array = np.full((self.num_row_dq, self.num_col_dq), '-')

        return meas_result_array

    def append(self, op):
        # Append an operation trace to the trace buffer
        self.trace_buffer.append(op)

        return

    def convert(self, raw_trace):
        # Convert opcodes from TCU into qc_compose_unit.op instances
        # idx format : (patch_row, patch_col, ucl_row, ucl_col, qb_num)

        op_list = []
        for idx, op in np.ndenumerate(raw_trace):
            if not len(op) == 0:
                # Decode indices
                patch_idx = (idx[0], idx[1])
                ucl_idx = (idx[2], idx[3])
                if idx[4] <= 3:
                    qb_num = idx[4]
                    qb_type = 'dq'
                else:
                    if idx[4] == 4:
                        qb_num = 0
                    elif idx[4] == 5:
                        qb_num = 3
                    elif idx[4] == 6:
                        qb_num = 1
                    elif idx[4] == 7:
                        qb_num = 2
                    else:
                        raise Exception ("Invalid codeword")
                    qb_type = 'aq'
                    
                # Convert two qubit gates
                if op[0:2] == self.cz_op:
                    if qb_type == 'aq':
                        pass
                    else:
                        ucl_row_off = 0
                        ucl_col_off = 0
                        if idx[4] == 0 or idx[4] == 1:
                            if int(op[2]) == 5 or int(op[2]) == 7:
                                ucl_row_off = -1
                        
                        if idx[4] == 0 or idx[4] == 2:
                            if int(op[2]) == 5 or int(op[2]) == 6:
                                ucl_col_off = -1

                        if idx[4] == 5 or idx[4] == 7:
                            if int(op[2]) == 0 or int(op[2]) == 1:
                                ucl_row_off = +1
                        
                        if idx[4] == 5 or idx[4] == 6:
                            if int(op[2]) == 0 or int(op[2]) == 2:
                                ucl_col_off = +1

                        target_patch_idx = (idx[0] + (idx[2] + ucl_row_off) // self.ucl_len, idx[1] + (idx[3] + ucl_col_off) // self.ucl_len)
                        target_ucl_idx = ((idx[2] + ucl_row_off) % self.ucl_len, (idx[3] + ucl_col_off) % self.ucl_len)
                        if int(op[2]) <= 3:
                            target_qb_num = int(op[2])
                            target_qb_type = 'dq'
                        else:
                            if int(op[2]) == 4:
                                target_qb_num = 0
                            elif int(op[2]) == 5:
                                target_qb_num = 3
                            elif int(op[2]) == 6:
                                target_qb_num = 1
                            elif int(op[2]) == 7:
                                target_qb_num = 2
                            else:
                                raise Exception ("Invalid codeword")
                            target_qb_type = 'aq'
                        op = qc_compose_unit.op('cz', patch_idx, ucl_idx, qb_type, qb_num, \
                            target_patch_idx, target_ucl_idx, target_qb_type, target_qb_num)
                        op_list.append(op)
                
                # Convert single qubit gates
                else:
                    if op == self.cx_op:
                        row, col = self.qc_compose_unit.get_qb_idx(patch_idx, ucl_idx, qb_type, qb_num)
                        if qb_type == 'aq':
                            latest_meas_result = self.latest_aq_meas_arr[row][col]
                        else: # 'dq'
                            latest_meas_result = self.latest_dq_meas_arr[row][col]
                            
                        if latest_meas_result == '0' or latest_meas_result == '-':
                            op = qc_compose_unit.op('i', patch_idx, ucl_idx, qb_type, qb_num)
                        else: # '1'
                            op = qc_compose_unit.op('x', patch_idx, ucl_idx, qb_type, qb_num)
                    elif op == self.h_op:
                        op = qc_compose_unit.op('h', patch_idx, ucl_idx, qb_type, qb_num)
                    elif op == self.m_op:
                        op = qc_compose_unit.op('h_t', patch_idx, ucl_idx, qb_type, qb_num)
                    elif op == self.h_s_op: #
                        op = qc_compose_unit.op('h_s', patch_idx, ucl_idx, qb_type, qb_num)
                    elif op == self.sdag_h_op: #
                        op = qc_compose_unit.op('sdag_h', patch_idx, ucl_idx, qb_type, qb_num)
                    elif op == self.meas_op:
                        op = qc_compose_unit.op('meas', patch_idx, ucl_idx, qb_type, qb_num)
                    elif op == self.h_sdag_h_op:
                        op = qc_compose_unit.op('h_sdag_h', patch_idx, ucl_idx, qb_type, qb_num)
                    else:
                        pass # add if other gates are needed
                    op_list.append(op)

        return op_list

    def revert (self):
        # Revert qc_compose_unit.op instances into opcodes from TCU
        trace_buffer_idx = []
        for trace in self.trace_buffer:
            trace_idx = []
            for op in trace:
                op_type = op.op_type
                if op_type == 'cz':
                    q1_idx, q2_idx = op.get()
                    q1_qb_type = q1_idx[2]
                    q2_qb_type = q2_idx[2]
                    q1_idx = self.qc_compose_unit.get_qb_idx(*q1_idx)
                    q2_idx = self.qc_compose_unit.get_qb_idx(*q2_idx)
                else:
                    q1_idx = op.get()
                    q1_qb_type = q1_idx[2]
                    q2_qb_type = None
                    q1_idx = self.qc_compose_unit.get_qb_idx(*q1_idx)
                    q2_idx = None
                trace_idx.append((op_type, q1_qb_type, q1_idx, q2_qb_type, q2_idx))
            trace_buffer_idx.append(trace_idx)
        
        return trace_buffer_idx

    def meas_in_op(self, op):
        # Check if measurement operations exist in the operation list
        op_types = [o.op_type for o in op]
        return ('meas' in op_types)

    def run(self):
        # Run quantum circuit and return measurement results
        
        self.qc_compose_unit.clear_error_trace()

        # Determine whether or not to inject errors
        if self.count in self.mask_meas_list:
            inject_no_error = True
        else:
            inject_no_error = False
        
        # Prepare STIM simulator with buffered traces
        meas_qb_list, meas_qb_idx, meas_qb_type = self.qc_compose_unit.append_trace(self.trace_buffer, inject_no_error=inject_no_error, inject_no_error_mask = self.inject_no_error_mask)
        
        # Get traces for injected errors
        error_trace = self.qc_compose_unit.get_error_trace()
        
        # Check measurement type
        if 'aq' in meas_qb_type:
            aq_result_valid = True
        else:
            aq_result_valid = False
        if 'dq' in meas_qb_type:
            dq_result_valid = True
        else:
            dq_result_valid = False
        
        # Initialize measurement result arrays
        aq_result_array = self.build_result_array('aq')
        dq_result_array = self.build_result_array('aq')
        
        # Emulate measurement results so that the large-scale simulation is available
        # FIXME: Is it better to delete this sentence? - A stat for the EDU latency is still valid as emulation preserves information of injected errors
        if self.emulate_mode:
            self.op_trace = self.revert()
            new_error_dq, new_error_aq = self.commute_error_array(self.op_trace, error_trace, self.cur_error_array_dq, self.cur_error_array_aq)
            self.cur_error_array_dq = new_error_dq
            self.cur_error_array_aq = new_error_aq
            for idx, qb_type in zip(meas_qb_idx, meas_qb_type):
                if qb_type == 'aq':
                    qb_err = self.cur_error_array_aq[idx]
                    if qb_err == 'x' or qb_err == 'y':
                        aq_result_array[idx[0]][idx[1]] = 1
                    else:
                        aq_result_array[idx[0]][idx[1]] = 0
                else: # 'dq'
                    qb_err = self.cur_error_array_dq[idx]
                    if qb_err == 'x' or qb_err == 'y':
                        dq_result_array[idx[0]][idx[1]] = 1
                    else:
                        dq_result_array[idx[0]][idx[1]] = 0          

        # Run actual simulation
        else:
            # Find a probability of each physical qubit measurement
            # Determine measurement results with calculated probabilities
            qc_sup = self.qc_compose_unit.get_qc()
            for qb, idx, qb_type in zip(meas_qb_list, meas_qb_idx, meas_qb_type):
                merged_prob, selected_result = ray.get(qc_sup.get_prob.remote(qb))
                qc_sup.project_qc.remote(qb, selected_result)
                
                if qb_type == 'aq':
                    aq_result_array[idx[0]][idx[1]] = int(selected_result)
                else: # 'dq'
                    dq_result_array[idx[0]][idx[1]] = int(selected_result)

            self.count += 1
            self.count %= (self.code_dist *3 + 4)
        
        # Flush buffer
        self.trace_buffer = []
            
        return aq_result_array, dq_result_array, aq_result_valid, dq_result_valid

    def extract_lq_probabilities (self):
        # Peek probabilities of logical qubit measurement result
        
        if self.emulate_mode:
            lq_state_distribution = None
            lq_state_extracted = False
        else:
            # Measure all logical qubits simultaneously for self.num_shots times
            if (self.count in self.lq_prob_extract_timing):
                target_lop_list = ['X','X'] + ['X'] * (self.num_lq-2)
                lq_state_distribution_x = self.peek_logical_qubits_state(target_lop_list, num_shots = self.num_shots)
                target_lop_list = ['Y','Y'] + ['Y'] * (self.num_lq-2)
                lq_state_distribution_y = self.peek_logical_qubits_state(target_lop_list, num_shots = self.num_shots)
                target_lop_list = ['Z','Z'] + ['Z'] * (self.num_lq-2)
                lq_state_distribution_z = self.peek_logical_qubits_state(target_lop_list, num_shots = self.num_shots)
            else:
                lq_state_distribution_x = None
                lq_state_distribution_y = None
                lq_state_distribution_z = None
            lq_state_extracted = (self.count in self.lq_prob_extract_timing)
            lq_state_distribution = (lq_state_distribution_x, lq_state_distribution_y, lq_state_distribution_z)
                
        return lq_state_distribution, lq_state_extracted
  
    def peek_logical_qubits_state(self, target_lop_list, num_shots = 8192):
        prob = self.qc_compose_unit.peek_multi_logical_qubits(target_lop_list, self.lq_pchidx, self.lq_pchtype, num_shots)
        return prob

    def init_mask_meas_list(self):
        # FIXME - No errors for
        mask_meas_list = [0, self.code_dist+1] # first ESM rounds
        mask_meas_list += [self.code_dist-1, 2*self.code_dist, 3*self.code_dist+1] # last ESM rounds
        mask_meas_list += [2*self.code_dist+1] # MEAS_INTMD
                
        # FIXME - remove errors that occur in long stabilizers
        inject_no_error_mask = [] # (patch, ucl, qb_type, qb_idx)
        inject_no_error_mask += [((0, 0), (self.num_ucrow-1, self.num_uccol-1), 'aq', 3)]
        inject_no_error_mask += [((1, 0), (0, self.num_uccol-1), 'aq', 1)]
        inject_no_error_mask += [((0, 1), (self.num_ucrow-1, ucl_col), 'aq', qb_idx) for ucl_col in range(self.num_uccol) for qb_idx in [2,3]]
        inject_no_error_mask += [((1, 1), (0, ucl_col), 'dq', qb_idx) for ucl_col in range(self.num_uccol) for qb_idx in [0,1]]
        inject_no_error_mask += [((1, 1), (0, ucl_col), 'aq', qb_idx) for ucl_col in range(self.num_uccol) for qb_idx in [0,1]]
        inject_no_error_mask += [((1, 2), (0, 0), 'dq', 0)]
        
        self.mask_meas_list = mask_meas_list
        self.inject_no_error_mask = inject_no_error_mask
        
        return
        
    def init_logical_meas_timing_list (self):
        lq_prob_extract_timing = [self.code_dist, self.code_dist *3 + 3]
        self.lq_prob_extract_timing = lq_prob_extract_timing
        
        return

    def init_plane_info (self):
        self.lq_pchidx = []
        self.lq_pchtype = []
        for i in range(self.num_lq):
            if i == 0:
                self.lq_pchidx.append((1,0))
                self.lq_pchtype.append('zb')
            elif i == 1:
                self.lq_pchidx.append((1,1))
                self.lq_pchtype.append('mb')
            elif i == self.num_lq -1:
                self.lq_pchidx.append((1,1+(i//2)))
                self.lq_pchtype.append('x')
            elif i % 2 == 0:
                self.lq_pchidx.append((0,1+(i//2)))
                self.lq_pchtype.append('m')
            else:
                self.lq_pchidx.append((2,1+(i//2)))
                self.lq_pchtype.append('m')
  
# Helper functions for qtexec_unit
def convert_idx_dim(code_distance, qb_type, row, col):
    patch_size = (code_distance + 1)
    ucl_size = 2
    patch_idx = (row // patch_size, col // patch_size)
    ucl_idx = ((row % patch_size) // ucl_size, (col % patch_size) // ucl_size)
    qb_idx = ((row % patch_size) % ucl_size) * 2 + ((col % patch_size) % ucl_size)
    if qb_type == 'dq':
        pass
    else:
        if qb_idx == 0:
            qb_idx = 4
        elif qb_idx == 1:
            qb_idx = 6
        elif qb_idx == 2:
            qb_idx = 7
        elif qb_idx == 3:
            qb_idx = 5
        else:
            raise Exception ("Invalid qb_idx")

    return patch_idx[0], patch_idx[1], ucl_idx[0], ucl_idx[1], qb_idx   

class qtexec_unit:
    def __init__(self, unit_stat, config, emulate, num_shots):
        #
        self.config         = config
        self.unit_stat      = unit_stat
        self.init_stats()

        # Parameters
        self.code_dist      = config.code_dist 
        self.num_pchrow     = config.num_pchrow
        self.num_pchcol     = config.num_pchcol
        self.num_ucrow      = config.num_ucrow
        self.num_uccol      = config.num_uccol
        self.num_qb_per_uc  = config.num_qb_per_uc
        self.meas_ns        = config.meas_ns   
        self.meas_cycle     = math.ceil(self.meas_ns*1)
        
        self.emulate_mode   = emulate
        self.num_shots      = num_shots

        self.emulator = qubit_plane_emulator(self.config, self.emulate_mode, self.num_shots)
        
        # Wires
        ## Input wire
        self.input_cwd_array = None 
        self.input_valid = None
        self.input_current_cycle = None
        
        # Registers
        ## Output register
        self.output_dq_meas_mem = self.emulator.build_result_array('dq')
        self.output_aq_meas_mem = self.emulator.build_result_array('aq')
        self.output_dqmeas_valid = None
        self.output_aqmeas_valid = None
        
        ## State register
        self.op_array = self.input_cwd_array
        self.op = None
        self.done = False 
        
        # Temporarily store measurement results before they are visible to outside
        self.dq_meas_mem = {} # {visible_cycle: measurement_result}
        self.aq_meas_mem = {} # {visible_cycle: measurement_result}

        # To find and store logical qubit probabilities
        self.lq_state_distribution = None
        self.lq_state_extracted = False
        self.lq_state_dist_list_x = list()
        self.lq_state_dist_list_y = list()
        self.lq_state_dist_list_z = list()
        self.debug_lq_pchidx = None
        self.debug_lq_pchtype = None
        self.cycle = 0


    ### Stat function ###
    def init_stats(self):
        # Data trnasfer
        ### to EDU
        self.unit_stat.data_transfer["EDU"] = {
                "num_eff": [], 
                "cycle": [],
                "bw": 1,
                "last_cyc": 0
                }
        ### to LMU
        self.unit_stat.data_transfer["LMU"] = {
                "num_eff": [], 
                "cycle": [],
                "bw": 1,
                "last_cyc": 0
                }
        return

    def update_stats (self, sim_cycle):
        # data_transfer
        if self.output_aqmeas_valid: 
            cycle = sim_cycle - self.unit_stat.data_transfer["EDU"]["last_cyc"]
            self.unit_stat.data_transfer["EDU"]["num_eff"].append(self.calc_measresult_num()[0])
            self.unit_stat.data_transfer["EDU"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["EDU"]["last_cyc"] = sim_cycle

        if self.output_dqmeas_valid: 
            cycle = sim_cycle - self.unit_stat.data_transfer["LMU"]["last_cyc"]
            self.unit_stat.data_transfer["LMU"]["num_eff"].append(self.calc_measresult_num()[1])
            self.unit_stat.data_transfer["LMU"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["LMU"]["last_cyc"] = sim_cycle

        else:
            pass
        return

    def calc_measresult_num (self):
        num_aq = 0
        for _, res in np.ndenumerate(self.output_aq_meas_mem):
            if res == '0' or res == '1':
                num_aq += 1
        num_dq = 0
        for _, res in np.ndenumerate(self.output_dq_meas_mem):
            if res == '0' or res == '1':
                num_dq += 1
        
        return (num_aq, num_dq)
    
    # Sequential logic        
    def update(self, sim_cycle=0):
        self.update_stats(sim_cycle)

        # Accumulate an incoming codeword array from TCU when the valid signal is set
        if self.input_valid:
            self.op_array = self.input_cwd_array
            self.op = self.emulator.convert(self.op_array)
            self.emulator.append(self.op)
        else:
            self.op_array = None 
            self.op = None
        
        # Run quantum circuits with stored quantum circuits only if the measurement operation is detected in the codeword array
        if self.input_valid and self.emulator.meas_in_op(self.op):
            aq_result, dq_result, aqmeas_valid, dqmeas_valid = self.emulator.run()
            self.lq_state_distribution, self.lq_state_extracted = self.emulator.extract_lq_probabilities()
        else:
            aq_result = None
            dq_result = None
            aqmeas_valid = False
            dqmeas_valid = False
        
        # If measurement results of both ancilla qubits and data qubits exist, pass measurement results of data qubits to adjacent ancilla qubits
        if aqmeas_valid and dqmeas_valid:
            for (i,j), val in np.ndenumerate(dq_result):
                if val != '-':
                    # Pass dq result to leftbottom ancilla
                    aq_result[i][j-1] = val
                    aq_result[i-1][j-1] = '0'
                    dq_result[i][j] = '0'
                else:
                    pass
            
            dqmeas_valid = False
        
        # Store measurement results of ancilla qubits with cycle information
        if aqmeas_valid:
            self.aq_meas_mem[self.input_current_cycle + self.meas_cycle - 1] = aq_result

        # Store measurement results of data qubits with cycle information
        if dqmeas_valid:
            self.dq_meas_mem[self.input_current_cycle + self.meas_cycle - 1] = dq_result

        # Pass measurement results to following units when the measurement time is elapsed
        self.output_aqmeas_valid = False
        self.output_dqmeas_valid = False
        
        ## ancilla qubit measurement results
        for cycle in self.aq_meas_mem:
            if self.input_current_cycle >= cycle:
                self.output_aq_meas_mem = self.aq_meas_mem[cycle]
                self.emulator.latest_dq_meas_arr = self.output_aq_meas_mem
                
                del self.aq_meas_mem[cycle]
                self.output_aqmeas_valid = True
                break

        ## data qubit measurement results
        for cycle in self.dq_meas_mem:
            if self.input_current_cycle >= cycle:
                dq_meas_mem_2d = self.dq_meas_mem[cycle]

                output_dq_meas_mem_5d = np.zeros((self.num_pchrow, self.num_pchcol, self.num_ucrow, self.num_uccol, (self.num_qb_per_uc // 2)), dtype=int)
                for i in range(self.num_pchrow * (self.code_dist + 1)):
                    for j in range(self.num_pchcol * (self.code_dist + 1)):
                        if dq_meas_mem_2d[i][j] == '1':
                            output_dq_meas_mem_5d[convert_idx_dim(self.code_dist,'dq',i,j)] = 1
                        else:
                            output_dq_meas_mem_5d[convert_idx_dim(self.code_dist,'dq',i,j)] = 0
                del self.dq_meas_mem[cycle]
                
                self.emulator.latest_dq_meas_arr = dq_meas_mem_2d
                self.output_dq_meas_mem = output_dq_meas_mem_5d
                self.output_dqmeas_valid = True
                break

        # Set done signal if every lists for storing measurement results are empty
        self.done = (self.op_array is None) and (not self.dq_meas_mem) and (not self.aq_meas_mem)

        return

    def save_current_logical_state (self):
        # After initialization or PPR, store logical qubit probabilities extracted from emulator
        if self.lq_state_extracted:
            self.lq_state_dist_list_x.append(self.lq_state_distribution[0])
            self.lq_state_dist_list_y.append(self.lq_state_distribution[1])
            self.lq_state_dist_list_z.append(self.lq_state_distribution[2])

            self.cur_lq_pchidx = self.emulator.lq_pchidx
            self.cur_lq_pchtype = self.emulator.lq_pchtype

            self.lq_state_extracted = False

    # Debug
    def debug(self):
        return

