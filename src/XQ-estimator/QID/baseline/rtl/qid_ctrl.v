`include "define.v"

module qid_ctrl(
    opcode,
    opcode_reg,
    mregdst,
    mregdst_reg,
    instbuf_empty,
    qifdone,
    all_decoded,
    to_pdubuf_full,
    to_lmubuf_full,
    to_pdubuf_valid,
    to_lmubuf_valid, 
    reg_stall
);

input [`OPCODE_BW-1:0] opcode;
input [`OPCODE_BW-1:0] opcode_reg;
input [`LQADDR_BW-1:0] mregdst;
input [`LQADDR_BW-1:0] mregdst_reg;
input instbuf_empty;
input qifdone;
input all_decoded;
input to_pdubuf_full;
input to_lmubuf_full;
output reg to_pdubuf_valid;
output reg to_lmubuf_valid; 
output reg reg_stall;


always @(*)
begin
    // reg_stall
    reg_stall = (to_pdubuf_full | to_lmubuf_full) | (opcode == `LQM_FB_OPCODE);

    // to_pdubuf_valid
    if (opcode != `INVALID_OPCODE & opcode_reg != `INVALID_OPCODE)
    begin
        if (opcode == `LQI_OPCODE & opcode_reg == `LQI_OPCODE)
            to_pdubuf_valid = 0;
        else if (opcode == `MERGE_INFO_OPCODE & opcode_reg == `MERGE_INFO_OPCODE)
            to_pdubuf_valid = 0;
        else if (opcode == `PPM_INTERPRET_OPCODE & opcode_reg == `PPM_INTERPRET_OPCODE)
            to_pdubuf_valid = 0;
        else if ((opcode == `LQM_X_OPCODE | opcode == `LQM_Y_OPCODE | opcode == `LQM_Z_OPCODE) & (opcode_reg == `LQM_X_OPCODE | opcode_reg == `LQM_Y_OPCODE | opcode_reg == `LQM_Z_OPCODE))
            to_pdubuf_valid = 0;
        else
            to_pdubuf_valid = ~reg_stall;
    end
    else if (opcode == `INVALID_OPCODE & opcode_reg != `INVALID_OPCODE)
    begin
        if (qifdone & (~all_decoded))
            to_pdubuf_valid = ~reg_stall;
        else
            to_pdubuf_valid = 0;
    end
    else
    begin
        to_pdubuf_valid = 0;
    end

    // to_lmubuf_valid
    if (opcode_reg == `LQM_X_OPCODE | opcode_reg == `LQM_Y_OPCODE | opcode_reg == `LQM_Z_OPCODE)
    begin
        if (~all_decoded)
            to_lmubuf_valid = ~reg_stall;
        else
            to_lmubuf_valid = 0;
    end
    else if (opcode_reg == `PPM_INTERPRET_OPCODE)
    begin
        if (opcode == `PPM_INTERPRET_OPCODE)
        begin
            if (mregdst != mregdst_reg)
                to_lmubuf_valid = ~reg_stall;
            else
                to_lmubuf_valid = 0;
        end
        else if (opcode != `INVALID_OPCODE)
        begin
            to_lmubuf_valid = ~reg_stall;
        end
        else // INVALID_OPCODE
        begin
            if (qifdone & (~all_decoded))
                to_lmubuf_valid = ~reg_stall;
            else
                to_lmubuf_valid = 0;
        end
    end
    else
        to_lmubuf_valid = 0;
end

endmodule
