`timescale 1ns / 1ps
/*
** =========================================================================
** Module Name  : py_tester
** Library      : BVU025_Lary
** Cell         : py_tester
** View         : systemVerilog
** Description   : Python-Led DPI-C Virtual Tester Hardware Interface
** Architecture : Matches i2c_communication_python master_controller architecture
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

    // 1. Import main Python test controller entry point
    import "DPI-C" context task c_main_tester();

    // 2. Export atomic hardware driver and sampler tasks to C / Python
    export "DPI-C" task sv_set_tm_on;
    export "DPI-C" task sv_set_tm_meas;
    export "DPI-C" task sv_set_trim_code;
    export "DPI-C" task sv_set_clk;
    export "DPI-C" task sv_set_done;
    export "DPI-C" task sv_delay_ns;
    export "DPI-C" function sv_get_cmp;
    export "DPI-C" task sv_finish_simulation;

    // Default pin initialization and launch Python master controller
    initial begin
        TMIRefOn   = 1'b0;
        TMIRefMeas = 1'b0;
        CLK        = 1'b0;
        dDone      = 1'b0;
        NvTrmIref  = 6'b100000; // Default 0x20 (32)

        // Launch Python master test flow
        c_main_tester();
    end

    // Hardware control tasks implementation
    task sv_set_tm_on(input int val);
        TMIRefOn = (val != 0) ? 1'b1 : 1'b0;
    endtask

    task sv_set_tm_meas(input int val);
        TMIRefMeas = (val != 0) ? 1'b1 : 1'b0;
    endtask

    task sv_set_trim_code(input int code);
        NvTrmIref = code[5:0];
    endtask

    task sv_set_clk(input int val);
        CLK = (val != 0) ? 1'b1 : 1'b0;
    endtask

    task sv_set_done(input int val);
        dDone = (val != 0) ? 1'b1 : 1'b0;
    endtask

    task sv_delay_ns(input int ns);
        #(ns);
    endtask

    function int sv_get_cmp();
        return (dIRefTMO === 1'b1) ? 1 : 0;
    endfunction

    task sv_finish_simulation();
        $display("[py_tester.sv] Simulation finished requested by Python Master.");
        $finish();
    endtask

endmodule
