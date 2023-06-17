`include "define.v"

module pdu_pchmaptbl(
    rst,
    clk,
    lqidx,
    rd_pchidx0,
    rd_pchidx1
);

input rst;
input clk;
input [`LQADDR_BW-1:0] lqidx;
output reg [`PCHADDR_BW-1:0] rd_pchidx0;
output reg [`PCHADDR_BW-1:0] rd_pchidx1;


/*** ROM  ***/
reg [`PCHADDR_BW-1:0] pch_maptable [`NUM_LQ-1:0][1:0];


always @(lqidx)
begin
    // read pch_maptable
    rd_pchidx0 = pch_maptable[lqidx][0];
    rd_pchidx1 = pch_maptable[lqidx][1];
end


/*** ROM init ***/
integer I;
reg [`PCHADDR_BW-1:0] init_pchidx0, init_pchidx1;

always @(posedge clk)
begin
    if (rst)
    begin
        for (I = 0; I < `NUM_LQ; I = I+1)
        begin
            if (I == 0) // two-patch Z ancilla
            begin
                init_pchidx0 = 0;
                init_pchidx1 = $unsigned(`NUM_PCHCOL);
            end
            else if (I == 1) // two-patch M ancilla
            begin
                init_pchidx0 = 1;
                init_pchidx1 = $unsigned(`NUM_PCHCOL + 1);
            end
            else
            begin
                if (I == `NUM_LQ-1) // single-patch X lq
                begin
                    init_pchidx0 = $unsigned(2*`NUM_PCHCOL-1);
                    init_pchidx1 = $unsigned(2*`NUM_PCHCOL-1);
                end
                else // single-patch M lq
                begin
                    if (I % 2 == 0) // first row
                    begin
                        init_pchidx0 = $unsigned((I >> 1) + 1);
                        init_pchidx1 = $unsigned((I >> 1) + 1);
                    end
                    else // last row
                    begin
                        init_pchidx0 = $unsigned((2*`NUM_PCHCOL) + ((I+1) >> 1));
                        init_pchidx1 = $unsigned((2*`NUM_PCHCOL) + ((I+1) >> 1));
                    end
                end
            end

            pch_maptable[I][0] <= init_pchidx0;
            pch_maptable[I][1] <= init_pchidx1;
        end
    end
end


endmodule
