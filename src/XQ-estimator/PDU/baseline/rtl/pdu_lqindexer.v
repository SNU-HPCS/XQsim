`include "define.v"

module pdu_lqindexer(
    lqlist_reg,
    lqidx,
    next_lqlist
);

input [`NUM_LQ-1:0] lqlist_reg;
output reg [`LQADDR_BW-1:0] lqidx;
output reg [`NUM_LQ-1:0] next_lqlist;

reg taken; 
integer I;

always @(*)
begin
    taken = 0;
    lqidx = 0;
    for (I = 0; I < `NUM_LQ; I = I+1)
    begin
        if ((~taken) & lqlist_reg[I])
        begin
            lqidx = $unsigned(I);
            taken = 1;
        end
    end
    
    next_lqlist = lqlist_reg;
    next_lqlist[lqidx] = 0;
end

endmodule
