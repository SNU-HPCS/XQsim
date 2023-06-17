import pandas as pd
import numpy as np
import os

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
    cell_list = ["ort", "dfft", "ndrot", "splitt"]
    if "mitll" in rsfqlib:
        name_list = ["mitll_"+cn for cn in cell_list]
    else:
        raise Exception()
    return

def gen_conn(num_data):
    # format
    columns = ["Type", "Name", "Depth", "A_type", "A_name", "A_depth_split", "A_dist_loop", "B_type", "B_name", "B_depth_split", "B_dist_loop"]
    conn = dict()
    for col in columns:
        conn[col] = []
    conn = pd.DataFrame(conn)
    #
    depth = 1
    # input-side OR
    entry = dict()
    entry["Type"] = get_name("or")
    entry["Name"] = "_ND_INOR"
    entry["Depth"] = depth
    entry["A_type"] = get_name("ndro")
    entry["A_name"] = "_ND_OUTNDRO"
    entry["A_depth_split"] = 1
    entry["A_dist_loop"] = num_data+1
    entry["B_type"] = "input_din"
    entry["B_name"] = "din"
    entry["B_depth_split"] = 0
    entry["B_dist_loop"] = None
    entry_df = pd.DataFrame(entry, index=[0])
    conn = pd.concat([conn, entry_df], ignore_index=True)
    depth += 1

    # 1st DFF
    for _ in range(depth, depth+num_data):
        entry = dict()
        entry["Type"] = get_name("dff")
        entry["Name"] = "_ND_DFF_{}".format(depth)
        entry["Depth"] = depth
        if depth == 2:
            entry["A_type"] = get_name("or")
            entry["A_name"] = "_ND_INOR"
        else:
            entry["A_type"] = get_name("dff")
            entry["A_name"] = ("_ND_DFF_{}".format(depth-1))
        entry["A_depth_split"] = 0
        entry["A_dist_loop"] = None
        entry["B_type"] = None
        entry["B_name"] = None
        entry["B_depth_split"] = None
        entry["B_dist_loop"] = None
        entry_df = pd.DataFrame(entry, index=[0])
        conn = pd.concat([conn, entry_df], ignore_index=True)
        depth += 1

    # output-side NDRO
    entry = dict()
    entry["Type"] = get_name("ndro")
    entry["Name"] = "_ND_OUTNDRO"
    entry["Depth"] = depth
    entry["A_type"] = get_name("dff")
    entry["A_name"] = "_ND_DFF_{}".format(depth-1)
    entry["A_depth_split"] = 0
    entry["A_dist_loop"] = None
    entry["B_type"] = None
    entry["B_name"] = None
    entry["B_depth_split"] = None
    entry["B_dist_loop"] = None
    entry_df = pd.DataFrame(entry, index=[0])
    conn = pd.concat([conn, entry_df], ignore_index=True)
    depth += 1

    # output
    entry = dict()
    entry["Type"] = "output_dout"
    entry["Name"] = "dout"
    entry["Depth"] = depth
    entry["A_type"] = get_name("ndro")
    entry["A_name"] = "_ND_OUTNDRO"
    entry["A_depth_split"] = 1
    entry["A_dist_loop"] = None
    entry["B_type"] = None
    entry["B_name"] = None
    entry["B_depth_split"] = None
    entry["B_dist_loop"] = None
    entry_df = pd.DataFrame(entry, index=[0])
    conn = pd.concat([conn, entry_df], ignore_index=True)

    conn.replace(to_replace=[None], value=np.nan, inplace=True)
    for col in conn.columns:
        try:
            conn[col] = conn[col].fillna(-1).astype(int).replace({-1: 0})
        except:
            pass

    return conn

def gen_bd (num_data):
    #
    bd = dict()
    bd[get_name("or")] = 1 
    bd[get_name("dff")] = num_data
    bd[get_name("ndro")] = 1
    bd[get_name("split")] = 1
    bd = pd.DataFrame(bd, index=[0])

    return bd

def gen_srmem_netlist (num_data, rsfqlib, wpath, dump, regen):
    conn_path = wpath + "connection.csv"
    bd_path = wpath + "breakdown.csv"

    if (not regen) and \
       (os.path.exists(conn_path) and os.path.exists(bd_path)):
        conn = pd.read_csv(conn_path)
        bd = pd.read_csv(bd_path)
    else:
        initial_setup(rsfqlib)
        conn = gen_conn(num_data)
        bd = gen_bd(num_data)

        conn.replace(to_replace=[None], value=np.nan, inplace=True)
        bd.replace(to_replace=[None], value=np.nan, inplace=True)
    
    if dump:
        conn.to_csv(conn_path, index=False)
        bd.to_csv(bd_path, index=False)

    return conn, bd
