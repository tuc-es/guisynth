#!/usr/bin/env python3
import os, sys
from scenarioPairs import SCENARIO_PAIRS

# Header
print("\\begin{tabular}{l|l||l|l||l|l||l|l}")
print("\\multicolumn{2}{c||}{\\textbf{Specification}}")
print("& \\multicolumn{2}{|c||}{\\textbf{Translation}}")
print("& \\multicolumn{2}{|c||}{\\textbf{Game solving}}")
print("& \\multicolumn{2}{|c}{\\textbf{Game solving}} \\\\")
print("\\multicolumn{2}{c||}{\\textbf{}}")
print("& \\multicolumn{2}{|c||}{\\textbf{to UVWs}}")
print("& \\multicolumn{2}{|c||}{\\textbf{(anti-chains)}}")
print("& \\multicolumn{2}{|c}{\\textbf{(no anti-chains)}}")
print("\\\\")

print("\\textbf{Rev.} & \\textbf{\#~Pro-}")
print("& \\textbf{Time} & \\textbf{\#}")
print("& \\textbf{Time} & \\textbf{\#}")
print("& \\textbf{Time} & \\textbf{\#}")
print("\\\\")

print("\\textbf{} & \\textbf{perties}")
print("& \\textbf{} & \\textbf{states}")
print("& \\textbf{} & \\textbf{positions}")
print("& \\textbf{} & \\textbf{positions}")
print("\\\\ \\hline")

for i,(x,a) in enumerate(SCENARIO_PAIRS):
    dest = ".out/"+a+".game"
    destPerf = ".out/"+a+".gameTime"
    destSmallAntichains = ".out/"+a+".guisynthSmallGameSizeAntichain"
    destSmallNonAntichains = ".out/"+a+".guisynthSmallGameSizeNonAntichain"

    # 1. Scenario number
    print(str(i+1)+"&")
    
    # 2. Number of properties
    with open(a,"r") as inFile:
        specFileLines = inFile.readlines()
        specFileParts = {"Threads":[],"Assumptions":[],"Guarantees":[],"CustomInputActions":[],"CustomOutputActions":[]}
        currentChapter = None
        lineNo = 0
        for line in specFileLines:
            line = line.strip()
            sys.stdout.flush()
            if not line.startswith("#"):
                if line.startswith("["):
                    assert line.endswith("]")
                    currentChapter = line[1:len(line)-1]
                else:
                    if len(line)>0:
                        specFileParts[currentChapter].append((line,lineNo))
            lineNo += 1

        print(len(specFileParts["Assumptions"])+len(specFileParts["Guarantees"]))
        # print(len(specFileParts["Assumptions"]))
        print(" & ")
    
    # 3. Translation time
    with open(destPerf,"r") as inFile:
        perf = None
        for line in inFile.readlines():
            if line.startswith("FINISHED CPU "):
                perf = line.split(" ")[2]
        assert not perf is None
        print(perf+" & ")
        
    # 4. UVW states
    with open(dest,"r") as inFile:
        nofStates = 0
        for line in inFile.readlines():
            if line.startswith("State "):
                nofStates += 1
        print(str(nofStates)+" & ")        
    
    # 5. Own tool
    for resultFile in [destSmallAntichains,destSmallNonAntichains]:
        maxLengthDecisionSequence = 0
        with open(resultFile,"r") as inFile:
            perf = None
            strategyLines = []
            nofPositions = "memout"
            inStrategyTransitions = False
            for line in inFile.readlines():
                if line.startswith("FINISHED CPU "):
                    perf = line.split(" ")[2]
                elif line.startswith("MEM CPU "):
                    perf = line.split(" ")[2]
                elif line.startswith("TRANSITIONS"):
                    inStrategyTransitions = True
                elif line.startswith("ENDTRANSITIONS"):
                    inStrategyTransitions = False
                elif line.startswith("#Positions: "):
                    nofPositions = line.split(" ")[1]
                else:
                    if inStrategyTransitions:
                        strategyLines.append(line.strip())
            if perf is None:
                print("Error: No performance in file "+resultFile+" found.")
                sys.exit(1)
            print(perf+" & "+nofPositions)
            
            if resultFile!=destSmallNonAntichains:
                print(" & ")

    
    # End of line
    print("\\\\")
    
# End
print("\\end{tabular}")
