`include "define.v"

module educell_decoder (
    my_rowidx,
    rst_cellstate,
    role,
    esm_exist,
    local_tokenmatch,
    possible_dir,
    curr_rowidx,
    flag_token,
    next_state,
    spike_dir
);
input [`TKROWADDR_BW-1:0] my_rowidx;
input rst_cellstate;
input [1:0] role;
input esm_exist;
input local_tokenmatch;
input [5:0] possible_dir;
input [`TKROWADDR_BW-1:0] curr_rowidx;
input flag_token;
output reg [2:0] next_state;
output reg [5:0] spike_dir;

// intermediate
reg [5:0] expected_dir; 
always @(*)
begin
    // next_state
    if (rst_cellstate)
        next_state = `EDUCELL_INACTIVE;
    else
    begin
        case(role)
            `ROLE_ACTIVE:
            begin
                if (local_tokenmatch)
                    next_state = `EDUCELL_SYNK;
                else if (esm_exist)
                    next_state = `EDUCELL_SOURCE;
                else
                    next_state = `EDUCELL_TRANSMIT;
            end
            `ROLE_BOUNDARY:
                next_state = `EDUCELL_BOUNDARY;
            `ROLE_INACTIVE:
                next_state = `EDUCELL_INACTIVE;
            default:
                next_state = `EDUCELL_INACTIVE;
        endcase
    end
    
    // spikedir
    //// expected_dir
    if (my_rowidx < curr_rowidx)
        expected_dir = {1'b0, 1'b0, 1'b0, 1'b1, 1'b0, 1'b0}; // se
    else if (my_rowidx > curr_rowidx)
        expected_dir = {1'b1, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0}; // nw
    else 
    begin
        if (flag_token)
            expected_dir = {1'b0, 1'b1, 1'b0, 1'b0, 1'b0, 1'b0}; // ne
        else
            expected_dir = {1'b0, 1'b0, 1'b1, 1'b0, 1'b0, 1'b0}; // sw
    end
    ////
    if ((expected_dir & possible_dir) != 0)
        spike_dir = expected_dir;
    else
    begin
        if (possible_dir[1] & (expected_dir[5] | expected_dir[4])) // N is possible
            spike_dir = {1'b0, 1'b0, 1'b0, 1'b0, 1'b1, 1'b0};
        else if (possible_dir[0] & (expected_dir[3] | expected_dir[2])) // S is possible
            spike_dir = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b1};
        else
            spike_dir = {1'b0, 1'b0, 1'b0, 1'b0, 1'b0, 1'b0};
    end
end

endmodule
