`include "define.v"

module piu_static_rom(
    rst,
    clk,
    pchidx,
    pchinfo_static
);

input rst, clk;
input [`PCHADDR_BW-1:0] pchidx;
output [`PCHSTAT_BW-1:0] pchinfo_static;

reg [`PCHSTAT_BW-1:0] regarray [`NUM_PCH-1:0];


assign pchinfo_static = regarray[pchidx];


reg [`PCHTYPE_BW-1:0] pchtype;
reg [`BDLOC_BW-1:0] z_bd, x_bd;
integer I;
integer PCHROW, PCHCOL;

always @(posedge clk)
begin
    if (rst)
    begin
        for (I = 0; I < `NUM_PCH; I = I+1)
        begin
            PCHROW = I / `NUM_PCHCOL;
            PCHCOL = I % `NUM_PCHCOL;

            if (PCHROW == 0 & PCHCOL == 0) // ZT
            begin
                pchtype = `PCHTYPE_ZT;
                z_bd = `BDLOC_I;
                x_bd = `BDLOC_E;
            end
            else if (PCHROW == 1 & PCHCOL == 0) // ZB
            begin 
                pchtype = `PCHTYPE_ZB;
                z_bd = `BDLOC_E;
                x_bd = `BDLOC_I;
            end
            else if (PCHROW == 0 & PCHCOL == 1) // MT
            begin
                pchtype = `PCHTYPE_MT;
                z_bd = `BDLOC_W;
                x_bd = `BDLOC_I;
            end
            else if (PCHROW == 1 & PCHCOL == 1) // MB
            begin
                pchtype = `PCHTYPE_MB;
                z_bd = `BDLOC_WE;
                x_bd = `BDLOC_I;
            end
            else if (PCHROW == 0 & PCHCOL != `NUM_PCHCOL-1) // M-N
            begin
                pchtype = `PCHTYPE_M;
                z_bd = `BDLOC_S;
                x_bd = `BDLOC_I;
            end
            else if (PCHROW == 2 & (PCHCOL != 0 & PCHCOL != 1 & PCHCOL != `NUM_PCHCOL-1))
            begin // M-S
                pchtype = `PCHTYPE_M;
                z_bd = `BDLOC_N;
                x_bd = `BDLOC_I;
            end
            else if (PCHROW == 1 & PCHCOL == `NUM_PCHCOL-1) // X
            begin
                pchtype = `PCHTYPE_X;
                z_bd = `BDLOC_W;
                x_bd = `BDLOC_I;
            end
            else if (PCHROW == 1 & (PCHCOL == 2 & PCHCOL == `NUM_PCHCOL-2)) // AWE
            begin
                pchtype = `PCHTYPE_AWE;
                z_bd = `BDLOC_I;
                x_bd = `BDLOC_I;
            end
            else if (PCHROW == 1 & PCHCOL == 2)
            begin // AW
                pchtype = `PCHTYPE_AW;
                z_bd = `BDLOC_I;
                x_bd = `BDLOC_I;
            end
            else if (PCHROW == 1 & PCHCOL == `NUM_PCHCOL-2)
            begin // AE
                pchtype = `PCHTYPE_AE;
                z_bd = `BDLOC_I;
                x_bd = `BDLOC_I;
            end
            else if (PCHROW == 1)
            begin // AC
                pchtype = `PCHTYPE_AC;
                z_bd = `BDLOC_I;
                x_bd = `BDLOC_I;
            end
            else // I
            begin
                pchtype = `PCHTYPE_I;
                z_bd = `BDLOC_I;
                x_bd = `BDLOC_I;
            end
            regarray[I] <= {pchtype, z_bd, x_bd};
        end
    end
end

endmodule
