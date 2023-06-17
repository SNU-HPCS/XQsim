`include "define.v"

module mux #(
    parameter NUM_DATA = {}, 
    parameter DATA_BW = {}
)(
    data_in, 
    sel,
    data_out
);

parameter SEL_WIDTH = `log2(NUM_DATA);

input [DATA_BW*NUM_DATA-1:0] data_in;
input [SEL_WIDTH-1:0] sel;
output [DATA_BW-1:0] data_out;

assign data_out = data_in[sel*DATA_BW +: DATA_BW];

endmodule
