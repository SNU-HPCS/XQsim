`include "define.v"

module edu_nexterr(
    err_nw,
    err_ne,
    err_sw,
    err_se,
    curr_err,
    next_err
);

input [1:0] err_nw;
input [1:0] err_ne;
input [1:0] err_sw;
input [1:0] err_se;
input [1:0] curr_err;
output [1:0] next_err;

assign next_err = (err_nw ^ err_ne ^ err_sw ^ err_se ^ curr_err);

endmodule
