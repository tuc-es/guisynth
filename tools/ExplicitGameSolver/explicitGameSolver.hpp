#ifndef __EXPLICIT_GAME_SOLVER__
#define __EXPLICIT_GAME_SOLVER__

#include "gameSolvingProblem.hpp"
#include "bitvector.hpp"
#include <unordered_map>
#include <set>
#include <list>

class ExplicitGameSolver {
private:
    GameSolvingProblem &problem;

    struct RejectingStatesLeftTuple {
        // The assumption state bit vector is inverted, so that we have an antichain again.
        BitVectorDynamic leftAssumptionStates; // Renumbered so that only rejecting states are considered
        BitVectorDynamic leftGuaranteeStates; // Renumbered so that only rejecting states are considered
    };

    struct TransitionWithoutTarget : public RejectingStatesLeftTuple {
        std::vector<unsigned int> outputActions;

        // Constructors
        TransitionWithoutTarget(const RejectingStatesLeftTuple &src, std::vector<unsigned int> _outputActions) :
            RejectingStatesLeftTuple(src), outputActions(_outputActions) {}
        TransitionWithoutTarget() {}
    };

    struct Transition : public TransitionWithoutTarget {
        int target;
    };

public:
    class Position {
    public:
        BitVectorDynamic position;
        int deadEndWinningStatus; // 0: unknown, 1=winning, -1=losing
        std::vector<std::vector<Transition>> outgoingTransitionsPerEnvironmentInput;
        std::vector<int> lastOutgoingTransitionsAlreadyExplored;
        std::vector<std::pair<int,int> > otherStatesDependingOnThisOneForSafetyWinning;

        // Functions
        Position(BitVectorDynamic &init, GameSolvingProblem &problem, ExplicitGameSolver &solver);
        bool isUnexplored() { return (outgoingTransitionsPerEnvironmentInput.size()==0); }
        bool couldUseExploration() { return (outgoingTransitionsPerEnvironmentInput.size()==0) && (deadEndWinningStatus==0); }
    };

private:
    std::unordered_map<BitVectorDynamic,int> positionNumberLookup;
    std::vector<Position> positions;


    // Internal information to map between state numbers and to the how manyth rejecting state
    // the given state number is.
    // --> This is cached information to spped up game solving
    RejectingStatesLeftTuple defaultRejectingStateLeftTupleForPositionExploring;
    BitVectorDynamic defaultPositionWithoutBeingInAnyAutomatonState;
    std::vector<int> assumptionAutomatonStateToNumberOfRejectingStateMapper;
    std::vector<int> guaranteeAutomatonStateToNumberOfRejectingStateMapper;
    std::vector<int> assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper;
    std::vector<int> guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper;
    size_t bitvectorLengthRejectingAssumptionAutomatonStatesLeft;
    size_t bitvectorLengthRejectingGuaranteeAutomatonStatesLeft;

    // Information needed only during the exploration of a state
    // --> This is cached information to spped up game solving
    std::vector<int> assumptionAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper;
    std::vector<int> guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper;
    size_t bitvectorSizeCombinedStateAndRejectingStateTuples;

    // Forward state exploration speed-up data cache
    // --> This is cached information to spped up game solving
    // Bitvecttors are of length "bitvectorSizeCombinedStateAndRejectingStateTuples"
    std::vector<std::vector<BitVectorDynamicNoBitCount> > forwardAssumptionMaskPerPredActionAndStateCombination;
    std::vector<std::vector<bool> > forwardAssumptionLeftPerPredActionAndStateCombination;
    std::vector<std::vector<BitVectorDynamicNoBitCount> > forwardGuaranteeMaskPerPredActionAndStateCombination;
    std::vector<std::vector<bool> > forwardGuaranteeLeftPerPredActionAndStateCombination;
    BitVectorDynamicNoBitCount forwardAssumptionClearingMask;
    BitVectorDynamicNoBitCount forwardGuaranteeClearingMask;

    std::vector<std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t>* > forwardStepAssumptionAllData; // Array per input
    std::vector<std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t>* > forwardStepGuaranteeAllData; // Array per input

    // Other cached data
    // --> This is cached information to spped up game solving
    size_t nofAssumptionAndGuaranteeStates;
    size_t nofInputAndOutputActions;

    // Final Strategy
    std::vector<std::map<std::pair<unsigned int,unsigned int>,unsigned int> > strategy; /* State/input pair to number of transition, vector index: system goal */
    std::set<unsigned int> winningPositions;

    // Internal functions
    void explorePosition(int positionNumber);
    BitVectorDynamicNoBitCount forwardStepStateExploration(BitVectorDynamicNoBitCount &source, int nofOverallAction) const;
    /*BitVectorDynamicNoBitCount forwardStepStateExploration(BitVectorDynamic &source, int nofOverallAction) const {
        return forwardStepStateExploration(*((BitVectorDynamicNoBitCount*)(&source)), nofOverallAction);
    }*/

    bool safetyPreSolve(bool eagerExploration, std::list<int> &statesToExplore);
    void addAssumptionDominatedOutgoingTransitions(unsigned int thisState,unsigned int inputEvent, unsigned int dominatingPosition);
    void findReachableStatesInCurrentStrategy(std::set<unsigned int> &);

public:
    ExplicitGameSolver(GameSolvingProblem &problem);
    ~ExplicitGameSolver() {
        for (auto a : forwardStepAssumptionAllData) delete[] a;
        for (auto a : forwardStepGuaranteeAllData) delete[] a;
    }
    bool solve();
    bool safetyPreSolve(bool eagerExploration);
    void gameGraphToDotOutput(bool drawLeavingEdges, bool cutGraph=false);
    void dumpStrategy();
    void makeNicerStrategy();
    void showForwardSequence(std::string caseString); // For debugging
    unsigned int getNofPositions() const { return positions.size(); }
};






#endif
