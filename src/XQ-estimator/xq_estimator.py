import os, sys
import shutil
#
curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
par_dir = os.path.join(curr_dir, os.pardir)
comm_dir = os.path.join(curr_dir, "rsfq_common")
custom_dir = os.path.join(comm_dir, "custom")
temp_dir = os.path.join(curr_dir, "temporary")
cmos_dir = os.path.join(*[curr_dir, "CryoModel", "CryoPipeline"])
# 
from absl import flags
from absl import app
#
import pandas as pd
pd.options.display.max_columns=15
#
from scipy import interpolate
from parse import compile
import numpy as np
from math import *
#
sys.path.insert(0, par_dir)
from sim_param import sim_param
from unit_stat import unit_stat_est
from util import *
from visualization import *
#
sys.path.insert(0, comm_dir)
from insert_sfq_gate import insert_sfq_gate
from adjust_sfq_timing import adjust_sfq_timing
#
sys.path.insert(0, custom_dir)
import ndro_ram, sr_mem, sptree, mgtree, ndro_nw, ndro_buf, dff_buf, pe
#
sys.path.insert(0, cmos_dir)
from cmos_estimator import run_cmos_model


class xq_estimator:
    def __init__(self):
        self.config = None
        self.num_lq = None
        self.dump_synth = None
        self.regen_synth = None
        self.dump_est = None
        self.regen_est = None
        self.param = None
    
    def setup(self, 
              config=None, 
              num_lq=None, 
              dump_synth=None,
              regen_synth=None,
              dump_est=None,
              regen_est=None):

        if config is not None:
            self.config = config
        if num_lq is not None:
            self.num_lq = num_lq
        if dump_synth is not None:
            self.dump_synth = dump_synth
        if regen_synth is not None:
            self.regen_synth = regen_synth
        if dump_est is not None:
            self.dump_est = dump_est
        if regen_est is not None:
            self.regen_est = regen_est

        if self.config is not None and self.num_lq is not None:
            config_filepath = "{}/configs/{}.json".format(par_dir, self.config)
            isadef_filepath = "{}/isa_format.json".format(par_dir)
            self.param = sim_param(config_filepath, isadef_filepath, self.num_lq)
            self.set_rtl_define(self.param)

        return


    def set_rtl_define(self, param):
        rtl_p_dict = dict()
        rtl_p_dict.update(param.qb_plane)
        rtl_p_dict.update(param.bw_def)
        rtl_p_dict.update(param.opcode_def)
        rtl_p_dict.update(param.g_cyc)

        for unit_name, unit_cfg in param.arch_unit.items():
            rtl_p_dict.update(unit_cfg)
        rtl_p_dict = {k.upper():v for (k, v) in rtl_p_dict.items()} 
        
        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)
        fill_param_line (os.path.join(curr_dir, "define_template.v"), os.path.join(temp_dir, "define.v"), rtl_p_dict)

        return

    def run(self):
        unit_stat_list = []
        for unit_name, unit_cfg in self.param.arch_unit.items():
            uarch = unit_cfg["uarch"]
            temp, tech, vopt = tuple(unit_cfg["temp_tech"].split("_"))
            if vopt == "Vopt":
                vopt = True
            else:
                vopt = False
            #
            if unit_name in ["QIM", "QXU"]:
                freq = 100
                p_stat = 0
                p_dyn = 0
                area = 0
                munit_df = None
            else:
                freq, p_stat, p_dyn, area, munit_df = self.unit_model(unit_name, uarch, temp, tech, vopt)
            unit_stat_list.append(unit_stat_est(name=unit_name, 
                                            uarch=uarch, 
                                            temp=temp,
                                            tech=tech, 
                                            freq=freq, 
                                            p_stat=p_stat,
                                            p_dyn=p_dyn,
                                            area=area,
                                            munit_df=munit_df)) 

        ## synchronize frequency
        sync_freq_by_domain(unit_stat_list)

        ## unit-specific stat
        for unit_stat in unit_stat_list:
            # PSU
            if unit_stat.name == "PSU":
                # tune num_mask_gen (following result frequency)
                if unit_stat.tech in ["RSFQ", "ERSFQ"] and unit_stat.uarch == "maskshare":
                    self.param.refine_psu_param(target="estimator", freq=unit_stat.freq)
                    self.set_rtl_define(self.param)
                    self.regen_est = True
                    self.regen_synth = False
                    unit_stat.freq, unit_stat.pstat, unit_stat.p_dyn, unit_stat.area, unit_stat.munit_df = self.sfq_model(unit_stat.name, unit_stat.uarch, unit_stat.tech)
                #
                unit_stat.psu_inst_bw = (self.param.cwd_bw * self.param.num_mask * unit_stat.freq) #Gbps
            # EDU
            if unit_stat.name == "EDU":
                ## token_setup
                if unit_stat.tech == "CMOS":
                    if unit_stat.uarch == "baseline":
                        token_setup_mf = 1
                    elif unit_stat.uarch == "fast":
                        token_setup_mf = 4
                    else:
                        raise Exception("xq_estimator - run: EDU with (uarch, tech) = ({}, {}) is not currently supported".format(unit_stat.uarch, unit_stat.tech))
                elif unit_stat.tech in ["RSFQ", "ERSFQ"]:
                    if unit_stat.uarch == "baseline":
                        token_setup_mf = 1
                    elif unit_stat.uarch in ["fast", "fastsliding"]:
                        mun_list = []
                        for mun in unit_stat.munit_df["Name"]:
                            if "tkset" in mun or "flgset" in mun:
                                mun_list.append(mun)
                        cond = None
                        for mun in mun_list:
                            try:
                                cond = cond | (unit_stat.munit_df["Name"] == mun)
                            except:
                                cond = (unit_stat.munit_df["Name"] == mun)
                        latency = sum(unit_stat.munit_df[cond]["Latency(ps)"]) # ps
                        
                        token_setup_mf = ceil(unit_stat.freq * latency * 1e-3) # cyc
                    else:
                        raise Exception("xq_estimator - run: EDU with (uarch, tech) = ({}, {}) is not currently supported".format(unit_stat.uarch, unit_stat.tech))
                else:
                    raise Exception("xq_estimator - run: EDU with (uarch, tech) = ({}, {}) is not currently supported".format(unit_stat.uarch, unit_stat.tech))

                ## spike_propagation
                spike_propagation_mf = 1

                ## error_match
                if unit_stat.tech == "CMOS":
                    error_match_mf = 1
                elif unit_stat.tech in ["RSFQ", "ERSFQ"]:
                    if unit_stat.uarch == "baseline":
                        error_match_mf = 1
                    elif unit_stat.uarch in ["fast", "fastsliding"]:
                        mun_list = []
                        for mun in unit_stat.munit_df["Name"]:
                            if "errmatch" in mun:
                                mun_list.append(mun)
                        cond = None
                        for mun in mun_list:
                            try:
                                cond = cond | (unit_stat.munit_df["Name"] == mun)
                            except:
                                cond = (unit_stat.munit_df["Name"] == mun)
                        latency = sum(unit_stat.munit_df[cond]["Latency(ps)"]) # ps
                        
                        error_match_mf = ceil(unit_stat.freq * latency * 1e-3) # cyc                       
                    else:
                        raise Exception("xq_estimator - run: EDU with (uarch, tech) = ({}, {}) is not currently supported".format(unit_stat.uarch, unit_stat.tech))

                ## param 
                unit_stat.edu_cycle_param = {
                        "token_setup_mf": token_setup_mf,
                        "spike_propagation_mf": spike_propagation_mf,
                        "error_match_mf": error_match_mf
                }
        ### clean temp_dir
        try:
            cmdline("rm {}/*".format(temp_dir))
        except:
            pass

        return unit_stat_list


    def unit_model(self, unit_name, uarch, temp, tech, vopt):
        if tech == "CMOS":
            freq, p_stat, p_dyn, area = self.cmos_model(unit_name, uarch, temp, vopt)
            munit_df = None

        elif (tech == "RSFQ" or tech == "ERSFQ") and temp == "4K":
            freq, p_stat, p_dyn, area, munit_df = self.sfq_model(unit_name, uarch, tech)

        else: 
            raise Exception("unit model - temp_tech {}_{} is currently not supported".format(temp, tech))
        return freq, p_stat, p_dyn, area, munit_df


    def cmos_model(self, unit_name, uarch, temp, vopt):
        unit_dir = os.path.join(*[curr_dir, unit_name, uarch, "cmos"])
        param = self.param
         
        # target fp table
        prefix = temp
        if vopt:
            prefix += "vopt"
        tb_path = os.path.join(unit_dir, "{}_fptbl.csv".format(prefix))
        #
        if os.path.exists(tb_path): 
            fp_df = pd.read_csv(tb_path)
        else:
            fp_df = pd.DataFrame(columns = ["CODE_DIST", "NUM_LQ", "Frequency(GHz)", "PowerStatic(W)", "PowerDynamic(W)", "Area(mm^2)"])
        cond_dist = (fp_df["CODE_DIST"] == param.code_dist)
        cond_lq = (fp_df["NUM_LQ"] == param.num_lq)
        cond_match = cond_dist & cond_lq

        # 
        if not self.regen_synth and not self.regen_est:
            # Check whether the data of target configuration exists
            if not fp_df[cond_match].empty:
                fp_entry = fp_df[cond_match].iloc[-1]
                freq = fp_entry["Frequency(GHz)"]
                p_stat = fp_entry["PowerStatic(W)"]
                p_dyn = fp_entry["PowerDynamic(W)"]
                area = 0
            
            elif len(fp_df[cond_dist]) > 1:
                dist_df = fp_df[cond_dist]
                x = dist_df["NUM_LQ"].to_numpy()
                z_freq = dist_df["Frequency(GHz)"].to_numpy()
                z_pstat = dist_df["PowerStatic(W)"].to_numpy()
                z_pdyn = dist_df["PowerDynamic(W)"].to_numpy()
                ### interpolate
                freq_ftn = interpolate.interp1d(x, z_freq, fill_value="extrapolate")
                pstat_ftn = interpolate.interp1d(x, z_pstat, fill_value="extrapolate")
                pdyn_ftn = interpolate.interp1d(x, z_pdyn, fill_value="extrapolate")
                ### get fp
                freq = freq_ftn(param.num_lq)
                p_stat = pstat_ftn(param.num_lq)
                p_dyn = pdyn_ftn(param.num_lq)
                area = 0 # no area support

            elif len(fp_df[cond_lq]) > 1:
                lq_df = fp_df[cond_lq]
                x = lq_df["CODE_DIST"].to_numpy()
                z_freq = lq_df["Frequency(GHz)"].to_numpy()
                z_pstat = lq_df["PowerStatic(W)"].to_numpy()
                z_pdyn = lq_df["PowerDynamic(W)"].to_numpy()
                ### interpolate
                freq_ftn = interpolate.interp1d(x, z_freq, fill_value="extrapolate")
                pstat_ftn = interpolate.interp1d(x, z_pstat, fill_value="extrapolate")
                pdyn_ftn = interpolate.interp1d(x, z_pdyn, fill_value="extrapolate")
                ### get fp
                freq = freq_ftn(param.code_dist)
                p_stat = pstat_ftn(param.code_dist)
                p_dyn = pdyn_ftn(param.code_dist)
                area = 0 # no area support

            else:
                x = []
                z_freq = []
                z_pstat = []
                z_pdyn = []

                if len(fp_df["CODE_DIST"].unique()) > 1:
                    for code_dist in fp_df["CODE_DIST"].unique():
                        cond_dist = (fp_df["CODE_DIST"] == code_dist)
                        dist_df = fp_df[cond_dist]

                        y = dist_df["NUM_LQ"].to_numpy()
                        w_freq = dist_df["Frequency(GHz)"].to_numpy()
                        w_pstat = dist_df["PowerStatic(W)"].to_numpy()
                        w_pdyn = dist_df["PowerDynamic(W)"].to_numpy()
                        if len(y) > 1:
                            ### interpolate
                            freq_ftn = interpolate.interp1d(y, w_freq, fill_value="extrapolate")
                            pstat_ftn = interpolate.interp1d(y, w_pstat, fill_value="extrapolate")
                            pdyn_ftn = interpolate.interp1d(y, w_pdyn, fill_value="extrapolate")
                            ### get fp
                            x.append(code_dist)
                            z_freq.append(freq_ftn(param.num_lq))
                            z_pstat.append(pstat_ftn(param.num_lq))
                            z_pdyn.append(pdyn_ftn(param.num_lq))
                        else:
                            raise Exception("cmos_model - not enough data for extra/interpolation")
                else:
                    raise Exception("cmos_model - not enough data for extra/interpolation")

                ### interpolate
                freq_ftn = interpolate.interp1d(x, z_freq, fill_value="extrapolate")
                pstat_ftn = interpolate.interp1d(x, z_pstat, fill_value="extrapolate")
                pdyn_ftn = interpolate.interp1d(x, z_pdyn, fill_value="extrapolate")
                ### get fp
                freq = freq_ftn(param.code_dist)
                p_stat = pstat_ftn(param.code_dist)
                p_dyn = pdyn_ftn(param.code_dist)
                area = 0 # no area support

        else: # regen_synth or regen_est
        # Check brief dc_shell installation
            if (self.regen_synth or self.regen_result) and not bool(cmdline("which dc_shell")): 
                raise Exception("cmos_model - Please install: dc_shell")

            rtl_dir = os.path.join(*[curr_dir, unit_name, uarch, "rtl"])
            out_dir = os.path.join(unit_dir, "D{}_Q{}".format(param.code_dist, param.num_lq))
            # copy target define.v to rtl_dir
            shutil.copy(os.path.join(temp_dir, "define.v"), rtl_dir)

            # run CryoModel
            ## set input vdd, vth
            if vopt: 
                # NOTE: Vdd & Vth for Vopt option are fixed 
                vdd = 0.38
                vth = 0.123
            else:
                # input vdd/vth 0 -> set default vdd, vth values in CryoModel
                vdd = 0
                vth = 0
            ## change working dierctory
            os.chdir(cmos_dir)
            ## run
            freq, p_stat, p_dyn, freq_300k, p_stat_300k, p_dyn_300k, area = run_cmos_model(
                           temperature = int(temp[:-1]), 
                           node = 45, 
                           vdd = vdd,
                           vth = vth, 
                           design_name = unit_name, 
                           rtl_dir = rtl_dir, 
                           out_dir = out_dir, 
                           regen_synth = self.regen_synth,
                           regen_est = self.regen_est
                           )
            ## restore working directory
            os.chdir(curr_dir)
            # remove target define.v from rtl_dir
            os.remove("{}/define.v".format(rtl_dir))
            
            # dump fp result to the tables
            if self.dump_est:
                ## if target entry exist, exclude it
                fp_df = fp_df[~cond_match]
                ## add fp entry
                fp_cols = fp_df.columns
                fp_data = [int(param.code_dist), int(param.num_lq), round(freq, 2), round(p_stat, 5), round(p_dyn, 5)]
                fp_entry = dict()
                for col, data in zip(fp_cols, fp_data):
                    fp_entry[col] = data
                entry_df = pd.DataFrame(fp_entry, index=[0])
                fp_df = pd.concat([fp_df, entry_df], ignore_index=True)

                ## ordering
                fp_df = fp_df.sort_values(by=["CODE_DIST", "NUM_LQ"], ascending=True)
                ## store
                fp_df.to_csv(tb_path, index=False)
                
                # if 300k table has no corresponding entry, also add it
                tb_path_300k = os.path.join(unit_dir, "300K_fptbl.csv")
                try:
                    fp_df_300k = pd.read_csv(tb_path_300k)
                except:
                    fp_df_300k = pd.DataFrame(columns = ["CODE_DIST", "NUM_LQ", "Frequency(GHz)", "PowerStatic(W)", "PowerDynamic(W)"])
                cond = (fp_df_300k["CODE_DIST"] == param.code_dist) & (fp_df_300k["NUM_LQ"] == param.num_lq)
                ## filter
                if fp_df_300k[cond].empty:
                    ## add entry
                    fp_entry_300k = [int(param.code_dist), int(param.num_lq), round(freq_300k, 2), round(p_stat_300k, 5), round(p_dyn_300k, 5)]
                    fp_df_300k.loc[len(fp_df_300k)] = fp_entry_300k
                    ## ordering
                    fp_df_300k = fp_df_300k.sort_values(by=["CODE_DIST", "NUM_LQ"], ascending=True)
                    ## store
                    fp_df_300k.to_csv(tb_path_300k, index=False)
                else:
                    pass
        
        # power unit: W -> mW
        p_stat = round(p_stat*1e3, 2)
        p_dyn = round(p_dyn*1e3, 2)
       
        return freq, p_stat, p_dyn, area

    ###
    def sfq_model(self, unit_name, uarch, tech):
        param = self.param
        assert "mitll".upper() in param.rsfqlib.upper() 

        unit_dir = os.path.join(*[curr_dir, unit_name, uarch, "rsfq"])
        tb_dir = os.path.join(unit_dir, "rsfq_fpatbl")
        tb_path = os.path.join(tb_dir, "D{}_Q{}.csv".format(param.code_dist, param.num_lq))
       
        ###
        if not self.regen_est and os.path.exists(tb_path):
            munit_df = pd.read_csv(tb_path)
        else: # regen_reslut
            os.chdir(unit_dir)
            #
            freq = 100
            p_stat = 0 
            e_dyn = 0
            area = 0
            # 
            gen_param = dict(param.qb_plane, **param.bw_def)
            unit_param = param.arch_unit[unit_name]
            #
            munit_temppath = os.path.join(unit_dir, "microunit_template.json")
            munit_dict = getJsonData(munit_temppath)
            munit_col = ["Name", "Num", "Freq(GHz)", "Pstat(nW)", "Edyn(nJ/Gacc)", "Area(um^2)", "Gate", "JJ", "Latency(ps)", "Pstat_sum(nW)", "Edyn_sum(nJ/Gacc)", "Area_sum(um^2)", "Gate_sum", "JJ_sum"]
            munit_df = pd.DataFrame(columns=munit_col)
            #
            for munit_name, munit_prop in munit_dict.items():
                # set munit num
                munit_num = munit_prop["num"]
                if not isinstance(munit_num, int):
                    if munit_num in gen_param.keys():
                        munit_num = gen_param[munit_num]
                    elif munit_num in unit_param.keys():
                        munit_num = unit_param[munit_num]
                    munit_prop["num"] = munit_num
                else:
                    pass
                #
                for mp_name, mp_target in munit_prop["param"].items():
                    if mp_target in gen_param.keys():
                        mp_val = gen_param[mp_target]
                    elif mp_target in unit_param.keys():
                        mp_val = unit_param[mp_target]
                    elif isinstance(mp_target, int):
                        mp_val = munit_prop["param"][mp_name]
                    munit_prop["param"][mp_name] = mp_val

                # run rsfq_munit_model
                munit_freq, munit_p_stat, munit_e_dyn, munit_area, munit_gc, munit_jj, munit_latency = rsfq_munit_model(munit_name, munit_prop, param.rsfqlib, self.dump_synth, self.regen_synth)            
                munit_entry = [munit_name, \
                               munit_prop["num"], \
                               munit_freq, \
                               munit_p_stat, \
                               munit_e_dyn, \
                               munit_area, \
                               munit_gc, \
                               munit_jj,\
                               munit_latency,
                               munit_prop["num"]*munit_p_stat, \
                               munit_prop["num"]*munit_e_dyn, \
                               munit_prop["num"]*munit_area, \
                               munit_prop["num"]*munit_gc, \
                               munit_prop["num"]*munit_jj \
                               ]
                munit_df.loc[len(munit_df)] = munit_entry

            if self.dump_est:
                if not os.path.exists(tb_dir):
                    os.mkdir(tb_dir)
                munit_df.to_csv(tb_path, index=False)
            os.chdir(curr_dir)

        freq = round(min(munit_df["Freq(GHz)"]), 2)
        p_stat = round(sum(munit_df["Pstat_sum(nW)"]), 2)
        e_dyn = round(sum(munit_df["Edyn_sum(nJ/Gacc)"]), 2)
        area = round(sum(munit_df["Area_sum(um^2)"]), 2)
        # unit
        p_stat = round(p_stat*1e-6, 3) # mW
        p_dyn = round(e_dyn*freq*1e-6, 4) # mW
        area = round(area*1e-6, 3) # mm^2           

        #
        if tech == "ERSFQ":
            p_stat = 0
            p_dyn *= 2
            area *= 1.4
            munit_df["Pstat(nW)"] = munit_df["Pstat(nW)"]*0
            munit_df["Edyn(nJ/Gacc)"] = munit_df["Edyn(nJ/Gacc)"]*2
            munit_df["Area(um^2)"] = munit_df["Area(um^2)"]*1.4
            munit_df["JJ"] = munit_df["JJ"]*1.4
            munit_df["Pstat_sum(nW)"] = munit_df["Pstat_sum(nW)"]*0
            munit_df["Edyn_sum(nJ/Gacc)"] = munit_df["Edyn_sum(nJ/Gacc)"]*2
            munit_df["Area_sum(um^2)"] = munit_df["Area_sum(um^2)"]*1.4
            munit_df["JJ_sum"] = munit_df["JJ_sum"]*(1.4)

        return freq, p_stat, p_dyn, area, munit_df

###
def rsfq_munit_model(munit_name, munit_prop, rsfqlib, dump, regen):
    munit_freq = 100
    munit_p_stat = 0
    munit_e_dyn = 0
    munit_area = 0
    munit_gc = 0
    munit_jj = 0
    munit_latency = 0
    ##
    if "demux" in munit_name or "mux" in munit_name:
        if munit_prop["param"]["NUM_DATA"] == 1:
            return munit_freq, munit_p_stat, munit_e_dyn, munit_area, munit_gc, munit_jj, munit_latency
    if "ndroram" in munit_name: 
        if munit_prop["param"]["NUM_DATA"] == 1:
            return munit_freq, munit_p_stat, munit_e_dyn, munit_area, munit_gc, munit_jj, munit_latency
    ##
    src_type, scope_type = tuple(munit_prop["type"].split("_"))
    if scope_type == "common":
        munit_name = ('_').join(munit_name.split("_")[:-1])
    #
    ### Generate rsfq gate netlist 
    munit_conn, munit_bd = gen_rsfq_netlist(
                 munit_name, 
                 munit_prop,
                 rsfqlib,
                 dump = dump, 
                 regen = regen
                 )
    ### Generate frequency optimized netlist (while considering clock distribution)
    if munit_name in ["sptree", "mgtree", "dffbuf"]:
        munit_conn_opt = None
        munit_bd_opt = munit_bd
        munit_conn_clk = None
        munit_bd_clk = None
    else:
        wpath = get_wpath(munit_name, munit_prop, "freqopt_netlist")
        munit_conn_opt, munit_bd_opt, munit_conn_clk, munit_bd_clk = opt_rsfq_netlist(munit_conn, 
                     munit_bd,
                     rsfqlib,
                     clk = munit_prop["clk"],
                     wpath = wpath, 
                     dump = dump, 
                     regen = regen
                     )
    ### Calculate frequency / power / area values
    munit_freq, munit_p_stat, munit_e_dyn, munit_area, munit_gc, munit_jj = get_rsfq_fpa(munit_conn_opt, munit_bd_opt, munit_bd_clk, rsfqlib)
   
    ### Calculatate latency
    munit_latency = get_rsfq_latency(
            clk = munit_prop["clk"],
            conn_clk = munit_conn_clk,
            conn_opt = munit_conn_opt, 
            munit_freq = munit_freq,
            munit_name = munit_name, 
            munit_prop = munit_prop,
            rsfqlib = rsfqlib)
    ##
    return munit_freq, munit_p_stat, munit_e_dyn, munit_area, munit_gc, munit_jj, munit_latency


###
def gen_rsfq_netlist (munit_name, munit_prop, rsfqlib, dump, regen):
    #
    src_type, scope_type = tuple(munit_prop["type"].split("_"))
    if src_type == "rtl":
        if scope_type == "unit":
            src = os.path.join(*[os.pardir, "rtl", "{}.v".format(munit_name)]) 
        elif scope_type == "common":
            src = os.path.join(*[comm_dir, "rtl", "{}.v".format(munit_name)])
        else:
            raise Exception("gen_rsfq_netlist (rtl) - does not suport scope_type: {}".format(scope_type))

        # gen_gate_rtl
        wpath = get_wpath(munit_name, munit_prop, "gate_rtl")
        gate_rtl_lines = gen_gate_rtl(src, munit_name, munit_prop["param"], rsfqlib, wpath, dump, regen)
           
        # insert sfq gates
        wpath = get_wpath(munit_name, munit_prop, "sfq_netlist")
        conn, bd = insert_sfq_gate(rtl_lines = gate_rtl_lines,
                                   plib_path = os.path.join(comm_dir, rsfqlib+".csv"),
                                   clib_path = os.path.join(comm_dir, rsfqlib+".v"),
                                   dump_path = wpath,
                                   dump = dump, 
                                   regen = regen, 
                                   verbose = False
                                   )
    elif src_type == "custom":
        ###
        wpath = get_wpath(munit_name, munit_prop, "sfq_netlist")
        if munit_name == "ndroram":
            conn, bd = ndro_ram.gen_ndroram_netlist(addr_bw = ceil(log(munit_prop["param"]["NUM_DATA"], 2)), 
                                           data_bw = munit_prop["param"]["DATA_BW"],
                                           rsfqlib = rsfqlib,
                                           wpath = wpath, 
                                           dump = dump, 
                                           regen = regen
                                           )
        elif munit_name == "srmem":
            conn, bd = sr_mem.gen_srmem_netlist(num_data = munit_prop["param"]["NUM_DATA"], 
                                         rsfqlib = rsfqlib,
                                         wpath = wpath, 
                                         dump = dump, 
                                         regen = regen
                                         )
        elif munit_name == "sptree":
            conn, bd = sptree.gen_sptree_netlist(data_bw = munit_prop["param"]["DATA_BW"],
                    num_data = munit_prop["param"]["NUM_DATA"],
                    rsfqlib = rsfqlib)
        elif munit_name == "mgtree":
            conn, bd = mgtree.gen_mgtree_netlist(data_bw = munit_prop["param"]["DATA_BW"],
                    num_data = munit_prop["param"]["NUM_DATA"],
                    rsfqlib = rsfqlib)
        elif munit_name == "ndronw":
            conn, bd = ndro_nw.gen_ndronw_netlist(data_bw = munit_prop["param"]["DATA_BW"], rsfqlib = rsfqlib)
        elif munit_name == "ndrobuf":
            conn, bd = ndro_buf.gen_ndrobuf_netlist(data_bw=munit_prop["param"]["DATA_BW"], 
                    rsfqlib = rsfqlib)
        elif munit_name == "dffbuf":
            conn, bd = dff_buf.gen_dffbuf_netlist(data_bw=munit_prop["param"]["DATA_BW"], 
                    rsfqlib = rsfqlib)
        elif munit_name == "pe":
            conn, bd = pe.gen_pe_netlist(rsfqlib)
        else:
            raise Exception("gen_rsfq_netlist (custom) - does not suport munit_name: {}".format(munit_name))
    else:
        raise Exception("gen_rsfq_netlist - does not suport src_type: {}".format(src_type))

    return conn, bd

###
def gen_gate_rtl (vlg_src, munit_name, param_dict, rsfqlib, wpath, dump, regen):
    ###
    if not regen and os.path.exists(wpath): 
        gate_rtl_lines = open(wpath, "r").readlines()
    else:
        # check yosys installation
        exist_yosys = bool(cmdline("which yosys"))
        if not exist_yosys:
            raise Exception("gen_gate_rtl - Please install: yosys")

        # copy src verilog to temporary dir
        temp_src = os.path.join(temp_dir, "temp_{}.v".format(munit_name))
        cmdline("cp {} {}".format(vlg_src, temp_src))
        # set param (not covered by define.v)
        if param_dict:
            fill_param_line(temp_src, temp_src, param_dict)
        # run yosys
        temp_dst = os.path.join(temp_dir, "temp_synth_{}.v".format(munit_name))
        temp_ys = os.path.join(temp_dir, "temp_{}.ys".format(munit_name))

        ys = open(temp_ys, "w")
        line = "read_verilog {}\n".format(temp_src)
        line += "read_verilog -lib {}/{}.v\n".format(comm_dir, rsfqlib)
        line += "synth\n"
        line += "dfflibmap -liberty {}/{}.lib\n".format(comm_dir, rsfqlib)
        line += "abc -liberty {}/{}.lib\n".format(comm_dir, rsfqlib)
        line += "opt_clean\n"
        line += "write_verilog {}\n".format(temp_dst)
        ys.write(line)
        ys.close()

        cmdline("yosys {}".format(temp_ys))
        gate_rtl_lines = open(temp_dst, "r").readlines()

        ###
        if dump:
            cmdline("cp {} {}".format(temp_dst, wpath))
        else:
            pass
    
    return gate_rtl_lines

###
def opt_rsfq_netlist(munit_conn, munit_bd, rsfqlib, clk, wpath, dump, regen):

    wpath = wpath + "{}_".format(rsfqlib)
    plib_path = os.path.join(comm_dir, "{}.csv".format(rsfqlib))
    verbose = False
    return adjust_sfq_timing(munit_conn, munit_bd, plib_path, clk, wpath, dump, regen, verbose)


###
def get_rsfq_fpa(conn_opt, bd_opt, bd_clk, rsfqlib):
    gate_param = pd.read_csv(os.path.join(comm_dir, "{}.csv".format(rsfqlib))).set_index("Name")

    ### freq
    freq = 100 
    if conn_opt is not None:
        min_cct = conn_opt.iloc[0]["MinCCT"]
        if min_cct is not None:
            freq = round(1000/min_cct, 2) # GHz (cct's unit is ps)
        else:
            pass

    ### power & area
    p_stat = 0 # nW 
    e_dyn = 0 # nJ / Gacc
    area = 0 # um^2
    gc = 0 # gate_count
    jj = 0 # num_jj
    if bd_opt is not None:
        for gate in bd_opt.columns:
            gate_num = bd_opt[gate][0]
            gate_stat_p = gate_param.loc[gate, "PowerStatic"]
            gate_dyn_e = gate_param.loc[gate, "EnergyDynamic"]                                 
            gate_area = gate_param.loc[gate, "Area"]
            gate_jj = gate_param.loc[gate, "JJs"]
            p_stat += gate_num * gate_stat_p
            e_dyn += gate_num * gate_dyn_e                                               
            area += gate_num * gate_area
            if "ptl".upper() in gate.upper():
                continue
            else:
                gc += gate_num
                jj += gate_num * gate_jj

    if bd_clk is not None: 
        for gate in bd_clk.columns:
            gate_num = bd_clk[gate][0]
            gate_stat_p = gate_param.loc[gate, "PowerStatic"]
            gate_dyn_e = gate_param.loc[gate, "EnergyDynamic"]        
            gate_area = gate_param.loc[gate, "Area"]
            gate_jj = gate_param.loc[gate, "JJs"]
            p_stat += gate_num * gate_stat_p
            e_dyn += gate_num * gate_dyn_e                                               
            area += gate_num * gate_area
            if "ptl".upper() in gate.upper():
                continue
            else:
                gc += gate_num
                jj += gate_num * gate_jj

    e_dyn = round(e_dyn, 2)

    return freq, p_stat, e_dyn, area, gc, jj


def get_rsfq_latency(clk, conn_clk, conn_opt, munit_freq,munit_name, munit_prop, rsfqlib):
    gate_param = pd.read_csv(os.path.join(comm_dir, "{}.csv".format(rsfqlib))).set_index("Name")
    for gn, _ in gate_param.iterrows():
        if "splitt".upper() in gn.upper():
            sn = gn
        elif "merget".upper() in gn.upper():
            mn = gn

    src_type, scope_type = tuple(munit_prop["type"].split("_"))

    # latency
    latency = 0
    if src_type == "rtl" or (src_type == "custom" and munit_name in ["pe"]):
        assert conn_clk is not None and conn_opt is not None
        ## clock
        ## clock stem
        for col in conn_clk.columns:
            if "stem".upper() in col.upper():
                gn = col.replace('stem_', '')
                gc = sum(conn_clk[col])
                latency += gate_param.loc[gn, "Delay"]*gc
        ## final clock branch
        if clk == "concurrent":
            fin_clk = conn_clk.iloc[len(conn_clk)-1]
        elif clk == "counter":
            fin_clk = conn_clk.iloc[0]
        else: 
            raise Exception("get_rsfq_latency - does not support clocking scheme: {}".format(clk))

        for col, gc in fin_clk.items():
            if "br".upper() in col.upper():
                gn = col.replace('br_', '')
                latency += gate_param.loc[gn, "Delay"]*gc

        ## final gate
        out_depth = max(conn_opt["Depth"])
        out_df = conn_opt.loc[conn_opt["Depth"] == out_depth, :]

        max_gl = 0
        for _, out_r in out_df.iterrows():
            gn = out_r["A_type"]
            gl = gate_param.loc[gn, "Delay"]

            sc = out_r["A_depth_split"]
            sl = gate_param.loc[sn, "Delay"]

            max_gl = max(max_gl, sc*sl+gl)
        latency += max_gl
            
        ## CCTs
        max_depth = max(conn_opt["Depth"])-1
        latency += max_depth*round(1000/munit_freq, 2)
    elif src_type == "custom" and munit_name  in ["sptree", "mgtree"]:
        if munit_name == "sptree":
            num_data = munit_prop["param"]["NUM_DATA"]
            depth = ceil(log(num_data, 2))
            delay = gate_param.loc[sn, "Delay"]
            latency += depth*delay
        elif munit_name == "mgtree":
            num_data = munit_prop["param"]["NUM_DATA"]
            depth = ceil(log(num_data, 2))
            delay = gate_param.loc[mn, "Delay"]
            delay += min(gate_param.loc[mn, "A2BTime"], gate_param.loc[mn, "B2ATime"])
            latency += depth*delay
        else:
            pass
    
    else: 
        pass

    return latency


###
def get_fpa_entry(csv_path, num_lq, num_pch, code_dist):
    if os.path.exists(csv_path):
        fpa_df = pd.read_csv(csv_path)

        # format check
        col_format = ["NUM_LQ", "NUM_PCH", "CODE_DIST", "Frequency", "PowerStatic", "EnergyDynamic", "Area"]
        assert list(fpa_df.columns) == col_format, "get_fpa_entry - incorrect column format in {}: {}".format(csv_path, fpa_df.columns)
        
        # get entry
        filter_cond = ((fpa_df["NUM_LQ"] == "-") | (fpa_df["NUM_LQ"] == num_lq)) &\
                ((fpa_df["NUM_PCH"] == "-") | (fpa_df["NUM_PCH"] == num_pch)) &\
                      ((fpa_df["CODE_DIST"] == "-") | (fpa_df["CODE_DIST"] == code_dist))

        target_entry = fpa_df.loc[filter_cond, :]
        
        assert not target_entry.empty, "get_fpa_entry - no valid entry for (NUM_LQ, NUM_PCH, CODE_DIST) = ({}, {}, {}) in {}".format(num_lq, num_pch, code_dist, csv_path)
        freq = float(target_entry["Frequency"])
        p_stat = float(target_entry["PowerStatic"])
        e_dyn = float(target_entry["EnergyDynamic"])
        area = float(target_entry["Area"])

    else:
        raise Exception("get_fpa_entry - no fpa table {}".format(csv_path))

    return freq, p_stat, e_dyn, area
###

###
def get_wpath(munit_name, munit_prop, dir_name):
    src_type, scope_type = tuple(munit_prop["type"].split("_"))

    if src_type == "rtl":
        if scope_type == "unit":
            wdir = os.getcwd()
        elif scope_type == "common":
            wdir = comm_dir
        else:
            raise Exception("get_wpath - does not support scope_type: {}".format(scope_type))
    elif src_type == "custom":
        if scope_type == "common":
            wdir = comm_dir
        else:
            raise Exception("get_wpath - does not support scope_type: {}".format(scope_type))
    else:
        raise Exception("get_wpath - does not support src_type: {}".format(src_type))
    
    wddir = os.path.join(wdir, dir_name)
    if not os.path.exists(wddir):
        os.mkdir(wddir)
    wpath = os.path.join(wddir, munit_name) + "/"
    if not os.path.exists(wpath):
        os.mkdir(wpath)

    for mp_name, mp_val in munit_prop["param"].items():
        wpath += "{}_{}_".format(mp_name, mp_val)
    if dir_name == "gate_rtl":
        if not munit_prop["param"]:
            wpath = wpath+"g_rtl.v"
        else:
            wpath = wpath[:-1] + ".v"

    return wpath
###

###
def sync_freq_by_domain(estimator_stat):
    estimator_stat_300K_CMOS = [u for u in estimator_stat if (u.temp == "300K" and u.tech == "CMOS")] 
    estimator_stat_4K_CMOS = [u for u in estimator_stat if (u.temp == "4K" and u.tech == "CMOS")] 
    estimator_stat_4K_SFQ = [u for u in estimator_stat if (u.temp == "4K" and (u.tech == "RSFQ" or u.tech == "ERSFQ"))] 

    # Minimum frequency
    min_freq_300K_CMOS  = min([u.freq for u in estimator_stat_300K_CMOS], default=None)
    min_freq_4K_CMOS    = min([u.freq for u in estimator_stat_4K_CMOS], default=None)
    min_freq_4K_SFQ     = min([u.freq for u in estimator_stat_4K_SFQ], default=None)

    # Set frequency by domain-minimum-frequency
    for u in estimator_stat_300K_CMOS:
        u.p_dyn = round(u.p_dyn * (min_freq_300K_CMOS/u.freq), 3)
        u.freq = min_freq_300K_CMOS
    for u in estimator_stat_4K_CMOS:
        u.p_dyn = round(u.p_dyn * (min_freq_4K_CMOS/u.freq), 3)
        u.freq = min_freq_4K_CMOS
    for u in estimator_stat_4K_SFQ:
        u.p_dyn = round(u.p_dyn * (min_freq_4K_SFQ/u.freq), 3)
        u.freq = min_freq_4K_SFQ
    return 
###

###
def main(argv):
    config = FLAGS.config
    num_lq = FLAGS.num_lq

    if FLAGS.dump_synth == "True":
        dump_synth = True
    else:
        dump_synth = False
    if FLAGS.regen_synth == "True":
        regen_synth = True
    else:
        regen_synth = False

    if FLAGS.dump_est == "True":
        dump_est = True
    else:
        dump_est = False
    if FLAGS.regen_est == "True":
        regen_est = True
    else:
        regen_est = False

    estimator = xq_estimator()
    estimator.setup(config, num_lq, dump_synth, regen_synth, dump_est, regen_est)
    unit_stat_list = estimator.run()

    print("****** XQ-estimator Result - Frequency & Power estimation ******")
    show_estimator_result(unit_stat_list)

    return

if __name__ == "__main__":
    ### MAIN ### 
    # Define input arguments 
    ## arg_name, default_value, description
    FLAGS = flags.FLAGS
    flags.DEFINE_string("config", "example_cmos_d5", "target config name", short_name='c')
    flags.DEFINE_integer("num_lq", 5, "target number of logical qubits", short_name='q')
    flags.DEFINE_string("dump_synth",  "False", "dump synthesis results or not", short_name='ds')
    flags.DEFINE_string("regen_synth", "False", "re-generate synthesis results or not", short_name='rs')
    flags.DEFINE_string("dump_est", "False", "dump estimator's result or not", short_name='de')
    flags.DEFINE_string("regen_est", "False", "re-generate estimator's result or not", short_name='re')
    app.run(main)
