import pandas as pd
import numpy as np

name_list = []

def get_name(cn):
    global name_list
    for on in name_list:
        if cn in on:
            name = on
            break
    return name

def initial_setup(rsfqlib):
    global name_list
    cell_list = ["andt", "dfft", "ndrot", "splitt"]
    if "mitll" in rsfqlib:
        name_list = ["mitll_"+cn for cn in cell_list]
    else:
        raise Exception()
    return


def gen_ndronw_netlist(data_bw, rsfqlib):
    initial_setup(rsfqlib)

    # Connection
    conn_dict = dict()
    columns = ["Type", "Name", "Depth", "A_type", "A_name", "A_depth_split", "A_dist_loop", "B_type", "B_name", "B_depth_split", "B_dist_loop"]
    
    for col in columns:
        conn_dict[col] = []

    conn_df = pd.DataFrame(conn_dict)
    num_and = 0
    num_dff = 0
    num_split = 0
    num_ndro = 0
    for w in range(0, data_bw):
        num_and += 1
        num_dff += 1
        num_split += 3
        num_ndro += 1

        # Depth1: AND
        entry = dict()
        entry["Type"] = get_name("and")
        entry["Name"] = "_ND_{}_0".format(w)
        entry["Depth"] = 1
        entry["A_type"] = "input_din[{}]".format(w)
        entry["A_name"] = "din[{}]".format(w)
        entry["A_depth_split"] = 0
        entry["A_dist_loop"] = None
        entry["B_type"] = "input_wrin[{}]".format(w)
        entry["B_name"] = "wrin[{}]".format(w)
        entry["B_depth_split"] = 1
        entry["B_dist_loop"] = None
        entry_df = pd.DataFrame(entry, index=[0])
        conn_df = pd.concat([conn_df, entry_df], ignore_index=True)

        # Depth1: DFF
        entry = dict()
        entry["Type"] = get_name("dff")
        entry["Name"] = "_ND_{}_1".format(w)
        entry["Depth"] = 1
        entry["A_type"] = "input_wrin[{}]".format(w)
        entry["A_name"] = "wrin[{}]".format(w)
        entry["A_depth_split"] = 1
        entry["A_dist_loop"] = None
        entry["B_type"] = None
        entry["B_name"] = None
        entry["B_depth_split"] = None
        entry["B_dist_loop"] = None
        entry_df = pd.DataFrame(entry, index=[0])
        conn_df = pd.concat([conn_df, entry_df], ignore_index=True)

        # Depth2: NDRO
        entry = dict()
        entry["Type"] = get_name("ndro")
        entry["Name"] = "_ND_{}_2".format(w)
        entry["Depth"] = 2
        entry["A_type"] = get_name("and")
        entry["A_name"] = "_ND_{}_0".format(w)
        entry["A_depth_split"] = 0
        entry["A_dist_loop"] = None
        entry["B_type"] = get_name("dff")
        entry["B_name"] = "_ND_{}_1".format(w)
        entry["B_depth_split"] = 1
        entry["B_dist_loop"] = None
        entry_df = pd.DataFrame(entry, index=[0])
        conn_df = pd.concat([conn_df, entry_df], ignore_index=True)
        
        # Output
        ## dout0
        entry = dict()
        entry["Type"] = "output_dout0[{}]".format(w)
        entry["Name"] = "dout0[{}]".format(w)
        entry["Depth"] = 3
        entry["A_type"] = get_name("ndro")
        entry["A_name"] = "_ND_{}_2".format(w)
        entry["A_depth_split"] = 1
        entry["A_dist_loop"] = None
        entry["B_type"] = None
        entry["B_name"] = None
        entry["B_depth_split"] = None
        entry["B_dist_loop"] = None
        entry_df = pd.DataFrame(entry, index=[0])
        conn_df = pd.concat([conn_df, entry_df], ignore_index=True)
        ## dout1
        entry = dict()
        entry["Type"] = "output_dout1[{}]".format(w)
        entry["Name"] = "dout1[{}]".format(w)
        entry["Depth"] = 3
        entry["A_type"] = get_name("ndro")
        entry["A_name"] = "_ND_{}_2".format(w)
        entry["A_depth_split"] = 1
        entry["A_dist_loop"] = None
        entry["B_type"] = None
        entry["B_name"] = None
        entry["B_depth_split"] = None
        entry["B_dist_loop"] = None
        entry_df = pd.DataFrame(entry, index=[0])
        conn_df = pd.concat([conn_df, entry_df], ignore_index=True)
        ## wrout
        entry = dict()
        entry["Type"] = "output_wrout[{}]".format(w)
        entry["Name"] = "wrout[{}]".format(w)
        entry["Depth"] = 2
        entry["A_type"] = get_name("dff")
        entry["A_name"] = "_ND_{}_1".format(w)
        entry["A_depth_split"] = 1
        entry["A_dist_loop"] = None
        entry["B_type"] = None
        entry["B_name"] = None
        entry["B_depth_split"] = None
        entry["B_dist_loop"] = None
        entry_df = pd.DataFrame(entry, index=[0])
        conn_df = pd.concat([conn_df, entry_df], ignore_index=True)
    # Breakdown
    bd_dict = dict()
    bd_dict[get_name("and")] = num_and
    bd_dict[get_name("dff")] = num_dff
    bd_dict[get_name("split")] = num_split
    bd_dict[get_name("ndro")] = num_ndro
    bd_df = pd.DataFrame(bd_dict, index=[0])

    conn_df.replace(to_replace=[None], value=np.nan, inplace=True)
    bd_df.replace(to_replace=[None], value=np.nan, inplace=True)
    
    return conn_df, bd_df
