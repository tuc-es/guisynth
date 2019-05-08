#!/usr/bin/env python3
import os, sys, subprocess
print("------------------------------------------------------------------------")

# ============================================
# Read parameters
# ============================================
if len(sys.argv)<4:
    print("Error: Expected three file names:\n (1) the XML file for the activity,\n (2) the specification file, and\n (3) the java file name in which to inject the generated code.",file=sys.stderr)
    sys.exit(1)
activityXMLFileName = sys.argv[1]
specificationFileName = sys.argv[2]
javaFileName = sys.argv[3]
otherOptions = sys.argv[4:]

# ============================================
# Parse other options
# ============================================
gameSideOutputFilename = None
nice = True
onlyGameConstruction = False
posOtherOptions = 0
while posOtherOptions<len(otherOptions):
    if otherOptions[posOtherOptions]=="--gameOutputFile":
        gameSideOutputFilename = otherOptions[posOtherOptions+1] 
        posOtherOptions += 2
    elif otherOptions[posOtherOptions]=="--notNice":
        nice = False
        posOtherOptions += 1
    elif otherOptions[posOtherOptions]=="--onlyGameConstruction":
        onlyGameConstruction = True
        posOtherOptions += 1
    else:
        print("Error: Did not understand option",otherOptions[posOtherOptions],file=sys.stderr)
        sys.exit(1)


# ============================================
# Base path for running other tools
# ============================================
basePath = sys.argv[0][0:sys.argv[0].rfind("orchestratorExplicit.py")]


# ============================================
# Read specification file
# ============================================
with open(specificationFileName,"r") as inFile:
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



# ============================================
# Read Activity XML file
# ============================================
import xml.etree.ElementTree as ET
tree = ET.parse(activityXMLFileName)
root = tree.getroot()

# ============================================
# Define events for types of elements
# ============================================
OUTPUT_EVENTS_BY_TYPE = {
    "Button":["enable","disable"],
    "TextView":[],
	"CheckBox":["check","uncheck"],
	"Switch":["check","uncheck"],
	"ImageView":[],
	"TableLayout":["hide","show"],
	"GridLayout":["hide","show"],
	"TableRow":[],	
	"android.support.design.widget.NavigationView":[],
	"ListView":["enable","disable"],
	"EditText":["enable","disable"],	
	"WebView":[],
	"Spinner":[],
}

INPUT_EVENTS_BY_TYPE = {
    "Button":["click"],
    "TextView":[],
    "Switch":["click","checked","unchecked"],
	"CheckBox":["click","checked","unchecked"],
	"ImageView":[],
	"GridLayout":[],
	"TableLayout":[],
	"TableRow":[],	
	"android.support.design.widget.NavigationView":[],
	"ListView":["selected"],
	"EditText":[],
	"WebView":[],
	"Spinner":[],
}

GUI_OBJECTS_SHOULD_RECURSE = {
    "Button":False,
    "TextView":False,
    "Switch":False,
	"CheckBox":False,
	"ImageView":False,
	"TableLayout":True,
	"GridLayout":True,
	"TableRow":True,	
	"android.support.design.widget.NavigationView":True,
	"ListView":False,
	"EditText":False,
	"WebView":False,
	"Spinner":False,
}

OUTPUT_EVENT_TO_CODE_MAPPER = {
    ("Button","enable"):(lambda x: "final Button b = findViewById(R.id."+x+"); b.setEnabled(true);"),
    ("Button","disable"):(lambda x: "final Button b = findViewById(R.id."+x+"); b.setEnabled(false);"),
	("Checkbox","check"):(lambda x: "final Checkbox c = findViewById(R.id."+x+"); c.setChecked(true);"),
	("Checkbox","uncheck"):(lambda x: "final Checkbox c = findViewById(R.id."+x+"); c.setChecked(false);"),
    ("EditText","enable"):(lambda x: "final EditText b = findViewById(R.id."+x+"); b.setEnabled(true);"),
    ("EditText","disable"):(lambda x: "final EditText b = findViewById(R.id."+x+"); b.setEnabled(false);"),
	("Switch","check"):(lambda x: "final Switch c = findViewById(R.id."+x+"); c.setChecked(true);"),
	("Switch","uncheck"):(lambda x: "final Switch c = findViewById(R.id."+x+"); c.setChecked(false);"),
	("TableLayout","hide"):(lambda x: "final TableLayout c = findViewById(R.id."+x+"); c.setVisibility(View.INVISIBLE);"),
	("TableLayout","show"):(lambda x: "final TableLayout c = findViewById(R.id."+x+"); c.setVisibility(View.VISIBLE);"),
	("GridLayout","hide"):(lambda x: "final GridLayout c = findViewById(R.id."+x+"); c.setVisibility(View.INVISIBLE);"),
	("GridLayout","show"):(lambda x: "final GridLayout c = findViewById(R.id."+x+"); c.setVisibility(View.VISIBLE);"),
    ("ListView","enable"):(lambda x: "final ListView b = findViewById(R.id."+x+"); b.setEnabled(true);"),
    ("ListView","disable"):(lambda x: "final ListView b = findViewById(R.id."+x+"); b.setEnabled(false);"),

}

INPUT_OBJECT_TO_CODE_MAPPER = {
    "Button":(lambda x,y: """{ final Button k = findViewById(R.id."""+x+""");
    k.setOnClickListener(new Button.OnClickListener() {
        public void onClick(View v) {
                """+y["click"]+"""
                }
        }); }"""),

	"CheckBox":(lambda x,y: """{ final CheckBox k = findViewById(R.id."""+x+""");
    k.setOnClickListener(new CheckBox.OnClickListener() {
        public void onClick(View v) {
                """+y["click"]+"""
                if (k.isChecked()) {
                    """+y["checked"]+"""
                } else {
                    """+y["unchecked"]+"""
                }
            }
        }); }"""),
	"Switch":(lambda x,y: """{ final Switch k = findViewById(R.id."""+x+""");
    k.setOnClickListener(new Switch.OnClickListener() {
        public void onClick(View v) {
                """+y["click"]+"""
                if (k.isChecked()) {
                    """+y["checked"]+"""
                } else {
                    """+y["unchecked"]+"""
                }
            }
        }); }"""),
    "ListView":(lambda x,y: """{ final ListView k = findViewById(R.id."""+x+""");
    k.setOnItemClickListener(new AdapterView.OnItemClickListener() {
        public void onItemClick(AdapterView<?> adapterView, View view, int i, long l) {
                selectedItem_"""+x+""" = i;
                """+y["selected"]+"""
            }
        }); }"""),

}

INPUT_OBJECT_TO_AUTO_GENERATED_DECLARATION_CODE_MAPPER = {
    "ListView":(lambda x,y: """int selectedItem_"""+x+""" = -1;
                """)
}

# ============================================
# Aggregate actions for the specifications
# ============================================

# The standards
inputEvents = ["init"]
outputEvents = ["done"]
typeOfObjectsUsedInSpecifications = {}

# Actions from the UI elements
def recurseProcess(child):
    elementType = child.tag
    if elementType=="android.support.constraint.ConstraintLayout":
        for child2 in child.getchildren():
            recurseProcess(child2)
    else:
        # Get ID of the child (and filter out prefix
        if not "{http://schemas.android.com/apk/res/android}id" in child.attrib:
            print("Warning: There exists a "+elementType+" element with no ID -- it thus cannot be used in the specification.")
            if GUI_OBJECTS_SHOULD_RECURSE[elementType]:
                for child2 in child.getchildren():
                    recurseProcess(child2)
        else:
            idName = child.attrib["{http://schemas.android.com/apk/res/android}id"]
            if idName.startswith("@+id/"):
                idName = idName[5:]
            inputEvents.extend([idName+"."+a for a in INPUT_EVENTS_BY_TYPE[elementType]])
            outputEvents.extend([idName+"."+a for a in OUTPUT_EVENTS_BY_TYPE[elementType]])
            typeOfObjectsUsedInSpecifications[idName] = elementType
            if GUI_OBJECTS_SHOULD_RECURSE[elementType]:
                for child2 in child.getchildren():
                    recurseProcess(child2)

for child in root.getchildren():
    recurseProcess(child)


# Threads
threadList = []
for (thread,line) in specFileParts["Threads"]:
    inputEvents.append(thread+".terminates")
    outputEvents.append(thread+".start")
    threadList.append(thread)

# CustomInputActions
customInputActions = []
customOutputActions = []

for (action,line) in specFileParts["CustomInputActions"]:
    customInputActions.append(action)
    inputEvents.append(action)
for (action,line) in specFileParts["CustomOutputActions"]:
    customOutputActions.append(action)
    outputEvents.append(action)

# =====================================================
# Sanity check
# =====================================================
if len(set(inputEvents))!=len(inputEvents):
    print("Error: There are multiple input events with the same name.",file=sys.stderr)
    for i,a in enumerate(inputEvents):
        for b in inputEvents[i+1:]:
            if a==b:
                print("Double: "+a,file=sys.stderr)
    print("Input events:",inputEvents,file=sys.stderr)
    sys.exit(1)
if len(set(outputEvents))!=len(outputEvents):
    print("Error: There are multiple output events with the same name.",file=sys.stderr)
    sys.exit(1)

# =====================================================
# Translate the specification parts to polish LTL
# =====================================================
with subprocess.Popen(basePath+"../LTLToPolish/ltl2polish",stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as polishProcess:
    for sectionName in ["Assumptions","Guarantees"]:
        for specFilePartLineNo in range(0,len(specFileParts[sectionName])):
            (lineText,lineNo) = specFileParts[sectionName][specFilePartLineNo]
            polishProcess.stdin.write((lineText+"\n").encode())
            polishProcess.stdin.flush()
            polished = polishProcess.stdout.readline()
            if len(polished)==0:
                # Error
                print("Error parsing specification file line",lineNo+1,"due to the following error:",file=sys.stderr)
                print("".join([a.decode() for a in polishProcess.stderr.readlines()]),file=sys.stderr)
                polishProcess.wait()
                sys.exit(1)
            polished = polished.decode().strip()
            assert polished.startswith("LTL ")
            polished = polished[4:]
            
            # replace ANYOUTPUTS
            parts = polished.split(" ")
            for i,a in enumerate(parts):
                if a=="ANYOUTPUTS":
                    parts[i] = "| "*(len(outputEvents)-1)+" ".join(outputEvents)
            polished = " ".join(parts)
            
            specFileParts[sectionName][specFilePartLineNo] = (polished,lineNo,lineText)
    polishProcess.stdin.close()


# =====================================================
# Translate them to UVWs
# =====================================================
allSpecParts = set([])
translatedSections = {}
for sectionName in ["Assumptions","Guarantees"]:
    with subprocess.Popen(basePath+"../PolishLTLToUVWTranslator/uvwBuilder.py /dev/stdin --singleAction",shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as translationProcess:
        translationProcess.stdin.write("LTL ".encode())
        allSpec = "& "*(len(specFileParts[sectionName])) + " ".join([a for (a,b,c) in specFileParts[sectionName]]+["1"])
        allSpecParts.update(allSpec.split(" "))
        print( "Compile: ",allSpec,file=sys.stderr)
        translationProcess.stdin.write((allSpec+"\n").encode())
        translationProcess.stdin.close()
        linesOut = translationProcess.stdout.readlines()
        linesErr = translationProcess.stderr.readlines()
        if (translationProcess.wait()!=0):
            print("Translation failed!",file=sys.stderr)
            print("".join([a.decode() for a in linesErr]),file=sys.stderr)
            print("Trying to find the culprit....",file=sys.stderr)
            for i in range(0,len(specFileParts[sectionName])):
                with subprocess.Popen(basePath+"../PolishLTLToUVWTranslator/uvwBuilder.py /dev/stdin",shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE) as translationCheckerProcess:
                    translationCheckerProcess.stdin.write("LTL ".encode())
                    allSpec = specFileParts[sectionName][i][0]
                    translationCheckerProcess.stdin.write((allSpec+"\n").encode())
                    translationCheckerProcess.stdin.close()
                    if (translationCheckerProcess.wait()!=0):
                        print("The following LTL specification part seems to be responsible:",file=sys.stderr)
                        print(specFileParts[sectionName][i][2],file=sys.stderr)
                        print("In Polish form, this is written as:",file=sys.stderr)
                        print(specFileParts[sectionName][i][0],file=sys.stderr)
                        print("Messages by the translator tool:",file=sys.stderr)
                        print(translationCheckerProcess.stdout.readlines(),file=sys.stderr)
                        sys.exit(1)
            print("Could not figure it out",file=sys.stderr)
            sys.exit(1)
        else:
            print("Translation succeeded!",file=sys.stderr)
        translatedSections[sectionName] = "".join([a.decode().replace("**TYPE**",sectionName) for a in linesOut])

# =====================================================
# Build overall specification file
# =====================================================
overallSpecFile = ["UVWBasedGame"]
overallSpecFile.extend(["Input "+a for a in inputEvents if a in allSpecParts or a=="init"])
overallSpecFile.extend(["Output "+a for a in outputEvents if a in allSpecParts or a=="done"])
overallSpecFile.append(translatedSections["Assumptions"])
overallSpecFile.append(translatedSections["Guarantees"])
overallSpecFile.append("") # Empty line at the end
print("Spec:\n"+"\n".join(overallSpecFile),file=sys.stderr)


# =====================================================
# Side output?
# =====================================================
if not gameSideOutputFilename is None:
    with open(gameSideOutputFilename,"w") as outFile:
        outFile.write(("\n".join([a for a in overallSpecFile])))

if onlyGameConstruction:
    sys.exit(0)
# =====================================================
# Run game solver
# =====================================================
strategy = []
if nice:
    niceString = "--nice "
else:
    niceString = ""
with subprocess.Popen(basePath+"../ExplicitGameSolver/gamesolver "+niceString+"/dev/stdin",shell=True,stdin=subprocess.PIPE,stdout=subprocess.PIPE, bufsize=100000000) as solverProcess:
    solverProcess.stdin.write(("\n".join([a for a in overallSpecFile])).encode())
    solverProcess.stdin.close()
    linesOut = solverProcess.stdout.readlines()
    linesErr = []
    # linesErr = solverProcess.stderr.readlines()
    if (solverProcess.wait()!=0):
        print("Game solving failed!",file=sys.stderr)
        print("".join([a.decode() for a in linesErr]),file=sys.stderr)
        sys.exit(1)
    else:
        print("Game solving succeeded!",file=sys.stderr)
        print("".join([a.decode() for a in linesOut]),file=sys.stderr)
    strategy = [a.decode().strip() for a in linesOut]


# =====================================================
# Realizable?
# =====================================================
if strategy[0]=="UNREALIZABLE":
    print("The specification is unrealizable.")
    sys.exit(0)
elif strategy[0]!="REALIZABLE":
    print("Error: Specification was neither found to be realizable nor unrealizable.\n",file=sys.stderr)
    sys.exit(1)
    

# =====================================================
# Read strategy
# ======================================================

# 1. Used actions
actionLine = strategy[1].split(" ")
assert actionLine[0]=="ACTIONS"
nofUsedInputActions = int(actionLine[1])
nofUsedOutputActions = int(actionLine[2])
assert len(actionLine)==3
usedInputActions = []
usedOutputActions = []
currentStrategyLine = 2
for (storage,number) in [(usedInputActions,nofUsedInputActions),(usedOutputActions,nofUsedOutputActions)]:
    for i in range(0,number):
        storage.append(strategy[currentStrategyLine].strip())
        currentStrategyLine+=1

# 1b. States
stateLinesHeader = strategy[currentStrategyLine].split(" ")
currentStrategyLine += 1
assert stateLinesHeader[0]=="STATES"
nofStrategyStates = stateLinesHeader[1]

# 2. Transition lines
transitionLinesHeader = strategy[currentStrategyLine].split(" ")
currentStrategyLine += 1
assert transitionLinesHeader[0]=="TRANSITIONS"
transitionLinesByInput = { i : [] for i in range(0,nofUsedInputActions+nofUsedOutputActions)}
while strategy[currentStrategyLine]!="ENDTRANSITIONS":
    lineData = [int(a) for a in strategy[currentStrategyLine].split(" ")]
    currentStrategyLine+=1
    transitionLinesByInput[lineData[2]].append(lineData)
currentStrategyLine+=1

# We assume that the initial state is always the first one

# =====================================================
# Prepare code building
# =====================================================
javaClassDeclarationCode = []
javaOnCreateCode = []


# =====================================================
# Add all "thread.terminates" to usedInputActions to
# Assure code Generation
# =====================================================
for action in inputEvents:
    if action.endswith(".terminates"):
        if not action in usedInputActions:
            usedInputActions.append(action)

# =====================================================
# Declaration code: Action / Output action effects
# =====================================================
for actionNo,lines in transitionLinesByInput.items():
    javaClassDeclarationCode.append("    void gameAction"+str(actionNo)+"() {")
    javaClassDeclarationCode.append("      logCurrentState(\"GameAction"+str(actionNo)+"\",currentSystemGoal,controllerState);")
    # javaClassDeclarationCode.append("      Log.w(\"Action\",\"GameAction"+str(actionNo)+"\");")
    
    # Output action? Then emit code.
    if actionNo >= nofUsedInputActions:
        outputActionNumber = actionNo - nofUsedInputActions
        outputAction = usedOutputActions[outputActionNumber]

        # Skip events without a "."
        if "." in outputAction:
            outputActionObject = outputAction.split(".")[0]
            outputActionEventType = outputAction.split(".")[1]

            # Emit code according to the code type
            if outputActionObject in threadList:
                # Thread?
                if outputActionEventType=="start":
                    javaClassDeclarationCode.append("      new java.lang.Thread() { public void run() {")
                    javaClassDeclarationCode.append("          "+outputActionObject+"();")
                    javaClassDeclarationCode.append("          runOnUiThread(new java.lang.Thread() { public void run() {")
                    javaClassDeclarationCode.append("             "+outputActionObject+"_onTerminate();")
                    javaClassDeclarationCode.append("          }});")
                    javaClassDeclarationCode.append("      }}.start();")

                else:
                    raise Exception("Could not identify how to emit code for thread action "+outputActionEventTypes)

            elif outputActionObject in typeOfObjectsUsedInSpecifications:
                # GUI Elements
                javaClassDeclarationCode.append("      "+OUTPUT_EVENT_TO_CODE_MAPPER[(typeOfObjectsUsedInSpecifications[outputActionObject],outputActionEventType)](outputActionObject))
            else:
                raise Exception("Could not identify how to emit code for action "+outputAction)
        elif outputAction=="done":
            javaClassDeclarationCode.append("      // Done action")
        elif outputAction in customOutputActions:
            javaClassDeclarationCode.append(" "+outputAction+"();")
        else:
            raise Exception("Unsupported.")

    javaClassDeclarationCode.append("    }")

# =====================================================
# Declaration code: Logging current state
# =====================================================
javaClassDeclarationCode.append("  void logCurrentState(String inputAction, int currentGoal, int controllerState) {")
javaClassDeclarationCode.append("      String a = inputAction+\" (\"+Integer.toString(controllerState);")
assumptionPointer = 0
javaClassDeclarationCode.append("      a = a + \") with goal \"+Integer.toString(currentGoal);")
javaClassDeclarationCode.append("      Log.w(\"Action\",a);")
javaClassDeclarationCode.append(" }")

# =====================================================
# Event handler code
# =====================================================
javaClassDeclarationCode.append("int currentSystemGoal = 0;")
javaClassDeclarationCode.append("int controllerState = 0;")


# Collect in this map the event code for multiple actions for the same event type.
inputActionEventCollector = {}
methodContinuationNumberSoFar = 0

for actionNo,inputAction in enumerate(usedInputActions):

    javaClassDeclarationCode.append("void onInputAction"+str(actionNo)+"() {")
    javaClassDeclarationCode.append("  logCurrentState(\"inputAction"+str(inputAction)+"\",currentSystemGoal,controllerState);")
    lastFnCode = "onInputAction"+str(actionNo)+"();"
    nofLinesThisCaseSoFar = 0

    for line in transitionLinesByInput[actionNo]:

        # Split up the strategy line

        startingGoalNumber = int(line[0])
        startingState = int(line[1])        
        
        nextGoal = line[-2]
        nextState = line[-1]
        actions = line[3:-2]
        
        if nofLinesThisCaseSoFar >100:
            javaClassDeclarationCode.append("  inputEventCase"+str(methodContinuationNumberSoFar)+"();")
            javaClassDeclarationCode.append("}\nvoid inputEventCase"+str(methodContinuationNumberSoFar)+"() {")
            methodContinuationNumberSoFar += 1
            nofLinesThisCaseSoFar = 0

        javaClassDeclarationCode.append("  if ((currentSystemGoal=="+str(startingGoalNumber)+") && (controllerState=="+str(startingState)+")) {")
        nofLinesThisCaseSoFar += 1
        javaClassDeclarationCode.append("Log.w(\"ActionLine\",\""+" ".join([str(a) for a in line])+"\");")
        if (nextGoal!=startingGoalNumber):
            javaClassDeclarationCode.append("currentSystemGoal = "+str(nextGoal)+";")
        if (nextState!=startingState):
            javaClassDeclarationCode.append("controllerState = "+str(nextState)+";")

        # Reduce the number of lines locally
        exeLines = []
        exeLines.append("gameAction"+str(actionNo)+"();")
        for a in actions:
            nofLinesThisCaseSoFar += 1
            exeLines.append("gameAction"+str(a+nofUsedInputActions)+"();")
        for i in range(0,(len(exeLines)+3)//4):
            block = exeLines[i*4:i*4+4]
            javaClassDeclarationCode.append(" ".join(block))    
        javaClassDeclarationCode.append("return; }")

    javaClassDeclarationCode.append(" Log.e(\"Action\",\"Failure -- Case uncovered.\");")
    javaClassDeclarationCode.append("}")

    eventCode = lastFnCode

    if "." in inputAction:
        inputActionObject = inputAction.split(".")[0]
        inputActionEventType = inputAction.split(".")[1]

        # Distinguish object types
        if inputActionObject in threadList:
            if inputActionEventType=="terminates":
                javaClassDeclarationCode.append(" void "+inputActionObject+"_onTerminate() {")
                javaClassDeclarationCode.append(eventCode)
                javaClassDeclarationCode.append(" }")
            else:
                raise Exception("Could not identify thread action")
        elif inputActionObject in typeOfObjectsUsedInSpecifications:
            if not inputActionObject in inputActionEventCollector:
                inputActionEventCollector[inputActionObject] = {a:"" for a in INPUT_EVENTS_BY_TYPE[typeOfObjectsUsedInSpecifications[inputActionObject]]}
            inputActionEventCollector[inputActionObject][inputActionEventType] = eventCode
        else:
            raise Exception("Could not identify type of input action")
    elif inputAction=="done":
        javaClassDeclarationCode.append(" void onDone() {")
        javaClassDeclarationCode.append(eventCode)
        javaClassDeclarationCode.append(" }")
    elif inputAction=="init":
        javaOnCreateCode.append(eventCode)
    elif inputAction in customInputActions:
        javaClassDeclarationCode.append(" void on_"+inputAction+"() {")
        javaClassDeclarationCode.append(eventCode)
        javaClassDeclarationCode.append(" }")
        javaClassDeclarationCode.append(" void emit_"+inputAction+"() {")
        # Old: javaClassDeclarationCode.append("      runOnUiThread(new java.lang.Thread() { public void run() {")
        javaClassDeclarationCode.append("      (new Handler(Looper.getMainLooper())).post(new java.lang.Thread() { public void run() {")
        javaClassDeclarationCode.append("         on_"+inputAction+"();")
        javaClassDeclarationCode.append("      }});")
        javaClassDeclarationCode.append(" }")
    else:
        raise Exception("Unsupported.")

# Process the cases from the mapper
for (objectName,eventCode) in inputActionEventCollector.items():
    javaOnCreateCode.append("      "+INPUT_OBJECT_TO_CODE_MAPPER[typeOfObjectsUsedInSpecifications[objectName]](objectName,eventCode))
    

# Declare additional code for (input) objects that have auto-generated code
for (objectName,eventCode) in inputActionEventCollector.items():
    if typeOfObjectsUsedInSpecifications[objectName] in INPUT_OBJECT_TO_AUTO_GENERATED_DECLARATION_CODE_MAPPER:
        javaClassDeclarationCode.append("      "+INPUT_OBJECT_TO_AUTO_GENERATED_DECLARATION_CODE_MAPPER[typeOfObjectsUsedInSpecifications[objectName]](objectName,eventCode))


javaOnCreateCode.append("Log.w(\"Action\",\"Application start\");")

# =====================================================
# Read java file
# =====================================================
with open(javaFileName,"r") as inFile:
    javaFileLines = list(inFile.read().splitlines())

# =====================================================
# Rewrite java file
# =====================================================
with open(javaFileName,"w") as outFile:
    mode = 0
    for line in javaFileLines:
        if mode==0:
            if line.strip()=="// --SYNTHESIZED-CODE-SUBCLASSES-START--":
                mode = 1
                outFile.write(line+"\n")
                outFile.write("\n".join(javaClassDeclarationCode)+"\n")
                outFile.write(line.replace("START","END")+"\n")
            elif line.strip()=="// --SYNTHESIZED-CODE-ON-CREATE-START--":
                mode = 1
                outFile.write(line+"\n")
                outFile.write("\n".join(javaOnCreateCode)+"\n")
                outFile.write(line.replace("START","END")+"\n")
            else:
                outFile.write(line+"\n")
        else:
            if line.strip()=="// --SYNTHESIZED-CODE-SUBCLASSES-END--":
                mode = 0
            elif line.strip()=="// --SYNTHESIZED-CODE-ON-CREATE-END--":
                mode = 0







# // --SYNTHESIZED-CODE-SUBCLASSES-START--
# // --SYNTHESIZED-CODE-SUBCLASSES-END--
# // --SYNTHESIZED-CODE-ON-CREATE-START--
# // --SYNTHESIZED-CODE-ON-CREATE-END--
