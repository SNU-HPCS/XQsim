`include "define.v"

module pdu_ctrl(
    state,
    to_pdubuf_empty,
    lqidx,
    next_lqlist,
    is_lastlq,
    is_evenlq,
    take_in,
    update_lqlist,
    flush_out,
    next_state
);

input [1:0] state;
input to_pdubuf_empty;
input [`LQADDR_BW-1:0] lqidx;
input [`NUM_LQ-1:0] next_lqlist;
output reg is_lastlq;
output reg is_evenlq;
output reg take_in;
output reg update_lqlist;
output reg flush_out;
output reg [1:0] next_state;

always @(*)
begin
    // is_lastlq
    if ((state == `PDU_RUNNING | state == `PDU_OUTPUT_RUNNING) & (next_lqlist == 0))
        is_lastlq = 1;
    else
        is_lastlq = 0;

    // is_evenlq
    if (lqidx % 2 == 0)
        is_evenlq = 1;
    else
        is_evenlq = 0;
    
    // take_in
    if ((state == `PDU_EMPTY | state == `PDU_OUTPUT_EMPTY) & ~to_pdubuf_empty)
        take_in = 1;
    else if (is_lastlq & ~to_pdubuf_empty)
        take_in = 1;
    else
        take_in = 0;

    // update_lqlist
    if ((state == `PDU_RUNNING | state == `PDU_OUTPUT_RUNNING) & (next_lqlist != 0))
        update_lqlist = 1;
    else
        update_lqlist = 0;

    // flush_out
    if (state == `PDU_OUTPUT_EMPTY | state == `PDU_OUTPUT_RUNNING)
        flush_out = 1;
    else
        flush_out = 0;
    
    // next_state 
    if (state == `PDU_EMPTY | state == `PDU_OUTPUT_EMPTY)
    begin
        if (~to_pdubuf_empty)
            next_state = `PDU_RUNNING;
        else
            next_state = `PDU_EMPTY;
    end
    else if (state == `PDU_RUNNING | state == `PDU_OUTPUT_RUNNING)
    begin
        if (next_lqlist == 0)
        begin
            if (~to_pdubuf_empty)
                next_state = `PDU_OUTPUT_RUNNING;
            else
                next_state = `PDU_OUTPUT_EMPTY;
        end
        else
            next_state = `PDU_RUNNING;
    end
    else
        next_state = state;
end

endmodule
