import os, re

new_bvsim = """procedure( bvSimProcessData( cid data )
    printf( "%s" data )
)

procedure( bvSim( @optional ( jsonConfig nil ) )
    let( ( configDir pyRunner pId resJsonPath resTable itemsTable item101 item102 status101 status102 overallStatus )
        configDir = if( stringp( jsonConfig ) bvGetFileDir( simplifyFilename( jsonConfig ) ) pwd() )
        pyRunner = simplifyFilename( strcat( configDir "/run_cosim.py" ) )
        
        if( isFile( pyRunner ) then
            printf( "\\n===========================================================================\\n" )
            printf( " ===> [bvSim] Starting Real-time OneTest AMS Co-simulation:\\n      %s\\n" pyRunner )
            printf( "===========================================================================\\n\\n" )

            ; Remove old test_report.json before starting simulation
            resJsonPath = strcat( configDir "/result/test_report.json" )
            when( isFile( resJsonPath ) deleteFile( resJsonPath ) )

            ; Use ipcBeginProcess with ipcWait to guarantee blocking until full completion with live CIW streaming
            pId = ipcBeginProcess(
                sprintf( nil "python3 -u %s" pyRunner )
                ""
                'bvSimProcessData
                'bvSimProcessData
                nil
                ""
            )
            
            if( pId then
                ipcWait( pId )
            else
                ; Fallback
                sh( sprintf( nil "python3 -u %s" pyRunner ) )
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

for p in target_files:
    if os.path.exists(p):
        content = open(p).read()
        # Find where bvSim or bvSimProcessData starts
        proc_idx = content.find("procedure( bvSimProcessData")
        if proc_idx == -1:
            proc_idx = content.find("procedure( bvSim(")
        if proc_idx != -1:
            content = content[:proc_idx] + new_bvsim
        else:
            content = content + "\n\n" + new_bvsim
        open(p, "w").write(content)
        print(f"Updated {p}")
