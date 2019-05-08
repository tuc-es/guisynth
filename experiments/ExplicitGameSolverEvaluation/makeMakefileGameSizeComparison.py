#!/usr/bin/env python3
import os, sys
from scenarioPairs import SCENARIO_PAIRS


dependencies = []

# Makefile first stuff
with open("Makefile","w") as outFile:
    outFile.write("default: tableGameSizes.tex\n\n")
    outFile.write("clean:\n\trm .out/*\n\n")
    
    # Game construction
    for (x,a) in SCENARIO_PAIRS:
        dest = ".out/"+a+".game"
        destPerf = ".out/"+a+".gameTime"
        outFile.write(dest+": \n")
        outFile.write("\tmkdir -p .out/\n")
        outFile.write("\t../../tools/timeout -m 6000000 -t 7200 ../../tools/Orchestrator/orchestratorExplicit.py "+x+" "+a+" /dev/null --onlyGameConstruction --gameOutputFile "+".out/"+a+".game"+" > "+destPerf+" 2>&1\n\n")
        dependencies.append(dest)

    # Non-Antichain
    for (x,a) in SCENARIO_PAIRS:
        destGame = ".out/"+a+".game"
        dest = ".out/"+a+".guisynthSmallGameSizeNonAntichain"
        outFile.write(dest+": "+destGame+"\n")
        outFile.write("\tmkdir -p .out/\n")
        outFile.write("\t../../tools/timeout -m 6000000 -t 7200 ../../tools/ExplicitGameSolver/gamesolverNonAntichain --getNofPositions "+destGame+" > "+dest+" 2>&1\n\n")
        dependencies.append(dest)
        
    # Basic explicit game solver
    for (x,a) in SCENARIO_PAIRS:
        destGame = ".out/"+a+".game"
        dest = ".out/"+a+".guisynthSmallGameSizeAntichain"
        outFile.write(dest+": "+destGame+"\n")
        outFile.write("\tmkdir -p .out/\n")
        outFile.write("\t../../tools/timeout -m 6000000 -t 7200 ../../tools/ExplicitGameSolver/gamesolverAntichain --getNofPositions "+destGame+" > "+dest+" 2>&1\n\n")
        dependencies.append(dest)

    
    # Summary
    outFile.write("tableGameSizes.tex: "+" ".join(dependencies)+"\n")
    outFile.write("\t./makeSummaryGameSizes.py > tableGameSizes.tex\n\n")

