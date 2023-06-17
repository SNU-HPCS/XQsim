`include "define.v"

module lmu_interpret(
    lqsignX_acc_reg,
    lqsignZ_acc_reg,
    lpplist,
    byproduct,
    meas_sign,
    byproduct_check,
    init_meas,
    byproduct_reg,
    a_valid,
    a_val,
    a_taken_reg,
    a_sign_reg,
    final_meas,
    next_byproduct,
    measfb_xorz
);

input [`NUM_LQ-1:0] lqsignX_acc_reg;
input [`NUM_LQ-1:0] lqsignZ_acc_reg;
input [`NUM_LQ*2-1:0] lpplist;
input [`NUM_LQ*2-1:0] byproduct;
input meas_sign;
input byproduct_check;
input init_meas;
input [`NUM_LQ*2-1:0] byproduct_reg;
input a_valid;
input a_val;
input a_taken_reg;
input a_sign_reg;
output reg final_meas;
output reg [`NUM_LQ*2-1:0] next_byproduct;
output reg [1:0] measfb_xorz;

integer I;
reg not_commute;
reg lqsign;
reg [1:0] lpp, bpp;
always @(*)
begin
    // final_meas
    not_commute = 0;
    lqsign = 0;
    for (I = 0; I < `NUM_LQ; I = I+1)
    begin
        lpp = lpplist[I*2 +: 2];
        bpp = byproduct[I*2 +: 2];
        if (lpp != bpp & lpp != `PP_I & bpp != `PP_I)
            not_commute = not_commute ^ 1;

        if (lpp == `PP_X)
            lqsign = lqsign ^ lqsignX_acc_reg[I];
        else if (lpp == `PP_Z)
            lqsign = lqsign ^ lqsignZ_acc_reg[I];
        else if (lpp == `PP_Y)
            lqsign = lqsign ^ (lqsignX_acc_reg[I] ^ lqsignZ_acc_reg[I]);
    end
    final_meas = (not_commute & byproduct_check) ^ lqsign ^ meas_sign ^ init_meas;
    
    // next_byproduct
    next_byproduct = byproduct ^ byproduct_reg;

    // measfb_xorz
    if (a_valid & ~a_taken_reg)
    begin
        if ((a_val == 1 & a_sign_reg == `MEASSIGN_PLUS) | (a_val == 0 & a_sign_reg == `MEASSIGN_MINUS))
            measfb_xorz = `FBXORZ_X;
        else if ((a_val == 1 & a_sign_reg == `MEASSIGN_MINUS) | (a_val == 0 & a_sign_reg == `MEASSIGN_PLUS))
            measfb_xorz = `FBXORZ_Z;
        else
            measfb_xorz = `FBXORZ_INVALID;
    end
    else 
        measfb_xorz = `FBXORZ_INVALID;
end

endmodule
