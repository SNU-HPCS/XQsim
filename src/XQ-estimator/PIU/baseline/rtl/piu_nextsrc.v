`include "define.v"

module piu_nextsrc(
    pch_list,
    take_in,
    prep_dyninfo,
    split_dyninfo,
    set_merged, 
    copy_merged, 
    sel_pchidxsrc,
    next_pchidxsrc,
    merged_mem, 
    next_pchlist, 
    next_esmon,
    next_merged
);

input [`NUM_PCH-1:0] pch_list;
input take_in;
input prep_dyninfo;
input split_dyninfo;
input set_merged;
input copy_merged;
input [1:0] sel_pchidxsrc;
input [`NUM_PCH-1:0] next_pchidxsrc;
input [`NUM_PCH-1:0] merged_mem;
output reg [`NUM_PCH-1:0] next_pchlist;
output reg [`NUM_PCH-1:0] next_esmon;
output reg [`NUM_PCH-1:0] next_merged;

integer PCHROW_ESMON, PCHCOL_ESMON;
integer PCHROW_MERGED, PCHCOL_MERGED;
integer I;

always @(*)
begin
    // next_pchlist
    if (take_in)
        next_pchlist = pch_list;
    else if (sel_pchidxsrc == `PCHIDXSRC_PCHLIST)
        next_pchlist = next_pchidxsrc;
    else
        next_pchlist = 0;

    // next_esmon 
    if (prep_dyninfo | split_dyninfo)
    begin
        for (I = 0; I < `NUM_PCH; I = I+1)
        begin
            PCHROW_ESMON = (I) / (`NUM_PCHCOL);
            PCHCOL_ESMON = (I) % (`NUM_PCHCOL);
            if (PCHROW_ESMON == 0 & PCHCOL_ESMON != `NUM_PCHCOL-1)
            begin
                if (I == 1 & prep_dyninfo)
                    next_esmon[I] = 0;
                else
                    next_esmon[I] = 1;
            end
            else if (PCHROW_ESMON == 1 & (PCHCOL_ESMON == 0 | PCHCOL_ESMON == 1 | PCHCOL_ESMON == `NUM_PCHCOL-1))
                next_esmon[I] = 1;
            else if (PCHROW_ESMON == 2 & (PCHCOL_ESMON != 0 & PCHCOL_ESMON != 1 & PCHCOL_ESMON != `NUM_PCHCOL-1))
                next_esmon[I] = 1;
            else
                next_esmon[I] = 0;
        end
    end
    else if (set_merged)
    begin
        for (I = 0; I < `NUM_PCH; I = I+1)
        begin
            PCHROW_ESMON = (I) / (`NUM_PCHCOL);
            PCHCOL_ESMON = (I) % (`NUM_PCHCOL);
            if (PCHROW_ESMON == 0 & PCHCOL_ESMON != `NUM_PCHCOL-1)
                next_esmon[I] = 1;
            else if (PCHROW_ESMON == 1)
                next_esmon[I] = 1;
            else if (PCHROW_ESMON == 2 & (PCHCOL_ESMON != 0 & PCHCOL_ESMON != 1 & PCHCOL_ESMON != `NUM_PCHCOL-1))
                next_esmon[I] = 1;
            else
                next_esmon[I] = 0;
        end
    end
    else if (sel_pchidxsrc == `PCHIDXSRC_ESMON)
        next_esmon = next_pchidxsrc;
    else
        next_esmon = 0;

    // next_merged
    if (set_merged)
    begin
        for (I = 0; I < `NUM_PCH; I = I+1)
        begin
            PCHROW_MERGED = (I) / (`NUM_PCHCOL);
            PCHCOL_MERGED = (I) % (`NUM_PCHCOL);
            if (PCHROW_MERGED == 1 & (PCHCOL_MERGED != 0 & PCHCOL_MERGED != 1 & PCHCOL_MERGED != `NUM_PCHCOL-1))
                next_merged[I] = 1;
            else
                next_merged[I] = pch_list[I];
        end
    end
    else if (copy_merged)
        next_merged = merged_mem;
    else if (sel_pchidxsrc == `PCHIDXSRC_MERGED)
        next_merged = next_pchidxsrc;
    else
        next_merged = 0;
end


endmodule
