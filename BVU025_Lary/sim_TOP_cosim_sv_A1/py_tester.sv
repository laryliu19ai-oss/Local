`timescale 1ns / 1ps

/*
** =========================================================================
** Module Name  : py_tester
** Library      : BVU025_Lary
** Cell         : py_tester
** View         : systemVerilog
** Description  : SystemVerilog Virtual Host Controller & SAR Engine
** Features     :
**   1. Power-Up Sequence & Trim Mode Enable (TMIRefOn)
**   2. Default Reset Code: NvTrmIref<5:0> = 6'b100000 (32, 0x20)
**   3. 100us Period SAR Clock (50us High / 50us Low):
**      - 50us High (Positive Phase): Apply Test Bit (Set to 1)
**      - 50us Low  (Negative Phase): Immediate Comparator Evaluation at Falling Edge
**          * dIRefTMO == High (1'b1) -> Discard 1 (Clear bit to 0 throughout Low phase)
**          * dIRefTMO == Low  (1'b0) -> Keep 1 (Maintain bit as 1 throughout Low phase)
**   4. dDone asserted at 0.9ms (after 6-bit SAR completes) until 1.4ms
**   5. Measurement Mode Switch at 1.40ms (TMIRefOn=0, TMIRefMeas=1)
** =========================================================================
*/

module py_tester (
    output logic        TMIRefOn,
    output logic        TMIRefMeas,
    output logic        CLK,
    output logic        dDone,
    output logic [5:0]  NvTrmIref,
    input  logic        dIRefTMO
);

    integer bit_idx;
    logic [5:0] current_trim;

    initial begin
        TMIRefOn     = 1'b0;
        TMIRefMeas   = 1'b0;
        CLK          = 1'b0;
        dDone        = 1'b0;
        NvTrmIref    = 6'b100000; // Default power-on reset value: 100000 (32, 0x20)
        current_trim = 6'b000000;

        // -------------------------------------------------------------
        // Step 1: Power-Up Delay & Trim Enable (t = 0 ~ 390us)
        // -------------------------------------------------------------
        #100000;
        $display("\n=======================================================");
        $display("[py_tester @ %0t ns] -> Power-Up Complete: VDD_PCB=3.3V, VSS_PCB=0V, NvTrmIref=6'b100000 (0x20)", $time);

        #290000; // t = 390us
        TMIRefOn = 1'b1;
        $display("[py_tester @ %0t ns] -> TMIRefOn = 1'b1 (Trim Mode Enabled)", $time);

        #10000; // t = 400us
        $display("[py_tester @ %0t ns] -> Starting Synchronous SAR Calibration (50us High Apply / 50us Low Evaluate)...", $time);

        // -------------------------------------------------------------
        // Step 2: 6-bit Binary SAR Calibration (t = 400us ~ 1000us)
        // -------------------------------------------------------------
        for (bit_idx = 5; bit_idx >= 0; bit_idx = bit_idx - 1) begin
            // 1. 50us High (Positive Phase): Apply test bit = 1
            CLK = 1'b1;
            current_trim[bit_idx] = 1'b1;
            NvTrmIref = current_trim;
            $display("[py_tester @ %0t ns | CLK High (50us)] -> SAR Step [Bit %0d]: Applied Trim Code = %0d (%b, 0x%02X)", 
                     $time, bit_idx, NvTrmIref, NvTrmIref, NvTrmIref);

            // Wait 50us during High phase for analog settling and comparison
            #50000;

            // 2. 50us Low (Negative Phase): Immediate decision at falling edge
            CLK = 1'b0;
            if (dIRefTMO === 1'b1) begin
                current_trim[bit_idx] = 1'b0;
                NvTrmIref = current_trim;
                $display("[py_tester @ %0t ns | CLK Low  (50us)] -> Sampled dIRefTMO = High -> Discard 1: Bit %0d cleared to 0 immediately, Code = %0d (%b, 0x%02X)", 
                         $time, bit_idx, NvTrmIref, NvTrmIref, NvTrmIref);
            end else begin
                $display("[py_tester @ %0t ns | CLK Low  (50us)] -> Sampled dIRefTMO = Low  -> Keep 1: Bit %0d maintained as 1, Code = %0d (%b, 0x%02X)", 
                         $time, bit_idx, NvTrmIref, NvTrmIref, NvTrmIref);
            end

            // Maintain the decided code throughout the entire 50us Low phase
            #50000;
        end

        // -------------------------------------------------------------
        // Step 3: SAR Done & Latch Optimal Code (t = 0.9ms ~ 1.4ms)
        // -------------------------------------------------------------
        dDone = 1'b1;
        $display("[py_tester @ %0t ns] -> *** SAR Calibration Converged! Optimal Trim Code = %0d (%b, 0x%02X), dDone = 1 ***", 
                 $time, NvTrmIref, NvTrmIref, NvTrmIref);

        // Extra 2 clock cycles (t = 1.0ms ~ 1.2ms)
        repeat (2) begin
            CLK = 1'b1;
            #50000;
            CLK = 1'b0;
            #50000;
        end

        // Settle until t = 1.40ms
        #200000; // t = 1.40ms
        dDone      = 1'b0;
        TMIRefOn   = 1'b0;
        #10000;  // t = 1.41ms
        TMIRefMeas = 1'b1;
        $display("[py_tester @ %0t ns] -> Switched to Measurement Mode: TMIRefOn=0, TMIRefMeas=1", $time);
        $display("=======================================================\n");
    end

endmodule
