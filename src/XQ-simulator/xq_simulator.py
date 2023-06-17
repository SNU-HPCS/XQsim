#
import os, sys
#
curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
par_dir = os.path.join(curr_dir, os.pardir)
parpar_dir = os.path.join(par_dir, os.pardir)
res_dir = os.path.join(curr_dir, "simres")

#
from absl import flags
from absl import app
#
from parse import compile
#
import timeit
import pandas as pd
import pickle
import ray
#
sys.path.insert(0, par_dir)
from sim_param import sim_param
from unit_stat import unit_stat_sim
from util import *
from visualization import *
#
from quantum_instruction_fetch import quantum_instruction_fetch as qif 
from quantum_instruction_decoder import quantum_instruction_decoder as qid 
from patch_decode_unit import patch_decode_unit as pdu 
from patch_information_unit import patch_information_unit as piu 
from physical_schedule_unit import physical_schedule_unit as psu 
from time_control_unit import time_control_unit as tcu 
from qtexec_unit import qtexec_unit as qxu
from error_decode_unit import error_decode_unit as edu
from pauliframe_unit import pauliframe_unit as pfu
from logical_measurement_unit import logical_measurement_unit as lmu 


class xq_simulator:
    def __init__(self):
        self.config = None
        self.qbin = None 
        self.num_lq = None
        self.skip_pqsim = None
        self.num_shots = None 
        self.dump = None
        self.regen = None
        self.debug = None
        #
        self.cycle = 0
        self.sim_done = False


    def setup(self, 
              config=None, 
              qbin=None, 
              num_lq=None,
              skip_pqsim=None, 
              num_shots=None,
              dump=None, 
              regen=None,
              debug=None):
        os.chdir(curr_dir)
        #
        if config is not None:
            self.config = config
        if qbin is not None:
            self.qbin = qbin
        if num_lq is not None:
            self.num_lq = num_lq
        if skip_pqsim is not None:
            self.skip_pqsim = skip_pqsim
        if num_shots is not None: 
            self.num_shots = num_shots
        if dump is not None:
            self.dump = dump
        if regen is not None:
            self.regen = regen
        if debug is not None:
            self.debug = debug

        if self.dump is not None and self.qbin is not None:
            self.dump_path = self.get_dump_path()

        if self.config is not None and self.qbin is not None and self.num_lq is not None:
            config_filepath = "{}/configs/{}.json".format(par_dir, self.config)
            isadef_filepath = "{}/isa_format.json".format(par_dir)
            self.qbin_filepath = "{}/quantum_circuits/binary/{}.qbin".format(par_dir, self.qbin)
            self.param = sim_param(config_filepath, isadef_filepath, self.num_lq)
            self.param.refine_psu_param(target="simulator")
        
        if self.param is not None:
            self.unit_stat_list = []
            for unit_name, unit_cfg in self.param.arch_unit.items():
                uarch = unit_cfg["uarch"]
                temp, tech, vopt = tuple(unit_cfg["temp_tech"].split("_"))
                unit_stat = unit_stat_sim(
                        name = unit_name, 
                        uarch = uarch
                        )
                self.unit_stat_list.append(unit_stat)

                if unit_stat.name == "QIM":
                    self.qif = qif(unit_stat, self.param, self.qbin_filepath)
                elif unit_stat.name == "QID":
                    self.qid = qid(unit_stat, self.param)
                elif unit_stat.name == "PDU":
                    self.pdu = pdu(unit_stat, self.param)
                elif unit_stat.name == "PIU":
                    self.piu = piu(unit_stat, self.param)
                elif unit_stat.name == "PSU":
                    self.psu = psu(unit_stat, self.param)
                elif unit_stat.name == "TCU":
                    self.tcu = tcu(unit_stat, self.param)
                elif unit_stat.name == "QXU":
                    self.qxu = qxu(unit_stat, self.param, self.skip_pqsim, self.num_shots)
                elif unit_stat.name == "EDU":
                    self.edu = edu(unit_stat, self.param, "layer") 
                elif unit_stat.name == "PFU":
                    self.pfu = pfu(unit_stat, self.param)
                elif unit_stat.name == "LMU":
                    self.lmu = lmu(unit_stat, self.param)
                else:
                    raise Exception("Invalid unit: {}".format(unit_stat.name))
        #
        return

    def get_dump_path(self):
        dump_dir = os.path.join(res_dir, self.config)
        if not os.path.exists(dump_dir):
            try: os.mkdir(dump_dir)
            except: pass
        dump_name = self.qbin
        dump_path = os.path.join(dump_dir, dump_name)

        return dump_path

    #
    def run(self):
        if (not self.regen) and \
            os.path.exists(self.dump_path+".stat") and \
            (self.skip_pqsim or os.path.exists(self.dump_path+".pqsim")):
            
            f = open(self.dump_path+".stat", 'rb')
            simulator_stat = pickle.load(f)
            f.close()
            if not self.skip_pqsim:
                f = open(self.dump_path+".pqsim", 'rb')
                pqsim_res = pickle.load(f)
                f.close()
            else:
                pqsim_res = None
        
            return simulator_stat, pqsim_res

        if not ray.is_initialized():
            ray.init()
        start = timeit.default_timer()
        print("Simulation starts", flush=True)
        #
        while not self.sim_done: 
            self.run_cycle_transfer()
            self.run_cycle_update()
            self.run_cycle_tick()

        print("Last cycle: {}".format(self.cycle))
        sim_time = round(timeit.default_timer()-start, 3)
        print("Simulation ends: {} sec".format(sim_time))
       
        if not self.emulate:
            self.lq_state_dist_list_x = self.qxu.lq_state_dist_list_x
            self.lq_state_dist_list_y = self.qxu.lq_state_dist_list_y
            self.lq_state_dist_list_z = self.qxu.lq_state_dist_list_z
            self.lq_pchidx = self.qxu.cur_lq_pchidx
            self.lq_pchtype = self.qxu.cur_lq_pchtype
            self.lqsign_acc_x = self.lmu.lqsign_acc_x
            self.lqsign_acc_z = self.lmu.lqsign_acc_z
            self.byproduct_list = self.lmu.byproduct_list
            self.output_pfarray_list = self.pfu.output_pfarray_list
            
            # To print resultant value
            pqsim_res = self.get_logical_state()
        else: 
            pqsim_res = None

        simulator_stat = self.unit_stat_list
        if self.dump: 
            f = open(self.dump_path+".stat", 'wb')
            pickle.dump(simulator_stat, f)
            f.close()
            if not self.skip_pqsim:
                f = open(self.dump_path+".pqsim", 'wb')
                pickle.dump(pqsim_res, f)
                f.close()
        else:
            pass
        
        return simulator_stat, pqsim_res
    
    def run_cycle_transfer (self):
        ###### Transfer ######
        # QIF
        self.qif.transfer()
        # QID
        ### QIF -> QID
        self.qid.input_inst = self.qif.output_inst
        self.qid.input_instbuf_empty = self.qif.output_instbuf_empty
        self.qid.input_qifdone = self.qif.done
        self.qid.transfer()
        # PDU
        ### QID -> PDU
        self.pdu.input_from_qid = self.qid.output_to_pchdec 
        self.pdu.input_pchdecbuf_empty = self.qid.output_pchdecbuf_empty
        self.pdu.transfer()
        # PIU
        ### PDU -> PIU
        self.piu.input_pdu_valid = self.pdu.output_valid
        self.piu.input_opcode = self.pdu.output_opcode
        self.piu.input_pch_list = self.pdu.output_pch_list
        self.piu.input_pchpp_list = self.pdu.output_pchpp_list
        self.piu.input_pchop_list = self.pdu.output_pchop_list 
        self.piu.input_pchmreg_list = self.pdu.output_pchmreg_list
        self.piu.transfer()
        # PSU
        ## PIU -> PSU
        self.psu.input_topsu_valid = self.piu.output_topsu_valid
        self.psu.input_pchinfo = self.piu.output_pchinfo
        self.psu.input_opcode = self.piu.output_opcode
        self.psu.input_last_pchinfo = self.piu.output_last_pchinfo
        self.psu.transfer()
        # TCU
        ## PSU -> TCU
        self.tcu.input_valid = self.psu.output_valid
        self.tcu.input_cwdarray = self.psu.output_cwdarray
        self.tcu.input_opcode = self.psu.output_opcode
        self.tcu.input_timing = self.psu.output_timing
        self.tcu.transfer()
        # QXU
        ### TCU -> QXU
        self.qxu.input_cwd_array = self.tcu.output_cwdarray
        self.qxu.input_valid = self.tcu.output_valid
        self.qxu.input_current_cycle = self.cycle
        # EDU
        ### QXU -> EDU
        self.edu.input_aqmeas_valid = self.qxu.output_aqmeas_valid 
        self.edu.input_aqmeas_array     = self.qxu.output_aq_meas_mem 
        self.edu.input_dqmeas_valid = self.qxu.output_dqmeas_valid 
        self.edu.input_dqmeas_array = self.qxu.output_dq_meas_mem 
        ### PIU -> EDU
        self.edu.input_pchinfo_valid   = self.piu.output_topsu_valid
        self.edu.input_pchinfo         = self.piu.output_pchinfo
        self.edu.input_last_pchinfo    = self.piu.output_last_pchinfo
        self.edu.input_piu_opcode  = self.piu.output_opcode 
        ### TCU -> EDU
        self.edu.input_tcu_opcode = self.tcu.output_opcode 
        self.edu.input_tcu_valid = self.tcu.output_valid 
        self.edu.transfer()
        # PFU
        ### PIU -> PFU
        self.pfu.input_topsu_valid = self.piu.output_topsu_valid
        self.pfu.input_pchinfo = self.piu.output_pchinfo
        self.pfu.input_last_pchinfo = self.piu.output_last_pchinfo
        self.pfu.input_piu_opcode = self.piu.output_opcode
        ### TCU -> PFU
        self.pfu.input_tcu_valid = self.tcu.output_valid 
        self.pfu.input_tcu_opcode = self.tcu.output_opcode 
        ### EDU -> PFU
        self.pfu.input_error_array = self.edu.output_error_array
        self.pfu.input_error_valid = self.edu.output_valid
        self.pfu.input_pfflag = self.edu.output_pfflag
        self.pfu.transfer()
        # LMU
        ### QID -> LMU
        self.lmu.input_to_lqmeas = self.qid.output_to_lqmeas
        self.lmu.input_lqmeasbuf_empty = self.qid.output_lqmeasbuf_empty
        ### PIU -> LMU
        self.lmu.input_pchinfo = self.piu.output_pchinfo
        self.lmu.input_tolmu_valid = self.piu.output_tolmu_valid
        self.lmu.input_last_pchinfo = self.piu.output_last_pchinfo
        ### TCU -> LMU
        self.lmu.input_opcode = self.tcu.output_opcode
        self.lmu.input_opcode_valid = self.tcu.output_valid
        ### EDU -> LMU
        self.lmu.input_aqmeas_array = self.edu.output_eigen_array 
        self.lmu.input_aqmeas_valid = self.edu.output_valid
        ### QXU -> LMU
        self.lmu.input_dqmeas_array = self.qxu.output_dq_meas_mem
        self.lmu.input_dqmeas_valid = self.qxu.output_dqmeas_valid
        ### PFU -> LMU
        self.lmu.input_pf_array = self.pfu.output_pfarray
        self.lmu.input_pf_valid = self.pfu.output_valid
        self.lmu.transfer()
        # LMU & QID
        self.qid.input_xorz = self.lmu.output_xorz
        self.qid.transfer()
        self.lmu.input_a_taken = self.qid.output_a_taken
        self.lmu.transfer()

        # Stall & Ready signal
        physched_pchwr_stall = (self.piu.output_topsu_valid and (self.psu.pchinfo_full or self.pfu.pchinfo_full)) 
        lqmeas_pchwr_stall = (self.piu.output_tolmu_valid and self.lmu.pchinfo_full)
        ### LMU
        if self.piu.output_topsu_valid and self.piu.output_tolmu_valid:
            self.lmu.input_pchwr_stall = physched_pchwr_stall or lqmeas_pchwr_stall
        else:
            self.lmu.input_pchwr_stall = lqmeas_pchwr_stall
        self.lmu.transfer()

        ### PFU
        if self.piu.output_topsu_valid and self.piu.output_tolmu_valid:
            self.pfu.input_pchwr_stall = physched_pchwr_stall or lqmeas_pchwr_stall
        else:
            self.pfu.input_pchwr_stall = physched_pchwr_stall
        self.pfu.transfer()
        ### EDU
        self.edu.input_stall = self.piu.input_stall
        self.edu.input_pchwr_stall = physched_pchwr_stall
        self.edu.transfer()
        ### PSU
        self.psu.input_cwdgen_stall = self.psu.output_valid and self.tcu.output_timebuf_full
        self.psu.input_timebuf_full = self.tcu.output_timebuf_full
        if self.piu.output_topsu_valid and self.piu.output_tolmu_valid:
            self.psu.input_pchwr_stall = physched_pchwr_stall or lqmeas_pchwr_stall
        else:
            self.psu.input_pchwr_stall = physched_pchwr_stall
        self.psu.transfer()
        ### PIU
        self.piu.input_stall = physched_pchwr_stall or lqmeas_pchwr_stall
        self.piu.transfer()
        ### PDU
        self.pdu.input_stall = self.pdu.output_valid and (self.piu.input_stall or not self.piu.take_input)
        self.pdu.transfer()
        ### QID
        self.qid.input_pchdecbuf_ready = self.pdu.take_input and not self.pdu.input_stall
        self.qid.input_lqmeasbuf_ready = (not self.lmu.instinfo_full)
        self.qid.transfer()
        ### QIM
        self.qif.input_instbuf_ready = (not self.qid.output_instdec_stall)
        self.qif.transfer()

        ###### Debug ######
        if self.debug:
            self.qif.debug()
            self.qid.debug()
            self.pdu.debug()
            self.piu.debug()
            self.psu.debug()
            self.tcu.debug()
            self.qxu.debug()
            self.edu.debug()
            self.pfu.debug()
            self.lmu.debug()
        return

    def run_cycle_update(self):
        if not self.emulate:
            self.qxu.save_current_logical_state()
            self.lmu.save_internal_value()
            self.pfu.save_internal_value()

        ###### Update ######
        self.lmu.update(self.cycle)
        self.pfu.update(self.cycle)
        self.edu.update(self.cycle)
        self.qxu.update(self.cycle)
        self.tcu.update(self.cycle)
        self.psu.update(self.cycle)
        self.piu.update(self.cycle)
        self.pdu.update(self.cycle)
        self.qid.update(self.cycle)
        self.qif.update(self.cycle)
        return

    def run_cycle_tick(self):
        ###### End signal ######
        done_cond = self.qif.done
        done_cond = done_cond and self.qid.done
        done_cond = done_cond and (self.pdu.state == "empty")
        done_cond = done_cond and (self.piu.state == "ready")
        done_cond = done_cond and (self.psu.state == "ready" and not self.psu.pchinfo_srmem.output_notempty) 
        done_cond = done_cond and self.tcu.output_timebuf_empty
        done_cond = done_cond and not (bool(self.qxu.dq_meas_mem) or bool(self.qxu.aq_meas_mem))
        done_cond = done_cond and (self.pfu.state == "ready")
        done_cond = done_cond and self.lmu.done

        if done_cond: 
            self.sim_done = True
        else: 
            pass
        self.cycle += 1
        if self.cycle % 100 == 0: 
            print("qif.done:",self.qif.done)
            print("qid.done:",self.qid.done)
            print("pdu.done:",self.pdu.state == "empty")
            print("piu.done:",self.piu.state == "ready")
            print("psu.done:",self.psu.state == "ready")
            print("tcu.done:",self.tcu.output_timebuf_empty)
            print("qxu.done:",not (bool(self.qxu.dq_meas_mem) or bool(self.qxu.aq_meas_mem)))
            print("pfu.done:",self.pfu.state == "ready")
            print("lmu.done:",self.lmu.done)
            ###### 
            if not self.debug:
                print("Cycle: ", self.cycle)
            print("sim_done: {}".format(self.sim_done), flush=True)
        if self.debug: 
            print("Cycle: ", self.cycle)
        return


    def get_logical_state (self):

        # A probability for measurement of all qubits
        lq_state_dist_list_x = self.lq_state_dist_list_x
        lq_state_dist_list_y = self.lq_state_dist_list_y
        lq_state_dist_list_z = self.lq_state_dist_list_z
        
        # lq to pchidx mapping
        lq_pchidx = self.lq_pchidx
        lq_pchtype = self.lq_pchtype
        
        # lmu.lqsign_acc_reg extracted per ppr
        lop_sign_x = self.lqsign_acc_x
        lop_sign_z = self.lqsign_acc_z
        
        # lmu.byproduct extracted per ppr
        byproduct = self.byproduct_list
        
        # psu.output_pfarray
        output_pfarray = self.output_pfarray_list
        
        ## Apply accumulated sign to raw state
        sign_corrected_state_x = []
        sign_corrected_state_y = []
        sign_corrected_state_z = []
        for cx, cy, cz, sx, sz in zip(lq_state_dist_list_x, lq_state_dist_list_y, lq_state_dist_list_z, lop_sign_x, lop_sign_z):
            sy = ['+' if x == z else '-' for (x,z) in zip(sx,sz)]
            
            _cx = apply_lop_sign(cx, sx)
            _cy = apply_lop_sign(cy, sy)
            _cz = apply_lop_sign(cz, sz)
            sign_corrected_state_x.append(_cx)
            sign_corrected_state_y.append(_cy)
            sign_corrected_state_z.append(_cz)
            
        # Apply byproduct to sign-corrected state
        bp_corrected_state_x = []
        bp_corrected_state_y = []
        bp_corrected_state_z = []
        for cx, cy, cz, bp in zip(sign_corrected_state_x, sign_corrected_state_y, sign_corrected_state_z, byproduct):

            sx = ['-' if b == 'Z' or b == 'Y' else '+' for b in bp]
            sy = ['-' if b == 'Z' or b == 'X' else '+' for b in bp]
            sz = ['-' if b == 'X' or b == 'Y' else '+' for b in bp]
            _cx = apply_lop_sign(cx, sx)
            _cy = apply_lop_sign(cy, sy)
            _cz = apply_lop_sign(cz, sz)
            bp_corrected_state_x.append(_cx)
            bp_corrected_state_y.append(_cy)
            bp_corrected_state_z.append(_cz)

        # Apply pauliframe to sign-corrected & byproduct-corrected state
        final_state_x = []
        final_state_y = []
        final_state_z = []
        for cx, cy, cz, pfarray in zip(bp_corrected_state_x, bp_corrected_state_y, bp_corrected_state_z, output_pfarray):
            pf_product_list_x = []
            pf_product_list_y = []
            pf_product_list_z = []

            for target_pchidx, target_pchtype in zip(lq_pchidx, lq_pchtype):
                qb_lop_x, qb_lop_z = get_lop_qb(target_pchidx, target_pchtype, self.param.code_dist)
                pf_product_x = 0
                pf_product_z = 0

                for pf in [pfarray[idx] for idx in qb_lop_z]:
                    pf_product_z ^= int(pf == 'x' or pf == 'y')
                for pf in [pfarray[idx] for idx in qb_lop_x]:
                    pf_product_x ^= int(pf == 'z' or pf == 'y')
                pf_product_y = pf_product_x ^ pf_product_z
                
                pf_product_list_x.append(pf_product_x)
                pf_product_list_y.append(pf_product_y)
                pf_product_list_z.append(pf_product_z)
            
            sx = ['-' if (p==1) else '+' for p in pf_product_list_x]
            sy = ['-' if (p==1) else '+' for p in pf_product_list_y]
            sz = ['-' if (p==1) else '+' for p in pf_product_list_z]
            _cx = apply_lop_sign(cx, sx)
            _cy = apply_lop_sign(cy, sy)
            _cz = apply_lop_sign(cz, sz)
            final_state_x.append(_cx)
            final_state_y.append(_cy)
            final_state_z.append(_cz)
        
        cx = final_state_x[-1]
        cy = final_state_y[-1]
        cz = final_state_z[-1]
        res_dict = {"cx": cx, "cy": cy, "cz": cz}

        return res_dict


### MAIN ###
def main(argv):
    config = FLAGS.config
    qbin = FLAGS.qbin
    num_shots = FLAGS.num_shots

    if FLAGS.dump_sim == "True":
        dump = True
    else:
        dump = False
    if FLAGS.regen_sim == "True":
        regen = True
    else:
        regen = False
    if FLAGS.skip_pqsim == "True":
        skip_pqsim = True
    else:
        skip_pqsim = False
    if FLAGS.debug == "True":
        debug = True
    else:
        debug = False
    b_format = compile("{}_n{}") 
    _, str_lq = b_format.parse(qbin)
    num_lq = int(str_lq)+2 # total number of lq

    simulator = xq_simulator()
    simulator.setup(
            config=config,
            qbin=qbin,
            num_lq=num_lq,
            skip_pqsim=skip_pqsim,
            num_shots=num_shots,
            dump=dump,
            regen=regen,
            debug=debug)

    simulator_res, pqsim_res = simulator.run()

    print("****** XQ-simulator Result - Cycle-level Simulation stat ******")
    show_simulator_stat(simulator_res)

    print("****** XQ-simulator Result - Loigcal-qubit quantum state distribution ******")
    for basis, s_dict in pqsim_res.items():
        if basis == "cx": 
            basis = "X"
        elif basis == "cy":
            basis = "Y"
        elif basis == "cz":
            basis = "Z"
            
        print("****** Measurement basis: {} ******".format(basis))
        for state, prob in s_dict.items():
            if prob <= 0:
                continue
            print("{}: {}".format(state, round(prob, 5)))
        print()

    return

if __name__ == "__main__":
    FLAGS = flags.FLAGS
    flags.DEFINE_string("config", "example_cmos_d5", "target config name", short_name='c')
    flags.DEFINE_string("qbin", "pprIIZZZ_n5", "target quantum binary", short_name='b')
    flags.DEFINE_integer("num_shots", 2048, "num shots for ftn. correct mode", short_name='s')
    flags.DEFINE_string("dump_sim", "False", "dump or not", short_name='di')
    flags.DEFINE_string("regen_sim", "False", "regen or not", short_name='ri')
    flags.DEFINE_string("skip_pqsim", "False", "skip physical-qubit level quantum simulation", short_name='sp')
    flags.DEFINE_string("debug", "False", "debug or not", short_name='db')
    app.run(main)
