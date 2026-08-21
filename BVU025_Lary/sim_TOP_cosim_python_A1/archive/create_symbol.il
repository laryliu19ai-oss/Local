libName = "BVU025_Lary"
cellName = "py_SAR6b"

; 1. Copy symbol from vaSAR6b to py_SAR6b
if(ddGetObj(libName "vaSAR6b" "symbol") then
    ccpCopy(ddGetObj(libName "vaSAR6b" "symbol") ddGetObj(libName) cellName "symbol" nil 'exact)
    printf("==> [Skill] Successfully created symbol for %s.%s!\n" libName cellName)
)

; 2. Create veriloga view directory
dest_dir = sprintf(nil "%s/%s/veriloga" ddGetObj(libName)~>readPath cellName)
sh(sprintf(nil "mkdir -p %s && cp /home/lary/project/BVU025/python/sim_TOP_cosim_python_A1/py_SAR6b.va %s/veriloga.va" dest_dir dest_dir))
printf("==> [Skill] Verilog-A view configured: %s/veriloga.va\n" dest_dir)
exit()
