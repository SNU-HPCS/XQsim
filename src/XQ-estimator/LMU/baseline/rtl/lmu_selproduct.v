`include "define.v"

module lmu_selproduct(
    sel_meas,
    sel_reverse,
    dqmeas_array_pch,
    aqmeas_array_pch,
    pf_array_pch,
    initial_meas
);

input [`SELMEAS_BW-1:0] sel_meas;
input sel_reverse;
input [`NUM_PCHDQ-1:0] dqmeas_array_pch;
input [`NUM_PCHAQ-1:0] aqmeas_array_pch;
input [`NUM_PCHDQ*2-1:0] pf_array_pch;
output initial_meas;



// sel_meas
wire [`SELLOC_BW-1:0] sel_loc;
wire sel_dqaq, sel_xz, sel_valid;
assign {sel_loc, sel_dqaq, sel_xz, sel_valid} = sel_meas;

// aqmeas product values
reg aq_even_all;
reg aq_even_w;
reg aq_even_e;
wire aq_even_winv;
assign aq_even_winv = aq_even_all ^ aq_even_w;

reg aq_odd_all;
reg aq_odd_w;
reg aq_odd_e;
reg aq_odd_s;
wire aq_odd_sinv;
wire aq_odd_winv;
assign aq_odd_winv = aq_odd_all ^ aq_odd_w;
assign aq_odd_sinv = aq_odd_all ^ aq_odd_s;

// dqmeas product values
reg dq_e;
reg dq_ne;
reg dq_w_bd;
reg dq_s_bd;
reg dq_sw;
wire dq_w;
wire dq_s;
wire dq_w_s;
wire dq_e_ex;
assign dq_w = dq_w_bd ^ dq_sw;
assign dq_s = dq_s_bd ^ dq_sw;
assign dq_w_s = dq_w_bd ^ dq_s_bd ^ dq_sw;
assign dq_e_ex = dq_e ^ dq_ne;

// pf product values
reg pf_e_zy;
reg pf_e_xy;
reg pf_s_bd_zy;
reg pf_s_bd_xy;
reg pf_sw_zy;
reg pf_sw_xy;
reg pf_w_bd_zy;
reg pf_w_bd_xy;
reg pf_ne_xz;
reg pf_ne_xy;
reg pf_ne_zy;

// output product
reg dq_product;
reg aq_product;
reg pf_product;
// output assign
assign initial_meas = aq_product ^ dq_product ^ pf_product;

integer UCROW, UCCOL, QBIDX;
integer IDX;
reg dqmeas;
reg aqmeas;
reg [1:0] pf;
reg uc_west, uc_north, uc_east, uc_south;
reg even;
always @(*)
begin
    // PRODUCT
    aq_even_all = 0;
    aq_even_w = 0;
    aq_even_e = 0;
    aq_odd_all = 0;
    aq_odd_w = 0;
    aq_odd_e = 0;
    aq_odd_s = 0;
    dq_e = 0;
    dq_ne = 0;
    dq_w_bd = 0;
    dq_s_bd = 0;
    dq_sw = 0;
    pf_e_zy = 0;
    pf_e_xy = 0;
    pf_ne_xz = 0;
    pf_ne_xy = 0;
    pf_ne_zy = 0;
    pf_w_bd_zy = 0;
    pf_w_bd_xy = 0;
    pf_s_bd_zy = 0;
    pf_s_bd_xy = 0;
    pf_sw_zy = 0; 
    pf_sw_xy = 0;

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
                IDX = UCROW*(`NUM_UCCOL*`NUM_QB/2) + UCCOL*(`NUM_QB/2) + QBIDX;
                dqmeas = dqmeas_array_pch[IDX];
                aqmeas = aqmeas_array_pch[IDX];
                pf = pf_array_pch[IDX*2 +: 2];

                // DQMEAS PRODUCT, PF PRODUCT
                //// _e
                if (uc_east & uc_north)
                begin
                    if (QBIDX == 3)
                    begin
                        dq_e = dq_e ^ dqmeas;
                        pf_e_zy = pf_e_zy ^ (pf == `PP_Z | pf == `PP_Y);
                        pf_e_xy = pf_e_xy ^ (pf == `PP_X | pf == `PP_Y);
                    end
                end
                else if (uc_east)
                begin
                    if (QBIDX == 1 | QBIDX == 3)
                    begin
                        dq_e = dq_e ^ dqmeas;
                        pf_e_zy = pf_e_zy ^ (pf == `PP_Z | pf == `PP_Y);
                        pf_e_xy = pf_e_xy ^ (pf == `PP_X | pf == `PP_Y);
                    end
                end
                //// _ne
                if (uc_east & uc_north)
                begin
                    if (QBIDX == 1)
                    begin
                        dq_ne = dqmeas;
                        pf_ne_xz = (pf == `PP_X | pf == `PP_Z);
                        pf_ne_xy = (pf == `PP_X | pf == `PP_Y);
                        pf_ne_zy = (pf == `PP_Z | pf == `PP_Y);
                    end
                end
                //// _w_bd
                if (uc_west & uc_north)
                begin
                    if (QBIDX == 3)
                    begin
                        dq_w_bd = dq_w_bd ^ dqmeas;
                        pf_w_bd_zy = pf_w_bd_zy ^ (pf == `PP_Z | pf == `PP_Y);
                        pf_w_bd_xy = pf_w_bd_xy ^ (pf == `PP_X | pf == `PP_Y);
                    end
                end
                else if (uc_west & ~uc_south)
                begin
                    if (QBIDX == 1 | QBIDX == 3)
                    begin
                        dq_w_bd = dq_w_bd ^ dqmeas;
                        pf_w_bd_zy = pf_w_bd_zy ^ (pf == `PP_Z | pf == `PP_Y);
                        pf_w_bd_xy = pf_w_bd_xy ^ (pf == `PP_X | pf == `PP_Y);
                    end
                end
                else if (uc_west)
                begin
                    if (QBIDX == 1)
                    begin
                        dq_w_bd = dq_w_bd ^ dqmeas;
                        pf_w_bd_zy = pf_w_bd_zy ^ (pf == `PP_Z | pf == `PP_Y);
                        pf_w_bd_xy = pf_w_bd_xy ^ (pf == `PP_X | pf == `PP_Y);
                    end
                end

                //// _s_bd
                if (uc_south & ~uc_west)
                begin
                    if (QBIDX == 2 | QBIDX == 3)
                    begin
                        dq_s_bd = dq_s_bd ^ dqmeas;
                        pf_s_bd_zy = pf_s_bd_zy ^ (pf == `PP_Z | pf == `PP_Y);
                        pf_s_bd_xy = pf_s_bd_xy ^ (pf == `PP_X | pf == `PP_Y);
                    end
                end
                
                //// _sw
                if (uc_south & uc_west)
                begin
                    if (QBIDX == 3)
                    begin
                        dq_sw = dqmeas;
                        pf_sw_zy = (pf == `PP_Z | pf == `PP_Y);
                        pf_sw_xy = (pf == `PP_X | pf == `PP_Y);
                    end
                end
               
                // AQMEAS PRODUCT
                ////
                if (QBIDX == 0 | QBIDX == 1)
                    even = 1;
                else
                    even = 0; // odd

                ////


                if (even) // even
                begin
                    aq_even_all = aq_even_all ^ aqmeas;
                    if (uc_west & QBIDX == 0)
                        aq_even_w = aq_even_w ^ aqmeas;
                    if (uc_east & QBIDX == 1)
                        aq_even_e = aq_even_e ^ aqmeas;
                end
                else // odd
                begin
                    aq_odd_all = aq_odd_all ^ aqmeas;
                    if (uc_west & QBIDX == 3)
                        aq_odd_w = aq_odd_w ^ aqmeas;
                    if (uc_east & QBIDX == 2)
                        aq_odd_e = aq_odd_e ^ aqmeas;
                    if (uc_south & QBIDX == 3)
                        aq_odd_s = aq_odd_s ^ aqmeas;
                end
            end
        end
    end



    /*** SELECT PRODUCT START ***/
    if (sel_dqaq == `SELDQAQ_DQ)
    begin
        aq_product = 0;
        
        // DQ PRODUCT, PF PRODUCT
        if (sel_loc == `SELLOC_E)
        begin
            dq_product = dq_e;
            pf_product = pf_e_zy;
        end
        else if (sel_loc == `SELLOC_NE)
        begin
            dq_product = dq_ne;
            pf_product = pf_ne_zy;
        end
        else if (sel_loc == `SELLOC_S)
        begin
            dq_product = dq_s;
            if (sel_xz == `SELXZ_X)
                pf_product = (pf_s_bd_zy ^ pf_sw_zy);
            else
                pf_product = (pf_s_bd_xy ^ pf_sw_xy);
        end
        else if (sel_loc == `SELLOC_W)
        begin
            dq_product = dq_w;
            if (sel_xz == `SELXZ_X)
                pf_product = (pf_w_bd_zy ^ pf_sw_zy);
            else
                pf_product = (pf_w_bd_xy ^ pf_sw_xy);
        end
        else if (sel_loc == `SELLOC_EXE)
        begin
            dq_product = dq_e_ex;
            if (sel_xz == `SELXZ_X)
                pf_product = (pf_ne_xz ^ pf_e_xy);
            else
                pf_product = (pf_ne_xy ^ pf_e_xy);
        end
        else if (sel_loc == `SELLOC_WS)
        begin
            dq_product = dq_w_s;
            pf_product = (pf_w_bd_xy ^ pf_s_bd_xy ^ pf_sw_xy);
        end
        else
        begin
            dq_product = 0;
            pf_product = 0;
        end
    end
    else // sel_dqaq == AQ
    begin
        dq_product = 0;

        // AQ PRODUCT, PF PRODUCT
        if (sel_loc == `SELLOC_E & sel_xz == `SELXZ_X & ~sel_reverse)
        begin
            aq_product = aq_even_e;
            pf_product = pf_e_zy;
        end
        else if (sel_loc == `SELLOC_EXE & sel_xz == `SELXZ_Z & ~sel_reverse)
        begin
            aq_product = aq_odd_e;
            pf_product = (pf_ne_xz ^ pf_e_xy);
        end
        else if (sel_loc == `SELLOC_W & sel_xz == `SELXZ_Z)
        begin
            if (sel_reverse)
            begin
                aq_product = aq_even_w;
                pf_product = (pf_w_bd_xy ^ pf_sw_xy);
            end
            else // ~sel_reverse
            begin
                aq_product = aq_odd_w;
                pf_product = (pf_w_bd_xy ^ pf_sw_xy);
            end
        end
        else if (sel_loc == `SELLOC_WINV & sel_xz == `SELXZ_Z)
        begin
            if (sel_reverse)
            begin
                aq_product = aq_even_winv;
                pf_product = (pf_w_bd_xy ^ pf_sw_xy);
            end
            else // ~sel_reverse
            begin
                aq_product = aq_odd_winv;
                pf_product = (pf_w_bd_xy ^ pf_sw_xy);
            end
        end
        else if (sel_loc == `SELLOC_SINV & sel_xz == `SELXZ_Z & ~sel_reverse)
        begin
            aq_product = aq_odd_sinv;
            pf_product = (pf_s_bd_xy ^ pf_sw_xy);
        end
        else if (sel_loc == `SELLOC_S & sel_xz == `SELXZ_Z & ~sel_reverse)
        begin
            aq_product = aq_odd_s;
            pf_product = (pf_s_bd_xy ^ pf_sw_xy);
        end

        else if (sel_loc == `SELLOC_ALL & sel_xz == `SELXZ_Z & ~sel_reverse)
        begin
            aq_product = aq_odd_all;
            pf_product = 0;
        end
        else
        begin
            aq_product = 0;
            pf_product = 0;
        end
    end
    /*** SELECT PRODUCT END ***/
end



endmodule
