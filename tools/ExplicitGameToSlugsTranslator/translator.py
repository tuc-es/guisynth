#!/usr/bin/env python3
#
# Translates a game for GUISynth to a specification file for slugs.
#
# Reads from stdin, writes to stdout
import os, sys

# Check preamble
firstLine = sys.stdin.readline()
if firstLine.strip()!="UVWBasedGame":
    print("Error: Expected a UVWBasedGame.",file=sys.stderr)
    sys.exit(1)

# Declare variables
inputSignals = []
outputSignals = []
states = [] # Format: (name,typeBool--assumptions=False)
rejectingStates = []
initialStates = []
transitions = []

# Read input lines
for line in sys.stdin.readlines():
    lineparts = line.strip().split(" ")
    if lineparts[0]=="Input":
        assert len(lineparts)==2
        inputSignals.append(lineparts[1])
    elif lineparts[0]=="Output":
        assert len(lineparts)==2
        outputSignals.append(lineparts[1])
    elif lineparts[0]=="State":
        assert lineparts[1] in ["Assumptions","Guarantees"]
        stateName = lineparts[2]
        states.append((stateName,lineparts[1]=="Guarantees"))
        for flag in lineparts[3:]:
            if flag=="reject":
                rejectingStates.append((stateName,lineparts[1]=="Guarantees"))
            elif flag=="initial":
                initialStates.append((stateName,lineparts[1]=="Guarantees"))
            else:
                raise Exception("Unknown state flag: "+flag)
    elif lineparts[0]=="Transition":
        assert lineparts[1] in ["Assumptions","Guarantees"]    
        typeFlag = lineparts[1]=="Guarantees"
        transitions.append((typeFlag,lineparts[2],lineparts[-1],lineparts[3:-1]))

# Turn length for the output player
limit_turnlength = 16

# Input Propositions and Output Propositions
nofInputPropositions = 1
while (1 << nofInputPropositions) <= len(inputSignals):
    nofInputPropositions += 1
nofOutputPropositions = 1
while (1 << nofOutputPropositions) <= len(outputSignals):
    nofOutputPropositions += 1
inputPropositions = ["inap"+str(a) for a in range(0,nofInputPropositions)]
outputPropositions = ["outap"+str(a) for a in range(0,nofOutputPropositions)]

# Encode signals into propositions
signalEncodingsPre = {}
signalEncodingsPost = {}
# ---> input
for i,a in enumerate(inputSignals):
    m = ("& "*(nofInputPropositions-1)).strip()
    mP = ("& "*(nofInputPropositions-1)).strip()
    for j in range(0,nofInputPropositions):
        if ((1 << j) & (i+1))>0:
            m = m + " "+inputPropositions[j]
            mP = mP + " "+inputPropositions[j]+"'"            
        else:
            m = m + " ! "+inputPropositions[j]
            mP = mP + " ! "+inputPropositions[j]+"'"
    signalEncodingsPre[a] = m
    signalEncodingsPost[a] = mP
# ---> output
for i,a in enumerate(outputSignals):
    m = ("& "*(nofOutputPropositions-1)).strip()
    mP = ("& "*(nofOutputPropositions-1)).strip()
    for j in range(0,nofOutputPropositions):
        if ((1 << j) & (i+1))>0:
            m = m + " "+outputPropositions[j]
            mP = mP + " "+outputPropositions[j]+"'"            
        else:
            m = m + " ! "+outputPropositions[j]
            mP = mP + " ! "+outputPropositions[j]+"'"
    signalEncodingsPre[a] = m
    signalEncodingsPost[a] = mP
            
assert len(signalEncodingsPre)==len(inputSignals)+len(outputSignals)

# No action
noActionOutputPre = ("& "*(nofOutputPropositions-1))+" ".join(["! "+a for a in outputPropositions])
noActionOutputPost = ("& "*(nofOutputPropositions-1))+" ".join(["! "+a+"'" for a in outputPropositions])
noActionInputPre = ("& "*(nofInputPropositions-1))+" ".join(["! "+a for a in inputPropositions])
noActionInputPost = ("& "*(nofInputPropositions-1))+" ".join(["! "+a+"'" for a in inputPropositions])


# Define action encoding function
def encodeAction(actionList):
    result = []
    for a in actionList:
        if a in signalEncodingsPre:
            result.append(signalEncodingsPre[a])
        else:
            result.append(a)
    return result


# Sanity check.....
assert outputSignals[0]=="done"

# Generate Preamble
print("[INPUT]")
for i in inputPropositions:
    print(i)
print("\n[OUTPUT]")
for o in outputPropositions:
    print(o)
for (statename,typ) in states:
    if typ:
        combined = "g_"+statename
    else:
        combined = "a_"+statename
    print(combined)
    
# Special output action: mode.
print("turn")
print("turnlength:0..."+str(limit_turnlength-1))
    
# Initial state
print("\n[SYS_INIT]")
for (statename,typ) in states:
    if typ:
        combined = "g_"+statename
    else:
        combined = "a_"+statename
    if (statename,typ) in initialStates:
        print(combined)
    else:
        print("! "+combined)
print("! turn")
        
# Input Actions -- Exactly one

print("\n[ENV_INIT]\n")

# Initially, exactly one valid input.
print("| "*(len(inputSignals)-1)+" ".join([signalEncodingsPre[a] for a in inputSignals]))


print("\n[ENV_TRANS]\n")
# Either there is an input or not
print("| "*len(inputSignals)+" ".join([signalEncodingsPost[a] for a in inputSignals])+" "+noActionInputPost)

# No turn? No input!
for a in inputSignals:
    print("| turn ! "+signalEncodingsPost[a])                

# If there is a turn, then valid input
print("| ! turn "+"| "*(len(inputSignals)-1)+" ".join([signalEncodingsPost[a] for a in inputSignals]))

# Output Actions -- Initially none
print("\n[SYS_INIT]")
print(noActionOutputPre)

# Output Actions - afterwards, one if it is not the environment player's turn
print("\n[SYS_TRANS]")
outputVarsPrimed = [a+"'" for a in outputSignals]
print("| "*len(outputSignals)+" ".join([signalEncodingsPost[a] for a in outputSignals])+" turn")
for a in outputSignals:
    print("| ! turn ! "+signalEncodingsPost[a])

# SYS_TRANS -- Turn semantics -- The variable tells if it is the environment player's turn NEXT -- 
print("[SYS_TRANS]")
print("turn -> ! turn'")
print("! turn -> (turnlength'=turnlength+1)")

# encode "! turn -> (done' <-> turn')"
print("| turn ! ^ turn' "+signalEncodingsPost["done"])

# Updating the state information
print("[SYS_TRANS]")

for (name,stateType) in states:
    if stateType:
        prefix = "g_"
    else:
        prefix = "a_"
    incoming = []
    for (typeflag,fromState,toState,label) in transitions:
        # print((typeflag,fromState,toState,label))
        if typeflag==stateType and toState==name:
            def retrue(k):
                if k=="TRUE":
                    return "1"
                elif k=="FALSE":
                    return "0"
                return k
            incoming.append((fromState,[retrue(a) for a in label]))
    # print(incoming)
    print("! ^ "+prefix+name+"' "+"| "*(len(incoming))+" ".join(["& "+prefix+fromstate+" "+" ".join(encodeAction(label)) for (fromstate,label) in incoming]+["0"]))
   
   
# Liveness assumptions & Guarantees
for (name,stateType) in rejectingStates:
    if stateType:
        prefix = "g_"
        print("[SYS_LIVENESS]")
    else:
        prefix = "a_"
        print("[ENV_LIVENESS]")
    incoming = []
    for (typeflag,fromState,toState,label) in transitions:
        # print((typeflag,fromState,toState,label))
        if typeflag==stateType and toState==name and fromState==name:
            def retrue(k):
                if k=="TRUE":
                    return "1"
                elif k=="FALSE":
                    return "0"

                return k
            incoming.append([retrue(a) for a in label])

    print("| | ! "+prefix+name+" ! "+prefix+name+"' ! "+"| "*(len(incoming))+" ".join([" ".join(encodeAction(label)) for label in incoming]+["0"]))
    
    
# Special waiting semantics: The system must never be in a state where it is waiting, but the environment is not.
# print(rejectingStates)
for (postFlag,section) in [(True,"[SYS_TRANS]"),(False,"[SYS_INIT]")]:
    print(section)
    if postFlag:
        postfix="'"
    else:
        postfix=""
    rejectingAssumptionStates = ["a_"+a+postfix for (a,b) in rejectingStates if not b]+["0"]
    if postFlag:
        rejectingAssumptionStates.append("! turn")
    for (nameA,flagA) in rejectingStates:
        if flagA==True:
            print("| ! g_"+nameA+postfix+" "+"| "*(len(rejectingAssumptionStates)-1)+" ".join(rejectingAssumptionStates))

# Special Error semantics
systemStates = [a for (a,b) in states if b]
environmentStates = [a for (a,b) in states if not b]
print("[SYS_TRANS]")
print("| | ! turn ! g_"+systemStates[0]+"' a_"+environmentStates[0]+"'")

print("[SYS_INIT]")
print("| ! g_"+systemStates[0]+" a_"+environmentStates[0])

