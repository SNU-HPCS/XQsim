`include "define.v"

module psu_cwdarrgen(
    mask_ext_array,
    special_ext_array,
    cwd,
    cwdsp,
    cwdarray
);

input [`NUM_PQ-1:0] mask_ext_array;
input [`NUM_PQ-1:0] special_ext_array;
input [`CWD_BW-1:0] cwd;
input [`CWD_BW-1:0] cwdsp;
output reg [`NUM_PQ*`CWD_BW-1:0] cwdarray;

reg [`CWD_BW-1:0] final_cwd;

integer I;
always @(*)
begin
    for (I = 0; I < `NUM_PQ; I = I+1)
    begin
        if (special_ext_array[I])
            final_cwd = cwdsp;
        else
            final_cwd = cwd;

        if (mask_ext_array[I])
            cwdarray[I*`CWD_BW +: `CWD_BW] = final_cwd;
        else
            cwdarray[I*`CWD_BW +: `CWD_BW] = `CWD_I;
    end
end

endmodule
