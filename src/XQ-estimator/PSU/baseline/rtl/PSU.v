`include "define.v"

module PSU(
    rst,
    clk,
    topsu_valid,
    opcode_in,
    pchinfo,
    last_pchinfo,
    cwdgen_stall,
    pchwr_stall, 
    psu_valid,
    cwdarray_out,
    timing_out,
    opcode_out
);

localparam LEN_SRMEM = ((`NUM_PCH/`NUM_PCU)*`NUM_PCU == `NUM_PCH) ? (`NUM_PCH/`NUM_PCU) : ((`NUM_PCH/`NUM_PCU) +1);

input rst, clk;
input topsu_valid;
input [`OPCODE_BW-1:0] opcode_in;
input [`PCHINFO_BW-1:0] pchinfo;
input last_pchinfo;
input cwdgen_stall, pchwr_stall;
output reg psu_valid;
output reg [`NUM_PQ*`CWD_BW-1:0] cwdarray_out;
output reg [`TIME_BW-1:0] timing_out;
output reg [`OPCODE_BW-1:0] opcode_out;


/*** Wires ***/
// from psu_opbuf (fifo)
wire [`OPCODE_BW-1:0] opcode_running;
// from psu_ctrl
wire [1:0] sel_cwdNtime;
wire flush_output;
wire next_qb;
wire next_uc;
wire next_pch;
wire next_id;
wire next_round;
wire next_opcode;
wire next_state;
// from psu_cntsrmem
wire [`TIME_BW-1:0] timing;
wire [`CWD_BW-1:0] cwd;
wire [`CWD_BW-1:0] cwdsp;
wire [`IDLEN_BW-1:0] id_len;
// from counters
wire [`QBADDR_BW-1:0] qb_counter0;
wire [`UCADDR_BW-1:0] uc_counter0;
// from psu_pisrmem
wire [`NUM_PCU*(`PCHINFO_BW+1)-1:0] pchinfo_list;
wire [`NUM_PCU*(2*`OPCODE_BW)-1:0] pchop_list;
wire [`NUM_PCU*(1)-1:0] pivalid_list;
wire pchinfo_full; 
wire pchinfo_valid; 
wire pchinfo_nextready; 
wire pchinfo_rdlast;
// from psu_opNloc
wire [`NUM_PCU*`OPCODE_BW-1:0] pcu_opcode;
wire [`NUM_UCC*`UCLOC_BW-1:0] ucc_ucloc;
// split for maskgen_array's input 
wire [`NUM_MASK*`OPCODE_BW-1:0] maskgen_opcode; 
wire [`NUM_MASK*`IDLEN_BW-1:0] maskgen_id;
wire [`NUM_MASK*`QBADDR_BW-1:0] maskgen_qbidx;
wire [`NUM_MASK*`UCLOC_BW-1:0] maskgen_ucloc;
wire [`NUM_MASK-1:0] maskgen_pchinfo_valid;
wire [`NUM_MASK*`PCHTYPE_BW-1:0] maskgen_pchtype;
wire [`NUM_MASK*`PCHDYN_BW-1:0] maskgen_pchdyn;

// from psu_maskgen_array
wire [`NUM_MASK-1:0] mask_array;
wire [`NUM_MASK-1:0] special_array;
// from psu_maskext
wire [`NUM_PQ-1:0] mask_ext_array;
wire [`NUM_PQ-1:0] special_ext_array;
// from psu_cwdarrgen
wire [`NUM_PQ*`CWD_BW-1:0] cwdarray;

// intermediate
wire [`NUM_PCU*`PCHADDR_BW-1:0] pchidx_list;


/*** Registers ***/
reg state;
reg [`NUM_QBCTRL*`QBADDR_BW-1:0] qb_counter;
reg [`NUM_UCC*`UCADDR_BW-1:0] uc_counter;
reg [`IDLEN_BW-1:0] id_counter;
reg [`ROUND_BW-1:0] round_counter;

// pipelining
reg [`NUM_MASK-1:0] mask_array_reg;
reg [`NUM_MASK-1:0] special_array_reg;
reg [`NUM_QBCTRL*`QBADDR_BW-1:0] qb_counter_reg;
reg [`NUM_UCC*`UCADDR_BW-1:0] uc_counter_reg;
reg [`NUM_PCU*`PCHADDR_BW-1:0] pchidx_list_reg;
reg [`NUM_PCU*(1)-1:0] pivalid_list_reg;
reg [`CWD_BW-1:0] cwd_reg;
reg [`CWD_BW-1:0] cwdsp_reg;
reg [`TIME_BW-1:0] timing_reg;
reg [`OPCODE_BW-1:0] opcode_reg;
reg valid_reg;


/*** Wire connection ***/
assign qb_counter0 = qb_counter[0 +: `QBADDR_BW];
assign uc_counter0 = uc_counter [0 +: `UCADDR_BW];
assign next_qb = (state == `PSU_RUNNING);
assign flush_output = psu_valid;

wire [`PCHINFO_BW-1:0] pidata_list [`NUM_PCU-1:0];

genvar j;
generate
    for (j = 0; j < `NUM_PCU; j = j+1) 
    begin: gen_pilist
        assign {pivalid_list[j], pidata_list[j]} = pchinfo_list[j*(`PCHINFO_BW+1) +: (`PCHINFO_BW+1)];
        assign pchop_list[j*(2*`OPCODE_BW) +: (2*`OPCODE_BW)] = pidata_list[j][(`PCHINFO_BW-1)-(`PCHSTAT_BW + `PCHDYN_BW + `PCHADDR_BW) -: (2*`OPCODE_BW)];
        assign pchidx_list[j*`PCHADDR_BW +: `PCHADDR_BW] = pidata_list[j][(`PCHINFO_BW-1)-(`PCHSTAT_BW+`PCHDYN_BW) -: `PCHADDR_BW];
    end
endgenerate

genvar k;
generate 
    for (k = 0; k < `NUM_MASK; k = k+1)
    begin: gen_maskgen_in
        assign maskgen_opcode[k*`OPCODE_BW +: `OPCODE_BW] = pcu_opcode[(k/`NUM_PCUQB)*`OPCODE_BW +: `OPCODE_BW];
        assign maskgen_id[k*`IDLEN_BW +: `IDLEN_BW] = id_counter;
        assign maskgen_qbidx[k*`QBADDR_BW +: `QBADDR_BW] = qb_counter[(k%`NUM_QBCTRL)*`QBADDR_BW +: `QBADDR_BW];
        assign maskgen_ucloc[k*`UCLOC_BW +: `UCLOC_BW] = ucc_ucloc[((k%`NUM_PCUQB)/`NUM_QBCTRL)*`UCLOC_BW +: `UCLOC_BW];
        assign maskgen_pchinfo_valid[k] = pivalid_list[(k/`NUM_PCUQB)];
        assign maskgen_pchtype[k*`PCHTYPE_BW +: `PCHTYPE_BW] = pidata_list[(k/`NUM_PCUQB)][`PCHINFO_BW-1 -: `PCHTYPE_BW];
        assign maskgen_pchdyn[k*`PCHDYN_BW +: `PCHDYN_BW] = pidata_list[(k/`NUM_PCUQB)][(`PCHINFO_BW-1)-`PCHSTAT_BW -: `PCHDYN_BW];
    end
endgenerate

integer J, K, IDX;
/*** Register update ***/
always @(posedge clk)
begin
    if (rst)
    begin
        psu_valid <= 0;
        cwdarray_out <= 0;
        timing_out <= 0;
        opcode_out <= `INVALID_OPCODE;
        for (J = 0; J < `NUM_UCC; J = J+1)
            uc_counter[J*`UCADDR_BW +: `UCADDR_BW] <= $unsigned(J);
        for (K = 0; K < `NUM_QBCTRL; K = K+1)
            qb_counter[K*`QBADDR_BW +: `QBADDR_BW] <= $unsigned(K);
        id_counter <= 0;
        round_counter <= 0;
        state <= `PSU_READY;
        //
        mask_array_reg <= 0;
        special_array_reg <= 0;
         for (J = 0; J < `NUM_UCC; J = J+1)
            uc_counter_reg[J*`UCADDR_BW +: `UCADDR_BW] <= $unsigned(J);
        for (K = 0; K < `NUM_QBCTRL; K = K+1)
            qb_counter_reg[K*`QBADDR_BW +: `QBADDR_BW] <= $unsigned(K);
        pchidx_list_reg <= 0;
        pivalid_list_reg <= 0;
        cwd_reg <= `CWD_I;
        cwdsp_reg <= `CWD_I;
        timing_reg <= 0;
        opcode_reg <= `INVALID_OPCODE;
        valid_reg <= 0;
    end
    else 
    begin
        pchidx_list_reg <= pchidx_list;
        pivalid_list_reg <= pivalid_list;

        if (~cwdgen_stall)
        begin
            // output regs
            psu_valid <= valid_reg;
            timing_out <= timing_reg;
            opcode_out <= opcode_reg;
            
            for (IDX = 0; IDX < `NUM_PQ; IDX = IDX+1)
            begin
                if (cwdarray[IDX*`CWD_BW +: `CWD_BW] != `CWD_I)
                    cwdarray_out[IDX*`CWD_BW +:`CWD_BW] <= cwdarray[IDX*`CWD_BW +: `CWD_BW];
                else if (flush_output)
                    cwdarray_out[IDX*`CWD_BW +:`CWD_BW] <= `CWD_I;
            end

            // pipelining
            mask_array_reg <= mask_array;
            special_array_reg <= special_array;
            ////
            if (next_id)
            begin
                valid_reg <= 1;
                timing_reg <= timing;
                opcode_reg <= opcode_running;
            end
            else
            begin
                valid_reg <= 0;
            end
            ////
            cwd_reg <= cwd;
            cwdsp_reg <= cwdsp;
            /////
            qb_counter_reg <= qb_counter; 
            uc_counter_reg <= uc_counter;

            // counters
            //// qb_counter
            if (next_uc)
            begin
                for (K = 0; K < `NUM_QBCTRL; K = K+1)
                    qb_counter[K*`QBADDR_BW +: `QBADDR_BW] <= $unsigned(K);
            end
            else if (next_qb)
            begin
                for (K = 0; K < `NUM_QBCTRL; K = K+1)
                    qb_counter[K*`QBADDR_BW +: `QBADDR_BW] <= qb_counter[K*`QBADDR_BW +: `QBADDR_BW] + `NUM_QBCTRL;
            end
            //// uc_counter
            if (next_pch)
            begin
                for (J = 0; J < `NUM_UCC; J = J+1)
                    uc_counter[J*`UCADDR_BW +: `UCADDR_BW] <= $unsigned(J);
            end
            else if (next_uc)
            begin
                for (J = 0; J < `NUM_UCC; J = J+1)
                    uc_counter[J*`UCADDR_BW +: `UCADDR_BW] <= uc_counter[J*`UCADDR_BW +: `UCADDR_BW] + `NUM_UCC;
            end
            //// id_counter
            if (next_round)
                id_counter <= 0;
            else if (next_id)
                id_counter <= id_counter + 1;
            //// round_counter
            if (next_opcode)
                round_counter <= 0;
            else if (next_round)
                round_counter <= round_counter + 1;

            // state 
            state <= next_state;
        end
    end
end


/*** Microunit instantiation ***/
// psu_opbuf
fifo #(
    .ADDR_BW(1), 
    .DATA_BW(`OPCODE_BW)
) UUT0(
    .rst(rst), 
    .clk(clk),
    .wr_din((~pchwr_stall) & topsu_valid & last_pchinfo), 
    .rd_dout((~cwdgen_stall) & next_opcode), 
    .din(opcode_in),
    .dout(opcode_running)
);
// psu_ctrl
psu_ctrl UUT1(
    .opcode_running(opcode_running),
    .psu_valid(psu_valid),
    .state(state),
    .qb_counter0(qb_counter0),
    .uc_counter0(uc_counter0),
    .pchinfo_rdlast(pchinfo_rdlast),
    .id_counter(id_counter),
    .id_len(id_len),
    .round_counter(round_counter),
    .pchinfo_valid(pchinfo_valid),
    .pchinfo_nextready(pchinfo_nextready),
    .sel_cwdNtime(sel_cwdNtime),
    .next_uc(next_uc),
    .next_pch(next_pch),
    .next_id(next_id),
    .next_round(next_round),
    .next_opcode(next_opcode),
    .next_state(next_state)
);
// psu_cntsrmem
psu_cntsrmem UUT2(
    .rst(rst),
    .clk(clk),
    .sel_cwdNtime(sel_cwdNtime),
    .next_id((~cwdgen_stall) & next_id),
    .timing(timing),
    .cwd(cwd),
    .cwdsp(cwdsp),
    .id_len(id_len)
);
// psu_pisrmem
srmem_double #(
    .NUM_RDPORT(`NUM_PCU),
    .LEN_SRMEM(LEN_SRMEM),
    .DATA_BW(`PCHINFO_BW)
) UUT3(
    .rst(rst), 
    .clk(clk),
    .valid_din((~pchwr_stall) & topsu_valid),
    .din(pchinfo),
    .is_lastdin(last_pchinfo),
    .req_pop((~cwdgen_stall) & next_pch),
    .req_newdata((~cwdgen_stall) & next_opcode),
    .dout_list(pchinfo_list),
    .wrfull(pchinfo_full),
    .rdvalid(pchinfo_valid),
    .nextready(pchinfo_nextready),
    .rdlastinfo(pchinfo_rdlast)
);

//psu_opNloc
psu_opNloc UUT4(
    .opcode_running(opcode_running),
    .pchop_list(pchop_list),
    .uc_counter(uc_counter),
    .pcu_opcode(pcu_opcode),
    .ucc_ucloc(ucc_ucloc)
);

// array of psu_maskgen
genvar i;
generate
    for (i = 0; i < `NUM_MASK; i = i+1)
    begin: gen_maskgen
        psu_maskgen UUT5_I(
            .opcode(maskgen_opcode[i*`OPCODE_BW +: `OPCODE_BW]), 
            .timeid(maskgen_id[i*`IDLEN_BW +: `IDLEN_BW]), 
            .qbidx(maskgen_qbidx[i*`QBADDR_BW +: `QBADDR_BW]),
            .ucloc(maskgen_ucloc[i*`UCLOC_BW +: `UCLOC_BW]),
            .pchinfo_valid(maskgen_pchinfo_valid[i]),
            .pchtype(maskgen_pchtype[i*`PCHTYPE_BW +: `PCHTYPE_BW]),
            .pchdyn(maskgen_pchdyn[i*`PCHDYN_BW +: `PCHDYN_BW]),
            .mask(mask_array[i]),
            .special(special_array[i])
        );
    end
endgenerate


// psu_maskext
psu_maskext UUT6(
    .pchidx_list(pchidx_list_reg),
    .pivalid_list(pivalid_list_reg),
    .uc_counter(uc_counter_reg), 
    .qb_counter(qb_counter_reg),
    .mask_array(mask_array_reg),
    .special_array(special_array_reg),
    .mask_ext_array(mask_ext_array),
    .special_ext_array(special_ext_array)
);

// psu_cwdarrgen
psu_cwdarrgen UUT7(
    .mask_ext_array(mask_ext_array),
    .special_ext_array(special_ext_array),
    .cwd(cwd_reg),
    .cwdsp(cwdsp_reg),
    .cwdarray(cwdarray)
);

endmodule
