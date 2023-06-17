module buffer #(
    parameter ADDR_BW = 1, 
    parameter DATA_BW = 4
)(
    rst,
    clk,
    wr_en,
    rd_en,
    wr_ptr,
    rd_ptr,
    din,
    dout
);

input rst, clk;
input wr_en, rd_en;
input [ADDR_BW-1:0] wr_ptr;
input [ADDR_BW-1:0] rd_ptr;
input [DATA_BW-1:0] din;
output reg [DATA_BW-1:0] dout;


reg [DATA_BW-1:0] regarray [2**ADDR_BW-1:0];

integer i;
// Register update
always @(posedge clk)
begin
    if (rst)
    begin
        for (i=0; i < 2**ADDR_BW-1; i=i+1)
            regarray[i] <= 0;
    end
    else
    begin
        if (wr_en)
            regarray[wr_ptr] <= din;
    end
end

always @(rd_en, rd_ptr)
begin
    if (rd_en)
        dout <= regarray[rd_ptr];
    else
        dout <= 0;
end


endmodule
