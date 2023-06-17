from IPython.display import display
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from qiskit.visualization import plot_histogram

def show_simulator_stat(unit_stat_list):
    for unit_stat in unit_stat_list:
        print("****** {} - {} ******".format(unit_stat.name, unit_stat.uarch))

        if unit_stat.name == "QXU":
            activation = 0
        else:
            activation = round(unit_stat.num_acc_cyc/unit_stat.num_update_cyc, 3)
        print("Activation: {}".format(activation))
        print()

        print("Data transfer: ")
        for dst, stat in unit_stat.data_transfer.items(): 
            df = pd.DataFrame(stat).drop_duplicates()
            blank_idx = ['']*len(df)
            df.index = blank_idx
            print("From {} - To {}".format(unit_stat.name, dst))
            display(df)
            print()

        if unit_stat.name == "EDU":
            df = pd.DataFrame(unit_stat.edu_cycle_result)
            blank_idx = ['']*len(df)
            df.index = blank_idx
            print("EDU cycles: ")
            display(df)
            print()
        
        if unit_stat.name == "TCU":
            df = pd.DataFrame(unit_stat.bw_req).drop_duplicates()
            blank_idx = ['']*len(df)
            df.index = blank_idx
            print("Inst. sent from TCU to QXU: ")
            display(df) 
            print()
    return 

def show_estimator_result(unit_stat_list, sfq_detail=False):
    col_list = ["Name", "Microarchi", "Temp", "Tech", "Freq(GHz)", "Pstat(mW)", "Pdyn_max(mW)"]
    df = pd.DataFrame(columns=col_list)
    for unit_stat in unit_stat_list:
        if unit_stat.name in ["QIM", "QXU"]: 
            continue
        entry = [unit_stat.name, unit_stat.uarch, unit_stat.temp, unit_stat.tech, unit_stat.freq, unit_stat.p_stat, unit_stat.p_dyn]
        df.loc[len(df)] = entry
    blank_idx = ['']*len(df)
    df.index = blank_idx

    display(df)
    print()
    
    for unit_stat in unit_stat_list: 
        if unit_stat.name in ["QIM", "QXU"]:
            continue
        if sfq_detail and unit_stat.tech in ["RSFQ", "ERSFQ"]:
            print("{} - {} detail".format(unit_stat.name, unit_stat.tech))
            display(unit_stat.munit_df)
            print()
    return


def draw_pqsim_res(pqsim_res, lqsim_res):
    _pqsim_res = dict()
    for basis, res in pqsim_res.items():
        _pqsim_res[basis] = dict()
        for state, prob in res.items():
            # _state = state[4:]
            _state = state[2:]
            try:
                _pqsim_res[basis][_state] += prob
            except:
                _pqsim_res[basis][_state] = prob
    _lqsim_res = dict()
    for basis, res in lqsim_res.items():
        _lqsim_res[basis] = dict()
        for state, prob in res.items():
            # _state = state[2:]
            _state = state[:]
            try:
                _lqsim_res[basis][_state] += prob
            except:
                _lqsim_res[basis][_state] = prob
    
    pqsim_dict = pd.DataFrame(_pqsim_res).to_dict()
    lqsim_dict = pd.DataFrame(_lqsim_res).to_dict()
    for basis in _pqsim_res:
        _n_qubit = len(next(iter(_pqsim_res[basis])))
        _all_states = [bin(i)[2:].zfill(_n_qubit) for i in range(2 ** _n_qubit)]
        _pqsim_dict = {k: v if not pd.isna(v) else 0 for (k,v) in pqsim_dict[basis].items()}
        _pqsim_prob = {s: _pqsim_dict.get(s, 0) for s in _all_states}
    
        _lqsim_dict = {k: v if not pd.isna(v) else 0 for (k,v) in lqsim_dict[basis].items()}
        _lqsim_prob = {s: _lqsim_dict.get(s, 0) for s in _all_states}

        sim_df = pd.DataFrame({
            'XQ-simulator': _pqsim_prob,
            'Qiskit': _lqsim_prob
        })
        #
        title_sz = 24
        label_sz = 20
        tick_sz = 16
        legend_sz = 16

        sim_df.plot(y=['XQ-simulator', 'Qiskit'], kind='bar', figsize=(20,4))
        plt.title("XQ-simulator: Logical qubit state distribution measured in {} basis".format(basis[1].upper())).set_fontsize(title_sz)
        plt.xlabel("Qubit state").set_fontsize(label_sz)
        plt.ylabel("Probability").set_fontsize(label_sz)
        plt.legend(prop={'size': legend_sz})
        plt.ylim(0, 1.4*max(sim_df["XQ-simulator"]))
        plt.xticks(fontsize=tick_sz)
        plt.yticks(fontsize=tick_sz)
    return


def summarize_simres(xqsim_res):
    print("Target qubit scale: {} physical qubits\n".format(xqsim_res["num_pq"]))

    print("*** Instruction bandwidth ***")
    print("Instruction bandwidth value: {} Gbps".format(xqsim_res["inst_bw_val"]))
    print("Instruction bandwidth requirement (Max): {} Gbps".format(xqsim_res["inst_bwreq_max"]))
    print("Instruction bandwidth requirement (Avg): {} Gbps".format(xqsim_res["inst_bwreq_avg"]))
    print()


    print("*** Error decoding latency ***")
    print("Error decoding latency (Max): {} ns".format(xqsim_res["edu_latency_max"]))
    print("Error decoding latency (Avg): {} ns".format(xqsim_res["edu_latency_avg"]))
    print("ESM cycle latency: {} ns".format(xqsim_res["edu_latency_const"]))
    print()

    print("*** 4K power consumption ***")
    print("4K device power consumption (Max): {} mW".format(xqsim_res["pdev_4K_max"]))
    print("4K device power consumption (Activation): {} mW".format(xqsim_res["pdev_4K_acc"]))
    print("300K-to-4K data transfser's 4K heat (Max): {} mW".format(xqsim_res["pwire_4K_max"]))
    print("300K-to-4K data transfser's 4K heat (Avg): {} mW".format(xqsim_res["pwire_4K_avg"]))
    print("4K power budget: {} mW".format(xqsim_res["power_4K_const"]))
    print()
  
    print("*** Check scalability (Optimistic) ***")
    ibw_sat_opt = (xqsim_res["inst_bwreq_avg"] < xqsim_res["inst_bw_val"])
    edl_sat_opt = (xqsim_res["edu_latency_avg"] < xqsim_res["edu_latency_const"])
    p4K_sat_opt = ((xqsim_res["pdev_4K_acc"]+xqsim_res["pwire_4K_avg"]) < xqsim_res["power_4K_const"])

    if ibw_sat_opt and edl_sat_opt and p4K_sat_opt:
        print("SUCCESS (Optimistic)")
    else:
        if not ibw_sat_opt:
            print("FAIL: Instruction bandwidth (Avg)")
        if not edl_sat_opt:
            print("FAIL: Error decoding latency (Avg)")
        if not p4K_sat_opt:
            print("FAIL: 4K power consumption (Acc+Avg)")
    print()      

    print("*** Check scalability (Pessimistic) ***")
    ibw_sat_pes = (xqsim_res["inst_bwreq_max"] < xqsim_res["inst_bw_val"])
    edl_sat_pes = (xqsim_res["edu_latency_max"] < xqsim_res["edu_latency_const"])
    p4K_sat_pes = ((xqsim_res["pdev_4K_max"]+xqsim_res["pwire_4K_max"]) < xqsim_res["power_4K_const"])

    if ibw_sat_pes and edl_sat_pes and p4K_sat_pes:
        print("SUCCESS (Pessimistic)")
    else:
        if not ibw_sat_pes:
            print("FAIL: Instruction bandwidth (Max)")
        if not edl_sat_pes:
            print("FAIL: Error decoding latency (Max)")
        if not p4K_sat_pes:
            print("FAIL: 4K power consumption (Max)")
    print()
    return


def draw_simres_scaling(simres_list, config):
    simres_dict = dict()
    for simres in simres_list: 
        if not simres_dict:
            for key, val in simres.items(): 
                simres_dict[key] = [0] 
                simres_dict[key].append(val)
        else:
            for key, val in simres.items():
                simres_dict[key].append(simres[key])

    simres_df = pd.DataFrame(simres_dict)

    #   
    title_sz = 24
    label_sz = 20
    tick_sz = 18
    legend_sz = 18
    lw = 3 
    
    #  inst bw
    inst_bw_df = simres_df[["num_pq", "inst_bw_val", "inst_bwreq_max"]].set_index("num_pq")
    inst_bw_df.rename(columns={"inst_bw_val": "Inst. BW Value", "inst_bwreq_max": "Inst. BW Requirement (max)"}, inplace=True)
    inst_bw_df.plot.line(figsize=(20,4), marker="o", linewidth=lw)
    plt.xlim([0, max(inst_bw_df.index)])
    plt.title("{}: Instruction bandwidth (Gbps)".format(config)).set_fontsize(title_sz)
    plt.xlabel("Number of phyiscal qubits").set_fontsize(label_sz)
    plt.ylabel("Bandwidth (Gbps)").set_fontsize(label_sz)
    plt.legend(prop={'size': legend_sz})
    plt.xticks(fontsize=tick_sz)
    plt.yticks(fontsize=tick_sz)
    plt.show()

    
    #   4K power
    power_budget_4k = max(simres_df["power_4K_const"])
    power_4kdev_df = simres_df[["num_pq", "pdev_4K_max"]].set_index("num_pq")
    power_300kto4k_df = simres_df[["num_pq", "pwire_4K_max"]].set_index("num_pq")
    
    plt.figure(figsize = (20, 4))
    plt.plot(simres_df["num_pq"], simres_df["pdev_4K_max"], 'o-', label="4K device power", linewidth=lw)
    plt.plot(simres_df["num_pq"], simres_df["pwire_4K_max"], 'o-', label="300K-to-4K cable heat", linewidth=lw)
    plt.axhline(y=power_budget_4k, color='r', linewidth=lw, label="4K power budget")
    plt.xlim([0, max(simres_df["num_pq"])])
    plt.ylim([0, 4*power_budget_4k])
    plt.title("{}: 4K power consumption (mW)".format(config)).set_fontsize(title_sz)
    plt.xlabel("Number of phyiscal qubits").set_fontsize(label_sz)
    plt.ylabel("Power (mW)").set_fontsize(label_sz)
    plt.legend(prop={'size': legend_sz})
    plt.xticks(fontsize=tick_sz)
    plt.yticks(fontsize=tick_sz)
    plt.show()
    
    #''' 
    # 
    esm_latency = max(simres_df["edu_latency_const"])
    edu_lat_df = simres_df[["num_pq", "edu_latency_max"]].set_index("num_pq")
    edu_lat_df.rename(columns={"edu_latency_max": "Error decoding latency"}, inplace=True)
    edu_lat_df.plot.line(figsize=(20,4), marker='o', linewidth=lw)
    plt.axhline(y=esm_latency, color='r', linewidth=lw, label="ESM latency")
    plt.xlim([0, max(edu_lat_df.index)])
    plt.ylim([0, 4*esm_latency])
    plt.title("{}: Error decoding latency (ns)".format(config)).set_fontsize(title_sz)
    plt.xlabel("Number of physical qubits").set_fontsize(label_sz)
    plt.ylabel("Latency (ns)").set_fontsize(label_sz)
    plt.legend(prop={'size': legend_sz})
    plt.xticks(fontsize=tick_sz)
    plt.yticks(fontsize=tick_sz)
    plt.show()
    return
