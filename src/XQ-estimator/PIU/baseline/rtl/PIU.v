`include "define.v"

module PIU (
    rst,
    clk,
    reg_stall,
    pdu_valid,
    opcode,
    pch_list,
    pchpp_list0,
    pchpp_list1,
    pchop_list0,
    pchop_list1,
    pchmreg_list0,
    pchmreg_list1,
    pchinfo_out,
    opcode_out,
    topsu_valid_out,
    tolmu_valid_out,
    last_pchinfo_out
);

input rst, clk, reg_stall;
input pdu_valid;
input [`OPCODE_BW-1:0] opcode;
input [`NUM_PCH-1:0] pch_list;
input [`NUM_PCH*2-1:0] pchpp_list0, pchpp_list1;
input [`NUM_PCH*`OPCODE_BW-1:0] pchop_list0, pchop_list1;
input [`NUM_PCH*`LQADDR_BW-1:0] pchmreg_list0, pchmreg_list1;

output [`PCHINFO_BW-1:0] pchinfo_out;
output [`OPCODE_BW-1:0] opcode_out;
output topsu_valid_out;
output tolmu_valid_out;
output last_pchinfo_out;


/*** Wires ***/
// from piu_ctrl
wire take_in;
wire update_pchidxsrc;
wire [1:0] sel_pchidxsrc;
wire [1:0] next_state;
wire is_writing;
wire prep_dyninfo;
wire split_dyninfo;
wire set_merged;
wire copy_merged;
wire pchlist_wren;
wire esmon_wren;
wire mgdreg_wren;
wire mgdmem_wren;
wire topsu_valid;
wire tolmu_valid;
wire last_pchinfo;

// from piu_pchindexer
wire [`PCHADDR_BW-1:0] pchidx;
wire [`NUM_PCH-1:0] next_pchidxsrc;
// from piu_nextsrc
wire [`NUM_PCH-1:0] next_pchlist;
wire [`NUM_PCH-1:0] next_esmon;
wire [`NUM_PCH-1:0] next_merged;
// from piu_static_rom 
wire [`PCHSTAT_BW-1:0] pchinfo_static;
wire [`PCHTYPE_BW-1:0] pchtype;
// from piu_dynamic_ram
wire [`PCHDYN_BW-1:0] pchinfo_dynamic;
// from piu_dyndecoder
wire [4*`FACEBD_BW-1:0] wr_facebd;
wire [4*`CORNERBD_BW-1:0] wr_cornerbd;
// from piu_pchinfo
wire [2*(`OPCODE_BW+`LQADDR_BW+2)-1:0] pchinfo_etc;


/*** Registers ***/
reg [1:0] state;
reg [`OPCODE_BW-1:0] opcode_reg;
reg [`NUM_PCH-1:0] pch_list_reg;
reg [`NUM_PCH-1:0] esmon_reg;
reg [`NUM_PCH-1:0] merged_reg;
reg [`NUM_PCH-1:0] merged_mem;
reg [`NUM_PCH*2-1:0] pchpp_list_reg0, pchpp_list_reg1;
reg [`NUM_PCH*`OPCODE_BW-1:0] pchop_list_reg0, pchop_list_reg1;
reg [`NUM_PCH*`LQADDR_BW-1:0] pchmreg_list_reg0, pchmreg_list_reg1;
//
reg [`PCHADDR_BW-1:0] pchidx_reg;
reg topsu_valid_reg;
reg tolmu_valid_reg;
reg last_pchinfo_reg;
reg is_writing_reg;
reg [`OPCODE_BW-1:0] opcode_reg_reg;
reg [`NUM_PCH*2-1:0] pchpp_list_reg0_reg, pchpp_list_reg1_reg;
reg [`NUM_PCH*`OPCODE_BW-1:0] pchop_list_reg0_reg, pchop_list_reg1_reg;
reg [`NUM_PCH*`LQADDR_BW-1:0] pchmreg_list_reg0_reg, pchmreg_list_reg1_reg;


/*** Wire connection ***/
assign pchtype = pchinfo_static[`PCHSTAT_BW-1 -: `PCHTYPE_BW];
assign pchinfo_out = {pchinfo_static, pchinfo_dynamic, pchidx_reg, pchinfo_etc};
//
assign topsu_valid_out = topsu_valid_reg;
assign tolmu_valid_out = tolmu_valid_reg;
assign last_pchinfo_out = last_pchinfo_reg;
assign opcode_out = opcode_reg_reg; 

/*** Register update ***/
integer I;
always @(posedge clk)
begin
    if (rst)
    begin
        state <= `PIU_READY;
        opcode_reg <= `INVALID_OPCODE;
        pch_list_reg <= 0;
        esmon_reg <= 0;
        merged_reg <= 0;
        merged_mem <= 0;
        pchpp_list_reg0 <= 0;
        pchpp_list_reg1 <= 0;
        for (I = 0; I < `NUM_PCH; I = I+1)
        begin
            pchop_list_reg0[I*`OPCODE_BW +: `OPCODE_BW] <= `INVALID_OPCODE;
            pchop_list_reg1[I*`OPCODE_BW +: `OPCODE_BW] <= `INVALID_OPCODE;
        end
        pchmreg_list_reg0 <= 0;
        pchmreg_list_reg1 <= 0;
        //
        pchidx_reg <= 0;
        topsu_valid_reg <= 0;
        tolmu_valid_reg <= 0;
        last_pchinfo_reg <= 0;
        is_writing_reg <= 0;
        opcode_reg_reg <= `INVALID_OPCODE;
        pchpp_list_reg0_reg <= 0;
        pchpp_list_reg1_reg <= 0;
        for (I = 0; I < `NUM_PCH; I = I+1)
        begin
            pchop_list_reg0_reg[I*`OPCODE_BW +: `OPCODE_BW] <= `INVALID_OPCODE;
            pchop_list_reg1_reg[I*`OPCODE_BW +: `OPCODE_BW] <= `INVALID_OPCODE;
        end
        pchmreg_list_reg0_reg <= 0;
        pchmreg_list_reg1_reg <= 0;       
    end
    else if (~reg_stall)
    begin
        // state 
        state <= next_state;
        // pchidx src regs
        if (pchlist_wren)
            pch_list_reg <= next_pchlist;
        if (esmon_wren)
            esmon_reg <= next_esmon;
        if (mgdreg_wren)
            merged_reg <= next_merged;
        if (mgdmem_wren)
            merged_mem <= next_merged;

        // pipelining
        pchidx_reg <= pchidx;
        topsu_valid_reg <= topsu_valid;
        tolmu_valid_reg <= tolmu_valid;
        last_pchinfo_reg <= last_pchinfo;
        is_writing_reg <= is_writing;
        opcode_reg_reg <= opcode_reg;
        pchpp_list_reg0_reg <= pchpp_list_reg0;
        pchpp_list_reg1_reg <= pchpp_list_reg1;
        pchop_list_reg0_reg <= pchop_list_reg0;
        pchop_list_reg1_reg <= pchop_list_reg1;
        pchmreg_list_reg0_reg <= pchmreg_list_reg0;
        pchmreg_list_reg1_reg <= pchmreg_list_reg1;

        // other input_regs
        if (take_in)
        begin
            opcode_reg <= opcode;
            pchpp_list_reg0 <= pchpp_list0;
            pchpp_list_reg1 <= pchpp_list1;
            pchop_list_reg0 <= pchop_list0;
            pchop_list_reg1 <= pchop_list1;
            pchmreg_list_reg0 <= pchmreg_list0;
            pchmreg_list_reg1 <= pchmreg_list1;
        end
    end
end


/*** Microunit instantiation ***/
piu_ctrl UUT0(
    .state(state),
    .pdu_valid(pdu_valid),
    .next_pchidxsrc(next_pchidxsrc),
    .pchidx(pchidx),
    .opcode_reg(opcode_reg),
    .opcode(opcode),
    .take_in(take_in),
    .update_pchidxsrc(update_pchidxsrc),
    .sel_pchidxsrc(sel_pchidxsrc),
    .topsu_valid(topsu_valid),
    .tolmu_valid(tolmu_valid),
    .next_state(next_state),
    .is_writing(is_writing),
    .prep_dyninfo(prep_dyninfo),
    .split_dyninfo(split_dyninfo),
    .set_merged(set_merged),
    .copy_merged(copy_merged),
    .last_pchinfo(last_pchinfo),
    .pchlist_wren(pchlist_wren),
    .esmon_wren(esmon_wren),
    .mgdreg_wren(mgdreg_wren),
    .mgdmem_wren(mgdmem_wren)
);

piu_pchindexer UUT1(
    .sel_pchidxsrc(sel_pchidxsrc),
    .pch_list_reg(pch_list_reg),
    .esmon_reg(esmon_reg),
    .merged_reg(merged_reg),
    .pchidx(pchidx),
    .next_pchidxsrc(next_pchidxsrc)
);

piu_nextsrc UUT2(
    .pch_list(pch_list),
    .take_in(take_in),
    .prep_dyninfo(prep_dyninfo),
    .split_dyninfo(split_dyninfo),
    .set_merged(set_merged), 
    .copy_merged(copy_merged), 
    .sel_pchidxsrc(sel_pchidxsrc),
    .next_pchidxsrc(next_pchidxsrc),
    .merged_mem(merged_mem), 
    .next_pchlist(next_pchlist), 
    .next_esmon(next_esmon),
    .next_merged(next_merged)
);

piu_static_rom UUT3(
    .rst(rst),
    .clk(clk),
    .pchidx(pchidx_reg),
    .pchinfo_static(pchinfo_static)
);

piu_dynamic_ram UUT4(
    .rst(rst), 
    .clk(clk),
    .prep_dyninfo(prep_dyninfo),
    .split_dyninfo(split_dyninfo),
    .is_writing(is_writing_reg), 
    .wr_facebd(wr_facebd),
    .wr_cornerbd(wr_cornerbd),
    .pchidx(pchidx_reg),
    .pchinfo_dynamic(pchinfo_dynamic)
);

piu_dyndecoder UUT5(
    .pchinfo_static(pchinfo_static), 
    .pchidx(pchidx_reg), 
    .pchpp_list_reg0(pchpp_list_reg0), 
    .pchpp_list_reg1(pchpp_list_reg1),
    .wr_facebd(wr_facebd),
    .wr_cornerbd(wr_cornerbd)
);

piu_pchinfo UUT6(
    .pchtype(pchtype),
    .pchop_list_reg0(pchop_list_reg0_reg), 
    .pchop_list_reg1(pchop_list_reg1_reg), 
    .pchmreg_list_reg0(pchmreg_list_reg0_reg),
    .pchmreg_list_reg1(pchmreg_list_reg1_reg), 
    .pchpp_list_reg0(pchpp_list_reg0_reg),
    .pchpp_list_reg1(pchpp_list_reg1_reg),
    .pchidx(pchidx_reg),
    .opcode_reg(opcode_reg),
    .pchinfo_etc(pchinfo_etc)
);

endmodule

