`include "define.v"

module educell_esmunit_idx(
    esm_reg, 
    first_esmidx,
    second_esmidx
);

input [`AQMEAS_TH-1:0] esm_reg;
output reg [`log2(`AQMEAS_TH)-1:0] first_esmidx, second_esmidx;

integer I;
reg first_set, second_set;
always @(*)
begin
    // intermediate
    first_set = 0;
    second_set = 0;
    first_esmidx = 0;
    second_esmidx = 0;
    for (I = 0; I < `AQMEAS_TH; I = I+1)
    begin
        if (esm_reg[I] == 1)
        begin
            if (~first_set)
            begin
                first_set = 1;
                first_esmidx = I;
            end
            else
            begin
                if (~second_set)
                begin
                    second_set = 1;
                    second_esmidx = I;
                end
            end
        end
    end
end

endmodule
