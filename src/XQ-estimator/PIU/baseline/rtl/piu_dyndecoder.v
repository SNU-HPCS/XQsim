`include "define.v"

module piu_dyndecoder(
    pchinfo_static, 
    pchidx, 
    pchpp_list_reg0, 
    pchpp_list_reg1,
    wr_facebd,
    wr_cornerbd
);

input [`PCHADDR_BW-1:0] pchidx;
input [`PCHSTAT_BW-1:0] pchinfo_static;
input [`NUM_PCH*2-1:0] pchpp_list_reg0, pchpp_list_reg1;
output [4*`FACEBD_BW-1:0] wr_facebd;
output [4*`CORNERBD_BW-1:0] wr_cornerbd;

wire [`PCHTYPE_BW-1:0] pchtype;
wire [`BDLOC_BW-1:0] z_bd, x_bd;
reg [1:0] pchpp_list [`NUM_PCH-1:0];
reg [1:0] north_pp, east_pp, south_pp;
reg [`FACEBD_BW-1:0] facebd_w, facebd_n, facebd_e, facebd_s;
reg [`CORNERBD_BW-1:0] cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se;

assign {pchtype, z_bd, x_bd} = pchinfo_static;
assign wr_facebd = {facebd_w, facebd_n, facebd_e, facebd_s};
assign wr_cornerbd = {cornerbd_nw, cornerbd_ne, cornerbd_sw, cornerbd_se};

integer I;
integer PCHROW, PCHCOL;
wire signed [`PCHADDR_BW:0] pchidx_s = $signed({1'b0, pchidx});

always @(pchpp_list_reg0, pchpp_list_reg1, pchidx)
begin
    // merge pchpp_list
    for (I = 0; I < `NUM_PCH; I = I+1)
        pchpp_list[I] = pchpp_list_reg0[I*2 +: 2] | pchpp_list_reg1[I*2 +: 2];
    // get north/east/south_pp
    PCHROW = (pchidx_s) / (`NUM_PCHCOL);
    PCHCOL = (pchidx_s) % (`NUM_PCHCOL);
    if (PCHROW != 0)
        north_pp = pchpp_list[pchidx_s - `NUM_PCHCOL];
    else
        north_pp = `PP_I;
    if (PCHCOL != `NUM_PCHCOL-1)
        east_pp = pchpp_list[pchidx_s + 1];
    else
        east_pp = `PP_I;
    if (PCHROW != `NUM_PCHROW-1)
        south_pp = pchpp_list[pchidx_s + `NUM_PCHCOL];
    else
        south_pp = `PP_I;
end

always @(*)
begin
    // generate wr_facebd
    // generate wr_cornerbd
    case (pchtype)
        `PCHTYPE_ZT:
        begin
            facebd_w = `FACEBD_X;
            facebd_n = `FACEBD_X;
            facebd_e = `FACEBD_MP;
            facebd_s = `FACEBD_PP;
            cornerbd_nw = `CORNERBD_C;
            cornerbd_ne = `CORNERBD_I;
            cornerbd_sw = `CORNERBD_I;
            cornerbd_se = `CORNERBD_I;
        end
        `PCHTYPE_ZB:
        begin
            facebd_w = `FACEBD_Z;
            facebd_n = `FACEBD_PP;
            facebd_e = `FACEBD_PP;
            facebd_s = `FACEBD_Z;
            cornerbd_nw = `CORNERBD_I;
            cornerbd_ne = `CORNERBD_Y;
            cornerbd_sw = `CORNERBD_C;
            cornerbd_se = `CORNERBD_I;
        end
        `PCHTYPE_MT:
        begin
            facebd_w = `FACEBD_MP;
            facebd_n = `FACEBD_Z;
            facebd_e = `FACEBD_Z;
            facebd_s = `FACEBD_LP;
            cornerbd_nw = `CORNERBD_I;
            cornerbd_ne = `CORNERBD_I;
            cornerbd_sw = `CORNERBD_I;
            cornerbd_se = `CORNERBD_Z;
        end
        `PCHTYPE_MB:
        begin
            facebd_w = `FACEBD_PP;
            facebd_n = `FACEBD_LP;
            facebd_e = `FACEBD_PP;
            facebd_s = `FACEBD_Z;
            cornerbd_nw = `CORNERBD_YE;
            cornerbd_ne = `CORNERBD_I;
            cornerbd_sw = `CORNERBD_I;
            cornerbd_se = `CORNERBD_I;
        end
        `PCHTYPE_M:
        begin
            if (z_bd == `BDLOC_S)
            begin
                facebd_w = `FACEBD_Z;
                facebd_n = `FACEBD_X;
                facebd_e = `FACEBD_Z;
                facebd_s = `FACEBD_PP;
                cornerbd_nw = `CORNERBD_I;
                cornerbd_ne = `CORNERBD_I;
                cornerbd_sw = `CORNERBD_I;
                cornerbd_se = `CORNERBD_I;
            end
            else // z_bd == `BDLOC_N
            begin
                facebd_w = `FACEBD_Z;
                facebd_n = `FACEBD_PP;
                facebd_e = `FACEBD_Z;
                facebd_s = `FACEBD_X;
                cornerbd_nw = `CORNERBD_Z;
                cornerbd_ne = `CORNERBD_I;
                cornerbd_sw = `CORNERBD_I;
                cornerbd_se = `CORNERBD_I;
            end
        end
        `PCHTYPE_X:
        begin
            facebd_w = `FACEBD_PP;
            facebd_n = `FACEBD_Z;
            facebd_e = `FACEBD_X;
            facebd_s = `FACEBD_Z;
            cornerbd_nw = `CORNERBD_I;
            cornerbd_ne = `CORNERBD_I;
            cornerbd_sw = `CORNERBD_I;
            cornerbd_se = `CORNERBD_I;
        end
        `PCHTYPE_AW:
        begin
            facebd_w = `FACEBD_PP;
            if (north_pp == `PP_Z)
            begin
                facebd_n = `FACEBD_PP;
                cornerbd_nw = `CORNERBD_ZE;
            end
            else
            begin
                facebd_n = `FACEBD_Z;
                cornerbd_nw = `CORNERBD_IE;
            end

            facebd_e = `FACEBD_PP;

            if (south_pp == `PP_Z)
                facebd_s = `FACEBD_PP;
            else
                facebd_s = `FACEBD_Z;
            cornerbd_ne = `CORNERBD_I;
            cornerbd_sw = `CORNERBD_I;
            cornerbd_se = `CORNERBD_I;
        end
        `PCHTYPE_AE:
        begin
            facebd_w = `FACEBD_PP;
            if (north_pp == `PP_Z)
            begin
                facebd_n = `FACEBD_PP;
                cornerbd_nw = `CORNERBD_Z;
            end
            else
            begin
                facebd_n = `FACEBD_Z;
                cornerbd_nw = `CORNERBD_I;
            end
            if (east_pp == `PP_Z)
                facebd_e = `FACEBD_PP;
            else
                facebd_e = `FACEBD_Z;
            if (south_pp == `PP_Z)
                facebd_s = `FACEBD_PP;
            else
                facebd_s = `FACEBD_Z;
            cornerbd_ne = `CORNERBD_I;
            cornerbd_sw = `CORNERBD_I;
            cornerbd_se = `CORNERBD_I;
        end
        `PCHTYPE_AC:
        begin
            facebd_w = `FACEBD_PP;
            if (north_pp == `PP_Z)
            begin
                facebd_n = `FACEBD_PP;
                cornerbd_nw = `CORNERBD_Z;
            end
            else
            begin
                facebd_n = `FACEBD_Z;
                cornerbd_nw = `CORNERBD_Z;
            end
            facebd_e = `FACEBD_PP;
            if (south_pp == `PP_Z)
                facebd_s = `FACEBD_PP;
            else
                facebd_s = `FACEBD_Z;
            cornerbd_ne = `CORNERBD_I;
            cornerbd_sw = `CORNERBD_I;
            cornerbd_se = `CORNERBD_I;
        end
        `PCHTYPE_AWE:
        begin
            facebd_w = `FACEBD_PP;
            if (north_pp == `PP_Z)
            begin
                facebd_n = `FACEBD_PP;
                cornerbd_nw = `CORNERBD_ZE;
            end
            else
            begin
                facebd_n = `FACEBD_Z;
                cornerbd_nw = `CORNERBD_IE;
            end
            if (east_pp == `PP_Z)
                facebd_e = `FACEBD_PP;
            else
                facebd_e = `FACEBD_Z;
            if (south_pp == `PP_Z)
                facebd_s = `FACEBD_PP;
            else
                facebd_s = `FACEBD_Z;
            cornerbd_ne = `CORNERBD_I;
            cornerbd_sw = `CORNERBD_I;
            cornerbd_se = `CORNERBD_I;
        end
        default:
        begin
            facebd_w = `FACEBD_I;
            facebd_n = `FACEBD_I;
            facebd_e = `FACEBD_I;
            facebd_s = `FACEBD_I;
            cornerbd_nw = `CORNERBD_I;
            cornerbd_ne = `CORNERBD_I;
            cornerbd_sw = `CORNERBD_I;
            cornerbd_se = `CORNERBD_I;
        end
    endcase
end

endmodule
