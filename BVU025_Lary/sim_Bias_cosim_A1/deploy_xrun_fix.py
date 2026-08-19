import subprocess

xrun_script = '''#!/bin/bash
export CDS_LIC_FILE=/usr/local/share/license/cds.lic
export LM_LICENSE_FILE=/usr/local/share/license/cds.lic
export CDS_AUTO_64BIT=ALL
export CDS_SKIP_OS_CHECK_ON_STARTUP=1
export IC_INVOKE_DIR=${IC_INVOKE_DIR:-/home/lary/project/BVU025/SCH}
export PATH=/home/lary/bin:/tools/cadence/IC/618/bin:/tools/cadence/SPECTRE/211/bin:/tools/cadence/XCELIUM/2409/tools/bin:/usr/local/bin:/usr/bin:/bin:$PATH

REAL_XRUN="/tools/cadence/XCELIUM/2409/tools/bin/xrun"

# If running from within an AMS simulation directory with xrunArgs and digital/ihnl:
if [ -f "xrunArgs" ] && [ -d "digital/ihnl" ]; then
    echo "[xrun_wrapper] Preparing AMS co-simulation netlist and arguments..."
    
    # 1. Back up header
    if [ ! -f netlist.vams.orig ]; then
        cp netlist.vams netlist.vams.orig
    fi
    
    # 2. Reassemble netlist.vams with header + all digital ihnl modules
    cat netlist.vams.orig > netlist.vams
    echo "" >> netlist.vams
    echo "// --- Digital IHNL Modules ---" >> netlist.vams
    for f in $(ls -v digital/ihnl/cds*/netlist 2>/dev/null); do
        echo "// File: $f" >> netlist.vams
        cat "$f" >> netlist.vams
        echo "" >> netlist.vams
    done
    
    # 3. Add electrical declarations to sim_Bias_cosim_A1 and Bias_A1
    python3 -c '
with open("netlist.vams", "r") as f:
    c = f.read()

# Add electrical declarations in sim_Bias_cosim_A1
target_sim = "module sim_Bias_cosim_A1 ();\\n\\n// Buses in the design\\n\\nwire  [5:0]  NvTrmIref;\\n"
repl_sim = "module sim_Bias_cosim_A1 ();\\n\\nelectrical aVdd, aVss, SUB, net3, xIRefTMIO, VBNC, DVDD_Trm, IREF_TrmCode;\\nelectrical TMIRefOn, TMIRefMeas, TMIRefOni, TMIRefMeasi, CLK, POR, dDone, dIRefTMO, net5, net6;\\nwire  [5:0]  NvTrmIref;\\n"
c = c.replace(target_sim, repl_sim)

# Add electrical declarations in Bias_A1
target_bias = "module Bias_A1 (IRefTMO, ibp_250n, SUB, VBNC, VBNC1, aVdd, aVss, En, \\n    rgTrim_IRef, TMIRefMeas, TMIRefOn, xIRefTMIO);\\n\\n// Buses in the design\\n"
repl_bias = "module Bias_A1 (IRefTMO, ibp_250n, SUB, VBNC, VBNC1, aVdd, aVss, En, \\n    rgTrim_IRef, TMIRefMeas, TMIRefOn, xIRefTMIO);\\n\\nelectrical SUB, aVss, aVdd, ibp_250n, En, TMIRefOn, xIRefTMIO, TMIRefMeas, VBNC, VBNC1;\\nelectrical IBP_Res, xIRefTMIOi, VBN, VBN1, VBP, VBP_Res, net3, net4, net5;\\nwire IRefTMO;\\nwire [5:0] rgTrim_IRef;\\n\\n// Buses in the design\\n"
c = c.replace(target_bias, repl_bias)

with open("netlist.vams", "w") as f:
    f.write(c)
'
    
    # 4. Clean textInputs & xrunArgs
    sed -i 's/ftype:va //g' textInputs 2>/dev/null
    sed -i 's/\${IC_INVOKE_DIR}/\/home\/lary\/project\/BVU025\/SCH/g' textInputs 2>/dev/null
    sed -i 's/-amsbind//g' xrunArgs 2>/dev/null
    sed -i '/Buffer_DIG/d' xrunArgs 2>/dev/null
    if grep -q "Buffer_DIG" textInputs 2>/dev/null; then
        if ! grep -q "binding.*Buffer_DIG" xrunArgs; then
            sed -i '/-v93/a -binding BVU025_Lary.Buffer_DIG:functional' xrunArgs 2>/dev/null
        fi
    fi
    echo "[xrun_wrapper] Netlist and arguments configured successfully!"
fi

# Execute real xrun
exec "$REAL_XRUN" "$@"
'''

res = subprocess.run(['ssh', 'lary@192.168.16.130', 'cat > /home/lary/bin/xrun && chmod +x /home/lary/bin/xrun && sed -i "s/\\r$//" /home/lary/bin/xrun'], input=xrun_script, text=True, capture_output=True)
print("Updated /home/lary/bin/xrun:", res.stdout, res.stderr)
