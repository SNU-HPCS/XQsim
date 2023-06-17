`include "define.v"

module lmu_measmux(
    pchidx, 
    dqmeas_array_ing, 
    aqmeas_array_ing, 
    pf_array_ing,
    dqmeas_array_pch, 
    aqmeas_array_pch,
    pf_array_pch
);

input [`PCHADDR_BW-1:0] pchidx;
input [`NUM_DQ-1:0] dqmeas_array_ing;
input [`NUM_AQ-1:0] aqmeas_array_ing;
input [`NUM_DQ*2-1:0] pf_array_ing;
output [`NUM_PCHDQ-1:0] dqmeas_array_pch;
output [`NUM_PCHAQ-1:0] aqmeas_array_pch;
output [`NUM_PCHDQ*2-1:0] pf_array_pch;

// dqmeas_mux
mux #(
    .NUM_INPUT(`NUM_PCH),
    .DATA_WIDTH(`NUM_PCHDQ)
) UUT0(
    .data_in(dqmeas_array_ing),
    .sel(pchidx),
    .data_out(dqmeas_array_pch)
);

// aqmeas_mux
mux #(
    .NUM_INPUT(`NUM_PCH),
    .DATA_WIDTH(`NUM_PCHAQ)
) UUT1(
    .data_in(aqmeas_array_ing),
    .sel(pchidx),
    .data_out(aqmeas_array_pch)
);

// dqmeas_mux
mux #(
    .NUM_INPUT(`NUM_PCH),
    .DATA_WIDTH(`NUM_PCHDQ*2)
) UUT2(
    .data_in(pf_array_ing),
    .sel(pchidx),
    .data_out(pf_array_pch)
);

endmodule
