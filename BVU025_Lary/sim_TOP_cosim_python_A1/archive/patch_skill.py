import os

stub = """
; Ensure ADE license function stub exists in standalone ViVA/Ocean environments
unless( isCallable( '_sevDoLicenseSpecificAction )
    defun( _sevDoLicenseSpecificAction ( @rest _args ) t )
)
"""

target_files = [
    "/home/lary/skill/bvShortcut.il",
    "/home/lary/skill/bvSimulationCore.il",
    "/home/lary/skill/modules/simulation/bvSimulationCore.il",
    "/home/lary/skill/skill/bvSimulationCore.il",
    "/home/lary/skill/bv_ciwMenu.il",
    "/home/lary/skill/bvViva_modules.il"
]

for p in target_files:
    if os.path.exists(p):
        content = open(p).read()
        if "_sevDoLicenseSpecificAction" not in content:
            open(p, "w").write(stub + "\n" + content)
            print(f"Patched: {p}")
        else:
            print(f"Already patched: {p}")
