from math import *
#
from util import *

class sim_param:
    def __init__(self, config_filepath, isadef_filepath, num_lq):
        config = getJsonData(config_filepath)
        isa_def = getJsonData(isadef_filepath)
        
        self.name = config["name"]
        # Set parameters for the modeling and simulation
        self.arch_unit = config["arch_unit"]
        self.qb_plane = config["qubit_plane"]
        self.qb_plane["num_lq"] = num_lq

        ## ISA parameters
        self.opcode_def = {"{}_OPCODE".format(k):v for (k,v) in isa_def["inst"].items()}
        self.bf_def = isa_def["bit_format"]
        
        ## Bitwidth parameters
        self.bw_def = dict()
        inst_bw = 0
        for bf, prop in self.bf_def.items():
            self.bw_def[bf+"_bw"] = prop["len"]
            inst_bw += prop["len"]
        self.bw_def["inst_bw"] = inst_bw

        ## Gate latency
        self.g_ns = config["scale_constraint"]["gate_latency"]
        sim_freq = 1    # simulator assumes 1 cycle per 1 ns
        self.g_cyc = dict()
        for key, val in self.g_ns.items():
            self.g_cyc["{}_cycle".format(key.split('_')[0])] = ceil(val * sim_freq)

        ## Power budget
        self.power_budget_4k = config["scale_constraint"]["4K_power_budget"]

        ## 300Kto4K cale
        self.cable_heat_300kto4k = config["scale_constraint"]["digital_cable_heat"]

        ## RSFQ lib
        self.rsfqlib = "mitll_v2p1"

        ## Micro-architecture parameters
        self.set_qbp_param()
        self.set_bw_param()
        self.set_uarch_param()
        self.copy_param()


    def set_qbp_param(self):
        code_dist = self.qb_plane["code_dist"]
        num_lq = self.qb_plane["num_lq"]
        block_type = self.qb_plane["block_type"]

        #
        if block_type == "Distillation":
            num_pchrow = 3 
            if num_lq == 1:
                num_pchcol = 1 
            elif num_lq == 2:
                num_pchcol = 2 
            else:
                num_pchcol = ceil((num_lq-2)/2)+2
            
            num_pch = num_pchrow * num_pchcol

            if num_pchcol == 1:
                num_pch_eff = num_pch - 1
            elif num_pchcol in [2, 3]:
                num_pch_eff = num_pch - 2
            else:
                num_pch_eff = num_pch - 4
        else:
            raise Exception("sim_param - set_qbp_param: block_type {} is currently not supported".format(block_type))

        #
        num_ucrow = num_uccol = (code_dist+1) // 2
        num_uc = num_ucrow * num_uccol 
        num_qb_per_uc = 8
        num_pq = num_pch*num_uc*num_qb_per_uc
        num_pq_eff = num_pch_eff * num_uc * num_qb_per_uc
        num_aq = num_dq = int(num_pq/2)
        num_pchqb = num_uc * num_qb_per_uc
        num_pchaq = num_pchdq = int(num_pchqb/ 2)
        num_aqrow = num_dqrow = num_pchrow * num_ucrow * 2
        num_aqcol = num_dqcol = num_pchcol * num_uccol * 2

        #
        self.qb_plane["num_pchrow"] = num_pchrow
        self.qb_plane["num_pchcol"] = num_pchcol
        self.qb_plane["num_pch"] = num_pch
        self.qb_plane["num_ucrow"] = num_ucrow
        self.qb_plane["num_uccol"] = num_uccol
        self.qb_plane["num_uc"] = num_uc
        self.qb_plane["num_qb_per_uc"] = num_qb_per_uc
        self.qb_plane["num_pq"] = num_pq
        self.qb_plane["num_aq"] = num_aq
        self.qb_plane["num_dq"] = num_dq
        self.qb_plane["num_pchqb"] = num_pchqb
        self.qb_plane["num_pchaq"] = num_pchaq
        self.qb_plane["num_pchdq"] = num_pchdq
        self.qb_plane["num_aqrow"] = num_aqrow
        self.qb_plane["num_aqcol"] = num_aqcol
        self.qb_plane["num_dqrow"] = num_dqrow
        self.qb_plane["num_dqcol"] = num_dqcol
        self.qb_plane["num_pch_eff"] = num_pch_eff
        self.qb_plane["num_pq_eff"] = num_pq_eff

        return

    def set_bw_param(self):
        num_lq = self.qb_plane["num_lq"]
        num_pch = self.qb_plane["num_pch"]
        num_qb_per_uc = self.qb_plane["num_qb_per_uc"]
        num_uc = self.qb_plane["num_uc"]
        num_pq = self.qb_plane["num_pq"]
        num_pchqb = self.qb_plane["num_pchqb"]
        code_dist = self.qb_plane["code_dist"]
        opcode_bw = self.bw_def["opcode_bw"]
        meas_flag_bw = self.bw_def["meas_flag_bw"]
        # General
        lqaddr_bw = get_bitwidth(num_lq)
        pchaddr_bw = get_bitwidth(num_pch)
        qbaddr_bw = get_bitwidth(num_qb_per_uc)
        round_bw = get_bitwidth(code_dist)
        # QID
        to_pdubuf_bw = opcode_bw + num_lq * (opcode_bw + lqaddr_bw + 2 + 1)
        to_lmubuf_bw = meas_flag_bw + (num_lq * 2) + lqaddr_bw + 1
        qid2pdu_bw = to_pdubuf_bw + 1
        qid2lmu_bw = to_lmubuf_bw + 1
        # PDU
        pchmap_bw = 2 * pchaddr_bw
        pdu2piu_bw = opcode_bw + (num_pch)+ (2*num_pch)*2 + (opcode_bw*num_pch)*2 + (lqaddr_bw*num_pch)*2
        # PIU
        pchtype_bw = 4
        facebd_bw = 3
        cornerbd_bw = 3
        bdloc_bw = 3
        pchstat_bw = (pchtype_bw + 2*bdloc_bw) 
        pchdyn_bw = (4*facebd_bw + 4*cornerbd_bw)
        pchinfo_bw = (pchstat_bw + pchdyn_bw + pchaddr_bw + (2*opcode_bw) + (2*lqaddr_bw) + (2*2))
        piu2psu_bw = opcode_bw + pchinfo_bw
        piu2edu_bw = opcode_bw + pchinfo_bw
        piu2lmu_bw = opcode_bw + pchinfo_bw
        # PSU
        cwd_bw = 4
        idlen_bw = 5
        ucloc_bw = 8
        time_bw = 16
        maskgen_in_bw = (opcode_bw + idlen_bw + qbaddr_bw + ucloc_bw + pchtype_bw + pchdyn_bw)
        cntsrmem_bw = cwd_bw + 2*time_bw
        # EDU
        pibuf_bw = pchtype_bw + (4*facebd_bw)
        aqloc_bw = 5
        role_bw = 2
        possible_dir_bw = 6
        syndrome_bw = 2
        predec_bw = role_bw + possible_dir_bw + (2*syndrome_bw)
        # PFU
        cwdgen_in_bw = (1 + pchtype_bw + pchdyn_bw + opcode_bw + 1)
        # LMU
        instinfo_bw = to_lmubuf_bw-1
        pfmeas_mux_bw = 2*num_pchqb
        #
        self.bw_def["lqaddr_bw"] = lqaddr_bw
        self.bw_def["pchaddr_bw"] = pchaddr_bw
        self.bw_def["round_bw"] = round_bw
        self.bw_def["pchtype_bw"] = pchtype_bw
        self.bw_def["bdloc_bw"] = bdloc_bw
        self.bw_def["facebd_bw"] = facebd_bw
        self.bw_def["cornerbd_bw"] = cornerbd_bw

        self.bw_def["to_pdubuf_bw"] = to_pdubuf_bw 
        self.bw_def["to_lmubuf_bw"] = to_lmubuf_bw
        self.bw_def["pchmap_bw"] = pchmap_bw
        self.bw_def["pchstat_bw"] = pchstat_bw
        self.bw_def["pchdyn_bw"] = pchdyn_bw
        self.bw_def["pchinfo_bw"] = pchinfo_bw
        self.bw_def["cwd_bw"] = cwd_bw
        self.bw_def["time_bw"] = time_bw
        self.bw_def["idlen_bw"] = idlen_bw
        self.bw_def["ucloc_bw"] = ucloc_bw

        self.bw_def["maskgen_in_bw"] = maskgen_in_bw
        self.bw_def["cntsrmem_bw"] = cntsrmem_bw
        self.bw_def["pibuf_bw"] = pibuf_bw
        self.bw_def["aqloc_bw"] = aqloc_bw
        self.bw_def["predec_bw"] = predec_bw
        self.bw_def["instinfo_bw"] = instinfo_bw
        self.bw_def["pfmeas_mux_bw"] = pfmeas_mux_bw
        self.bw_def["qid2pdu_bw"] = qid2pdu_bw
        self.bw_def["qid2lmu_bw"] = qid2lmu_bw
        self.bw_def["pdu2piu_bw"] = pdu2piu_bw
        self.bw_def["piu2psu_bw"] = piu2psu_bw
        self.bw_def["piu2edu_bw"] = piu2edu_bw
        self.bw_def["piu2lmu_bw"] = piu2lmu_bw

        self.bw_def["cwdgen_in_bw"] = cwdgen_in_bw
        return
    

    def set_uarch_param(self):
        code_dist = self.qb_plane["code_dist"]
        num_pch = self.qb_plane["num_pch"]
        num_uc = self.qb_plane["num_uc"]
        num_qb_per_uc = self.qb_plane["num_qb_per_uc"]
        num_aq = self.qb_plane["num_aq"]
        num_pchaq = self.qb_plane["num_pchaq"]
        ##
        for unit_name, unit_cfg in self.arch_unit.items():
            uarch = unit_cfg["uarch"]
            if unit_name == "QIM":
                if uarch == "none":
                    unit_cfg["instbuf_sz"] = 20
                    unit_cfg["instmem_acc_cyc"] = 1
                else:
                    raise Exception("sim_param - set_uarch_param: Please first define {} microarchitecture for QIM".format(uarch))

            elif unit_name == "QID":
                if uarch == "baseline":
                    unit_cfg["to_pdubuf_sz"] = 16
                    unit_cfg["to_lmubuf_sz"] = 16
                else:
                    raise Exception("sim_param - set_uarch_param: Please first define {} microarchitecture for QID".format(uarch))

            elif unit_name == "PDU":
                if uarch == "baseline":
                    pass
                else:
                    raise Exception("sim_param - set_uarch_param: Please first define {} microarchitecture for PDU".format(uarch))

            elif unit_name == "PIU":
                if uarch == "baseline":
                    pass
                else:
                    raise Exception("sim_param - set_uarch_param: Please first define {} microarchitecture for PIU".format(uarch))

            elif unit_name == "PSU":
                if uarch in ["baseline", "maskshare"]:
                    # Heuristic: first assuming 1.5GHz PSU, 14ns SQ gate. For maskshare, parameters are adjusted by refine_psu_param later.
                    if code_dist < 5:
                        num_pcu = ceil(num_pch/3)
                        num_ucc = num_uc
                        num_qbctrl = ceil(num_qb_per_uc/8)
                    else:
                        num_pcu = ceil(num_pch/3)
                        num_ucc = ceil(num_uc/8)
                        num_qbctrl = num_qb_per_uc
                    unit_cfg["num_pcu"] = num_pcu
                    unit_cfg["num_ucc"] = num_ucc
                    unit_cfg["num_qbctrl"] = num_qbctrl
                    unit_cfg["num_mask"] = num_pcu * num_ucc * num_qbctrl
                    unit_cfg["num_pchdmx"] = num_pcu
                    unit_cfg["num_pchdmx_out"] = ceil(num_pch/num_pcu)
                    unit_cfg["num_pcuqb"] = num_ucc * num_qbctrl
                    unit_cfg["num_ucdmx"] = num_pch*num_ucc
                    unit_cfg["num_ucdmx_out"] = ceil(num_uc/num_ucc) 
                    unit_cfg["num_uccqb"] = num_qbctrl
                    unit_cfg["num_qbdmx"] = num_pch * num_uc * num_qbctrl
                    unit_cfg["num_qbdmx_out"] = ceil(num_qb_per_uc/num_qbctrl)               
                else:
                    raise Exception("sim_param - set_uarch_param: Please first define {} microarchitecture for PSU".format(uarch))

            elif unit_name == "TCU":
                if uarch in ["baseline", "simplebuf"]:
                    pass
                else:
                    raise Exception("sim_param - set_uarch_param: Please first define {} microarchitecture for TCU".format(uarch))

            elif unit_name == "QXU":
                if uarch == "none": 
                    pass
                else:
                    raise Exception("sim_param - set_uarch_param: Please first define {} microarchitecture for QXU".format(uarch))

            elif unit_name == "EDU":
                if uarch in ["baseline", "fast", "fastsliding"]:
                    unit_cfg["aqmeas_th"] = 3
                    unit_cfg["bd_delay"] = 3
                    unit_cfg["timeout_th"] = 2
                    unit_cfg["timeout_limit"] = unit_cfg["bd_delay"] + code_dist
                    if uarch == "baseline":
                        unit_cfg["num_educell"] = num_aq
                    elif uarch == "fast":
                        unit_cfg["num_educell"] = num_aq
                        unit_cfg["num_pe"] = num_pch
                    elif uarch == "fastsliding": 
                        unit_cfg["num_educell"] = (num_pchaq * 6)
                        unit_cfg["num_pe"] = 1                   
                else:
                    raise Exception("sim_param - set_uarch_param: Please first define {} microarchitecture for EDU".format(uarch))

            elif unit_name == "PFU":
                if uarch == "baseline":
                    pass
                else:
                    raise Exception("sim_param - set_uarch_param: Please first define {} microarchitecture for PFU".format(uarch))

            elif unit_name == "LMU":
                if uarch == "baseline":
                    unit_cfg["mobuf_sz"] = 16
                else:
                    raise Exception("sim_param - set_uarch_param: Please first define {} microarchitecture for LMU".format(uarch))

            else:
                raise Exception("set_uarch_param - Invalid unit_nmae; {}".format(unit_name))
        return
   

    def copy_param(self):
        # qbp
        self.num_lq = self.qb_plane["num_lq"]
        self.block_type = self.qb_plane["block_type"]
        self.code_dist = self.qb_plane["code_dist"]
        self.phy_err_rate = self.qb_plane["physical_error_rate"]
        self.num_pch = self.qb_plane["num_pch"]
        self.num_pchrow = self.qb_plane["num_pchrow"]
        self.num_pchcol = self.qb_plane["num_pchcol"]
        self.num_uc = self.qb_plane["num_uc"]
        self.num_ucrow = self.qb_plane["num_ucrow"]
        self.num_uccol = self.qb_plane["num_uccol"]
        self.num_qb_per_uc = self.qb_plane["num_qb_per_uc"]
        self.num_aqrow = self.qb_plane["num_aqrow"]
        self.num_aqcol = self.qb_plane["num_aqcol"]
        self.num_dqrow = self.qb_plane["num_dqrow"]
        self.num_dqcol = self.qb_plane["num_dqcol"]
        self.num_pch_eff = self.qb_plane["num_pch_eff"]
        self.num_pq = self.qb_plane["num_pq"]
        self.num_pq_eff = self.qb_plane["num_pq_eff"]
        self.num_pchaq = self.qb_plane["num_pchaq"]
        # bwdef
        self.inst_bw = self.bw_def["inst_bw"]
        self.opcode_bw = self.bw_def["opcode_bw"]
        self.meas_flag_bw = self.bw_def["meas_flag_bw"]
        self.mreg_dst_bw = self.bw_def["mreg_dst_bw"]
        self.lq_addr_offset_bw = self.bw_def["lq_addr_offset_bw"]
        self.target_bw = self.bw_def["target_bw"]
        self.cwd_bw = self.bw_def["cwd_bw"]
        ##
        self.qid2pdu_bw = self.bw_def["qid2pdu_bw"]
        self.qid2lmu_bw = self.bw_def["qid2lmu_bw"]
        self.pdu2piu_bw = self.bw_def["pdu2piu_bw"]
        self.piu2psu_bw = self.bw_def["piu2psu_bw"]
        self.piu2edu_bw = self.bw_def["piu2edu_bw"]
        self.piu2lmu_bw = self.bw_def["piu2lmu_bw"]

        # opcode
        self.LQI_opcode = format(self.opcode_def["LQI_OPCODE"], "0{}b".format(self.opcode_bw))
        self.LQM_X_opcode = format(self.opcode_def["LQM_X_OPCODE"], "0{}b".format(self.opcode_bw))
        self.LQM_Z_opcode = format(self.opcode_def["LQM_Z_OPCODE"], "0{}b".format(self.opcode_bw))
        self.RUN_ESM_opcode = format(self.opcode_def["RUN_ESM_OPCODE"], "0{}b".format(self.opcode_bw))
        self.INIT_INTMD_opcode = format(self.opcode_def["INIT_INTMD_OPCODE"], "0{}b".format(self.opcode_bw))
        self.MEAS_INTMD_opcode = format(self.opcode_def["MEAS_INTMD_OPCODE"], "0{}b".format(self.opcode_bw))
        self.SPLIT_INFO_opcode = format(self.opcode_def["SPLIT_INFO_OPCODE"], "0{}b".format(self.opcode_bw))
        self.PREP_INFO_opcode = format(self.opcode_def["PREP_INFO_OPCODE"], "0{}b".format(self.opcode_bw))
        self.MERGE_INFO_opcode = format(self.opcode_def["MERGE_INFO_OPCODE"], "0{}b".format(self.opcode_bw))
        self.PPM_INTERPRET_opcode = format(self.opcode_def["PPM_INTERPRET_OPCODE"], "0{}b".format(self.opcode_bw))
        self.LQM_FB_opcode = format(self.opcode_def["LQM_FB_OPCODE"], "0{}b".format(self.opcode_bw))
        self.LQM_Y_opcode = format(self.opcode_def["LQM_Y_OPCODE"], "0{}b".format(self.opcode_bw))
        # gate_ns
        self.sqgate_ns = self.g_ns["sqgate_ns"]
        self.tqgate_ns = self.g_ns["tqgate_ns"]
        self.meas_ns = self.g_ns["meas_ns"]
        # arch
        ### QIM
        qim_param = self.arch_unit["QIM"]
        self.instbuf_sz = qim_param["instbuf_sz"]
        self.instmem_acc_cyc = qim_param["instmem_acc_cyc"]
        ### QID
        qid_param = self.arch_unit["QID"]
        self.to_pdubuf_sz = qid_param["to_pdubuf_sz"]
        self.to_lmubuf_sz = qid_param["to_lmubuf_sz"]
        ### PDU
        ### PIU
        ### PSU
        psu_param = self.arch_unit["PSU"]
        self.num_pcu = psu_param["num_pcu"]
        self.num_ucc = psu_param["num_ucc"]
        self.num_qbctrl = psu_param["num_qbctrl"]
        self.num_mask = psu_param["num_mask"]
        ### TCU
        ### EDU
        edu_param =self.arch_unit["EDU"]
        self.bd_delay = edu_param["bd_delay"]
        self.aqmeas_th = edu_param["aqmeas_th"]
        self.timeout_limit = edu_param["timeout_limit"]
        ### PFU
        ### LMU

        return

    def refine_psu_param(self, target, freq=1):
        if target == "estimator":
            mask_per_cyc = self.sqgate_ns * freq
        elif target == "simulator":
            mask_per_cyc = self.sqgate_ns * 1 # simulation 1 cycle = 1 ns
        else:
            raise Exception("sim_param - refine_psu_param: target should be estimator or simulator")

        #
        if mask_per_cyc >= self.num_pch:
            num_pcu = 1
            mask_per_cyc = ceil(mask_per_cyc/self.num_pch)
            if mask_per_cyc >= self.num_uc:
                num_ucc = 1
                mask_per_cyc = ceil(mask_per_cyc/num_uc)
                if mask_per_cyc >= self.num_qb_per_uc:
                    num_qbctrl = 1
                else:
                    num_qbctrl = ceil(self.num_qb_per_uc/mask_per_cyc)
            else:
                num_ucc = ceil(self.num_uc/mask_per_cyc)
                num_qbctrl = self.num_qb_per_uc
        else:
            num_pcu = ceil(self.num_pch/mask_per_cyc)
            num_ucc = self.num_uc
            num_qbctrl = self.num_qb_per_uc
        
        #
        self.arch_unit["PSU"]["num_pcu"] = num_pcu
        self.arch_unit["PSU"]["num_ucc"] = num_ucc
        self.arch_unit["PSU"]["num_qbctrl"] = num_qbctrl
        self.arch_unit["PSU"]["num_mask"] = num_pcu * num_ucc * num_qbctrl
        self.arch_unit["PSU"]["num_pchdmx"] = num_pcu
        self.arch_unit["PSU"]["num_pchdmx_out"] = ceil(self.num_pch/num_pcu)
        self.arch_unit["PSU"]["num_pcuqb"] = num_ucc * num_qbctrl
        self.arch_unit["PSU"]["num_ucdmx"] = self.num_pch*num_ucc
        self.arch_unit["PSU"]["num_ucdmx_out"] = ceil(self.num_uc/num_ucc) 
        self.arch_unit["PSU"]["num_uccqb"] = num_qbctrl
        self.arch_unit["PSU"]["num_qbdmx"] = self.num_pch * self.num_uc * num_qbctrl
        self.arch_unit["PSU"]["num_qbdmx_out"] = ceil(self.num_qb_per_uc/num_qbctrl)                          
        # 
        self.copy_param()

        return 
