`include "define.v"

module pfu_pfupdater(
    mgdcwd,
    error, 
    sel_cwd_err,
    pf,
    newpf
);

input [`CWD_BW-1:0] mgdcwd;
input [1:0] error;
input sel_cwd_err;
input [1:0] pf;
output reg [1:0] newpf;

reg [`CWD_BW-1:0] cwd_to_pf;

always @(*)
begin
    if (sel_cwd_err == `SELCWDERR_CWD)
        cwd_to_pf = mgdcwd;
    else // SELCWDERR_ERR
        cwd_to_pf = error;

    if (cwd_to_pf == `CWD_I | cwd_to_pf == `CWD_X | cwd_to_pf == `CWD_Z | cwd_to_pf == `CWD_Y)
        newpf = cwd_to_pf[1:0] ^ pf;
    else if (cwd_to_pf == `CWD_H)
    begin
        if (pf == `PP_X)
            newpf = `PP_Z;
        else if (pf == `PP_Z)
            newpf = `PP_X;
        else
            newpf = pf;
    end
    else if (cwd_to_pf == `CWD_CX)
        newpf = `CWD_I;
    else
        newpf = pf;
end

endmodule
