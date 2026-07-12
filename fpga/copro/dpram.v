// Behavioral stand-in for the MiSTer core's rtl/dpram.vhd (VHDL -- verilator can't ingest
// it). True dual-port RAM, synchronous 1-cycle reads: the exact contract CoproDrMario.sv
// relies on. SIMULATION ONLY -- Quartus builds use the core's real dpram wrapper.
module dpram #(
    parameter widthad_a = 12,
    parameter width_a   = 8
)(
    input                       clock_a,
    input       [widthad_a-1:0] address_a,
    input       [width_a-1:0]   data_a,
    input                       wren_a,
    output reg  [width_a-1:0]   q_a,
    input                       clock_b,
    input       [widthad_a-1:0] address_b,
    input       [width_a-1:0]   data_b,
    input                       wren_b,
    output reg  [width_a-1:0]   q_b
);

reg [width_a-1:0] mem [0:(1<<widthad_a)-1];

always @(posedge clock_a) begin
    if (wren_a) mem[address_a] <= data_a;
    q_a <= mem[address_a];
end

always @(posedge clock_b) begin
    if (wren_b) mem[address_b] <= data_b;
    q_b <= mem[address_b];
end

endmodule
