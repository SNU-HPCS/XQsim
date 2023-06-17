`include "define.v"

module pfu_ctrl(
    state,
    tcu_opcode_reg,
    pchinfo_rdlast,
    error_valid,
    pchwr_stall,
    topsu_valid,
    piu_opcode,
    last_pchinfo,
    pfflag,
    next_state,
    pisrmem_push,
    pisrmem_pop,
    opbuf_push,
    opbuf_pop,
    sel_cwd_err,
    next_valid,
    pf_wren
);

input [1:0] state;
input [`OPCODE_BW-1:0] tcu_opcode_reg;
input pchinfo_rdlast;
input error_valid;
input pchwr_stall;
input topsu_valid;
input [`OPCODE_BW-1:0] piu_opcode;
input last_pchinfo;
input pfflag;
output reg [1:0] next_state;
output reg pisrmem_push;
output reg pisrmem_pop;
output reg opbuf_push;
output reg opbuf_pop;
output reg sel_cwd_err;
output reg next_valid;
output reg pf_wren;

always @(*)
begin
    // next_state
    if (state == `PFU_READY)
    begin
       if (tcu_opcode_reg == `RUN_ESM_OPCODE)
           next_state = `PFU_UPDATING;
       else
           next_state = `PFU_READY;
    end
    else if (state == `PFU_UPDATING)
    begin
       if (pchinfo_rdlast)
           next_state = `PFU_WAITING;
       else
           next_state = `PFU_UPDATING;
    end
    else if (state == `PFU_WAITING)
    begin
        if (error_valid)
            next_state = `PFU_READY;
        else
            next_state = `PFU_WAITING;
    end
    else
    begin
        next_state = `PFU_READY;
    end

    // pisrmem_push
    pisrmem_push = (~pchwr_stall) & (topsu_valid) & (piu_opcode != `RUN_ESM_OPCODE);
    // pisrmem_pop
    pisrmem_pop = (state == `PFU_UPDATING);

    // opbuf_push
    opbuf_push = pisrmem_push & last_pchinfo;
    // opbuf_pop
    opbuf_pop = (state == `PFU_UPDATING) & (next_state == `PFU_WAITING);

    // sel_cwd_err
    if (state == `PFU_UPDATING)
        sel_cwd_err = `SELCWDERR_CWD;
    else
        sel_cwd_err = `SELCWDERR_ERR;

    // next_valid
    next_valid = (state == `PFU_WAITING) & (next_state == `PFU_READY) & (pfflag);

    // pf_wren
    pf_wren = (state == `PFU_UPDATING) | error_valid;
end

endmodule

