`include "define.v"

module edu_ctrl(
    pchinfo_valid,
    piu_opcode,
    pchwr_stall,
    pchinfo_taken,
    state,
    aqmeas_valid,
    aqmeas_counter,
    first_token,
    esmhead_exist,
    last_token_reg,
    global_tokenmatch,
    global_errormatch, 
    global_measmatch,
    round_counter,
    timeout_th,
    timeout_counter,
    wr_pireg,
    rst_pireg, 
    wr_zeroesm,
    esm_finish,
    next_state,
    token_finish,
    layer_retry,
    layer_finish,
    shift_token, 
    rst_first_token,
    rst_cellstate,
    next_valid,
    rst_timeout,
    up_timeout, 
    set_measerr_flag,
    set_last_measerr_flag,
    pop_aqmeasbuf,
    apply_aqmeas_flip
);

/*** INPUT/OUTPUT DECLARATION***/
input pchinfo_valid;
input [`OPCODE_BW-1:0] piu_opcode;
input pchwr_stall;
input pchinfo_taken;
input [1:0] state;
input aqmeas_valid;
input [`ROUND_BW-1:0] aqmeas_counter;
input first_token;
input esmhead_exist;
input last_token_reg;
input global_tokenmatch;
input global_errormatch;
input global_measmatch;
input [`ROUND_BW-1:0] round_counter;
input [`ROUND_BW:0] timeout_th;
input [`ROUND_BW:0] timeout_counter;
output reg wr_pireg;
output reg rst_pireg;
output reg wr_zeroesm;
output reg esm_finish;
output reg [1:0] next_state;
output reg token_finish;
output reg layer_retry;
output reg layer_finish;
output reg shift_token;
output reg rst_first_token;
output reg rst_cellstate;
output reg next_valid;
output reg rst_timeout;
output reg up_timeout;
output reg set_measerr_flag;
output reg set_last_measerr_flag;
output reg pop_aqmeasbuf;
output reg apply_aqmeas_flip;

/*** WIRE TRANSFER (COMBINATIONAL LOGIC) ***/
always @(*)
begin
    // token_finish: QECOOL w/o row skipping
    if (state == `EDU_TOKENALLOC)
    begin
        if (first_token & ~esmhead_exist)
            token_finish = 1;
        else if (last_token_reg == 1)
            token_finish = 1;
        else
            token_finish = 0;
    end
    else
    begin
        token_finish = 0;
    end

    // layer_retry
    if (token_finish & esmhead_exist)
    begin
        if (timeout_th < `TIMEOUT_LIMIT)
            layer_retry = 1;
        else
            layer_retry = 0;
    end
    else
    begin
        layer_retry = 0;
    end

    // layer_finish
    if (token_finish & ~layer_retry)
        layer_finish = 1;
    else
        layer_finish = 0;

    // next_state
    if (state == `EDU_READY)
    begin
        if (aqmeas_counter == `AQMEAS_TH)
            next_state = `EDU_TOKENALLOC;
        else
            next_state = `EDU_READY;
    end
    else if (state == `EDU_TOKENALLOC)
    begin
        if (global_tokenmatch)
        begin
            next_state = `EDU_ERRORPAIRING;
        end
        else if (layer_finish)
        begin
            if (round_counter < $unsigned(`CODE_DIST-`AQMEAS_TH))
                next_state = `EDU_WAITING;
            else if (round_counter == $unsigned(`CODE_DIST-1))
                next_state = `EDU_READY;
            else
                next_state = `EDU_TOKENALLOC;
        end
        else
        begin
            next_state = `EDU_TOKENALLOC;
        end
    end
    else if (state == `EDU_ERRORPAIRING)
    begin
        if ((timeout_counter == timeout_th) | global_errormatch | global_measmatch)
            next_state = `EDU_TOKENALLOC;
        else
            next_state = `EDU_ERRORPAIRING;
    end
    else if (state == `EDU_WAITING)
    begin
        if (aqmeas_counter == `AQMEAS_TH)
            next_state = `EDU_TOKENALLOC;
        else
            next_state = `EDU_WAITING;
    end
    else
    begin
        next_state = `EDU_READY;
    end

    // wr_pireg
    if (pchinfo_valid & (piu_opcode == `RUN_ESM_OPCODE) & (~pchwr_stall))
        wr_pireg = 1;
    else
        wr_pireg = 0;

    // rst_pireg
    rst_pireg = pchinfo_taken;

    // rst_first_token
    rst_first_token = (state == `EDU_TOKENALLOC);

    // shift_token
    shift_token = (state == `EDU_TOKENALLOC);

    // wr_zeroesm
    if (layer_finish & next_state == `EDU_TOKENALLOC)
        wr_zeroesm = 1;
    else
        wr_zeroesm = 0;

    // esm_finsih
    if (layer_finish & next_state == `EDU_READY)
        esm_finish = 1;
    else
        esm_finish = 0;

    // up_timeout
    if (state == `EDU_ERRORPAIRING)
        up_timeout = 1;
    else
        up_timeout = 0;

    // rst_timeout
    if (state == `EDU_ERRORPAIRING & next_state != `EDU_ERRORPAIRING)
        rst_timeout = 1;
    else
        rst_timeout = 0;

    // rst_cellstate
    if (state == `EDU_ERRORPAIRING & next_state == `EDU_TOKENALLOC)
        rst_cellstate = 1;
    else 
        rst_cellstate = 0;

    // next_valid
    if (state == `EDU_TOKENALLOC & next_state == `EDU_READY)
        next_valid = 1;
    else
        next_valid = 0;

    // set_measerr_flag
    if (token_finish & esmhead_exist)
    begin
        if (round_counter >= $unsigned(`AQMEAS_TH-1) & round_counter < $unsigned(`CODE_DIST))
        begin
            if (timeout_th == `TIMEOUT_LIMIT)
                set_measerr_flag = 1;
            else
                set_measerr_flag = 0;
        end
        else
        begin
            set_measerr_flag = 0;
        end
    end
    else
    begin
        set_measerr_flag = 0;
    end

    // set_last_measerr_flag
    set_last_measerr_flag = (set_measerr_flag) & (round_counter == $unsigned(`CODE_DIST-1));

    // pop_aqmeasbuf
    pop_aqmeasbuf = (state == `EDU_READY | state == `EDU_WAITING);

    // apply_aqmeas_flip
    apply_aqmeas_flip = (next_state == `EDU_READY);
end

endmodule

