#!/usr/bin/env python3
import os, sys, subprocess

# Translator GUISynth----->TLSF
#
# Limits:
# - Waiting for nothing is allowed!

# ============================================
# Base path for running other tools
# ============================================
basePath = sys.argv[0][0:sys.argv[0].rfind("translator.py")]

# ============================================
# Functions
# ============================================
def getNofBitsNeeded(d):
    nofBits = 0
    while (d>(1<<nofBits)):
        nofBits += 1
    return nofBits

parts = {"[CustomInputActions]":[],
    "[CustomOutputActions]":[],
    "[Threads]":[],
    "[Assumptions]":[],
    "[Guarantees]":[]}

currentSection = None
for line in sys.stdin.readlines():
    line = line.strip()
    if line.startswith("["):
        currentSection = line
    else:
        if not line.startswith("#"):
            if len(line)>0:
                parts[currentSection].append(line)
        
                
allInputs = ["init"]+parts["[CustomInputActions]"]+[a+".terminates" for a in parts["[Threads]"]]
allOutputs = ["done"]+parts["[CustomOutputActions]"]+[a+".start" for a in parts["[Threads]"]]

# =====================================================
# First pass -- propositions
# =====================================================
with subprocess.Popen(basePath+"../LTLToPolish/ltl2polish",stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as polishProcess:
    for sectionName in ["[Assumptions]","[Guarantees]"]:
        for specFilePartLineNo in range(0,len(parts[sectionName])):
            lineText = parts[sectionName][specFilePartLineNo]
            polishProcess.stdin.write((lineText+"\n").encode())
            polishProcess.stdin.flush()
            polished = polishProcess.stdout.readline()
            if len(polished)==0:
                # Error
                print("".join([a.decode() for a in polishProcess.stderr.readlines()]),file=sys.stderr)
                polishProcess.wait()
                sys.exit(1)
            polished = polished.decode().strip()
            assert polished.startswith("LTL ")
            polished = polished[4:]
            
            # replace ANYOUTPUTS
            pparts = polished.split(" ")
            for part in pparts:
                if "." in part:
                    if not part in allInputs+allOutputs: 
                        if part.endswith(".hide"):
                            allOutputs.append(part)
                        elif part.endswith(".show"):
                            allOutputs.append(part)
                        elif part.endswith(".disable"):
                            allOutputs.append(part)
                        elif part.endswith(".enable"):
                            allOutputs.append(part)
                        elif part.endswith(".selected"):
                            allInputs.append(part)
                        elif part.endswith(".click"):
                            allInputs.append(part)
                        else:                        
                            assert False

    polishProcess.stdin.close()

# =====================================================
# Translate the specification parts to polish LTL
# =====================================================
with subprocess.Popen(basePath+"../LTLToPolish/ltl2polish",stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as polishProcess:
    for sectionName in ["[Assumptions]","[Guarantees]"]:
        for specFilePartLineNo in range(0,len(parts[sectionName])):
            lineText = parts[sectionName][specFilePartLineNo]
            polishProcess.stdin.write((lineText+"\n").encode())
            polishProcess.stdin.flush()
            polished = polishProcess.stdout.readline()
            if len(polished)==0:
                # Error
                print("".join([a.decode() for a in polishProcess.stderr.readlines()]),file=sys.stderr)
                polishProcess.wait()
                sys.exit(1)
            polished = polished.decode().strip()
            assert polished.startswith("LTL ")
            polished = polished[4:]
            
            # replace ANYOUTPUTS
            pparts = polished.split(" ")
            for i,a in enumerate(pparts):
                if a=="ANYOUTPUTS":
                    pparts[i] = "| "*(len(allOutputs)-1)+" ".join(allOutputs)
            pparts = (" ".join(pparts)).split(" ")
            
            parts[sectionName][specFilePartLineNo] = pparts
    polishProcess.stdin.close()


# =====================================================
# Header
# =====================================================
nofInputBits = getNofBitsNeeded(len(allInputs)+1)
nofOutputBits = getNofBitsNeeded(len(allOutputs)+1)

print("INFO {")
print("    TITLE:       \"Automatically translated\"")
print("    DESCRIPTION: \"Automatically translated\"")
print("    SEMANTICS:   Mealy")
print("    TARGET:      Mealy")
print("}")

print("MAIN {")
print("    INPUTS {")
for i in range(0,nofInputBits):
    print("      x"+str(i)+";")
print("    }")
print("    OUTPUTS {")
for i in range(0,nofOutputBits):
    print("      y"+str(i)+";")
print("    }")

allInputBits = ["x"+str(i) for i in range(0,nofInputBits)]
allOutputBits = ["y"+str(i) for i in range(0,nofOutputBits)]

# =====================================================
# Translate
# =====================================================
def translateToInfix(part,pos):
    if part[pos]=="G":
        (nextPos,t) = translateToInfix(part,pos+1)
        return (nextPos,"(G("+t+"))")
    if part[pos]=="F":
        (nextPos,t) = translateToInfix(part,pos+1)
        return (nextPos,"(F("+t+"))")
    if part[pos]=="X":
        (nextPos,t) = translateToInfix(part,pos+1)
        return (nextPos,"(X("+t+"))")
    if part[pos]=="!":
        (nextPos,t) = translateToInfix(part,pos+1)
        return (nextPos,"(!("+t+"))")
    if part[pos]=="U":
        (nextPos,t) = translateToInfix(part,pos+1)
        (nextPos2,t2) = translateToInfix(part,nextPos)
        return (nextPos2,"(("+t+") U ("+t2+"))")
    if part[pos]=="&":
        (nextPos,t) = translateToInfix(part,pos+1)
        (nextPos2,t2) = translateToInfix(part,nextPos)
        return (nextPos2,"(("+t+") & ("+t2+"))")
    if part[pos]=="|":
        (nextPos,t) = translateToInfix(part,pos+1)
        (nextPos2,t2) = translateToInfix(part,nextPos)
        return (nextPos2,"(("+t+") | ("+t2+"))")
    if part[pos]=="->":
        (nextPos,t) = translateToInfix(part,pos+1)
        (nextPos2,t2) = translateToInfix(part,nextPos)
        return (nextPos2,"(("+t+") -> ("+t2+"))")
    if part[pos]=="W":
        (nextPos,t) = translateToInfix(part,pos+1)
        (nextPos2,t2) = translateToInfix(part,nextPos)
        return (nextPos2,"(("+t+") W ("+t2+"))")
    
    # Rest...
    if part[pos] in allInputs:
        i = allInputs.index(part[pos])+1
        m = []
        for j in range(0,len(allInputBits)):
            if (i & (1<<j))!=0:
                m.append(allInputBits[j])
            else:
                m.append("! "+allInputBits[j])
        return (pos+1,"("+" & ".join(m)+")")
    elif part[pos] in allOutputs:
        i = allOutputs.index(part[pos])+1
        m = []
        for j in range(0,len(allOutputBits)):
            if (i & (1<<j))!=0:
                m.append(allOutputBits[j])
            else:
                m.append("! "+allOutputBits[j])
        return (pos+1,"("+" & ".join(m)+")")
    else:
        raise Exception("Don't know what to do with "+part[pos]+" in the formula "+" ".join(part))


# =====================================================
# Assumptions
# =====================================================
print("    ASSUMPTIONS {")
# Only select an input if there is no output
print("      G((X("+" | ".join(allInputBits)+")) -> ("+" & ".join(["! "+a for a in allOutputBits[1:]])+"));")
# After an input, the output player has to have a chance to respond.
print("      G(("+" | ".join(allInputBits)+") -> X("+" & ".join(["! "+a for a in allInputBits])+"));")

# Other assumptions
for a in parts["[Assumptions]"]:
    (d,p) = translateToInfix(a,0)
    assert d==len(a)
    print("      "+p+";")

print("    }")


# =====================================================
# Guarantees
# =====================================================
print("    GUARANTEES {")
# Can only emit output if there was something before
print("      G((X("+" | ".join(allOutputBits)+")) -> ("+" | ".join(allInputBits+allOutputBits)+"));")
# System is silent if there is a input
print("      G((("+" | ".join(allOutputBits)+")) -> ("+" & ".join(["! "+a for a in allInputBits])+"));")
# But System is not silent *after an input*
print("      G((("+" | ".join(allInputBits)+")) -> X("+" | ".join([a for a in allOutputBits])+"));")
# If there is some data, then eventually done
print("      G((("+" | ".join(allOutputBits)+")) -> ((!("+" & ".join(["! "+a for a in allOutputBits])+")) U (("+"& ".join(["! "+a for a in allOutputBits[1:]])+" & y0))));")
# After a done, no next output
print("      G(("+allOutputBits[0]+" & "+" & ".join(["! "+a for a in allOutputBits[1:]])+") -> X("+" & ".join(["! "+a for a in allOutputBits])+"));")


# Other guarantees
for a in parts["[Guarantees]"]:
    (d,p) = translateToInfix(a,0)
    assert d==len(a)
    print("      "+p+";")

print("    }")


# End
print("}")
