from qiskit import *
from qiskit.quantum_info.operators import Operator, Pauli

import numpy as np

def pauli_product(pauli_list, n_qubit): 
    assert len(pauli_list) == n_qubit
    
    pauil_product = None
    for pauli in pauli_list: 
        if pauli == 'X': 
            curr_pauli = Operator(Pauli(label='X'))
        elif pauli == 'Y': 
            curr_pauli = Operator(Pauli(label='Y'))
        elif pauli == 'Z': 
            curr_pauli = Operator(Pauli(label='Z'))
        elif pauli == 'I': 
            curr_pauli = Operator(np.eye(2, 2))
            
        try:
            pauli_product = curr_pauli.tensor(pauli_product)
        except:
            pauli_product = curr_pauli
            
    return pauli_product


def pp_rotation(pp, rotation):
    n_qubit = len(pp.input_dims())
    ppr = np.cos(rotation) * Operator(np.eye(2**n_qubit, 2**n_qubit)) - 1j * np.sin(rotation) * pp
    
    return ppr

def get_ppr_result (ppr_list, sign_list, basis, num_shots = 1024, init = None):
    n_qubit = len(ppr_list[0])

    if init is None:
        init = np.array([1] + [0] * (2 ** n_qubit -1))
    else:
        pass

    theta_list = [np.pi/8 if sign == '+' else -np.pi/8 for sign in sign_list]

    #
    init_qc_op = Operator(np.eye(2**(n_qubit), 2**(n_qubit)))
    qc_op = init_qc_op
    for pauli_list, theta in zip(ppr_list, theta_list):
        ppr = pp_rotation(pauli_product(pauli_list, n_qubit), theta)
        qc_op = qc_op.compose(ppr)

    #
    curr_state = np.matmul(qc_op.data, init)
    curr_state = curr_state / np.sqrt(np.sum(curr_state*np.conjugate(curr_state)))

    test_qc = QuantumCircuit(n_qubit, n_qubit)
    test_qc.initialize(curr_state, test_qc.qubits)

    if basis == 'X':
        test_qc.h(range(n_qubit))
    elif basis == 'Y':
        test_qc.sdg(range(n_qubit))
        test_qc.h(range(n_qubit))
    else: # 'Z'
        pass
        
    test_qc.measure(range(n_qubit),range(n_qubit))

    backend = Aer.get_backend('qasm_simulator')
    job = execute(test_qc, backend, shots=num_shots)
    test_counts = job.result().get_counts()
    # Move LSB from right to left
    test_counts = {k[::-1]: v for (k,v) in test_counts.items()}

    return test_counts

def get_ideal_ppr_result (ppr_list, sign_list, basis, init = None):
    n_qubit = len(ppr_list[0])

    if init is None:
        init = np.array([1] + [0] * (2 ** n_qubit -1))
    else:
        pass

    theta_list = [np.pi/8 if sign == '+' else -np.pi/8 for sign in sign_list]

    #
    init_qc_op = Operator(np.eye(2**(n_qubit), 2**(n_qubit)))
    qc_op = init_qc_op
    for pauli_list, theta in zip(ppr_list, theta_list):
        ppr = pp_rotation(pauli_product(pauli_list, n_qubit), theta)
        qc_op = qc_op.compose(ppr)

    #
    curr_state = np.matmul(qc_op.data, init)
    curr_state = curr_state / np.sqrt(np.sum(curr_state*np.conjugate(curr_state)))

    test_qc = QuantumCircuit(n_qubit, n_qubit)
    test_qc.initialize(curr_state, test_qc.qubits)

    if basis == 'X':
        test_qc.h(range(n_qubit))
    elif basis == 'Y':
        test_qc.sdg(range(n_qubit))
        test_qc.h(range(n_qubit))
    else: # 'Z'
        pass
        
    backend = Aer.get_backend('statevector_simulator')
    job = execute(test_qc, backend, shots=1)
    statevector = job.result().get_statevector()
    state = [bin(i)[2:].zfill(n_qubit) for i in range(2 ** n_qubit)]
    probabilities = {k: abs(s)**2 for (k,s) in zip(state, statevector)}
    
    # Move LSB from right to left
    probabilities = {k[::-1]: v for (k,v) in probabilities.items()}

    return probabilities

def run_ppr_with_qiskit (ppr, num_shots = 2048, get_exact_state = False):
    sign = '+'
    pauli_list = list(ppr)
    n_qubit = len(pauli_list)
    init = np.array([1,1]/np.sqrt(2))
    for _ in range(n_qubit-1):
        init = np.kron(init, np.array([1, np.exp(1j*np.pi/4)]/np.sqrt(2)))

    lqsim_res = {}
    if get_exact_state:
        lqsim_res['cx'] = get_ideal_ppr_result ([pauli_list], [sign], 'X', init)
        lqsim_res['cy'] = get_ideal_ppr_result ([pauli_list], [sign], 'Y', init)
        lqsim_res['cz'] = get_ideal_ppr_result ([pauli_list], [sign], 'Z', init)
    else:
        lqsim_res['cx'] = {k: v/num_shots for (k,v) in get_ppr_result ([pauli_list], [sign], 'X', num_shots, init).items()}
        lqsim_res['cy'] = {k: v/num_shots for (k,v) in get_ppr_result ([pauli_list], [sign], 'Y', num_shots, init).items()}
        lqsim_res['cz'] = {k: v/num_shots for (k,v) in get_ppr_result ([pauli_list], [sign], 'Z', num_shots, init).items()}
    
    return lqsim_res

def remove_ancilla_state (sim_res):
    _sim_res = {}
    for k,v in sim_res.items():
        try:
            _sim_res[k[2:]] += v
        except:
            _sim_res[k[2:]] = v
    
    return _sim_res
