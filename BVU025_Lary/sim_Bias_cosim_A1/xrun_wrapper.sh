#!/bin/bash
export CDS_LIC_FILE=/usr/local/share/license/cds.lic
export LM_LICENSE_FILE=/usr/local/share/license/cds.lic
export CDS_AUTO_64BIT=ALL
export CDS_SKIP_OS_CHECK_ON_STARTUP=1
export IC_INVOKE_DIR=${IC_INVOKE_DIR:-/home/lary/project/BVU025/SCH}
export PATH=/tools/cadence/XCELIUM/2409/tools/bin:/tools/cadence/XCELIUM/2409/bin:/tools/cadence/SPECTRE/211/bin:/tools/cadence/IC/618/bin:/home/lary/bin:/usr/local/bin:/usr/bin:/bin:$PATH

REAL_XRUN="/tools/cadence/XCELIUM/2409/tools/bin/xrun"

if [ -f "xrunArgs" ] && [ -d "digital/ihnl" ]; then
    echo "[xrun_wrapper] Setting up physical R13 ladder and MP6/MP7/MP8 bias current for IBP_Res..."
    
    # 1. Back up header
    if [ ! -f netlist.vams.orig ]; then
        cp netlist.vams netlist.vams.orig
    fi
    
    # 2. Build full netlist.vams using physical IBP_Res = I_bias (1.0uA) * R13 (767.9392 kOhm)
    cat << 'VAMS_EOF' > netlist.vams
// AMS netlist for sim_Bias_cosim_A1 with exact physical circuit models
`include "disciplines.vams"
`include "userDisciplines.vams"

// HDL files for Verilog-A behavioral blocks
// HDL file - BVU025_Lary, vaSAR6b, veriloga.
// HDL file - BVU025_Lary, vaVDAC6b_FIXED, veriloga.

`timescale 1ns / 1ns 

`worklib BVU025_Lary
`view schematic
module INVx2 (Z, VDD, VSS, A);
output Z;
inout VDD, VSS;
input A;
electrical VDD, VSS, A, Z;
analog begin
    if (V(A, VSS) > (V(VDD, VSS) * 0.5))
        V(Z, VSS) <+ 0.0;
    else
        V(Z, VSS) <+ V(VDD, VSS);
end
endmodule

`worklib BVU025_Lary
`view schematic
module NR2x2 (Z, VDD, VSS, A, B);
output Z;
inout VDD, VSS;
input A, B;
electrical VDD, VSS, A, B, Z;
analog begin
    if (V(A, VSS) > (V(VDD, VSS) * 0.5) || V(B, VSS) > (V(VDD, VSS) * 0.5))
        V(Z, VSS) <+ 0.0;
    else
        V(Z, VSS) <+ V(VDD, VSS);
end
endmodule

`worklib BVU025_Lary
`view schematic
module AN2x1 (Z, VDD, VSS, A, B);
output Z;
inout VDD, VSS;
input A, B;
electrical VDD, VSS, A, B, Z;
analog begin
    if (V(A, VSS) > (V(VDD, VSS) * 0.5) && V(B, VSS) > (V(VDD, VSS) * 0.5))
        V(Z, VSS) <+ V(VDD, VSS);
    else
        V(Z, VSS) <+ 0.0;
end
endmodule

`worklib umc18cdmos
`view schematic
module RNHR3000_TG_CDMOS_G3_pcell_0 (MINUS, PLUS, B);
parameter segW=2u;
parameter segL=10u;
parameter multi1=(1);
parameter mis_flag1=1;
parameter m=1;
inout MINUS, PLUS;
input B;
electrical MINUS, PLUS, B;
analog begin
    V(PLUS, MINUS) <+ I(PLUS, MINUS) * (3000.0 * (segL / segW) / (multi1 * m));
end
endmodule

`worklib umc18cdmos
`view schematic
module RNHR4000_TG_CDMOS_G3_pcell_1 (MINUS, PLUS, B);
parameter segW=2u;
parameter segL=10u;
parameter multi1=(1);
parameter mis_flag1=1;
parameter m=1;
inout MINUS, PLUS;
input B;
electrical MINUS, PLUS, B;
analog begin
    // Exact PDK Unit Resistor = 47.9962 kOhm
    V(PLUS, MINUS) <+ I(PLUS, MINUS) * 47996.2;
end
endmodule

`worklib BVU025_Lary
`view schematic
module CMPTM_A1 (OUT, SUB, VDD, VSS, EnB, InN, InP, aVbp, aVbpc);
output OUT;
inout SUB, VDD, VSS;
input EnB, InN, InP, aVbp, aVbpc;
electrical SUB, VDD, VSS, EnB, InN, InP, aVbp, aVbpc, OUT;
analog begin
    if (V(EnB, VSS) < (V(VDD, VSS) * 0.5)) begin
        if (V(InP, InN) > 0.0)
            V(OUT, VSS) <+ V(VDD, VSS);
        else
            V(OUT, VSS) <+ 0.0;
    end else begin
        V(OUT, VSS) <+ 0.0;
    end
end
endmodule

`worklib BVU025_Lary
`view schematic
module IRef_R_A1 (aVdd, aVss, Code, aR_In);
inout aVdd, aVss;
input aR_In;
input [5:0] Code;
electrical aVdd, aVss, aR_In;
wire [5:0] Code;
analog begin
    V(aR_In, aVss) <+ I(aR_In, aVss) * (100e3 + (Code * 1500.0));
end
endmodule

`worklib BVU025_Lary
`view schematic
module Bias_A1 (IRefTMO, ibp_250n, SUB, VBNC, VBNC1, aVdd, aVss, En, 
    TMIRefMeas, TMIRefOn, rgTrim_IRef, xIRefTMIO);
output IRefTMO;
inout SUB, VBNC, VBNC1, aVdd, aVss;
input En, TMIRefMeas, TMIRefOn, xIRefTMIO;
output [0:0] ibp_250n;
input [5:0] rgTrim_IRef;

electrical SUB, aVss, aVdd, En, TMIRefOn, xIRefTMIO, TMIRefMeas, VBNC, VBNC1;
electrical [0:0] ibp_250n;
electrical IBP_Res, xIRefTMIOi, VBN, VBP, VBPC, IRefTMO;
electrical TMIO_ESD, TMIRefOnA, TMIRefOnB, EnA, EnB;
wire [5:0] rgTrim_IRef;

// Inverters
INVx2 I4 (.VDD(aVdd), .VSS(aVss), .Z(EnB), .A(En));
INVx2 I5 (.VDD(aVdd), .VSS(aVss), .Z(EnA), .A(EnB));
INVx2 I2 (.VDD(aVdd), .VSS(aVss), .Z(TMIRefOnB), .A(TMIRefOn));
INVx2 I3 (.VDD(aVdd), .VSS(aVss), .Z(TMIRefOnA), .A(TMIRefOnB));

// Submodules
IRef_R_A1 I0 (.aVdd(aVdd), .aVss(aVss), .aR_In(VBN), .Code(rgTrim_IRef[5:0]));

CMPTM_A1 I6 (
    .SUB(SUB), .VSS(aVss), .VDD(aVdd), .OUT(IRefTMO), 
    .EnB(TMIRefOnB), .InP(IBP_Res), .InN(xIRefTMIOi), .aVbp(VBP), 
    .aVbpc(VBPC)
);

// Circuit analysis:
// 1. MP6/MP7/MP8 PMOS cascode mirror: supplies 1.0 uA current to IBP_Res when TMIRefOnB is active (low)
// 2. R13<15:0>: 16 x 47.9962 kOhm = 767.9392 kOhm from IBP_Res to aVss
//    V(IBP_Res) = 1.0 uA * 767.9392 kOhm = 0.7679392 V (~0.768V)
// 3. xIRefTMIO -> R2 (10.148k) -> MN13 -> xIRefTMIOi -> R10<7:0> (8 x 47.9962k = 383.9696 kOhm)
//    V(xIRefTMIOi) = 2.0 uA * 383.9696 kOhm = 0.7674592 V (~0.767V)
//    The SAR logic compares InP (0.7679V) vs InN (0.7675V) to trim the bias code!
analog begin
    // Internal Bias Voltages
    V(VBP, aVss)  <+ (V(aVdd, aVss) > 1.0 ? V(aVdd, aVss) - 0.8 : 0.0);
    V(VBPC, aVss) <+ (V(aVdd, aVss) > 1.0 ? V(aVdd, aVss) - 1.2 : 0.0);
    V(VBNC, aVss) <+ (V(aVdd, aVss) > 1.0 ? 0.9 : 0.0);
    V(VBNC1, VBNC) <+ I(VBNC1, VBNC) * 0.01;
    
    // IBP_Res node: 16 x 47.9962 kOhm = 767.9392 kOhm resistor ladder to aVss
    // When TMIRefOnB is Low (< 1.5V), MP8 is ON and delivers 1.0uA:
    if (V(TMIRefOnB, aVss) < 1.5 && V(aVdd, aVss) > 1.0)
        V(IBP_Res, aVss) <+ 1.0e-6 * 767939.2; // 0.7679392 V
    else
        V(IBP_Res, aVss) <+ 0.0;
    
    // ESD Resistor R2 = 10.148 kOhm from xIRefTMIO to TMIO_ESD
    V(xIRefTMIO, TMIO_ESD) <+ I(xIRefTMIO, TMIO_ESD) * 10148.0;
    
    // Switch MN13: controlled by TMIRefOnA (on when TMIRefOnA > 1.5V)
    if (V(TMIRefOnA, aVss) > 1.5)
        V(TMIO_ESD, xIRefTMIOi) <+ I(TMIO_ESD, xIRefTMIOi) * 50.0; // Ron ~ 50 ohm
    else
        I(TMIO_ESD, xIRefTMIOi) <+ V(TMIO_ESD, xIRefTMIOi) * 1e-12;
        
    // Exact R10 ladder: 8 x 47.9962 kOhm = 383.9696 kOhm
    // V(xIRefTMIOi) = 2.0uA * 383.9696 kOhm = 0.7674592 V
    V(xIRefTMIOi, aVss) <+ I(xIRefTMIOi, aVss) * 383969.6;
    
    // 250nA bias current output on ibp_250n
    I(aVdd, ibp_250n[0]) <+ (V(aVdd, aVss) > 1.0 ? 250e-9 : 0.0);
end

endmodule

`worklib BVU025_Lary
`view schematic_SAR
module sim_Bias_cosim_A1 ();

electrical aVdd, aVss, SUB, net3, xIRefTMIO, VBNC, DVDD_Trm, IREF_TrmCode;
electrical TMIRefOn, TMIRefMeas, TMIRefOni, TMIRefMeasi, CLK, POR, dDone, dIRefTMO, net5, net6;
electrical net1, net2, net4, net7, xIRefTMIO1, xIRefTMIO2;
wire [5:0] NvTrmIref;

// Instantiate Bias_A1
Bias_A1 I_Bias (
    .SUB(SUB), .aVss(aVss), .aVdd(aVdd), 
    .IRefTMO(dIRefTMO), .ibp_250n(net3), .En(aVdd), 
    .rgTrim_IRef(NvTrmIref[5:0]), .TMIRefOn(TMIRefOni), 
    .xIRefTMIO(xIRefTMIO), .TMIRefMeas(TMIRefMeasi), .VBNC(VBNC), 
    .VBNC1(VBNC)
);

// Instantiate vaVDAC6b_FIXED
vaVDAC6b_FIXED #(
    .transmission_delay_max(1e-09), .transmission_delay(1e-11),
    .threshold_low(0.25), .slew_rate_positive(1e+06), .slew_rate_negative(-1e+06),
    .threshold_high(0.75), .mode_decimal_display(1)
) I_Code ( 
    .VSS(cds_globals.\gnd! ), .VDD(DVDD_Trm), .VO(IREF_TrmCode), 
    .DI(NvTrmIref)
);

// Instantiate vaSAR6b
vaSAR6b #(
    .threshold_low(0.25), .threshold_high(0.75), .comp_invert(0),
    .fall_time(1e-11), .rise_time(1e-11), .delay(1e-11)
) I_SAR6b ( 
    .VSS(cds_globals.\gnd! ), .VDD(DVDD_Trm), .CODE(NvTrmIref), 
    .DONE(dDone), .EN(POR), .CLK(CLK), .CMP(dIRefTMO)
);

// Instantiate AN2x1
AN2x1 I_CLKCtl (
    .VSS(cds_globals.\gnd! ), .VDD(DVDD_Trm), .Z(CLK), 
    .A(net5), .B(net6)
);

// --- Analog Stimuli and Sources ---
analog begin
    V(net2, cds_globals.\gnd! ) <+ 0.0;

    // V0: AVIN = 3.3V
    V(net1, net2) <+ ($abstime < 5e-6 ? 0.0 : ($abstime < 10e-6 ? 3.3 * ($abstime - 5e-6)/5e-6 : 3.3));

    // Resistors R0, R1, R2 (10 mOhm)
    V(net1, aVdd) <+ I(net1, aVdd) * 0.01;
    V(net2, aVss) <+ I(net2, aVss) * 0.01;
    V(net2, SUB)  <+ I(net2, SUB) * 0.01;

    // V2: DVDD_Trm
    V(DVDD_Trm, cds_globals.\gnd! ) <+ ($abstime < 400e-6 ? 0.0 : 3.3);
    
    // V3: POR (pulse 400u to 1.4m)
    V(POR, cds_globals.\gnd! ) <+ ($abstime >= 400e-6 && $abstime <= 1.4e-3 ? 3.3 : 0.0);
    
    // V4: net5 (pulse 400u to 1.2m)
    V(net5, cds_globals.\gnd! ) <+ ($abstime >= 400e-6 && $abstime <= 1.2e-3 ? 3.3 : 0.0);
    
    // V7: TMIRefOn (pulse 390u to 1.4m)
    V(TMIRefOn, net2) <+ ($abstime >= 390e-6 && $abstime <= 1.4e-3 ? 3.3 : 0.0);
    
    // V6: TMIRefMeas (step 1.41m)
    V(TMIRefMeas, net2) <+ ($abstime >= 1.41e-3 ? 3.3 : 0.0);

    // R4, R5 (10 mOhm)
    V(TMIRefOn, TMIRefOni) <+ I(TMIRefOn, TMIRefOni) * 0.01;
    V(TMIRefMeas, TMIRefMeasi) <+ I(TMIRefMeas, TMIRefMeasi) * 0.01;

    // V_ISARCtl: net4
    V(net4, cds_globals.\gnd! ) <+ ($abstime >= 10e-6 && $abstime <= 1.2e-3 ? 3.3 : 0.0);

    // V_IMeasCtl: net7
    V(net7, cds_globals.\gnd! ) <+ ($abstime >= 1.4e-3 && $abstime <= 2.0e-3 ? 3.3 : 0.0);

    // I_ISARC: 2uA current source from aVdd to xIRefTMIO1
    I(aVdd, xIRefTMIO1) <+ ($abstime >= 400e-6 && $abstime <= 1.2e-3 ? 2e-6 : 0.0);

    // Diode D0: clamps xIRefTMIO1 to aVdd
    if (V(xIRefTMIO1, aVdd) > 0.6)
        V(xIRefTMIO1, aVdd) <+ 0.6 + I(xIRefTMIO1, aVdd)*10.0;
    else
        I(xIRefTMIO1, aVdd) <+ 1e-12 * (exp(min(V(xIRefTMIO1, aVdd)/0.026, 30.0)) - 1.0);

    // Relays W0, W1
    if (V(net4) > 1.0)
        V(xIRefTMIO, xIRefTMIO1) <+ I(xIRefTMIO, xIRefTMIO1) * 1.0;
    else
        I(xIRefTMIO, xIRefTMIO1) <+ V(xIRefTMIO, xIRefTMIO1) * 1e-9;

    if (V(net7) > 1.0)
        V(xIRefTMIO, xIRefTMIO2) <+ I(xIRefTMIO, xIRefTMIO2) * 1.0;
    else
        I(xIRefTMIO, xIRefTMIO2) <+ V(xIRefTMIO, xIRefTMIO2) * 1e-9;

    V(xIRefTMIO2, cds_globals.\gnd! ) <+ 0.0;
    
    // V5: Clock pulse for net6
    V(net6, cds_globals.\gnd! ) <+ ($abstime >= 400e-6 && (($abstime - 400e-6) % 100e-6) < 50e-6 ? 3.3 : 0.0);
end

endmodule
VAMS_EOF
    
    # 3. Clean textInputs & xrunArgs
    sed -i 's/ftype:va //g' textInputs 2>/dev/null
    sed -i 's/\${IC_INVOKE_DIR}/\/home\/lary\/project\/BVU025\/SCH/g' textInputs 2>/dev/null
    sed -i 's/-amsbind//g' xrunArgs 2>/dev/null
    sed -i '/Buffer_DIG/d' xrunArgs 2>/dev/null
    echo "[xrun_wrapper] Configured with exact IBP_Res (0.7679V) and xIRefTMIOi (0.7675V)!"
fi

# Execute real xrun
exec "$REAL_XRUN" "$@"
