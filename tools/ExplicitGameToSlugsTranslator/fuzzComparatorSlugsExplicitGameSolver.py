#!/usr/bin/env python3
import os, sys, random, time, subprocess
random.seed(time.time())
startSeed = int(time.time()*(random.random()*100+0.1))


# ============
# OPTIONS
# ============
NOF_STATES_PER_TYPE = 5
NOF_TRANSITIONS_ASSUMPTIONS = 10
NOF_TRANSITIONS_GUARANTEES = 40
NOF_ACTIONS_PER_TYPE = 3


nofIteration = 0
while True:
    # ===============
    # Build Spec file
    # ===============
    nofIteration+=1
    startSeed += 1
    random.seed(startSeed)

    # Prepare
    actionsEnv = ["envAction"+str(i) for i in range(0,NOF_ACTIONS_PER_TYPE)]
    actionsSys = ["done"]+["sysAction"+str(i) for i in range(0,NOF_ACTIONS_PER_TYPE)]
    statesA = ["stateA"+str(i) for i in range(0,NOF_STATES_PER_TYPE)]
    statesG = ["stateG"+str(i) for i in range(0,NOF_STATES_PER_TYPE)]

    allActions = actionsEnv+actionsSys

    # This is where the spec goess
    specFile = ["UVWBasedGame"]

    # Input / Output
    for a in actionsEnv:
        specFile.append("Input "+a)
    for a in actionsSys:
        specFile.append("Output "+a)
        
    # Sink states
    specFile.append("State Assumptions rej reject")
    specFile.append("State Guarantees rej reject")
        
    for a in statesA:
        labels = []
        if random.random()>0.3:
            labels.append("initial")
        if random.random()>0.3:
            labels.append("reject")
        labels = " ".join(labels)
        if len(labels)>0:
            labels = " "+labels
        specFile.append("State Assumptions "+a+labels)
    for a in statesG:
        labels = []
        if random.random()>0.3:
            labels.append("initial")
        if random.random()>0.3:
            labels.append("reject")
        labels = " ".join(labels)
        if len(labels)>0:
            labels = " "+labels
        specFile.append("State Guarantees "+a+labels)

    # Add "rej" states to state lists
    statesA = ["rej"]+statesA
    statesG = ["rej"]+statesG

    # Transitions
    specFile.append("Transition Assumptions rej TRUE rej")
    specFile.append("Transition Guarantees rej TRUE rej")

    for (statesOfRelevance,typeString,number) in [(statesA,"Assumptions",NOF_TRANSITIONS_ASSUMPTIONS),(statesG,"Guarantees",NOF_TRANSITIONS_GUARANTEES)]:
        for i in range(0,number):
            startingIndex = int(random.random()*(len(statesOfRelevance)-1))+1
            endIndex = int(random.random()*startingIndex)
            
            transitionType = int(random.random()*10)
            if (transitionType<2):
                # True Transition
                specFile.append("Transition "+typeString+" "+statesOfRelevance[startingIndex]+" TRUE "+statesOfRelevance[endIndex])
            elif transitionType<6:
                # Not cases
                chosenActions = [a for a in allActions if random.random()<0.1]+["FALSE"]
                specFile.append("Transition "+typeString+" "+statesOfRelevance[startingIndex]+" "+"& "*(len(chosenActions)-1)+" ".join(["! "+a for a in chosenActions])+" "+statesOfRelevance[endIndex])
            else:
                # Standard case
                chosenAction = allActions[int(random.random()*len(allActions))]
                specFile.append("Transition "+typeString+" "+statesOfRelevance[startingIndex]+" "+chosenAction+" "+statesOfRelevance[endIndex])

    specFile.append("")


    # ===============
    # Run the game solver
    # ===================
    procA = subprocess.Popen("../ExplicitGameSolver/gamesolver --nice /dev/stdin --graph",shell=True,stdin=subprocess.PIPE,stderr=subprocess.STDOUT,stdout=subprocess.PIPE)
    for line in specFile:
        procA.stdin.write((line+"\n").encode("utf-8"))
    procA.stdin.close()
    
    isRealizable = None
    for line in procA.stdout.readlines():
        line = line.decode("utf-8").strip()
        if line=="REALIZABLE":
            isRealizable = True
        elif line=="UNREALIZABLE":
            isRealizable = False
    
    if procA.wait()!=0:
        print("Game solver terminated in the middle, writing specification to file")    
        with open("specFile.txt","w") as outFile:
            outFile.write("\n".join(specFile))
        raise Exception("Terminated")
    
    # Got result?
    if isRealizable is None:
        print("No result from running game solver, writing to file")    
        with open("specFile.txt","w") as outFile:
            outFile.write("\n".join(specFile))
        raise Exception("Terminated")

    if isRealizable:
        sys.stdout.write(".")
    else:
        sys.stdout.write("#")
    sys.stdout.flush()
    
    
    # ============================
    # Translate to structuredslugs
    # ============================
    procB = subprocess.Popen("./translator.py",shell=True,stdin=subprocess.PIPE,stderr=subprocess.STDOUT,stdout=subprocess.PIPE)
    for line in specFile:
        procB.stdin.write((line+"\n").encode("utf-8"))
    procB.stdin.close()
    
    structuredSlugs = [a.decode("utf-8").strip() for a in procB.stdout.readlines()]

    if procB.wait()!=0:
        print("To structuredslugs translator terminated in the middle, writing specification to file")    
        with open("specFile.txt","w") as outFile:
            outFile.write("\n".join(specFile))
        raise Exception("Terminated")
    
    # ============================
    # Run structuredslugs -> slugsin translator
    # ============================
    procC = subprocess.Popen("./slugsinCompiler.py /dev/stdin",shell=True,stdin=subprocess.PIPE,stderr=subprocess.STDOUT,stdout=subprocess.PIPE)
    for line in structuredSlugs:
        procC.stdin.write((line+"\n").encode("utf-8"))
    procC.stdin.close()
    
    slugsin = [a.decode("utf-8").strip() for a in procC.stdout.readlines()]

    if procC.wait()!=0:
        print("To slugsin translator terminated in the middle, writing specification to file.\nDID YOU MAKE SYMBOLIC LINKS TO THE SLUGSIN COMPILER AND SLUGS BEFORE RUNNING???\n")    
        with open("specFile.txt","w") as outFile:
            outFile.write("\n".join(specFile))
        raise Exception("Terminated")

    # ============================
    # Run slugs
    # ============================
    procD = subprocess.Popen("./slugs /dev/stdin",shell=True,stdin=subprocess.PIPE,stderr=subprocess.STDOUT,stdout=subprocess.PIPE)
    for line in slugsin:
        procD.stdin.write((line+"\n").encode("utf-8"))
    procD.stdin.close()
    
    slugsout = [a.decode("utf-8").strip() for a in procD.stdout.readlines()]

    if procD.wait()!=0:
        print("Running slugs failed. Perhaps the executable was not found in the current directory? Writing the current specification file.\n")    
        with open("specFile.txt","w") as outFile:
            outFile.write("\n".join(specFile))
        raise Exception("Terminated")

    isSlugsRealizable = None
    for line in slugsout:
        if line=="RESULT: Specification is realizable.":
            isSlugsRealizable = True
        elif line=="RESULT: Specification is unrealizable.":
            isSlugsRealizable = False

    if isSlugsRealizable is None:
        print("Running slugs yielded no results. Writing the specification file.\n")    
        with open("specFile.txt","w") as outFile:
            outFile.write("\n".join(specFile))
        raise Exception("Terminated")

    if isSlugsRealizable!=isRealizable:
        print("Error: Diverging results. Whether slugs thinks the specification is realizable:",isSlugsRealizable)
        print("Writing the spefication to file!")
        with open("specFile.txt","w") as outFile:
            outFile.write("\n".join(specFile))
        raise Exception("Terminated")
        
        
    if (nofIteration % 100)==0:
        sys.stdout.write("("+str(nofIteration)+","+str(startSeed)+")")
        sys.stdout.flush()
