import os, sys
#
from absl import flags
from absl import app
#
curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
comp_dir = os.path.join(curr_dir, "compiler")
sys.path.insert(0, comp_dir)
from gsc_compiler import gsc_compiler


def gen_single_esm(num_lq):
    qc_name = "esm_n{}".format(int(num_lq-2))
    compiler = gsc_compiler()
    compiler.setup(qc_name = qc_name, 
                   compile_mode = "assemble")
    ##
    f = open(compiler.qisa_filepath, 'w')
    ### PREP_INFO
    prep_line = "PREP_INFO NA NA NA NA\n"
    f.write(prep_line)

    ### LQI
    lqi_temp = "LQI NA NA"
    bit_def = compiler.isa_def["bit_format"]
    len_target = bit_def["target"]["len"]//2
    offset_hexlen = bit_def["lq_addr_offset"]["len"]//4

    max_offset, last_idx = divmod(num_lq, len_target)
    for offset in range(0, max_offset):
        offset_hex = "0x"+format(offset, "0{}x".format(offset_hexlen))
        target_list = "["
        for idx in range(0, len_target):
            target_list += "T,"
        target_list += "]\n"
        lqi_line = ' '.join([lqi_temp, offset_hex, target_list]) 
        f.write(lqi_line)
    if last_idx != 0:
        max_offset_hex = "0x"+format(max_offset, "0{}x".format(offset_hexlen))
        target_list = "["
        for idx in range(0, last_idx):
            target_list += "T,"
        for idx in range(last_idx, len_target):
            target_list += "-,"
        target_list += "]\n"
        lqi_line = ' '.join([lqi_temp, max_offset_hex, target_list])
        f.write(lqi_line)

    ### MERGE_INFO
    merge_temp = "MERGE_INFO NA NA"
    bit_def = compiler.isa_def["bit_format"]
    len_target = bit_def["target"]["len"]//2
    offset_hexlen = bit_def["lq_addr_offset"]["len"]//4

    max_offset, last_idx = divmod(num_lq, len_target)
    for offset in range(0, max_offset):
        offset_hex = "0x"+format(offset, "0{}x".format(offset_hexlen))
        target_list = "["
        for idx in range(0, len_target):
            if offset == 0 and idx == 0:
                target_list += "Y,"
            else:
                target_list += "Z,"
        target_list += "]\n"
        merge_line = ' '.join([merge_temp, offset_hex, target_list]) 
        f.write(merge_line)
    if last_idx != 0:
        max_offset_hex = "0x"+format(max_offset, "0{}x".format(offset_hexlen))
        target_list = "["
        for idx in range(0, last_idx):
            if max_offset == 0 and idx == 0:
                target_list += "Y,"
            else:
                target_list += "Z,"
        for idx in range(last_idx, len_target):
            target_list += "I,"
        target_list += "]\n"
        merge_line = ' '.join([merge_temp, max_offset_hex, target_list])
        f.write(merge_line)
    ### RUN_ESM
    resm_line = "RUN_ESM NA NA NA NA\n"
    f.write(resm_line)
    f.close()
    #
    compiler.run()
    return qc_name


def main(argv):
    num_lq = FLAGS.num_lq
    qbin = gen_single_esm(num_lq)
    print("Quantum program (binary): {} is generated".format(qbin))
    return


if __name__ == "__main__":
    FLAGS = flags.FLAGS
    flags.DEFINE_integer("num_lq", 7, "target number of logical qubits", short_name='q')
    app.run(main)
