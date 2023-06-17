`include "define.v"

module educell_spikegen(
    state,
    delayed_esmval, 
    delayed_bdval, 
    spike_taken, 
    spikedir_reg,
    spike_out_nw,
    spike_out_ne, 
    spike_out_sw,
    spike_out_se,
    spike_out_n,
    spike_out_s
);

input [2:0] state;
input [`AQMEAS_TH-1:0] delayed_esmval; 
input delayed_bdval; 
input spike_taken; 
input [5:0] spikedir_reg; 
output reg spike_out_nw;
output reg spike_out_ne; 
output reg spike_out_sw;
output reg spike_out_se;
output reg spike_out_n;
output reg spike_out_s;

reg spike_out;

/*** WIRE TRANSFER (COMBINATIONAL LOGIC) ***/
always @(*)
begin
    // spike_out generation
    if (state == `EDUCELL_SOURCE)
        spike_out = (|delayed_esmval);
    else if (state == `EDUCELL_BOUNDARY)
        spike_out = delayed_bdval;
    else if (state == `EDUCELL_TRANSMIT)
        spike_out = spike_taken;
    else
        spike_out = 0;
    // spike_out forwarding
    spike_out_nw = (spike_out & spikedir_reg[5]);
    spike_out_ne = (spike_out & spikedir_reg[4]);
    spike_out_sw = (spike_out & spikedir_reg[3]);
    spike_out_se = (spike_out & spikedir_reg[2]);
    spike_out_n = (spike_out & spikedir_reg[1]);
    spike_out_s = (spike_out & spikedir_reg[0]);

end

endmodule
