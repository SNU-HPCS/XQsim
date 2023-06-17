import pandas as pd

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
    cell_list = ["merget"]
    if "mitll" in rsfqlib:
        name_list = ["mitll_"+cn for cn in cell_list]
    else:
        raise Exception()
    return


def gen_mgtree_netlist(data_bw, num_data, rsfqlib):
    initial_setup(rsfqlib)

    conn = None

    bd = dict()
    bd[get_name("merge")] = data_bw * (num_data-1)
    bd = pd.DataFrame(bd, index=[0])

    return conn, bd
