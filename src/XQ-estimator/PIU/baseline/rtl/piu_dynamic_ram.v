`include "define.v"

module piu_dynamic_ram(
    rst, 
    clk,
    prep_dyninfo,
    split_dyninfo,
    is_writing, 
    wr_facebd,
    wr_cornerbd,
    pchidx,
    pchinfo_dynamic
);

input rst, clk;
input prep_dyninfo, split_dyninfo;
input is_writing;
input [4*`FACEBD_BW-1:0] wr_facebd;
input [4*`CORNERBD_BW-1:0] wr_cornerbd;
input [`PCHADDR_BW-1:0] pchidx;
output [`PCHDYN_BW-1:0] pchinfo_dynamic;

reg [`PCHDYN_BW-1:0] regarray [`NUM_PCH-1:0];
assign pchinfo_dynamic = regarray[pchidx];

reg [4*`FACEBD_BW-1:0] facebd;
reg [4*`CORNERBD_BW-1:0] cornerbd;

integer I;
integer PCHROW, PCHCOL;

always @(posedge clk)
begin
    if (rst)
    begin
        for (I = 0; I < `NUM_PCH; I = I+1)
            regarray[I] <= 0;
    end
    else if (prep_dyninfo | split_dyninfo)
    begin
        for (I = 0; I < `NUM_PCH; I = I+1)
        begin
            PCHROW = I / `NUM_PCHCOL;
            PCHCOL = I % `NUM_PCHCOL;

            if (PCHROW == 0 & PCHCOL == 0) // ZT
            begin
                facebd = {`FACEBD_X, `FACEBD_X, `FACEBD_Z, `FACEBD_PP};
                cornerbd = {`CORNERBD_C, `CORNERBD_I, `CORNERBD_I, `CORNERBD_I};
            end
            else if (PCHROW == 1 & PCHCOL == 0) // ZB
            begin
                // facebd = {`FACEBD_Z, `FACEBD_PP, `FACEBD_X, `FACEBD_PP};
                facebd = {`FACEBD_Z, `FACEBD_PP, `FACEBD_X, `FACEBD_Z};
                cornerbd = {`CORNERBD_I, `CORNERBD_I, `CORNERBD_C, `CORNERBD_I};
            end
            else if (PCHROW == 0 & PCHCOL == 1) // MT
            begin
                if (prep_dyninfo)
                    facebd = {`FACEBD_I, `FACEBD_I, `FACEBD_I, `FACEBD_I};
                else // split_dyninfo
                    facebd = {`FACEBD_X, `FACEBD_Z, `FACEBD_Z, `FACEBD_LP};
                cornerbd = {`CORNERBD_I, `CORNERBD_I, `CORNERBD_I, `CORNERBD_I};
            end
            else if (PCHROW == 1 & PCHCOL == 1) // MB
            begin
                if (prep_dyninfo)
                    facebd = {`FACEBD_X, `FACEBD_Z, `FACEBD_X, `FACEBD_Z};
                else // split_dyninfo
                    facebd = {`FACEBD_X, `FACEBD_LP, `FACEBD_X, `FACEBD_Z};
                cornerbd = {`CORNERBD_I, `CORNERBD_I, `CORNERBD_I, `CORNERBD_I};
            end
            else if ((PCHROW == 0 & PCHCOL != `NUM_PCHCOL-1) | (PCHROW == 2 & (PCHCOL != 0 & PCHCOL != 1 & PCHCOL != `NUM_PCHCOL-1))) // M
            begin
                facebd = {`FACEBD_Z, `FACEBD_X, `FACEBD_Z, `FACEBD_X};
                cornerbd = {`CORNERBD_I, `CORNERBD_I, `CORNERBD_I, `CORNERBD_I};
            end
            else if (PCHROW == 1 & PCHCOL == `NUM_PCHCOL-1) // X
            begin
                facebd = {`FACEBD_X, `FACEBD_Z, `FACEBD_X, `FACEBD_Z};
                cornerbd = {`CORNERBD_I, `CORNERBD_I, `CORNERBD_I, `CORNERBD_I};
            end
            else // AW/AE/AC/AWE/I
            begin
                facebd = {`FACEBD_I, `FACEBD_I, `FACEBD_I, `FACEBD_I};
                cornerbd = {`CORNERBD_I, `CORNERBD_I, `CORNERBD_I, `CORNERBD_I};
            end
            regarray[I] <= {facebd, cornerbd};
        end
    end
    else if (is_writing)
    begin
        regarray[pchidx] <= {wr_facebd, wr_cornerbd}; 
    end
end

endmodule
