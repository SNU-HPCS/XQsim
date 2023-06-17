import os, sys 
#
curr_path = os.path.abspath(__file__)
curr_dir = os.path.dirname(curr_path)
par_dir = os.path.join(curr_dir, os.pardir)
#
sys.path.insert(0, par_dir)
from util import *
import buffer as buffer
#
import numpy as np

class time_control_unit:
    def __init__(self, unit_stat, config):
        #
        self.config = config
        #
        self.unit_stat = unit_stat
        self.init_stats()
        # Wires
        ## Input wire
        self.input_valid = None
        self.input_opcode = None
        self.input_timing = None
        self.input_cwdarray = None
        ## Intermediate wire
        self.timing_match = None
        ## Output wire
        ### from timing_buf
        self.output_timebuf_full = None
        self.output_timebuf_empty = None
        ### from cwdbuf_array
        self.output_cwdarray = None
        ### from opcode_buf
        self.output_opcode = None
        ### from control
        self.output_valid = None

        # Registers
        ## Internal register
        self.timer = 1
        self.timer_val = 1

        # Buffers
        self.timing_buf = buffer.buffer("timing_buf", 2)
        self.opcode_buf = buffer.buffer("opcode_buf", 2)
        self.cwdbuf_array = np.empty((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, self.config.num_qb_per_uc),dtype=object)
        for (i, j, k, l, m), _ in np.ndenumerate(self.cwdbuf_array):
            self.cwdbuf_array[i][j][k][l][m] = buffer.buffer("cwdbuf_{}".format((i, j, k, l, m)), 2)
        self.cycle = 0
    
    def transfer(self):
        # timing_match
        self.timing_match = (self.timer == 1)

        # buffer inputs
        ## input_data
        if self.input_valid:
            self.timing_buf.input_data = self.input_timing
            self.opcode_buf.input_data = self.input_opcode
            for (i, j, k, l, m), cwdbuf in np.ndenumerate(self.cwdbuf_array):
                cwdbuf.input_data = self.input_cwdarray[i][j][k][l][m]
        else:
            self.timing_buf.input_data = None
            self.opcode_buf.input_data = None
            for (i, j, k, l, m), cwdbuf in np.ndenumerate(self.cwdbuf_array):
                cwdbuf.input_data = None
        ## input_ready
        self.timing_buf.input_ready = self.timing_match
        self.opcode_buf.input_ready = self.timing_match
        for (i, j, k, l, m), cwdbuf in np.ndenumerate(self.cwdbuf_array):
            cwdbuf.input_ready = self.timing_match

        # buffer transfer
        self.timing_buf.transfer()
        self.opcode_buf.transfer()
        for _, cwdbuf in np.ndenumerate(self.cwdbuf_array):
            cwdbuf.transfer()

        # output
        ## output_timebuf_full/empty
        self.output_timebuf_full = self.timing_buf.full
        self.output_timebuf_empty = self.timing_buf.empty
        ## output_valid
        self.output_valid = self.timing_match and (not self.timing_buf.empty)
        ## output_opcode
        self.output_opcode = self.opcode_buf.head
        ## output_cwdarray
        self.output_cwdarray = np.empty((self.config.num_pchrow, self.config.num_pchcol, self.config.num_ucrow, self.config.num_uccol, self.config.num_qb_per_uc), dtype='U8')
        for (i, j, k, l, m), cwdbuf in np.ndenumerate(self.cwdbuf_array):
            self.output_cwdarray[i][j][k][l][m] = cwdbuf.head
        return


    def update(self, sim_cycle=0):
        self.update_stats(sim_cycle)

        # timer
        if self.output_valid:
            self.timer = self.timing_buf.head
            self.timer_val = self.timing_buf.head
        elif not self.timing_match:
            self.timer -= 1
        else: # not valid but timing_match
            pass

        # buffers
        self.timing_buf.update()
        self.opcode_buf.update()
        for _, cwdbuf in np.ndenumerate(self.cwdbuf_array):
            cwdbuf.update()
        return


    # Debug
    def debug(self):
        # Add variables to check in the debugging mode
        if self.output_valid:
            print("tcu.output_cwdarray:")
            debug_array(self.config, self.output_cwdarray)
        return

    def init_stats (self):
        # Data transfer
        ### to QXU
        self.unit_stat.data_transfer["QXU"] = {
                "num_eff": [], 
                "num_max": [], 
                "cycle": [],
                "bw": self.config.cwd_bw,
                "last_cyc": 0
                }
        self.unit_stat.bw_req = {
                "cycle": [], 
                "bit_max": [],
                "bit_eff": []
                }
        #
        self.unit_stat.num_acc_cyc = 0
        self.unit_stat.num_update_cyc = 0
        return
    
    def update_stats (self, sim_cycle):
        self.unit_stat.num_update_cyc += 1 
        # num_acc_cyc
        if self.timer == 1 and not self.timing_buf.empty: 
            self.unit_stat.num_acc_cyc += 1 # Read
        elif self.input_valid and not self.timing_buf.full: 
            self.unit_stat.num_acc_cyc += 1 # Write
        else:
            pass
        # data_transfer
        if self.output_valid:
            cycle = sim_cycle - self.unit_stat.data_transfer["QXU"]["last_cyc"]
            self.unit_stat.data_transfer["QXU"]["num_max"].append(self.config.num_pq_eff)
            #
            num_scheduled_cwd = 0
            for _, op in np.ndenumerate(self.output_cwdarray):
                if len(op) != 0:
                    num_scheduled_cwd += 1
                else:
                    pass
            self.unit_stat.data_transfer["QXU"]["num_eff"].append(num_scheduled_cwd)
            #
            self.unit_stat.data_transfer["QXU"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["QXU"]["last_cyc"] = sim_cycle
        else:
            pass
        # inst_bw_req 
        if self.output_valid:
            if self.timer_val == 1: 
                pass
            else:
                time = self.timer_val
                bit_eff = num_scheduled_cwd * self.config.cwd_bw
                bit_max = self.config.num_pq_eff * self.config.cwd_bw
                self.unit_stat.bw_req["cycle"].append(time)
                self.unit_stat.bw_req["bit_max"].append(bit_max)
                self.unit_stat.bw_req["bit_eff"].append(bit_eff)
        else:
            pass
        return
