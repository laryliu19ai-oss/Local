; Test Verilog-A compilation & extract
cv = _schHDLOpen("BVU025_Lary" "py_tester" "veriloga" "a")
if(cv then
    status = _schHDLExtract(cv)
    printf("==> [Skill] Verilog-A extract returned status: %L\n" status)
    _schHDLClose(cv)
)
exit()
