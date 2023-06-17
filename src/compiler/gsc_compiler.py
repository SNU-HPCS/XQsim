# General
import os, sys
#
curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
par_dir = os.path.join(curr_dir, os.pardir)
#
from functools import partial
from math import *
import subprocess
from parse import compile
import numpy as np
# Qiskit
from qiskit import * 
# pytket
from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
from pytket.predicates import GateSetPredicate
from pytket import Circuit, OpType
from pytket.passes import *
# absl 
from absl import flags
from absl import app
#
sys.path.insert(0, par_dir)
import util

# gsc_compiler compiles an arbitrary quantum circuit to the custom quantum ISA (QISA)
# [Ref.A] Byun, Ilkwon, et al. "XQsim: modeling cross-technology control processors for 10+ K qubit quantum computers." Proceedings of the 49th Annual International Symposium on Computer Architecture. 2022.
# [Ref.B] Litinski, Daniel. "A game of surface codes: Large-scale quantum computing with lattice surgery." Quantum 3 (2019): 128.
# [Ref.C] Ross, Neil J., and Peter Selinger. "Optimal ancilla-free Clifford+ T approximation of z-rotations." Quantum Inf. Comput. 16.11&12 (2016): 901-953.

class gsc_compiler: 
    def __init__(self):
        self.qc_name = None
        self.compile_mode = None
        isa_def_path = os.path.join(par_dir, "isa_format.json")
        self.isa_def = util.getJsonData(isa_def_path)

    def setup(self, qc_name, compile_mode):
        self.qc_name = qc_name
        self.compile_mode = compile_mode
        
        # Set target filepaths
        qc_dir = os.path.join(par_dir, "quantum_circuits")
        self.qasm_filepath = os.path.join(*[qc_dir, "open_qasm", self.qc_name+".qasm"])
        self.qtrp_filepath = os.path.join(*[qc_dir, "transpiled", self.qc_name+".qtrp"])
        self.qisa_filepath = os.path.join(*[qc_dir, "qisa_compiled", self.qc_name+".qisa"])
        self.qbin_filepath = os.path.join(*[qc_dir, "binary", self.qc_name+".qbin"])
        return
        

    def run(self):
        # TRANSPILE
        if "transpile" in self.compile_mode:
            self.transpile()
            
        # QISA COMPILE
        if "qisa_compile" in self.compile_mode:
            self.qisa_compile()

        # ASSEMBLE
        if "assemble" in self.compile_mode: 
            self.assemble()
        return


    def transpile(self):
        # Transpile [qasm_filepath] into the sequence of Pauli-product rotations, PPR(pi/8), and Pauli-product measurements, PPM.
        # Save the transpiled circuit to [qtrp_filepath] 
        print("TRANSPILE START\nInput: {}\nOutput: {}".format(os.path.abspath(self.qasm_filepath), os.path.abspath(self.qtrp_filepath)))

        # Load the quantum circuit from the .qasm file
        qc = QuantumCircuit.from_qasm_file(self.qasm_filepath)

        # Run the circuit translation
        clif_t_qc = decompose_qc_to_Clifford_T(qc)
        ppr_qc = format_ppr(*decompose_Clifford_T_to_PPR(clif_t_qc))

        # Write the fomatted string to the output file
        qtrp = open(self.qtrp_filepath, "w")
        for line in ppr_qc:
            qtrp.write(line)
        qtrp.close()

        # Print the result
        print("TRANSPILE END")
        print()
        #os.system("cat {}".format(self.qtrp_filepath))
        return


    def qisa_compile(self):
        # Compile [qtrp_filepath] for the target QISA
        # Save the generated quantum instructions to [qisa_filepath]
        print("QISA COMPILE START\nInput: {}\nOutput: {}".format(os.path.abspath(self.qtrp_filepath), os.path.abspath(self.qisa_filepath)))

        # Open files to read and write.
        qtrp = open(self.qtrp_filepath, "r")
        qisa = open(self.qisa_filepath, "w")

        # Local variables to generate qisa lines
        num_lq = get_num_lq(self.qasm_filepath) + 2
        first_op = True
        mreg_free_idx = 1  

        # Iteratively generate qisa lines from qtrp lines
        qtrp_line_format = compile("{} {} [{}] [{}] {}\n")
        for line in qtrp:
            # Parse the qtrp line
            op, sign, pp, lq, mreg = qtrp_line_format.parse(line)
            # NOTE: Allocate LQ_0 and LQ_1 to the two ancilla logical qubits (i.e., magic state, zero state) [Ref.B]
            lqlist = [int(compile("q[{}]").parse(q_str)[0])+2 \
                      for q_str in lq.split(",")]
            pauli_product = [*pp]
            mreg = compile("meas[{}]").parse(mreg)
            if mreg is None: 
                pass
            else:
                mreg_dst = int(mreg[0]) + 2

            # Generate and write qisa lines based on the target op
            qisa_str = ""
            if op == "PPR":
                lqlist = [0, 1] + lqlist
                # PPR(pi/8) is implemented by the auto-corrected pi/8 rotation in [Ref.B].
                # Several instructions are required to run the included PPMs, SQMs, and byproduct PPR(pi/2).
                ## PREP_INFO
                qisa_str += build_qisa_lines(inst="PREP_INFO",
                                             isa_def=self.isa_def)
                ## LQI
                qisa_str += build_qisa_lines(inst="LQI",
                                             lqlist=lqlist,
                                             num_lq=num_lq,
                                             isa_def=self.isa_def,
                                             op = "PPR",
                                             first_op=first_op)
                ## RUN_ESM
                qisa_str += build_qisa_lines(inst="RUN_ESM",
                                             isa_def=self.isa_def)
                ## MERGE_INFO
                qisa_str += build_qisa_lines(inst="MERGE_INFO",
                                             lqlist=lqlist,
                                             pauli_product=["Y", "Z"]+pauli_product,
                                             num_lq=num_lq,
                                             isa_def=self.isa_def)
                ## INIT_INTMD
                qisa_str += build_qisa_lines(inst="INIT_INTMD",
                                             isa_def=self.isa_def)
                ## RUN_ESM
                qisa_str += build_qisa_lines(inst="RUN_ESM",
                                             isa_def=self.isa_def)
                ## PPM_INTERPRET (b)
                qisa_str += build_qisa_lines(inst="PPM_INTERPRET",
                                             meas_flag="+FFB",
                                             mreg_dst=0,
                                             lqlist=[0, 1],
                                             pauli_product=["Y", "Z"],
                                             num_lq=num_lq,
                                             isa_def=self.isa_def)
                ## PPM_INTERPRET (a)
                qisa_str += build_qisa_lines(inst="PPM_INTERPRET",
                                             meas_flag=sign+"TTA",
                                             mreg_dst=mreg_free_idx,
                                             lqlist=lqlist,
                                             pauli_product=["I", "Z"]+pauli_product,
                                             num_lq=num_lq,
                                             isa_def=self.isa_def)
                mreg_free_idx = set_mreg_free_idx(mreg_free_idx, num_lq)

                ## MEAS_INTMD
                qisa_str += build_qisa_lines(inst="MEAS_INTMD",
                                             isa_def=self.isa_def)
                ## SPLIT_INFO
                qisa_str += build_qisa_lines(inst="SPLIT_INFO",
                                             isa_def=self.isa_def)
                ## RUN_ESM
                qisa_str += build_qisa_lines(inst="RUN_ESM",
                                             isa_def=self.isa_def)
                ## LQM_X
                qisa_str += build_qisa_lines(inst="LQM_X",
                                             meas_flag="+FFD",
                                             mreg_dst=mreg_free_idx,
                                             lqlist=[1],
                                             num_lq = num_lq,
                                             isa_def=self.isa_def)
                mreg_free_idx = set_mreg_free_idx(mreg_free_idx, num_lq)
                
                ## LQM_FB
                qisa_str += build_qisa_lines(inst="LQM_FB",
                                             meas_flag="+FFC",
                                             mreg_dst=mreg_free_idx,
                                             lqlist=[0],
                                             num_lq = num_lq,
                                             isa_def=self.isa_def)
                mreg_free_idx = set_mreg_free_idx(mreg_free_idx, num_lq)
                
            elif op == "PPM":
                # PPM is implemented by the lattice surgery, which merges and splits the logical qubit patches. 
                # The lattice surgery is implemented by the instructions below.
                ## PREP_INFO
                qisa_str += build_qisa_lines(inst="PREP_INFO",
                                             isa_def=self.isa_def)
                ## LQI
                qisa_str += build_qisa_lines(inst="LQI",
                                             lqlist=lqlist,
                                             num_lq=num_lq,
                                             isa_def=self.isa_def,
                                             op="PPM",
                                             first_op=first_op)
                ## RUN_ESM
                if first_op:
                    qisa_str += build_qisa_lines(inst="RUN_ESM",
                                                 isa_def=self.isa_def)
                ## MERGE_INFO
                qisa_str += build_qisa_lines(inst="MERGE_INFO",
                                             lqlist=lqlist,
                                             pauli_product=pauli_product,
                                             num_lq=num_lq,
                                             isa_def=self.isa_def)
                ## INIT_INTMD
                qisa_str += build_qisa_lines(inst="INIT_INTMD",
                                             isa_def=self.isa_def)
                ## RUN_ESM
                qisa_str += build_qisa_lines(inst="RUN_ESM",
                                             isa_def=self.isa_def)
                ## PPM_INTERPRET (normal)
                qisa_str += build_qisa_lines(inst="PPM_INTERPRET",
                                             meas_flag=sign+"TTN",
                                             mreg_dst=mreg_free_idx,
                                             lqlist=lqlist,
                                             pauli_product=pauli_product,
                                             num_lq=num_lq,
                                             isa_def=self.isa_def)
                mreg_free_idx = set_mreg_free_idx(mreg_free_idx, num_lq)
                
                ## MEAS_INTMD
                qisa_str += build_qisa_lines(inst="MEAS_INTMD",
                                             isa_def=self.isa_def)
                ## SPLIT_INFO
                qisa_str += build_qisa_lines(inst="SPLIT_INFO",
                                             isa_def=self.isa_def)
                ## RUN_ESM
                qisa_str += build_qisa_lines(inst="RUN_ESM",
                                             isa_def=self.isa_def)

            elif op == "SQM":
                # Handle the remaining single-qubit measurements
                qisa_str += build_qisa_lines(inst="LQM_{}".format(pp), 
                                             meas_flag=sign+"FTN",
                                             mreg_dst=mreg_free_idx,
                                             lqlist=lqlist,
                                             num_lq=num_lq,
                                             isa_def=self.isa_def)
                mreg_free_idx = set_mreg_free_idx(mreg_free_idx, num_lq)
            else:
                raise Exception("qisa_compile - Undefined operation: ", op)
            if first_op:
                first_op = False
            # Write the generated lines 
            qisa.write(qisa_str)
        qisa.close()

        # Print the qisa_compile's result
        print("QISA COMPILE END")
        print()
        #os.system("cat {}".format(self.qisa_filepath))
        return 


    def assemble(self):
        # Assemble [qisa_filepath] based on the target QISA"s bit format
        # Save the generated binary to [qbin_path]
        if "test" not in self.qc_name and "scale" not in self.qc_name:
            print("GSC-compiler: ASSEMBLE - {}".format(self.qc_name))
        
        # Open files to read and write
        qisa = open(self.qisa_filepath, "r")
        qbin = open(self.qbin_filepath, "wb")

        # inst/bit/mflag definition from isa_def
        inst_def = self.isa_def["inst"]
        bit_def = self.isa_def["bit_format"]
        mflag_def = self.isa_def["meas_flag"]

        # bit width info.
        opcode_bw = bit_def["opcode"]["len"]
        meas_flag_bw = bit_def["meas_flag"]["len"]
        mreg_dst_bw = bit_def["mreg_dst"]["len"]
        lq_addr_offset_bw = bit_def["lq_addr_offset"]["len"]
        target_bw = bit_def["target"]["len"]

        # Check the bit format's correctness
        ## opcode
        assert np.power(2, opcode_bw) >= len(inst_def), "assemble - opcode_bw is too small: {}".format(opcode_bw)
        ## bit widths
        for key, val in bit_def.items():
            assert val["len"] == val["msb"]-val["lsb"]+1, "assmeble - bit format is wrong: {}".format(key)

        # Generate binary lines
        for qisa_line in qisa:
            opcode, meas_flag, mreg_dst, lq_addr_offset, target = qisa_line.split()
            # opcode
            opcode_bit = format(inst_def[opcode], "0{}b".format(opcode_bw))

            # meas_flag
            if meas_flag == "NA":
                meas_flag_bit = format(0, "0{}b".format(meas_flag_bw))
            else:
                meas_flag_bit = ""
                for flag, bit_len in mflag_def.items():
                    val = meas_flag[0]
                    if flag == "sign":
                        if val == "+":
                            meas_flag_bit += "0"
                        elif val == "-":
                            meas_flag_bit += "1"
                        else:
                            raise Exception("assemble - meas_flag sign should be + or -: ", val)
                    elif flag == "pp_register":
                        if val == "F":
                            meas_flag_bit += "0"
                        elif val == "T":
                            meas_flag_bit += "1"
                        else: 
                            raise Exception("assemble - meas_flag pp_register should be F or T: ", val)
                    elif flag == "bp_check":
                        if val == "F":
                            meas_flag_bit += "0"
                        elif val == "T":
                            meas_flag_bit += "1"
                        else:
                            raise Exception("assemble - meas_flag bp_check should be F or T: ", val)
                    elif flag == "abcd_flag":
                        if val == "A":
                            meas_flag_bit += "1" + format(0, "0{}b".format(bit_len-1))
                        elif val == "B":
                            meas_flag_bit += "1" + format(1, "0{}b".format(bit_len-1))
                        elif val == "C":
                            meas_flag_bit += "1" + format(2, "0{}b".format(bit_len-1))
                        elif val == "D":
                            meas_flag_bit += "1" + format(3, "0{}b".format(bit_len-1))
                        elif val == "N":
                            meas_flag_bit += format(0, "0{}b".format(bit_len))
                        else:
                            raise Exception("assemble - meas_flag abcd_flag should be A/B/C/D/N: ", val)
                    meas_flag = meas_flag[1:]

            # mreg_dst
            if mreg_dst == "NA":
                mreg_dst_bit = format(0, "0{}b".format(mreg_dst_bw))
            else:
                mreg_dst_bit = format(int(mreg_dst, 16), "0{}b".format(mreg_dst_bw))

            # lq_addr_offset
            if lq_addr_offset == "NA":
                lq_addr_offset_bit = format(0, "0{}b".format(lq_addr_offset_bw))
            else:
                 lq_addr_offset_bit = format(int(lq_addr_offset, 16), "0{}b".format(lq_addr_offset_bw))

            # target
            if target == "NA":
                target_bit = format(0, "0{}b".format(target_bw))
            else:
                target_list = target[1:-2].split(',')
                target_list.reverse()
                target_bit = ""
                for t in target_list:
                    if t == "I":
                       target_bit += "00"
                    elif t == "X":
                        target_bit += "01"
                    elif t == "Z":
                        target_bit += "10"
                    elif t == "Y":
                        target_bit += "11"
                    elif t == "T":
                        target_bit += "01"
                    elif t == "-":
                        target_bit += "00"
                    else:
                        raise Exception("t: ", t)
            
            # Check the bit length for each field
            assert len(opcode_bit) == opcode_bw, "assemble - generated opcode bit length is wrong: {}".format(len(opcode_bit))
            assert len(meas_flag_bit) == meas_flag_bw, "assemble - generated meas_flag bit length is wrong: {}".format(len(meas_flag_bit))
            assert len(mreg_dst_bit) == mreg_dst_bw, "assemble - generated mreg_dst bit length is wrong: {}".format(len(mreg_dst_bit))
            assert len(lq_addr_offset_bit) == lq_addr_offset_bw, "assemble - generated lq_addr_offset bit length is wrong: {}".format(len(lq_addr_offset_bit))
            assert len(target_bit) == target_bw, "assemble - generated target bit length is wrong: {}".format(len(target_bit))
            
            # Write the generated binary line
            qbin_bitstring = opcode_bit + \
                                 meas_flag_bit + \
                                 mreg_dst_bit + \
                                 lq_addr_offset_bit + \
                                 target_bit
            qbin_byte = int(qbin_bitstring, 2).to_bytes(8, byteorder="big")
            qbin.write(qbin_byte)

        qisa.close()
        qbin.close()

        # Print the result 
        #print("ASSEMBLE RESULT")
        #print()
        #os.system("cat {}".format(self.qbin_filepath))
        return


### Functions for the TRANSPILE ###
# Function to decompose the input qc to the Clifford+T gates
def decompose_qc_to_Clifford_T (qc, precision = 1e-10, opt=1):
    # qc: Qiskit QuantumCircuit object
    decomposed_qc = qc.decompose()
    circ = qiskit_to_tk(decomposed_qc)
    
    gateset = GateSetPredicate({OpType.X, OpType.Y, OpType.Z, OpType.H, OpType.CX, OpType.S, OpType.T, OpType.Barrier, OpType.Measure})
    
    if(gateset.verify(circ) == False):
        # Decomposition step
        multiq_gates = {OpType.CX}
        singleq_gates = {OpType.X, OpType.Y, OpType.Z, OpType.H, OpType.S, OpType.T}
        available_gates = multiq_gates.union(singleq_gates)
        cx_replacement = Circuit(2).CX(0,1)
        tk1_replacement = partial(tk1_replacement_precision, precision=precision)
        try: # For pytket version 0.15.0
            custom = RebaseCustom(multiq_gates, cx_replacement, singleq_gates, tk1_replacement)
            custom.apply(circ)
        except: # For pytket version 1.15.0
            custom = RebaseCustom(available_gates, cx_replacement, tk1_replacement)
            custom.apply(circ)

        # Optimization step
        RemoveBarriers().apply(circ)
        comp = RepeatPass(SequencePass([CommuteThroughMultis(), RemoveRedundancies()]))
        comp.apply(circ)
        return tk_to_qiskit(circ)

    else:
        return decomposed_qc


# Fucntion to decompose TK1(a,b,c) into a sequence of Clifford+T gates
# TK1(a,b,c) = Rz(a)*Rx(b)*Rz(c) = Rz(a)*H*Rz(b)*H*Rz(c) in matrix order
# In pytket, Rz(a) = exp((-i*\pi*a*Z)/2)
def tk1_replacement_precision(a, b, c, precision):
    if isclose(a, 0.5, abs_tol=precision) and isclose(b, 0.5, abs_tol=precision) and isclose(c, 0.5, abs_tol=precision): 
        return parse_to_tket_format(["H"])
        
    circ_a = rz_approximate_synthesis("pi*" + str(a if a >= 0 else (2 + a)), precision)
    circ_b = rz_approximate_synthesis("pi*" + str(b if b >= 0 else (2 + b)), precision)
    circ_c = rz_approximate_synthesis("pi*" + str(c if c >= 0 else (2 + c)), precision)
    circ_tk1 = circ_c
    circ_tk1.H(0)
    circ_tk1.append(circ_b)
    circ_tk1.H(0)
    circ_tk1.append(circ_a)
    return circ_tk1


# Function to decompose an arbitrary rotation in z-axis Rz(angle) into a sequence of Clifford+T gates
def rz_approximate_synthesis (angle, precision_eps = 1e-10):
    if isclose(float(angle[3:]), 0.25, abs_tol=precision_eps):
        result_circ_order = ["T"]
    elif isclose(float(angle[3:]), 0.75, abs_tol=precision_eps):
        result_circ_order = ["T","S"]
    elif isclose(float(angle[3:]), 1.25, abs_tol=precision_eps):
        result_circ_order = ["T","S","S"]
    elif isclose(float(angle[3:]), 1.75, abs_tol=precision_eps):
        result_circ_order = ["T","S","S","S"]
    else:
        if "e" in angle:
            coeff = angle[angle.find("*")+1:]
            exponent = int(coeff[coeff.find("e")+1:])
            prec = -1 * (int(str(precision_eps)[str(precision_eps).find("e")+1:]) + exponent)
            angle = "pi*" + "{0:.{prec}f}".format(float(angle[3:]), prec=prec)

        if os.name == "nt": # Windows
            result = subprocess.run([".\gridsynth.exe", str(angle), "--rseed=10", "--epsilon", str(precision_eps)], stdout=subprocess.PIPE) # default precision epsilon=1e-10
        else: # Linux
            result = subprocess.run([os.path.join(curr_dir, "gridsynth"), str(angle), "--rseed=10", "--epsilon", str(precision_eps)], stdout=subprocess.PIPE) # default precision epsilon=1e-10
        result_str = result.stdout.decode("utf-8")
        result_mat_order         = [op for op in list(result_str)]
        result_circ_order = list(reversed(result_mat_order))
    return parse_to_tket_format(result_circ_order)


# Function to convert an operation list to a pytket circuit 
def parse_to_tket_format(op_list):
    circ = Circuit(1)
    for op in op_list:
        if (op == "S"):
            circ.S(0)
        elif (op == "H"):
            circ.H(0)            
        elif (op == "X"):
            circ.X(0)            
        elif (op == "T"):
            circ.T(0)
    return circ

# Function to decompose a (Clifford+T) circuit to the sequence of PPRs and PPMs
def decompose_Clifford_T_to_PPR (qc_clifford_T):
    circ = qiskit_to_tk(qc_clifford_T)
    circ_list = [[com.op.get_name(), com.args] for com in list(circ)]

    # Build PPR(pi/8) from T gates
    circ_ppr_list = []
    for T_index in list(filter(lambda e: circ_list[e][0] == "T", range(len(circ_list)))):
        circ_ppr_list.append(construct_one_block(T_index, circ_list))

    # Build PPM from Measurement
    circ_ppm_list = []
    for M_index in list(filter(lambda e: circ_list[e][0] == "Measure", range(len(circ_list)))):
        circ_ppm_list.append(construct_one_block(M_index, circ_list) + [circ_list[M_index][1][1]])

    # Order the measurements: PPM first, SQM last
    circ_ppm_list.sort(reverse=True)

    return circ_ppr_list, circ_ppm_list


# Fucntion to generate PPR(pi/8)s and PPMs from T gates and Measurements, respectively 
def construct_one_block (starting_index, circ_list):
    pauli_list = ["Z"]
    qubit_list = [circ_list[starting_index][1][0]]
    sign_pos = True

    for op in reversed(circ_list[0:starting_index]):
        # X, Y, Z, H, CX, S, T, Measure
        # ignore measurement now
        op_name = op[0]
        if (op_name == "CX"):
            op_qubit_ctrl = op[1][0]
            op_qubit_target = op[1][1]
            if(op_qubit_ctrl in qubit_list and op_qubit_target in qubit_list):
                index_ctrl = qubit_list.index(op_qubit_ctrl)
                index_target = qubit_list.index(op_qubit_target)

                # Check commutation with Z(-pi/4)
                if (pauli_list[index_ctrl] == "X"):
                    pauli_list[index_ctrl] = "Y"
                elif (pauli_list[index_ctrl] == "Y"):
                    pauli_list[index_ctrl] = "X"
                    sign_pos = not(sign_pos)
                elif (pauli_list[index_ctrl] == "Z"):
                    pass

                # Check commutation with X(-pi/4)
                if (pauli_list[index_target] == "X"):
                    pass
                elif (pauli_list[index_target] == "Y"):
                    pauli_list[index_target] = "Z"
                elif (pauli_list[index_target] == "Z"):
                    pauli_list[index_target] = "Y"
                    sign_pos = not(sign_pos)

                # Check commutation with ZX(pi/4)
                iscommute = True
                if (pauli_list[index_ctrl] == "X" or pauli_list[index_ctrl] == "Y"):
                    iscommute = not(iscommute)

                if (pauli_list[index_target] == "Y" or pauli_list[index_target] == "Z"):
                    iscommute = not(iscommute)
                
                # Update PPR if anti-commute
                if (iscommute == False):
                    # Commute with Z
                    if (pauli_list[index_ctrl] == "X"):
                        # iZX = -Y
                        pauli_list[index_ctrl] = "Y"
                        sign_pos = not(sign_pos)
                    elif (pauli_list[index_ctrl] == "Y"):
                        # iZY = X
                        pauli_list[index_ctrl] = "X"
                    elif (pauli_list[index_ctrl] == "Z"):
                        del pauli_list[index_ctrl]
                        del qubit_list[index_ctrl]
                        if index_ctrl < index_target:
                            index_target -= 1

                    # Commute with X
                    if (pauli_list[index_target] == "X"):
                        del pauli_list[index_target]
                        del qubit_list[index_target]
                    elif (pauli_list[index_target] == "Y"):
                        # iXY = -Z
                        pauli_list[index_target] = "Z"
                        sign_pos = not(sign_pos)                            
                    elif (pauli_list[index_target] == "Z"):
                        # iXZ = Y
                        pauli_list[index_target] = "Y"

            elif(op_qubit_ctrl in qubit_list): # CNOT on control qubit = Z
                index = qubit_list.index(op_qubit_ctrl)
                if (pauli_list[index] == "X" or pauli_list[index] == "Y"):
                    pauli_list.append("X")
                    qubit_list.append(op_qubit_target)
            elif(op_qubit_target in qubit_list): # CNOT on target qubit = X
                index = qubit_list.index(op_qubit_target)
                if (pauli_list[index] == "Y" or pauli_list[index] == "Z"):   
                    pauli_list.append("Z")
                    qubit_list.append(op_qubit_ctrl)
            else:
                pass
        else:
            op_qubit = op[1][0]
            if(op_qubit in qubit_list):
                index = qubit_list.index(op_qubit)
                if (op_name == "X"):
                    # -X-PPR(Y)- -> -PPR(-Y)-X-
                    # -X-PPR(Z)- -> -PPR(-Z)-X-
                    if (pauli_list[index] == "Y" or pauli_list[index] == "Z"):
                        sign_pos = not(sign_pos)
                elif (op_name == "Y"):
                    # -Y-PPR(X)- -> -PPR(-X)-Y-
                    # -Y-PPR(Z)- -> -PPR(-Z)-Y-
                    if (pauli_list[index] == "X" or pauli_list[index] == "Z"):
                        sign_pos = not(sign_pos)
                elif (op_name == "Z"):
                    # -Z-PPR(X)- -> -PPR(-X)-Z-
                    # -Z-PPR(Y)- -> -PPR(-Y)-Z-
                    if (pauli_list[index] == "X" or pauli_list[index] == "Y"):
                        sign_pos = not(sign_pos)
                elif (op_name == "H"):
                    # -H-PPR(X)- -> -PPR(Z)-H-
                    # -H-PPR(Y)- -> -PPR(-Y)-H-
                    # -H-PPR(Z)- -> -PPR(X)-H-
                    if (pauli_list[index] == "X"):
                        pauli_list[index] = "Z"
                    elif (pauli_list[index] == "Y"):
                        sign_pos = not(sign_pos)
                    elif (pauli_list[index] == "Z"):
                        pauli_list[index] = "X"
                elif (op_name == "S"):
                    # -S-PPR(X)- -> -PPR(-Y)-S-
                    # -S-PPR(Y)- -> -PPR(X)-S-
                    # -S-PPR(Z)- -> -PPR(Z)-S-
                    if (pauli_list[index] == "X"):
                        pauli_list[index] = "Y"
                        sign_pos = not(sign_pos)
                    elif (pauli_list[index] == "Y"):
                        pauli_list[index] = "X"
                    elif (pauli_list[index] == "Z"):
                        pass
                elif (op_name == "T" or op_name == "Measure" or op_name == "Barrier"):
                    pass
                elif (op_name == "Rx(0.5)"):
                    # -Rx(0.5)-PPR(X)- -> -PPR(X)-Rx(0.5)-
                    # -Rx(0.5)-PPR(Y)- -> -PPR(-Z)-Rx(0.5)-
                    # -Rx(0.5)-PPR(Z)- -> -PPR(Y)-Rx(0.5)-
                    if (pauli_list[index] == "X"):
                        pass
                    elif (pauli_list[index] == "Y"):
                        pauli_list[index] = "Z"
                        sign_pos = not(sign_pos)
                    elif (pauli_list[index] == "Z"):
                        pauli_list[index] = "Y"
                elif (op_name == "Ry(0.5)"):
                    # -Ry(0.5)-PPR(X)- -> -PPR(Z)-Ry(0.5)-
                    # -Ry(0.5)-PPR(Y)- -> -PPR(Y)-Ry(0.5)-
                    # -Ry(0.5)-PPR(Z)- -> -PPR(-X)-Ry(0.5)-
                    if (pauli_list[index] == "X"):
                        pauli_list[index] = "Z"
                    elif (pauli_list[index] == "Y"):
                        pass
                    elif (pauli_list[index] == "Z"):
                        pauli_list[index] = "X"
                        sign_pos = not(sign_pos)
    # order
    pauli_list, qubit_list = zip(*sorted(zip(pauli_list, qubit_list), key = lambda x : x[1].index))
    pauli_list = list(pauli_list)
    qubit_list = list(qubit_list)

    return [pauli_list, qubit_list, sign_pos]


# Function to format the list of PPRs and PPMs 
def format_ppr (circ_ppr_list, circ_ppm_list):
    print_format_list = []
    for PPR in circ_ppr_list:
        line = "PPR"
        if PPR[2]:
            line = line + " + "
        else:
            line = line + " - "

        line = line + "["
        for pauli in PPR[0]:
            line = line + str(pauli)
        line = line + "] ["

        for qubit in PPR[1]:
            if(qubit == PPR[1][-1]):
                line = line + str(qubit.reg_name) + str(qubit.index)
            else:
                line = line + str(qubit.reg_name) + str(qubit.index) + ","
            
        line = line + "]  \n"
        print_format_list.append(line)
    
    for PPM in circ_ppm_list:
        if len(PPM[0]) <= 1:
            line = "SQM"
        else:
            line = "PPM"

        if PPM[2]:
            line = line + " + "
        else:
            line = line + " - "

        line = line + "["
        for pauli in PPM[0]:
            line = line + str(pauli)
        line = line + "] ["
        
        for qubit in PPM[1]:
            if(qubit == PPM[1][-1]):
                line = line + str(qubit.reg_name) + str(qubit.index)
            else:
                line = line + str(qubit.reg_name) + str(qubit.index) + ","
        line = line + str("] ") + str(PPM[3])
    
        line = line + "\n"
        print_format_list.append(line)

    return print_format_list


### Functions for the QISA COMPILE ###
# Function to build qisa lines for the target instruction
def build_qisa_lines(
                inst = None,
                meas_flag = None,
                mreg_dst = None,
                lqlist = None,
                pauli_product = None,
                num_lq = None,
                isa_def = None,
                op = None,
                first_op = None,
                ):

    inst_def = isa_def["inst"]
    bit_def = isa_def["bit_format"]
    mflag_def = isa_def["meas_flag"]

    # Field - inst
    inst_max_len = max([len(i) for i in inst_def.keys()])
    if inst in inst_def.keys():
        inst_str = format(inst, "<{}".format(inst_max_len))
    else:
        raise Exception("build_qisa_lines - Invalid instruction: ", inst)

    # Field - meas_flag
    num_meas_flag = len(mflag_def)
    if meas_flag is not None:
        meas_flag_str = meas_flag
    else:
        meas_flag_str = format("NA", "<{}s".format(num_meas_flag))

    # Field - mreg_dst
    mreg_dst_hexlen = bit_def["mreg_dst"]["len"] // 4
    if mreg_dst is not None:
        mreg_dst_str = "0x" + format(mreg_dst, "0{}x".format(mreg_dst_hexlen))
    else:
        mreg_dst_str = format("NA", "<{}s".format(mreg_dst_hexlen+2))

    # Field - lq_addr_offset & target
    lq_addr_offset_hexlen = bit_def["lq_addr_offset"]["len"] // 4
    lq_addr_offset_list = []
    target_list = []
    if lqlist is not None:
        max_target_lq = bit_def["target"]["len"] // 2
        max_lqaddr_offset = (num_lq // max_target_lq)
        if max_lqaddr_offset >= np.power(2, bit_def["lq_addr_offset"]["len"]):
            raise Exception("build_qisa_lines - too-large num_lq: ", num_lq)
        for offset in range(max_lqaddr_offset+1):
            lq_indices = [(idx % max_target_lq) for idx in lqlist if idx // max_target_lq == offset]
            
            if not lq_indices:
                continue
            ## Generate lq_addr_offset
            lq_addr_offset_list.append("0x"+format(offset, "0{}x".format(lq_addr_offset_hexlen)))

            ## Generate target
            ## The target field is differently generated for each instruction.
            ### Target for LQI
            if inst == "LQI":
                lq_or_pauli_list = ["-"] * max_target_lq

                if op == "PPR":
                    if first_op:
                        for idx in range(num_lq):
                            lq_or_pauli_list[idx] = "T"
                    else:
                        for idx in range(2):
                            lq_or_pauli_list[idx] = "T"
                elif op == "PPM":
                    if first_op: 
                        for idx in range(2, num_lq):
                            lq_or_pauli_list[idx] = "T"
                    else:
                        return ""
                else:
                    raise Exception("build_qisa_lines - Invalid op for LQI: ", op)
            ### Target for MERGE_INFO & PPM_INTERPRET
            elif inst == "MERGE_INFO" or inst == "PPM_INTERPRET":
                lq_or_pauli_list = ["I"] * max_target_lq
                for idx in lq_indices:
                    lq_or_pauli_list[idx] = pauli_product[0]
                    pauli_product = pauli_product[1:]
            ### Target for LQM_X, LQM_Y, LQM_Z, and LQM_FB
            elif "LQM" in inst:
                lq_or_pauli_list = ["-"] * max_target_lq
                for idx in lq_indices:
                    lq_or_pauli_list[idx] = "T"
            else:
                raise Exception("build_qisa_lines - Invalid target_including inst: ", inst)
            ### String format for the target
            target_str = "["
            for t in lq_or_pauli_list:
                target_str += (t + ",")
            target_str += "]"
            target_list.append(target_str)
    else:
        lq_addr_offset_list.append(format("NA", "<{}s".format(lq_addr_offset_hexlen+2)))
        target_list.append("NA")
    
    # Build the qisa lines for the target instruction
    for i in range(len(lq_addr_offset_list)):
        qisa_line = inst_str + " "
        qisa_line += meas_flag_str   + " "
        qisa_line += mreg_dst_str   + " "
        qisa_line += lq_addr_offset_list[i] + " "
        qisa_line += target_list[i] + " "
        qisa_line = qisa_line.rstrip() + "\n"

    return qisa_line

# Function to get the target qc's number of logical qubits
def get_num_lq (qasm_filepath):
    qasm = open(qasm_filepath, "r")
    for line in qasm:
        if "qreg" in line:
            num_lq = int(compile("qreg q[{}];\n").parse(line)[0])
            break
    return num_lq

# Function to set the next free mreg idx
def set_mreg_free_idx (mreg_free_idx, num_lq):
    ret_mreg_free_idx = mreg_free_idx + 1
    if ret_mreg_free_idx == num_lq:
        ret_mreg_free_idx = 1
    return ret_mreg_free_idx


### MAIN ###
def main(argv):
    compiler = gsc_compiler()
    compiler.setup(qc_name=FLAGS.qc,
                   compile_mode=FLAGS.compile_mode
                   )
    compiler.run()
    return 

if __name__ == "__main__":
    # Define input arguments
    # arg_name, default value, description
    FLAGS = flags.FLAGS
    flags.DEFINE_string("quantum_circuit", "qft_n2", "target quantum circuit name", short_name="qc")
    flags.DEFINE_list("compile_mode", "transpile,qisa_compile,assemble", "list of target compilation steps", short_name="m")

    app.run(main)
