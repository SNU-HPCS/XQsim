class unit_stat_est:
    def __init__(self, 
                 name, 
                 uarch,
                 temp,
                 tech,
                 freq,
                 p_stat,
                 p_dyn,
                 area,
                 munit_df
                 ):
        self.name = name
        self.uarch = uarch
        self.temp = temp
        self.tech = tech
        self.freq = freq
        self.p_stat = p_stat
        self.p_dyn = p_dyn
        self.area = area
        self.munit_df = munit_df
        #
        self.psu_inst_bw = None # PSU
        self.edu_cycle_param = None # EDU


class unit_stat_sim:
    def __init__(self, name, uarch):
        self.name = name
        self.uarch = uarch
        #
        self.num_acc_cyc = 0
        self.num_update_cyc = 0
        self.data_transfer = dict()
        self.edu_cycle_result = None # EDU
        self.bw_req = None # TCU
