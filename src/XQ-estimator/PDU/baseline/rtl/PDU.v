`include   "define.v"

module PDU (
    rst, 
    clk,
    reg_stall,
    to_pdubuf_dout,
    to_pdubuf_empty,
    pduout_valid,
    pduout_opcode, 
    pch_list,
    pchpp_list0,
    pchop_list0,
    pchmreg_list0,
    pchpp_list1,
    pchop_list1,
    pchmreg_list1
);

input rst, clk;
input reg_stall;
input [`TO_PDUBUF_BW-1:0] to_pdubuf_dout;
input to_pdubuf_empty;
output reg pduout_valid;
output reg [`OPCODE_BW-1:0] pduout_opcode;
output reg [`NUM_PCH-1:0] pch_list;
output reg [`NUM_PCH*2-1:0] pchpp_list0, pchpp_list1;
output reg [`NUM_PCH*`OPCODE_BW-1:0] pchop_list0, pchop_list1;
output reg [`NUM_PCH*`LQADDR_BW-1:0] pchmreg_list0, pchmreg_list1;


/*** Wires ***/
// from to_pdubuf_dout
wire [`OPCODE_BW-1:0] opcode;
wire [`NUM_LQ-1:0] lqlist;
wire [`NUM_LQ*2-1:0] lpplist;
wire [`NUM_LQ*`OPCODE_BW-1:0] oplist;
wire [`NUM_LQ*`LQADDR_BW-1:0] mreglist;
// from pdu_lqindexer
wire [`LQADDR_BW-1:0] lqidx;
wire [`NUM_LQ-1:0] next_lqlist;
// from pdu_pchmaptbl
wire [`PCHADDR_BW-1:0] rd_pchidx0, rd_pchidx1;
// from pdu_decoder
wire [`NUM_PCH-1:0] pch_list_curr;
wire [`NUM_PCH*2-1:0] pchpp_list_curr;
wire [`NUM_PCH*`OPCODE_BW-1:0] pchop_list_curr;
wire [`NUM_PCH*`LQADDR_BW-1:0] pchmreg_list_curr;
// from pdu_ctrl
wire is_lastlq;
wire is_evenlq;
wire take_in;
wire update_lqlist;
wire flush_out;
wire [1:0] next_state;


/*** Registers ***/
reg [`OPCODE_BW-1:0] opcode_reg;
reg [`NUM_LQ-1:0] lqlist_reg;
reg [`NUM_LQ*2-1:0] lpplist_reg;
reg [`NUM_LQ*`OPCODE_BW-1:0] oplist_reg;
reg [`NUM_LQ*`LQADDR_BW-1:0] mreglist_reg;
reg [1:0] state;

/*** Wire connection ***/
assign {opcode, lqlist, lpplist, oplist, mreglist} = to_pdubuf_dout;

/*** Register update ***/
integer I;

always @(posedge clk)
begin
    if (rst)
    begin
        opcode_reg <= `INVALID_OPCODE;
        lqlist_reg <= 0;
        lpplist_reg <= 0;
        oplist_reg <= {`NUM_LQ{`INVALID_OPCODE}};
        mreglist_reg <= 0;
        state <= `PDU_EMPTY;
        pduout_valid <= 0;
        pduout_opcode <= `INVALID_OPCODE;
        pch_list <= 0;
        pchpp_list0 <= 0;
        pchpp_list1 <= 0;
        pchop_list0 <= {(`NUM_PCH*`OPCODE_BW){1'b1}};
        pchop_list1 <= {(`NUM_PCH*`OPCODE_BW){1'b1}};
        pchmreg_list0 <= 0;
        pchmreg_list1 <= 0;
    end
    else if (~reg_stall)
    begin
        // state 
        state <= next_state;

        // input regs 
        if (take_in)
        begin
            opcode_reg <= opcode;
            lqlist_reg <= lqlist;
            lpplist_reg <= lpplist;
            oplist_reg <= oplist;
            mreglist_reg <= mreglist;
        end
        else if (update_lqlist)
        begin
            lqlist_reg <= next_lqlist;
        end

        // pduout_valid
        if (is_lastlq)
            pduout_valid <= 1;
        else
            pduout_valid <= 0;

        // pduout_opcode
        pduout_opcode <= opcode_reg;

        // output lists
        for (I = 0; I < `NUM_PCH; I = I+1)
        begin
            if (flush_out | pch_list_curr[I])
            begin
                pch_list[I] <= pch_list_curr[I];
                if (is_evenlq)
                begin
                    pchpp_list0[I*2 +: 2] <= pchpp_list_curr[I*2 +: 2];
                    pchop_list0[I*`OPCODE_BW +: `OPCODE_BW] <= pchop_list_curr[I*`OPCODE_BW +: `OPCODE_BW];
                    pchmreg_list0[I*`LQADDR_BW +: `LQADDR_BW] <= pchmreg_list_curr[I*`LQADDR_BW +: `LQADDR_BW];

                    pchpp_list1[I*2 +: 2] <= `PP_I;
                    pchop_list1[I*`OPCODE_BW +: `OPCODE_BW] <= `INVALID_OPCODE;
                    pchmreg_list1[I*`LQADDR_BW +: `LQADDR_BW] <= 1'b0;
                end
                else
                begin
                    pchpp_list1[I*2 +: 2] <= pchpp_list_curr[I*2 +: 2];
                    pchop_list1[I*`OPCODE_BW +: `OPCODE_BW] <= pchop_list_curr[I*`OPCODE_BW +: `OPCODE_BW];
                    pchmreg_list1[I*`LQADDR_BW +: `LQADDR_BW] <= pchmreg_list_curr[I*`LQADDR_BW +: `LQADDR_BW];

                    pchpp_list0[I*2 +: 2] <= `PP_I;
                    pchop_list0[I*`OPCODE_BW +: `OPCODE_BW] <= `INVALID_OPCODE;
                    pchmreg_list0[I*`LQADDR_BW +: `LQADDR_BW] <= 1'b0;
                end
            end
        end
    end
end


/*** Microunit instantiation ***/
pdu_ctrl UUT0(
    .state(state),
    .to_pdubuf_empty(to_pdubuf_empty),
    .lqidx(lqidx),
    .next_lqlist(next_lqlist),
    .is_lastlq(is_lastlq),
    .is_evenlq(is_evenlq),
    .take_in(take_in),
    .update_lqlist(update_lqlist),
    .flush_out(flush_out),
    .next_state(next_state)
);

pdu_lqindexer UUT1(
    .lqlist_reg(lqlist_reg),
    .lqidx(lqidx),
    .next_lqlist(next_lqlist)
);

pdu_pchmaptbl UUT2(
    .rst(rst),
    .clk(clk),
    .lqidx(lqidx),
    .rd_pchidx0(rd_pchidx0),
    .rd_pchidx1(rd_pchidx1)
);

pdu_decoder UUT3(
    .rd_pchidx0(rd_pchidx0),
    .rd_pchidx1(rd_pchidx1),
    .lqidx(lqidx),
    .lpplist_reg(lpplist_reg),
    .oplist_reg(oplist_reg),
    .mreglist_reg(mreglist_reg),
    .pch_list_curr(pch_list_curr),
    .pchpp_list_curr(pchpp_list_curr),
    .pchop_list_curr(pchop_list_curr),
    .pchmreg_list_curr(pchmreg_list_curr)
);

endmodule
