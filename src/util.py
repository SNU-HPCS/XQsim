import json
import numpy as np
from math import *
from subprocess import PIPE, Popen
import pandas as pd

def get_bitwidth (num):
    return ceil(log(num, 2))

def getJsonData (json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        contents = f.read()
        while "/*" in contents:
            preComment, postComment = contents.split("/*", 1)
            contents = preComment + postComment.split("*/", 1)[1]
        json_data = json.loads(contents.replace("'", '"'))
        
    return json_data

def fill_param_line (src, dst, param_dict):
    lines = open(src, "r").readlines()
    f_dst = open(dst, "w")
    for line in lines:
        if "{}" in line:
            p = line.split()[1]
            line = line.replace("{}", str(param_dict[p]))
        f_dst.write(line)
    f_dst.close()
    return 

def cmdline(command):
    process = Popen(args = command, 
                    stdout = PIPE,
                    shell = True
                    )
    return process.communicate()[0]

def print_lattice(lattice_array, code_distance):
    ucl_size = 2
    num_ucrow = (code_distance + 1) // 2
    num_uccol = (code_distance + 1) // 2

    fringe = lattice_array.shape[1] % (ucl_size * 2)
    for i in range(lattice_array.shape[0]):
        for j in range(0, lattice_array.shape[1] - fringe, ucl_size * 2):
            if j % num_uccol == num_uccol - 1:
                print(lattice_array[i][j]+lattice_array[i][j+1]+lattice_array[i][j+2]+lattice_array[i][j+3]+'┃ ', end='')
            else:
                print(lattice_array[i][j]+lattice_array[i][j+1]+lattice_array[i][j+2]+lattice_array[i][j+3]+'╎ ', end='')
                            
        for j in range(lattice_array.shape[1] - fringe, lattice_array.shape[1]):
            print(lattice_array[i][j], end='')

        if (i % 4) == 0:
            print(' Q0   Q1', end=' ')
        elif (i % 4) == 1:
            print('    Q4   Q6', end=' ')
        elif (i % 4) == 2:
            print(' Q2   Q3', end=' ')
        else:
            print('    Q7   Q5', end=' ')

        print('')
        if (i % (ucl_size * 2)) == 3:
            for j in range(0, lattice_array.shape[1] - fringe, ucl_size * 2):
                if i % num_ucrow == num_ucrow - 1:
                    print('━━━━━━━━', end='')
                    if j % num_uccol == num_uccol - 1:
                        print("╋━", end='')
                    else:
                        print("━━", end='')
                else:
                    print('╌╌╌╌╌╌╌╌', end='')
                    if j % num_uccol == num_uccol - 1:
                        print("┃╌", end='')
                    else:
                        print("┼╌", end='')
                
                
            for j in range(lattice_array.shape[1] - fringe, lattice_array.shape[1]):
                if i % num_ucrow == num_ucrow - 1:
                    print('━', end='')
                else:
                    print('╌', end='')
            print('')
    print()
    
    return

def debug_array(param, cwd_list, arr_qb_type = 'dq'):
    patch_size = (param.code_dist + 1)    
    num_row_dq = param.num_pchrow * patch_size + 1  
    num_col_dq = param.num_pchcol * patch_size + 1  
    ucl_size = 2

    lattice_array = np.full((num_row_dq+num_row_dq, \
        num_col_dq+num_col_dq), '  ', dtype='U2')
    for i in range(num_row_dq+num_row_dq):
        for j in range(num_col_dq+num_col_dq):
            if (i+j) % 2 == 0:
                lattice_array[i][j] = '- ' 

    for (pchrow, pchcol, ucrow, uccol, qbidx), cwd in np.ndenumerate(cwd_list):
        patch_idx = (pchrow, pchcol)
        ucl_idx = (ucrow, uccol)
        
        if arr_qb_type == 'aq':
            qbidx += 4
        else:
            pass
        
        if type(cwd) is np.int64:
            cwd = str(cwd)
        
        if len(cwd) > 0:
            if qbidx <= 3:
                qb_num = qbidx
                qb_type = 'dq' 
            else:
                if qbidx == 4:
                    qb_num = 0
                elif qbidx == 5:
                    qb_num = 3
                elif qbidx == 6:
                    qb_num = 1
                elif qbidx == 7:
                    qb_num = 2
                else:
                    raise Exception("Invalid qbidx: {}".format(qbidx))
                qb_type = 'aq' 
                
            row = patch_size * patch_idx[0] + ucl_size * ucl_idx[0] + (qb_num // 2)
            col = patch_size * patch_idx[1] + ucl_size * ucl_idx[1] + (qb_num % 2) 
            if qb_type == 'dq':
                row = 2*row
                col = 2*col
            else:
                row = 2*row + 1
                col = 2*col + 1

            if 'cz' in cwd:
                lattice_array[row][col] = cwd.replace('cz', 'C')
            elif cwd == 'meas':
                lattice_array[row][col] = 'M '
            elif cwd == 'cx':
                lattice_array[row][col] = 'CX'
            elif cwd == 'h':
                lattice_array[row][col] = 'H '
            elif cwd == 'm':
                lattice_array[row][col] = 'm '
            elif cwd == 'sdag_h':
                lattice_array[row][col] = 'SH'
            elif cwd == 'h_s':
                lattice_array[row][col] = 'HS'
            elif cwd == '1':
                lattice_array[row][col] = '1 '
            elif cwd == '0':
                lattice_array[row][col] = '0 '
            elif cwd == 'i': 
                lattice_array[row][col] = 'I '
            elif cwd == 'x': 
                lattice_array[row][col] = 'X '
            elif cwd == 'y':
                lattice_array[row][col] = 'Y '
            elif cwd == 'z':
                lattice_array[row][col] = 'Z '
            elif cwd == 'h_sdag_h':
                lattice_array[row][col] = 'HH'
            else:
                pass

    print_lattice(lattice_array, param.code_dist)
    return

def debug_patch(param, cwd_list, arr_qb_type = 'dq'):
    patch_size = (param.code_dist + 1)    
    num_row_dq = patch_size + 1  
    num_col_dq = patch_size + 1  
    ucl_size = 2

    lattice_array = np.full((num_row_dq+num_row_dq, \
        num_col_dq+num_col_dq), '  ', dtype='U2')
    for i in range(num_row_dq+num_row_dq):
        for j in range(num_col_dq+num_col_dq):
            if (i+j) % 2 == 0:
                lattice_array[i][j] = '- ' 

    for (ucrow, uccol, qbidx), cwd in np.ndenumerate(cwd_list):
        patch_idx = (0, 0)
        ucl_idx = (ucrow, uccol)
        
        if arr_qb_type == 'aq':
            qbidx += 4
        else:
            pass
        
        if type(cwd) is np.int64:
            cwd = str(cwd)
        
        if len(cwd) > 0:
            if qbidx <= 3:
                qb_num = qbidx
                qb_type = 'dq' 
            else:
                if qbidx == 4:
                    qb_num = 0
                elif qbidx == 5:
                    qb_num = 3
                elif qbidx == 6:
                    qb_num = 1
                elif qbidx == 7:
                    qb_num = 2
                else:
                    raise Exception("Invalid qbidx: {}".format(qbidx))
                qb_type = 'aq' 
                
            row = patch_size * patch_idx[0] + ucl_size * ucl_idx[0] + (qb_num // 2)
            col = patch_size * patch_idx[1] + ucl_size * ucl_idx[1] + (qb_num % 2) 
            if qb_type == 'dq':
                row = 2*row
                col = 2*col
            else:
                row = 2*row + 1
                col = 2*col + 1

            if 'cz' in cwd:
                lattice_array[row][col] = cwd.replace('cz', 'C')
            elif cwd == 'meas':
                lattice_array[row][col] = 'M '
            elif cwd == 'cx':
                lattice_array[row][col] = 'CX'
            elif cwd == 'h':
                lattice_array[row][col] = 'H '
            elif cwd == 'm':
                lattice_array[row][col] = 'm '
            elif cwd == 'sdag_h':
                lattice_array[row][col] = 'SH'
            elif cwd == 'h_s':
                lattice_array[row][col] = 'HS'
            elif cwd == '1':
                lattice_array[row][col] = '1 '
            elif cwd == '0':
                lattice_array[row][col] = '0 '
            elif cwd == 'i': 
                lattice_array[row][col] = 'I '
            elif cwd == 'x': 
                lattice_array[row][col] = 'X '
            elif cwd == 'y':
                lattice_array[row][col] = 'Y '
            elif cwd == 'z':
                lattice_array[row][col] = 'Z '
            elif cwd == 'h_sdag_h':
                lattice_array[row][col] = 'HH'
            else:
                pass

    print_lattice(lattice_array, param.code_dist)
    return


def apply_lop_sign (counts, lop_sign):
    counts_w_sign = {}
    for k, v in counts.items():
        k_w_sign = ''
        for s, sign in zip(k, lop_sign):
            if sign == '+':
                k_w_sign += s
            else:
                if s == '0':
                    k_w_sign += '1'
                else:
                    k_w_sign += '0'
            
        counts_w_sign[k_w_sign] = v
    
    return counts_w_sign


def apply_lop_sign_to_c (abcd_reg, lop_sign):
    if lop_sign[0] == '-':
        a = abcd_reg['a']
        b = abcd_reg['b']
        c = 1 - abcd_reg['c']
        d = abcd_reg['d']
    else:
        a = abcd_reg['a']
        b = abcd_reg['b']
        c = abcd_reg['c']
        d = abcd_reg['d']
    
    return {'a':a,'b':b,'c':c,'d':d}

def merge_bp (current_bp, new_bp):
    next_bp = current_bp[:]
    for i, (c, n) in enumerate(zip(next_bp, new_bp)):
        if c == 'I':
            next_bp[i] = n
        elif c == 'X':
            if n == 'I':
                next_bp[i] = 'X'
            elif n == 'X':
                next_bp[i] = 'I'
            elif n == 'Y':
                next_bp[i] = 'Z'
            elif n == 'Z':
                next_bp[i] = 'Y'
            else:
                raise Exception()
        elif c == 'Y':
            if n == 'I':
                next_bp[i] = 'Y'
            elif n == 'X':
                next_bp[i] = 'Z'
            elif n == 'Y':
                next_bp[i] = 'I'
            elif n == 'Z':
                next_bp[i] = 'X'
            else:
                raise Exception()
        elif c == 'Z':
            if n == 'I':
                next_bp[i] = 'Z'
            elif n == 'X':
                next_bp[i] = 'Y'
            elif n == 'Y':
                next_bp[i] = 'X'
            elif n == 'Z':
                next_bp[i] = 'I'
            else:
                raise Exception()
        else:
            raise Exception()
        
    return next_bp

def get_lop_qb (target_pchidx, pchtype, code_distance):
    pchrow, pchcol = target_pchidx
        
    if pchtype == 'x':
        qb_lop_x = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in [(pchrow + 1) * (code_distance + 1) - 1] \
            for j in range((pchcol) * (code_distance + 1) + 1, (pchcol + 1) * (code_distance + 1))]
        qb_lop_z = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range((pchrow) * (code_distance + 1) + 1, (pchrow + 1) * (code_distance + 1)) \
            for j in [(pchcol) * (code_distance + 1) + 1]]
    elif pchtype == 'mb':
        qb_lop_x = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in [(pchrow + 1) * (code_distance + 1) - 1] \
            for j in range((pchcol) * (code_distance + 1) + 1, (pchcol + 1) * (code_distance + 1))]
        qb_lop_z = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range((pchrow -1) * (code_distance + 1) + 1, (pchrow) * (code_distance + 1)) \
            for j in [(pchcol) * (code_distance + 1) + 1]] + \
                [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range((pchrow) * (code_distance + 1) + 1, (pchrow + 1) * (code_distance + 1)) \
            for j in [(pchcol) * (code_distance + 1) + 1]]
    elif pchtype == 'zb':
        qb_lop_x = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range((pchrow - 1) * (code_distance + 1) +1, (pchrow) * (code_distance + 1) +1) \
            for j in [(pchcol + 1) * (code_distance + 1) - 1]]
        qb_lop_z = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range((pchrow) * (code_distance + 1), (pchrow + 1) * (code_distance + 1)) \
            for j in [(pchcol + 1) * (code_distance + 1) - 1]]
    elif pchtype == 'm':
        qb_lop_z = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in [(pchrow + 1) * (code_distance + 1) - 1] \
            for j in range((pchcol) * (code_distance + 1) + 1, (pchcol + 1) * (code_distance + 1))]
        qb_lop_x = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range((pchrow) * (code_distance + 1) + 1, (pchrow + 1) * (code_distance + 1)) \
            for j in [(pchcol) * (code_distance + 1) + 1]]
    elif pchtype == 'dq_eb_l':
        qb_lop_x = ([convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range(pchrow*(code_distance+1), (pchrow+1)*(code_distance+1)) \
            for j in [(pchcol)*(code_distance+1)+1]])
        qb_lop_z = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range((pchrow -1)*(code_distance+1)+1, pchrow*(code_distance +1) +1) \
            for j in [(pchcol)*(code_distance +1) +1]]
    elif pchtype == 'dq_eb_r':
        qb_lop_x = ([convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range(pchrow*(code_distance+1)+1, (pchrow+1)*(code_distance+1)) \
            for j in [(pchcol+1)*(code_distance+1)-1]])
        qb_lop_z = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range((pchrow-1)*(code_distance+1)+1, pchrow*(code_distance+1)+2) \
            for j in [(pchcol+1)*(code_distance+1)-1]]
    elif pchtype == 'dq_ob_l':
        qb_lop_x = ([convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range(pchrow*(code_distance+1)+1, (pchrow+1)*(code_distance+1)) \
            for j in [(pchcol)*(code_distance+1)+1]])
        qb_lop_z = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range((pchrow-1)*(code_distance+1)+1, pchrow*(code_distance+1)+2) \
            for j in [(pchcol)*(code_distance+1)+1]]
    elif pchtype == 'dq_ob_r':
        qb_lop_x = ([convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range(pchrow*(code_distance+1), (pchrow+1)*(code_distance+1)) \
            for j in [(pchcol+1)*(code_distance+1)-1]])
        qb_lop_z = [convert_idx_2d_to_5d (code_distance,'dq',i,j) \
            for i in range((pchrow-1)*(code_distance+1)+1, pchrow*(code_distance+1)+1) \
            for j in [(pchcol+1)*(code_distance+1)-1]]
    else:
        raise Exception("Undefined pchtype: {} at {}".format(pchtype, target_pchidx))
    return qb_lop_x, qb_lop_z

def convert_idx_2d_to_5d (code_distance, qb_type, row, col):
    patch_size = (code_distance + 1)
    ucl_size = 2
    patch_idx = (row // patch_size, col // patch_size)
    ucl_idx = ((row % patch_size) // ucl_size, (col % patch_size) // ucl_size)
    qb_idx = ((row % patch_size) % ucl_size) * 2 + ((col % patch_size) % ucl_size)
    
    if qb_type == 'dq':
        pass
    else:
        if qb_idx == 0:
            qb_idx = 4
        elif qb_idx == 1:
            qb_idx = 6
        elif qb_idx == 2:
            qb_idx = 7
        elif qb_idx == 3:
            qb_idx = 5
        else:
            raise Exception ("Invalid qb_idx")

    return patch_idx[0], patch_idx[1], ucl_idx[0], ucl_idx[1], qb_idx   
