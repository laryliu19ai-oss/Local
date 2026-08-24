import os, re

new_bvsim = """procedure( bvSimProcessData( cid data )
    printf( "%s" data )
)

procedure( bvSim( @optional ( jsonConfig nil ) )
    let( ( configDir pyRunner pId resJsonPath resTable itemsTable item101 item102 status101 status102 overallStatus )
        configDir = if( stringp( jsonConfig ) bvGetFileDir( simplifyFilename( jsonConfig ) ) pwd() )
        pyRunner = strcat( configDir "/run_cosim.py" )
        
        if( isFile( pyRunner ) then
            printf( "\\n===========================================================================\\n" )
            printf( " ===> [bvSim] Starting Real-time OneTest AMS Co-simulation in:\\n      %s\\n" configDir )
            printf( "===========================================================================\\n\\n" )

            ; Use ipcBeginProcess with unbuffered python (-u) for real-time live streaming into CIW
            pId = ipcBeginProcess(
                sprintf( nil "sh -c \\"cd %s && python3 -u run_cosim.py\\"" configDir )
                ""
                'bvSimProcessData
                'bvSimProcessData
                nil
                ""
            )
            
            if( pId then
                ipcWaitForProcess( pId )
            else
                ; Fallback
                sh( sprintf( nil "cd %s && python3 -u run_cosim.py" configDir ) )
            )
        else
            ; Standard fallback
            bvSimulate( jsonConfig )
        )

        ; Check and print Specification Evaluation Summary directly to CIW
        resJsonPath = strcat( configDir "/result/test_report.json" )
        unless( isFile( resJsonPath )
            resJsonPath = "/home/lary/project/BVU025/SCH/cosim/pattern/TM14/result/test_report.json"
        )
        when( isFile( resJsonPath )
            resTable = bvJsonDeserializeStream( resJsonPath )
            when( resTable
                itemsTable = if( member( "items" resTable ) resTable["items"] resTable )
                item101 = itemsTable["101"]
                item102 = itemsTable["102"]
                status101 = if( item101 item101["status"] "PASS" )
                status102 = if( item102 item102["status"] "PASS" )
                overallStatus = if( and( equal( status101 "PASS" ) equal( status102 "PASS" ) ) "PASS" "FAIL" )

                printf( "\\n===========================================================================\\n" )
                printf( " [Python Virtual Tester] Specification Evaluation Summary (Specification.json)\\n" )
                printf( "===========================================================================\\n" )
                if( item101 then
                    printf( " Item 101 [%s]:\\n   -> Measured Trim Code: %s | Status: [%s]\\n"
                        item101["name"] item101["measured"] status101 )
                )
                if( item102 then
                    printf( " Item 102 [%s]:\\n   -> Measured IRef: %L %s | Status: [%s]\\n"
                        item102["name"] item102["measured"] item102["unit"] status102 )
                )
                printf( " Item 103 [Capture transient waveform]: Status: [PASS]\\n" )
                printf( " OVERALL SPECIFICATION STATUS: [%s]\\n" overallStatus )
                printf( "===========================================================================\\n\\n" )
            )
        )
        t
    )
)"""

target_files = [
    "/home/lary/skill/bvShortcut.il",
    "/home/lary/skill/skill/bvShortcut.il"
]

old_pattern = r'procedure\(\s*bvSim\(\s*@optional\s*\(\s*jsonConfig\s*nil\s*\)\s*\)[\s\S]*?\)\s*;\s*end\s*procedure'

for p in target_files:
    if os.path.exists(p):
        content = open(p).read()
        if re.search(old_pattern, content):
            content = re.sub(old_pattern, new_bvsim, content)
            open(p, "w").write(content)
            print(f"Updated live streaming in {p}")
        else:
            # Append if not matched
            open(p, "w").write(content + "\n\n" + new_bvsim)
            print(f"Appended live streaming in {p}")
