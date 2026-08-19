import os
import re
import sys
import time

def run_fix():
    print("Running fix_wrapper...")
    os.chdir('/home/lary/simulation/BVU025/BVU025A/sim_Bias_cosim_A1/ams/config/netlist')
    
    if os.path.exists('./analog/netlist'):
        c = open('./analog/netlist').read()
        
        # Remove buggy definitions
        c = re.sub(r'subckt CMPTM_A1\b[\s\S]*?ends CMPTM_A1', '// CMPTM_A1 removed', c)
        c = re.sub(r'subckt Bias_A1\b[\s\S]*?ends Bias_A1', '// Bias_A1 removed', c)
        c = re.sub(r'subckt AN2x1\b[\s\S]*?ends AN2x1', '// AN2x1 removed', c)
        c = re.sub(r'subckt INVx2\b[\s\S]*?ends INVx2', '// INVx2 removed', c)
        c = re.sub(r'subckt NR2x2\b[\s\S]*?ends NR2x2', '// NR2x2 removed', c)
        
        input_scs_path = '/home/lary/simulation/BVU025/BVU025A/sim_Bias_cosim_A1/spectre/config/netlist/input.scs'
        with open(input_scs_path, 'r') as f:
            input_data = f.read()
            
        blocks_to_extract = [
            'Bias_A1_schematic',
            'CMPTM_A1_schematic',
            'IRef_R_A1_schematic',
            'INVx2_schematic',
            'AN2x1_schematic',
            'NR2x2_schematic',
            'RNHR3000_TG_CDMOS_G3_pcell_0_schematic',
            'RNHR4000_TG_CDMOS_G3_pcell_1_schematic'
        ]
        
        extracted_blocks = []
        for bname in blocks_to_extract:
            m = re.search(rf'(subckt {bname}\b[\s\S]*?ends {bname})', input_data)
            if m:
                extracted_blocks.append(m.group(1))
            else:
                print(f"WARNING: {bname} not found in input.scs!")
                
        all_blocks_str = '\n\n'.join(extracted_blocks)
        all_blocks_str = all_blocks_str.replace('Bias_A1_schematic', 'Bias_A1')
        all_blocks_str = all_blocks_str.replace('CMPTM_A1_schematic', 'CMPTM_A1')
        all_blocks_str = all_blocks_str.replace('AN2x1_schematic', 'AN2x1')
        all_blocks_str = all_blocks_str.replace('NR2x2_schematic', 'NR2x2')
        all_blocks_str = re.sub(r'\\<(\d+)\\>', r'_\1', all_blocks_str)
        
        c += '\n\n// --- EXTRACTED FROM SPECTRE INPUT.SCS ---\n'
        c += all_blocks_str
        c += '\n// ----------------------------------------\n'

        c = re.sub(r'\nI_Bias\s+Bias_A1\b.*', '\n// I_Bias in netlist.vams', c)
        c = re.sub(r'\nI_CLKCtl\s+AN2x1\b.*', '\n// I_CLKCtl in netlist.vams', c)

        header = 'simulator lang=spectre\nglobal 0\nparameters AVIN=3.3 Trim=50u v1=3.3\n\n'
        open('./subckts.scs', 'w').write(header + c + '\n')

    h = open('./.amsOSSHeader').read().strip() if os.path.exists('./.amsOSSHeader') else ''
    hdl = open('./.hdlFileInfo_forNetlist').read().strip() if os.path.exists('./.hdlFileInfo_forNetlist') else ''

    vams_top = '''`timescale 1ns / 1ns 

`worklib BVU025_Lary
`view schematic_SAR

(* cds_ams_schematic *) 
(* dfII_lib="BVU025_Lary", dfII_cell="sim_Bias_cosim_A1", dfII_view="schematic_SAR", worklib_name="BVU025_Lary", view_name="schematic_SAR" *)

module sim_Bias_cosim_A1 ();

wire [5:0] NvTrmIref;
electrical aTrimRef_5, aTrimRef_4, aTrimRef_3, aTrimRef_2, aTrimRef_1, aTrimRef_0;
electrical aVdd, aVss, SUB, TMIRefOn, TMIRefMeas, TMIRefOni, TMIRefMeasi;
electrical CLK, POR, DVDD_Trm, dIRefTMO, IREF_TrmCode, dDone, net3, net5, net6, VBNC, xIRefTMIO;

analog begin
    V(aVss) <+ 0.0;
    V(SUB) <+ 0.0;
    
    V(aVdd, aVss) <+ transition(($abstime < 5e-06 ? 0.0 : 3.3), 5e-06, 5e-06, 5e-06);
    V(DVDD_Trm, aVss) <+ transition(($abstime < 400e-06 ? 0.0 : 3.3), 0, 1e-09, 1e-09);
    V(POR, aVss) <+ transition(($abstime < 400e-06 ? 0.0 : (($abstime < 1.4e-03) ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(TMIRefOn, aVss) <+ transition(($abstime < 390e-06 ? 0.0 : (($abstime < 1.4e-03) ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(TMIRefOni, TMIRefOn) <+ 0.0;
    V(TMIRefMeas, aVss) <+ transition(($abstime < 1.41e-03 ? 0.0 : 3.3), 0, 1e-09, 1e-09);
    V(TMIRefMeasi, TMIRefMeas) <+ 0.0;
    V(net5, aVss) <+ transition(($abstime < 400e-06 ? 0.0 : (($abstime < 1.2e-03) ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    V(net6, aVss) <+ transition(($abstime < 400e-06 ? 0.0 : ((($abstime - 400e-06) - floor(($abstime - 400e-06)/100e-06)*100e-06 < 50e-06) ? 3.3 : 0.0)), 0, 1e-09, 1e-09);
    
    if ($abstime >= 400e-06 && $abstime <= 1.2e-03)
        I(aVdd, xIRefTMIO) <+ 2.0e-6;
    else
        I(aVdd, xIRefTMIO) <+ 0.0;
    
    // Switch W1 to V_IMeas (0V) during measurement phase (>= 1.41ms)
    I(xIRefTMIO, aVss) <+ V(xIRefTMIO, aVss) / ($abstime >= 1.41e-03 ? 1e-3 : 1e9);
    
    // ANALOG BUFFER FOR D2A COUPLING ISOLATION
    V(aTrimRef_5, aVss) <+ transition((NvTrmIref[5] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(aTrimRef_4, aVss) <+ transition((NvTrmIref[4] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(aTrimRef_3, aVss) <+ transition((NvTrmIref[3] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(aTrimRef_2, aVss) <+ transition((NvTrmIref[2] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(aTrimRef_1, aVss) <+ transition((NvTrmIref[1] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
    V(aTrimRef_0, aVss) <+ transition((NvTrmIref[0] == 1'b1 ? 3.3 : 0.0), 0, 1e-09, 1e-09);
end

Bias_A1 I_Bias (
    .En(aVdd),
    .IRefTMO(dIRefTMO),
    .SUB(SUB),
    .TMIRefMeas(TMIRefMeasi),
    .TMIRefOn(TMIRefOni),
    .VBNC(VBNC),
    .VBNC1(VBNC),
    .aVdd(aVdd),
    .aVss(aVss),
    .ibp_250n_0(net3),
    .rgTrim_IRef_5(aTrimRef_5),
    .rgTrim_IRef_4(aTrimRef_4),
    .rgTrim_IRef_3(aTrimRef_3),
    .rgTrim_IRef_2(aTrimRef_2),
    .rgTrim_IRef_1(aTrimRef_1),
    .rgTrim_IRef_0(aTrimRef_0),
    .xIRefTMIO(xIRefTMIO)
);

AN2x1 I_CLKCtl (
    .A(net5),
    .B(net6),
    .VDD(DVDD_Trm),
    .VSS(cds_globals.\\gnd! ),
    .Z(CLK)
);

vaVDAC6b_FIXED #( .transmission_delay_max(1e-09), .transmission_delay(1e-11) 
    , .threshold_low(0.25), .slew_rate_positive(1e+06), .slew_rate_negative(-1e+06) 
    , .threshold_high(0.75), .mode_decimal_display(1) )  I_Code ( 
    .VSS(cds_globals.\\gnd! ), .VDD(DVDD_Trm), .VO(IREF_TrmCode), 
    .DI(NvTrmIref));

vaSAR6b #( .threshold_low(0.25), .threshold_high(0.75), .comp_invert(1), .fall_time(1e-09) 
    , .rise_time(1e-09), .delay(1e-11) )  I_SAR6b ( 
    .VSS(cds_globals.\\gnd! ), .VDD(DVDD_Trm), .CODE(NvTrmIref), 
    .DONE(dDone), .EN(POR), .CLK(CLK), .CMP(dIRefTMO));

endmodule
'''
    vams_content = h + '\n\n`include "disciplines.vams"\n`include "userDisciplines.vams"\n\n' + hdl + '\n\n' + vams_top + '\n'
    open('./netlist.vams', 'w').write(vams_content)

    amsbind = '''// Binding AMSD Control Block for config BVU025_Lary.sim_Bias_cosim_A1:config
amsd {
\tconfig designtop="BVU025_Lary.sim_Bias_cosim_A1:schematic_SAR"
\tconfig cell="vaSAR6b" lib="BVU025_Lary" view="veriloga" stopview="yes"
\tconfig cell="vaVDAC6b_FIXED" lib="BVU025_Lary" view="veriloga" stopview="yes"
\tconfig cell="Bias_A1" lib="BVU025_Lary" view="analogtext"
\tconfig cell="AN2x1" lib="BVU025_Lary" view="analogtext"
}
'''
    open('./.amsbind.scs', 'w').write(amsbind)

    if os.path.exists('./spiceModels.scs'):
        sp_c = open('./spiceModels.scs').read()
        if 'subckts.scs' not in sp_c:
            sp_c += '\ninclude "./subckts.scs" amsd_subckt_bind=yes\n'
            open('./spiceModels.scs', 'w').write(sp_c)

    if os.path.exists('./amsControlSpectre.scs'):
        ctrl_c = open('./amsControlSpectre.scs').read()
        if 'rawfmt=psfxl' not in ctrl_c:
            ctrl_c = ctrl_c.replace('reltol=1e-3', 'reltol=1e-3 cmin=1e-15 max_minstep_nonconv=20 rawfmt=psfxl')
            ctrl_c = ctrl_c.replace('errpreset=conservative', 'errpreset=moderate')
            ctrl_c = ctrl_c.replace('wave_out options rawfmt=uwi uwifmt=sst2:wdf', '// wave_out')
            open('./amsControlSpectre.scs', 'w').write(ctrl_c)

if __name__ == '__main__':
    run_fix()
    print("DEPLOYED SPECTRE EXACT COPY FIX")
    if len(sys.argv) > 1 and sys.argv[1] == '--daemon':
        last_mtime = 0
        target_file = '/home/lary/simulation/BVU025/BVU025A/sim_Bias_cosim_A1/ams/config/netlist/analog/netlist'
        while True:
            try:
                if os.path.exists(target_file):
                    mtime = os.path.getmtime(target_file)
                    if mtime != last_mtime:
                        last_mtime = mtime
                        run_fix()
            except Exception as e:
                pass
            time.sleep(1)
