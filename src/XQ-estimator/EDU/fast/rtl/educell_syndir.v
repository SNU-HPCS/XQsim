`include "define.v"


module educell_syndir(
    spike_in_nw,
    spike_in_ne, 
    spike_in_sw,
    spike_in_se, 
    spike_in_n,
    spike_in_s,
    syndir
);

input spike_in_nw;
input spike_in_ne;
input spike_in_sw;
input spike_in_se;
input spike_in_n;
input spike_in_s;
output reg [5:0] syndir;

always @(*)
begin
    if (spike_in_s)
        syndir = 6'b000001;
    else if (spike_in_n)
        syndir = 6'b000010;
    else if (spike_in_se)
        syndir = 6'b000100;
    else if (spike_in_sw)
        syndir = 6'b001000;
    else if (spike_in_ne)
        syndir = 6'b010000;
    else if (spike_in_nw)
        syndir = 6'b100000;
    else
        syndir = 6'b000000;
end

endmodule
