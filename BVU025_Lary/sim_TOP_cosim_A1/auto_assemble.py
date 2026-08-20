import os
import glob
import re
import sys

def auto_assemble(netlist_dir):
    if not os.path.exists(os.path.join(netlist_dir, 'digital', 'ihnl')):
        return
    
    cwd = os.getcwd()
    try:
        os.chdir(netlist_dir)
        
        # 1. Assemble netlist.vams from ihnl
        ihnl_files = sorted(
            glob.glob('./digital/ihnl/cds*/netlist'), 
            key=lambda x: int(os.path.basename(os.path.dirname(x)).replace('cds', ''))
        )
        if not ihnl_files:
            return

        h = open('./.amsOSSHeader').read() if os.path.exists('./.amsOSSHeader') else ''
        hdl = open('./.hdlFileInfo_forNetlist').read() if os.path.exists('./.hdlFileInfo_forNetlist') else ''
        
        # Load all submodules except sim_TOP_cosim_A1 and TOP_A1 (which will be cleanly defined)
        ihnl_modules = []
        for f in ihnl_files:
            content = open(f).read()
            if 'module sim_TOP_cosim_A1' not in content and 'module TOP_A1' not in content:
                ihnl_modules.append(content)
        
        ihnl_content = '\n\n'.join(ihnl_modules)

        # Buffer_DIG functional module
        buffer_dig_module = """
// Library - BVU025_Lary, Cell - Buffer_DIG, View - functional
`timescale 1ns / 1ns 

`worklib BVU025_Lary
`view functional

module Buffer_DIG (out, in);
output out;
input in;
assign out = in;
endmodule
"""

        # TOP_A1 module with analog trim bit drivers
        top_a1_module = """
// Library - BVU025_Lary, Cell - TOP_A1, View - schematic
`timescale 1ns / 1ns 

`worklib BVU025_Lary
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

// Analog Drivers for 3.3V levels into Bias_A1
analog begin
    V(aTrimRef_5, aVss) <+ transition((NvTrmIref[5] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(aTrimRef_4, aVss) <+ transition((NvTrmIref[4] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(aTrimRef_3, aVss) <+ transition((NvTrmIref[3] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(aTrimRef_2, aVss) <+ transition((NvTrmIref[2] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(aTrimRef_1, aVss) <+ transition((NvTrmIref[1] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(aTrimRef_0, aVss) <+ transition((NvTrmIref[0] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);

    V(eTMIRefOn, aVss)   <+ transition((TMIRefOni == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(eTMIRefMeas, aVss) <+ transition((TMIRefMeasi == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
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

        # Define complete sim_TOP_cosim_A1 with internal mixed-signal stimulus
        sim_top_module = """
// Library - BVU025_Lary, Cell - sim_TOP_cosim_A1, View - schematic
`timescale 1ns / 1ns 

`worklib BVU025_Lary
`view schematic

(* cds_ams_schematic *) 
module sim_TOP_cosim_A1 ();

wire [5:0] NvTrmIref;
wire dDone, CLK, dIRefTMO;
electrical aVdd, aVss, DVDD_Trm, POR, TMIRefOn, TMIRefMeas, net5, net6, net4, net7, GPIO8, IREF_TrmCode;

// Analog stimulus for co-simulation testbench
analog begin
    // Power Supplies
    V(aVdd, cds_globals.\\gnd! ) <+ transition(($abstime < 10e-06 ? 3.3*$abstime/10e-06 : 3.3), 0, 1e-09, 1e-09);
    V(aVss, cds_globals.\\gnd! ) <+ 0.0;
    V(DVDD_Trm, cds_globals.\\gnd! ) <+ transition(($abstime < 400e-06 ? 0.0 : 3.3), 0, 1e-09, 1e-09);
    
    // Control Signals
    V(POR, cds_globals.\\gnd! ) <+ transition(($abstime < 400e-06 ? 0.0 : ($abstime < 1.4e-03 ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(TMIRefOn, cds_globals.\\gnd! ) <+ transition(($abstime < 390e-06 ? 0.0 : ($abstime < 1.4e-03 ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(TMIRefMeas, cds_globals.\\gnd! ) <+ transition(($abstime < 1.41e-03 ? 0.0 : 3.3), 0, 1e-09, 1e-09);
    
    // Clock Stimulus
    V(net5, cds_globals.\\gnd! ) <+ transition(($abstime < 400e-06 ? 0.0 : ($abstime < 1.2e-03 ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(net6, cds_globals.\\gnd! ) <+ transition(($abstime < 400e-06 ? 0.0 : ((($abstime - 400e-06) - floor(($abstime - 400e-06)/100e-06)*100e-06 < 50e-06) ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    
    // Current Stimulus & Measurement Switch Control
    V(net4, cds_globals.\\gnd! ) <+ transition(($abstime < 400e-06 ? 0.0 : ($abstime < 1.2e-03 ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(net7, cds_globals.\\gnd! ) <+ transition(($abstime < 1.4e-03 ? 0.0 : ($abstime < 1.8e-03 ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    
    // ISAR Current source (2uA during SAR calibration)
    if ($abstime >= 400e-06 && $abstime <= 1.2e-03)
        I(aVdd, GPIO8) <+ 2.0e-6;
    else
        I(aVdd, GPIO8) <+ 0.0;
    
    // Switch W1 to Measurement Ground (0V) during measurement phase (>= 1.40ms)
    I(GPIO8, cds_globals.\\gnd! ) <+ V(GPIO8, cds_globals.\\gnd! ) / ($abstime >= 1.40e-03 ? 1e-3 : 1e9);
end

vaVDAC6b_FIXED #( .transmission_delay_max(1e-09), .transmission_delay(1e-11) 
    , .threshold_low(0.25), .slew_rate_positive(1e+06), .slew_rate_negative(-1e+06) 
    , .threshold_high(0.75), .mode_decimal_display(1) )  I_Code ( 
    .VSS(cds_globals.\\gnd! ), .VDD(DVDD_Trm), .VO(IREF_TrmCode), 
    .DI(NvTrmIref));

vaSAR6b #( .threshold_low(0.25), .threshold_high(0.75), .comp_invert(1), .fall_time(1e-09) 
    , .rise_time(1e-09), .delay(1e-11) )  I_SAR6b ( 
    .VSS(cds_globals.\\gnd! ), .VDD(DVDD_Trm), .CODE(NvTrmIref), 
    .DONE(dDone), .EN(POR), .CLK(CLK), .CMP(dIRefTMO));

AN2x1 I_CLKCtl ( 
    .VSS(cds_globals.\\gnd! ), .VDD(DVDD_Trm), .Z(CLK), 
    .A(net5), .B(net6));

TOP_A1 I_Bias ( 
    .GPIO8(GPIO8), .dIRefTMO(dIRefTMO), 
    .NvTrmIref(NvTrmIref[5:0]), .aVss(aVss), .aVdd(aVdd), 
    .TMIRefOn(TMIRefOn), .TMIRefMeas(TMIRefMeas));

endmodule
"""

        full_vams = h + '\n\n`include "disciplines.vams"\n`include "userDisciplines.vams"\n\n' + hdl + buffer_dig_module + '\n\n' + ihnl_content + '\n\n' + top_a1_module + '\n\n' + sim_top_module + '\n'
        open('./netlist.vams', 'w').write(full_vams)

        # 2. Build subckts.scs from analog/netlist
        bias_subckts_path = '/home/lary/simulation/BVU025/BVU025A/sim_Bias_cosim_A1/ams/config/netlist/subckts.scs'
        if os.path.exists(bias_subckts_path):
            subckts_scs = open(bias_subckts_path).read()
        else:
            subckts_scs = "simulator lang=spectre\n\n"
        
        if 'subckt AN2x1' not in subckts_scs and os.path.exists('./analog/netlist'):
            an2x1_block = re.search(r'subckt AN2x1.*?ends AN2x1', open('./analog/netlist').read(), re.DOTALL)
            if an2x1_block:
                subckts_scs += "\n\n" + an2x1_block.group(0) + "\n"
        
        open('./subckts.scs', 'w').write(subckts_scs)

        # 3. Clean and enforce .amsbind.scs
        amsbind_content = """// Binding AMSD Control Block
amsd {
\tconfig designtop="BVU025_Lary.sim_TOP_cosim_A1:schematic"

\tconfig cell="vaSAR6b" lib="BVU025_Lary" view="veriloga" stopview="yes"
\tconfig cell="vaVDAC6b_FIXED" lib="BVU025_Lary" view="veriloga" stopview="yes"
\tconfig cell="Buffer_DIG" lib="BVU025_Lary" view="functional"
\tconfig cell="TOP_A1" lib="BVU025_Lary" view="schematic"
\tconfig cell="Bias_A1" lib="BVU025_Lary" view="analogtext"
\tconfig cell="AN2x1" lib="BVU025_Lary" view="analogtext"
}
"""
        open('./.amsbind.scs', 'w').write(amsbind_content)

        # 4. Ensure spiceModels.scs includes subckts.scs
        if os.path.exists('./spiceModels.scs'):
            sm_lines = [l for l in open('./spiceModels.scs').read().splitlines() if 'analog/netlist' not in l and 'subckts.scs' not in l]
            sm_clean = '\n'.join(sm_lines) + '\ninclude "./subckts.scs" amsd_subckt_bind=yes\n'
            open('./spiceModels.scs', 'w').write(sm_clean)

        # 5. Set Connect Rules vsup=3.3V in ie_card.scs
        ie_content = """
// Connect Rules (3.3V full-swing for CDMOS)
amsd{
    ie vsup=3.3 discipline=logic 
}
"""
        open('./ie_card.scs', 'w').write(ie_content)

        # 6. Ensure textInputs creates BVU025_Lary library
        if os.path.exists('./textInputs'):
            ti = open('./textInputs').read()
            if '-makelib BVU025_Lary' not in ti:
                ti += '\n-makelib BVU025_Lary\n-endlib\n'
                open('./textInputs', 'w').write(ti)

        # 7. Assemble complete .completeDesignInfo.ckt
        globals_v = open('./cds_globals.vams').read() if os.path.exists('./cds_globals.vams') else ''
        ams_ctrl = open('./amsControlSpectre.scs').read() if os.path.exists('./amsControlSpectre.scs') else ''
        probe = open('./probe.tcl').read() if os.path.exists('./probe.tcl') else ''

        full_info = full_vams + '\n\n' + globals_v + '\n\n// Cadence AMS Control File\n' + ams_ctrl + '\n\n// Connect Rules\n' + ie_content + '\n\n// Probe commands\n' + probe
        open('./.completeDesignInfo.ckt', 'w').write(full_info)

        print(f"[Auto-Assemble] Successfully assembled TOP_A1 with electrical ports and 3.3V logic discipline!")
    finally:
        os.chdir(cwd)

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    auto_assemble(target)
