from queue import Queue

class buffer:
    def __init__(self, buf_name, buf_size):
        # Parameter
        self.buf_name = buf_name
        self.buf_size = buf_size
        # Wires
        ## Input wire
        self.input_data = None  # from prev_stage
        self.input_ready = None # from next_stage
        ## Output wire
        self.head = None        # to next_stage
        # Registers
        ## Output register
        self.full = False       # to prev_stage
        self.empty = True       # to next_stage
        # Included hardware unit
        self.buffer = Queue(maxsize=self.buf_size)
    
    # Intra-unit wire transfer
    def transfer(self):
        # Output wire
        if not self.empty:
            self.head = self.buffer.queue[0]
        else:
            self.head = None
        return

    # Sequential logic        
    def update(self):
        # full and empty define buffer's state
        if not self.full and (self.input_data is not None): 
            self.buffer.put(self.input_data)

        if not self.empty and self.input_ready:
            self.buffer.get()
        
        self.full = self.buffer.full()
        self.empty = self.buffer.empty()
        return

    def debug(self):
        print("{}.input_data: {}".format(self.buf_name, self.input_data))
        print("{}.input_ready: {}".format(self.buf_name, self.input_ready))
        print("{}.head: {}".format(self.buf_name, self.head))
        print("{}.full: {}".format(self.buf_name, self.full))
        print("{}.empty: {}".format(self.buf_name, self.empty))
        print("{}.length: {}".format(self.buf_name, self.buffer.qsize()))
        print("{}.buffer: {}".format(self.buf_name, self.buffer.queue))

        return
