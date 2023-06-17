`include "define.v"

module LMU (
    rst,
    clk,
    pchwr_stall,
    qid_lmubuf_dout,
    qid_lmubuf_empty,
    qid_a_taken,
    piu_pchinfo,
    piu_tolmu_valid,
    piu_lastpchinfo,
    tcu_opcode,
    tcu_valid,
    dqmeas_valid,
    dqmeas_array,
    aqmeas_valid,
    aqmeas_array,
    pf_valid,
    pf_array,
    measfb_xorz,
    finmeas_reg_val,
    finmeas_reg_valid
);

input rst, clk;
input pchwr_stall;
// from qid
input [`TO_LMUBUF_BW-1:0] qid_lmubuf_dout;
input qid_lmubuf_empty;
input qid_a_taken;
// from piu
input [`PCHINFO_BW-1:0] piu_pchinfo;
input piu_tolmu_valid;
input piu_lastpchinfo;
// from tcu
input [`OPCODE_BW-1:0] tcu_opcode;
input tcu_valid;
// from qc interface
input dqmeas_valid;
input [`NUM_DQ-1:0] dqmeas_array;
// from edu
input aqmeas_valid;
input [`NUM_AQ-1:0] aqmeas_array;
// from pfu
input pf_valid;
input [`NUM_DQ*2-1:0] pf_array;
//
output [1:0] measfb_xorz;
output reg [`NUM_LQ-1:0] finmeas_reg_val;
output reg [`NUM_LQ-1:0] finmeas_reg_valid;

/*** Wires ***/
// from lmu_iisrmem
wire [`INSTINFO_BW-1:0] instinfo;
wire instinfo_full;
wire instinfo_valid;
wire instinfo_nextready;
wire instinfo_rdlast;
// from lmu_pisrmem
wire [`PCHINFO_BW-1:0] pchinfo;
wire pchinfo_full;
wire pchinfo_valid;
wire pchinfo_nextready;
wire pchinfo_rdlast;
// from lmu_measopbuf
wire [`OPCODE_BW-1:0] measop;
// from lmu_ctrl
wire [1:0] next_state;
wire new_array_ing;
wire [`SELMEAS_BW*2-1:0] sel_meases;
wire [1:0] initmeas_wrens;
wire initmeas_rst;
wire pchinfo_pop;
wire flip_initmeas_wr;
wire flip_initmeas_rd;
wire instinfo_pop;
wire finmeas_wren;
wire byproduct_wren;
wire abcd_rst;
wire meas_sign;
wire byproduct_regwren;
wire byproduct_check;
wire abcd_wren;
wire [1:0] abcd_addr;
wire sel_reverse;
wire lqsign_temp_wren;
wire lqsign_temp_rst;
wire lqsign_acc_wren;
// from lmu_measmux
wire [`NUM_PCHDQ-1:0] dqmeas_array_pch;
wire [`NUM_PCHAQ-1:0] aqmeas_array_pch;
wire [`NUM_PCHDQ*2-1:0] pf_array_pch;
// from lmu_selmeas
wire [1:0] initial_meases;
// from lmu_interpret
wire final_meas;
wire [`NUM_LQ*2-1:0] next_byproduct;
// from lmu_lqsigngen
wire lqsign_valid;
wire [`LQADDR_BW-1:0] lqsign_valid_idx;
wire [`NUM_LQ-1:0] lqsignZ_temp_list;
wire [`NUM_LQ-1:0] lqsignX_temp_list;
// pchinfo
wire [`PCHTYPE_BW-1:0] pchtype;
wire [`BDLOC_BW-1:0] z_bd, x_bd;
wire [`FACEBD_BW-1:0] facebd_w, facebd_n, facebd_e, facebd_s;
wire [`CORNERBD_BW-1:0] cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se;
wire [`PCHADDR_BW-1:0] pchidx;
wire [`OPCODE_BW-1:0] pchop0, pchop1;
wire [`LQADDR_BW-1:0] pchmreg0, pchmreg1;
wire [1:0] pchpp0, pchpp1;
// instinfo
wire [`MEAS_FLAG_BW-1:0] measflags;
wire [`NUM_LQ*2-1:0] lpplist;
wire [`LQADDR_BW-1:0] mregdst;
// abcd_reg
wire a_valid, a_val, b_valid, b_val, c_valid, c_val, d_valid, d_val;
// qid_lmubuf_dout
wire [`LQADDR_BW-1:0] qid_lmubuf_mregdst;
// intermediate
wire is_measop;
wire init_meas;

/*** Registers ***/
reg [1:0] state;
reg [`OPCODE_BW-1:0] prev_opcode;
reg dqmeas_ready, aqmeas_ready, pf_ready;
reg [`NUM_DQ-1:0] dqmeas_array_reg, dqmeas_array_ing;
reg [`NUM_AQ-1:0] aqmeas_array_reg, aqmeas_array_ing;
reg [`NUM_DQ*2-1:0] pf_array_reg, pf_array_ing;
reg sel_initmeas_wr, sel_initmeas_rd;
reg [`NUM_LQ*2-1:0] byproduct_reg;
reg [`NUM_LQ*2-1:0] byproduct;
reg a_taken_reg, a_sign_reg;
// meas regs
reg [`NUM_LQ-1:0] initmeas_reg [1:0];
reg [`NUM_LQ*2-1:0] finmeas_reg;
reg [4*2-1:0] abcd_reg;
reg [`NUM_LQ-1:0] lqsignX_temp_reg;
reg [`NUM_LQ-1:0] lqsignZ_temp_reg;
reg [`NUM_LQ-1:0] lqsign_valid_temp_reg;
reg [`NUM_LQ-1:0] lqsignX_acc_reg;
reg [`NUM_LQ-1:0] lqsignZ_acc_reg;
// pipelining regs
reg new_array_ing_reg;
reg pchinfo_rdlast_reg;
////
reg [`NUM_PCHDQ-1:0] dqmeas_array_pch_reg;
reg [`NUM_PCHAQ-1:0] aqmeas_array_pch_reg;
reg [`NUM_PCHDQ*2-1:0] pf_array_pch_reg;
reg [`SELMEAS_BW*2-1:0] sel_meases_reg;
reg sel_reverse_reg;
reg pchinfo_valid_reg;
reg [`OPCODE_BW-1:0] pchop0_reg, pchop1_reg;
reg [`PCHADDR_BW-1:0] pchidx_reg; 
reg [`PCHTYPE_BW-1:0] pchtype_reg;
reg [`FACEBD_BW-1:0] facebd_n_reg;
reg [`LQADDR_BW-1:0] pchmreg0_reg, pchmreg1_reg;

/*** Wire connection ***/
assign {pchtype, z_bd, x_bd, facebd_w, facebd_n, facebd_e, facebd_s, cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se, pchidx, pchop0, pchop1, pchmreg0, pchmreg1, pchpp0, pchpp1} = pchinfo;
assign {measflags, lpplist, mregdst} = instinfo;
assign is_measop = (tcu_opcode == `LQI_OPCODE | tcu_opcode == `INIT_INTMD_OPCODE | tcu_opcode == `MEAS_INTMD_OPCODE | tcu_opcode == `LQM_X_OPCODE | tcu_opcode == `LQM_Y_OPCODE | tcu_opcode == `LQM_Z_OPCODE);
assign init_meas = initmeas_reg[sel_initmeas_rd][mregdst];
assign {d_valid, d_val, c_valid, c_val, b_valid, b_val, a_valid, a_val} = abcd_reg;
assign qid_lmubuf_mregdst = qid_lmubuf_dout[(`TO_LMUBUF_BW-1)-(`MEAS_FLAG_BW+2*`NUM_LQ) -: `LQADDR_BW];
assign {meas_sign, byproduct_regwren, byproduct_check, abcd_wren, abcd_addr} = measflags;
assign flip_initmeas_rd = initmeas_rst;
assign instinfo_pop = finmeas_wren;
assign sel_reverse = (pchtype == `PCHTYPE_MT);

integer I;
always @(*)
begin
    for (I = 0; I < `NUM_LQ; I = I+1)
    begin
        {finmeas_reg_valid[I], finmeas_reg_val[I]} = finmeas_reg[I*2 +: 2];
    end
end

/*** Register update ***/
always @(posedge clk)
begin
    if (rst)
    begin
        state <= `LMU_READY;
        prev_opcode <= `INVALID_OPCODE;
        dqmeas_ready <= 0;
        aqmeas_ready <= 0;
        pf_ready <= 0;
        dqmeas_array_reg <= 0;
        aqmeas_array_reg <= 0;
        pf_array_reg <= 0;
        dqmeas_array_ing <= 0;
        aqmeas_array_ing <= 0;
        pf_array_ing <= 0;
        sel_initmeas_wr <= 0;
        sel_initmeas_rd <= 0;
        byproduct_reg <= 0;
        byproduct <= 0;
        a_taken_reg <= 0;
        a_sign_reg <= 0;
        initmeas_reg[0] <= 0;
        initmeas_reg[1] <= 0;
        finmeas_reg <= 0;
        abcd_reg <= 0;
        lqsignX_temp_reg <= 0;
        lqsignZ_temp_reg <= 0;
        lqsign_valid_temp_reg <= 0;
        lqsignX_acc_reg <= 0;
        lqsignZ_acc_reg <= 0;
        //pipelining
        new_array_ing_reg <= 0;
        pchinfo_rdlast_reg <= 0;
        ////
        dqmeas_array_pch_reg <= 0;
        aqmeas_array_pch_reg <= 0;
        pf_array_pch_reg <= 0;
        sel_meases_reg <= 0;
        sel_reverse_reg <= 0;
        pchinfo_valid_reg <= 0;
        pchop0_reg <= `INVALID_OPCODE;
        pchop1_reg <= `INVALID_OPCODE;
        pchidx_reg <= 0;
        pchtype_reg <= `PCHTYPE_I; 
        facebd_n_reg <= `FACEBD_I;
        pchmreg0_reg <= 0;
        pchmreg1_reg <= 0;
    end
    else
    begin
        // state 
        state <= next_state;
        // prev_opcode 
        if (tcu_valid)
            prev_opcode <= tcu_opcode;

        // array_ing
        if (new_array_ing)
        begin
            dqmeas_array_ing <= dqmeas_array_reg;
            aqmeas_array_ing <= aqmeas_array_reg;
            pf_array_ing <= pf_array_reg;
            dqmeas_ready <= 0;
            aqmeas_ready <= 0;
            pf_ready <= 0;
        end
        // input registers
        if (dqmeas_valid)
        begin
            if (measop == `LQM_X_OPCODE | measop == `LQM_Y_OPCODE | measop == `LQM_Z_OPCODE | measop == `MEAS_INTMD_OPCODE)
            begin
                dqmeas_ready <= 1;
                dqmeas_array_reg <= dqmeas_array;
            end
        end
        if (aqmeas_valid)
        begin
            aqmeas_ready <= 1;
            aqmeas_array_reg <= aqmeas_array;
        end
        if (pf_valid)
        begin
            pf_ready <= 1;
            pf_array_reg <= pf_array;
        end
        // sel_initmeas_wr/rd
        if (flip_initmeas_wr)
            sel_initmeas_wr <= sel_initmeas_wr ^ 1;
        if (flip_initmeas_rd)
            sel_initmeas_rd <= sel_initmeas_rd ^ 1;
        // byproduct_reg
        if (byproduct_regwren)
            byproduct_reg <= lpplist;
    
        // byproduct
        if (byproduct_wren)
            byproduct <= next_byproduct;

        // a_taken_reg
        if (qid_a_taken)
            a_taken_reg <= 1;
        if (abcd_rst)
            a_taken_reg <= 0;

        // a_sign_reg
        if (abcd_wren & abcd_addr == `ABCDADDR_A)
            a_sign_reg <= meas_sign;

        // initmeas_reg
        if (initmeas_rst)
        begin
            initmeas_reg[sel_initmeas_rd] <= 0;
        end
        else
        begin
            if (initmeas_wrens[0])
            begin
                initmeas_reg[sel_initmeas_wr][pchmreg0_reg] <= initmeas_reg[sel_initmeas_wr][pchmreg0_reg] ^ initial_meases[0];
            end
            if (initmeas_wrens[1])
            begin
                initmeas_reg[sel_initmeas_wr][pchmreg1_reg] <= initmeas_reg[sel_initmeas_wr][pchmreg1_reg] ^ initial_meases[1];
            end
        end

        // finmeas_reg
        if (finmeas_wren)
        begin
            finmeas_reg[mregdst*2 +: 2] <= {1'b1, final_meas};
        end
        else if ((~qid_lmubuf_empty) & (~instinfo_full))
        begin
            finmeas_reg[qid_lmubuf_mregdst*2+1] <= 0;
        end

        // abcd_reg
        if (abcd_rst)
        begin
            abcd_reg <= 0;
        end
        else if (abcd_wren)
        begin
            abcd_reg[abcd_addr*2 +: 2] <= {1'b1, final_meas};
        end

        // lqsign_temp_reg
        if (lqsign_temp_rst)
        begin
            lqsignX_temp_reg <= 0;
            lqsignZ_temp_reg <= 0;
            lqsign_valid_temp_reg <= 0;
        end
        else if (lqsign_temp_wren)
        begin
            lqsignX_temp_reg <= (lqsignX_temp_reg ^ lqsignX_temp_list);
            lqsignZ_temp_reg <= (lqsignZ_temp_reg ^ lqsignZ_temp_list);
            if (lqsign_valid)
                lqsign_valid_temp_reg[lqsign_valid_idx] <= 1;
        end

        // lqsign_acc_reg
        if (lqsign_acc_wren)
        begin
            for (I = 0; I < `NUM_LQ; I = I+1)
            begin
                if (lqsign_valid_temp_reg[I])
                begin
                    lqsignZ_acc_reg[I] <= (lqsignZ_acc_reg[I] ^ lqsignZ_temp_reg[I]);
                    lqsignX_acc_reg[I] <= (lqsignX_acc_reg[I] ^ lqsignX_temp_reg[I]);
                end
            end
        end

        // pipelining regs
        new_array_ing_reg <= new_array_ing;
        pchinfo_rdlast_reg <= pchinfo_rdlast;
        ////
        dqmeas_array_pch_reg <= dqmeas_array_pch;
        aqmeas_array_pch_reg <= aqmeas_array_pch;
        pf_array_pch_reg <= pf_array_pch;
        sel_meases_reg <= sel_meases;
        sel_reverse_reg <= sel_reverse;
        pchinfo_valid_reg <= pchinfo_valid;
        pchop0_reg <= pchop0;
        pchop1_reg <= pchop1;
        pchidx_reg <= pchidx;
        pchtype_reg <= pchtype; 
        facebd_n_reg <= facebd_n;
        pchmreg0_reg <= pchmreg0;
        pchmreg1_reg <= pchmreg1;
    end
end


/*** Microunit instantiation ***/
// lmu_iisrmem
srmem_double #(
    .NUM_RDPORT(1),
    .LEN_SRMEM(`NUM_LQ),
    .DATA_BW(`INSTINFO_BW)
) UUT0(
    .rst(rst), 
    .clk(clk),
    .valid_din(~qid_lmubuf_empty),
    .din(qid_lmubuf_dout[1 +: `INSTINFO_BW]),
    .is_lastdin(qid_lmubuf_dout[0]),
    .req_pop(instinfo_pop),
    .req_newdata(1'b1),
    .dout_list({instinfo_valid, instinfo}),
    .wrfull(instinfo_full),
    .nextready(instinfo_nextready),
    .rdlastinfo(instinfo_rdlast)
);

// lmu_pisrmem
srmem_double #(
    .NUM_RDPORT(1),
    .LEN_SRMEM(`NUM_PCH),
    .DATA_BW(`PCHINFO_BW)
) UUT1(
    .rst(rst), 
    .clk(clk),
    .valid_din((~pchwr_stall) & piu_tolmu_valid),
    .din(piu_pchinfo),
    .is_lastdin(piu_lastpchinfo),
    .req_pop(pchinfo_pop),
    .req_newdata(1'b1),
    .dout_list({pchinfo_valid, pchinfo}),
    .wrfull(pchinfo_full),
    .nextready(pchinfo_nextready),
    .rdlastinfo(pchinfo_rdlast)
);

// lmu_measopbuf
fifo #(
    .ADDR_BW(`log2(`MOBUF_SZ)),
    .DATA_BW(`OPCODE_BW)
) UUT2(
    .rst(rst), 
    .clk(clk),
    .wr_din(tcu_valid & is_measop & tcu_opcode != prev_opcode), 
    .rd_dout(dqmeas_valid), 
    .din(tcu_opcode),
    .dout(measop)
);

// lmu_ctrl
lmu_ctrl UUT3(
    .new_array_ing_reg(new_array_ing_reg),
    .pchinfo_rdlast_reg(pchinfo_rdlast_reg),
    .sel_meases_reg(sel_meases_reg),
    .state(state),
    .pchinfo_valid(pchinfo_valid),
    .pchtype(pchtype),
    .facebd_n(facebd_n),
    .pchop0(pchop0),
    .pchop1(pchop1),
    .dqmeas_ready(dqmeas_ready),
    .aqmeas_ready(aqmeas_ready),
    .pf_ready(pf_ready), 
    .pchinfo_rdlast(pchinfo_rdlast), 
    .instinfo_rdlast(instinfo_rdlast),
    .abcd_reg(abcd_reg),
    .measflags(measflags),
    .next_state(next_state),
    .new_array_ing(new_array_ing),
    .sel_meases(sel_meases),
    .initmeas_wrens(initmeas_wrens),
    .initmeas_rst(initmeas_rst),
    .pchinfo_pop(pchinfo_pop),
    .flip_initmeas_wr(flip_initmeas_wr),
    .finmeas_wren(finmeas_wren),
    .byproduct_wren(byproduct_wren),
    .abcd_rst(abcd_rst),
    .lqsign_temp_wren(lqsign_temp_wren),
    .lqsign_temp_rst(lqsign_temp_rst),
    .lqsign_acc_wren(lqsign_acc_wren)
);

// lmu_measmux
lmu_measmux UUT4(
    .pchidx(pchidx), 
    .dqmeas_array_ing(dqmeas_array_ing), 
    .aqmeas_array_ing(aqmeas_array_ing), 
    .pf_array_ing(pf_array_ing),
    .dqmeas_array_pch(dqmeas_array_pch), 
    .aqmeas_array_pch(aqmeas_array_pch),
    .pf_array_pch(pf_array_pch)
);

// lmu_selproduct
lmu_selproduct UUT5_0(
    .sel_meas(sel_meases_reg[0 +: `SELMEAS_BW]),
    .sel_reverse(sel_reverse_reg),
    .dqmeas_array_pch(dqmeas_array_pch_reg),
    .aqmeas_array_pch(aqmeas_array_pch_reg),
    .pf_array_pch(pf_array_pch_reg),
    .initial_meas(initial_meases[0])
);
lmu_selproduct UUT5_1(
    .sel_meas(sel_meases_reg[`SELMEAS_BW +: `SELMEAS_BW]),
    .sel_reverse(sel_reverse_reg),
    .dqmeas_array_pch(dqmeas_array_pch_reg),
    .aqmeas_array_pch(aqmeas_array_pch_reg),
    .pf_array_pch(pf_array_pch_reg),
    .initial_meas(initial_meases[1])
);

// lmu_interpret
lmu_interpret UUT6(
    .lqsignX_acc_reg(lqsignX_acc_reg),
    .lqsignZ_acc_reg(lqsignZ_acc_reg),
    .lpplist(lpplist),
    .byproduct(byproduct),
    .meas_sign(meas_sign),
    .byproduct_check(byproduct_check),
    .init_meas(init_meas),
    .byproduct_reg(byproduct_reg),
    .a_valid(a_valid),
    .a_val(a_val),
    .a_taken_reg(a_taken_reg),
    .a_sign_reg(a_sign_reg),
    .final_meas(final_meas),
    .next_byproduct(next_byproduct),
    .measfb_xorz(measfb_xorz)
);

// lmu_lqsigngen
lmu_lqsigngen UUT7(
    .dqmeas_array_pch(dqmeas_array_pch_reg),
    .pf_array_pch(pf_array_pch_reg),
    .pchinfo_valid(pchinfo_valid_reg),
    .pchop0(pchop0_reg), 
    .pchop1(pchop1_reg),
    .pchidx(pchidx_reg),
    .pchtype(pchtype_reg),
    .facebd_n(facebd_n_reg),
    .lqsignZ_acc_reg(lqsignZ_acc_reg),
    .lqsignX_acc_reg(lqsignX_acc_reg),
    .lqsign_valid(lqsign_valid),
    .lqsign_valid_idx(lqsign_valid_idx),
    .lqsignZ_temp_list(lqsignZ_temp_list),
    .lqsignX_temp_list(lqsignX_temp_list) 
);

endmodule
