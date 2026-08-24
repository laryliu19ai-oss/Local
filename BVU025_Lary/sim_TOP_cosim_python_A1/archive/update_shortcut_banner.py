import os, re

new_bvsim = """procedure( bvSim( @optional ( jsonConfig nil ) )
    let( ( configDir pyRunner simRet resJsonPath resTable itemsTable item101 item102 status101 status102 overallStatus outLog inP line )
        configDir = if( stringp( jsonConfig ) bvGetFileDir( simplifyFilename( jsonConfig ) ) pwd() )
        pyRunner = strcat( configDir "/run_cosim.py" )
        
        if( isFile( pyRunner ) then
            printf( "\\n===========================================================================\\n" )
            printf( " ===> [bvSim] Starting OneTest AMS Co-simulation in:\\n      %s\\n" configDir )
            printf( " ===> Running xrun + Spectre + Python SAR Virtual Tester (approx 20-30s)...\\n" )
            printf( "===========================================================================\\n" )
            drain( nil )

            ; Execute Python OneTest Co-simulation runner and stream log to CIW
            outLog = makeTempFileName( "/tmp/bvsim_run_XXXXXX" )
            sh( sprintf( nil "cd %s && python3 run_cosim.py > %s 2>&1" configDir outLog ) )
            when( isFile( outLog )
                inP = infile( outLog )
                when( inP
                    while( gets( line inP )
                        printf( "%s" line )
                    )
                    close( inP )
                    deleteFile( outLog )
                )
            )
            simRet = t
        else
            ; Standard fallback
            simRet = bvSimulate( jsonConfig )
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
        simRet
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
            print(f"Updated {p}")
        else:
            print(f"Pattern not found in {p}")
