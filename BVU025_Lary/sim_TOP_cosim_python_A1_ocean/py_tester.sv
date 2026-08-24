`timescale 1ns / 1ps
/*
** =========================================================================
** Module Name  : py_tester
** Library      : BVU025_Lary
** Cell         : py_tester
** View         : systemVerilog
** Description   : SystemVerilog DPI-C Python Virtual Tester Interface
** Features     :
**   1. Pure Python-driven test algorithm via DPI-C (py_bridge.c / py_tester.py)
**   2. Drives TMIRefOn, TMIRefMeas, CLK, dDone, NvTrmIref<5:0>
**   3. Samples dIRefTMO digital comparator output
** =========================================================================
*/

module py_tester (
    output logic       TMIRefOn,
    output logic       TMIRefMeas,
    output logic       CLK,
    output logic       dDone,
    output logic [5:0] NvTrmIref,
    input  logic       dIRefTMO
);

    // Import C functions via DPI-C
    import "DPI-C" context function void py_init_tester(input string work_dir);
    import "DPI-C" context function void py_tester_step(
        input  longint time_ns,
        input  int     cmp_val,
        output int     trim_code,
        output int     clk_out,
        output int     done_out,
        output int     tm_on_out,
        output int     tm_meas_out
    );
    import "DPI-C" context function void py_finish_tester();

    int trim_val;
    int clk_val;
    int done_val;
    int tm_on_val;
    int tm_meas_val;
    int cmp_int;

    initial begin
        // 1. Initialize Python Tester
        py_init_tester(".");
        
        TMIRefOn   = 1'b0;
        TMIRefMeas = 1'b0;
        CLK        = 1'b0;
        dDone      = 1'b0;
        NvTrmIref  = 6'b100000;

        // 2. Main Sampling Loop: Tick every 1us (1000ns)
        while ($time <= 2000000) begin
            cmp_int = (dIRefTMO === 1'b1) ? 1 : 0;
            
            // Call Python step callback
            py_tester_step(
                $time,
                cmp_int,
                trim_val,
                clk_val,
                done_val,
                tm_on_val,
                tm_meas_val
            );

            // Assign hardware pins
            NvTrmIref  = trim_val[5:0];
            CLK        = clk_val[0];
            dDone      = done_val[0];
            TMIRefOn   = tm_on_val[0];
            TMIRefMeas = tm_meas_val[0];

            #1000; // 1us step
        end

        // 3. Close Python Tester
        py_finish_tester();
    end

endmodule
