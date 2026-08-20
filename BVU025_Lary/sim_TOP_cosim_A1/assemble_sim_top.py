import os
import glob
import re

netlist_dir = '/home/lary/simulation/BVU025/BVU025A/sim_TOP_cosim_A1/ams/config/netlist'
os.chdir(netlist_dir)

# 1. Assemble netlist.vams
h = open('./.amsOSSHeader').read() if os.path.exists('./.amsOSSHeader') else ''
hdl = open('./.hdlFileInfo_forNetlist').read() if os.path.exists('./.hdlFileInfo_forNetlist') else ''

ihnl_files = sorted(glob.glob('./digital/ihnl/cds*/netlist'), key=lambda x: int(os.path.basename(os.path.dirname(x)).replace('cds', '')))
ihnl_content = '\n\n'.join([open(f).read() for f in ihnl_files])

# Fix vector connection and pin naming to SPICE subckt port in TOP_A1 module
ihnl_content = re.sub(
    r'\.rgTrim_IRef\s*\(\s*NvTrmIref\[5:0\]\s*\)',
    '.rgTrim_IRef_5(NvTrmIref[5]), .rgTrim_IRef_4(NvTrmIref[4]), .rgTrim_IRef_3(NvTrmIref[3]), .rgTrim_IRef_2(NvTrmIref[2]), .rgTrim_IRef_1(NvTrmIref[1]), .rgTrim_IRef_0(NvTrmIref[0])',
    ihnl_content
)
ihnl_content = re.sub(r'\.ibp_250n\s*\(', '.ibp_250n_0(', ihnl_content)

full_vams = h + '\n\n`include "disciplines.vams"\n`include "userDisciplines.vams"\n\n' + hdl + '\n\n' + ihnl_content + '\n'
open('./netlist.vams', 'w').write(full_vams)

# 2. Extract clean subcircuits and use the fully-pinned Bias_A1 definition
bias_subckts_path = '/home/lary/simulation/BVU025/BVU025A/sim_Bias_cosim_A1/ams/config/netlist/subckts.scs'
if os.path.exists(bias_subckts_path):
    subckts_scs = open(bias_subckts_path).read()
else:
    analog_raw = open('./analog/netlist').read() if os.path.exists('./analog/netlist') else ''
    subckt_blocks = re.findall(r'subckt\s+.*?ends(?:\s+\w+)?', analog_raw, re.DOTALL)
    subckts_scs = "simulator lang=spectre\n\n" + "\n\n".join(subckt_blocks) + "\n"

# Ensure AN2x1 subckt is present in subckts.scs
if 'subckt AN2x1' not in subckts_scs:
    an2x1_block = re.search(r'subckt AN2x1.*?ends AN2x1', open('./analog/netlist').read(), re.DOTALL)
    if an2x1_block:
        subckts_scs += "\n\n" + an2x1_block.group(0) + "\n"

open('./subckts.scs', 'w').write(subckts_scs)

# 3. Write proper .amsbind.scs
amsbind_content = """// Binding AMSD Control Block for config BVU025_Lary.sim_TOP_cosim_A1:config
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

# 4. Update spiceModels.scs to include subckts.scs
sm_lines = [l for l in open('./spiceModels.scs').read().splitlines() if 'analog/netlist' not in l and 'subckts.scs' not in l]
sm_clean = '\n'.join(sm_lines) + '\ninclude "./subckts.scs" amsd_subckt_bind=yes\n'
open('./spiceModels.scs', 'w').write(sm_clean)

print(f'Successfully prepared sim_TOP_cosim_A1 with ibp_250n_0 pin alignment!')
