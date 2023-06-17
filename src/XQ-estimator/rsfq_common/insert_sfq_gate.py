from absl import flags, app

import os
import pandas as pd
from parse import compile
import copy
from math import *
import numpy as np

curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
par_dir = os.path.join(curr_dir, os.pardir)


# Global variables
node_list = []
o_node_list = []    # output node list
##
buff_n = ""
dff_n = ""
split_n = ""

class Node:
    def __init__(self, node_type, node_name,\
                 name_A, name_B, name_Q):
        self.node_type = node_type
        self.node_name = node_name 
        self.name_A = name_A
        self.name_B = name_B
        self.name_Q = name_Q
        self.parent_A = None
        self.parent_B = None
        self.depth_A = 0
        self.depth_B = 0
        self.children = []
        self.visit = False
        self.num_split = 0
        self.depth_split = 0

    def debug(self):
        print("node_type: ", self.node_type)
        print("node_name: ", self.node_name)
        print("name_A: ", self.name_A)
        print("name_B: ", self.name_B)
        print("name_Q: ", self.name_Q)
        print("depth_A: ", self.depth_A)
        print("depth_B: ", self.depth_B)
        if self.parent_A is not None:
            print("parent_A: ", self.parent_A.node_name)
        else:
            print("parent_A: None")
        if self.parent_B is not None:
            print("parent_B: ", self.parent_B.node_name)
        else:
            print("parent_B: None")
        print("children: ")
        for child in self.children:
            print(child.node_name)
        print("visit: ", self.visit)
        print("depth_split: ", self.depth_split)
        print("num_split: ", self.num_split)
        print()
        return


def gen_cell_list(clib_path):
    cell_name_list = []
    
    g_format = compile("module {}({});")
    clib = open(clib_path, "r")

    for line in clib:
        line = ' '.join(line.split())
        try:
            cell_name, _ = g_format.parse(line)
        except:
            continue
        cell_name_list.append(cell_name)

    return cell_name_list


def gen_node_list(rtl_lines, clib_path):
    global node_list, o_node_list
    global buff_n, dff_n

    i_format_s = compile("input {};")
    i_format_m = compile("input [{}:0] {};")
    o_format_s = compile("output {};")
    o_format_m = compile("output [{}:0] {};")
    g_format = compile(".{}({})")
    as_format = compile("assign {} = {};")

    cell_name_list = gen_cell_list(clib_path)

    line_it = iter(rtl_lines)
    for line in line_it:
        line = ' '.join(line.split())
        if len(line.split()) == 0:
            continue
        if "*" in line:
            continue 
        
        # Input node
        if ("input" in line) and (not "module" in line) and (not "assign" in line):
            if len(line.split()) > 2:
                bit_width, name = i_format_m.parse(line)
                for i in range(0, int(bit_width)+1):
                    node = Node(node_type = 'input',
                                node_name = "{}[{}]".format(name, i),
                                name_A = None,
                                name_B = None, 
                                name_Q = "{}[{}]".format(name, i)
                                )
                    node_list.append(node)
            else:
                name, = i_format_s.parse(line)
                node = Node(node_type = 'input',
                            node_name = name,
                            name_A = None, 
                            name_B = None,
                            name_Q = name
                            )
                node_list.append(node)
        
        # Output node
        if ("output" in line) and (not "module" in line) and (not "assign" in line):
            if len(line.split()) > 2:
                bit_width, name = o_format_m.parse(line)
                for i in range(0, int(bit_width)+1):
                    node = Node(node_type = 'output', 
                                node_name = "{}[{}]".format(name, i),
                                name_A = "{}[{}]".format(name, i),
                                name_B = None,
                                name_Q = None
                                )
                    node_list.append(node)
                    o_node_list.append(node)

            else:
                name, = o_format_s.parse(line)
                node = Node(node_type = 'output', 
                            node_name = name,
                            name_A = name,
                            name_B = None,
                            name_Q = None 
                            )
                node_list.append(node)
                o_node_list.append(node)

        # Gate node
        node_type = None
        name_A = None
        name_B = None
        name_Q = None
        ##
        ls = line.split()
        if ls[0] in cell_name_list:
            node_type = ls[0]
            if node_type == buff_n:
                node_type = dff_n
            node_name = ls[1]
            
            while(True):
                line = ' '.join(next(line_it).split())
                line = line.replace(',', '')
                if ';' in line:
                    break;
                net, name = g_format.parse(line)
                if net == 'A':
                    name_A = name
                if net == 'B':
                    name_B = name
                if net == 'Q':
                    name_Q = name
                   
            node = Node(node_type = node_type, 
                        node_name = node_name,
                        name_A = name_A, 
                        name_B = name_B, 
                        name_Q = name_Q
                        )
            node_list.append(node)

        # Assign handling 
        if "assign" in line:
            dst, src = as_format.parse(line)
            for node in node_list:
                if src == node.name_Q:
                    for node_it in node_list:
                        if dst == node_it.name_A or dst == node_it.name_B:
                            node.name_Q = dst
                            break
                        else:
                            continue
                else:
                    pass
    return


def build_tree():
    global node_list
    
    # Initialize
    for node in node_list:
        node.parent_A = None
        node.parent_B = None
        node.children = []

    # Build tree
    for node in node_list:
        node_type = node.node_type
        name_A = node.name_A
        name_B = node.name_B
        name_Q = node.name_Q

        for node_it in node_list:
            # Find children 
            if (name_Q is not None) and \
               (node_it.name_A == name_Q or node_it.name_B == name_Q):
                node.children.append(node_it)
            # Find parent_A
            if (node_it.name_Q is not None) and \
               (node_it.name_Q == name_A):
                node.parent_A = node_it
            # Find parent_B
            if (node_it.name_Q is not None) and \
               (node_it.name_Q == name_B):
                node.parent_B = node_it
    return


def set_depth():
    global node_list
   
    # Initialize
    for node in node_list:
        node.depth_A = 0
        node.depth_B = 0
    
    # Set depth
    stack = []
    for node in node_list:
        if node.parent_A is None and node.parent_B is None:
            if node.node_type != "input":
                node.depth_A = 1
                node.depth_B = 1
            stack.append(node)

    while len(stack) > 0:
        node = stack.pop()
        for child in node.children:
            next_depth = max(node.depth_A, node.depth_B) + 1
            if node.name_Q == child.name_A and child.depth_A < next_depth:
                child.depth_A = next_depth
                stack.append(child)
            if node.name_Q == child.name_B and child.depth_B < next_depth:
                child.depth_B = next_depth
                stack.append(child)
    return

def insert_dff():
    global o_node_list
    global node_list
    global dff_n

    # Initialize
    for node in node_list:
        node.visit = False
    
    # Set output depth B
    # Initial stack: output nodes
    stack = []
    max_depth_o = 0
    for o_node in o_node_list:
        max_depth_o = max(o_node.depth_A, max_depth_o)
    for o_node in o_node_list:
        o_node.depth_B = max_depth_o
        stack.append(o_node)
    
    # Insert DFF
    net_id = 0
    node_id = 0
    while len(stack) > 0:
        node = stack.pop()
        
        if node.visit:
            continue
        node.visit = True

        if node.parent_A:
            stack.append(node.parent_A)
        if node.parent_B: 
            stack.append(node.parent_B)

        if (node.node_type == 'output' and node.parent_A is not None) or\
           (node.parent_A is not None and node.parent_B is not None):
            
            # Check the depth balance
            depth_gap = node.depth_A - node.depth_B
            if depth_gap == 0:
                continue
            if depth_gap > 0:
                parent = node.parent_B
            if depth_gap < 0:
                parent = node.parent_A

            # Insert DFFs
            for i in range(0, abs(depth_gap)):
                curr_name = "_ND{}_".format(node_id)
                if i == 0:
                    curr_Q = "_NT{}_".format(net_id) 
                    net_id += 1
                    if depth_gap > 0:
                        node.name_B = curr_Q
                    if depth_gap < 0:
                        node.name_A = curr_Q
                else:
                    curr_Q = curr_A
                if i == abs(depth_gap)-1:
                    curr_A = parent.name_Q
                else: 
                    curr_A = "_NT{}_".format(net_id) 

                new_node = Node(node_type = dff_n,
                                node_name = curr_name,
                                name_A = curr_A, 
                                name_B = None,
                                name_Q = curr_Q
                                )
                node_list.append(new_node)
                net_id += 1
                node_id += 1
    return


def set_split():
    global node_list

    for node in node_list:
        num_children = len(node.children)
        if num_children > 1:
            node.depth_split = ceil(log2(num_children))
            node.num_split = int(pow(2, node.depth_split)-1)
        else:
            node.depth_split = 0
            node.num_split = 0
    return 

def gen_connection():
    global node_list
    
    ret_df = pd.DataFrame(columns=["Type", "Name", "Depth", "A_type", "A_name", "A_depth_split", "A_dist_loop", "B_type", "B_name", "B_depth_split", "B_dist_loop"])

    for node in node_list:
        if node.node_type == 'input':
            continue

        df_row = dict()
        df_row['Type'] = node.node_type
        df_row['Name'] = node.node_name
        if node.node_type == 'output':
            df_row['Type'] = df_row['Type'] + "_{}".format(node.node_name)
        df_row['Depth'] = max(node.depth_A, node.depth_B)
        if node.parent_A:
            df_row['A_type'] = node.parent_A.node_type
            if node.parent_A.node_type == 'input':
                df_row['A_type'] = df_row['A_type'] + "_{}".format(node.parent_A.node_name)
            df_row['A_name'] = node.parent_A.node_name
            df_row['A_depth_split'] = node.parent_A.depth_split
            edge_A = (node.parent_A.node_name, node.node_name)
            df_row['A_dist_loop'] = None
        else:
            df_row['A_type'] = None
            df_row['A_name'] = None
            df_row['A_depth_split'] = None
            df_row['A_dist_loop'] = None

        if node.parent_B:
            df_row['B_type'] = node.parent_B.node_type
            if node.parent_B.node_type == 'input':
                df_row['B_type'] = df_row['B_type'] + "_{}".format(node.parent_B.node_name)
            df_row['B_name'] = node.parent_B.node_name
            df_row['B_depth_split'] = node.parent_B.depth_split
            edge_B = (node.parent_B.node_name, node.node_name)
            df_row['B_dist_loop'] = None
        else:
            df_row['B_type'] = None
            df_row['B_name'] = None
            df_row['B_depth_split'] = None
            df_row['B_dist_loop'] = None
        
        entry_df = pd.DataFrame(df_row, index=[0])
        ret_df = pd.concat([ret_df, entry_df], ignore_index=True)
    
    ret_df.replace(to_replace=[None], value=np.nan, inplace=True)
    for col in ret_df.columns:
        try:
            ret_df[col] = ret_df[col].fillna(-1).astype(int).replace({-1: 0})
        except:
            pass
    
    return ret_df


def gen_breakdown():
    global node_list
    global split_n

    ret_dict = dict()

    for node in node_list:
        try:
            ret_dict[split_n] += node.num_split
        except:
            ret_dict[split_n] = 0
            ret_dict[split_n] += node.num_split

        if node.node_type == 'input' or node.node_type == 'output':
            continue
        try:
            ret_dict[node.node_type] += 1
        except:
            ret_dict[node.node_type] = 1

    ret_df = pd.DataFrame(ret_dict, index=[0])
    ret_df.replace(to_replace=[None], value=np.nan, inplace=True)
    for col in ret_df.columns:
        ret_df[col] = ret_df[col].fillna(-1).astype(int).replace({-1: np.nan})

    return ret_df
        

def insert_sfq_gate(rtl_lines, plib_path, clib_path, dump_path, dump, regen, verbose):
    conn_path = dump_path + "connection.csv"
    bd_path = dump_path + "breakdown.csv"
    if (not regen) and (os.path.exists(conn_path) and os.path.exists(bd_path)):
        if verbose:
            print("\n************ Insert SFQ gate -> SKIP ************")
        conn = pd.read_csv(conn_path)
        bd = pd.read_csv(bd_path)
    else:
        if verbose:
            print("\n************ Insert SFQ gate -> START ************")
            print("\t input parameter lib: {}".format(plib_path))
            print("\t input cell lib: {}".format(clib_path))
            print()
        
        global node_list, o_node_list
        global buff_n, dff_n, split_n

        # 0. Set gate names not in the cell
        plib = pd.read_csv(plib_path)
        for name in plib['Name']:
            if 'bufft' in name:
                buff_n = name
            elif 'dfft' in name:
                dff_n = name
            elif 'splitt' in name:
                split_n = name
            else:
                pass

        # 1. Generate node list and build initial tree
        gen_node_list(rtl_lines, clib_path)
        build_tree()

        # 2. DFF insertion 
        set_depth()
        insert_dff()
        build_tree()
        set_depth()

        for node in node_list:
            if node.parent_A is not None and node.parent_B is not None:
                if node.depth_A != node.depth_B: 
                    raise Exception("insert_sfq_gate - Path balancing fails")

        # 3. Split insertion (in fact, wire cells are not handled as the nodes)
        set_split()
       
        # 4. Generate the connection & breakdown dataframes (and Save them)
        conn = gen_connection().sort_values(by=["Depth"]).reset_index(drop=True)
        bd = gen_breakdown().reset_index(drop=True)

        ### Reset global variables
        node_list = []
        o_node_list = []
       
        ### output dump
        if dump:
            conn.to_csv(conn_path, index=False)
            bd.to_csv(bd_path, index=False)
            if verbose:
                print("\t output dataframe (connection): {}".format(conn_path))
                print("\t output dataframe (breakdown): {}".format(bd_path))
        else:
            if verbose:
                print("\t do not dump output dataframes")


    if verbose: 
        ## print outputs 
        print()
        print("\t Connection")
        print(conn.to_string())
        print()
        print("\t Breakdown")
        print(bd.to_string())
        print("************ Insert SFQ gate -> FINISH ************\n")

    return conn, bd


def main(argv):
    unit_name = FLAGS.unit_name
    lib = FLAGS.lib
    dump = bool(FLAGS.dump)
    regen = bool(FLAGS.regen)

    src_dir = os.path.join(par_dir, "gate_rtl")
    src_path = os.path.join(src_dir, "{}_{}.v".format(unit_name, lib))

    plib_dir = os.path.join(par_dir, "param")
    plib_path = os.path.join(plib_dir, "{}.csv".format(lib))

    clib_dir = os.path.join(*[par_dir, "HDLlib", lib])
    clib_path = os.path.join(clib_dir, "{}.v".format(lib))

    dump_dir = os.path.join(par_dir, "sfq_netlist")
    dump_path = os.path.join(dump_dir, "{}_{}_".format(unit_name, lib))

    conn, bd = insert_sfq_gate(src_path, plib_path, clib_path, dump_path, dump, regen)

    return 


if __name__ == "__main__":
    FLAGS = flags.FLAGS
    flags.DEFINE_string("unit_name", "fa_1b", "name of the target unit", short_name = "un")
    flags.DEFINE_string("lib", "mitll_v2p1", "name of the target library", short_name = "lib")
    flags.DEFINE_integer("dump", 1, "dump the result or not")
    flags.DEFINE_integer("regen", 1, "re-generate the result or not")

    app.run(main)
