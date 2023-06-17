import pandas as pd
import numpy as np
from math import *

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
    cell_list = ["andt", "dfft", "nott"]
    if "mitll" in rsfqlib:
        name_list = ["mitll_"+cn for cn in cell_list]
    else:
        raise Exception()
    return

def gen_conn_bd(): 
    # Connection
    conn_dict = dict()
    columns = ["Type", "Name", "Depth", "A_type", "A_name", "A_depth_split", "A_dist_loop", "B_type", "B_name", "B_depth_split", "B_dist_loop"]
    
    for col in columns:
        conn_dict[col] = []
    conn_df = pd.DataFrame(conn_dict)

    # Depth1: NOT
    entry = dict()
    entry["Type"] = get_name("not")
    entry["Name"] = "_ND_0_1"
    entry["Depth"] = 1
    entry["A_type"] = "input_others"
    entry["A_name"] = "others"
    entry["A_depth_split"] = 0
    entry["A_dist_loop"] = None
    entry["B_type"] = None
    entry["B_name"] = None
    entry["B_depth_split"] = None
    entry["B_dist_loop"] = None
    entry_df = pd.DataFrame(entry, index=[0])
    conn_df = pd.concat([conn_df, entry_df], ignore_index=True)

    # Depth1: DFF
    entry = dict()
    entry["Type"] = get_name("dff")
    entry["Name"] = "_ND_1_1"
    entry["Depth"] = 1
    entry["A_type"] = "input_self"
    entry["A_name"] = "self"
    entry["A_depth_split"] = 0
    entry["A_dist_loop"] = None
    entry["B_type"] = None
    entry["B_name"] = None
    entry["B_depth_split"] = None
    entry["B_dist_loop"] = None
    entry_df = pd.DataFrame(entry, index=[0])
    conn_df = pd.concat([conn_df, entry_df], ignore_index=True)

    # Depth2: AND
    entry = dict()
    entry["Type"] = get_name("and")
    entry["Name"] = "_ND_0_2"
    entry["Depth"] = 2
    entry["A_type"] = get_name("not")
    entry["A_name"] = "_ND_0_1"
    entry["A_depth_split"] = 0
    entry["A_dist_loop"] = None
    entry["B_type"] = get_name("dff")
    entry["B_name"] = "_ND_1_1"
    entry["B_depth_split"] = 0
    entry["B_dist_loop"] = None
    entry_df = pd.DataFrame(entry, index=[0])
    conn_df = pd.concat([conn_df, entry_df], ignore_index=True)

    # Output
    ## dout
    entry = dict()
    entry["Type"] = "output_set"
    entry["Name"] = "set"
    entry["Depth"] = 3
    entry["A_type"] = get_name("and")
    entry["A_name"] = "_ND_0_3"
    entry["A_depth_split"] = 0
    entry["A_dist_loop"] = None
    entry["B_type"] = None
    entry["B_name"] = None
    entry["B_depth_split"] = None
    entry["B_dist_loop"] = None
    entry_df = pd.DataFrame(entry, index=[0])
    conn_df = pd.concat([conn_df, entry_df], ignore_index=True)

    # Breakdown
    bd_dict = dict()
    bd_dict[get_name("not")] = 1
    bd_dict[get_name("dff")] = 1
    bd_dict[get_name("and")] = 1
    bd_df = pd.DataFrame(bd_dict, index=[0])

    conn_df.replace(to_replace=[None], value=np.nan, inplace=True)
    bd_df.replace(to_replace=[None], value=np.nan, inplace=True)

    return conn_df, bd_df

def gen_pe_netlist(rsfqlib):
    initial_setup(rsfqlib)
    return gen_conn_bd()
