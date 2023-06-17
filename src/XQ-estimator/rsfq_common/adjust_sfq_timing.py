from absl import flags, app

import os
import pandas as pd 
import numpy as np
from math import *
import copy

curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
par_dir = os.path.join(curr_dir, os.pardir)

# 
gate_param_df = None
conn_df = None
bd_df = None
clk_conn_df = None
clk_bd_df = None
# 
split_trees = dict ()

#
buff_n = ""
ptl_n = ""
split_n = ""


def isNaN(arg):
    if type(arg) == float and isnan(arg):
        return True
    if type(arg) == str and arg.lower() == 'nan':
        return True
    else:
        return False

def init_clk_df():
    global conn_df, clk_conn_df, clk_bd_df
    global buff_n, ptl_n, split_n
    # Clock conn counts the number of wire cells in the critical path of each depth       
    clk_conn_df = pd.DataFrame(columns = ['Depth', 'stem_{}'.format(split_n), 'stem_{}'.format(buff_n), 'stem_{}'.format(ptl_n), 'br_{}'.format(split_n), 'br_{}'.format(ptl_n)]) 
    # Clock bd counts the number of total wire cells in the clock tree
    clk_bd_df = pd.DataFrame(columns = [split_n, buff_n, ptl_n])

    unit_depth = int(max(conn_df['Depth']))

    for depth in range(1, unit_depth):
        curr_width = len(conn_df.loc[conn_df['Depth'] == depth])
        curr_depth = ceil(log2(curr_width))
 
        # for clk_conn
        entry = [depth, 1, 0, 0, curr_depth, 0]
        clk_conn_df.loc[len(clk_conn_df)] = entry

    clk_conn_df = clk_conn_df.set_index("Depth")
    clk_bd_df.loc[0] = [0, 0, 0]
    return 

def cal_clkline_delay(input_clkconn_df, depth, part):
    global gate_param_df
   
    if not part in ['stem', 'br']:
        raise Exception("cal_clkline_delay - part")

    clk_conn_row = input_clkconn_df.loc[depth]

    clkline_delay = 0
    for name, num_gate in clk_conn_row.items():
        if name.split('_')[0] == part:
            gate_type = name.split('_')[1]
            gate_type = name.replace(part+"_", "")
            clkline_delay  += num_gate * gate_param_df.loc[gate_type, "Delay"]
    return clkline_delay

def cal_connection_delay(clk_scheme, input_clkconn_df, conn_entry, net):
    global gate_param_df 
    global buff_n, ptl_n, split_n
    
    buff_delay = gate_param_df.loc[buff_n, "Delay"]
    ptl_delay = gate_param_df.loc[ptl_n, "Delay"]
    split_delay = gate_param_df.loc[split_n, "Delay"]

    # gate_delay_net
    gate_net = conn_entry["{}_type".format(net)]
    if "input" in gate_net:
        gate_delay_net = 0
    else:
        gate_delay_net = gate_param_df.loc[gate_net, "Delay"]
    
    # wire_delay_net
    wire_delay_net = 0
    for g_name, val in conn_entry.items():
        if "split" in g_name and net in g_name:
            wire_delay_net += split_delay * val
        if "buff" in g_name and net in g_name:
            wire_delay_net += buff_delay * val
        if "ptl" in g_name and net in g_name:
            wire_delay_net += ptl_delay * val
    
    # data_delay & clock_delay
    depth = int(conn_entry["Depth"])
    loop_dist = conn_entry["{}_dist_loop".format(net)]
    from_loop = (loop_dist > 0)

    if clk_scheme == "concurrent":
        if from_loop:
            #
            clock_delay = cal_clkline_delay(input_clkconn_df, depth, "br")
            #
            data_delay = 0
            for level in range(depth+1, depth+loop_dist+1):
                data_delay += cal_clkline_delay(input_clkconn_df, level, "stem")
            data_delay += cal_clkline_delay(input_clkconn_df, depth+loop_dist, "br")
            data_delay += (gate_delay_net + wire_delay_net)
        else:
            #
            clock_delay = cal_clkline_delay(input_clkconn_df, depth, "stem")
            clock_delay += cal_clkline_delay(input_clkconn_df, depth, "br")
            #
            data_delay = 0
            if depth > 1:
                data_delay += cal_clkline_delay(input_clkconn_df, depth-1, "br")
            data_delay += (gate_delay_net + wire_delay_net)

    elif clk_scheme == "counter":
        if from_loop:
            #
            clock_delay = 0
            for level in range(depth+1, depth+loop_dist+1):
                clock_delay += cal_clkline_delay(input_clkconn_df, level, "stem")
            clock_delay += cal_clkline_delay(input_clkconn_df, depth, "br")
            #
            data_delay = cal_clkline_delay(input_clkconn_df, depth+loop_dist, "br")
            data_delay += (gate_delay_net + wire_delay_net) 
        else:
            if depth > 1:
                #
                clock_delay = cal_clkline_delay(input_clkconn_df, depth, "br")
                #
                data_delay = 0
                data_delay += cal_clkline_delay(input_clkconn_df, depth, "stem")
                data_delay += cal_clkline_delay(input_clkconn_df, depth-1, "br")
                data_delay +=  (gate_delay_net + wire_delay_net)
            else: # (depth == 1)
                clock_delay = 0
                for level in range(2, len(input_clkconn_df)+1):
                    clock_delay += cal_clkline_delay(input_clkconn_df, level, "stem")
                clock_delay += split_delay
                clock_delay += cal_clkline_delay(input_clkconn_df, 1, "br")
                data_delay = (gate_delay_net + wire_delay_net)

    else:
        raise Exception("cal_connection_delay - clk_scheme")

    return  data_delay, clock_delay


def cal_buff_ptl(timing_gap):
    global gate_param_df 
    global buff_n, ptl_n
    buff_delay = gate_param_df.loc[buff_n, "Delay"]
    ptl_delay = gate_param_df.loc[ptl_n, "Delay"]
    
    num_buff = floor(timing_gap / buff_delay)
    timing_gap -= num_buff * buff_delay

    num_ptl = ceil(timing_gap / ptl_delay)
    
    return num_buff, num_ptl


def adjust_datapath(clk_scheme, input_clkconn_df, input_conn_df):
    global gate_param_df
    ret_conn_df = input_conn_df.copy(deep=True)
    for idx, row in ret_conn_df.iterrows():
        gate_target = row["Type"]
        if 'output' in gate_target:
            continue

        gate_A = str(row["A_type"])
        gate_B = str(row["B_type"])
        depth = row["Depth"]
        
        A2B_time = gate_param_df.loc[gate_target, "A2BTime"]
        B2A_time = gate_param_df.loc[gate_target, "B2ATime"]
        C2I_time = gate_param_df.loc[gate_target, "C2ITime"]

        # 1. C2I constraint
        if not isNaN(gate_A):
            data_delay_A, clock_delay_A = cal_connection_delay(clk_scheme, input_clkconn_df, row, "A")
            delay_C2A = data_delay_A - clock_delay_A
            if C2I_time > delay_C2A:
                timing_gap = C2I_time - delay_C2A
                num_buff, num_ptl = cal_buff_ptl(timing_gap)
                row["A_buff"] += num_buff
                row["A_ptl"] += num_ptl

        if not isNaN(gate_B):
            data_delay_B, clock_delay_B = cal_connection_delay(clk_scheme, input_clkconn_df, row, "B")
            delay_C2B = data_delay_B - clock_delay_B
            if C2I_time > delay_C2B:
                timing_gap = C2I_time - delay_C2B
                num_buff, num_ptl = cal_buff_ptl(timing_gap)
                row["B_buff"] += num_buff
                row["B_ptl"] += num_ptl

        # 2. A2B & B2A timing 
        if (isNaN(gate_A) or 'input' in gate_A) or (isNaN(gate_B) or 'input' in gate_B):
            pass
        else:
            data_delay_A, _ = cal_connection_delay(clk_scheme, input_clkconn_df, row, "A")
            data_delay_B, _ = cal_connection_delay(clk_scheme, input_clkconn_df, row, "B")

            if data_delay_A >= data_delay_B:
                delay_B2A = data_delay_A - data_delay_B
                timing_gap = abs(B2A_time - delay_B2A)
                num_buff, num_ptl = cal_buff_ptl(timing_gap)
                

                if B2A_time > delay_B2A:
                    row["A_buff"] += num_buff
                    row["A_ptl"] += num_ptl
                else: 
                    row["B_buff"] += num_buff
                    if num_ptl > 0:
                        row["B_ptl"] += (num_ptl-1)
            else: # data_delay_A <= data_delay_B
                delay_A2B = data_delay_B - data_delay_A
                timing_gap = abs(A2B_time - delay_A2B)
                num_buff, num_ptl = cal_buff_ptl(timing_gap)

                if A2B_time > delay_A2B:
                    row["B_buff"] += num_buff
                    row["B_ptl"] += num_ptl
                else: 
                    row["A_buff"] += num_buff
                    if num_ptl > 0:
                        row["A_ptl"] += (num_ptl-1)
        ret_conn_df.loc[idx] = row
    ret_conn_df = ret_conn_df.sort_values(by=['Depth'], ascending=True)

    return ret_conn_df


def cal_min_cct(clk_scheme, input_clkconn_df, input_conn_df):
    global gate_param_df

    ret_conn_df = input_conn_df.copy(deep=True)
    ret_conn_df['MinCCT'] = [np.nan]*len(ret_conn_df.index)
    
    for idx, row in ret_conn_df.iterrows():
        gate_target = row["Type"]
        #
        if 'output' in gate_target:
            continue

        #       
        gate_A = row["A_type"]
        gate_B = row["B_type"]

        if not isNaN(gate_A):
            data_delay_A, clock_delay_A = cal_connection_delay(clk_scheme, input_clkconn_df, row, "A")
            delay_C2A = data_delay_A - clock_delay_A
        else:
            delay_C2A = 0
        
        if not isNaN(gate_B):
            data_delay_B, clock_delay_B = cal_connection_delay(clk_scheme, input_clkconn_df, row, "B")
            delay_C2B = data_delay_B - clock_delay_B
        else:
            delay_C2B = 0

        delay_C2I = max(delay_C2A, delay_C2B)
        if delay_C2I == 0: # A and B are inputs
            continue

        #
        I2I_time = gate_param_df.loc[gate_target, "I2ITime"]
        I2I_time = max(I2I_time, gate_param_df.loc[split_n, "I2ITime"])
        I2I_time = max(I2I_time, gate_param_df.loc[buff_n, "I2ITime"])
 
        #
        I2C_time = gate_param_df.loc[gate_target, "I2CTime"]       

        #
        min_cct = delay_C2I + I2C_time
        min_cct = max(min_cct, I2I_time)
        row['MinCCT'] = round(min_cct, 2)
        ret_conn_df.loc[idx] = row
    return ret_conn_df


def adjust_clkpath(clk_scheme, input_clkconn_df, input_conn_df):
    global gate_param_df
    global ptl_n

    if clk_scheme != "concurrent":
        raise Exception("adjust_clkpath - clk_scheme")

    # Add wire cells in the clock stem to minimize CCT
    temp_clkconn_df = input_clkconn_df.copy(deep=True)
    temp_conn_df = input_conn_df.copy(deep=True)

    while (True):
        row = temp_conn_df.iloc[0]

        # Check whether the tuning is possible or not

        ## 1. MinCCT should not be NaN
        if isNaN(row["MinCCT"]):
            break

        ## 2. Target circuit should not include the loop
        if row["A_dist_loop"] > 0 or row["B_dist_loop"] > 0:
            break

        ## 3. Data delay should be meaningfully larger than the clock delay
        gate_target = row["Type"]
        gate_A = row["A_type"]
        gate_B = row["B_type"]

        if not isNaN(gate_A):
            data_delay_A, clock_delay_A = cal_connection_delay(clk_scheme, temp_clkconn_df, row, "A")
            delay_C2A = data_delay_A - clock_delay_A
        else:
            delay_C2A = 10000   # Heuristic

        if not isNaN(gate_B):
            data_delay_B, clock_delay_B = cal_connection_delay(clk_scheme, temp_clkconn_df, row, "B")
            delay_C2B = data_delay_B - clock_delay_B
        else:
            delay_C2B = 10000   # Heuristic
        delay_C2I = min(delay_C2A, delay_C2B)

        C2I_time = gate_param_df.loc[gate_target, "C2ITime"]
        timing_gap = delay_C2I - C2I_time
        
        ptl_delay = gate_param_df.loc[ptl_n, "Delay"]

        if timing_gap < ptl_delay:
            break

        # All conditions are satisfied. Now, insert wire cells to the clock stem
        num_buff, num_ptl = cal_buff_ptl(timing_gap)
        ## Insert wire cells 
        depth = row["Depth"]
        clk_conn_row = temp_clkconn_df.loc[depth]
        clk_conn_row["stem_{}".format(buff_n)] += num_buff
        clk_conn_row["stem_{}".format(ptl_n)] += num_ptl

        ## Update temp_conn_df
        temp_conn_df = adjust_datapath(clk_scheme, temp_clkconn_df, temp_conn_df)
        temp_conn_df = cal_min_cct(clk_scheme, temp_clkconn_df, temp_conn_df).sort_values(by=["MinCCT"], ascending=False)

    return temp_conn_df, temp_clkconn_df


def update_breakdown():
    global conn_df, clk_conn_df
    global bd_df, clk_bd_df
    global gate_param_df
   
    # breakdown
    for _, row in conn_df.iterrows():
        num_buff = row["A_buff"] + row["B_buff"]
        num_ptl = row["A_ptl"] + row["B_ptl"]
        try:
            bd_df[buff_n] += num_buff
        except:
            bd_df[buff_n] = num_buff
        try:
            bd_df[ptl_n] += num_ptl
        except:
            bd_df[ptl_n] = num_ptl

    # clock breakdown
    for _, row in clk_conn_df.iterrows():
        br_width = int(pow(2, row["br_{}".format(split_n)]))
        for gate_type, num_gate in row.items():
            part = gate_type.split('_')[0]
            gate_type = gate_type.replace("{}_".format(part), "")

            if part == "br":
                if gate_type == split_n:
                    num_gate = (br_width-1)
                elif gate_type == ptl_n:
                    num_gate = br_width * num_gate
                elif gate_type == buff_n:
                    pass
                else:
                    raise Exception("update_breakdown - part")
            else:
                pass
            clk_bd_df[gate_type] += num_gate
    return 


def adjust_sfq_timing(conn, bd, plib_path, clk, dump_path, dump, regen, verbose):
    conn_opt_path = dump_path + "connection.csv"
    bd_opt_path = dump_path + "breakdown.csv"
    conn_clk_path = dump_path + "clkconnection.csv"
    bd_clk_path = dump_path + "clkbreakdown.csv"

    if (not regen) and \
       os.path.exists(conn_opt_path) and \
       os.path.exists(bd_opt_path) and \
       os.path.exists(conn_clk_path) and \
       os.path.exists(bd_clk_path):
        if verbose:
            print("\n************ Adjust SFQ timing -> SKIP ************")
        conn_opt = pd.read_csv(conn_opt_path)
        bd_opt = pd.read_csv(bd_opt_path)
        conn_clk = pd.read_csv(conn_clk_path)
        bd_clk = pd.read_csv(bd_clk_path)
    else:
        if verbose:
            print("\n************ Adjust SFQ timing -> START ************")
            print("\t input parameter lib: {}".format(plib_path))
            print()

        global gate_param_df, conn_df, bd_df, clk_conn_df, clk_bd_df
        # Set inputs
        gp = pd.read_csv(plib_path)
        gate_param_df = gp.set_index('Name')
        conn_df = conn
        bd_df = bd
        clk_scheme = clk
        if clk_scheme == "concurrent":
            tuning = True
        else:
            tuning = False
        ## 
        global buff_n, ptl_n, split_n

        for g_name in gp['Name']:
            if 'bufft' in g_name:
                buff_n = g_name
            elif 'ptl' in g_name:
                if not ('rx' in g_name or 'tx' in g_name):
                    ptl_n = g_name
                else:
                    pass
            elif 'splitt' in g_name:
                split_n = g_name
            else:
                pass

        # Inititalize clk_conn_df & clk_bd_df
        init_clk_df()
 
        # Add columns to consider wire cells on each data path
        conn_df["A_buff"] = [0] * len(conn_df)
        conn_df["A_ptl"] = [0] * len(conn_df)
        conn_df["B_buff"] = [0] * len(conn_df)
        conn_df["B_ptl"] = [0] * len(conn_df)

        # Run the first timing adjustment 
        ## Goal: Satisfy all the timing constraints
        conn_df = adjust_datapath(clk_scheme, clk_conn_df, conn_df)
        conn_df = cal_min_cct(clk_scheme, clk_conn_df, conn_df).sort_values(by=["MinCCT"], ascending=False) 
        
        # Iterate the timing adjustment to minimize CCT
        if tuning:
           conn_df, clk_conn_df = adjust_clkpath(clk_scheme, clk_conn_df, conn_df)
        else:
            pass
       
        # Update breakdown dfs (add wire cells)
        update_breakdown()

        # output
        conn_opt = conn_df.reset_index(drop=True)
        bd_opt = bd_df.reset_index(drop=True)
        conn_clk = clk_conn_df.reset_index(drop=True)
        bd_clk = clk_bd_df.reset_index(drop=True)

        # Dump dfs
        if dump:
            conn_opt.to_csv(conn_opt_path, index=False)
            bd_opt.to_csv(bd_opt_path, index=False)
            conn_clk.to_csv(conn_clk_path, index=False)
            bd_clk.to_csv(bd_clk_path, index=False)
            if verbose:
                print("\t output dataframe (connection-opt): {}".format(conn_opt_path))
                print("\t output dataframe (breakdown-opt): {}".format(bd_opt_path))
                print("\t output dataframe (connection-clk): {}".format(conn_clk_path))
                print("\t output dataframe (breakdown-clk): {}".format(bd_clk_path))
        else:
            if verbose:
                print("\t do not dump output dataframes")
    if verbose: 
        # print outputs
        print()
        print("\t Connection (opt)")
        print(conn_opt.to_string())
        print()
        print("\t Breakdown (opt)")
        print(bd_opt.to_string())
        print()
        print("\t Connection (clk)")
        print(conn_clk.to_string())
        print()
        print("\t Breakdown (clk)")
        print(bd_clk.to_string())
        print("************ Adjust SFQ timing -> FINISH ************\n")

    return conn_opt, bd_opt, conn_clk, bd_clk 


def main(argv):
    unit_name = FLAGS.unit_name
    lib = FLAGS.lib
    clk = FLAGS.clk
    dump = bool(FLAGS.dump)
    regen = bool(FLAGS.regen)

    src_dir = os.path.join(par_dir, "sfq_netlist")
    conn_path = os.path.join(src_dir, "{}_{}_connection.csv".format(unit_name, lib))
    bd_path = os.path.join(src_dir, "{}_{}_breakdown.csv".format(unit_name, lib))
    conn = pd.read_csv(conn_path)
    bd = pd.read_csv(bd_path)

    plib_dir = os.path.join(par_dir, "param")
    plib_path = os.path.join(plib_dir, "{}.csv".format(lib))

    dump_dir = os.path.join(par_dir, "freqopt_netlist")
    dump_path = os.path.join(dump_dir, "{}_{}_{}_".format(unit_name, lib, clk))
    
    #
    conn_opt, bd_opt, conn_clk, bd_clk = adjust_sfq_timing(conn, bd, plib_path, clk, dump_path, dump, regen)

    return

if __name__ == "__main__":
    FLAGS = flags.FLAGS
    flags.DEFINE_string("unit_name", "fa_1b", "name of the target unit", short_name = "un")
    flags.DEFINE_string("lib", "mitll_v2p1", "name of the target library", short_name = "lib")
    flags.DEFINE_string("clk", "concurrent", "clocking scheme - concurrent or counter")
    flags.DEFINE_integer("dump", 1, "dump the result or not")
    flags.DEFINE_integer("regen", 1, "re-generate the result or not")

    app.run(main)
