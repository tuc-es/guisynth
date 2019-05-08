#ifndef __GAME_SOLVING_PROBLEM_HPP__
#define __GAME_SOLVING_PROBLEM_HPP__

#include <vector>
#include <map>
#include <string>
#include <sstream>
#include <tuple>
#include "bitvector.hpp"

class Automaton {
public:
    std::map<std::string,unsigned int> stateNumbers;
    std::vector<bool> rejectingStates;
    std::vector<bool> initialStates;

    /* First index: starting state, second index: Number of the transition, pair: target state, label */
    std::vector<std::vector<std::pair<unsigned int, BitVectorDynamic> > > transitions;
    std::vector<std::vector<std::pair<unsigned int, BitVectorDynamic> > > reverseTransitions;
    unsigned int nofStates;

public:

    inline Automaton() {
        nofStates = 0;
    }

    inline void addState(std::string stateName,bool reject, bool initial) {
        // Check if state is already there
        for (auto it : stateNumbers) {
            if (it.first==stateName) throw "Error: State name is duplicate.";
        }
        int nextStateNo = stateNumbers.size();
        stateNumbers[stateName] = nextStateNo;
        rejectingStates.push_back(reject);
        initialStates.push_back(initial);
        transitions.push_back(std::vector<std::pair<unsigned int, BitVectorDynamic> >());
        nofStates = transitions.size();
    }

    unsigned int findState(std::string stateName) {
        for (auto it : stateNumbers) {
            if (it.first==stateName) return it.second;
        }
        std::ostringstream errorMsg;
        errorMsg << "Error: State '" << stateName << "' not found.";
        throw errorMsg.str();
    }

    inline unsigned int getNofStates() const {
        return nofStates;
    }

    void computeReverseTransitions() {
        reverseTransitions.clear();
        reverseTransitions.resize(nofStates);
        for (unsigned int i=0;i<nofStates;i++) {
            for (const auto &it : transitions[i]) {
                reverseTransitions[it.first].push_back(std::pair<unsigned int, BitVectorDynamic>(i,it.second));
            }
        }
    }


};

class GameSolvingProblem {

public:
    std::vector<std::string> inputEvents;
    std::vector<std::string> outputEvents;

    Automaton assumptions;
    Automaton guarantees;


    GameSolvingProblem(std::istream &is);
    GameSolvingProblem(const char *filename);

    BitVectorDynamic getInitialStates() const;

private:
    std::pair<BitVectorDynamic,unsigned int> parseTransitionLabel(std::vector<std::string> elements, unsigned int elementPtr, unsigned int nofElementsPerTransitionLabel);
    void readProblem(std::istream &inFile);

public:
    inline int getBitvectorSizeStates() {
        int a = assumptions.getNofStates()+guarantees.getNofStates();
        return (a+BitVectorDynamic::nofBitsPerElement-1)/BitVectorDynamic::nofBitsPerElement;
    }
    inline int getBitvectorSizeOnlyAssumptionStates() {
        int a = assumptions.getNofStates();
        return (a+BitVectorDynamic::nofBitsPerElement-1)/BitVectorDynamic::nofBitsPerElement;
    }
    inline int getBitvectorSizeOnlyGuaranteeStates() {
        int a = assumptions.getNofStates();
        return (a+BitVectorDynamic::nofBitsPerElement-1)/BitVectorDynamic::nofBitsPerElement;
    }


};



#endif
