#!/bin/bash
# Pre-simulation auto-assembly of ihnl into netlist.vams
CUR_DIR="$(pwd)"
echo "[xrun wrapper] Invoked in directory: $CUR_DIR with args: $@" >> /tmp/xrun_wrapper.log

# Determine target netlist directory
NETLIST_DIR="$CUR_DIR"
if [ -d "$CUR_DIR/ams/config/netlist" ]; then
    NETLIST_DIR="$CUR_DIR/ams/config/netlist"
fi

# ONLY run auto_assemble when xrun is invoked for actual simulation (with xrunArgs)
# Do NOT run during intermediate netlisting (-version, -compile, assembler, etc.)
if [[ "$*" == *"xrunArgs"* ]]; then
    python3 /home/lary/project/BVU025/SCH/cosim/pattern/TM14/auto_assemble_global.py "$NETLIST_DIR" >> /tmp/xrun_wrapper.log 2>&1

    # Ensure symlink between psf/xrun.log and netlist/xrun.log exists
    if [ -d "$NETLIST_DIR/../psf" ]; then
        mkdir -p "$NETLIST_DIR/../psf"
        touch "$NETLIST_DIR/../psf/xrun.log"
        ln -sf "$NETLIST_DIR/../psf/xrun.log" "$NETLIST_DIR/xrun.log"
    fi
fi

/tools/cadence/XCELIUM/2409/tools/bin/xrun "$@"
XRUN_EXIT=$?
echo "[xrun wrapper] xrun exited with code $XRUN_EXIT" >> /tmp/xrun_wrapper.log

if [ $XRUN_EXIT -eq 0 ]; then
    TARGET_PSF=""
    if [[ "$NETLIST_DIR" == *"_A1"* ]] || [[ "$NETLIST_DIR" == *"sim_TOP_cosim_python_A1"* ]]; then
        TARGET_PSF="/home/lary/project/BVU025/SCH/cosim/pattern/TM14and15/psf"
    elif [[ "$NETLIST_DIR" == *"TM14"* ]]; then
        TARGET_PSF="/home/lary/project/BVU025/SCH/cosim/pattern/TM14/psf"
    elif [[ "$NETLIST_DIR" == *"TM15"* ]]; then
        TARGET_PSF="/home/lary/project/BVU025/SCH/cosim/pattern/TM15/psf"
    fi

    if [ -n "$TARGET_PSF" ]; then
        mkdir -p "$TARGET_PSF"
        if [ -d "$NETLIST_DIR/../psf" ]; then
            cp -u "$NETLIST_DIR/../psf"/* "$TARGET_PSF/" 2>/dev/null || true
        elif [ -d "$NETLIST_DIR/psf" ]; then
            cp -u "$NETLIST_DIR/psf"/* "$TARGET_PSF/" 2>/dev/null || true
        fi
    fi
fi

exit $XRUN_EXIT
