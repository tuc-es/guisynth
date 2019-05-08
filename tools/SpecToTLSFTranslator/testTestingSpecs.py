#!/usr/bin/env python3
import os
import sys,glob

testingFiles = glob.glob("testingSpecs/*.txt")

for ts in testingFiles:

    print("----> "+ts)
    assert os.system("../../tools/SpecToTLSFTranslator/translator.py < " + ts + " > /tmp/intermediate.tlfs")==0
    
    assert os.system("../../lib/strix/bin/strix -r /tmp/intermediate.tlfs > /tmp/result.strix")==0
    strixResult = None
    with open("/tmp/result.strix","r") as inFile:
        for line in inFile.readlines():
            if line.startswith("UNREALIZABLE"):
                strixResult = False
            elif line.startswith("REALIZABLE"):
                strixResult = True
    assert not strixResult is None
    
    if strixResult:
        print("Strix says it's realizable")
    else:
        print("Strix says it's unrealizable")
        
    
    xmlFile = ts[0:-4]+".xml"
    
    # Run Orchestrator
    assert os.system("../Orchestrator/orchestratorExplicit.py "+xmlFile+" "+ts+" /dev/null > /tmp/orchesRes 2>&1")==0
    
    orchesResult = None
    with open("/tmp/orchesRes","r") as inFile:
        for line in inFile.readlines():
            if line.startswith("UNREALIZABLE"):
                orchesResult = False
            elif line.startswith("REALIZABLE"):
                orchesResult = True
    assert not orchesResult is None
    
    if orchesResult:
        print("Orchestrator says it's realizable")
    else:
        print("Orchestrator says it's unrealizable")
    
    assert orchesResult==strixResult
    
