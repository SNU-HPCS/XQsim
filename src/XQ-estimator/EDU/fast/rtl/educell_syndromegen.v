`include "define.v"

module educell_syndromegen(
    state,
    syndrome_taken,
    spike_taken,
    syndir_reg,
    syn_to_west,
    syn_to_east,
    syndrome_out_nw,
    syndrome_out_ne,
    syndrome_out_sw,
    syndrome_out_se,
    syndrome_out_n,
    syndrome_out_s
);

input [2:0] state;
input syndrome_taken;
input spike_taken;
input [5:0] syndir_reg;
input [1:0] syn_to_west;
input [1:0] syn_to_east;
output reg [1:0] syndrome_out_nw;
output reg [1:0] syndrome_out_ne;
output reg [1:0] syndrome_out_sw;
output reg [1:0] syndrome_out_se;
output reg [1:0] syndrome_out_n;
output reg [1:0] syndrome_out_s;

reg [1:0] syndrome_out;

always @(*)
begin
    if (syndrome_taken & spike_taken)
    begin
        if (state == `EDUCELL_SOURCE | state == `EDUCELL_BOUNDARY)
            syndrome_out = `PP_I;
        else if (syndir_reg[5] | syndir_reg[3]) // w
            syndrome_out = syn_to_west;
        else if (syndir_reg[4] | syndir_reg[2]) //e
            syndrome_out = syn_to_east;
        else if (syndir_reg[1] | syndir_reg[0])
            syndrome_out = `PP_Z; // don't care
        else
            syndrome_out = `PP_I;
    end
    else
        syndrome_out = `PP_I;

    syndrome_out_nw = (syndrome_out & {2{syndir_reg[5]}});
    syndrome_out_ne = (syndrome_out & {2{syndir_reg[4]}});
    syndrome_out_sw = (syndrome_out & {2{syndir_reg[3]}});
    syndrome_out_se = (syndrome_out & {2{syndir_reg[2]}});
    syndrome_out_n = (syndrome_out & {2{syndir_reg[1]}});
    syndrome_out_s = (syndrome_out & {2{syndir_reg[0]}});

end

endmodule
