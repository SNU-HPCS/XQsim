`include "define.v"

module lmu_lqsigngen(
    dqmeas_array_pch,
    pf_array_pch,
    pchinfo_valid,
    pchop0, 
    pchop1,
    pchidx,
    pchtype,
    facebd_n,
    lqsignZ_acc_reg,
    lqsignX_acc_reg,
    lqsign_valid,
    lqsign_valid_idx,
    lqsignZ_temp_list,
    lqsignX_temp_list 
);

input [`NUM_PCHDQ-1:0] dqmeas_array_pch;
input [`NUM_PCHDQ*2-1:0] pf_array_pch;
input pchinfo_valid;
input [`OPCODE_BW-1:0] pchop0, pchop1;
input [`PCHADDR_BW-1:0] pchidx;
input [`PCHTYPE_BW-1:0] pchtype;
input [`FACEBD_BW-1:0] facebd_n;
input [`NUM_LQ-1:0] lqsignZ_acc_reg;
input [`NUM_LQ-1:0] lqsignX_acc_reg;
output reg lqsign_valid;
output reg [`LQADDR_BW-1:0] lqsign_valid_idx;
output reg [`NUM_LQ-1:0] lqsignZ_temp_list;
output reg [`NUM_LQ-1:0] lqsignX_temp_list;

wire anc_pchtype;
assign anc_pchtype = (pchtype == `PCHTYPE_AW | pchtype == `PCHTYPE_AC | pchtype == `PCHTYPE_AE | pchtype == `PCHTYPE_AWE);

// dqmeas product values
reg dq_w_out;
reg dq_w_in;
reg dq_nw;
reg dq_sw;
reg dq_s;

// pf product values
reg pf_w_out;
reg pf_w_in;
reg pf_nw;
reg pf_sw;
reg pf_s;

reg sign_a_below;
reg sign_a_above;
reg sign_a_right;

reg dqmeas;
reg [1:0] pf;
reg uc_west, uc_north, uc_east, uc_south;
wire signed [`PCHADDR_BW:0] pchidx_s = $signed({1'b0, pchidx});

integer UCROW, UCCOL, QBIDX;
integer PCHROW, PCHCOL, LQIDX;
integer I;

always @(*)
begin
    if (pchinfo_valid)
    begin
        PCHROW = (pchidx_s / `NUM_PCHCOL);
        PCHCOL = (pchidx_s % `NUM_PCHCOL);

        // lqidx 
        if (PCHCOL == 0 & (PCHROW == 0 | PCHROW == 1))
            LQIDX = 0;
        else if (PCHCOL == 1 & (PCHROW == 0 | PCHROW == 1))
            LQIDX = 1;
        else if (PCHROW == 0)
            LQIDX = (PCHCOL-1) * 2;
        else if (PCHROW == 2)
            LQIDX = (PCHCOL-1) * 2 + 1;
        else if (PCHROW == 1 & (PCHCOL == `NUM_PCHCOL-1))
            LQIDX = `NUM_LQ-1;
        else
            LQIDX = 0;

        if (pchop0 == `PPM_INTERPRET_OPCODE | pchop1 == `PPM_INTERPRET_OPCODE)
        begin
            // lqsign_valid, lqsign_valid_idx
            if (pchtype == `PCHTYPE_ZB | pchtype == `PCHTYPE_M | pchtype == `PCHTYPE_X)
            begin
                lqsign_valid = 1;
                lqsign_valid_idx = $unsigned(LQIDX);
            end
            else
            begin
                lqsign_valid = 0;
                lqsign_valid_idx = 0;
            end

            // lqsignX/Z_temp_list
            /*** DQ/PF PRODUCT START ***/
            dq_w_out = 0;
            dq_w_in = 0;
            dq_nw = 0;
            dq_sw = 0;
            dq_s = 0;
            pf_w_out = 0;
            pf_w_in = 0;
            pf_nw = 0;
            pf_sw = 0;
            pf_s = 0;

            for (UCROW = 0; UCROW < `NUM_UCROW; UCROW = UCROW+1)
            begin
                for (UCCOL = 0; UCCOL < `NUM_UCCOL; UCCOL = UCCOL+1)
                begin
                    for (QBIDX = 0; QBIDX < (`NUM_QB/2); QBIDX = QBIDX+1)
                    begin
                        //
                        uc_west = (UCCOL == 0);
                        uc_north = (UCROW == 0);
                        uc_east = (UCCOL == `NUM_UCCOL-1);
                        uc_south = (UCROW == `NUM_UCROW-1);
                        //
                        I = UCROW*(`NUM_UCCOL*`NUM_QB/2) + UCCOL*(`NUM_QB/2) + QBIDX;
                        dqmeas = dqmeas_array_pch[I];
                        pf = pf_array_pch[I*2 +: 2];
                        //
                        //// _w_out
                        if (uc_west & uc_north)
                        begin
                            if (QBIDX == 2)
                            begin
                                dq_w_out = dq_w_out ^ dqmeas;
                                pf_w_out = pf_w_out ^ (pf == `PP_Z | pf == `PP_Y);
                            end
                        end
                        else if (uc_west)
                        begin
                            if (QBIDX == 0 | QBIDX == 2)
                            begin
                                dq_w_out = dq_w_out ^ dqmeas;
                                pf_w_out = pf_w_out ^ (pf == `PP_Z | pf == `PP_Y);
                            end
                        end
                        //// w_in
                        if (uc_west & uc_north)
                        begin
                            if (QBIDX == 3)
                            begin
                                dq_w_in = dq_w_in ^ dqmeas;
                                pf_w_in = pf_w_in ^ (pf == `PP_Z | pf == `PP_Y);
                            end
                        end
                        else if (uc_west)
                        begin
                            if (QBIDX == 1 | QBIDX == 3)
                            begin
                                dq_w_in = dq_w_in ^ dqmeas;
                                pf_w_in = pf_w_in ^ (pf == `PP_Z | pf == `PP_Y);
                            end
                        end
                        //// _nw
                        if (uc_west & uc_north)
                        begin
                            if (QBIDX == 1)
                            begin
                                dq_nw = dqmeas;
                                pf_nw = (pf == `PP_Z | pf == `PP_Y);
                            end
                        end
                        //// _sw
                        if (uc_west & uc_south)
                        begin
                            if (QBIDX == 2)
                            begin
                                dq_sw = dqmeas;
                                pf_sw = (pf == `PP_Z | pf == `PP_Y);
                            end
                        end
                        //// _s
                        if (uc_west & uc_south)
                        begin
                            if (QBIDX == 3)
                            begin
                                dq_s = dq_s ^ dqmeas;
                                pf_s = pf_s ^ (pf == `PP_Z | pf == `PP_Y);
                            end
                        end
                        else if (uc_south)
                        begin
                            if (QBIDX == 2 | QBIDX == 3)
                            begin
                                dq_s = dq_s ^ dqmeas;
                                pf_s = pf_s ^ (pf == `PP_Z | pf == `PP_Y);
                            end
                        end
                    end
                end
            end
            /*** DQ/PF PRODUCT END ***/

            /*** TEMP LIST START ***/
            lqsignX_temp_list = 0;
            lqsignZ_temp_list = 0;
        
            if (pchtype == `PCHTYPE_MB)
            begin
                lqsignZ_temp_list[0] = dq_w_out ^ pf_w_out;
                lqsignX_temp_list[0] = dq_w_out ^ pf_w_out;
            end
            else if (pchtype == `PCHTYPE_M & facebd_n == `FACEBD_PP)
            begin
                lqsignX_temp_list[LQIDX] = dq_nw ^ pf_nw;
            end
            else if (pchtype == `PCHTYPE_X)
            begin
                lqsignX_temp_list[LQIDX] = dq_sw ^ pf_sw;
            end
            else if (anc_pchtype)
            begin
                sign_a_below = (dq_sw ^ pf_sw);
                sign_a_above = (dq_sw ^ dq_w_in ^ dq_nw) ^ (pf_sw ^ pf_w_in ^ pf_nw);
                sign_a_right = (dq_sw ^ dq_s) ^ (pf_sw ^ pf_s);
                for (I = 0; I < `NUM_LQ; I = I+1)
                begin
                    if (I == (PCHCOL-1)*2+1)
                        lqsignX_temp_list[I] = sign_a_below;
                    else if (I == (PCHCOL-1)*2)
                        lqsignX_temp_list[I] = sign_a_above;
                    else if (I >= PCHCOL*2)
                        lqsignX_temp_list[I] = sign_a_right;
                    else
                        lqsignX_temp_list[I] = 0;
                end
            end
            else
            begin
                lqsignX_temp_list = 0;
                lqsignZ_temp_list = 0;
            end
            /*** TEMP LIST END ***/
        end
        else // for LQMs
        begin
            if (pchtype == `PCHTYPE_ZB | pchtype == `PCHTYPE_M | pchtype == `PCHTYPE_X)
            begin
                lqsign_valid = 1;
                lqsign_valid_idx = $unsigned(LQIDX);
                lqsignZ_temp_list = 0;
                lqsignZ_temp_list[LQIDX] = lqsignZ_acc_reg[LQIDX];
                lqsignX_temp_list = 0;
                lqsignX_temp_list[LQIDX] = lqsignX_acc_reg[LQIDX];
            end
            else
            begin
                lqsign_valid = 0;
                lqsign_valid_idx = 0;
                lqsignZ_temp_list = 0;
                lqsignX_temp_list = 0;
            end
        end
    end
    else
    begin // invalid pchinfo
        lqsign_valid = 0;
        lqsign_valid_idx = 0;
        lqsignZ_temp_list = 0;
        lqsignX_temp_list = 0;
    end
end

endmodule
