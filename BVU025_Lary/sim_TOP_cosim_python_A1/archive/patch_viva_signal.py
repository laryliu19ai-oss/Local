import os, re

new_func = """procedure( bvVivaCreateSignalFromType( signalType signalName signalExpression signalVariables )
    let( ( plotSignal varName )
        varName = sprintf( nil "bvSig_%d" bvGlobalPlotSigIndex )
        bvGlobalPlotSigIndex = bvGlobalPlotSigIndex + 1
        cond(
            ( equal( signalType "voltage" )
                plotSignal = bvPlotExec( sprintf( nil "%s = if( v( \\"%s\\" ) v( \\"%s\\" ) getData( \\"%s\\" ) )" varName signalName signalName signalName ) )
            )
            ( equal( signalType "current" )
                plotSignal = bvPlotExec( sprintf( nil "%s = if( i( \\"%s\\" ) i( \\"%s\\" ) if( getData( \\"%s\\" ) getData( \\"%s\\" ) getData( \\"%s_$flow\\" ) ) )" varName signalName signalName signalName signalName signalName ) )
            )
            ( or( equal( signalType "digital" ) equal( signalType "digitalBus" ) equal( signalType "bus" ) )
                plotSignal = bvPlotExec( sprintf( nil "%s = if( getData( \\"%s\\" ) getData( \\"%s\\" ) if( getData( \\"sim_TOP_cosim_python_A1.%s\\" ) getData( \\"sim_TOP_cosim_python_A1.%s\\" ) v( \\"%s\\" ) ) )" varName signalName signalName signalName signalName signalName ) )
            )
            ( equal( signalType "expression" )
                bvPlotScriptLog( sprintf( nil "; expression: %s = evalstring( \\"%s\\" )" varName
                    bvSignalExpression( signalExpression signalVariables ) ) )
                plotSignal = evalstring( bvSignalExpression( signalExpression signalVariables ) )
            )
            ( t
                plotSignal = bvPlotExec( sprintf( nil "%s = if( getData( \\"%s\\" ) getData( \\"%s\\" ) v( \\"%s\\" ) )" varName signalName signalName signalName ) )
            )
        )
        plotSignal
    )
)"""

target_files = [
    "/home/lary/skill/modules/viva/bvVivaPlotWindow.il",
    "/home/lary/skill/skill/modules/viva/bvVivaPlotWindow.il"
]

pattern = r'procedure\(\s*bvVivaCreateSignalFromType\s*\([\s\S]*?\)\s*;\s*end\s*procedure'

for p in target_files:
    if os.path.exists(p):
        content = open(p).read()
        if re.search(pattern, content):
            content = re.sub(pattern, new_func, content)
            open(p, "w").write(content)
            print(f"Patched {p}")
        else:
            print(f"Pattern not found in {p}")
