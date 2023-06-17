`include "define.v"

module qid_decoder (
    temp_opcode,
    instbuf_empty,
    measfb_xorz,
    opcode,
    a_taken
);

input [`OPCODE_BW-1:0] temp_opcode;
input instbuf_empty;
input [1:0] measfb_xorz;
output reg [`OPCODE_BW-1:0] opcode;
output reg a_taken;

always @(*)
begin
    a_taken = (temp_opcode == `LQM_FB_OPCODE) & (measfb_xorz == `PP_X | measfb_xorz == `PP_Z);

    if (instbuf_empty)
        opcode = `INVALID_OPCODE;
    else
    begin
        if (temp_opcode == `LQM_FB_OPCODE)
        begin
            if (measfb_xorz == `PP_X)
                opcode = `LQM_X_OPCODE;
            else if (measfb_xorz == `PP_Z)
                opcode = `LQM_Z_OPCODE;
            else
                opcode = `LQM_FB_OPCODE;
        end
        else
            opcode = temp_opcode;
    end
end

endmodule
