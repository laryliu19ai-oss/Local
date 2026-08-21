; SKILL script to generate py_tester Symbol with user-specified Pin sides
libName = "BVU025_Lary"
cellName = "py_tester"

; Delete old symbol view
if(ddGetObj(libName cellName "symbol") then
    ddDeleteObj(ddGetObj(libName cellName "symbol"))
)

; Pin sides:
; Top: aVdd
; Bottom: aVss
; Right: TMIRefOn, TMIRefMeas, NvTrmIref<5:0>, GPIO8
; Left: dIRefTMO
pinSpec = list(nil
    'topPins    list("aVdd")
    'bottomPins list("aVss")
    'rightPins  list("TMIRefOn" "TMIRefMeas" "NvTrmIref<5:0>" "GPIO8")
    'leftPins   list("dIRefTMO")
)

symObj = schPinListToSymbol(libName cellName "symbol" pinSpec)
printf("==> [Skill] Symbol regenerated with Right/Left pin alignment: %L\n" symObj)
exit()
