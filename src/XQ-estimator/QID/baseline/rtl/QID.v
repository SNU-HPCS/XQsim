`include "define.v"

module QID (
    rst, 
    clk,
    inst,
    instbuf_empty,
    qifdone,
    measfb_xorz,
    to_pdubuf_ready,
    to_lmubuf_ready,
    a_taken,
    to_pdubuf_dout,
    to_pdubuf_empty,
    to_lmubuf_dout,
    to_lmubuf_empty
);

parameter OPCODE_STIDX = (`INST_BW-1);
parameter MEASFLAGS_STIDX = (OPCODE_STIDX - `OPCODE_BW);
parameter MREGDST_STIDX = (MEASFLAGS_STIDX - `MEAS_FLAG_BW);
parameter LQIDXOFFSET_STIDX = (MREGDST_STIDX - `MREG_DST_BW);
parameter LPPLIST_STIDX = (LQIDXOFFSET_STIDX - `LQ_ADDR_OFFSET_BW);

input rst, clk;
input [`INST_BW-1:0] inst;
input instbuf_empty;
input qifdone;
input to_pdubuf_ready;
input to_lmubuf_ready;
input [1:0] measfb_xorz;
output a_taken;
output [`TO_PDUBUF_BW-1:0] to_pdubuf_dout;
output [`TO_LMUBUF_BW-1:0] to_lmubuf_dout;
output to_pdubuf_empty;
output to_lmubuf_empty;

/*** Wires ***/
// from qid_decoder
wire [`OPCODE_BW-1:0] temp_opcode;
wire [`OPCODE_BW-1:0] opcode;
wire [`MEAS_FLAG_BW-1:0] measflags;
wire [`LQADDR_BW-1:0] mregdst;
wire [`LQ_ADDR_OFFSET_BW-1:0] lqidx_offset;
wire [`TARGET_BW-1:0] lpplist;

// from qid_locator
wire [`NUM_LQ*`OPCODE_BW-1:0] opcode_loc;
wire [`NUM_LQ*`LQADDR_BW-1:0] mregdst_loc;
wire [`NUM_LQ*2-1:0] lpplist_loc;
wire [`NUM_LQ-1:0] lqlist_loc;

// from qid_ctrl
wire to_pdubuf_valid;
wire to_lmubuf_valid;
wire reg_stall;

// from registers
wire [`TO_PDUBUF_BW-1:0] to_pdubuf_din;
wire [`TO_LMUBUF_BW-1:0] to_lmubuf_din;

// from to_pdubuf
wire to_pdubuf_full;

// from to_lmubuf
wire to_lmubuf_full;

/*** Registers ***/
// accumulate output of locator
reg [`NUM_LQ*`OPCODE_BW-1:0] opcode_acc;
reg [`NUM_LQ*`LQADDR_BW-1:0] mregdst_acc;
reg [`NUM_LQ*2-1:0] lpplist_acc_pdu;
reg [`NUM_LQ*2-1:0] lpplist_acc_lmu;
reg [`NUM_LQ-1:0] lqlist_acc;
// transiently keep output of decoder
reg [`OPCODE_BW-1:0] opcode_reg;
reg [`MEAS_FLAG_BW-1:0] measflags_reg;
reg [`LQADDR_BW-1:0] mregdst_reg;
// for the last instruction
reg all_decoded;

/*** Wire connection ***/
assign to_pdubuf_din = {opcode_reg, lqlist_acc, lpplist_acc_pdu, opcode_acc, mregdst_acc};
assign to_lmubuf_din = {measflags_reg, lpplist_acc_lmu, mregdst_reg, to_pdubuf_valid};
assign temp_opcode = inst[OPCODE_STIDX -: `OPCODE_BW];
assign measflags = inst[MEASFLAGS_STIDX -: `MEAS_FLAG_BW];
assign mregdst = (inst[(MREGDST_STIDX-`MREG_DST_BW+`LQADDR_BW) -: `LQADDR_BW]);
assign lqidx_offset = inst[LQIDXOFFSET_STIDX -: `LQ_ADDR_OFFSET_BW];
assign lpplist = inst[LPPLIST_STIDX -: `TARGET_BW];

/*** Register update ***/
integer I;
reg pduacc_wren, lmuacc_wren;

always @(posedge clk)
begin
    if (rst)
    begin
        for (I = 0; I < `NUM_LQ; I = I+1)
            opcode_acc[I*`OPCODE_BW +: `OPCODE_BW] <= `INVALID_OPCODE;
        mregdst_acc <= 0;
        lpplist_acc_pdu <= 0;
        lpplist_acc_lmu <= 0;
        lqlist_acc <= 0;
        opcode_reg <= `INVALID_OPCODE;
        measflags_reg <= 0;
        mregdst_reg <= 0;
        all_decoded <= 0;
    end
    else
    begin
        // acc
        for (I = 0; I < `NUM_LQ; I = I+1)
        begin
            pduacc_wren = (lqlist_loc[I] | to_pdubuf_valid) & (~reg_stall);
            lmuacc_wren = (lqlist_loc[I] | to_pdubuf_valid | to_lmubuf_valid) & (~reg_stall);

            if (pduacc_wren)
            begin
                opcode_acc[I*`OPCODE_BW +: `OPCODE_BW] <= opcode_loc[I*`OPCODE_BW +: `OPCODE_BW];
                mregdst_acc[I*`LQADDR_BW +: `LQADDR_BW] <= mregdst_loc[I*`LQADDR_BW +: `LQADDR_BW];
                lpplist_acc_pdu[I*2 +: 2] <= lpplist_loc[I*2 +: 2];
                lqlist_acc[I] <= lqlist_loc[I];
            end

            if (lmuacc_wren)
            begin
                lpplist_acc_lmu[I*2 +: 2] <= lpplist_loc[I*2 +: 2];
            end
        end

        // reg
        if (~reg_stall)
        begin
            opcode_reg <= opcode;
            measflags_reg <= measflags;
            mregdst_reg <= mregdst;
        end

        // all_decoded
        if (instbuf_empty & qifdone)
            all_decoded <= 1;
    end
end


/*** Microunit instantiation ***/
// qid_decoder
qid_decoder UUT0(
    .temp_opcode(temp_opcode),
    .instbuf_empty(instbuf_empty),
    .measfb_xorz(measfb_xorz),
    .opcode(opcode),
    .a_taken(a_taken)
);

// qid_locator
qid_locator UUT1(
    .opcode(opcode), 
    .mregdst(mregdst), 
    .lqidx_offset(lqidx_offset), 
    .lpplist(lpplist), 
    .opcode_loc(opcode_loc), 
    .mregdst_loc(mregdst_loc),
    .lpplist_loc(lpplist_loc),
    .lqlist_loc(lqlist_loc)
);

// qid_ctrl
qid_ctrl UUT2(
    .opcode(opcode),
    .opcode_reg(opcode_reg),
    .mregdst(mregdst),
    .mregdst_reg(mregdst_reg),
    .instbuf_empty(instbuf_empty),
    .qifdone(qifdone),
    .all_decoded(all_decoded),
    .to_pdubuf_full(to_pdubuf_full),
    .to_lmubuf_full(to_lmubuf_full),
    .to_pdubuf_valid(to_pdubuf_valid),
    .to_lmubuf_valid(to_lmubuf_valid), 
    .reg_stall(reg_stall)
);

// to_pdubuf
fifo #(
    .ADDR_BW(`log2(`TO_PDUBUF_SZ)),
    .DATA_BW(`TO_PDUBUF_BW)
) UUT3(
    .rst(rst), 
    .clk(clk),
    .wr_din(to_pdubuf_valid), 
    .rd_dout(to_pdubuf_ready), 
    .din(to_pdubuf_din),
    .full(to_pdubuf_full), 
    .empty(to_pdubuf_empty),
    .dout(to_pdubuf_dout)
);

// to_lmubuf
fifo #(
    .ADDR_BW(`log2(`TO_LMUBUF_SZ)),
    .DATA_BW(`TO_LMUBUF_BW)
) UUT4(
    .rst(rst), 
    .clk(clk),
    .wr_din(to_lmubuf_valid), 
    .rd_dout(to_lmubuf_ready), 
    .din(to_lmubuf_din),
    .full(to_lmubuf_full), 
    .empty(to_lmubuf_empty),
    .dout(to_lmubuf_dout)   
);

endmodule
