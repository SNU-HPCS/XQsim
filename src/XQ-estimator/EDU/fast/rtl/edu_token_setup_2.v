`include "define.v"


module edu_token_setup_2(
    token_exist_row_1_reg,
    token_col_row_1_reg,
    token_set_row_2,
    flag_set_row_2
);

input token_exist_row_1_reg;
input [`AQROWADDR_BW-1:0] token_col_row_1_reg;
output reg [`NUM_AQROW-1:0] token_set_row_2;
output reg [`NUM_AQROW-1:0] flag_set_row_2;

integer I;
always @(*)
begin
    if (token_exist_row_1_reg)
    begin
        token_set_row_2 = 0;
        token_set_row_2[token_col_row_1_reg] = 1;

        flag_set_row_2 = 0;
        for (I = 0; $unsigned(I) <= token_col_row_1_reg; I = I+1)
        begin
            flag_set_row_2[I] = 1;
        end
    end
    else
    begin
        token_set_row_2 = 0;
        flag_set_row_2 = 0;
    end
end

endmodule
