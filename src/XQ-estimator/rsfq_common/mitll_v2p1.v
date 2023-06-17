module mitll_bufft(A, Q);
input A;
output Q;
assign Q = A;
endmodule

module mitll_nott(A, Q);
input A;
output Q;
assign Q = ~A;
endmodule

module mitll_andt(A, B, Q);
input A, B;
output Q;
assign Q = (A & B);
endmodule

module mitll_ort(A, B, Q);
input A, B;
output Q;
assign Q = (A | B);
endmodule

module mitll_xort(A, B, Q);
input A, B;
output Q;
assign Q = (A ^ B);
endmodule

module mitll_xnort(A, B, Q);
input A, B;
output Q;
assign Q = ~(A ^ B);
endmodule

module mitll_dfft(C, A, Q);
input C, A;
output reg Q;
always @(posedge C)
	Q <= A;
endmodule

