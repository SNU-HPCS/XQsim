`include "define.v"

// RR
module edu_token_setup(
    first_token,
    token_out_array,
    curr_rowidx_reg,
    token_set_array,
    flag_set_array,
    last_token,
    next_rowidx
);

input first_token;
input [`NUM_AQ-1:0] token_out_array;
input [`TKROWADDR_BW-1:0] curr_rowidx_reg;
output reg [`NUM_AQ-1:0] token_set_array;
output reg [`NUM_AQ-1:0] flag_set_array;
output reg last_token;
output reg [`TKROWADDR_BW-1:0] next_rowidx;

integer I, J;
reg [`NUM_AQROW+`NUM_AQCOL-2:0] row_tokens_out;

always @(*)
begin
    // 
    for (I = 0; I < `NUM_AQROW; I = I+1)
    begin
        for (J = 0; J < `NUM_AQCOL; J = J+1)
        begin
            if (I == 0 | J == `NUM_AQCOL-1)
                row_tokens_out[I+J] = token_out_array[I*`NUM_AQCOL+J];
        end
    end

    //
    token_set_array = 0;
    flag_set_array = 0;
    for (I = 0; I < `NUM_AQROW; I = I+1)
    begin
        for (J = 0; J < `NUM_AQCOL; J = J+1)
        begin
            if (J == 0 | I == `NUM_AQROW-1)
            begin
                if (I == 0)
                begin
                    token_set_array[I*`NUM_AQCOL+J] = first_token;
                    flag_set_array[I*`NUM_AQCOL+J] = first_token;
                end
                else
                begin
                    token_set_array[I*`NUM_AQCOL+J] = row_tokens_out[I+J-1];
                    flag_set_array[I*`NUM_AQCOL+J] = row_tokens_out[I+J-1];
                end
            end
            else
            begin
                token_set_array[I*`NUM_AQCOL+J] = token_out_array[(I+1)*`NUM_AQCOL + (J-1)];
                flag_set_array[I*`NUM_AQCOL+J] = token_out_array[(I+1)*`NUM_AQCOL + (J-1)];
            end
        end
    end

    //
    last_token = token_out_array[`NUM_AQ-1];

    //
    next_rowidx = curr_rowidx_reg;
    for (I = 0; I < `NUM_AQROW+`NUM_AQCOL-1; I = I+1)
    begin
        if (row_tokens_out[I])
        begin
            next_rowidx = I+1;
        end
    end
end

endmodule
