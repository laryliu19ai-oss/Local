import subprocess

check_il = """
cv = dbOpenCellViewByType("BVU025_Lary" "py_tester" "symbol" "schematicSymbol" "r")
if(cv then
    printf("==> Symbol Terminals: %L\\n" cv~>terminals~>name)
    printf("==> Symbol Shapes Count: %d\\n" length(cv~>shapes))
    foreach(term cv~>terminals
        printf("  Terminal: %s, Pins: %L\\n" term~>name term~>pins~>fig~>bBox)
    )
    dbClose(cv)
else
    printf("==> Failed to open symbol\\n")
)
exit()
"""

with open(r"c:\Antgravity\Local\BVU025_Lary\sim_TOP_cosim_python_A1\check_sym.il", "w") as f:
    f.write(check_il)
