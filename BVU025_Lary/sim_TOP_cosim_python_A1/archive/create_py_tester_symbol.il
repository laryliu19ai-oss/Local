; Skill Script to create py_tester Symbol and Verilog-A view in BVU025_Lary
libName = "BVU025_Lary"
cellName = "py_tester"

; Define pin list
inList = list("dIRefTMO")
outList = list("TMIRefOn" "TMIRefMeas" "NvTrmIref<5:0>")
ioList = list("aVdd" "aVss" "GPIO8")

; Create Symbol view using Cadence built-in pin-to-symbol generator
schPinListToSymbol(libName cellName "symbol" list(nil 'input inList 'output outList 'inout ioList))
printf("==> [Skill] Created py_tester Symbol view in %s.%s\n" libName cellName)

; Setup Verilog-A view directory
dest_dir = sprintf(nil "%s/%s/veriloga" ddGetObj(libName)~>readPath cellName)
sh(sprintf(nil "mkdir -p %s && cp /home/lary/project/BVU025/python/sim_TOP_cosim_python_A1/py_tester.va %s/veriloga.va" dest_dir dest_dir))
printf("==> [Skill] Verilog-A view configured at: %s/veriloga.va\n" dest_dir)
exit()
