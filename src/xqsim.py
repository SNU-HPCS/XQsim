import os, sys 

curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
sim_dir = os.path.join(curr_dir, "XQ-simulator")
est_dir = os.path.join(curr_dir, "XQ-estimator")
#
sys.path.insert(0, sim_dir)
sys.path.insert(0, est_dir)
#
from absl import flags
from absl import app
#
from parse import compile
# 
from xq_simulator import xq_simulator
from xq_estimator import xq_estimator
from sim_param import sim_param
from visualization import *

#
import ray
import time
from multiprocessing import Process, Queue
import numpy as np
import pandas as pd
from math import ceil
pd.set_option("display.max_rows", 999)
#
from IPython.display import display

class xqsim:
    def __init__(self):
        # input
        self.config = None
        self.qbin = None
        self.num_lq = None
        self.num_shots = None
        self.dump_synth = None
        self.regen_synth = None
        self.dump_est = None
        self.regen_est = None
        self.dump_sim = None
        self.regen_sim = None
        self.skip_pqsim = None
        self.debug = None
        return

    def setup(self, 
              config=None, 
              qbin=None, 
              num_shots=None,
              dump_synth=None,
              regen_synth=None,
              dump_est=None,
              regen_est=None,
              dump_sim=None,
              regen_sim=None,
              skip_pqsim=None,
              debug=None):
        #
        self.config = config
        self.qbin = qbin
        self.num_shots = num_shots
        self.dump_synth = dump_synth
        self.regen_synth = regen_synth
        self.dump_est = dump_est
        self.regen_est = regen_est
        self.dump_sim = dump_sim
        self.regen_sim = regen_sim
        self.skip_pqsim = skip_pqsim
        self.debug = debug
        #
        b_format = compile("{}_n{}") 
        _, str_lq = b_format.parse(self.qbin)
        self.num_lq = int(str_lq)+2 # total number of lq

        return

    def run(self):
        # estimator
        self.estimator = xq_estimator()
        self.estimator.setup(
                config = self.config, 
                num_lq = self.num_lq,
                dump_synth = self.dump_synth,
                regen_synth = self.regen_synth,
                dump_est = self.dump_est,
                regen_est = self.regen_est
                )
        estimator_stat = self.estimator.run()

        # simulator
        self.simulator = xq_simulator()
        self.simulator.setup(
                config = self.config,
                qbin = self.qbin,
                num_lq = self.num_lq,
                skip_pqsim = self.skip_pqsim,
                num_shots = self.num_shots,
                dump = self.dump_sim, 
                regen = self.regen_sim,
                debug = self.debug
               )
        simulator_stat, pqsim_res = self.simulator.run()

        #scalability metrics
        xqsim_res = self.gen_xqsim_res(estimator_stat, simulator_stat)
        return xqsim_res, pqsim_res


    def gen_xqsim_res(self, estimator_stat, simulator_stat):
        param = self.simulator.param
        #
        pdev_4K_max = 0
        pdev_4K_acc = 0
        transfer_df = None

        #
        for est_stat, sim_stat in zip(estimator_stat, simulator_stat):
            assert est_stat.name == sim_stat.name
            name = est_stat.name 

            # inst_bwreq
            if name == "TCU":
                inst_bwreq_max, inst_bwreq_avg = get_inst_bw_res(est_stat, sim_stat)

            # inst_bw_val
            if name == "PSU":
                inst_bw_val = est_stat.psu_inst_bw

            # edu_latency
            if name == "EDU":
                edu_latency_max, edu_latency_avg = get_edu_latency_res(est_stat, sim_stat)

            # 4K device power
            if est_stat.temp == "4K" and not est_stat.name in ["QIM", "QXU"]:
                u_pdev_4K_max, u_pdev_4K_acc = get_pdev_4K_res(est_stat, sim_stat)
                pdev_4K_max += u_pdev_4K_max
                pdev_4K_acc += u_pdev_4K_acc

            # data transfer
            if sim_stat.data_transfer:
                transfer_unit_df = get_transfer_unit(est_stat, sim_stat)
                try: 
                    transfer_df = pd.concat([transfer_df, transfer_unit_df], ignore_index=True)
                except:
                    transfer_df = transfer_unit_df
        # 300K-4K data transfer
        gbps_300K_4K_max, gbps_300K_4K_avg = get_gbps_300K_4K_res(transfer_df, estimator_stat)
        ## 300K-4K wire heat
        pwire_4K_max = round(param.cable_heat_300kto4k * gbps_300K_4K_max, 2)
        pwire_4K_avg = round(param.cable_heat_300kto4k * gbps_300K_4K_avg, 2) # mW

        # others
        ## esm_latency 
        esm_latency = 0
        esm_seq = self.simulator.psu.cwdNtime_srmem["RESM"]
        for entry in esm_seq:
            cwd = entry[1]
            if cwd == "h":
                esm_latency += param.sqgate_ns
            elif cwd == "cz":
                esm_latency += param.tqgate_ns
            elif cwd == "meas":
                esm_latency += param.meas_ns
            else:
                raise Exception()

        # wrap up
        xqsim_res = dict()
        ##
        xqsim_res["inst_bwreq_max"] = inst_bwreq_max
        xqsim_res["inst_bwreq_avg"] = inst_bwreq_avg
        xqsim_res["inst_bw_val"] = inst_bw_val
        xqsim_res["edu_latency_max"] = edu_latency_max
        xqsim_res["edu_latency_avg"] = edu_latency_avg
        xqsim_res["pdev_4K_max"] = pdev_4K_max
        xqsim_res["pdev_4K_acc"] = pdev_4K_acc
        xqsim_res["gbps_300K_4K_max"] = gbps_300K_4K_max
        xqsim_res["gbps_300K_4K_avg"] = gbps_300K_4K_avg
        xqsim_res["pwire_4K_max"] = pwire_4K_max
        xqsim_res["pwire_4K_avg"] = pwire_4K_avg
        ## 
        xqsim_res["edu_latency_const"] = esm_latency
        xqsim_res["power_4K_const"] = param.power_budget_4k
        ##
        xqsim_res["num_pq"] = param.num_pq
        xqsim_res["num_pq_eff"] = param.num_pq_eff

        return xqsim_res
###
def get_inst_bw_res(tcu_est_stat, tcu_sim_stat):
    bwreq_df = pd.DataFrame(tcu_sim_stat.bw_req)
    bwreq_df["bwreq"] = (bwreq_df["bit_eff"]/bwreq_df["cycle"]) # Gbps (simulator's 1 cycle = 1ns)
    inst_bwreq_max = round(max(bwreq_df["bwreq"]), 3)
    #
    inst_bwreq_avg = (sum(bwreq_df["bit_eff"])/sum(bwreq_df["cycle"]))
    inst_bwreq_avg = round(inst_bwreq_avg, 3)
    
    return inst_bwreq_max, inst_bwreq_avg


def get_edu_latency_res(edu_est_stat, edu_sim_stat):
    # edu cycle
    if edu_est_stat.tech in ["CMOS", "RSFQ", "ERSFQ"] and edu_est_stat.uarch == "baseline":
        edu_cycle_list = edu_sim_stat.edu_cycle_result["cyc_edu_running_list"]
    elif (edu_est_stat.tech == "CMOS" and edu_est_stat.uarch == "fast") or (edu_est_stat.tech in ["RESFQ", "ERSFQ"] and edu_est_stat.uarch in ["fast", "fastsliding"]):
        num_list_zip = zip(
                edu_sim_stat.edu_cycle_result["num_propagation_list"],
                edu_sim_stat.edu_cycle_result["num_token_setup_list"],
                edu_sim_stat.edu_cycle_result["num_error_match_list"],
                edu_sim_stat.edu_cycle_result["num_layer_retry_list"]
                )

        edu_cycle_list = []
        for (np, nt, ne, nl) in num_list_zip:
            edu_cycle = 0
            #
            edu_cycle += edu_est_stat.edu_cycle_param["token_setup_mf"]*(nt + nl + 1)
            #
            edu_cycle += edu_est_stat.edu_cycle_param["spike_propagation_mf"]*(np)
            #
            edu_cycle += edu_est_stat.edu_cycle_param["error_match_mf"]*(ne)
            edu_cycle_list.append(edu_cycle)
    else:
        raise Exception("xqsim - get_edu_latency_res: EDU with (uarch, tech) = ({}, {}) is not currently supported".format(edu_est_stat.uarch, edu_est_stat.tech))
    # edu latency
    edu_latency_list = [round(cyc/edu_est_stat.freq, 2) for cyc in edu_cycle_list] # ns
    edu_latency_max = max(edu_latency_list)
    edu_latency_avg = round(sum(edu_latency_list)/len(edu_latency_list), 2)
    
    return edu_latency_max, edu_latency_avg


def get_pdev_4K_res(est_stat, sim_stat):
    pstat_4K = est_stat.p_stat # mW
    pdyn_4K_max = est_stat.p_dyn # mW
    pdyn_4K_acc = est_stat.p_dyn * (sim_stat.num_acc_cyc/sim_stat.num_update_cyc)

    u_pdev_4K_max = round(pstat_4K + pdyn_4K_max, 2)
    u_pdev_4K_acc = round(pstat_4K + pdyn_4K_acc, 2)

    return u_pdev_4K_max, u_pdev_4K_acc


def get_transfer_unit(est_stat, sim_stat):
    cols = ["src", "dst", "max_gbps", "avg_gbps"]
    transfer_unit_df = pd.DataFrame(columns=cols)

    src = est_stat.name 
    for dst, stat in sim_stat.data_transfer.items():
        eff_bit_list = [num_eff * stat["bw"] for num_eff in stat["num_eff"]]
        if len(eff_bit_list) == 0:
            avg_gbps = 0
            max_gbps = 0
        else:
            if src in ["QIM", "QID", "PDU", "PIU"]:
                avg_gbps = round((sum(eff_bit_list)/sim_stat.num_update_cyc), 2)
                max_gbps = avg_gbps
            else:
                avg_gbps = round((sum(eff_bit_list)/stat["last_cyc"]), 2)
                eff_gbps_list = [round((eb/cyc), 2) for (eb, cyc) in zip(eff_bit_list, stat["cycle"])]
                max_gbps = max(eff_gbps_list)
        #
        row = [[src, dst, max_gbps, avg_gbps]]
        row_df = pd.DataFrame(row, columns=cols, index=[0])
        transfer_unit_df = pd.concat([transfer_unit_df, row_df], ignore_index=True)
   
    return transfer_unit_df 

def get_gbps_300K_4K_res(transfer_df, estimator_stat):
    gbps_300K_4K_max = 0
    gbps_300K_4K_avg = 0
    for _, row in transfer_df.iterrows():
        for est_stat in estimator_stat:
            if row["src"] == est_stat.name:
                src_temp = est_stat.temp
            if row["dst"] == est_stat.name: 
                dst_temp = est_stat.temp
        #
        if (src_temp == "300K" and dst_temp == "4K") or ( src_temp == "4K" and dst_temp == "300K"):
            gbps_300K_4K_max += row["max_gbps"]
            gbps_300K_4K_avg += row["avg_gbps"]
    
    return gbps_300K_4K_max, gbps_300K_4K_avg

##
def main(argv):
    #
    if FLAGS.dump_synth == "True":
        dump_synth = True
    else:
        dump_synth = False
    if FLAGS.regen_synth == "True":
        regen_synth = True
    else:
        regen_synth = False
    if FLAGS.dump_est == "True":
        dump_est = True
    else:
        dump_est = False
    if FLAGS.regen_est == "True":
        regen_est = True
    else:
        regen_est = False
    if FLAGS.dump_sim == "True":
        dump_sim = True
    else:
        dump_sim = False
    if FLAGS.regen_sim == "True":
        regen_sim = True
    else:
        regen_sim = False
    if FLAGS.skip_pqsim == "True":
        skip_pqsim = True
    else:
        skip_pqsim = False 
    if FLAGS.debug == "True":
        debug = True
    else:
        debug = False 

    #
    framework = xqsim()
    framework.setup(
            config=FLAGS.config, 
            qbin=FLAGS.qbin, 
            num_shots=FLAGS.num_shots,
            dump_synth=dump_synth,
            regen_synth=regen_synth,
            dump_est=dump_est,
            regen_est=regen_est,
            dump_sim=dump_sim,
            regen_sim=regen_sim,
            skip_pqsim=skip_pqsim,
            debug=debug
            )
    
    xqsim_res, pqsim_res = framework.run()
    
    summarize_simres(xqsim_res)

    return


if __name__ == "__main__":
    FLAGS = flags.FLAGS 
    flags.DEFINE_string("config", "example_cmos_d5", "target config name", short_name='c')
    flags.DEFINE_string("qbin", "pprIIZZZ_n5", "target quantum binary", short_name='b')
    flags.DEFINE_integer("num_shots", 512, "num shots for ftn. correct mode", short_name='s')
    flags.DEFINE_string("dump_synth",  "False", "dump synthesis results or not", short_name='ds')
    flags.DEFINE_string("regen_synth", "False", "re-generate synthesis results or not", short_name='rs')
    flags.DEFINE_string("dump_est", "False", "dump estimator's result or not", short_name='de')
    flags.DEFINE_string("regen_est", "False", "re-generate estimator's result or not", short_name='re')
    flags.DEFINE_string("dump_sim", "False", "dump or not", short_name='di')
    flags.DEFINE_string("regen_sim", "False", "regen or not", short_name='ri')
    flags.DEFINE_string("skip_pqsim", "False", "skip physical-qubit level quantum simulation", short_name='sp')
    flags.DEFINE_string("debug", "False", "debug or not", short_name='db')
    app.run(main)
