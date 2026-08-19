#!/bin/ksh


function convertReturnValue
{
   typeset rtnVal=$1
   if [[ -z $AMS_RESULTS_DIR ]]
   then
       typeset AMS_RESULTS_DIR="../psf"
   fi
   typeset logFileName="${AMS_RESULTS_DIR}/logFile"
   if [[ "$1" = 1 && -s "$logFileName" ]]
   then
       rtnVal=$2
   fi
   # Supply the value back to the caller.
   return $rtnVal
}

# Set location variables

if [[ -z $AMS_CIC_HIER ]]; then
   export    AMS_CIC_HIER=/tools/cadence/IC/618
fi

if [[ -z $AMS_IUS_HIER ]]; then
   export    AMS_IUS_HIER=/tools/cadence/XCELIUM/2409
fi

if [[ -z $IC_INVOKE_DIR ]]; then
   export    IC_INVOKE_DIR=/home/lary/project/BVU025/SCH
fi

export TESTBENCH_TOPCELL="sim_Bias_cosim_A1"
xrun -f xrunArgs 


convertReturnValue $? 0

