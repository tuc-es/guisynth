#!/usr/bin/env python3
import os, sys
from scenarioPairs import SCENARIO_PAIRS

# Header
print("\\begin{tabular}{l|l||l|l|l|l||l|l|l|l}")
print("\\multicolumn{2}{c||}{\\textbf{Specification}}")
print("& \\multicolumn{4}{|c||}{\\textbf{Game solving}}")
print("& \\multicolumn{4}{|c}{\\textbf{Game solving}}")
print("\\\\")
print("\\multicolumn{2}{c||}{\\textbf{}}")
print("& \\multicolumn{4}{|c||}{\\textbf{(not kind)}}")
print("& \\multicolumn{4}{|c}{\\textbf{(kind)}} \\\\")
print("\\textbf{Rev.} & \\textbf{\#~Pro-}")
print("& \\textbf{Time} & \\textbf{Size} & \\textbf{Size st.} & \\textbf{\# Pos.}")
print("& \\textbf{Time} & \\textbf{Size} & \\textbf{Size st.} & \\textbf{\# Pos.}")
print("\\\\")

print("\\textbf{} & \\textbf{perties}")
print("& \\textbf{} & \\textbf{strat.} & \\textbf{flat} & \\textbf{reach.}")
print("& \\textbf{} & \\textbf{strat.} & \\textbf{flat} & \\textbf{reach.}")
print("\\\\ \\hline")


# Store analyszed stuff
maxLengthDecisionSequences = []

for i,(x,a) in enumerate(SCENARIO_PAIRS):
    dest = ".out/"+a+".game"
    destPerf = ".out/"+a+".gameTime"
    destSmall = ".out/"+a+".guisynthSmall"
    destKind = ".out/"+a+".guisynthKind"
    
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
        
    # 5. Own tool
    for resultFile in [destSmall,destKind]:
        maxLengthDecisionSequence = 0
        with open(resultFile,"r") as inFile:
            perf = None
            strategyLines = []
            inStrategyTransitions = False
            for line in inFile.readlines():
                if line.startswith("FINISHED CPU "):
                    perf = line.split(" ")[2]
                elif line.startswith("TRANSITIONS"):
                    inStrategyTransitions = True
                elif line.startswith("ENDTRANSITIONS"):
                    inStrategyTransitions = False
                else:
                    if inStrategyTransitions:
                        strategyLines.append(line.strip())
            assert not perf is None
            print(perf+" & ")
            
            # Nof states
            core = set([])
            for line in strategyLines:
                line = line.split(" ")
                core.add((line[0],line[1]))
                maxLengthDecisionSequence = max(maxLengthDecisionSequence,len(line)-5)
            print(str(len(core))+"&")
            maxLengthDecisionSequences.append(maxLengthDecisionSequence)
            
            # Nof states flat
            core = set([])
            for line in strategyLines:
                line = line.split(" ")
                for i in range(2,len(line)-2):
                    core.add(tuple(line[i:]))
            print(str(len(core))+"&")
            
            # Nof states reachable
            core = set([])
            for line in strategyLines:
                line = line.split(" ")
                core.add(line[1])
            print(str(len(core)))
            
            if (resultFile==destSmall):
                print("&")

    
    # End of line
    print("\\\\")
    
# End
print("\\end{tabular}")
# print("Max Lengths decision sequences: ",str(maxLengthDecisionSequences))
