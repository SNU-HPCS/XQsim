`include "define.v"

module edu_token_setup_0(
    esmhead_row,
    flag_out_row, 
    token_exist_row_0,
    token_col_row_0
);

input [`NUM_UCROW*2-1:0] esmhead_row;
input [`NUM_UCROW*2-1:0] flag_out_row;
output reg token_exist_row_0;
output reg [`log2(`NUM_UCROW):0] token_col_row_0;

wire [`NUM_UCROW*2-1:0] syndrome_row;
assign syndrome_row = (esmhead_row & ~flag_out_row);

integer I;

always @(*)
begin
    token_exist_row_0 = 0;
    token_col_row_0 = 0;
    for (I = 0; I < `NUM_UCROW*2; I = I+1)
    begin
        if (syndrome_row[I] & ~token_exist_row_0)
        begin
            token_exist_row_0 = 1;
            token_col_row_0 = $unsigned(I);
        end
    end
end

endmodule
