`include "define.v"

module pdu_decoder(
    rd_pchidx0,
    rd_pchidx1,
    lqidx,
    lpplist_reg,
    oplist_reg,
    mreglist_reg,
    pch_list_curr,
    pchpp_list_curr,
    pchop_list_curr,
    pchmreg_list_curr
);

input [`PCHADDR_BW-1:0] rd_pchidx0, rd_pchidx1;
input [`LQADDR_BW-1:0] lqidx;
input [`NUM_LQ*2-1:0] lpplist_reg;
input [`NUM_LQ*`OPCODE_BW-1:0] oplist_reg;
input [`NUM_LQ*`LQADDR_BW-1:0] mreglist_reg;
output reg [`NUM_PCH-1:0] pch_list_curr;
output reg [`NUM_PCH*2-1:0] pchpp_list_curr;
output reg [`NUM_PCH*`OPCODE_BW-1:0] pchop_list_curr;
output reg [`NUM_PCH*`LQADDR_BW-1:0] pchmreg_list_curr;

/*** Wires ***/
reg [1:0] lpp;
reg [`OPCODE_BW-1:0] op;
reg [`LQADDR_BW-1:0] mreg;
wire signed [`LQADDR_BW:0] lqidx_s = $signed({1'b0, lqidx});
wire signed [`PCHADDR_BW:0] rd_pchidx0_s = $signed({1'b0, rd_pchidx0});
wire signed [`PCHADDR_BW:0] rd_pchidx1_s = $signed({1'b0, rd_pchidx1});

/*** Combinational logic ***/
integer I;
always @(*)
begin
    // generate pch_list_curr
    for (I = 0; I < `NUM_PCH; I = I+1)
    begin
        if (I == rd_pchidx0_s | I == rd_pchidx1_s)
            pch_list_curr[I] = 1;
        else
            pch_list_curr[I] = 0;
    end

    // mux lpp, op, mreg
    lpp = lpplist_reg[lqidx_s*2 +: 2];
    op = oplist_reg[lqidx_s*`OPCODE_BW +: `OPCODE_BW];
    mreg = mreglist_reg[lqidx_s*`LQADDR_BW +: `LQADDR_BW];

    // generate pchpp/op/mreg_list_curr
    for (I = 0; I < `NUM_PCH; I = I+1)
    begin
        if (pch_list_curr[I])
        begin
            pchpp_list_curr[I*2 +: 2] = lpp;
            pchop_list_curr[I*`OPCODE_BW +: `OPCODE_BW] = op;
            pchmreg_list_curr[I*`LQADDR_BW +: `LQADDR_BW] = mreg;
        end
        else
        begin
            pchpp_list_curr[I*2 +: 2] = 0;
            pchop_list_curr[I*`OPCODE_BW +: `OPCODE_BW] = `INVALID_OPCODE;
            pchmreg_list_curr[I*`LQADDR_BW +: `LQADDR_BW] = 0;
        end
    end
end



endmodule
