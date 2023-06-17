//`include "../define.v"
`include "define.v"

module qid_locator(
    opcode, 
    mregdst, 
    lqidx_offset, 
    lpplist, 
    opcode_loc, 
    mregdst_loc,
    lpplist_loc,
    lqlist_loc
);

parameter LPPLIST_LEN = (`TARGET_BW/2);

input [`OPCODE_BW-1:0] opcode;
input [`LQADDR_BW-1:0] mregdst;
input [`LQ_ADDR_OFFSET_BW-1:0] lqidx_offset;
input [`TARGET_BW-1:0] lpplist;
output reg [`NUM_LQ*`OPCODE_BW-1:0] opcode_loc;
output reg [`NUM_LQ*`LQADDR_BW-1:0] mregdst_loc;
output reg [`NUM_LQ*2-1:0] lpplist_loc;
output reg [`NUM_LQ-1:0] lqlist_loc;

reg [1:0] lpp;
integer I, LQIDX_OFFSET;
wire signed [`LQ_ADDR_OFFSET_BW:0] lqidx_offset_s = $signed({1'b0, lqidx_offset});

always @(*)
begin
    lpplist_loc = 0;
    lqlist_loc = 0;
    opcode_loc = {`OPCODE_BW{1'b1}}; 
    mregdst_loc = 0;
    LQIDX_OFFSET = lqidx_offset_s * LPPLIST_LEN;
    for (I = 0; I < LPPLIST_LEN; I = I+1)
    begin
        lpp = lpplist[I*2 +: 2];

        lpplist_loc[2*(I+LQIDX_OFFSET) +: 2] = lpp;
        if (lpp != `PP_I)
        begin
            lqlist_loc[(I+LQIDX_OFFSET)] = 1;
            opcode_loc[(I+LQIDX_OFFSET)*`OPCODE_BW +: `OPCODE_BW] = opcode;
            mregdst_loc[(I+LQIDX_OFFSET)*`LQADDR_BW +: `LQADDR_BW] = mregdst;
        end
        else
        begin
            lqlist_loc[(I+LQIDX_OFFSET)] = 0;
            opcode_loc[(I+LQIDX_OFFSET)*`OPCODE_BW +: `OPCODE_BW] = `INVALID_OPCODE;
            mregdst_loc[(I+LQIDX_OFFSET)*`LQADDR_BW +: `LQADDR_BW] = 0;
        end
    end
end

endmodule
