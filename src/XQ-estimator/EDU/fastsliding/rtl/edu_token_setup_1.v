`include "define.v"

module edu_token_setup_1(
    token_exist_rows_0_reg,
    token_exist_rows_1,
    token_exist_1,
    token_row_1
);

input [(2*`NUM_UCROW+2*`NUM_UCCOL-1)+1:0] token_exist_rows_0_reg;
output reg [(2*`NUM_UCROW+2*`NUM_UCCOL-1)-1:0] token_exist_rows_1;
output reg token_exist_1;
output reg [`log2(`NUM_UCROW)+1:0] token_row_1;

integer I;
always @(*) 
begin
    token_exist_rows_1 = 0;
    token_exist_1 = 0;
    token_row_1 = 0;

    for (I = 0; I < `NUM_AQROW+`NUM_AQCOL-1; I = I+1)
    begin
        if (token_exist_rows_0_reg[I] & ~token_exist_1)
        begin
            token_exist_rows_1[I] = 1;
            token_exist_1 = 1;
            token_row_1 = $unsigned(I);
        end
    end
end

endmodule
