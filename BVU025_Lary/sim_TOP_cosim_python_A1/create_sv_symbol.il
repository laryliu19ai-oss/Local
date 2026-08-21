; SKILL Script to generate py_tester SystemVerilog View & Symbol in BVU025_Lary
libName = "BVU025_Lary"
cellName = "py_tester"

; 1. Delete old symbol and create fresh
if(ddGetObj(libName cellName "symbol") then
    ddDeleteObj(ddGetObj(libName cellName "symbol"))
)

cv = dbOpenCellViewByType(libName cellName "symbol" "schematicSymbol" "w")
if(cv then
    ; Body rectangle on ("device" "drawing")
    dbCreateRect(cv list("device" "drawing") list(-1.5:-1.2 1.5:1.2))

    ; Cell name label
    dbCreateLabel(cv list("annotate" "drawing7") 0.0:0.0 cellName "centerCenter" "R0" "roman" 0.1)
    dbCreateLabel(cv list("annotate" "drawing") -1.4:1.3 "[@instanceName]" "lowerLeft" "R0" "roman" 0.08)

    procedure(createSymPin(cv name dir pt linePt labelPt labelJust)
        let((net term pinFig lineFig lblFig)
            net = dbMakeNet(cv name)
            term = dbCreateTerm(net name dir)
            pinFig = dbCreateRect(cv list("pin" "drawing") 
                list((xCoord(pt)-0.025):(yCoord(pt)-0.025) (xCoord(pt)+0.025):(yCoord(pt)+0.025)))
            lineFig = dbCreateLine(cv list("device" "drawing") list(linePt pt))
            dbCreatePin(net pinFig)
            lblFig = dbCreateLabel(cv list("annotate" "drawing7") labelPt name labelJust "R0" "roman" 0.0625)
        )
    )

    ; Left Pin: dIRefTMO
    createSymPin(cv "dIRefTMO" "input" -1.8:0.0 -1.5:0.0 -1.4:0.0 "centerLeft")

    ; Right Pins: TMIRefOn, TMIRefMeas, NvTrmIref<5:0>, SCL, SDA
    createSymPin(cv "TMIRefOn"        "output"      1.8:0.8   1.5:0.8   1.4:0.8   "centerRight")
    createSymPin(cv "TMIRefMeas"      "output"      1.8:0.4   1.5:0.4   1.4:0.4   "centerRight")
    createSymPin(cv "NvTrmIref<5:0>"  "output"      1.8:0.0   1.5:0.0   1.4:0.0   "centerRight")
    createSymPin(cv "SCL"             "inputOutput" 1.8:-0.4  1.5:-0.4  1.4:-0.4  "centerRight")
    createSymPin(cv "SDA"             "inputOutput" 1.8:-0.8  1.5:-0.8  1.4:-0.8  "centerRight")

    ; Selection Box
    dbCreateRect(cv list("instance" "drawing") list(-1.85:-1.25 1.85:1.25))

    dbSave(cv)
    dbClose(cv)
    printf("==> [Skill] SystemVerilog py_tester Symbol created successfully!\n")
)

; 2. Setup functional/systemVerilog view directory
dest_dir = sprintf(nil "%s/%s/functional" ddGetObj(libName)~>readPath cellName)
sh(sprintf(nil "mkdir -p %s && cp /home/lary/project/BVU025/python/sim_TOP_cosim_python_A1/py_tester.sv %s/verilog.v" dest_dir dest_dir))
dest_sv = sprintf(nil "%s/%s/systemVerilog" ddGetObj(libName)~>readPath cellName)
sh(sprintf(nil "mkdir -p %s && cp /home/lary/project/BVU025/python/sim_TOP_cosim_python_A1/py_tester.sv %s/verilog.sv" dest_sv dest_sv))
printf("==> [Skill] SystemVerilog views (functional & systemVerilog) configured!\n")

exit()
