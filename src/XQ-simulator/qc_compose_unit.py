import numpy as np
import stim
import ray
import sys

SUPPORTED_OP_TYPES = {'h','cz','h_t','meas','x','i','h_s','sdag_h','cnot', 'cx', 'z', 'y', 'h_sdag_h'} # all cx was replaced to 'i' or 'x' at previous stage
SUPPORTED_QB_TYPES = {'dq','aq'}
SPLIT_PER_M = 5 # 3, 5

UCL_SIZE = 2

class op:
    '''
    Patch layout
        ucl[0][0] ucl[0][1] ... ucl[0][n]
        ucl[1][0] ucl[1][1] ... ucl[1][n]
        ...       ...       ... ...
        ucl[n][0] ucl[n][1] ... ucl[n][n]
        where n == (d-1)/2 (d is odd)

    Unit cell layout
        dq[0]    dq[1]
            aq[0]     aq[1]
        dq[2]    dq[3]
            aq[2]     aq[3]

    Mapping
        [dq[0],dq[1],dq[2],dq[3],x1,x2,z1,z2] -> [dq[0],dq[1],dq[2],dq[3],aq[0],aq[3],aq[1],aq[2]]
    '''

    # op_type = None
    # patch_idx_1 = None # (row, col)
    # ucl_idx_1 = None # (row, col)
    # qb_type_1 = None # dq or aq
    # qb_idx_1 = None # 0, 1, 2, 3

    # patch_idx_2 = None # (row, col)
    # ucl_idx_2 = None # (row, col)
    # qb_type_2 = None # dq or aq
    # qb_idx_2 = None # 0, 1, 2, 3

    def __init__(self, op_type, patch_idx_1, ucl_idx_1, qb_type_1, qb_idx_1, \
        patch_idx_2 = None, ucl_idx_2 = None, qb_type_2 = None, qb_idx_2 = None) -> None:
        
        # Exception handling
        
        if not op_type in SUPPORTED_OP_TYPES:
            raise Exception("Invalid operation type")
        
        if patch_idx_1 == None or ucl_idx_1 == None or qb_idx_1 == None:
            raise Exception("Invalid qubit1 index")

        
        if not qb_type_1 in SUPPORTED_QB_TYPES:
            raise Exception("Invalid qubit1 type. Supported types: {}".format(SUPPORTED_QB_TYPES))

        if op_type == 'cz' or op_type == 'cnot':
            if patch_idx_2 == None or ucl_idx_2 == None or qb_idx_2 == None:
                raise Exception("Invalid qubit2 index")
            if not qb_type_2 in SUPPORTED_QB_TYPES:
                raise Exception("Invalid qubit2 type. Supported types: {}".format(SUPPORTED_QB_TYPES))

        self.op_type = op_type
        self.patch_idx_1 = patch_idx_1
        self.ucl_idx_1 = ucl_idx_1
        self.qb_type_1 = qb_type_1
        self.qb_idx_1 = qb_idx_1

        if op_type == 'cz' or op_type == 'cnot':
            self.patch_idx_2 = patch_idx_2
            self.ucl_idx_2 = ucl_idx_2
            self.qb_type_2 = qb_type_2
            self.qb_idx_2 = qb_idx_2
        else:
            pass

        return

    def get(self):
        if self.op_type == 'cz' or self.op_type == 'cnot':
            return (self.patch_idx_1, self.ucl_idx_1, self.qb_type_1, self.qb_idx_1), (self.patch_idx_2, self.ucl_idx_2, self.qb_type_2, self.qb_idx_2)
        else:
            return (self.patch_idx_1, self.ucl_idx_1, self.qb_type_1, self.qb_idx_1)


def merge_one_prob(val_list, coeff):
    result = sum(v*c for v, c in zip(val_list, coeff))
    return result

def merge_prob(val_list, coeff):
    num_split = int(np.rint(np.log(len(val_list)) / np.log(SPLIT_PER_M)))
    cur_list = val_list
    
    for n in range(num_split):
        next_list = [merge_one_prob(cur_list[SPLIT_PER_M*i:SPLIT_PER_M*(i+1)], coeff)\
                                for i in range (SPLIT_PER_M ** (num_split - 1 - n))]
        cur_list = next_list

    result = cur_list[0]

    return result

def merge_prob_multi(val_list, coeff, num_lq):
    prob_key = {format(k, '0'+str(num_lq)+'b') for k in range(2 ** num_lq)}
    merged_prob = {}
    for state in prob_key:
        cur_list = [val.get(state, 0) for val in val_list]
        merged_prob[state] = merge_prob(cur_list, coeff)

    return merged_prob

def select_result (merged_prob):
    # parity = [0, 1]
    parity = [False, True]
    if merged_prob < 0:
        merged_prob = 0
    elif merged_prob > 1:
        merged_prob = 1
    
    probabilities = [merged_prob, 1-merged_prob]
    
    return np.random.choice(parity, size=1, p=probabilities)[0]

@ray.remote
class qc_worker:
    def __init__(self, coeff, initial_circuit, num_qb, qc_worker_id):
        (self.num_row_dq, self.num_col_dq, self.num_row_aq, self.num_col_aq) = num_qb
        self.qc_worker_id = qc_worker_id
        
        self.qc_list = [stim.TableauSimulator()]
        
        self.qc_list[0].do(initial_circuit)
            
        self.coeff = coeff

    def split_qc(self):
        self.qc_list = [qc if i == 0 else qc.copy() for qc in self.qc_list for i in range(SPLIT_PER_M)]
        return
    
    def apply_qc(self, op_list):
        for qc_idx, qc in enumerate(self.qc_list):
            qc.do(op_list[qc_idx % SPLIT_PER_M])
        return
    
    def get_prob(self, qb):
        num_qb = len(self.qc_list[0].current_inverse_tableau())
        target_paulistring = stim.PauliString("I"* qb + "Z" + "I"* (num_qb - qb - 1))
        prob_0_list = [(0.5 + 0.5*qc.peek_observable_expectation(target_paulistring)) for qc in self.qc_list]
        merged_prob = merge_prob(prob_0_list, self.coeff)
        return merged_prob
    
    def get_prob_multiqb(self, lop_qb_list, target_lop_list, num_shots):
        prob_list = [dict() for _ in self.qc_list]
        num_lq = len(target_lop_list) - target_lop_list.count('I')
        
        for _ in range(num_shots):
            qc_list_copy = [qc.copy() for qc in self.qc_list]
            
            state_list = [''] * len(qc_list_copy)
            for lop_qb, target_lop in zip(lop_qb_list, target_lop_list):
                if target_lop == 'I':
                    continue
                
                # Change basis
                lop_qb_x = lop_qb[0]
                lop_qb_z = lop_qb[1]
                if target_lop == 'X': # 
                    [qc.h(*lop_qb_x) for qc in qc_list_copy]
                    meas_qb = lop_qb_x
                elif target_lop == 'Y':
                    lop_qb_y = list(set(lop_qb_x).intersection(lop_qb_z))
                    [qc.s_dag(*lop_qb_y) for qc in qc_list_copy]
                    [qc.h(*lop_qb_x) for qc in qc_list_copy]
                    meas_qb = list(dict.fromkeys(lop_qb_x + lop_qb_z))
                elif target_lop == 'Z':
                    meas_qb = lop_qb_z
                elif target_lop == 'HX': #
                    change_basis_qb = list(dict.fromkeys(lop_qb_x + lop_qb_z))
                    [qc.h(*change_basis_qb) for qc in qc_list_copy]
                    [qc.h(*lop_qb_x) for qc in qc_list_copy]
                    meas_qb = lop_qb_x
                elif target_lop == 'HY':
                    lop_qb_y = list(set(lop_qb_x).intersection(lop_qb_z))
                    meas_qb = list(dict.fromkeys(lop_qb_x + lop_qb_z))
                    [qc.h(*meas_qb) for qc in qc_list_copy]
                    
                    [qc.s_dag(*lop_qb_y) for qc in qc_list_copy]
                    [qc.h(*lop_qb_x) for qc in qc_list_copy]
                meas_result = [qc.measure_many(*meas_qb) for qc in qc_list_copy]
                lo_meas_result = [str(meas.count(True) % 2) for meas in meas_result]
                state_list = [s + l for (s,l) in zip(state_list, lo_meas_result)]
            
            for prob, state in zip(prob_list, state_list):
                try:
                    prob[state] += (1 / num_shots)
                except:
                    prob[state] = (1 / num_shots)
                
        merged_prob = merge_prob_multi(prob_list, self.coeff, num_lq)
        
        return merged_prob
    
    def project_qc(self, qb, target_value):
        for qc in self.qc_list:
            result, kickback = qc.measure_kickback(qb)
            if result == target_value:
                pass
            else:
                if kickback is None:
                    pass
                else:
                    qc.do(kickback)
        return
    
    
@ray.remote
class qc_supervisor:
    def __init__(self, initial_num_split, initial_fresh_m_idx, num_qb): # num_threads == 5 ** initial_num_split
        (self.num_row_dq, self.num_col_dq, self.num_row_aq, self.num_col_aq) = num_qb
        
        num_qc_worker = pow(SPLIT_PER_M, initial_num_split)
        op_list = [stim.Circuit() for _ in range(num_qc_worker)]
        
        if SPLIT_PER_M == 3: # single magic state per 3 splits
            self.coeff = (
                        np.sqrt(2)/2,
                        1/2,
                        (1-np.sqrt(2))/2
            )
            
            q1 = initial_fresh_m_idx
            for iter_split in range(initial_num_split -1,-1,-1):
                for i, circ in enumerate(op_list):
                    circ.append_operation('H', [q1])
                    
                    if (i // pow(SPLIT_PER_M, iter_split)) % SPLIT_PER_M == 0:
                        pass
                    elif (i // pow(SPLIT_PER_M, iter_split)) % SPLIT_PER_M == 1:
                        circ.append_operation('S', [q1])
                    elif (i // pow(SPLIT_PER_M, iter_split)) % SPLIT_PER_M == 2:
                        circ.append_operation('S_DAG', [q1])
                    
                q1 += 1
        elif SPLIT_PER_M == 5: # two magic state per 5 splits
            self.coeff = (
                        0.5-0.5*np.sqrt(2),  # E2
                        0.5-0.25*np.sqrt(2), # K2
                        -0.25*np.sqrt(2),    # K2 bar
                        0.5*np.sqrt(2),      # ++
                        0.5*np.sqrt(2)       # 00
            )
            
            q1 = initial_fresh_m_idx
            q2 = initial_fresh_m_idx +1
            for iter_split in range(initial_num_split -1,-1,-1):
                for i, circ in enumerate(op_list):
                    if (i // pow(SPLIT_PER_M, iter_split)) % SPLIT_PER_M == 0:
                        circ.append_operation('H', [q1])
                        circ.append_operation('CNOT', [q1,q2])
                    elif (i // pow(SPLIT_PER_M, iter_split)) % SPLIT_PER_M == 1:
                        circ.append_operation('H', [q1])
                        circ.append_operation('H', [q2])
                        circ.append_operation('CZ', [q1,q2])
                    elif (i // pow(SPLIT_PER_M, iter_split)) % SPLIT_PER_M == 2:
                        circ.append_operation('H', [q1])
                        circ.append_operation('H', [q2])
                        circ.append_operation('CZ', [q1,q2])
                        circ.append_operation('X', [q1])
                        circ.append_operation('X', [q2])
                    elif (i // pow(SPLIT_PER_M, iter_split)) % SPLIT_PER_M == 3:
                        circ.append_operation('H', [q1])
                        circ.append_operation('H', [q2])
                    else:
                        pass
                    
                    circ.append_operation('S_DAG', [q1])
                    circ.append_operation('S_DAG', [q2])
                    circ.append_operation('H', [q1])
                    circ.append_operation('H', [q2])
                
                q1 += 2
                q2 += 2
        else:
            raise Exception("SPLIT_PER_M other than 3, 5 are currently not supported")

        self.qc_worker_list = [qc_worker.remote(self.coeff, circ, num_qb, op_list.index(circ)) for circ in op_list]
        
    def split_qc(self):
        [qc_wk.split_qc.remote() for qc_wk in self.qc_worker_list]
        return
    
    def apply_qc(self, op_list):
        [qc_wk.apply_qc.remote(op_list) for qc_wk in self.qc_worker_list]
        return
    
    def get_prob(self, qb):
        prob_0_list = ray.get([qc_wk.get_prob.remote(qb) for qc_wk in self.qc_worker_list])
        merged_prob = merge_prob(prob_0_list, self.coeff)
        selected_result = select_result(merged_prob)
        return merged_prob, selected_result

    def get_prob_multiqb(self, lop_qb_list, target_lop_list, num_shots):
        prob_list = ray.get([qc_wk.get_prob_multiqb.remote(lop_qb_list, target_lop_list, num_shots) for qc_wk in self.qc_worker_list])
        num_lq = len(target_lop_list) - target_lop_list.count('I')
        merged_prob = merge_prob_multi(prob_list, self.coeff, num_lq)
        return merged_prob

    def project_qc(self, qb, target_value):
        [qc_wk.project_qc.remote(qb, target_value) for qc_wk in self.qc_worker_list]
        return
    
class qc_compose_unit:
    def __init__ (self, code_distance, num_row_patch, num_col_patch, physical_error_rate, emulate_mode):
        self.emulate_mode = emulate_mode
        self.initial_num_split = 0
        self.physical_error_rate = physical_error_rate
        self.code_distance = code_distance

        num_row_dq = num_row_patch * (code_distance + 1) +1
        num_col_dq = num_col_patch * (code_distance + 1) +1
        num_row_aq = num_row_dq - 1
        num_col_aq = num_col_dq - 1
        self.num_row_dq = num_row_dq
        self.num_col_dq = num_col_dq
        self.num_row_aq = num_row_aq
        self.num_col_aq = num_col_aq

        # Physical qubit array
        self.dq_array = np.arange(0,num_row_dq*num_col_dq).reshape(num_row_dq, -1)
        self.aq_array = np.arange(num_row_dq*num_col_dq, num_row_dq*num_col_dq + num_row_aq*num_col_aq).reshape(num_row_aq, -1)
        
        # list of arrays that track injected errors
        self.error_trace_dq = []
        self.error_trace_aq = []

        self.op_list = [stim.Circuit() for _ in range(SPLIT_PER_M)]
        
        self.fresh_m_idx = num_row_dq*num_col_dq + num_row_aq*num_col_aq
        self.num_fresh_m = 2*self.initial_num_split
        self.num_split = self.initial_num_split
        
        if self.emulate_mode:
            self.qc_sup = qc_supervisor.remote(0, self.fresh_m_idx, 
                (self.num_row_dq, self.num_col_dq, self.num_row_aq, self.num_col_aq))
        else:
            self.qc_sup = qc_supervisor.remote(self.initial_num_split, self.fresh_m_idx, 
                (self.num_row_dq, self.num_col_dq, self.num_row_aq, self.num_col_aq))
        return

    def get_qubit(self, patch_idx, ucl_idx, qb_type, qb_idx):

        row, col = self.get_qb_idx(patch_idx, ucl_idx, qb_type, qb_idx)

        # Exception handling
        num_row_dq = self.num_row_dq
        num_col_dq = self.num_col_dq
        num_row_aq = self.num_row_aq
        num_col_aq = self.num_col_aq
        if (qb_type == 'dq' and (num_row_dq < row or num_col_dq < col)):
            raise Exception("Not enough dq_array size", (num_row_dq, num_col_dq), (row, col))
        elif qb_type == 'aq' and (num_row_aq < row or num_col_aq < col):
            raise Exception("Not enough aq_array size", (num_row_dq, num_col_dq), (row, col))
        
        if qb_type == 'dq':
            qb = self.dq_array[row][col]
        else: # aq
            qb = self.aq_array[row][col]

        return qb

    def get_qb_idx(self, patch_idx, ucl_idx, qb_type, qb_idx):

        patch_size = (self.code_distance + 1)
        ucl_size = UCL_SIZE

        row = patch_size * patch_idx[0] + ucl_size * ucl_idx[0] + (qb_idx // 2)
        col = patch_size * patch_idx[1] + ucl_size * ucl_idx[1] + (qb_idx % 2)            

        return row, col

    def split_qc(self):
        self.qc_sup.split_qc.remote()
        
        self.num_split += 1
        return

    def get_qc(self):
        return self.qc_sup
    
    def get_lop_qb (self, target_pchidx, pchtype):
        pchrow, pchcol = target_pchidx
        
        if pchtype == 'x':
            qb_lop_x = [self.dq_array[i][j] \
                for i in [(pchrow + 1) * (self.code_distance + 1) - 1] \
                for j in range((pchcol) * (self.code_distance + 1) + 1, (pchcol + 1) * (self.code_distance + 1))]
            qb_lop_z = [self.dq_array[i][j] \
                for i in range((pchrow) * (self.code_distance + 1) + 1, (pchrow + 1) * (self.code_distance + 1)) \
                for j in [(pchcol) * (self.code_distance + 1) + 1]]
        elif pchtype == 'mb':
            qb_lop_x = [self.dq_array[i][j] \
                for i in [(pchrow + 1) * (self.code_distance + 1) - 1] \
                for j in range((pchcol) * (self.code_distance + 1) + 1, (pchcol + 1) * (self.code_distance + 1))]
            qb_lop_z = [self.dq_array[i][j] \
                for i in range((pchrow -1) * (self.code_distance + 1) + 1, (pchrow) * (self.code_distance + 1)) \
                for j in [(pchcol) * (self.code_distance + 1) + 1]] + \
                    [self.dq_array[i][j] \
                for i in range((pchrow) * (self.code_distance + 1) + 1, (pchrow + 1) * (self.code_distance + 1)) \
                for j in [(pchcol) * (self.code_distance + 1) + 1]]
        elif pchtype == 'zb':
            qb_lop_x = [self.dq_array[i][j] \
                for i in range((pchrow - 1) * (self.code_distance + 1) +1, (pchrow) * (self.code_distance + 1) +1) \
                for j in [(pchcol + 1) * (self.code_distance + 1) - 1]]
            qb_lop_z = [self.dq_array[i][j] \
                for i in range((pchrow) * (self.code_distance + 1), (pchrow + 1) * (self.code_distance + 1)) \
                for j in [(pchcol + 1) * (self.code_distance + 1) - 1]]
        elif pchtype == 'm':
            qb_lop_z = [self.dq_array[i][j] \
                for i in [(pchrow + 1) * (self.code_distance + 1) - 1] \
                for j in range((pchcol) * (self.code_distance + 1) + 1, (pchcol + 1) * (self.code_distance + 1))]
            qb_lop_x = [self.dq_array[i][j] \
                for i in range((pchrow) * (self.code_distance + 1) + 1, (pchrow + 1) * (self.code_distance + 1)) \
                for j in [(pchcol) * (self.code_distance + 1) + 1]]
        elif pchtype == 'z':
            qb_lop_x = [self.dq_array[i][j] \
                for i in [(pchrow + 1) * (self.code_distance + 1) - 1] \
                for j in range((pchcol) * (self.code_distance + 1) + 1, (pchcol + 1) * (self.code_distance + 1))]
            qb_lop_z = [self.dq_array[i][j] \
                for i in range((pchrow) * (self.code_distance + 1) + 1, (pchrow + 1) * (self.code_distance + 1)) \
                for j in [(pchcol) * (self.code_distance + 1) + 1]]
        else:
            raise Exception("Undefined pchtype: {} at {}".format(pchtype, target_pchidx))
        
        return qb_lop_x, qb_lop_z

    def peek_multi_logical_qubits(self, target_lop_list, target_pchidx_list, pchtype_list, num_shots):
        if num_shots <= 0:
            return dict()
        
        lop_qb_list = [self.get_lop_qb(target_pchidx, pchtype) for target_pchidx, pchtype in zip(target_pchidx_list, pchtype_list)]
        
        prob = ray.get(self.qc_sup.get_prob_multiqb.remote(lop_qb_list, target_lop_list, num_shots))
        
        return prob  
    
    def append_op (self, op, q1 = None, q2 = None):
        if op == 'cz':
            for circuit_op in self.op_list:
                circuit_op.append_operation('CZ', [q1, q2])
        elif op == 'h':
            for circuit_op in self.op_list:
                circuit_op.append_operation('H', [q1])
        elif op == 'h_t':
            if SPLIT_PER_M == 3:
                self.op_list[0].append_operation('H', [q1])
                self.op_list[1].append_operation('H', [q1])
                self.op_list[2].append_operation('H', [q1])
                
                self.op_list[1].append_operation('S', [q1])
                self.op_list[2].append_operation('S_DAG', [q1])
            elif SPLIT_PER_M == 5:
                self.op_list[0].append_operation('H', [q1])
                self.op_list[0].append_operation('CNOT', [q1,q2])
                
                self.op_list[1].append_operation('H', [q1])
                self.op_list[1].append_operation('H', [q2])
                self.op_list[1].append_operation('CZ', [q1,q2])
                
                self.op_list[2].append_operation('H', [q1])
                self.op_list[2].append_operation('H', [q2])
                self.op_list[2].append_operation('CZ', [q1,q2])
                self.op_list[2].append_operation('X', [q1])
                self.op_list[2].append_operation('X', [q2])
                
                self.op_list[3].append_operation('H', [q1])
                self.op_list[3].append_operation('H', [q2])
                
                for circuit_op in self.op_list:
                    circuit_op.append_operation('S_DAG', [q1])
                    circuit_op.append_operation('S_DAG', [q2])
                    circuit_op.append_operation('H', [q1])
                    circuit_op.append_operation('H', [q2])
        elif op == 's':
            for circuit_op in self.op_list:
                circuit_op.append_operation('S', [q1])
        elif op == 'sdg':
            for circuit_op in self.op_list:
                circuit_op.append_operation('S_DAG', [q1])
        elif op == 'x':
            for circuit_op in self.op_list:
                circuit_op.append_operation('X', [q1])
        elif op == 'y':
            for circuit_op in self.op_list:
                circuit_op.append_operation('Y', [q1])
        elif op == 'z':
            for circuit_op in self.op_list:
                circuit_op.append_operation('Z', [q1])
        elif op == 'i':
            pass
        elif op == 'swap':
            for circuit_op in self.op_list:
                circuit_op.append_operation('SWAP', [q1, q2])
        else:
            raise Exception("Operation {} is not supported".format(op))
        
        return
    
    def apply_all_op (self):
        circ_id = ray.put(self.op_list)
        self.qc_sup.apply_qc.remote(circ_id)
        
        self.op_list = [stim.Circuit() for _ in range(SPLIT_PER_M)]
        return

    
    '''
    op_trace
        [
            [op, ...], # Time step 0
            [op, ...], # Time step 1
            ...,
            [op, ...], # Time step n-1
        ]
    '''
    def append_trace(self, op_trace, inject_no_error = False, inject_no_error_mask = []):

        meas_qb_list = []
        meas_qb_idx = []
        meas_qb_type = []

        for i in range(len(op_trace)):

            ops_per_time_step = op_trace[i]
            error_map_dq, error_map_aq = self.init_error_map()
            for op in ops_per_time_step:
                # Build gates except measurement
                op_type = op.op_type
                if op_type == 'meas':
                    q1_idx = op.get()
                else:
                    if op_type == 'cz' or op_type == 'cnot':
                        q1_idx, q2_idx = op.get()
                    else:
                        q1_idx = op.get()

                    if not op_type in SUPPORTED_OP_TYPES:
                        raise Exception("Invalid op_type: {}".format(op_type))
                    elif self.emulate_mode:
                        pass
                    elif op_type == 'h':
                        self.append_op(op_type, self.get_qubit(*q1_idx))
                    elif op_type == 'h_t':
                        if self.num_fresh_m:
                            pass
                        else:
                            self.apply_all_op()
                            self.split_qc()
                            
                            if SPLIT_PER_M == 3:
                                fresh_m_1 = self.fresh_m_idx
                                self.append_op(op_type, fresh_m_1)
                                self.num_fresh_m += 1
                            elif SPLIT_PER_M == 5:
                                fresh_m_1 = self.fresh_m_idx
                                fresh_m_2 = self.fresh_m_idx + 1
                                self.append_op(op_type, fresh_m_1, fresh_m_2)
                                self.num_fresh_m += 2
                            else:
                                raise Exception ("SPLIT_PER_M other than 3,5 are currently not supported")
                            
                        self.append_op('swap',self.get_qubit(*q1_idx),self.fresh_m_idx)
                        self.fresh_m_idx += 1
                        self.num_fresh_m -= 1
                    elif op_type == 'h_s':
                        self.append_op('h', self.get_qubit(*q1_idx))
                        self.append_op('s', self.get_qubit(*q1_idx))
                    elif op_type == 'sdag_h':
                        self.append_op('sdg', self.get_qubit(*q1_idx))
                        self.append_op('h', self.get_qubit(*q1_idx))
                    elif op_type == 'cz':
                        self.append_op(op_type, self.get_qubit(*q1_idx),self.get_qubit(*q2_idx))
                        # For debugging
                    elif op_type == 'i':
                        pass
                    elif op_type == 'x':
                        self.append_op(op_type, self.get_qubit(*q1_idx))
                    elif op_type == 'cx':
                        self.append_op(op_type, self.get_qubit(*q1_idx))
                    elif op_type == 'cnot':
                        self.append_op(op_type, self.get_qubit(*q1_idx),self.get_qubit(*q2_idx))
                    elif op_type == 'z':
                        self.append_op(op_type, self.get_qubit(*q1_idx))
                    elif op_type == 'y':
                        self.append_op(op_type, self.get_qubit(*q1_idx))
                    elif op_type == 'h_sdag_h':
                        self.append_op('h', self.get_qubit(*q1_idx))
                        self.append_op('sdg', self.get_qubit(*q1_idx))
                        self.append_op('h', self.get_qubit(*q1_idx))
                    else:
                        pass # Add if needed

                # Select error gate
                selected_error_gate = self.select_gate_error_gate(op_type, inject_no_error)
                    
                # Remove errors that occur in masked qubits
                if len(selected_error_gate) == 1:
                    if any([all([idx1 == idx2 for (idx1, idx2) in zip(q1_idx, no_error_mask_idx)]) for no_error_mask_idx in inject_no_error_mask]):
                        selected_error_gate = 'i'
                elif len(selected_error_gate) == 2:
                    if any([all([idx1 == idx2 for (idx1, idx2) in zip(q1_idx, no_error_mask_idx)]) for no_error_mask_idx in inject_no_error_mask]):
                        selected_error_gate_0 = 'i'
                    else:
                        selected_error_gate_0 = selected_error_gate[0]
                    
                    if any([all([idx1 == idx2 for (idx1, idx2) in zip(q2_idx, no_error_mask_idx)]) for no_error_mask_idx in inject_no_error_mask]):
                        selected_error_gate_1 = 'i'
                    else:
                        selected_error_gate_1 = selected_error_gate[1]
                        
                    selected_error_gate = selected_error_gate_0 + selected_error_gate_1

                # Apply error gate on quantum circuits
                if self.emulate_mode:
                    pass
                elif (selected_error_gate == 'i') or (selected_error_gate == 'ii'):
                    pass
                elif op_type == 'cz' or op_type == 'cnot':
                    self.append_op(selected_error_gate[0], self.get_qubit(*q1_idx))
                    self.append_op(selected_error_gate[1], self.get_qubit(*q2_idx))
                else:
                    self.append_op(selected_error_gate, self.get_qubit(*q1_idx))

                # Update error_map
                if (selected_error_gate == 'i') or (selected_error_gate == 'ii'):
                    pass
                elif op_type == 'cz' or op_type == 'cnot':
                    row_1, col_1 = self.get_qb_idx(*q1_idx)
                    if q1_idx[2] == 'dq':
                        error_map_dq[row_1][col_1] = selected_error_gate[0]
                    else:
                        error_map_aq[row_1][col_1] = selected_error_gate[0]
                    row_2, col_2 = self.get_qb_idx(*q2_idx)
                    if q2_idx[2] == 'dq':
                        error_map_dq[row_2][col_2] = selected_error_gate[1]
                    else:
                        error_map_aq[row_2][col_2] = selected_error_gate[1]
                else:
                    row_1, col_1 = self.get_qb_idx(*q1_idx)
                    if q1_idx[2] == 'dq':
                        error_map_dq[row_1][col_1] = selected_error_gate
                    else:
                        error_map_aq[row_1][col_1] = selected_error_gate
    
            self.append_error_trace(error_map_dq, error_map_aq)
            
            # Build measure
            ops_types = [o.op_type for o in ops_per_time_step]
            if 'meas' in ops_types:
                if i != len(op_trace) - 1:
                    raise Exception("Invalid trace: measurements can only be on the last entry of the list")

                # Build lists of measured qubits
                meas_qb_list = []
                meas_qb_idx = []
                meas_qb_type = []
                for op in ops_per_time_step:
                    meas_qb_list.append(self.get_qubit(*op.get()))
                    meas_qb_idx.append(self.get_qb_idx(*op.get()))
                    meas_qb_type.append(op.get()[2])

        self.append_error_trace(error_map_dq, error_map_aq)
        
        self.apply_all_op()

        return meas_qb_list, meas_qb_idx, meas_qb_type

    def select_gate_error_gate (self, op, inject_no_error = False):
        if inject_no_error:
            if op == 'cz' or op == 'cnot':
                return 'ii'
            else:
                return 'i'

        error_sq_gate = ['x','y','z','i']
        error_dq_gate = ['xx','xy','xz','xi','yx','yy','yz','yi','zx','zy','zz','zi','ix','iy','iz','ii']

        if op == 'cz' or op == 'cnot':
            probabilities = [self.physical_error_rate / 15] *15 + [1 - self.physical_error_rate]
            return np.random.choice(error_dq_gate,size=1,p=probabilities)[0]
        else:
            probabilities = [self.physical_error_rate / 3, self.physical_error_rate / 3, self.physical_error_rate / 3, 1 - self.physical_error_rate]
            return np.random.choice(error_sq_gate,size=1,p=probabilities)[0]
        
    def init_error_map (self):
        error_map_aq = np.full((self.num_row_aq, self.num_col_aq), '-')
        error_map_dq = np.full((self.num_row_dq, self.num_col_dq), '-') 
        return error_map_dq, error_map_aq
    
    def append_error_trace (self, error_map_dq, error_map_aq):
        self.error_trace_dq.append(error_map_dq)
        self.error_trace_aq.append(error_map_aq)
        return

    def get_error_trace (self):
        return self.error_trace_dq, self.error_trace_aq
    
    def clear_error_trace (self):
        self.error_trace_dq = []
        self.error_trace_aq = []
        return
