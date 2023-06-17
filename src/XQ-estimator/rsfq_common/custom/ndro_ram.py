import pandas as pd
import numpy as np
from math import *
import copy
import os

# User inputs
num_address_bits = None
num_data_bits = None

# Define output dataframes
connection_df = None
breakdown_df = None

# gate numbering
num_and = 0
num_or = 0
num_dff = 0
num_not = 0
num_split = 0
num_ndro = 0

#
name_list = []

def get_name(cn):
    global name_list
    for on in name_list:
        if cn in on:
            name = on
            break
    return name


def init_setup (addr_bw, data_bw, rsfqlib):
    global connection_df, breakdown_df, num_address_bits, num_data_bits
    global num_and, num_or, num_dff, num_not, num_split, num_ndro
    global name_list

    connection_columns = ["Type","Name","Depth","A_type","A_name","A_depth_split","A_dist_loop",\
                        "B_type","B_name","B_depth_split","B_dist_loop"]
    connection_df = pd.DataFrame (None, columns=connection_columns)

    cell_list = ["splitt", "andt", "dfft", "nott", "ndrot", "ort"]
    if "mitll" in rsfqlib:
        name_list = ["mitll_"+cn for cn in cell_list]
    else:
        raise Exception()
    breakdown_df = pd.DataFrame (dict.fromkeys (name_list, 0), \
                                index=[0], columns=name_list)
    num_address_bits = addr_bw
    num_data_bits = data_bw
    num_and = 0
    num_or = 0
    num_dff = 0
    num_not = 0
    num_split = 0
    num_ndro = 0

    return


def gen_ndro_array (wr_data_list, wr_enable_list, depth):
    global connection_df, breakdown_df, num_address_bits, num_data_bits
    global num_and, num_or, num_dff, num_not, num_split, num_ndro
    output_list_ = list ()
    for wr_data_, wr_enable_ in zip (wr_data_list, wr_enable_list):
        output_list_.append ((gen_ndro_cell (wr_data_, wr_enable_, depth)))
    return output_list_
    

def gen_ndro_cell (wr_data, wr_enable, depth):
    global connection_df, breakdown_df, num_address_bits, num_data_bits
    global num_and, num_or, num_dff, num_not, num_split, num_ndro
    # Depth 1
    ## insert AND
    df_row = {"Type": get_name("and"), \
             "Name": "_AND{}_".format (num_and), \
             "Depth": depth, \
             "A_type": wr_data["Type"].item (), \
             "A_name": wr_data["Name"].item (), \
             "A_depth_split": 0, \
             "B_type": wr_enable["Type"].item (), \
             "B_name": wr_enable["Name"].item (), \
             #"B_depth_split": 1, \
             "B_depth_split": 1 + ceil(log(num_data_bits,2)), \
             }
    entry_df = pd.DataFrame(df_row, index=[0])
    connection_df = pd.concat([connection_df, entry_df], ignore_index=True)
    num_and += 1
    num_split += 1

    ## insert DFF
    df_row = {"Type": get_name("dff"), \
             "Name": "_DFF{}_".format (num_dff), \
             "Depth": depth, \
             "A_type": wr_enable["Type"].item (), \
             "A_name": wr_enable["Name"].item (), \
             "A_depth_split": 1 + ceil(log(num_data_bits,2)), \
             }
    entry_df = pd.DataFrame(df_row, index=[0])
    connection_df = pd.concat([connection_df, entry_df], ignore_index=True)
    num_dff += 1

    ## insert NDRO
    df_row = {"Type": get_name("ndro"), \
             "Name": "_NDRO{}_".format (num_ndro), \
             "Depth": depth+1, \
             "A_type": get_name("and"), \
             "A_name": "_AND{}_".format ((num_and-1)), \
             "A_depth_split": 0, \
             "B_type": get_name("dff"), \
             "B_name": "_DFF{}_".format ((num_dff-1)), \
             "B_depth_split": 0, \
             }
    entry_df = pd.DataFrame(df_row, index=[0])
    connection_df = pd.concat([connection_df, entry_df], ignore_index=True)
    num_ndro += 1

    return entry_df.copy()


def gen_mux (input, depth):
    outputs_ = input
    next_outputs_ = None
    # for each multiplexer stage 
    # (i.e., same select line indicates same stage)
    for addr_bit_ in range (num_address_bits):
        next_outputs_ = list ()
        # select declare
        if num_address_bits == 1:
            select_df = pd.DataFrame({"Type": "input_sel", "Name": "sel"}, index=[0])
        else:
            select_df = pd.DataFrame({"Type": "input_sel[{}]".format (addr_bit_), \
                                    "Name": "sel[{}]".format (addr_bit_)}, index=[0])
        # insert DFFs to adjust the timing of select[x] line
        select_df = gen_dff (select_df, 3*addr_bit_+2, 1)

        for mux_index_ in range (2**(num_address_bits-addr_bit_-1)):
            # input declare
            input1_df = outputs_[2*mux_index_]
            input2_df = outputs_[2*mux_index_+1]
            # generate 2to1-mux
            next_outputs_ = next_outputs_ \
                + gen_2to1_mux (input1_df, input2_df, select_df, num_address_bits-addr_bit_-1, 3 + 3*addr_bit_)
        outputs_ = next_outputs_
    return next_outputs_, 3*num_address_bits+depth # demux ports, depth


def gen_dff (input, target_dffs, depth):
    global connection_df, breakdown_df, num_address_bits, num_data_bits
    global num_and, num_or, num_dff, num_not, num_split
    if target_dffs <= 0:
        return input
    input_list_ = list ()
    input_list_.append (input)
    for dff_index_ in range (target_dffs):
        ## insert DFF
        input_ = input_list_.pop ()
        select_splits = 0
        if "input" in input_["Type"].item ():
            select_splits = ceil(log(num_data_bits,2))
            num_split += num_data_bits-1
        df_row = {"Type": get_name("dff"), \
                 "Name": "_DFF{}_".format (num_dff), \
                 "Depth": depth + dff_index_, \
                 "A_type": input_["Type"].item (), \
                 "A_name": input_["Name"].item (), \
                 "A_depth_split": select_splits, \
                 }
        entry_df = pd.DataFrame(df_row, index=[0])
        connection_df = pd.concat([connection_df, entry_df], ignore_index=True)
        num_dff += 1

        input_list_.append (entry_df.copy())
    return input_list_.pop ()


def gen_2to1_mux (input1, input2, select, select_splits, depth):
    global connection_df, breakdown_df, num_address_bits, num_data_bits
    global num_and, num_or, num_dff, num_not, num_split

    ## insert DFF
    df_row = {"Type": get_name("dff"), \
             "Name": "_DFF{}_".format (num_dff), \
             "Depth": depth, \
             "A_type": input1["Type"].item (), \
             "A_name": input1["Name"].item (), \
             "A_depth_split": 0, \
             }
    entry_df = pd.DataFrame(df_row, index=[0])
    connection_df = pd.concat([connection_df, entry_df], ignore_index=True)
    num_dff += 1
    ## insert not gate
    df_row = {"Type": get_name("not"), \
             "Name": "_NOT{}_".format (num_not), \
             "Depth": depth, \
             "A_type": select["Type"].item (), \
             "A_name": select["Name"].item (), \
             "A_depth_split": 1 + select_splits, \
             }
    entry_df = pd.DataFrame(df_row, index=[0])
    connection_df = pd.concat([connection_df, entry_df], ignore_index=True)
    num_not += 1
    num_split += 1 + select_splits
    ## insert AND
    df_row = {"Type": get_name("and"), \
             "Name": "_AND{}_".format (num_and), \
             "Depth": depth, \
             "A_type": select["Type"].item (), \
             "A_name": select["Name"].item (), \
             "A_depth_split": 1 + select_splits, \
             "B_type": input2["Type"].item (), \
             "B_name": input2["Name"].item (), \
             "B_depth_split": 0, \
             }
    entry_df = pd.DataFrame(df_row, index=[0])
    connection_df = pd.concat([connection_df, entry_df], ignore_index=True)
    num_and += 1

    # Depth 1
    ## insert AND
    df_row = {"Type": get_name("and"), \
             "Name": "_AND{}_".format (num_and), \
             "Depth": depth+1, \
             "A_type": get_name("dff"), \
             "A_name": "_DFF{}_".format ((num_dff-1)), \
             "A_depth_split": 0, \
             "B_type": get_name("not"), \
             "B_name": "_NOT{}_".format ((num_not-1)), \
             "B_depth_split": 0, \
             }
    entry_df = pd.DataFrame(df_row, index=[0])
    connection_df = pd.concat([connection_df, entry_df], ignore_index=True)
    num_and += 1
    ## insert DFF
    df_row = {"Type": get_name("dff"), \
             "Name": "_DFF{}_".format (num_dff), \
             "Depth": depth+1, \
             "A_type": get_name("and"), \
             "A_name": "_AND{}_".format (num_and-2), \
             "A_depth_split": 0, \
             }
    entry_df = pd.DataFrame(df_row, index=[0])
    connection_df = pd.concat([connection_df, entry_df], ignore_index=True)
    num_dff += 1
    
    # Depth 2
    ## insert OR
    df_row = {"Type": get_name("ort"), \
             "Name": "_OR{}_".format (num_or), \
             "Depth": depth+2, \
             "A_type": get_name("and"), \
             "A_name": "_AND{}_".format ((num_and-1)), \
             "A_depth_split": 0, \
             "B_type": get_name("dff"), \
             "B_name": "_DFF{}_".format ((num_dff-1)), \
             "B_depth_split": 0, \
             }
    entry_df = pd.DataFrame(df_row, index=[0])
    connection_df = pd.concat([connection_df, entry_df], ignore_index=True)
    num_or += 1

    return [entry_df.copy()]


def connect_outputs (output_list, depth):
    global connection_df, breakdown_df, num_address_bits, num_data_bits
    global num_and, num_or, num_dff, num_not, num_split, num_ndro
    
    for n_, output_ in enumerate (output_list):
        ## insert output
        if len (output_list) == 1:
            df_row = {"Type": "output_data", \
                     "Name": "data", \
                     "Depth": depth, \
                     "A_type": output_["Type"].item (), \
                     "A_name": output_["Name"].item (), \
                     "A_depth_split": 0, \
                     }
        else:
            df_row = {"Type": "output_data[{}]".format (n_), \
                     "Name": "data[{}]".format (n_), \
                     "Depth": depth, \
                     "A_type": output_["Type"].item (), \
                     "A_name": output_["Name"].item (), \
                     "A_depth_split": 0, \
                     }
        entry_df = pd.DataFrame(df_row, index=[0])
        connection_df = pd.concat([connection_df, entry_df], ignore_index=True)


def update_breakdown ():
    breakdown_df[get_name("and")] = num_and
    breakdown_df[get_name("dff")] = num_dff
    breakdown_df[get_name("not")] = num_not
    breakdown_df[get_name("split")] = num_split
    breakdown_df[get_name("ndrot")] = num_ndro
    breakdown_df[get_name("ort")] = num_or

def gen_conn_bd (addr_bw, data_bw, rsfqlib):
    init_setup(addr_bw, data_bw, rsfqlib)
    #
    output_list = list ()
    for data_bit_ in range (num_data_bits):
        wr_enable_list = list ()
        wr_input_list = list ()
        ndro_output_list = list ()
        for n_ in range (2**num_address_bits):
            ndro_index_ = data_bit_ * (2**num_address_bits) + n_
            enable_df = pd.DataFrame({"Type": "input_enable[{}]".format (ndro_index_), \
                                    "Name": "enable[{}]".format (ndro_index_)}, index=[0])
            data_df = pd.DataFrame({"Type": "input_data[{}]".format (ndro_index_), \
                                    "Name": "data[{}]".format (ndro_index_)}, index=[0])
            wr_enable_list.append (enable_df)
            wr_input_list.append (data_df)
        ndro_output_list = gen_ndro_array (wr_input_list, wr_enable_list, 1)
        output_df, depth = gen_mux (ndro_output_list, 3)
        output_list = output_list + output_df
    connect_outputs (output_list, depth)
    update_breakdown ()

    return


def gen_ndroram_netlist (addr_bw, data_bw, rsfqlib, wpath, dump, regen):
    conn_path = wpath + "connection.csv"
    bd_path = wpath + "breakdown.csv"

    if (not regen) and \
       (os.path.exists(conn_path) and os.path.exists(bd_path)):
        conn = pd.read_csv(conn_path)
        bd = pd.read_csv(bd_path)
    else:
        gen_conn_bd(addr_bw, data_bw, rsfqlib)
        conn = connection_df
        bd = breakdown_df
        
        if dump:
            conn.to_csv(conn_path, index=False)
            bd.to_csv(bd_path, index=False)
    return conn, bd
