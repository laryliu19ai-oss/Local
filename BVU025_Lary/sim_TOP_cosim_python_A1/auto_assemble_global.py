#!/usr/bin/env python3
import os
import sys
import glob
import re

def universal_assemble(netlist_dir):
    cwd = os.getcwd()
    try:
        os.chdir(netlist_dir)
        print(f"[Auto-Assemble] Working in: {netlist_dir}")

        lib_name = "BVU025_Lary"
        top_cell = "sim_TOP_cosim_python_A1"

        if os.path.exists("./designInfo"):
            info = open("./designInfo").read()
            m_cell = re.search(r'cell\s+([^\s\n]+)', info)
            if m_cell:
                top_cell = m_cell.group(1).replace('"', '').strip()
            m_lib = re.search(r'library\s+([^\s\n]+)', info)
            if m_lib:
                lib_name = m_lib.group(1).replace('"', '').strip()

        print(f"[Auto-Assemble] Detected design: {lib_name}.{top_cell}")

        # 1. Header and HDL files
        h = open('./.amsOSSHeader').read() if os.path.exists('./.amsOSSHeader') else ''
        hdl = open('./.hdlFileInfo_forNetlist').read() if os.path.exists('./.hdlFileInfo_forNetlist') else ''

        # 2. Common digital helpers
        common_digital_helpers = f"""
// Common Helper Modules for {lib_name}
`timescale 1ns / 1ns 

`worklib {lib_name}
`view functional

module Buffer_DIG (out, in);
output out;
input in;
assign out = in;
endmodule
"""

        # 3. Clean TOP_A1 Module Definition
        top_a1_block = f"""
// Specialized 3.3V TOP_A1 Module
`timescale 1ns / 1ns 

`worklib {lib_name}
`view schematic

(* cds_ams_schematic *) 
module TOP_A1 (dIRefTMO, GPIO8, aVdd, aVss, NvTrmIref, TMIRefMeas, TMIRefOn);
output dIRefTMO;
inout GPIO8, aVdd, aVss;
input TMIRefMeas, TMIRefOn;
input [5:0] NvTrmIref;

electrical GPIO8, aVdd, aVss;
wire TMIRefOni, TMIRefMeasi;
electrical aTrimRef_5, aTrimRef_4, aTrimRef_3, aTrimRef_2, aTrimRef_1, aTrimRef_0;
electrical eTMIRefOn, eTMIRefMeas;

real vtrim_5, vtrim_4, vtrim_3, vtrim_2, vtrim_1, vtrim_0;
real vtmon, vtmmeas;

analog begin
    vtrim_5 = (NvTrmIref[5] == 1'b1 ? 3.3 : 0.0);
    vtrim_4 = (NvTrmIref[4] == 1'b1 ? 3.3 : 0.0);
    vtrim_3 = (NvTrmIref[3] == 1'b1 ? 3.3 : 0.0);
    vtrim_2 = (NvTrmIref[2] == 1'b1 ? 3.3 : 0.0);
    vtrim_1 = (NvTrmIref[1] == 1'b1 ? 3.3 : 0.0);
    vtrim_0 = (NvTrmIref[0] == 1'b1 ? 3.3 : 0.0);

    vtmon   = (TMIRefOni == 1'b1 ? 3.3 : 0.0);
    vtmmeas = (TMIRefMeasi == 1'b1 ? 3.3 : 0.0);

    V(aTrimRef_5, aVss) <+ transition(vtrim_5, 0, 10e-09, 10e-09);
    V(aTrimRef_4, aVss) <+ transition(vtrim_4, 0, 10e-09, 10e-09);
    V(aTrimRef_3, aVss) <+ transition(vtrim_3, 0, 10e-09, 10e-09);
    V(aTrimRef_2, aVss) <+ transition(vtrim_2, 0, 10e-09, 10e-09);
    V(aTrimRef_1, aVss) <+ transition(vtrim_1, 0, 10e-09, 10e-09);
    V(aTrimRef_0, aVss) <+ transition(vtrim_0, 0, 10e-09, 10e-09);

    V(eTMIRefOn, aVss)   <+ transition(vtmon, 0, 10e-09, 10e-09);
    V(eTMIRefMeas, aVss) <+ transition(vtmmeas, 0, 10e-09, 10e-09);
end

Bias_A1 I_Bias (
    .En(aVdd),
    .IRefTMO(dIRefTMO),
    .SUB(aVss),
    .TMIRefMeas(eTMIRefMeas),
    .TMIRefOn(eTMIRefOn),
    .VBNC(VBNC),
    .VBNC1(VBNC),
    .aVdd(aVdd),
    .aVss(aVss),
    .ibp_250n_0(net1),
    .rgTrim_IRef_5(aTrimRef_5),
    .rgTrim_IRef_4(aTrimRef_4),
    .rgTrim_IRef_3(aTrimRef_3),
    .rgTrim_IRef_2(aTrimRef_2),
    .rgTrim_IRef_1(aTrimRef_1),
    .rgTrim_IRef_0(aTrimRef_0),
    .xIRefTMIO(GPIO8)
);

Buffer_DIG I_BUF1 ( .out(TMIRefOni), .in(TMIRefOn));
Buffer_DIG I_BUF2 ( .out(TMIRefMeasi), .in(TMIRefMeas));

endmodule
"""

        # 4. Clean Board_A1 Module Definition (wraps TOP_A1)
        board_a1_block = f"""
// Specialized 3.3V Board_A1 Module
`timescale 1ns / 1ns 

`worklib {lib_name}
`view schematic

(* cds_ams_schematic *) 
module Board_A1 (dIRefTMO, GPIO8, aVdd, aVss, NvTrmIref, TMIRefMeas, TMIRefOn);
output dIRefTMO;
inout GPIO8, aVdd, aVss;
input TMIRefMeas, TMIRefOn;
input [5:0] NvTrmIref;

TOP_A1 TOP (
    .GPIO8(GPIO8),
    .aVdd(aVdd),
    .aVss(aVss),
    .dIRefTMO(dIRefTMO),
    .NvTrmIref(NvTrmIref[5:0]),
    .TMIRefMeas(TMIRefMeas),
    .TMIRefOn(TMIRefOn)
);

endmodule
"""

        # 5. Determine TB block with exact schematic instance names: Board & TESTER
        if "python" in top_cell or "sv" in top_cell:
            tb_block = f"""
// Exact Schematic Top Module for {top_cell}
`timescale 1ns / 1ns 

`worklib {lib_name}
`view schematic

(* cds_ams_schematic *) 
module {top_cell} ();

wire [5:0] NvTrmIref;
wire TMIRefOn, TMIRefMeas, dIRefTMO;
wire CLK, dDone;
electrical VDD_PCB, VSS_PCB, GPIO8;
ground VSS_PCB;

real i_isar_val;
real r_gpio8_shunt;

analog begin
    // Power Supply on VDD_PCB (3.3V) and VSS_PCB (0V ground)
    V(VDD_PCB, VSS_PCB) <+ transition(3.3, 0, 10e-06);

    // Calibration Mode: Force 2uA ISARC into GPIO8 during Trim Mode (390us ~ 1.35ms)
    i_isar_val = ($abstime >= 390e-06 && $abstime <= 1.35e-03) ? 2.0e-6 : 0.0;
    I(VDD_PCB, GPIO8) <+ transition(i_isar_val, 0, 10e-09);

    // Measurement Mode: Pull GPIO8 to ground via 1mOhm shunt (>= 1.40ms)
    r_gpio8_shunt = ($abstime >= 1.40e-03) ? 1e-3 : 1e9;
    I(GPIO8, VSS_PCB) <+ V(GPIO8, VSS_PCB) / transition(r_gpio8_shunt, 0, 10e-09);
end

// Board_A1 Instance: Board
Board_A1 Board (
    .GPIO8(GPIO8),
    .dIRefTMO(dIRefTMO),
    .NvTrmIref(NvTrmIref[5:0]),
    .aVss(VSS_PCB),
    .aVdd(VDD_PCB),
    .TMIRefOn(TMIRefOn),
    .TMIRefMeas(TMIRefMeas)
);

// py_tester Instance: TESTER
py_tester TESTER (
    .TMIRefOn(TMIRefOn),
    .TMIRefMeas(TMIRefMeas),
    .CLK(CLK),
    .dDone(dDone),
    .NvTrmIref(NvTrmIref[5:0]),
    .dIRefTMO(dIRefTMO)
);

endmodule
"""
            amsbind_content = f"""// Binding AMSD Control Block for {lib_name}.{top_cell}:config
amsd {{
\tconfig designtop="{lib_name}.{top_cell}:schematic"

\tconfig cell="Buffer_DIG" lib="{lib_name}" view="functional"
\tconfig cell="Board_A1" lib="{lib_name}" view="schematic"
\tconfig cell="TOP_A1" lib="{lib_name}" view="schematic"
\tconfig cell="Bias_A1" lib="{lib_name}" view="analogtext"
}}
"""
            text_inputs = f"""// HDL file for Lib - {lib_name} ,Cell - Buffer_DIG, View - functional
-amscompilefile "file:/home/lary/project/BVU025/SCH/{lib_name}/Buffer_DIG/functional/verilog.v lib:{lib_name} cell:Buffer_DIG view:functional"

// HDL file for Lib - {lib_name} ,Cell - py_tester, View - systemVerilog
-amscompilefile "file:/home/lary/project/BVU025/SCH/{lib_name}/py_tester/systemVerilog/verilog.sv lib:{lib_name} cell:py_tester view:systemVerilog"

-makelib umc18cdmos
-endlib
-makelib {lib_name}
-endlib
"""
        else:
            # Condition B
            tb_block = f"""
`timescale 1ns / 1ns 

`worklib {lib_name}
`view schematic

(* cds_ams_schematic *) 
module {top_cell} ();

wire [5:0] NvTrmIref;
wire dDone, CLK, dIRefTMO;
electrical aVdd, aVss, DVDD_Trm, POR, TMIRefOn, TMIRefMeas, net5, net6, net4, net7, GPIO8, IREF_TrmCode;
ground aVss;

analog begin
    V(aVdd, aVss) <+ transition(3.3, 0, 10e-06);
    V(DVDD_Trm, aVss) <+ transition(($abstime < 400e-06 ? 0.0 : 3.3), 0, 1e-09, 1e-09);
    V(POR, aVss) <+ transition(($abstime < 400e-06 ? 0.0 : ($abstime < 1.4e-03 ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(TMIRefOn, aVss) <+ transition(($abstime < 390e-06 ? 0.0 : ($abstime < 1.4e-03 ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(TMIRefMeas, aVss) <+ transition(($abstime < 1.41e-03 ? 0.0 : 3.3), 0, 1e-09, 1e-09);
    V(net5, aVss) <+ transition(($abstime < 400e-06 ? 0.0 : ($abstime < 1.2e-03 ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(net6, aVss) <+ transition(($abstime < 400e-06 ? 0.0 : ((($abstime - 400e-06) - floor(($abstime - 400e-06)/100e-06)*100e-06 < 50e-06) ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(net4, aVss) <+ transition(($abstime < 400e-06 ? 0.0 : ($abstime < 1.2e-03 ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(net7, aVss) <+ transition(($abstime < 1.4e-03 ? 0.0 : ($abstime < 1.8e-03 ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    
    if ($abstime >= 400e-06 && $abstime <= 1.2e-03)
        I(aVdd, GPIO8) <+ 2.0e-6;
    else
        I(aVdd, GPIO8) <+ 0.0;
        
    I(GPIO8, aVss) <+ V(GPIO8, aVss) / ($abstime >= 1.40e-03 ? 1e-3 : 1e9);
end

vaVDAC6b_FIXED #( .transmission_delay_max(1e-09), .transmission_delay(1e-11) 
    , .threshold_low(0.25), .slew_rate_positive(1e+06), .slew_rate_negative(-1e+06) 
    , .threshold_high(0.75), .mode_decimal_display(1) ) I_Code ( 
    .VSS(aVss), .VDD(DVDD_Trm), .VO(IREF_TrmCode), 
    .DI(NvTrmIref));

vaSAR6b #( .threshold_low(0.25), .threshold_high(0.75), .comp_invert(1), .fall_time(1e-09) 
    , .rise_time(1e-09), .delay(1e-11) ) I_SAR6b ( 
    .VSS(aVss), .VDD(DVDD_Trm), .CODE(NvTrmIref), 
    .DONE(dDone), .EN(POR), .CLK(CLK), .CMP(dIRefTMO));

AN2x1 I_CLKCtl ( 
    .VSS(aVss), .VDD(DVDD_Trm), .Z(CLK), 
    .A(net5), .B(net6));

TOP_A1 I_Bias ( 
    .GPIO8(GPIO8), .dIRefTMO(dIRefTMO), 
    .NvTrmIref(NvTrmIref[5:0]), .aVss(aVss), .aVdd(aVdd), 
    .TMIRefOn(TMIRefOn), .TMIRefMeas(TMIRefMeas));

endmodule
"""
            amsbind_content = f"""// Binding AMSD Control Block for {lib_name}.{top_cell}
amsd {{
\tconfig designtop="{lib_name}.{top_cell}:schematic"

\tconfig cell="vaSAR6b" lib="{lib_name}" view="veriloga" stopview="yes"
\tconfig cell="vaVDAC6b_FIXED" lib="{lib_name}" view="veriloga" stopview="yes"
\tconfig cell="Buffer_DIG" lib="{lib_name}" view="functional"
\tconfig cell="TOP_A1" lib="{lib_name}" view="schematic"
\tconfig cell="Bias_A1" lib="{lib_name}" view="analogtext"
\tconfig cell="AN2x1" lib="{lib_name}" view="analogtext"
}}
"""
            text_inputs = f"""// HDL file for Lib - {lib_name} ,Cell - Buffer_DIG, View - functional
-amscompilefile "file:/home/lary/project/BVU025/SCH/{lib_name}/Buffer_DIG/functional/verilog.v lib:{lib_name} cell:Buffer_DIG view:functional"

// HDL file for Lib - {lib_name} ,Cell - vaSAR6b, View - veriloga
-amscompilefile "file:/home/lary/project/BVU025/SCH/{lib_name}/vaSAR6b/veriloga/veriloga.va ftype:va lib:{lib_name} cell:vaSAR6b view:veriloga"

// HDL file for Lib - {lib_name} ,Cell - vaVDAC6b_FIXED, View - veriloga
-amscompilefile "file:/home/lary/project/BVU025/SCH/{lib_name}/vaVDAC6b_FIXED/veriloga/veriloga.va ftype:va lib:{lib_name} cell:vaVDAC6b_FIXED view:veriloga"

-makelib umc18cdmos
-endlib
-makelib {lib_name}
-endlib
"""

        # Write netlist.vams with exact schematic nets & instances
        full_vams = h + '\n\n`include "disciplines.vams"\n`include "userDisciplines.vams"\n\n' + hdl + common_digital_helpers + '\n\n' + top_a1_block + '\n\n' + board_a1_block + '\n\n' + tb_block + '\n'
        open('./netlist.vams', 'w').write(full_vams)

        # Subcircuits (strictly extract only lines inside subckt ... ends blocks)
        raw_scs = ""
        bias_subckts_path = f'/home/lary/simulation/BVU025/BVU025A/sim_Bias_cosim_A1/ams/config/netlist/subckts.scs'
        if os.path.exists(bias_subckts_path):
            raw_scs = open(bias_subckts_path).read()
        elif os.path.exists('./analog/netlist'):
            raw_scs = open('./analog/netlist').read()

        clean_lines = ['simulator lang=spectre\nglobal 0\n\n']
        in_subckt = False
        for line in raw_scs.splitlines(True):
            stripped = line.strip()
            if stripped.startswith('subckt '):
                in_subckt = True
            if in_subckt:
                clean_lines.append(line)
            if stripped.startswith('ends') or stripped.startswith('ends '):
                in_subckt = False
                clean_lines.append('\n')

        open('./subckts.scs', 'w').writelines(clean_lines)

        # Update spiceModels.scs
        sm_lines = [l for l in open('./spiceModels.scs').read().splitlines() if 'analog/netlist' not in l and 'subckts.scs' not in l]
        sm_clean = '\n'.join(sm_lines) + '\ninclude "./subckts.scs" amsd_subckt_bind=yes\n'
        open('./spiceModels.scs', 'w').write(sm_clean)

        # Update .amsbind.scs and textInputs
        open('./.amsbind.scs', 'w').write(amsbind_content)
        open('./textInputs', 'w').write(text_inputs)

        # Clean xrunArgs
        args = open('./xrunArgs').read()
        args = args.replace('${IC_INVOKE_DIR}/', f'/home/lary/project/BVU025/SCH/')
        args = args.replace('-sv', '')
        if "python" in top_cell:
            args = args.replace('AN2x1', '').replace('vaSAR6b', '').replace('vaVDAC6b_FIXED', '')
        open('./xrunArgs', 'w').write(args)

        # Update amsControlSpectre.scs with subcircuit probe levels and transistor terminal saves BEFORE tran
        ctrl_raw = open('./amsControlSpectre.scs').read() if os.path.exists('./amsControlSpectre.scs') else ''
        ctrl_clean_lines = [l for l in ctrl_raw.splitlines() if 'subcktprobelvl' not in l and 'save ' not in l]
        ctrl_base = '\n'.join(ctrl_clean_lines)

        save_block = f"""
saveOptions options subcktprobelvl=5 currents=all save=allpub
save {top_cell}.Board.TOP.I_Bias:all
save {top_cell}.Board.TOP.I_Bias.MN0:d
save {top_cell}.Board.TOP.I_Bias.MN0:s
save {top_cell}.Board.TOP.I_Bias.MN0:1
save {top_cell}.Board.TOP.I_Bias.MN0:all
"""
        if 'tran tran' in ctrl_base:
            ctrl_final = ctrl_base.replace('tran tran', save_block + '\ntran tran')
        else:
            ctrl_final = save_block + '\n' + ctrl_base
        open('./amsControlSpectre.scs', 'w').write(ctrl_final)

        # Update probe.tcl with deep hierarchy probe for subcircuit instances
        probe_tcl = f"""
database -open ams_database -into "../psf" -default
probe -create -emptyok -database ams_database -all -depth all {{{top_cell}}}
probe -create -emptyok -database ams_database -flow -depth all {{{top_cell}}}
probe -create -emptyok -database ams_database -flow {{{top_cell}.Board.GPIO8}}
probe -create -emptyok -database ams_database -flow {{{top_cell}.Board.TOP.GPIO8}}
probe -create -emptyok -database ams_database -flow {{{top_cell}.Board.TOP.I_Bias.MN0:d}}
probe -create -emptyok -database ams_database -flow {{{top_cell}.Board.TOP.I_Bias.MN0:1}}
probe -create -emptyok -database ams_database -flow -ports -index -depth all {{{top_cell}}}
"""
        open('./probe.tcl', 'w').write(probe_tcl)

        # Update spiceModels.scs with save for internal terminal currents and port currents
        save_stmts = f"""
save {top_cell}.Board:GPIO8
save {top_cell}.Board.TOP:GPIO8
save {top_cell}.Board.TOP.I_Bias.MN0:d
save {top_cell}.Board.TOP.I_Bias.MN0:s
save {top_cell}.Board.TOP.I_Bias.MN0:1
"""
        sm_content = open('./spiceModels.scs').read()
        if f"{top_cell}.Board.TOP.I_Bias.MN0:d" not in sm_content:
            open('./spiceModels.scs', 'a').write(save_stmts)

        print(f"[Auto-Assemble] Finished auto-assembling {lib_name}.{top_cell} successfully!")

    finally:
        os.chdir(cwd)

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    universal_assemble(target)
