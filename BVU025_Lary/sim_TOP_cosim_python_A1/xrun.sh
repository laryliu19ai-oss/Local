#!/bin/bash
# Pre-simulation auto-assembly of ihnl into netlist.vams
CUR_DIR="$(pwd)"
echo "[xrun wrapper] Invoked in directory: $CUR_DIR with args: $@" >> /tmp/xrun_wrapper.log

# ONLY run auto_assemble when xrun is invoked for actual simulation (with xrunArgs)
# Do NOT run during intermediate netlisting (-version, -compile, assembler, etc.)
if [[ "$*" == *"xrunArgs"* ]]; then
    if [ -d "$CUR_DIR/digital/ihnl" ]; then
        python3 /home/lary/bin/auto_assemble.py "$CUR_DIR" "/home/lary/project/BVU025/SCH/cosim/pattern/TM14and15" >> /tmp/xrun_wrapper.log 2>&1
    elif [ -d "$CUR_DIR/ams/config/netlist/digital/ihnl" ]; then
        python3 /home/lary/bin/auto_assemble.py "$CUR_DIR/ams/config/netlist" "/home/lary/project/BVU025/SCH/cosim/pattern/TM14and15" >> /tmp/xrun_wrapper.log 2>&1
    elif [ -f "$CUR_DIR/netlist.vams" ]; then
        python3 /home/lary/bin/auto_assemble.py "$CUR_DIR" "/home/lary/project/BVU025/SCH/cosim/pattern/TM14and15" >> /tmp/xrun_wrapper.log 2>&1
    fi

    # Ensure symlink between psf/xrun.log and netlist/xrun.log exists
    if [ -d "$CUR_DIR/../psf" ]; then
        mkdir -p "$CUR_DIR/../psf"
        touch "$CUR_DIR/../psf/xrun.log"
        ln -sf "$CUR_DIR/../psf/xrun.log" "$CUR_DIR/xrun.log"
    fi
fi

/tools/cadence/XCELIUM/2409/tools/bin/xrun "$@"
XRUN_EXIT=$?
echo "[xrun wrapper] xrun exited with code $XRUN_EXIT" >> /tmp/xrun_wrapper.log

if [ $XRUN_EXIT -eq 0 ]; then
    # Sync PSF files to TM14and15 pattern psf directory if running from simulation directory
    if [ -d "$CUR_DIR/../psf" ]; then
        mkdir -p /home/lary/project/BVU025/SCH/cosim/pattern/TM14and15/psf
        cp -u "$CUR_DIR/../psf"/* /home/lary/project/BVU025/SCH/cosim/pattern/TM14and15/psf/ 2>/dev/null || true
    elif [ -d "$CUR_DIR/psf" ]; then
        mkdir -p /home/lary/project/BVU025/SCH/cosim/pattern/TM14and15/psf
        cp -u "$CUR_DIR/psf"/* /home/lary/project/BVU025/SCH/cosim/pattern/TM14and15/psf/ 2>/dev/null || true
    fi
fi

exit $XRUN_EXIT
