`include "define.v"

module TCU(
    rst, 
    clk, 
    psu_valid,
    opcode_in,
    timing_in,
    cwdarray_in,
    timebuf_full,
    timebuf_empty,
    tcu_valid,
    opcode_out,
    cwdarray_out
);

input rst;
input clk;
input psu_valid;
input [`OPCODE_BW-1:0] opcode_in;
input [`TIME_BW-1:0] timing_in;
input [`NUM_PQ*`CWD_BW-1:0] cwdarray_in;
output timebuf_full;
output timebuf_empty;
output tcu_valid;
output [`OPCODE_BW-1:0] opcode_out;
output [`NUM_PQ*`CWD_BW-1:0] cwdarray_out;

/*** Wires ***/
wire timing_match;
wire [`TIME_BW-1:0] timing_out;
wire next_wrptr, next_rdptr;
wire [1:0] next_numitem;
wire buffer_wren;
wire buffer_rden;

/*** Registers ***/
reg wr_ptr, rd_ptr;
reg [1:0] num_item;
reg [`TIME_BW-1:0] timer;

/*** Wire connection ***/
assign timing_match = (timer == 1);
assign tcu_valid = timing_match && (~timebuf_empty);

/*** Register update ***/ 
always @(posedge clk)
begin
    if (rst)
    begin
        rd_ptr <= 0;
        wr_ptr <= 0;
        num_item <= 0;
        timer <= 1;
    end
    else
    begin
        rd_ptr <= next_rdptr;
        wr_ptr <= next_wrptr;
        num_item <= next_numitem;
        if (tcu_valid)
            timer <= timing_out;
        else if (~timing_match)
            timer <= timer-1;
    end
end


/*** Microunit instantiation ***/
// buffer_ctrl
buffer_ctrl #(
    .ADDR_BW(1)
) UUT0(
    .wr_din(psu_valid), 
    .rd_dout(timing_match), 
    .wr_ptr(wr_ptr), 
    .rd_ptr(rd_ptr),
    .num_item(num_item), 
    .next_wrptr(next_wrptr), 
    .next_rdptr(next_rdptr), 
    .next_numitem(next_numitem), 
    .reg_push(buffer_wren), 
    .reg_pop(buffer_rden),
    .full(timebuf_full), 
    .empty(timebuf_empty)
);

// opcode_buf 
buffer #(
    .ADDR_BW(1),
    .DATA_BW(`OPCODE_BW)
) UUT1(
    .rst(rst),
    .clk(clk),
    .wr_en(buffer_wren),
    .rd_en(~timebuf_empty),
    .wr_ptr(wr_ptr),
    .rd_ptr(rd_ptr),
    .din(opcode_in),
    .dout(opcode_out)
);

// timing_buf
buffer #(
    .ADDR_BW(1),
    .DATA_BW(`TIME_BW)
) UUT2(
    .rst(rst),
    .clk(clk),
    .wr_en(buffer_wren),
    .rd_en(~timebuf_empty),
    .wr_ptr(wr_ptr),
    .rd_ptr(rd_ptr),
    .din(timing_in),
    .dout(timing_out)
);

genvar i;
generate
    for (i = 0; i < `NUM_PQ; i = i+1)
    begin: gen_cwdbuf
        buffer #(
            .ADDR_BW(1),
            .DATA_BW(`CWD_BW)
        ) UUT3_I(
            .rst(rst), 
            .clk(clk),
            .wr_en(buffer_wren),
            .rd_en(~timebuf_empty),
            .wr_ptr(wr_ptr),
            .rd_ptr(rd_ptr),
            .din(cwdarray_in[i*`CWD_BW +: `CWD_BW]),
            .dout(cwdarray_out[i*`CWD_BW +: `CWD_BW])
        );
    end
endgenerate


endmodule
