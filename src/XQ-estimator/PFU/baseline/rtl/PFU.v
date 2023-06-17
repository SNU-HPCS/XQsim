`include "define.v"

module PFU(
    rst,
    clk, 
    pchwr_stall,
    pchinfo,
    topsu_valid,
    last_pchinfo,
    piu_opcode,
    tcu_valid,
    tcu_opcode,
    error_array,
    error_valid,
    pfflag,
    pf_array,
    pfu_valid
);

input rst, clk;
input pchwr_stall;
input [`PCHINFO_BW-1:0] pchinfo;
input topsu_valid;
input last_pchinfo;
input [`OPCODE_BW-1:0] piu_opcode;
input tcu_valid;
input [`OPCODE_BW-1:0] tcu_opcode;
input [`NUM_DQ*2-1:0] error_array;
input error_valid;
input pfflag;
output [`NUM_DQ*2-1:0] pf_array;
output pfu_valid;

/*** Wires ***/
// from pfu_ctrl
wire [1:0] next_state;
wire pisrmem_push;
wire pisrmem_pop;
wire opbuf_push;
wire opbuf_pop;
wire sel_cwd_err;
wire next_valid;
wire pf_wren;
// from piu_opbuf
wire [`OPCODE_BW-1:0] cwd_opcode;
wire opbuf_empty;
// from pchinfo_srmem
wire [`PCHINFO_BW-1:0] pchinfo_pfu;
wire pivalid_pfu;
wire pchinfo_full;
wire pchinfo_valid;
wire pchinfo_rdlast;
wire [`PCHTYPE_BW-1:0] pchtype;
wire [`PCHDYN_BW-1:0] pchdyn;
wire [`PCHADDR_BW-1:0] pchidx;
// from pfu_cwdpatch
wire [`NUM_PCHDQ*`CWD_BW-1:0] cwd_patch;
// from pfu_demux
wire [`NUM_DQ*`CWD_BW-1:0] cwd_array;
// from array of pfu_pfupdater
wire [`NUM_DQ*2-1:0] new_pfarray;

/*** Registers ***/
reg [1:0] state;
reg [`OPCODE_BW-1:0] tcu_opcode_reg;
reg valid_reg;
reg [`NUM_DQ*2-1:0] pfarray_reg;

/*** Wire connection ***/ 
assign pchtype = pchinfo_pfu[`PCHINFO_BW-1 -: `PCHTYPE_BW];
assign pchdyn = pchinfo_pfu[(`PCHINFO_BW-1)-`PCHSTAT_BW -: `PCHDYN_BW];
assign pchidx = pchinfo_pfu[(`PCHINFO_BW-1)-(`PCHSTAT_BW+`PCHDYN_BW) -: `PCHADDR_BW];
assign pf_array = pfarray_reg;
assign pfu_valid = valid_reg;

/*** Register update ***/
always @(posedge clk)
begin
    if (rst)
    begin
        state <= `PFU_READY;
        tcu_opcode_reg <= `INVALID_OPCODE;
        valid_reg <= 0;
        pfarray_reg <= 0;
    end
    else
    begin
        state <= next_state;
        if (tcu_valid)
            tcu_opcode_reg <= tcu_opcode;
        valid_reg <= next_valid;
        if (pf_wren)
            pfarray_reg <= new_pfarray;
    end
end

// pfu_control
pfu_ctrl UUT0(
    .state(state),
    .tcu_opcode_reg(tcu_opcode_reg),
    .pchinfo_rdlast(pchinfo_rdlast),
    .error_valid(error_valid),
    .pchwr_stall(pchwr_stall),
    .topsu_valid(topsu_valid),
    .piu_opcode(piu_opcode),
    .last_pchinfo(last_pchinfo),
    .pfflag(pfflag),
    .next_state(next_state),
    .pisrmem_push(pisrmem_push),
    .pisrmem_pop(pisrmem_pop),
    .opbuf_push(opbuf_push),
    .opbuf_pop(opbuf_pop),
    .sel_cwd_err(sel_cwd_err),
    .next_valid(next_valid),
    .pf_wren(pf_wren)
);

// piu_opcode_buf
fifo #(
    .ADDR_BW(1),
    .DATA_BW(`OPCODE_BW)
) UUT1(
    .rst(rst),
    .clk(clk),
    .wr_din(opbuf_push),
    .rd_dout(opbuf_pop),
    .din(piu_opcode),
    .dout(cwd_opcode),
    .empty(opbuf_empty)
);

// pfu_pisrmem
srmem_double #(
    .NUM_RDPORT(1),
    .LEN_SRMEM(`NUM_PCH),
    .DATA_BW(`PCHINFO_BW)
) UUT2(
    .rst(rst), 
    .clk(clk),
    .valid_din(pisrmem_push),
    .din(pchinfo),
    .is_lastdin(last_pchinfo),
    .req_pop(pisrmem_pop),
    .req_newdata(1'b1),
    .dout_list({pivalid_pfu, pchinfo_pfu}),
    .wrfull(pchinfo_full),
    .rdvalid(pchinfo_valid),
    .rdlastinfo(pchinfo_rdlast)
);

integer QBIDX;
genvar i, j, k;
generate
    for (i = 0; i < `NUM_UCROW; i = i+1)
    begin: gen_pfu_cwdgen_i
        for (j = 0; j < `NUM_UCCOL; j = j+1)
        begin: gen_pfu_cwdgen_j
            for (k = 0; k < (`NUM_QB/2); k = k+1)
            begin: gen_pfu_cwdgen_k
                pfu_cwdgen UUT3_i_j_k(
                    .ucrow($unsigned(i[0 +: `UCADDR_BW])),
                    .uccol($unsigned(j[0 +: `UCADDR_BW])),
                    .qbidx($unsigned(k[0 +: `QBADDR_BW])),
                    .pchinfo_valid(pchinfo_valid), 
                    .pchtype(pchtype),
                    .pchdyn(pchdyn), 
                    .cwd_opcode(cwd_opcode),
                    .cwd_valid(~opbuf_empty),
                    .cwd_pf(cwd_patch[(i*(`NUM_UCROW*`NUM_QB/2)+j*(`NUM_QB/2)+k)*`CWD_BW +: `CWD_BW])
            );
            end
        end
    end
endgenerate

// pfu_demux
demux #(
    .NUM_DATA(`NUM_PCH),
    .DATA_BW(`NUM_PCHDQ*`CWD_BW)
) UUT4(
    .data_in(cwd_patch),
    .sel(pchidx),
    .data_out(cwd_array)
);

// array of pfu_pfupdater
genvar l;
generate
    for (l = 0; l < `NUM_DQ; l = l+1)
    begin: gen_pfupdater
        pfu_pfupdater UUT5_I(
            .mgdcwd(cwd_array[l*`CWD_BW +: `CWD_BW]),
            .error(error_array[l*2 +: 2]),
            .sel_cwd_err(sel_cwd_err),
            .pf(pfarray_reg[l*2 +: 2]),
            .newpf(new_pfarray[l*2 +: 2])
        );
    end
endgenerate

endmodule
