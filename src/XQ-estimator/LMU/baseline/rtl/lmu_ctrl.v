`include "define.v"

module lmu_ctrl(
    new_array_ing_reg,
    pchinfo_rdlast_reg,
    sel_meases_reg,
    //
    state,
    pchinfo_valid,
    pchtype,
    facebd_n,
    pchop0,
    pchop1,
    dqmeas_ready,
    aqmeas_ready,
    pf_ready, 
    pchinfo_rdlast, 
    instinfo_rdlast,
    abcd_reg,
    measflags,
    next_state,
    new_array_ing,
    sel_meases,
    initmeas_wrens,
    initmeas_rst,
    pchinfo_pop,
    flip_initmeas_wr,
    finmeas_wren,
    byproduct_wren,
    abcd_rst,
    lqsign_temp_wren,
    lqsign_temp_rst,
    lqsign_acc_wren
);
input new_array_ing_reg;
input pchinfo_rdlast_reg;
input [`SELMEAS_BW*2-1:0] sel_meases_reg;
//
input [1:0] state;
input pchinfo_valid;
input [`PCHTYPE_BW-1:0] pchtype;
input [`FACEBD_BW-1:0] facebd_n;
input [`OPCODE_BW-1:0] pchop0, pchop1;
input dqmeas_ready, aqmeas_ready, pf_ready;
input pchinfo_rdlast;
input instinfo_rdlast;
input [4*2-1:0] abcd_reg;
input [`MEAS_FLAG_BW-1:0] measflags;
output reg [1:0] next_state;
output reg new_array_ing;
output reg [`SELMEAS_BW*2-1:0] sel_meases;
output reg [1:0] initmeas_wrens;
output reg initmeas_rst;
output reg pchinfo_pop;
output reg flip_initmeas_wr;
output reg finmeas_wren;
output reg byproduct_wren;
output reg abcd_rst;
output reg lqsign_temp_wren;
output reg lqsign_temp_rst;
output reg lqsign_acc_wren;

/*** Wires ***/
// abcd_reg
wire a_valid, a_val, b_valid, b_val, c_valid, c_val, d_valid, d_val;
// intermediate
reg all_input_ready;
reg is_measpp;
wire is_dqmeasop0, is_dqmeasop1;
wire abcd_valid, bpgen_condition;

// Assignment
assign {d_valid, d_val, c_valid, c_val, b_valid, b_val, a_valid, a_val} = abcd_reg;
assign abcd_valid = (a_valid & b_valid & c_valid & d_valid);
assign bpgen_condition = ((~a_val) & (c_val^d_val)) | (a_val & (b_val^c_val^d_val));
assign is_dqmeasop0 = (pchop0 == `LQM_X_OPCODE | pchop0 == `LQM_Y_OPCODE | pchop0 == `LQM_Z_OPCODE);
assign is_dqmeasop1 = (pchop1 == `LQM_X_OPCODE | pchop1 == `LQM_Y_OPCODE | pchop1 == `LQM_Z_OPCODE);


// 
integer I, J;
reg [`OPCODE_BW-1:0] pchop;

// {sel_loc, sel_dqaq, sel_xz, sel_valid}
reg [`SELMEAS_BW-1:0] selmeas;

always @(*)
begin
    // next_state
    if (pchinfo_valid)
    begin
        if (is_dqmeasop0 | is_dqmeasop1)
        begin
            all_input_ready = dqmeas_ready & pf_ready;
            is_measpp = 0;
        end
        else if (pchop0 == `PPM_INTERPRET_OPCODE | pchop1 == `PPM_INTERPRET_OPCODE)
        begin
            all_input_ready = aqmeas_ready & pf_ready & dqmeas_ready;
            is_measpp = 1;
        end
        else
        begin
            all_input_ready = 0;
            is_measpp = 0;
        end
    end
    else
    begin
        all_input_ready = 0;
        is_measpp = 0;
    end

    case (state)
        `LMU_READY:
        begin
            if (new_array_ing_reg)
                next_state = `LMU_PRODUCTING;
            else
                next_state = `LMU_READY;
        end
        `LMU_PRODUCTING: 
        begin
            if (pchinfo_rdlast_reg)
            begin
                next_state = `LMU_INTERPRETING;
            end
            else
                next_state = `LMU_PRODUCTING;
        end
        `LMU_INTERPRETING:
        begin
            if (instinfo_rdlast)
                next_state = `LMU_BPUPDATING;
            else
                next_state = `LMU_INTERPRETING;
        end
        `LMU_BPUPDATING:
        begin
            next_state = `LMU_READY;
        end
        default:
        begin
            next_state = state;
        end
    endcase
   
    // new_array_ing
    if (state == `LMU_READY & all_input_ready)
        new_array_ing = 1;
    else
        new_array_ing = 0;

    // sel_meases
    for (I = 0; I < 2; I = I+1)
    begin
        if (pchinfo_valid)
        begin
            if (I == 0)
                pchop = pchop0;
            else
                pchop = pchop1;

            // sel_loc
            case (pchop)
                `PPM_INTERPRET_OPCODE:
                begin
                    if (pchtype == `PCHTYPE_ZT)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_E;
                    else if (pchtype == `PCHTYPE_ZB)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_EXE;
                    else if (pchtype == `PCHTYPE_MT)
                    begin
                        if (I == 0)
                            selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_W;
                        else
                            selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_WINV;
                    end
                    else if (pchtype == `PCHTYPE_MB)
                    begin
                        if (I == 0)
                            selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_W;
                        else
                            selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_WINV;
                    end
                    else if (pchtype == `PCHTYPE_M)
                    begin
                        if (facebd_n == `FACEBD_PP)
                            selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_SINV;
                        else
                            selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_S;
                    end
                    else if (pchtype == `PCHTYPE_X)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_W;
                    else if (pchtype == `PCHTYPE_AW | pchtype == `PCHTYPE_AC | pchtype == `PCHTYPE_AE | pchtype == `PCHTYPE_AWE)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_ALL;
                    else
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_ALL;
                end
                `LQM_X_OPCODE:
                begin
                    if (pchtype == `PCHTYPE_ZT)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_E;
                    else if (pchtype == `PCHTYPE_ZB)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_NE;
                    else if (pchtype == `PCHTYPE_MT)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_I;
                    else if (pchtype == `PCHTYPE_MB)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_S;
                    else if (pchtype == `PCHTYPE_M)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_W;
                    else if (pchtype == `PCHTYPE_X)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_S;
                    else
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_I;
                end
                `LQM_Y_OPCODE:
                begin
                    if (pchtype == `PCHTYPE_ZT)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_E;
                    else if (pchtype == `PCHTYPE_ZB)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_EXE;
                    else if (pchtype == `PCHTYPE_MT)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_W;
                    else if (pchtype == `PCHTYPE_MB)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_WS;
                    else if (pchtype == `PCHTYPE_M)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_WS;
                    else if (pchtype == `PCHTYPE_X)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_WS;
                    else
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_I;
                end
                `LQM_Z_OPCODE:
                begin
                    if (pchtype == `PCHTYPE_ZT)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_I;
                    else if (pchtype == `PCHTYPE_ZB)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_EXE;
                    else if (pchtype == `PCHTYPE_MT)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_W;
                    else if (pchtype == `PCHTYPE_MB)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_W;
                    else if (pchtype == `PCHTYPE_M)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_S;
                    else if (pchtype == `PCHTYPE_X)
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_W;
                    else
                        selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_I;
                end
                default:
                    selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_ALL;
            endcase

            // sel_dqaq
            if (pchop == `PPM_INTERPRET_OPCODE)
                selmeas[2] = `SELDQAQ_AQ;
            else
                selmeas[2] = `SELDQAQ_DQ;

            // sel_xz
            if (pchop == `PPM_INTERPRET_OPCODE)
            begin
                if (pchtype == `PCHTYPE_ZT)
                    selmeas[1] = `SELXZ_X;
                else
                    selmeas[1] = `SELXZ_Z;
            end
            else if (pchop == `LQM_X_OPCODE)
            begin
                if (pchtype == `PCHTYPE_X | pchtype == `PCHTYPE_MB | pchtype == `PCHTYPE_M)
                    selmeas[1] = `SELXZ_X;
                else
                    selmeas[1] = `SELXZ_Z;
            end
            else if (pchop == `LQM_Y_OPCODE)
            begin
                if (pchtype == `PCHTYPE_ZB)
                    selmeas[1] = `SELXZ_X;
                else
                    selmeas[1] = `SELXZ_Z;
            end
            else if (pchop == `LQM_Z_OPCODE)
            begin
                selmeas[1] = `SELXZ_Z;
            end
            else
            begin
                selmeas[1] = `SELXZ_Z;
            end

            // sel_valid
            if (pchop == `PPM_INTERPRET_OPCODE | pchop == `LQM_X_OPCODE | pchop == `LQM_Y_OPCODE | pchop == `LQM_Z_OPCODE)
                selmeas[0] = 1;
            else
                selmeas[0] = 0;
        end
        else
        begin
            selmeas[(`SELMEAS_BW-1) -: `SELLOC_BW] = `SELLOC_ALL;
            selmeas[2] = `SELDQAQ_DQ;
            selmeas[1] = `SELXZ_Z;
            selmeas[0] = 0;
        end
        sel_meases[I*`SELMEAS_BW +: `SELMEAS_BW] = selmeas;
    end

    // initmeas_wrens
    for (J = 0; J < 2; J = J+1)
    begin
        initmeas_wrens[J] = (state == `LMU_PRODUCTING & sel_meases_reg[J*`SELMEAS_BW]);
    end
    // initmeas_rst
    initmeas_rst =  (state == `LMU_INTERPRETING & next_state != `LMU_INTERPRETING);
    // pchinfo_pop
    pchinfo_pop = (new_array_ing_reg | (state == `LMU_PRODUCTING & ~pchinfo_rdlast_reg));
    // flip_initmeas_wr
    flip_initmeas_wr = (state == `LMU_PRODUCTING & next_state != `LMU_PRODUCTING);
    // finmeas_wren
    finmeas_wren = (state == `LMU_INTERPRETING);
    // byproduct_wren
    if (state == `LMU_BPUPDATING)
        byproduct_wren = (abcd_valid & bpgen_condition);
    else
        byproduct_wren = 0;
    // abcd_rst
    abcd_rst = abcd_valid;
    // lqsign_temp_wren
    lqsign_temp_wren = (state == `LMU_PRODUCTING);
    // lqsign_temp_rst/lqsign_acc_wren 
    lqsign_temp_rst = (state == `LMU_BPUPDATING);
    lqsign_acc_wren = (state == `LMU_BPUPDATING);
end

endmodule
