#!/bin/bash
# Pre-simulation auto-assembly of ihnl into netlist.vams
CUR_DIR="$(pwd)"
echo "[xrun wrapper] Invoked in directory: $CUR_DIR with args: $@" >> /tmp/xrun_wrapper.log

if [ -d "$CUR_DIR/digital/ihnl" ]; then
    python3 /home/lary/bin/auto_assemble.py "$CUR_DIR" "/home/lary/project/BVU025/SCH/cosim/pattern/TM14" >> /tmp/xrun_wrapper.log 2>&1
elif [ -d "$CUR_DIR/ams/config/netlist/digital/ihnl" ]; then
    python3 /home/lary/bin/auto_assemble.py "$CUR_DIR/ams/config/netlist" "/home/lary/project/BVU025/SCH/cosim/pattern/TM14" >> /tmp/xrun_wrapper.log 2>&1
fi

exec /tools/cadence/XCELIUM/2409/tools/bin/xrun "$@"
