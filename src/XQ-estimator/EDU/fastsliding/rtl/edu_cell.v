`include "define.v"

module edu_cell #(
    parameter AQROW = 0,
    parameter AQCOL = 0
)(
    rst, 
    clk,
    pchinfo,
    set_first_aqmeas,
    wr_zeroesm,
    token_finish, 
    shift_token,
    rst_cellstate,
    curr_rowidx,
    global_tokenmatch,
    global_errormatch,
    global_measmatch,
    set_measerr_flag,
    set_last_measerr_flag,
    pop_aqmeasbuf,
    last_aqmeas_flip,
    apply_aqmeas_flip,
    aqmeas_valid,
    aqmeas,
    token_in,
    flag_in,
    spike_in_nw,
    spike_in_ne, 
    spike_in_sw,
    spike_in_se,
    spike_in_n, 
    spike_in_s,
    syndrome_in_nw,
    syndrome_in_ne, 
    syndrome_in_sw,
    syndrome_in_se,
    syndrome_in_n, 
    syndrome_in_s,
    esmhead_exist,
    token_out,
    flag_out,
    local_tokenmatch,
    local_errormatch,
    local_measmatch,
    eigen,
    spike_out_nw,
    spike_out_ne, 
    spike_out_sw,
    spike_out_se,
    spike_out_n, 
    spike_out_s,
    syndrome_out_nw,
    syndrome_out_ne, 
    syndrome_out_sw,
    syndrome_out_se,
    syndrome_out_n, 
    syndrome_out_s, 
    aqmeasbuf_valid
);


localparam EDUPI_BW = `PCHTYPE_BW + (4*`FACEBD_BW);
localparam MY_ROWIDX = AQROW+AQCOL;
localparam [6:0] LOCATION = {
                                ((AQROW+AQCOL)%2 == 0),
                                (AQCOL % (`NUM_UCCOL*2) == 0),
                                (AQROW % (`NUM_UCROW*2) == 0),
                                (AQCOL % (`NUM_UCCOL*2) == (`NUM_UCCOL*2-1)),
                                (AQROW % (`NUM_UCROW*2) == (`NUM_UCROW*2-1)),
                                (AQROW % (`NUM_UCROW*2) == 1),
                                (AQROW % (`NUM_UCROW*2) == (`NUM_UCROW*2-2))
                            };

/*** INPUT/OUTPUT DECLARATION***/
input rst;
input clk;
input [EDUPI_BW-1:0] pchinfo;
input set_first_aqmeas;
input wr_zeroesm;
input token_finish;
input shift_token;
input rst_cellstate;
//input [`AQADDR_BW-1:0] curr_rowidx;
input [`TKROWADDR_BW-1:0] curr_rowidx;

input global_tokenmatch;
input global_errormatch;
input global_measmatch;
input set_measerr_flag;
input set_last_measerr_flag;
input pop_aqmeasbuf;
input last_aqmeas_flip;
input apply_aqmeas_flip;
input aqmeas_valid;
input aqmeas;
input token_in;
input flag_in;
input spike_in_nw;
input spike_in_ne;
input spike_in_sw;
input spike_in_se;
input spike_in_n;
input spike_in_s;
input [1:0] syndrome_in_nw;
input [1:0] syndrome_in_ne;
input [1:0] syndrome_in_sw;
input [1:0] syndrome_in_se;
input [1:0] syndrome_in_n;
input [1:0] syndrome_in_s;
output reg esmhead_exist;
output reg token_out;
output reg flag_out;
output reg local_tokenmatch;
output reg local_errormatch;
output reg local_measmatch;
output reg eigen;
output spike_out_nw;
output spike_out_ne;
output spike_out_sw;
output spike_out_se;
output spike_out_n;
output spike_out_s;
output [1:0] syndrome_out_nw;
output [1:0] syndrome_out_ne;
output [1:0] syndrome_out_sw;
output [1:0] syndrome_out_se;
output [1:0] syndrome_out_n;
output [1:0] syndrome_out_s;

/*** WIRE DECLARATION & ASSIGN***/
// from educell_predecoder
wire [5:0] possible_dir;
wire [1:0] role;
wire [1:0] syn_to_west;
wire [1:0] syn_to_east;
wire first_aqmeas_flag;

// from aqmeasbuf
output wire aqmeasbuf_valid;
wire aqmeasbuf_val;
reg esm_val;
// from esm_reg 
reg esm_head;
reg esm_exist;
// from educell_decoder
wire [2:0] next_state;
wire [5:0] spike_dir;
// from delay_reg
reg [`AQMEAS_TH-1:0] delayed_esmval;
reg delayed_bdval;
// from educell_syndir
wire [5:0] syndir;
// from educell_esmunit_idx
wire [`log2(`AQMEAS_TH)-1:0] first_esmidx, second_esmidx;

/*** REGISTER DECLARATION ***/ 
// constant
// for esm val generation
reg first_aqmeas;
reg [1:0] prev_aqmeas_reg;
reg measerr_flag;
reg last_measerr_flag;
reg last_aqmeas_flip_reg;
reg [1:0] aqmeas_buf_val;
reg [1:0] aqmeas_buf_valid;
// for esm val store
reg [`AQMEAS_TH-1:0] esm_reg;
reg [`AQMEAS_TH-2:0] esm_delay_reg [`AQMEAS_TH-2:0];
reg [`BD_DELAY-1:0] bd_delay_reg;
// for token 
reg token_reg;
reg flag_token;
// 
reg [2:0] state;
reg [5:0] spikedir_reg;
//
reg spike_taken;
reg [5:0] syndir_reg;
reg syndrome_taken;
// for pipelining
reg [1:0] role_reg;
reg [5:0] possible_dir_reg;



/*** WIRE TRANSFER (COMBINATIONAL LOGIC) ***/
assign aqmeasbuf_valid = aqmeas_buf_valid[0];
assign aqmeasbuf_val = aqmeas_buf_val[0];

integer IW;
always @(*) 
begin
    // esm_val
    if (first_aqmeas | wr_zeroesm)
        esm_val = 0;
    //else if (aqmeasbuf_valid)
    else if (aqmeasbuf_valid & role == `ROLE_ACTIVE)
        esm_val = aqmeasbuf_val ^ prev_aqmeas_reg[0] ^ measerr_flag;
    else
        esm_val = 0;
    
    // from esm_reg
    esm_head = esm_reg[0];
    esm_exist = (|esm_reg);
    // from delay_regs
    for (IW = 0; IW < `AQMEAS_TH; IW = IW+1)
    begin
        if (IW == 0)
            delayed_esmval[IW] = esm_head;
        else
            delayed_esmval[IW] = esm_delay_reg[IW-1][0];
    end
    delayed_bdval = bd_delay_reg[0];
    // output
    token_out = token_reg;
    flag_out = flag_token;
    esmhead_exist = (esm_head == 1);
    //local_tokenmatch = (role == `ROLE_ACTIVE & token_out == 1 & esmhead_exist);
    local_tokenmatch = (role_reg == `ROLE_ACTIVE & token_out == 1 & esmhead_exist);

    local_errormatch = ((state == `EDUCELL_SOURCE | state == `EDUCELL_BOUNDARY) & syndrome_taken);
    local_measmatch = ((state == `EDUCELL_SYNK) & (|delayed_esmval[`AQMEAS_TH-1:1]));
    eigen = measerr_flag ^ prev_aqmeas_reg[1] ^ prev_aqmeas_reg[0];
end

/*** REGISTER UPDATE ***/ 
integer IR, JR, KR, LR, MR;
always @(posedge clk)
begin
    if (rst)
    begin
        //
        first_aqmeas <= 1;
        prev_aqmeas_reg <= 0;
        last_aqmeas_flip_reg <= 0;
        aqmeas_buf_val <= 0;
        aqmeas_buf_valid <= 0;
        measerr_flag <= 0;
        last_measerr_flag <= 0;
        esm_reg <= 0;
        token_reg <= 0;
        flag_token <= 0;
        state <= `EDUCELL_INACTIVE;
        //
        for (JR = 0; JR < `AQMEAS_TH-1; JR = JR+1)
        begin
            esm_delay_reg[JR] <= 0;
        end
        bd_delay_reg <= 0;
        //
        spike_taken <= 0;
        spikedir_reg <= 0;
        syndir_reg <= 0;
        syndrome_taken <= 0;
        // pipelining
        role_reg <= 0;
        possible_dir_reg <= 0;
    end
    else
    begin
        // first_aqmeas
        if (aqmeasbuf_valid & pop_aqmeasbuf)
            first_aqmeas <= 0;
        else if (set_first_aqmeas & first_aqmeas_flag)
            first_aqmeas <= 1;
        // prev_aqmeas_reg
        if (pop_aqmeasbuf & aqmeasbuf_valid)
        begin
            if (first_aqmeas)
                prev_aqmeas_reg[0] <= 0;
            else
                prev_aqmeas_reg[0] <= prev_aqmeas_reg[1];
            prev_aqmeas_reg[1] <= aqmeasbuf_val;
        end
        if (apply_aqmeas_flip & last_aqmeas_flip_reg)
        begin
            prev_aqmeas_reg[0] <= prev_aqmeas_reg[0]^1;
        end
        // aqmeas_buf
        if (aqmeas_valid | pop_aqmeasbuf)
        begin
            aqmeas_buf_val[0] <= aqmeas_buf_val[1];
            aqmeas_buf_valid[0] <= aqmeas_buf_valid[1];
            if (aqmeas_valid)
            begin
                aqmeas_buf_val[1] <= aqmeas;
                aqmeas_buf_valid[1] <= 1;
            end
            else
            begin
                aqmeas_buf_val[1] <= 0;
                aqmeas_buf_valid[1] <= 0;
            end
        end
        // last_aqmeas_flip_reg
        if (last_aqmeas_flip)
            last_aqmeas_flip_reg <= 1;
        else if (apply_aqmeas_flip)
            last_aqmeas_flip_reg <= 0;
        // measerr_flag
        if (set_measerr_flag & esm_head)
            measerr_flag <= 1;
        else if (aqmeasbuf_valid & pop_aqmeasbuf)
            measerr_flag <= 0;
        // last_measerr_flag
        if (set_last_measerr_flag & esm_head)
            last_measerr_flag <= 1;
        else if (aqmeasbuf_valid & pop_aqmeasbuf)
            last_measerr_flag <= 0;
        // esm_reg
        //// push new esm_val
        //if (aqmeas_valid | wr_zeroesm)
        if ((aqmeasbuf_valid & pop_aqmeasbuf) | wr_zeroesm)
        begin
            for (IR = 0; IR < `AQMEAS_TH; IR = IR+1)
            begin
                if (IR == `AQMEAS_TH-1)
                    esm_reg[IR] <= esm_val;
                else
                    esm_reg[IR] <= esm_reg[IR+1];
            end
        end
        //// ???
        //else if (role != `ROLE_ACTIVE & token_out & esmhead_exist)
        else if (role_reg != `ROLE_ACTIVE & token_out & esmhead_exist)
            esm_reg[0] <= 0;
        //// pop for errormatch
        else if (global_errormatch)
        begin
            if (state == `EDUCELL_SYNK)
            begin
                esm_reg[0] <= 0;
            end
            else if (state == `EDUCELL_SOURCE & local_errormatch)
            begin
                esm_reg[first_esmidx] <= 0;
            end
        end
        //// pop for measmatch
        else if (global_measmatch)
        begin
            if (state == `EDUCELL_SYNK)
            begin
                esm_reg[0] <= 0;
                esm_reg[second_esmidx] <= 0;
            end
        end

        // token_reg
        if (token_finish)
            token_reg <= 0;
        else if (shift_token)
            token_reg <= token_in;
        // flag_token
        if (token_finish)
            flag_token <= 0;
        else if (shift_token & ~flag_token)
            flag_token <= flag_in;
        // state
        if (rst_cellstate | global_tokenmatch)
            state <= next_state;
        // spikedir_reg
        if (rst_cellstate)
            spikedir_reg <= 0;
        else if (global_tokenmatch)
            spikedir_reg <= spike_dir;
        // esm_delay_reg
        for (KR = 0; KR < `AQMEAS_TH-1; KR = KR+1)
        begin
            for (LR = 0; LR < `AQMEAS_TH-1; LR = LR+1)
            begin
                if (rst_cellstate)
                begin
                    esm_delay_reg[KR][LR] <= 0;
                end
                else if (state == `EDUCELL_SYNK | state == `EDUCELL_SOURCE)
                begin
                    if (LR > KR)
                        esm_delay_reg[KR][LR] <= 0;
                    else if (LR == KR)
                        esm_delay_reg[KR][LR] <= esm_reg[KR+1];
                    else // LR < KR
                        esm_delay_reg[KR][LR] <= esm_delay_reg[KR][LR+1];
                end
            end
        end
        // bd_delay_reg
        for (MR = 0; MR < `BD_DELAY; MR = MR+1)
        begin
            if (rst_cellstate)
            begin
                bd_delay_reg[MR] <= 0;
            end
            else if (state == `EDUCELL_BOUNDARY)
            begin
                if (MR == `BD_DELAY-1)
                    bd_delay_reg[MR] <= 1;
                else
                    bd_delay_reg[MR] <= bd_delay_reg[MR+1];
            end
        end
        // spike_taken
        if (rst_cellstate)
            spike_taken <= 0;
        else if (state == `EDUCELL_SOURCE)
            spike_taken <= 1;
        else if (~spike_taken)
            spike_taken <= (spike_in_nw | spike_in_ne | spike_in_sw | spike_in_se | spike_in_n | spike_in_s);
        // syndir_reg
        if (rst_cellstate)
        begin
            syndir_reg <= 0;
        end
        else if ((~spike_taken) & (spike_in_nw | spike_in_ne | spike_in_sw | spike_in_se | spike_in_n | spike_in_s))
            syndir_reg <= syndir;
        // syndrome_taken
        if (rst_cellstate)
            syndrome_taken <= 0;
        else if (state == `EDUCELL_SYNK)
            syndrome_taken <= 1;
        else if (~syndrome_taken)
            syndrome_taken <= (|(syndrome_in_nw | syndrome_in_ne | syndrome_in_sw | syndrome_in_se | syndrome_in_n | syndrome_in_s));
        // pipelining
        role_reg <= role;
        possible_dir_reg <= possible_dir;
    end
end


/*** MICROUNIT DECLARATION ***/

// educell_predecoder
educell_predecoder UUT1(
    .location(LOCATION),
    .pchinfo(pchinfo),
    .role(role), 
    .possible_dir(possible_dir),
    .syn_to_west(syn_to_west),
    .syn_to_east(syn_to_east),
    .first_aqmeas_flag(first_aqmeas_flag)
);

// educell_decoder
educell_decoder UUT2(
    .my_rowidx($unsigned(MY_ROWIDX[0 +: `TKROWADDR_BW])),
    .rst_cellstate(rst_cellstate),
    .role(role_reg),
    .esm_exist(esm_exist),
    .local_tokenmatch(local_tokenmatch),
    .possible_dir(possible_dir_reg),
    .curr_rowidx(curr_rowidx),
    .flag_token(flag_token),
    .next_state(next_state),
    .spike_dir(spike_dir)
);

// educell_spikegen
educell_spikegen UUT3(
    .state(state),
    .delayed_esmval(delayed_esmval), 
    .delayed_bdval(delayed_bdval), 
    .spike_taken(spike_taken), 
    .spikedir_reg(spikedir_reg),
    .spike_out_nw(spike_out_nw),
    .spike_out_ne(spike_out_ne), 
    .spike_out_sw(spike_out_sw),
    .spike_out_se(spike_out_se),
    .spike_out_n(spike_out_n),
    .spike_out_s(spike_out_s)
);

// educell_syndir
educell_syndir UUT4(
    .spike_in_nw(spike_in_nw),
    .spike_in_ne(spike_in_ne), 
    .spike_in_sw(spike_in_sw),
    .spike_in_se(spike_in_se), 
    .spike_in_n(spike_in_n),
    .spike_in_s(spike_in_s),
    .syndir(syndir)
);

// educell_syndromegen
educell_syndromegen UUT5(
    .state(state),
    .syndrome_taken(syndrome_taken),
    .spike_taken(spike_taken),
    .syndir_reg(syndir_reg),
    .syn_to_west(syn_to_west),
    .syn_to_east(syn_to_east),
    .syndrome_out_nw(syndrome_out_nw),
    .syndrome_out_ne(syndrome_out_ne),
    .syndrome_out_sw(syndrome_out_sw),
    .syndrome_out_se(syndrome_out_se),
    .syndrome_out_n(syndrome_out_n),
    .syndrome_out_s(syndrome_out_s)
);

// educell_esmunit_idx
educell_esmunit_idx UUT6(
    .esm_reg(esm_reg), 
    .first_esmidx(first_esmidx),
    .second_esmidx(second_esmidx)
);

endmodule
