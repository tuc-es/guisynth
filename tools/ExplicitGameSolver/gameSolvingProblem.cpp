#include "gameSolvingProblem.hpp"
#include <fstream>
#include <sstream>
#include <set>
#include "tools.hpp"


GameSolvingProblem::GameSolvingProblem(const char *filename) {
    std::ifstream inStream(filename);
    readProblem(inStream);
}

GameSolvingProblem::GameSolvingProblem(std::istream &inFile) {
    readProblem(inFile);
}


void GameSolvingProblem::readProblem(std::istream &inFile) {

    if (inFile.fail()) throw "Error opening input file";

    std::string idLine;
    std::getline(inFile,idLine);
    if (idLine!="UVWBasedGame") throw "Did not find correct File identifier line 'UVWBasedGame' at the beginning of the file.";

    std::string dataLine;
    bool readAutomatonPart = false;
    while (std::getline(inFile,dataLine)) {
        std::vector<std::string> parts = splitAndStrip(dataLine);
        if (parts.size()>0) {
            if (parts[0].substr(0,1)=="#") {
                // Comment line
            } else if (parts[0]=="Input") {
                if (readAutomatonPart) throw "Error: Input and Output Signals must be defined before all automaton states.";
                if (parts.size()<2) throw "Error: Need an event name after 'Input'";
                std::string signalName = parts[1];
                inputEvents.push_back(signalName);
                if (parts.size()>2) throw "Error: Stray information after an input event declaration.";
            } else if (parts[0]=="Output") {
                if (readAutomatonPart) throw "Error: Input and Output Signals must be defined before all automaton states.";
                if (parts.size()<2) throw "Error: Need an event name after 'Output'";
                std::string signalName = parts[1];
                outputEvents.push_back(signalName);
                if (parts.size()>2) throw "Error: Stray information after an output event declaration.";
            } else if (parts[0]=="State") {
                if (parts.size()<3) throw "Error: State definitions need at least 3 words";
                Automaton *targetAutomaton = NULL;
                if (parts[1]=="Assumptions") {
                    targetAutomaton = &assumptions;
                } else if (parts[1]=="Guarantees") {
                    targetAutomaton = &guarantees;
                } else {
                    throw "Error: Expected 'Assumptions' or 'Guarantees' as parameter after 'State'";
                }
                std::string stateName = parts[2];
                bool reject = false;
                bool initial = false;
                for (unsigned int i=3;i<parts.size();i++) {
                    std::string param = parts[i];
                    if (param=="reject") {
                        reject = true;
                    } else if (param=="initial") {
                        initial = true;
                    } else {
                        throw "Error: Expected 'reject' or 'initial' as state parameter.";
                    }
                }
                targetAutomaton->addState(stateName,reject,initial);
            } else if (parts[0]=="Transition") {
                if (parts.size()<3) throw "Error: State definitions need at least 3 words";
                Automaton *targetAutomaton = NULL;
                if (parts[1]=="Assumptions") {
                    targetAutomaton = &assumptions;
                } else if (parts[1]=="Guarantees") {
                    targetAutomaton = &guarantees;
                } else {
                    throw "Error: Expected 'Assumptions' or 'Guarantees' as parameter after 'State'";
                }
                std::string startingStateName = parts[2];
                unsigned int startingStateNumber = targetAutomaton->findState(startingStateName);
                // Reading condition
                unsigned int nofInputAndOutputEvents = inputEvents.size()+outputEvents.size();
                unsigned int nofElementsPerTransitionLabel = (nofInputAndOutputEvents + BitVectorDynamic::nofBitsPerElement - 1) / BitVectorDynamic::nofBitsPerElement;
                std::pair<BitVectorDynamic,unsigned int> transitionLabelAndReadingPointer = parseTransitionLabel(parts,3,nofElementsPerTransitionLabel);
                if (transitionLabelAndReadingPointer.second!=parts.size()-1) throw "Error reading a transition: There are stray elements";
                unsigned int destinationStateNumber = targetAutomaton->findState(parts[transitionLabelAndReadingPointer.second]);
                targetAutomaton->transitions[startingStateNumber].push_back(std::pair<unsigned int,BitVectorDynamic>(destinationStateNumber,transitionLabelAndReadingPointer.first));

            } else {
                std::cerr << "Error: Did not understand the line '" << dataLine << "'.\n";
                throw "Input file parsing error.";
            }
        }

    }
    if (inFile.bad()) throw "Error reading from file.";

    // Check that the first output is "done" -- needed for the semantics
    if (inputEvents.size()==0) throw "Expected at least one input event.";
    if (outputEvents.size()==0) throw "Expected a 'done' input event.";
    if (outputEvents[0]!="done") throw "The first output event must be the 'done' event.";

    // Check that event names are only used once.
    {
        std::set<std::string> eventNames;
        eventNames.insert(inputEvents.begin(),inputEvents.end());
        eventNames.insert(outputEvents.begin(),outputEvents.end());
        if (eventNames.size()!=inputEvents.size()+outputEvents.size()) throw "Error: Some event name was declared twice";
    }

    // Add rejeting assumption state if there is none. Likewise, do the same for the guarantees
    {
        bool foundA = false;
        bool foundG = false;
        for (auto it : assumptions.rejectingStates) foundA |= it;
        for (auto it : guarantees.rejectingStates) foundG |= it;
        if (!foundA) {
            assumptions.addState("__automaticallyAddedRejectingState",true,false);
        }
        if (!foundG) {
            guarantees.addState("__automaticallyAddedRejectingState",true,false);
        }
    }


    // Merge transitions with the same predecessor and target states
    for (Automaton *a : {&assumptions,&guarantees}) {
        for (unsigned int i=0;i<a->getNofStates();i++) {
            std::map<unsigned int,BitVectorDynamic> ts;
            for (auto &it : a->transitions[i]) {
                if (ts.count(it.first)>0) {
                    ts[it.first] |= it.second;
                } else {
                    ts[it.first] = it.second;
                }
            }
            a->transitions[i].clear();
            for (auto &it : ts) {
                a->transitions[i].push_back(std::pair<unsigned int, BitVectorDynamic>(it.first,it.second));
            }
        }
    }

    // Check that the first state of every automaton is a self-looping rejecting state
    // (that rejects everything) -- We use this for safety-pre solving.
    // This also means that safety pre-solving will be incomplete if
    // the first state of each automaton is not the only
    // state rejecting everything
    for (Automaton *a : {&assumptions,&guarantees}) {
        if (!(a->rejectingStates[0])) {
            throw "Error: The first state of each automaton needs to be rejecting";
        }
        if (a->transitions[0].size()!=1) {
            throw "Error: Expecting a single self-loop for the first states of each automaton.";
        }
        if (a->transitions[0][0].first!=0) {
            throw "Error: Expecting a self-loop for the first states of each automaton.";
        }
        for (unsigned int i=0;i<inputEvents.size()+outputEvents.size();i++) {
            if (!(a->transitions[0][0].second.isBitSet(i)))
                throw "Error: The self-loop on the first state of one of the automata is not for all actions!";
        }
    }


    // Trigger the computation of the inverse transitions
    assumptions.computeReverseTransitions();
    guarantees.computeReverseTransitions();
}


std::pair<BitVectorDynamic,unsigned int> GameSolvingProblem::parseTransitionLabel(std::vector<std::string> elements, unsigned int elementPtr, unsigned int nofElementsPerTransitionLabel) {

    if (elementPtr==elements.size()) throw "Error reading transition label! End of line found.";
    std::string nextOp = elements[elementPtr++];

    if (nextOp=="TRUE") {
        BitVectorDynamic d(nofElementsPerTransitionLabel);
        d.invert();
        return std::pair<BitVectorDynamic,unsigned int>(d,elementPtr);
    } else if (nextOp=="FALSE") {
        BitVectorDynamic d(nofElementsPerTransitionLabel);
        return std::pair<BitVectorDynamic,unsigned int>(d,elementPtr);
    } else if (nextOp=="!") {
        std::pair<BitVectorDynamic,unsigned int> next = parseTransitionLabel(elements,elementPtr,nofElementsPerTransitionLabel);
        next.first.invert();
        return next;
    } else if (nextOp=="&") {
        std::pair<BitVectorDynamic,unsigned int> next = parseTransitionLabel(elements,elementPtr,nofElementsPerTransitionLabel);
        std::pair<BitVectorDynamic,unsigned int> next2 = parseTransitionLabel(elements,next.second,nofElementsPerTransitionLabel);
        next2.first &= next.first;
        return next2;
    }


    else {

        // Search for the variable in the input bits
        for (unsigned int i=0;i<inputEvents.size();i++) {
            if (inputEvents[i]==nextOp) {
                BitVectorDynamic d(nofElementsPerTransitionLabel);
                d.setBit(i);
                return std::pair<BitVectorDynamic,unsigned int>(d,elementPtr);
            }
        }

        // Search for the variable in the output bits
        for (unsigned int i=0;i<outputEvents.size();i++) {
            if (outputEvents[i]==nextOp) {
                BitVectorDynamic d(nofElementsPerTransitionLabel);
                d.setBit(i+inputEvents.size());
                return std::pair<BitVectorDynamic,unsigned int>(d,elementPtr);
            }
        }

        std::ostringstream emsg;
        emsg << "Error: Could not identify transition label operator '" << nextOp << "'";
        throw emsg.str();
    }

}




BitVectorDynamic GameSolvingProblem::getInitialStates() const {
    unsigned int nofElementsPerTransitionLabel = (inputEvents.size()+outputEvents.size() + BitVectorDynamic::nofBitsPerElement - 1) / BitVectorDynamic::nofBitsPerElement;

    BitVectorDynamic d(nofElementsPerTransitionLabel);
    for (unsigned int i=0;i<assumptions.initialStates.size();i++) {
        if (!(assumptions.initialStates.at(i))) d.setBit(i);
    }

    for (unsigned int i=0;i<guarantees.initialStates.size();i++) {
        if (guarantees.initialStates.at(i)) d.setBit(i+assumptions.getNofStates());
    }
    return d;

}
