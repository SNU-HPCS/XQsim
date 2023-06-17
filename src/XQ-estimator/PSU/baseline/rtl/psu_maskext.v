`include "define.v"

module psu_maskext(
    pchidx_list,
    pivalid_list,
    uc_counter, 
    qb_counter,
    mask_array,
    special_array,
    mask_ext_array,
    special_ext_array
);

input [`NUM_PCU*`PCHADDR_BW-1:0] pchidx_list;
input [`NUM_PCU*(1)-1:0] pivalid_list;
input [`NUM_UCC*`UCADDR_BW-1:0] uc_counter;
input [`NUM_QBCTRL*`QBADDR_BW-1:0] qb_counter;
input [`NUM_MASK-1:0] mask_array;
input [`NUM_MASK-1:0] special_array;
output reg [`NUM_PQ-1:0] mask_ext_array;
output reg [`NUM_PQ-1:0] special_ext_array;

reg [`NUM_PCUQB-1:0] mask_pchext_array [`NUM_PCH-1:0];
wire [`NUM_PCHDMX_OUT*`NUM_PCUQB-1:0] temp_special_pchext_array [`NUM_PCU-1:0];
reg [`NUM_PCUQB-1:0] special_pchext_array [`NUM_PCH-1:0];
//
wire [`NUM_UCDMX_OUT*`NUM_UCCQB-1:0] temp_mask_ucext_array[`NUM_PCH-1:0][`NUM_UCC-1:0];
reg [`NUM_UCCQB-1:0] mask_ucext_array [`NUM_PCH-1:0][`NUM_UC-1:0];
wire [`NUM_UCDMX_OUT*`NUM_UCCQB-1:0] temp_special_ucext_array[`NUM_PCH-1:0][`NUM_UCC-1:0];
reg [`NUM_UCCQB-1:0] special_ucext_array [`NUM_PCH-1:0][`NUM_UC-1:0];
//
wire [`NUM_QBDMX_OUT-1:0] temp_mask_qbext_array[`NUM_PCH-1:0][`NUM_UC-1:0][`NUM_QBCTRL-1:0];
wire [`NUM_QBDMX_OUT-1:0] temp_special_qbext_array[`NUM_PCH-1:0][`NUM_UC-1:0][`NUM_QBCTRL-1:0];
//
reg [`PCHADDR_BW-1:0] pchidx;
reg [`log2(`NUM_UCDMX_OUT)-1:0] ucsel [`NUM_UCC-1:0];
reg [`log2(`NUM_QBDMX_OUT)-1:0] qbsel [`NUM_QBCTRL-1:0];

integer I, J, K;
integer UCCID, UCID, QBCID, QBID;
always @(*)
begin

    for (J = 0; J < `NUM_UCC; J = J+1)
        ucsel[J] = (uc_counter[J*`UCADDR_BW +: `UCADDR_BW] / `NUM_UCC);
    for (K = 0; K < `NUM_QBCTRL; K = K+1)
        qbsel[K] = (qb_counter[K*`QBADDR_BW +: `QBADDR_BW] / `NUM_QBCTRL);

    //
    for (I = 0; I < `NUM_PCH; I=I+1)
    begin
        mask_pchext_array[I] = 0;
        special_pchext_array[I] = 0;
    end
    for (I = 0; I < `NUM_PCU; I = I+1)
    begin
        if (pivalid_list[I]) begin
            pchidx = pchidx_list[I*`PCHADDR_BW +: `PCHADDR_BW];
            mask_pchext_array[pchidx] = mask_array[I*`NUM_PCUQB +: `NUM_PCUQB];
            special_pchext_array[pchidx] = special_array[I*`NUM_PCUQB +: `NUM_PCUQB];
        end
    end


    for (I = 0; I < `NUM_PCH; I = I+1)
    begin
        for (J = 0; J < `NUM_UC; J = J+1)
        begin
            UCCID = J % `NUM_UCC;
            UCID = J / `NUM_UCC;
            mask_ucext_array[I][J] = temp_mask_ucext_array[I][UCCID][UCID*`NUM_UCCQB +: `NUM_UCCQB];
            special_ucext_array[I][J] = temp_special_ucext_array[I][UCCID][UCID*`NUM_UCCQB +: `NUM_UCCQB];
        end
    end

    for (I = 0; I < `NUM_PCH; I = I+1)
    begin
        for (J = 0; J < `NUM_UC; J = J+1)
        begin
            for (K = 0; K < `NUM_QB; K = K+1)
            begin
                QBCID = K % `NUM_QBCTRL;
                QBID = K / `NUM_QBCTRL;
                mask_ext_array[I*(`NUM_UC*`NUM_QB) + J*(`NUM_QB) + K] = temp_mask_qbext_array[I][J][QBCID][QBID];
                special_ext_array[I*(`NUM_UC*`NUM_QB) + J*(`NUM_QB) + K] = temp_special_qbext_array[I][J][QBCID][QBID];
            end
        end
    end
end


genvar iu, ju;
generate
    if (`NUM_UCDMX_OUT == 1)
    begin: gen_ucext_c
        for (iu = 0; iu < `NUM_PCH; iu = iu+1)
        begin: gen_ucext_c_i
            for (ju = 0; ju < `NUM_UCC; ju = ju+1)
            begin: gen_ucext_c_j
                assign temp_mask_ucext_array[iu][ju] = mask_pchext_array[iu][ju*`NUM_UCCQB +: `NUM_UCCQB];
                assign temp_special_ucext_array[iu][ju] = special_pchext_array[iu][ju*`NUM_UCCQB +: `NUM_UCCQB];
            end
        end
    end
    else
    begin: gen_ucext_g
        for (iu = 0; iu < `NUM_PCH; iu = iu+1)
        begin: gen_ucext_g_i
            for (ju = 0; ju < `NUM_UCC; ju = ju+1)
            begin: gen_ucext_g_j
                demux #(
                    .NUM_DATA(`NUM_UCDMX_OUT),
                    .DATA_BW(`NUM_UCCQB)
                ) UUT2_iu_ju(
                    .data_in(mask_pchext_array[iu][ju*`NUM_UCCQB +: `NUM_UCCQB]),
                    .sel(ucsel[ju]),
                    .data_out(temp_mask_ucext_array[iu][ju])
                );
                demux #(
                    .NUM_DATA(`NUM_UCDMX_OUT),
                    .DATA_BW(`NUM_UCCQB)
                ) UUT3_iu_ju(
                    .data_in(special_pchext_array[iu][ju*`NUM_UCCQB +: `NUM_UCCQB]),
                    .sel(ucsel[ju]),
                    .data_out(temp_special_ucext_array[iu][ju])
                );
            end
        end
    end
endgenerate


genvar iq, jq, kq;
generate
    if (`NUM_QBDMX_OUT == 1)
    begin: gen_qbext_c
        for (iq = 0; iq < `NUM_PCH; iq = iq+1)
        begin: gen_qbext_c_i
            for (jq = 0; jq < `NUM_UC; jq = jq+1)
            begin: gen_qbext_c_j
                for (kq = 0; kq < `NUM_QBCTRL; kq = kq+1)
                begin: gen_qbext_c_k
                    assign temp_mask_qbext_array[iq][jq][kq] = mask_ucext_array[iq][jq][kq*`NUM_QBCTRL +: `NUM_QBCTRL]; 
                    assign temp_special_qbext_array[iq][jq][kq] = special_ucext_array[iq][jq][kq*`NUM_QBCTRL +: `NUM_QBCTRL]; 
                end
            end
        end
    end
    else
    begin: gen_qbext_g
        for (iq = 0; iq < `NUM_PCH; iq = iq+1)
        begin: gen_qbext_g_i
            for (jq = 0; jq < `NUM_UC; jq = jq+1)
            begin: gen_qbext_g_j
                for (kq = 0; kq < `NUM_QBCTRL; kq = kq+1)
                begin: gen_qbext_g_k
                    demux #(
                        .NUM_DATA(`NUM_QBDMX_OUT),
                        .DATA_BW(1)
                    ) UUT4_iq_jq_kq(
                        .data_in(mask_ucext_array[iq][jq][kq]),
                        .sel(qbsel[kq]),
                        .data_out(temp_mask_qbext_array[iq][jq][kq])
                    );
                    demux #(
                        .NUM_DATA(`NUM_QBDMX_OUT),
                        .DATA_BW(1)
                    ) UUT5_iq_jq_kq(
                        .data_in(special_ucext_array[iq][jq][kq]),
                        .sel(qbsel[kq]),
                        .data_out(temp_special_qbext_array[iq][jq][kq])
                    );
                end
            end
        end
    end
endgenerate

endmodule
