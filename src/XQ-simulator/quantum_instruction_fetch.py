from math import *
#
import buffer

#
class quantum_instruction_fetch: 
    def __init__(self, unit_stat, config, qbin_filepath):
        #
        self.config = config
        # 
        self.unit_stat = unit_stat
        self.init_stats()

        # Wires 
        ## Input wire
        self.input_instbuf_ready = None 
        ## Output wire
        self.output_inst = None
        self.output_instbuf_empty = None
        # Done signal
        self.all_fetched = False
        self.done = False

        # Microunits
        self.inst_mem = quantum_instruction_memory(config, qbin_filepath)
        self.pc_unit = pc_unit(config)
        self.inst_buf = buffer.buffer("inst_buf", config.instbuf_sz)

    def init_stats(self):
        # Data transfer
        ### to QID
        self.unit_stat.data_transfer["QID"] = {
                "num_eff": [],
                "num_max": [],
                "cycle": [],
                "bw": self.config.inst_bw,
                "last_cyc": 0
                }
        # 
        self.unit_stat.num_acc_cyc = 0
        self.unit_stat.num_update_cyc = 0
        return

    def update_stats(self, sim_cycle):
        self.unit_stat.num_update_cyc += 1
        # data_transfer 
        if self.input_instbuf_ready and not self.output_instbuf_empty:
            cycle = sim_cycle - self.unit_stat.data_transfer["QID"]["last_cyc"]
            self.unit_stat.data_transfer["QID"]["num_eff"].append(1)
            self.unit_stat.data_transfer["QID"]["num_max"].append(1)
            self.unit_stat.data_transfer["QID"]["cycle"].append(cycle)
            self.unit_stat.data_transfer["QID"]["last_cyc"] = sim_cycle
        else:
            pass
        
        if not self.all_fetched:
            self.unit_stat.num_acc_cyc += 1

        return

    def transfer(self):
        # inst_buf
        self.inst_buf.input_ready = self.input_instbuf_ready
        self.inst_buf.input_data = self.inst_mem.read_inst
        self.inst_buf.transfer()

        # inst_mem 
        self.inst_mem.input_instbuf_full = self.inst_buf.full
        self.inst_mem.input_stall = (self.inst_buf.full and self.inst_mem.read_inst)
        self.inst_mem.input_addr = self.pc_unit.pc

        # pc_unit
        self.pc_unit.input_memready = self.inst_mem.ready
        self.pc_unit.input_stall = (self.inst_buf.full and self.inst_mem.read_inst)

        # output
        self.output_inst = self.inst_buf.head
        self.output_instbuf_empty = self.inst_buf.empty

        # done
        if self.inst_mem.read_addr >= len(self.inst_mem.memory):    
            self.inst_mem.read_inst = None
            self.all_fetched = True
    
        if self.all_fetched and not self.output_instbuf_empty:
            self.done = True
        return 


    def update(self, sim_cycle=0):
        self.update_stats(sim_cycle)

        self.inst_buf.update()
        if not self.all_fetched:
            self.inst_mem.update()
            self.pc_unit.update()
        return

    def debug(self):
        print("qif.output_inst: {}".format(self.output_inst))
        self.inst_buf.debug()
        return 

class quantum_instruction_memory:
    def __init__(self, config, qbin_filepath):
        self.config = config
        # configeters
        self.qbin_filepath = qbin_filepath
        # Wires 
        ## Input wire 
        self.input_addr = None
        self.input_instbuf_full = None
        self.input_stall = None
        # Registers
        ## Input register 
        self.read_addr = 0
        ## Output register
        self.read_inst = None
        ## State register
        self.read_counter = 0
        self.ready = True

        # Initialization 
        self.memory = []
        self.load_binary()

    def transfer(self):
        pass

    def update(self):
        # Stall
        if self.input_stall: 
            return 

        # Normal operation
        if not self.input_instbuf_full and self.read_inst:
            self.read_inst = None

        ### Idle
        if self.ready:
            self.read_addr = self.input_addr
            self.read_counter = 0
            self.ready = False
        ### Running
        else:
            self.read_counter += 1
        
        if self.read_counter == (self.config.instmem_acc_cyc-1):
            inst_byte = ceil(self.config.inst_bw/8)
            self.read_inst = self.memory[self.read_addr:self.read_addr+inst_byte]
            self.ready = True
        return

    def debug(self):
        # Add variables to check in the debugging mode
        pass

    def load_binary(self):
        with open(self.qbin_filepath, "rb") as qbin:
            byte = qbin.read(1)
            count = 0
            test = ""
            while byte != b"":
                self.memory.append(byte)
                bstr = format(int.from_bytes(byte, byteorder="big"), "08b")
                byte = qbin.read(1)
        return


class pc_unit:
    def __init__(self, config):
        # configeter
        self.inst_byte = ceil(config.inst_bw/8)
        # Wires
        ## Input wire
        self.input_memready = None
        self.input_stall = None
        # Registers
        ## Output register
        self.pc = 0
        ## State register
        self.default_nextpc = self.pc + self.inst_byte
    
    # Sequential logic        
    def update(self):
        # Stall
        if self.input_stall:
            return 
        # Normal operation
        ### Set nextpc (Currently just pc+inst_byte)
        if self.input_memready:
            self.pc = self.default_nextpc
            self.default_nextpc = self.pc + self.inst_byte
        else:
            pass
        return

    def debug(self):
        return
