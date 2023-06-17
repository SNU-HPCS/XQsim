`include "define.v"

module psu_opNloc(
    opcode_running,
    pchop_list,
    uc_counter,
    pcu_opcode,
    ucc_ucloc
);

input [`OPCODE_BW-1:0] opcode_running;
input [`NUM_PCU*(2*`OPCODE_BW)-1:0] pchop_list;
input [`NUM_UCC*`UCADDR_BW-1:0] uc_counter;
output reg [`NUM_UCC*`UCLOC_BW-1:0] ucc_ucloc;
output reg [`NUM_PCU*`OPCODE_BW-1:0] pcu_opcode;


reg [`OPCODE_BW-1:0] opcode, pchop0, pchop1;
reg uc_west, uc_north, uc_east, uc_south, uc_lowtri, uc_uppertri, uc_leftdiag, uc_rightdiag;

integer I;
integer UCROW, UCCOL;
reg signed [`UCADDR_BW:0] ucidx_s;

always @(*)
begin
    // pcu_opcode
    for (I = 0; I < `NUM_PCU; I = I+1)
    begin
        if (opcode_running == `LQM_X_OPCODE | opcode_running == `LQM_Y_OPCODE | opcode_running == `LQM_Z_OPCODE)
        begin
            {pchop0, pchop1} = pchop_list[I*(2*`OPCODE_BW) +: (2*`OPCODE_BW)];
            opcode = (pchop0 & pchop1);
        end
        else
            opcode = opcode_running;
        pcu_opcode[I*`OPCODE_BW +: `OPCODE_BW] = opcode;
    end
    // ucc_ucloc
    for (I = 0; I < `NUM_UCC; I = I+1)
    begin
            // ucloc
            ucidx_s = $signed({1'b0, uc_counter[I*`UCADDR_BW +: `UCADDR_BW]});
            UCROW = (ucidx_s) / (`NUM_UCCOL);
            UCCOL = (ucidx_s) % (`NUM_UCCOL);
            ucc_ucloc[I*`UCLOC_BW +: `UCLOC_BW] = {(UCCOL==0), (UCROW==0), (UCCOL==`NUM_UCCOL-1), (UCROW==`NUM_UCROW-1), ((UCROW+UCCOL) > `NUM_UCROW), ((UCROW+UCCOL) < `NUM_UCROW-1), ((UCROW+UCCOL) == `NUM_UCROW-1), ((UCROW+UCCOL) == `NUM_UCROW)};
    end
end


endmodule
