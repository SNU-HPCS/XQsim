`include "define.v"

module piu_pchindexer(
    sel_pchidxsrc,
    pch_list_reg,
    esmon_reg,
    merged_reg,
    pchidx,
    next_pchidxsrc
);

input [1:0] sel_pchidxsrc;
input [`NUM_PCH-1:0] pch_list_reg;
input [`NUM_PCH-1:0] esmon_reg;
input [`NUM_PCH-1:0] merged_reg;
output reg [`PCHADDR_BW-1:0] pchidx;
output reg [`NUM_PCH-1:0] next_pchidxsrc;

reg [`NUM_PCH-1:0] pchidxsrc;
reg taken;
integer I;

always @(*)
begin
    case(sel_pchidxsrc)
        `PCHIDXSRC_PCHLIST:
            pchidxsrc = pch_list_reg;
        `PCHIDXSRC_ESMON:
            pchidxsrc = esmon_reg;
        `PCHIDXSRC_MERGED:
            pchidxsrc = merged_reg;
        default:
            pchidxsrc = 0;
    endcase

    taken = 0;
    pchidx = 0;
    for (I = 0; I < `NUM_PCH; I = I+1)
    begin
        if ((~taken) & pchidxsrc[I])
        begin
            pchidx = $unsigned(I);
            taken = 1;
        end
    end

    for (I = 0; I < `NUM_PCH; I = I+1)
    begin
        if ($unsigned(I) == pchidx)
            next_pchidxsrc[I] = 0;
        else
            next_pchidxsrc[I] = pchidxsrc[I];
    end
end

endmodule
