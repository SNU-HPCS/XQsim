`include "define.v"


module edu_token_setup_3(
    token_exist_1_reg,
    token_row_1_reg,
    token_valid_1_reg,
    last_token,
    next_rowidx,
    token_match
);

input token_exist_1_reg;
input [`TKROWADDR_BW-1:0] token_row_1_reg;
input token_valid_1_reg;
output reg last_token;
output reg [`TKROWADDR_BW-1:0] next_rowidx;
output reg token_match;

always @(*)
begin
    if (token_valid_1_reg)
    begin
        last_token = ~token_exist_1_reg;
        next_rowidx = token_row_1_reg;
        token_match = token_exist_1_reg;
    end
    else
    begin
        last_token = 0;
        next_rowidx = 0;
        token_match = 0;
    end
end

endmodule
