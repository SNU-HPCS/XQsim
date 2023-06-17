`include "define.v"

module EDU (
    rst, 
    clk, 
    pchwr_stall, 
    pchinfo_valid, 
    pchinfo, 
    last_pchinfo, 
    piu_opcode,
    aqmeas_valid, 
    aqmeas_array,
    dqmeas_valid,
    dqmeas_array,
    tcu_opcode,
    tcu_valid,
    error_array,
    eigen_array,
    edu_valid,
    pfflag
);

parameter EDUPI_BW = `PCHTYPE_BW + (4*`FACEBD_BW);

/*** INPUT/OUTPUT DECLARATION***/
input rst, clk;
// stall
input pchwr_stall;
// from PIU
input pchinfo_valid;
input [`PCHINFO_BW-1:0] pchinfo;
input last_pchinfo;
input [`OPCODE_BW-1:0] piu_opcode;
// from QCI
input aqmeas_valid;
input [`NUM_AQ-1:0] aqmeas_array;
input dqmeas_valid;
input [`NUM_DQ-1:0] dqmeas_array;
// from TCU
input [`OPCODE_BW-1:0] tcu_opcode;
input tcu_valid;
// to PFU, LMU
output [`NUM_DQ*2-1:0] error_array;
output [`NUM_AQ-1:0] eigen_array;
output reg edu_valid;
output reg pfflag;

/*** WIRE DECLARATION ***/
// input decomposition & shortcut assign
wire [`PCHADDR_BW-1:0] pchidx;
wire [`PCHTYPE_BW-1:0] pchtype;
wire [(4*`FACEBD_BW)-1:0] facebd;
assign pchidx = pchinfo[`PCHINFO_BW-`PCHSTAT_BW-`PCHDYN_BW-1 -: `PCHADDR_BW];
assign pchtype = pchinfo[`PCHINFO_BW-1 -: `PCHTYPE_BW];
assign facebd = pchinfo[`PCHINFO_BW-`PCHSTAT_BW-1 -: (4*`FACEBD_BW)];
////
wire next_pchinfo_taken;

// from edu_ctrl (control signals)
wire wr_pireg;
wire rst_pireg;
wire [1:0] next_state;
wire esm_finish;
wire token_finish;
wire layer_retry;
wire layer_finish;
wire wr_zeroesm;
wire shift_token;
wire rst_first_token;
wire rst_cellstate;
wire next_valid;
wire rst_timeout;
wire up_timeout;
wire set_measerr_flag;
wire set_last_measerr_flag;
wire pop_aqmeasbuf;
wire apply_aqmeas_flip;
wire rst_token_pipe;

// from edu_pibuf (fifo)
wire [`NUM_PCH*EDUPI_BW-1:0] pchinfo_running;
wire pchinfo_empty;

// input/output of edu_token_setup
wire last_token;
wire [`TKROWADDR_BW-1:0] next_rowidx;

// input/output of educell
reg [EDUPI_BW-1:0] pchinfo_array [`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire tokenin_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire flagin_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikein_nw_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikein_ne_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikein_sw_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikein_se_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikein_n_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikein_s_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromein_nw_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromein_ne_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromein_sw_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromein_se_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromein_n_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromein_s_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];

wire esmhead_exist_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire tokenout_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire flagout_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire local_tokenmatch_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire local_errormatch_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire local_measmatch_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire eigen_array_wire[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikeout_nw_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikeout_ne_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikeout_sw_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikeout_se_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikeout_n_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire spikeout_s_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromeout_nw_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromeout_ne_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromeout_sw_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromeout_se_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromeout_n_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire [1:0] syndromeout_s_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];
wire aqmeasbuf_valid_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];

// from edu_cell array
reg esmhead_exist;
reg global_tokenmatch;
reg global_errormatch;
reg global_measmatch;

reg aqmeasbuf_valid;
wire [1:0] err_nw_array[`NUM_DQROW-1:0][`NUM_DQCOL-1:0];
wire [1:0] err_ne_array[`NUM_DQROW-1:0][`NUM_DQCOL-1:0];
wire [1:0] err_sw_array[`NUM_DQROW-1:0][`NUM_DQCOL-1:0];
wire [1:0] err_se_array[`NUM_DQROW-1:0][`NUM_DQCOL-1:0];
wire [1:0] next_error_array[`NUM_DQROW-1:0][`NUM_DQCOL-1:0];

// from last_aqmeas_flip 
reg last_aqmeas_flip_array[`NUM_AQROW-1:0][`NUM_AQCOL-1:0];


// for pipelining
//// token setup
wire [(`NUM_AQROW+`NUM_AQCOL-1)*(`NUM_AQROW)-1:0] esmhead_rows;
wire [(`NUM_AQROW+`NUM_AQCOL-1)*(`NUM_AQROW)-1:0] flag_out_rows;

wire [(`NUM_AQROW+`NUM_AQCOL-1)-1:0] token_exist_rows_0;
wire [`AQROWADDR_BW*(`NUM_AQROW+`NUM_AQCOL-1)-1:0] token_col_rows_0;

wire [(`NUM_AQROW+`NUM_AQCOL-1)-1:0] token_exist_rows_1;
wire token_exist_1;
wire [`TKROWADDR_BW-1:0] token_row_1;
wire [`AQROWADDR_BW*(`NUM_AQROW+`NUM_AQCOL-1)-1:0] token_col_rows_1;

wire [(`NUM_AQROW+`NUM_AQCOL-1)*(`NUM_AQROW)-1:0] token_set_rows_2;
wire [(`NUM_AQROW+`NUM_AQCOL-1)*(`NUM_AQROW)-1:0] flag_set_rows_2;
wire token_match;

/******/


/*** REGISTER DECLARATION ***/ 
// accumulate pchinfo -> push pchinfos to pibuf
reg [`NUM_PCH*EDUPI_BW-1:0] pchinfo_regs;
// catch last pchinfo timing
reg pchinfo_taken;
// 
reg [`OPCODE_BW-1:0] opcode_reg;
// state
reg [1:0] state;
// counters
reg [`TKROWADDR_BW-1:0] curr_rowidx_reg;
reg [`ROUND_BW-1:0] aqmeas_counter;
reg [`ROUND_BW-1:0] round_counter;
reg [`ROUND_BW:0] timeout_th;
reg [`ROUND_BW:0] timeout_counter;
// 
reg set_first_aqmeas;
reg first_token;
reg last_token_reg;
// 
reg [1:0] error_array_reg[`NUM_DQROW-1:0][`NUM_DQCOL-1:0];
reg edu_valid_reg;
// for pipelining
//// token setup
reg [(`NUM_AQROW+`NUM_AQCOL-1)-1:0] token_exist_rows_0_reg;
reg [`AQROWADDR_BW*(`NUM_AQROW+`NUM_AQCOL-1)-1:0] token_col_rows_0_reg;
reg token_valid_0_reg;

reg [(`NUM_AQROW+`NUM_AQCOL-1)-1:0] token_exist_rows_1_reg;
reg token_exist_1_reg;
reg [`TKROWADDR_BW-1:0] token_row_1_reg;
reg [`AQROWADDR_BW*(`NUM_AQROW+`NUM_AQCOL-1)-1:0] token_col_rows_1_reg;
reg token_valid_1_reg;

reg token_match_reg; 

//// others
reg [`NUM_PCH*EDUPI_BW-1:0] pchinfo_running_reg;
reg set_first_aqmeas_reg;


/*** WIRE ALLOCATION & ASSIGNMENT  ***/ 
assign next_pchinfo_taken = (~pchinfo_taken) & (last_pchinfo & (piu_opcode == `RUN_ESM_OPCODE));

genvar iw, jw;
generate
    for (iw = 0; iw < `NUM_AQROW; iw = iw+1)
    begin: gen_inout_iw
        for (jw = 0; jw < `NUM_AQCOL; jw = jw+1)
        begin: gen_inout_jw
            // generate educell input 
            // input: tokenin_array, flagin_array
            if (iw+jw >= `NUM_AQROW)
            begin
                assign tokenin_array[iw][jw] = token_set_rows_2[(iw+jw)*`NUM_AQROW+(-iw+`NUM_AQROW-1)];
                assign flagin_array[iw][jw] = flag_set_rows_2[(iw+jw)*`NUM_AQROW+(-iw+`NUM_AQROW-1)];
            end
            else
            begin
                assign tokenin_array[iw][jw] = token_set_rows_2[(iw+jw)*`NUM_AQROW+(jw)];
                assign flagin_array[iw][jw] = flag_set_rows_2[(iw+jw)*`NUM_AQROW+(jw)];
            end

            // input: spikein_arrays
            //// nw
            if (iw == 0 | jw == 0)
            begin: gen_spikein_nw_c
                assign spikein_nw_array[iw][jw] = 0;
            end
            else
            begin: gen_spikein_nw_g
                assign spikein_nw_array[iw][jw] = spikeout_se_array[iw-1][jw-1];
            end
            //// ne
            if (iw == 0 | jw == `NUM_AQCOL-1)
            begin: gen_spikein_ne_c
                assign spikein_ne_array[iw][jw] = 0;
            end
            else
            begin: gen_spikein_ne_g
                assign spikein_ne_array[iw][jw] = spikeout_sw_array[iw-1][jw+1];
            end
            //// sw
            if (iw == `NUM_AQROW-1 | jw == 0)
            begin: gen_spikein_sw_c
                assign spikein_sw_array[iw][jw] = 0; 
            end
            else
            begin: gen_spikein_sw_g
                assign spikein_sw_array[iw][jw] = spikeout_ne_array[iw+1][jw-1];
            end
            //// se
            if (iw == `NUM_AQROW-1 | jw == `NUM_AQCOL-1)
            begin: gen_spikein_se_c
                assign spikein_se_array[iw][jw] = 0; 
            end
            else
            begin: gen_spikein_se_g
                assign spikein_se_array[iw][jw] = spikeout_nw_array[iw+1][jw+1];
            end
            //// n
            if (iw == 0)
            begin: gen_spikein_n_c
                assign spikein_n_array[iw][jw] = 0; 
            end
            else
            begin: gen_spikein_n_g
                assign spikein_n_array[iw][jw] = spikeout_s_array[iw-1][jw];
            end
            //// s
            if (iw == `NUM_AQROW-1)
            begin: gen_spikein_s_c
                assign spikein_s_array[iw][jw] = 0; 
            end
            else
            begin: gen_spikein_s_g
                assign spikein_s_array[iw][jw] = spikeout_n_array[iw+1][jw];
            end

            // input: syndromein_arrays
            //// nw
            if (iw == 0 | jw == 0)
            begin: gen_syndromein_nw_c
                assign syndromein_nw_array[iw][jw] = `PP_I;
            end
            else
            begin: gen_syndromein_nw_g
                assign syndromein_nw_array[iw][jw] = syndromeout_se_array[iw-1][jw-1];
            end
            //// ne
            if (iw == 0 | jw == `NUM_AQCOL-1)
            begin: gen_syndromein_ne_c
                assign syndromein_ne_array[iw][jw] = `PP_I;
            end
            else
            begin: gen_syndromein_ne_g
                assign syndromein_ne_array[iw][jw] = syndromeout_sw_array[iw-1][jw+1];
            end
            //// sw
            if (iw == `NUM_AQROW-1 | jw == 0)
            begin: gen_syndromein_sw_c
                assign syndromein_sw_array[iw][jw] = `PP_I; 
            end
            else
            begin: gen_syndromein_sw_g
                assign syndromein_sw_array[iw][jw] = syndromeout_ne_array[iw+1][jw-1];
            end
            //// se
            if (iw == `NUM_AQROW-1 | jw == `NUM_AQCOL-1)
            begin: gen_syndromein_se_c
                assign syndromein_se_array[iw][jw] = `PP_I; 
            end
            else
            begin: gen_syndromein_se_g
                assign syndromein_se_array[iw][jw] = syndromeout_nw_array[iw+1][jw+1];
            end
            //// n
            if (iw == 0)
            begin: gen_syndromein_n_c
                assign syndromein_n_array[iw][jw] = `PP_I; 
            end
            else
            begin: gen_syndromein_n_g
                assign syndromein_n_array[iw][jw] = syndromeout_s_array[iw-1][jw];
            end
            //// s
            if (iw == `NUM_AQROW-1)
            begin: gen_syndromein_s_n
                assign syndromein_s_array[iw][jw] = `PP_I; 
            end
            else
            begin: gen_syndromein_s_g
                assign syndromein_s_array[iw][jw] = syndromeout_n_array[iw+1][jw];
            end
            // output: syndromeout_*_array -> err_*_array
            //// nw
            if (iw == 0 | jw == 0)
            begin: err_nw_c
                assign err_nw_array[iw][jw] = `PP_I;
            end
            else
            begin: err_nw_g
                assign err_nw_array[iw][jw] = syndromeout_se_array[iw-1][jw-1];
            end
            //// ne
            if (iw == 0)
            begin: err_ne_c
                assign err_ne_array[iw][jw] = `PP_I;
            end
            else
            begin: err_ne_g
                assign err_ne_array[iw][jw] = syndromeout_sw_array[iw-1][jw];
            end
            //// sw
            if (jw == 0)
            begin: err_sw_c
                assign err_sw_array[iw][jw] = `PP_I;
            end
            else
            begin: err_sw_g
                assign err_sw_array[iw][jw] = syndromeout_ne_array[iw][jw-1];
            end
            //// se
            assign err_se_array[iw][jw] = syndromeout_nw_array[iw][jw];

            // EDU outputs
            assign error_array[(iw*`NUM_DQCOL+jw)*2 +: 2] = error_array_reg[iw][jw];
            assign eigen_array[iw*`NUM_AQCOL+jw] = eigen_array_wire[iw][jw];

            // generate edu_token_setup input
            if (iw+jw >= `NUM_AQROW)
            begin
                assign esmhead_rows[(iw+jw)*`NUM_AQROW+(-iw+`NUM_AQROW-1)] = esmhead_exist_array[iw][jw];
                assign flag_out_rows[(iw+jw)*`NUM_AQROW+(-iw+`NUM_AQROW-1)] = flagout_array[iw][jw];
            end
            else
            begin
                assign esmhead_rows[(iw+jw)*`NUM_AQROW+(jw)] = esmhead_exist_array[iw][jw];
                assign flag_out_rows[(iw+jw)*`NUM_AQROW+(jw)] = flagout_array[iw][jw];
            end
        end
    end
endgenerate


integer IW, JW;
integer PCHROW, PCHCOL, PCHIDX;
integer PR, PC, UR, UC, QB, IDX;
integer DQROW, DQCOL;
reg dqmeas;

always @(*)
begin
    for (IW = 0; IW < `NUM_AQROW; IW = IW+1)
    begin
        for (JW = 0; JW < `NUM_AQCOL; JW = JW+1)
        begin
            // educell input: pchinfo_array
            PCHROW = IW/(`NUM_UCROW*2);
            PCHCOL = JW/(`NUM_UCCOL*2);
            PCHIDX = PCHROW*`NUM_PCHCOL + PCHCOL;
            // use educell output
            pchinfo_array[IW][JW] = pchinfo_running_reg[PCHIDX*EDUPI_BW +: EDUPI_BW];
            // output: esmhead_exist_array -> esmhead_exist
            if (IW == 0 & JW == 0)
                esmhead_exist = esmhead_exist_array[IW][JW];
            else
                esmhead_exist = esmhead_exist | esmhead_exist_array[IW][JW];
            // output: local_errormatch_array -> global_errormatch
            if (IW == 0 & JW == 0)
                global_errormatch = local_errormatch_array[IW][JW];
            else
                global_errormatch = global_errormatch | local_errormatch_array[IW][JW];
            // output: local_measmatch_array -> global_measmatch
            if (IW == 0 & JW == 0)
                global_measmatch = local_measmatch_array[IW][JW];
            else
                global_measmatch = global_measmatch | local_measmatch_array[IW][JW];
            // output: aqmeasbuf_valid_array -> aqmeasbuf_valid
            if (IW == 0 & JW == 0)
                aqmeasbuf_valid = aqmeasbuf_valid_array[IW][JW];
            else
                aqmeasbuf_valid = aqmeasbuf_valid | aqmeasbuf_valid_array[IW][JW];
        end
    end
    //
    global_tokenmatch = token_match_reg;

    // EDU outputs
    // output: edu_valid
    edu_valid = edu_valid_reg;
    // output: pfflag
    if (edu_valid)
        pfflag = (opcode_reg == `LQM_X_OPCODE | opcode_reg == `LQM_Y_OPCODE | opcode_reg == `LQM_Z_OPCODE | opcode_reg == `MEAS_INTMD_OPCODE);
    else
        pfflag = 0;

    // last_aqmeas_flip_array
    for (IW = 0; IW < `NUM_AQROW; IW = IW+1)
    begin
        for (JW = 0; JW < `NUM_AQCOL; JW = JW+1)
        begin
            last_aqmeas_flip_array[IW][JW] = 0;
        end
    end

    for (PR = 0; PR < `NUM_PCHROW; PR = PR+1)
    begin
        for (PC = 0; PC < `NUM_PCHCOL; PC = PC+1)
        begin
            for (UR = 0; UR < `NUM_UCROW; UR = UR+1)
            begin
                for (UC = 0; UC < `NUM_UCCOL; UC = UC+1)
                begin
                    for (QB = 0; QB < (`NUM_QB/2); QB = QB+1)
                    begin
                        if (dqmeas_valid & opcode_reg == `MEAS_INTMD_OPCODE)
                        begin
                            IDX = PR*(`NUM_PCHCOL*`NUM_UCROW*`NUM_UCCOL*`NUM_QB/2) + PC*(`NUM_UCROW*`NUM_UCCOL*`NUM_QB/2) + UR*(`NUM_UCCOL*`NUM_QB/2) + UC*(`NUM_QB/2) + QB;
                            dqmeas = dqmeas_array[IDX];
                            
                            if (QB == 2 | QB == 3)
                                DQROW = PR*(`CODE_DIST+1) + UR*2 + 1;
                            else
                                DQROW = PR*(`CODE_DIST+1) + UR*2;

                            if (QB == 1 | QB == 3)
                                DQCOL = PC*(`CODE_DIST+1) + UC*2 + 1;
                            else
                                DQCOL = PC*(`CODE_DIST+1) + UC*2;

                            if (DQROW != 0 & DQCOL != 0)
                                last_aqmeas_flip_array[DQROW-1][DQCOL-1] = last_aqmeas_flip_array[DQROW-1][DQCOL-1] ^ dqmeas;
                            if (DQROW != 0)
                                last_aqmeas_flip_array[DQROW-1][DQCOL] = last_aqmeas_flip_array[DQROW-1][DQCOL] ^ dqmeas;
                            if (DQCOL != 0)
                                last_aqmeas_flip_array[DQROW][DQCOL-1] = last_aqmeas_flip_array[DQROW][DQCOL-1] ^ dqmeas;
                            last_aqmeas_flip_array[DQROW][DQCOL] = last_aqmeas_flip_array[DQROW][DQCOL] ^ dqmeas;
                        end
                    end
                end
            end
        end
    end
end


/*** REGISTER UPDATE ***/ 
integer IR, JR;
always @(posedge clk)
begin
    if (rst)
    begin
        state <= `EDU_READY;
        pchinfo_regs <= 0;
        pchinfo_taken <= 0;
        opcode_reg <= `INVALID_OPCODE;
        curr_rowidx_reg <= 0;
        aqmeas_counter <= 0;
        round_counter <= 0;
        timeout_th <= 2;
        timeout_counter <= 0;
        set_first_aqmeas <= 1;
        first_token <= 1;
        last_token_reg <= 0;
        for (IR = 0; IR < `NUM_DQROW; IR = IR+1)
        begin
            for (JR =0; JR < `NUM_DQCOL; JR = JR+1)
            begin
                error_array_reg[IR][JR] <= `PP_I;
            end
        end
        edu_valid_reg <= 0;
        // pipelining 
        token_exist_rows_0_reg <= 0;
        token_col_rows_0_reg <= 0;
        token_valid_0_reg <= 0;

        token_exist_rows_1_reg <= 0;
        token_exist_1_reg <= 0;
        token_row_1_reg <= 0;
        token_col_rows_1_reg <= 0;
        token_valid_1_reg <= 0;

        token_match_reg <= 0;
        //
        pchinfo_running_reg <= 0;
        set_first_aqmeas_reg <= 1;
    end
    else
    begin
        // state
        state <= next_state; 
        // set_first_aqmeas
        if (aqmeas_valid)
            set_first_aqmeas <= 0;
        else if (layer_finish & round_counter == $unsigned(`CODE_DIST-1))
            set_first_aqmeas <= 1;
        // first_token
        if (token_finish)
            first_token <= 1;
        else if (rst_first_token)
            first_token <= 0;
        // pchinfo_regs
        if (rst_pireg)
        begin
            pchinfo_regs <= 0;
        end
        else if (wr_pireg)
        begin
            pchinfo_regs[pchidx*EDUPI_BW +: EDUPI_BW] <= {pchtype, facebd};
        end
        // pchinfo_taken
        pchinfo_taken <= next_pchinfo_taken;
        // opcode_reg
        if (tcu_valid & (tcu_opcode != `RUN_ESM_OPCODE))
            opcode_reg <= tcu_opcode;
        // curr_rowidx_reg
        if (token_finish)
            curr_rowidx_reg <= 0;
        else if (shift_token)
            curr_rowidx_reg <= next_rowidx;
        // aqmeas_counter
        if (aqmeasbuf_valid & pop_aqmeasbuf)
            aqmeas_counter <= aqmeas_counter + 1;
        else if (layer_finish)
            aqmeas_counter <= aqmeas_counter - 1;
        // round_counter
        if (esm_finish)
            round_counter <= 0;
        else if (layer_finish)
            round_counter <= round_counter + 1;
        // timeout_th
        if (layer_finish)
            timeout_th <= 2;
        else if (layer_retry)
            timeout_th <= timeout_th + 2;
        // timeout_counter
        if (rst_timeout)
            timeout_counter <= 0;
        else if (up_timeout)
            timeout_counter <= timeout_counter + 1;

        // last_token_reg
        if (token_finish)
            last_token_reg <= 0;
        else if (shift_token)
            last_token_reg <= last_token;
        // error_array_reg
        for (IR = 0; IR < `NUM_DQROW; IR = IR+1)
        begin
            for (JR =0; JR < `NUM_DQCOL; JR = JR+1)
            begin
                if (global_errormatch)
                    error_array_reg[IR][JR] <= next_error_array[IR][JR];
                else if (edu_valid)
                    error_array_reg[IR][JR] <= `PP_I;
            end
        end
        // valid_reg
        edu_valid_reg <= next_valid;

        // pipelining
        if (rst_token_pipe)
        begin
            token_exist_rows_0_reg <= 0;
            token_col_rows_0_reg <= 0;
            token_valid_0_reg <= 0;

            token_exist_rows_1_reg <= 0;
            token_exist_1_reg <= 0;
            token_row_1_reg <= 0;
            token_col_rows_1_reg <= 0;
            token_valid_1_reg <= 0;

            token_match_reg <= 0;
        end
        else if (shift_token)
        begin
            token_exist_rows_0_reg <= token_exist_rows_0;
            token_col_rows_0_reg <= token_col_rows_0;
            token_valid_0_reg <= 1;

            token_exist_rows_1_reg <= token_exist_rows_1;
            token_exist_1_reg <= token_exist_1;
            token_row_1_reg <= token_row_1;
            token_col_rows_1_reg <= token_col_rows_1;
            token_valid_1_reg <= token_valid_0_reg;

            token_match_reg <= token_match;
        end
        // 
        if (pchinfo_empty)
        begin
            pchinfo_running_reg <= 0;
        end
        else
        begin
            pchinfo_running_reg <= pchinfo_running;
        end
        set_first_aqmeas_reg <= set_first_aqmeas;
    end
end


/*** MICROUNIT DECLARATION ***/
// edu_ctrl
edu_ctrl UUT0(
    .pchinfo_valid(pchinfo_valid),
    .piu_opcode(piu_opcode),
    .pchwr_stall(pchwr_stall),
    .pchinfo_taken(pchinfo_taken),
    .state(state),
    .aqmeas_valid(aqmeas_valid),
    .aqmeas_counter(aqmeas_counter),
    .first_token(first_token),
    .esmhead_exist(esmhead_exist),
    .last_token_reg(last_token_reg),
    .global_tokenmatch(global_tokenmatch),
    .global_errormatch(global_errormatch),
    .global_measmatch(global_measmatch),
    .round_counter(round_counter),
    .timeout_th(timeout_th),
    .timeout_counter(timeout_counter),
    .wr_pireg(wr_pireg),
    .rst_pireg(rst_pireg),
    .wr_zeroesm(wr_zeroesm),
    .esm_finish(esm_finish),
    .next_state(next_state),
    .token_finish(token_finish), 
    .layer_retry(layer_retry),
    .layer_finish(layer_finish),
    .shift_token(shift_token),
    .rst_first_token(rst_first_token),
    .rst_cellstate(rst_cellstate),
    .next_valid(next_valid),
    .rst_timeout(rst_timeout),
    .up_timeout(up_timeout),
    .set_measerr_flag(set_measerr_flag),
    .set_last_measerr_flag(set_last_measerr_flag),
    .pop_aqmeasbuf(pop_aqmeasbuf),
    .apply_aqmeas_flip(apply_aqmeas_flip),
    .rst_token_pipe(rst_token_pipe)
);

// edu_pibuf
fifo #(
    .ADDR_BW(1),
    .DATA_BW(`NUM_PCH*EDUPI_BW)
) UUT1(
    .rst(rst), 
    .clk(clk),
    .wr_din(rst_pireg), 
    .rd_dout(esm_finish), 
    .din(pchinfo_regs),
    .empty(pchinfo_empty),
    .dout(pchinfo_running)
);

// edu_cell array
genvar i, j;
generate
    for (i = 0; i < `NUM_AQROW; i = i+1)
    begin: gen_educell_i
        for (j = 0; j < `NUM_AQCOL; j = j+1)
        begin: gen_educell_j
            edu_cell #(
                .AQROW(i), 
                .AQCOL(j)
            ) UUT2_i_j(
                .rst(rst),
                .clk(clk),
                .pchinfo(pchinfo_array[i][j]),
                .set_first_aqmeas(set_first_aqmeas_reg),
                .wr_zeroesm(wr_zeroesm),
                .token_finish(token_finish),
                .shift_token(shift_token),
                .rst_cellstate(rst_cellstate),
                .curr_rowidx(curr_rowidx_reg),
                .global_tokenmatch(global_tokenmatch),
                .global_errormatch(global_errormatch),
                .global_measmatch(global_measmatch),
                .set_measerr_flag(set_measerr_flag),
                .set_last_measerr_flag(set_last_measerr_flag),
                .pop_aqmeasbuf(pop_aqmeasbuf),
                .last_aqmeas_flip(last_aqmeas_flip_array[i][j]),
                .apply_aqmeas_flip(apply_aqmeas_flip),
                .aqmeas_valid(aqmeas_valid),
                .aqmeas(aqmeas_array[i*`NUM_AQCOL+j]),
                .token_in(tokenin_array[i][j]),
                .flag_in(flagin_array[i][j]),
                .spike_in_nw(spikein_nw_array[i][j]),
                .spike_in_ne(spikein_ne_array[i][j]), 
                .spike_in_sw(spikein_sw_array[i][j]),
                .spike_in_se(spikein_se_array[i][j]),
                .spike_in_n(spikein_n_array[i][j]), 
                .spike_in_s(spikein_s_array[i][j]),
                .syndrome_in_nw(syndromein_nw_array[i][j]),
                .syndrome_in_ne(syndromein_ne_array[i][j]), 
                .syndrome_in_sw(syndromein_sw_array[i][j]),
                .syndrome_in_se(syndromein_se_array[i][j]),
                .syndrome_in_n(syndromein_n_array[i][j]), 
                .syndrome_in_s(syndromein_s_array[i][j]),
                .esmhead_exist(esmhead_exist_array[i][j]),
                .token_out(tokenout_array[i][j]),
                .flag_out(flagout_array[i][j]),
                .local_tokenmatch(local_tokenmatch_array[i][j]),
                .local_errormatch(local_errormatch_array[i][j]),
                .local_measmatch(local_measmatch_array[i][j]),
                .eigen(eigen_array_wire[i][j]),
                .spike_out_nw(spikeout_nw_array[i][j]),
                .spike_out_ne(spikeout_ne_array[i][j]), 
                .spike_out_sw(spikeout_sw_array[i][j]),
                .spike_out_se(spikeout_se_array[i][j]),
                .spike_out_n(spikeout_n_array[i][j]), 
                .spike_out_s(spikeout_s_array[i][j]),
                .syndrome_out_nw(syndromeout_nw_array[i][j]),
                .syndrome_out_ne(syndromeout_ne_array[i][j]), 
                .syndrome_out_sw(syndromeout_sw_array[i][j]),
                .syndrome_out_se(syndromeout_se_array[i][j]),
                .syndrome_out_n(syndromeout_n_array[i][j]), 
                .syndrome_out_s(syndromeout_s_array[i][j]),
                .aqmeasbuf_valid(aqmeasbuf_valid_array[i][j])
            );
            
            edu_nexterr UUT3_i_j(
                .err_nw(err_nw_array[i][j]),
                .err_ne(err_ne_array[i][j]),
                .err_sw(err_sw_array[i][j]),
                .err_se(err_se_array[i][j]),
                .curr_err(error_array_reg[i][j]),
                .next_err(next_error_array[i][j])
            );
        end
    end
endgenerate

genvar k;
generate
    for (k = 0; k < (`NUM_AQROW+`NUM_AQCOL-1); k = k+1)
    begin: gen_token_setup_0_k
        edu_token_setup_0 UUT4_k(
            .esmhead_row(esmhead_rows[k*`NUM_AQROW +: `NUM_AQROW]),
            .flag_out_row(flag_out_rows[k*`NUM_AQROW +: `NUM_AQROW]),
            .token_exist_row_0(token_exist_rows_0[k]),
            .token_col_row_0(token_col_rows_0[k*`AQROWADDR_BW +: `AQROWADDR_BW])
        );
    end
endgenerate

edu_token_setup_1 UUT5(
    .token_exist_rows_0_reg(token_exist_rows_0_reg),
    .token_exist_rows_1(token_exist_rows_1),
    .token_exist_1(token_exist_1),
    .token_row_1(token_row_1)
);
assign token_col_rows_1 = token_col_rows_0_reg;


genvar l;
generate
    for (l = 0; l < (`NUM_AQROW+`NUM_AQCOL-1); l = l+1)
    begin: gen_token_setup_2_l
        edu_token_setup_2 UUT6_l(
            .token_exist_row_1_reg(token_exist_rows_1_reg[l]), 
            .token_col_row_1_reg(token_col_rows_1_reg[l*`AQROWADDR_BW +: `AQROWADDR_BW]),
            .token_set_row_2(token_set_rows_2[l*`NUM_AQROW +: `NUM_AQROW]),
            .flag_set_row_2(flag_set_rows_2[l*`NUM_AQROW +: `NUM_AQROW])
        );
    end
endgenerate

edu_token_setup_3 UUT7(
    .token_exist_1_reg(token_exist_1_reg),
    .token_row_1_reg(token_row_1_reg),
    .token_valid_1_reg(token_valid_1_reg),
    .last_token(last_token),
    .next_rowidx(next_rowidx),
    .token_match(token_match)
);

endmodule
