#!/usr/bin/env python3
import os, sys
from scenarioPairs import SCENARIO_PAIRS


dependencies = []

# Makefile first stuff
with open("Makefile","w") as outFile:
    outFile.write("default: table.tex\n\n")
    outFile.write("clean:\n\trm .out/*\n\n")
    
    # Game construction
    for (x,a) in SCENARIO_PAIRS:
        dest = ".out/"+a+".game"
        destPerf = ".out/"+a+".gameTime"
        outFile.write(dest+": \n")
        outFile.write("\tmkdir -p .out/\n")
        outFile.write("\t../../tools/timeout -m 6000000 -t 7200 ../../tools/Orchestrator/orchestratorExplicit.py "+x+" "+a+" /dev/null --onlyGameConstruction --gameOutputFile "+".out/"+a+".game"+" > "+destPerf+" 2>&1\n\n")
        dependencies.append(dest)

    # Basic explicit game solver
    for (x,a) in SCENARIO_PAIRS:
        destGame = ".out/"+a+".game"
        dest = ".out/"+a+".guisynthSmall"
        outFile.write(dest+": "+destGame+"\n")
        outFile.write("\tmkdir -p .out/\n")
        outFile.write("\t../../tools/timeout -m 6000000 -t 7200 ../../tools/ExplicitGameSolver/gamesolver "+destGame+" > "+dest+" 2>&1\n\n")
        dependencies.append(dest)
        
    # Basic explicit game solver
    for (x,a) in SCENARIO_PAIRS:
        destGame = ".out/"+a+".game"    
        dest = ".out/"+a+".guisynthKind"
        outFile.write(dest+": "+destGame+"\n")
        outFile.write("\tmkdir -p .out/\n")
        outFile.write("\t../../tools/timeout -m 6000000 -t 7200 ../../tools/ExplicitGameSolver/gamesolver --nice "+destGame+" > "+dest+" 2>&1\n\n")
        dependencies.append(dest)

    # GR(1) synthesis
    for (x,a) in SCENARIO_PAIRS:
        destGame = ".out/"+a+".game"    
        dest = ".out/"+a+".gr1"
        outFile.write(dest+": "+destGame+"\n")
        outFile.write("\tmkdir -p .out/\n")
        outFile.write("\t../../tools/timeout -m 6000000 -t 7200 \"../../tools/ExplicitGameToSlugsTranslator/translator.py < "+destGame+" | ../../lib/slugs/tools/StructuredSlugsParser/compiler.py /dev/stdin | ../../lib/slugs/src/slugs /dev/stdin\" > "+dest+" 2>&1\n\n")
        dependencies.append(dest)
    
        # TLSF synthesis
        destGame = ".out/"+a+".game"    
        destInter = ".out/"+a+".tlsf"
        dest = ".out/"+a+".strix"
        outFile.write(dest+": "+destGame+"\n")
        outFile.write("\tmkdir -p .out/\n")
        outFile.write("\t../../tools/SpecToTLSFTranslator/translator.py < "+a+" > "+destInter+"\n")
        outFile.write("\t../../tools/timeout -m 6000000 -t 7200 ../../lib/strix/bin/strix -r "+destInter+" > "+dest+" 2>&1\n\n")
        dependencies.append(dest)

    
    # Summary
    outFile.write("table.tex: "+" ".join(dependencies)+"\n")
    outFile.write("\t./makeSummary.py > table.tex\n\n")

