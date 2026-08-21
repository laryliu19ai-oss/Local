; Robust Cadence Symbol Generator for py_tester with genuine Pins and Terminals
libName = "BVU025_Lary"
cellName = "py_tester"

cv = dbOpenCellViewByType(libName cellName "symbol" "schematicSymbol" "w")
if(cv then
    ; 1. Draw outer body box on ("device" "drawing")
    ; Coordinates: Left = -1.5, Right = 1.5, Bottom = -1.2, Top = 1.2
    dbCreateRect(cv list("device" "drawing") list(-1.5:-1.2 1.5:1.2))

    ; 2. Add cell name label and instance label
    dbCreateLabel(cv list("annotate" "drawing7") 0.0:0.0 cellName "centerCenter" "R0" "roman" 0.1)
    dbCreateLabel(cv list("annotate" "drawing") -1.4:1.3 "[@instanceName]" "lowerLeft" "R0" "roman" 0.08)

    ; Helper procedure to create real schematic symbol pin
    procedure(createSymPin(cv name dir pt linePt labelPt labelJust)
        let((net term pinFig lineFig lblFig)
            ; Create or get net and terminal
            net = dbMakeNet(cv name)
            term = dbCreateTerm(net name dir)

            ; Draw pin square on ("pin" "drawing")
            pinFig = dbCreateRect(cv list("pin" "drawing") 
                list((xCoord(pt)-0.025):(yCoord(pt)-0.025) (xCoord(pt)+0.025):(yCoord(pt)+0.025)))
            
            ; Draw lead line from body to pin
            lineFig = dbCreateLine(cv list("device" "drawing") list(linePt pt))

            ; Create Pin
            dbCreatePin(net pinFig)

            ; Create Pin Label
            lblFig = dbCreateLabel(cv list("annotate" "drawing7") labelPt name labelJust "R0" "roman" 0.0625)
        )
    )

    ; Top Pin: aVdd (y = 1.2 -> 1.5)
    createSymPin(cv "aVdd" "inputOutput" 0.0:1.5 0.0:1.2 0.0:1.1 "centerCenter")

    ; Bottom Pin: aVss (y = -1.2 -> -1.5)
    createSymPin(cv "aVss" "inputOutput" 0.0:-1.5 0.0:-1.2 0.0:-1.1 "centerCenter")

    ; Left Pin: dIRefTMO (x = -1.5 -> -1.8)
    createSymPin(cv "dIRefTMO" "input" -1.8:0.0 -1.5:0.0 -1.4:0.0 "centerLeft")

    ; Right Pins: TMIRefOn, TMIRefMeas, NvTrmIref<5:0>, GPIO8 (x = 1.5 -> 1.8)
    createSymPin(cv "TMIRefOn"        "output"      1.8:0.6   1.5:0.6   1.4:0.6   "centerRight")
    createSymPin(cv "TMIRefMeas"      "output"      1.8:0.2   1.5:0.2   1.4:0.2   "centerRight")
    createSymPin(cv "NvTrmIref<5:0>"  "output"      1.8:-0.2  1.5:-0.2  1.4:-0.2  "centerRight")
    createSymPin(cv "GPIO8"           "inputOutput" 1.8:-0.6  1.5:-0.6  1.4:-0.6  "centerRight")

    ; 3. Draw Selection Box on ("instance" "drawing")
    dbCreateRect(cv list("instance" "drawing") list(-1.85:-1.55 1.85:1.55))

    dbSave(cv)
    dbClose(cv)
    printf("==> [Skill] Genuine py_tester Symbol created successfully with %d pins!\n" 7)
)
exit()
