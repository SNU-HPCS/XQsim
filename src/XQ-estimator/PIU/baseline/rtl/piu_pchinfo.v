`include "define.v"

module piu_pchinfo(
    pchtype,
    pchop_list_reg0, 
    pchop_list_reg1, 
    pchmreg_list_reg0,
    pchmreg_list_reg1, 
    pchpp_list_reg0,
    pchpp_list_reg1,
    pchidx,
    opcode_reg,
    pchinfo_etc
);

input [`PCHTYPE_BW-1:0] pchtype;
input [`NUM_PCH*2-1:0] pchpp_list_reg0, pchpp_list_reg1;
input [`NUM_PCH*`OPCODE_BW-1:0] pchop_list_reg0, pchop_list_reg1;
input [`NUM_PCH*`LQADDR_BW-1:0] pchmreg_list_reg0, pchmreg_list_reg1;
input [`PCHADDR_BW-1:0] pchidx;
input [`OPCODE_BW-1:0] opcode_reg;
output [2*(`OPCODE_BW+`LQADDR_BW+2)-1:0] pchinfo_etc;

reg [1:0] pchpp0, pchpp1;
reg [`OPCODE_BW-1:0] pchop0, pchop1;
reg [`LQADDR_BW-1:0] pchmreg0, pchmreg1;

assign pchinfo_etc = {pchop0, pchop1, pchmreg0, pchmreg1, pchpp0, pchpp1};

reg [`LQADDR_BW-1:0] temp_pchmreg;
wire signed [`PCHADDR_BW:0] pchidx_s = $signed({1'b0, pchidx});
integer I;

always @(*)
begin
    // pchop0, pchop1
    if ((pchtype == `PCHTYPE_MT | pchtype == `PCHTYPE_MB) & (opcode_reg == `PPM_INTERPRET_OPCODE))
    begin
        pchop0 = `PPM_INTERPRET_OPCODE;
        pchop1 = `PPM_INTERPRET_OPCODE;
    end
    else if ((pchtype == `PCHTYPE_AW | pchtype == `PCHTYPE_AE | pchtype == `PCHTYPE_AC | pchtype == `PCHTYPE_AWE) & (opcode_reg == `PPM_INTERPRET_OPCODE))
    begin
        pchop0 = `PPM_INTERPRET_OPCODE;
        pchop1 = `INVALID_OPCODE;
    end
    else 
    begin
        pchop0 = pchop_list_reg0[pchidx_s*`OPCODE_BW +: `OPCODE_BW];
        pchop1 = pchop_list_reg1[pchidx_s*`OPCODE_BW +: `OPCODE_BW];
    end

    // pchmreg0, pchmreg1
    if ((pchtype == `PCHTYPE_AW | pchtype == `PCHTYPE_AE | pchtype == `PCHTYPE_AC | pchtype == `PCHTYPE_AWE) & (opcode_reg == `PPM_INTERPRET_OPCODE))
    begin
        for (I = 0; I < `NUM_PCH; I = I+1)
        begin
            if (I == 0)
                temp_pchmreg = 0;

            temp_pchmreg = temp_pchmreg | ( pchmreg_list_reg0[I] | pchmreg_list_reg1[I]);
        end
        pchmreg0 = temp_pchmreg;
        pchmreg1 = 0;
    end
    else 
    begin
        pchmreg0 = pchmreg_list_reg0[pchidx_s*`LQADDR_BW +: `LQADDR_BW];
        pchmreg1 = pchmreg_list_reg1[pchidx_s*`LQADDR_BW +: `LQADDR_BW];
    end
    
    // pchpp0, pchpp1
    if ((pchtype == `PCHTYPE_MT | pchtype == `PCHTYPE_MB) & (opcode_reg == `PPM_INTERPRET_OPCODE))
    begin
        pchpp0 = `PP_Y;
        pchpp1 = `PP_Z;
    end
    else
    begin
        pchpp0 = pchpp_list_reg0[pchidx_s*2 +: 2];
        pchpp1 = pchpp_list_reg1[pchidx_s*2 +: 2];
    end
end

endmodule

