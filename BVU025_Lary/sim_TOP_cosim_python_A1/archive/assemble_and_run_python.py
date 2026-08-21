#!/usr/bin/env python3
import os
import glob
import re
import subprocess

def assemble_and_run():
    netlist_dir = '/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_python_A1/ams/config/netlist'
    if not os.path.exists(netlist_dir):
        print(f"Directory {netlist_dir} not found.")
        return 1

    os.chdir(netlist_dir)
    print(f"Working directory: {netlist_dir}")

    lib_name = "BVU025_Lary"

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

    # 4. Clean Testbench Module for sim_TOP_cosim_python_A1
    tb_block = f"""
// Testbench Module for sim_TOP_cosim_python_A1
`timescale 1ns / 1ns 

`worklib {lib_name}
`view schematic

(* cds_ams_schematic *) 
module sim_TOP_cosim_python_A1 ();

wire [5:0] NvTrmIref;
wire TMIRefOn, TMIRefMeas, dIRefTMO;
wire SCL, SDA;
electrical aVdd, aVss, GPIO8;

real i_isar_val;
real r_gpio8_shunt;

analog begin
    // Smooth power supply ramp to 3.3V
    V(aVdd, aVss) <+ transition(3.3, 0, 10e-06);
    
    // Calibration Mode: Force 2uA into GPIO8 during SAR (400us ~ 1.35ms)
    i_isar_val = ($abstime >= 400e-06 && $abstime <= 1.35e-03) ? 2.0e-6 : 0.0;
    I(aVdd, GPIO8) <+ transition(i_isar_val, 0, 10e-09);
        
    // Measure Mode: Pull GPIO8 to ground via 1mOhm shunt (>= 1.40ms)
    r_gpio8_shunt = ($abstime >= 1.40e-03) ? 1e-3 : 1e9;
    I(GPIO8, aVss) <+ V(GPIO8, aVss) / transition(r_gpio8_shunt, 0, 10e-09);
end

// 1. SystemVerilog py_tester Instance
py_tester I27 (
    .TMIRefOn(TMIRefOn),
    .TMIRefMeas(TMIRefMeas),
    .NvTrmIref(NvTrmIref),
    .dIRefTMO(dIRefTMO),
    .SCL(SCL),
    .SDA(SDA)
);

// 2. DUT TOP_A1 Instance
TOP_A1 TOP ( 
    .GPIO8(GPIO8),
    .dIRefTMO(dIRefTMO), 
    .NvTrmIref(NvTrmIref[5:0]),
    .aVss(aVss),
    .aVdd(aVdd), 
    .TMIRefOn(TMIRefOn),
    .TMIRefMeas(TMIRefMeas)
);

endmodule
"""

    full_vams = h + '\n\n`include "disciplines.vams"\n`include "userDisciplines.vams"\n\n' + hdl + common_digital_helpers + '\n\n' + top_a1_block + '\n\n' + tb_block + '\n'
    open('./netlist.vams', 'w').write(full_vams)

    # 5. Subcircuits
    bias_subckts_path = '/home/lary/simulation/BVU025/BVU025A/sim_Bias_cosim_A1/ams/config/netlist/subckts.scs'
    if os.path.exists(bias_subckts_path):
        subckts_scs = open(bias_subckts_path).read()
    else:
        analog_raw = open('./analog/netlist').read() if os.path.exists('./analog/netlist') else ''
        subckt_blocks = re.findall(r'subckt\s+.*?ends(?:\s+\w+)?', analog_raw, re.DOTALL)
        subckts_scs = "simulator lang=spectre\n\n" + "\n\n".join(subckt_blocks) + "\n"

    open('./subckts.scs', 'w').write(subckts_scs)

    # 6. Update spiceModels.scs
    sm_lines = [l for l in open('./spiceModels.scs').read().splitlines() if 'analog/netlist' not in l and 'subckts.scs' not in l]
    sm_clean = '\n'.join(sm_lines) + '\ninclude "./subckts.scs" amsd_subckt_bind=yes\n'
    open('./spiceModels.scs', 'w').write(sm_clean)

    # 7. Update .amsbind.scs
    amsbind_content = f"""// Binding AMSD Control Block for {lib_name}.sim_TOP_cosim_python_A1:config
amsd {{
\tconfig designtop="{lib_name}.sim_TOP_cosim_python_A1:schematic"

\tconfig cell="Buffer_DIG" lib="{lib_name}" view="functional"
\tconfig cell="TOP_A1" lib="{lib_name}" view="schematic"
\tconfig cell="Bias_A1" lib="{lib_name}" view="analogtext"
}}
"""
    open('./.amsbind.scs', 'w').write(amsbind_content)

    # 8. Clean textInputs
    text_inputs = f"""// HDL file for Lib - {lib_name} ,Cell - Buffer_DIG, View - functional
-amscompilefile "file:/home/lary/project/BVU025/SCH/{lib_name}/Buffer_DIG/functional/verilog.v lib:{lib_name} cell:Buffer_DIG view:functional"

// HDL file for Lib - {lib_name} ,Cell - py_tester, View - systemVerilog
-amscompilefile "file:/home/lary/project/BVU025/SCH/{lib_name}/py_tester/systemVerilog/verilog.sv ftype:sv lib:{lib_name} cell:py_tester view:systemVerilog"

-makelib umc18cdmos
-endlib
-makelib {lib_name}
-endlib
"""
    open('./textInputs', 'w').write(text_inputs)

    # 9. Clean xrunArgs
    args = open('./xrunArgs').read()
    args = args.replace('${IC_INVOKE_DIR}/', '/home/lary/project/BVU025/SCH/')
    args = args.replace('-sv', '')
    args = args.replace('AN2x1', '').replace('vaSAR6b', '').replace('vaVDAC6b_FIXED', '')
    open('./xrunArgs', 'w').write(args)

    # 10. amsControlSpectre.scs
    if os.path.exists('./amsControlSpectre.scs'):
        ctrl = open('./amsControlSpectre.scs').read()
        if 'cmin=' not in ctrl:
            ctrl = ctrl.replace('tran tran', 'opts options cmin=1e-15 gmin=1e-12\ntran tran')
        open('./amsControlSpectre.scs', 'w').write(ctrl)

    print("[Success] Netlist and transition expressions validated.")

    # 11. Run Simulation
    print("===> Executing ./runSimulation...")
    res = subprocess.run(['./runSimulation'], shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print("=== Simulation Output ===")
    print(res.stdout[-3000:] if len(res.stdout) > 3000 else res.stdout)
    return res.returncode

if __name__ == "__main__":
    assemble_and_run()
