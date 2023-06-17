
class srmem_double: 
    def __init__(self, srmem_name, num_rdport, len_mem): # NOTE: assume num_wrport = 1 
        # Parameter 
        self.srmem_name = srmem_name
        self.num_rdport = num_rdport 
        self.len_mem = len_mem
        # Wires
        ## Input wire
        self.input_valid = None
        self.input_data = None
        self.input_last_data = None
        self.input_pop = None
        self.input_new_data = None
        ## Intermediate wire
        self.flip_pchwr = None
        self.flip_pchrd = None
        ## Output wire 
        self.output_data = None
        self.output_wrfull = None
        self.output_rdvalid = None
        self.output_nextready = None
        self.output_rdlastinfo = None
        self.output_notempty =  None
        # Registers
        self.sel_pchwr = 0
        self.sel_pchrd = 0
        # Double-buffered srmem_single
        srmem_0 = srmem_single("{}_0".format(self.srmem_name), self.num_rdport, self.len_mem)
        srmem_1 = srmem_single("{}_1".format(self.srmem_name), self.num_rdport, self.len_mem)
        self.double_buffer = [srmem_0, srmem_1]

    def transfer(self):
        # connect input/output of two srmem_single
        ## write path
        wr_buffer = self.double_buffer[self.sel_pchwr]
        notwr_buffer = self.double_buffer[self.sel_pchwr^1]
        wr_buffer.input_valid = self.input_valid
        wr_buffer.input_data = self.input_data 
        wr_buffer.input_last_data = self.input_last_data
        notwr_buffer.input_valid = False
        notwr_buffer.input_data = None
        notwr_buffer.input_last_data = False
        ## read path
        rd_buffer = self.double_buffer[self.sel_pchrd]
        notrd_buffer = self.double_buffer[self.sel_pchrd^1]
        rd_buffer.input_pop = self.input_pop
        rd_buffer.input_new_data = self.input_new_data
        notrd_buffer.input_pop = False
        notrd_buffer.input_new_data = False
        ##
        self.double_buffer[0].transfer()
        self.double_buffer[1].transfer()
        ## output data
        self.output_data = self.double_buffer[self.sel_pchrd].output_data
        
        # flip_pchwr
        wr_buffer = self.double_buffer[self.sel_pchwr]
        if wr_buffer.state == "filling" and wr_buffer.next_state != "filling":
            self.flip_pchwr = True
        else:
            self.flip_pchwr = False
        
        # flip_pchrd
        rd_buffer = self.double_buffer[self.sel_pchrd]
        if rd_buffer.state == "reading" and rd_buffer.next_state == "filling":
            self.flip_pchrd = True
        else:
            self.flip_pchrd = False

        # output_wrfull
        self.output_wrfull = wr_buffer.output_wrfull
        # dutput_rdvalid
        self.output_rdvalid = rd_buffer.output_rdvalid
        # output_nextready 
        if self.flip_pchrd:
            self.output_nextready = self.double_buffer[self.sel_pchrd^1].output_rdvalid
        else:
            self.output_nextready = (rd_buffer.next_state == "reading")
        # output_rdlastinfo
        if rd_buffer.state == "reading":
            if self.len_mem == 1:
                self.output_rdlastinfo = True
            elif rd_buffer.next_state != "reading":
                self.output_rdlastinfo = True
            elif (rd_buffer.tlptr == rd_buffer.len_mem-1 and rd_buffer.input_pop) and (rd_buffer.hdptr == rd_buffer.tlptr):
                self.output_rdlastinfo = True
            else:
                self.output_rdlastinfo = False
        else:
            self.output_rdlastinfo = False
        # output_notempty
        self.output_notempty = rd_buffer.output_notempty or wr_buffer.output_notempty

        return


    def update(self):
        self.double_buffer[0].update()
        self.double_buffer[1].update()
        if self.flip_pchwr:
            self.sel_pchwr = self.sel_pchwr ^ 1
        if self.flip_pchrd:
            self.sel_pchrd = self.sel_pchrd ^ 1
        return


    def debug(self):
        print("{}.output_notempty: {}".format(self.srmem_name, self.output_notempty))
        print("{}.flip_pchwr: {}".format(self.srmem_name, self.flip_pchwr))
        print("{}.flip_pchrd: {}".format(self.srmem_name, self.flip_pchrd))
        print("{}.sel_pchwr: {}".format(self.srmem_name, self.sel_pchwr))
        print("{}.sel_pchrd: {}".format(self.srmem_name, self.sel_pchrd))
        print("{}.input_valid: {}".format(self.srmem_name, self.input_valid))
        print("{}.input_data: {}".format(self.srmem_name, self.input_data))
        print("{}.input_last_data: {}".format(self.srmem_name, self.input_last_data))
        print("{}.input_pop: {}".format(self.srmem_name, self.input_pop))
        print("{}.input_new_data: {}".format(self.srmem_name, self.input_new_data))
        print("{}.output_data: {}".format(self.srmem_name, self.output_data))
        print("{}.output_wrfull: {}".format(self.srmem_name, self.output_wrfull))
        print("{}.output_rdvalid: {}".format(self.srmem_name, self.output_rdvalid))
        self.double_buffer[0].debug()
        self.double_buffer[1].debug()
        print()
        return
  


class srmem_single:
    def __init__(self, srmem_name, num_rdport, len_mem): # NOTE: assume num_wrport = 1 
        # Parameter 
        self.srmem_name = srmem_name
        self.num_rdport = num_rdport
        self.len_mem = len_mem
        # Wires
        ## Input wire
        self.input_valid = None
        self.input_data = None
        self.input_last_data = None
        self.input_pop = None
        self.input_new_data = None
        ## Intermediate wire
        self.next_state = None
        self.next_data = None
        self.shift_en = None
        self.rst_hdptr = None
        self.rst_tlptr = None
        self.rst_memptr = None
        self.up_hdptr = None
        self.up_tlptr = None
        self.up_memptr = None
        self.rst_valid = None
        ## Output wire
        self.output_data = None
        self.output_wrfull = None
        self.output_rdvalid = None
        self.output_notempty = None

        # Registers
        ## Internal registers
        self.mem = []
        for i in range(self.num_rdport):
            self.mem.append([{'data': None, 'valid': False}]*self.len_mem)
        self.state = "filling"
        self.hdptr = 0
        self.tlptr = 0
        self.memptr = 0

    
    def transfer(self):
        if self.state == "filling":
            # next_state
            head_valid = False
            if self.input_last_data and self.input_valid:
                for i in range(self.num_rdport):
                    head = self.mem[i][self.len_mem-1]
                    if head['valid']:
                        head_valid = True
                        break
                
                if (self.hdptr == self.len_mem-1 and self.memptr == 0) or head_valid:
                    self.next_state = "reading"
                else:
                    self.next_state = "moving"
            else:
                self.next_state = "filling"
            # next_data
            self.next_data = [{'data':self.input_data, 'valid':self.input_valid}] * self.num_rdport
            # shift_en
            self.shift_en = []
            for i in range(self.num_rdport):
                if i == self.memptr:
                    self.shift_en.append(self.input_valid)
                else:
                    self.shift_en.append(False)
            # rst/up_hdptr 
            if self.input_valid and self.memptr == 0:
                self.up_hdptr = True
            else:
                self.up_hdptr = False
            self.rst_hdptr = False
            # rst/up_tlptr
            self.up_tlptr = False
            self.rst_tlptr = True
            # rst/up_memptr
            if self.input_valid:
                self.up_memptr = True
            else:
                self.up_memptr = False
            self.rst_memptr = False
            # rst_valid
            self.rst_valid = False

        elif self.state == "moving":
            # next_state
            if self.hdptr == self.len_mem-1:
                self.next_state = "reading"
            else:
                self.next_state = "moving"
            # next_data
            self.next_data = [{'data':None, 'valid':False}] * self.num_rdport
            # shift_en
            self.shift_en = [True] * self.num_rdport
            # rst/up_hdptr 
            self.up_hdptr = True
            self.rst_hdptr = False
            # rst/up_tlptr
            self.up_tlptr = True
            self.rst_tlptr = False
            # rst/up_memptr
            self.up_memptr = False
            self.rst_memptr = False
            # rst_valid
            self.rst_valid = False

        elif self.state == "reading":
            # next_state
            if self.tlptr == self.len_mem-1 and self.input_pop:
                if self.input_new_data: 
                    self.next_state = "filling"
                else:
                    if (self.hdptr == self.tlptr):
                        self.next_state = "reading"
                    else:
                        self.next_state = "moving"
            else:
                self.next_state = "reading"
            
            # next_data
            self.next_data = []
            for i in range(self.num_rdport):
                self.next_data.append(self.mem[i][self.len_mem-1])

            # shift_en
            self.shift_en = [self.input_pop] * self.num_rdport
            # rst/up_hdptr 
            if self.next_state == "filling":
                self.up_hdptr = False
                self.rst_hdptr = True
            else:
                if self.input_pop:
                    self.up_hdptr = True
                else:
                    self.up_hdptr = False
                self.rst_hdptr = False
            # rst/up_tlptr
            if self.input_pop:
                self.up_tlptr = True
            else:
                self.up_tlptr = False
            self.rst_tlptr = False
            # rst/up_memptr
            self.up_memptr = False
            self.rst_memptr = True
            # rst_valid
            if self.next_state == "filling":
                self.rst_valid = True
            else:
                self.rst_valid = False
        else:
            print("Invalid state in {}: {}".format(self.srmem_name, self.state))
            sys.exit()

        # output_data
        self.output_data = []
        for i in range(self.num_rdport):
            self.output_data.append(self.mem[i][self.len_mem-1])
        # output_wrfull
        self.output_wrfull = (self.state != "filling")
        # output_rdvalid
        self.output_rdvalid = (self.state == "reading")
        # output_notempty
        self.output_notempty = False
        for i in range(self.num_rdport):
            for j in range(self.len_mem):
                if self.mem[i][j]['valid']: 
                    self.output_notempty = True
                    break
            
        return


    def update(self):
        # mem
        ## rst_valid
        if self.rst_valid:
            for i in range(self.num_rdport):
                for j in range(self.len_mem):
                    self.mem[i][j]['valid'] = False
        ## shift_en
        else:
            for i in range(self.num_rdport):
                if self.shift_en[i]:
                    for j in range(self.len_mem-1, 0, -1):
                        self.mem[i][j] = self.mem[i][j-1]
                    self.mem[i][0] = self.next_data[i]
        # state
        self.state = self.next_state

        # hdptr
        if self.up_hdptr: 
            self.hdptr += 1
            if self.hdptr == self.len_mem:
                self.hdptr = 0
        if self.rst_hdptr:
            self.hdptr = 0

        # tlptr
        if self.up_tlptr: 
            self.tlptr += 1
            if self.tlptr == self.len_mem:
                self.tlptr = 0
        if self.rst_tlptr:
            self.tlptr = 0

        # memptr
        if self.up_memptr:
            self.memptr += 1
            if self.memptr == self.num_rdport:
                self.memptr = 0
        if self.rst_memptr:
            self.memptr = 0
        
        return

    def debug(self):
        print("{}.state: {}".format(self.srmem_name, self.state))
        print("{}.mem: {}".format(self.srmem_name, self.mem))
        print("{}.hdptr: {}".format(self.srmem_name, self.hdptr))
        print("{}.tlptr: {}".format(self.srmem_name, self.tlptr))
        print("{}.memptr: {}".format(self.srmem_name, self.memptr))
        print("{}.input_valid: {}".format(self.srmem_name, self.input_valid))
        print("{}.input_data: {}".format(self.srmem_name, self.input_data))
        print("{}.input_last_data: {}".format(self.srmem_name, self.input_last_data))
        print("{}.input_pop: {}".format(self.srmem_name, self.input_pop))
        print("{}.input_new_data: {}".format(self.srmem_name, self.input_new_data))
        print("{}.next_state: {}".format(self.srmem_name, self.next_state))
        print("{}.next_data: {}".format(self.srmem_name, self.next_data))
        print("{}.shift_en: {}".format(self.srmem_name, self.shift_en))
        print("{}.rst_hdptr: {}".format(self.srmem_name, self.rst_hdptr))
        print("{}.rst_tlptr: {}".format(self.srmem_name, self.rst_tlptr))
        print("{}.rst_memptr: {}".format(self.srmem_name, self.rst_memptr))
        print("{}.up_hdptr: {}".format(self.srmem_name, self.up_hdptr))
        print("{}.up_tlptr: {}".format(self.srmem_name, self.up_tlptr))
        print("{}.up_memptr: {}".format(self.srmem_name, self.up_memptr))
        print("{}.rst_valid: {}".format(self.srmem_name, self.rst_valid))
        print("{}.output_data: {}".format(self.srmem_name, self.output_data))
        print()
        return
