#include "explicitGameSolver.hpp"
#include <list>
#include <set>
#include <unordered_set>
#include "tools.hpp"
#include "binaryAntichain.hpp"

ExplicitGameSolver::Position::Position(BitVectorDynamic &init, GameSolvingProblem &problem, ExplicitGameSolver &solver) : position(init) {
    if (!(init.isBitSet(0))) {
        deadEndWinningStatus = 1;
    } else if (init.isBitSet(problem.assumptions.getNofStates())) {
        deadEndWinningStatus = -1;
    } else {
        bool inAssumptionRejectingState = false;
        for (int posi : solver.assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper) {
            inAssumptionRejectingState |= !(init.isBitSet(posi));
        }
        if (!inAssumptionRejectingState) {
            for (int posi : solver.guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper) {
                if (init.isBitSet(posi+problem.assumptions.getNofStates())) {
                    deadEndWinningStatus = -1;
                    return;
                }
            }
        }
        deadEndWinningStatus = 0;
    }
}


ExplicitGameSolver::ExplicitGameSolver(GameSolvingProblem &_problem) : problem(_problem) {

    // Here, we fill the internal information to map between state numbers
    // and to the how manyth rejecting state the given state number is.
    defaultRejectingStateLeftTupleForPositionExploring.leftAssumptionStates = BitVectorDynamic(problem.getBitvectorSizeOnlyAssumptionStates());
    defaultRejectingStateLeftTupleForPositionExploring.leftGuaranteeStates = BitVectorDynamic(problem.getBitvectorSizeOnlyGuaranteeStates());
    defaultPositionWithoutBeingInAnyAutomatonState = BitVectorDynamic(problem.getBitvectorSizeStates());

    nofAssumptionAndGuaranteeStates = problem.assumptions.getNofStates()+problem.guarantees.getNofStates();
    nofInputAndOutputActions = problem.inputEvents.size()+problem.outputEvents.size();

    int nofRejectingStatesSoFar = 0;
    for (unsigned int i=0;i<problem.assumptions.getNofStates();i++) {
        if (problem.assumptions.rejectingStates[i]) {
            assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper.push_back(i);
            assumptionAutomatonStateToNumberOfRejectingStateMapper.push_back(nofRejectingStatesSoFar);
            defaultRejectingStateLeftTupleForPositionExploring.leftAssumptionStates.setBit(nofRejectingStatesSoFar);
            nofRejectingStatesSoFar++;
        } else {
            assumptionAutomatonStateToNumberOfRejectingStateMapper.push_back(-1);
        }
    }

    nofRejectingStatesSoFar = 0;
    for (unsigned int i=0;i<problem.guarantees.getNofStates();i++) {
        if (problem.guarantees.rejectingStates[i]) {
            guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.push_back(i);
            guaranteeAutomatonStateToNumberOfRejectingStateMapper.push_back(nofRejectingStatesSoFar);
            defaultRejectingStateLeftTupleForPositionExploring.leftGuaranteeStates.setBit(nofRejectingStatesSoFar);
            nofRejectingStatesSoFar++;
        } else {
            guaranteeAutomatonStateToNumberOfRejectingStateMapper.push_back(-1);
        }
        defaultPositionWithoutBeingInAnyAutomatonState.setBit(i+problem.assumptions.getNofStates());
    }

    // Compute assumptionAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper;
    //     and guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper;
    int posCombined = nofAssumptionAndGuaranteeStates;
    for (unsigned int i=0;i<problem.assumptions.getNofStates();i++) {
        if (assumptionAutomatonStateToNumberOfRejectingStateMapper[i]!=-1) {
            assumptionAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper.push_back(posCombined++);
        } else {
            assumptionAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper.push_back(-1);
        }
    }
    for (unsigned int i=0;i<problem.guarantees.getNofStates();i++) {
        if (guaranteeAutomatonStateToNumberOfRejectingStateMapper[i]!=-1) {
            guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper.push_back(posCombined++);
        } else {
            guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper.push_back(-1);
        }
    }
    bitvectorSizeCombinedStateAndRejectingStateTuples = (posCombined+BitVectorDynamic::nofBitsPerElement-1)/BitVectorDynamic::nofBitsPerElement;

    bitvectorLengthRejectingAssumptionAutomatonStatesLeft = (assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size()+BitVectorDynamic::nofBitsPerElement-1)/BitVectorDynamic::nofBitsPerElement;
    bitvectorLengthRejectingGuaranteeAutomatonStatesLeft = (guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size()+BitVectorDynamic::nofBitsPerElement-1)/BitVectorDynamic::nofBitsPerElement;

    // Allocate strategy buffer
    strategy.resize(guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size());


    // Fill forward exploration buffers
    forwardAssumptionMaskPerPredActionAndStateCombination.resize(problem.assumptions.getNofStates());
    forwardAssumptionLeftPerPredActionAndStateCombination.resize(problem.assumptions.getNofStates());
    for (unsigned int i=0;i<problem.assumptions.getNofStates();i++) {
        for (unsigned int action=0;action<nofInputAndOutputActions;action++) {
            forwardAssumptionMaskPerPredActionAndStateCombination[i].push_back(BitVectorDynamicNoBitCount(bitvectorSizeCombinedStateAndRejectingStateTuples));
            BitVectorDynamicNoBitCount &thisOne = forwardAssumptionMaskPerPredActionAndStateCombination[i].back();
            thisOne.fill();
            bool left = true;

            for (auto &it : problem.assumptions.transitions[i]) {
                if (it.second.isBitSet(action)) {
                    thisOne.clearBit(it.first);
                    if (it.first==i) {
                        left = false;
                    }
                }
            }

            forwardAssumptionLeftPerPredActionAndStateCombination[i].push_back(left);
        }
    }

    forwardGuaranteeMaskPerPredActionAndStateCombination.resize(problem.guarantees.getNofStates());
    forwardGuaranteeLeftPerPredActionAndStateCombination.resize(problem.guarantees.getNofStates());
    for (unsigned int i=0;i<problem.guarantees.getNofStates();i++) {
        for (unsigned int action=0;action<nofInputAndOutputActions;action++) {
            forwardGuaranteeMaskPerPredActionAndStateCombination[i].push_back(BitVectorDynamicNoBitCount(bitvectorSizeCombinedStateAndRejectingStateTuples));
            BitVectorDynamicNoBitCount &thisOne = forwardGuaranteeMaskPerPredActionAndStateCombination[i].back();
            thisOne.clear();
            bool left = true;

            for (auto &it : problem.guarantees.transitions[i]) {
                if (it.second.isBitSet(action)) {
                    thisOne.setBit(it.first+problem.assumptions.getNofStates());
                    if (it.first==i) {
                        left = false;
                    }
                }
            }

            forwardGuaranteeLeftPerPredActionAndStateCombination[i].push_back(left);
        }
    }


    // Forward clearing functions
    forwardAssumptionClearingMask = BitVectorDynamicNoBitCount(bitvectorSizeCombinedStateAndRejectingStateTuples);
    forwardGuaranteeClearingMask = BitVectorDynamicNoBitCount(bitvectorSizeCombinedStateAndRejectingStateTuples);
    forwardGuaranteeClearingMask.fill();
    for (unsigned int i=0;i<problem.assumptions.getNofStates();i++) {
        forwardAssumptionClearingMask.setBit(i);
    }
    for (unsigned int j=0;j<problem.guarantees.getNofStates();j++) {
        forwardGuaranteeClearingMask.clearBit(j+problem.assumptions.getNofStates());
    }

    // Combined information for forward step -- Assumptions
    forwardStepAssumptionAllData.resize(nofInputAndOutputActions);
    for (unsigned int action=0;action<nofInputAndOutputActions;action++) {
        std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t> *allAssumptionStates = new std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t>[problem.assumptions.getNofStates()];
        forwardStepAssumptionAllData[action] = allAssumptionStates;
        static_assert(BitVectorDynamic::nofBitsPerElement==64,"NofBitsPerElement assumed to be 64");
        for (unsigned int i=0;i<problem.assumptions.getNofStates();i++) {
            BitVectorDynamicNoBitCount thisOne = BitVectorDynamicNoBitCount(bitvectorSizeCombinedStateAndRejectingStateTuples);
            thisOne.fill();
            bool left = true;

            for (auto &it : problem.assumptions.transitions[i]) {
                if (it.second.isBitSet(action)) {
                    thisOne.clearBit(it.first);
                    if (it.first==i) {
                        left = false;
                    }
                }
            }

            int posSetBitProgress = assumptionAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[i];
            uint64_t maskProgress;
            if (posSetBitProgress==-1) {
                maskProgress = 0;
            } else {
                maskProgress = (uint64_t)1 << (posSetBitProgress % 64);
                posSetBitProgress = posSetBitProgress / 64;
            }

            allAssumptionStates[i] = std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t>(
                (uint64_t)1 << (i % 64),
                i/64,
                left && problem.assumptions.rejectingStates[i],
                thisOne,
                posSetBitProgress,
                maskProgress);
        }
    }


    // Combined information for forward step -- Guarantees
    forwardStepGuaranteeAllData.resize(nofInputAndOutputActions);
    for (unsigned int action=0;action<nofInputAndOutputActions;action++) {
        std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t> *allGuaranteeStates = new std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t>[problem.guarantees.getNofStates()];
        forwardStepGuaranteeAllData[action] = allGuaranteeStates;
        static_assert(BitVectorDynamic::nofBitsPerElement==64,"NofBitsPerElement assumed to be 64");
        for (unsigned int i=0;i<problem.guarantees.getNofStates();i++) {
            BitVectorDynamicNoBitCount thisOne = BitVectorDynamicNoBitCount(bitvectorSizeCombinedStateAndRejectingStateTuples);
            thisOne.clear();
            bool left = true;

            for (auto &it : problem.guarantees.transitions[i]) {
                if (it.second.isBitSet(action)) {
                    thisOne.setBit(it.first+problem.assumptions.getNofStates());
                    if (it.first==i) {
                        left = false;
                    }
                }
            }

            int posSetBitProgress = guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[i];
            uint64_t maskProgress;
            if (posSetBitProgress==-1) {
                maskProgress = 0;
            } else {
                maskProgress = ~((uint64_t)1 << (posSetBitProgress % 64));
                posSetBitProgress = posSetBitProgress / 64;
            }

            allGuaranteeStates[i] = std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t>(
                (uint64_t)1 << ((i+problem.assumptions.getNofStates()) % 64),
                (i+problem.assumptions.getNofStates())/64,
                left && problem.guarantees.rejectingStates[i],
                thisOne,
                posSetBitProgress,
                maskProgress);
        }
    }

}

/**
 * @brief Main solving function -- assumes that
 * @return
 */
bool ExplicitGameSolver::solve() {


    /*
     * First things first -- We remove the transitions that are losing already
     */
    for (unsigned int i=0;i<positions.size();i++) {
        for (unsigned int nofAction=0;nofAction<positions[i].lastOutgoingTransitionsAlreadyExplored.size();nofAction++) {
            /*std::cerr << "XPLORE: " << positions[i].lastOutgoingTransitionsAlreadyExplored[nofAction] << "," << nofAction << std::endl;
            positions[i].outgoingTransitionsPerEnvironmentInput[nofAction].erase(
                positions[i].outgoingTransitionsPerEnvironmentInput[nofAction].begin(),
                positions[i].outgoingTransitionsPerEnvironmentInput[nofAction].begin()+
                    std::max(0,positions[i].lastOutgoingTransitionsAlreadyExplored[nofAction]-1));
            positions[i].lastOutgoingTransitionsAlreadyExplored[nofAction] = std::max(
                positions[i].lastOutgoingTransitionsAlreadyExplored[nofAction], 0);*/

            for(unsigned int t=0;t<positions[i].outgoingTransitionsPerEnvironmentInput[nofAction].size();t++) {
                if (positions[
                        positions[i].outgoingTransitionsPerEnvironmentInput[nofAction][t].target].deadEndWinningStatus==-1) {
                    positions[i].outgoingTransitionsPerEnvironmentInput[nofAction].erase(positions[i].outgoingTransitionsPerEnvironmentInput[nofAction].begin()+t);
                    t--;
                }
            }
        }
    }

    BitVectorDynamic initialPosition = problem.getInitialStates();

    // Idea: We try to solve the game using the positions we already have.
    // If at some point, the outer-most fixed point does not include the initial state any more,
    // we need to re-explore or the game is actually losing. We can distinguish the cases
    // by keeping track of states to be explored that could make a difference to the inclusion
    // of a position -- we do this for every position. If at some point, the initial state
    // is not contained in the outermost fixed point without one of these states being declared,
    // we can abort the computation.

    // We store the positions worthy of exploring in a bitvector.
    // When the initial state is removed from the outermost greatest fixpoint,
    // these are the states refined. These are then checked for being safety-winning

    // But first -- Win from a complete game.
    std::set<unsigned int> Z;
    unsigned int oldZSize = 0;
    for (unsigned int i=0;i<positions.size();i++) {
        // Only use the positions in Z that are not clearly losing.
        if (positions[i].deadEndWinningStatus!=-1) {
            Z.insert(i);
        }
    }

    // Nested GR(1) fixed points
    while (oldZSize!=Z.size()) {
        oldZSize = Z.size();
#ifndef NDEBUG
        std::cerr << "Z interation!\n";
#endif
        for (unsigned int systemGoal=0;systemGoal<guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();systemGoal++) {
            strategy[systemGoal].clear();
            std::set<unsigned int> Y;
#ifndef NDEBUG
            std::cerr << "Y.reset()\n";
#endif


            // Mark the dead-end winning states as such
            for (unsigned int i=0;i<positions.size();i++) {
                if (positions[i].deadEndWinningStatus==1) Y.insert(i);
            }

            unsigned int oldYSize = Z.size();
            while (Y.size()!=oldYSize) {
                oldYSize = Y.size();
                for (unsigned int environmentGoal=0;environmentGoal<assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();environmentGoal++) {
                    std::set<unsigned int> X(Z);
                    unsigned int oldXSize = 0;
                    std::map<std::pair<unsigned int,unsigned int>,unsigned int> oldStrategy = strategy[systemGoal];
                    while (X.size()!=oldXSize) {
                        strategy[systemGoal] = oldStrategy;
                        oldXSize = X.size();
                        std::set<int> toRemove;
                        for (auto it : X) {
#ifndef NDEBUG
                            std::cerr << "Inner X: " << systemGoal << " " << environmentGoal << ":" << it << std::endl;
#endif
                            // Check if for each of the states in X, there is a suitable successor
                            bool foundTrans = true;

                            if (positions[it].isUnexplored()) {
                                // Remove if not winning
                                if (positions[it].deadEndWinningStatus!=1)
                                    toRemove.insert(it);
                            } else if (Y.count(it)==0) {

                                // Only go here if not already in Y (to make strategy extraction sane)
                                for (unsigned int envAction=0;(envAction<problem.inputEvents.size()) && foundTrans;envAction++) {

                                    // Iterate through the transitions and check if there is a suitable one.
                                    foundTrans = false;
                                    unsigned int transitionNumber = 0;
                                    for (Transition &transition : positions[it].outgoingTransitionsPerEnvironmentInput[envAction]) {
                                        if (!(positions[transition.target].couldUseExploration())) {
                                            if (transition.leftGuaranteeStates.isBitSet(systemGoal) && (Z.count(transition.target)>0)) {
                                                // Case 1: Goal reached
                                                foundTrans = true;
#ifndef NDEBUG
                                                std::cerr << "Action " << envAction << " ok cause trans1 to " << transition.target << ";;" << transition.leftGuaranteeStates.data[0] << std::endl;
#endif
                                                strategy[systemGoal][std::make_pair(it,envAction)] = transitionNumber;
                                                goto done;
                                            } else if (Y.count(transition.target)>0) {
                                                // Case 2: Closer to the goal
                                                foundTrans = true;
#ifndef NDEBUG
                                                std::cerr << "Action " << envAction << " ok cause trans2 to " << transition.target << " ; " << Y.size() << std::endl;
#endif
                                                strategy[systemGoal][std::make_pair(it,envAction)] = transitionNumber;
                                                goto done;
                                            } else if ((X.count(transition.target)>0) && !transition.leftAssumptionStates.isBitSet(environmentGoal)) {
                                                // Case 3: waiting for environment goal
                                                foundTrans = true;
#ifndef NDEBUG
                                                std::cerr << "Action " << envAction << " ok cause trans3 to " << transition.target << std::endl;
#endif
                                                strategy[systemGoal][std::make_pair(it,envAction)] = transitionNumber;
                                                goto done;
                                            }
                                        }
                                        transitionNumber++;
                                    }
                                    done:
                                    /* nop needed */ (void)1;
                                }
                                if (!foundTrans) toRemove.insert(it);
                            }
                        }

                        // Delete old states
                        // Remote all from X that is in toRemove
                        {
                            std::set<unsigned int>::iterator it = X.begin();
                            while (it!=X.end()) {
                                if (toRemove.count(*it)>0) {
                                    X.erase(it++); //increment before passing to erase, because after the call it would be invalidated
                                } else {
                                    ++it;
                                }
                            }
                        }
                    }

                    // Add states to Y
                    Y.insert(X.begin(),X.end());
#ifndef NDEBUG
                    std::cerr << "Size X: " << X.size() << std::endl;
                    std::cerr << "Size Y now: " << Y.size() << std::endl;
#endif
                }
            }

            // Remote all from Z that is not in Y
            {
                std::set<unsigned int>::iterator it = Z.begin();
                while (it!=Z.end()) {
                    if (Y.count(*it)==0) {
                        Z.erase(it++); //increment before passing to erase, because after the call it would be invalidated
                    } else {
                        ++it;
                    }
                }
            }
        }
    }

#ifndef NDEBUG
    std::cerr << "Winning positions:";
    for (auto x : Z) std::cerr << " " << x;
    std::cerr << std::endl;
#endif

    winningPositions = Z;
    return Z.count(0) > 0;
}


bool ExplicitGameSolver::safetyPreSolve(bool eagerExploration) {

    // Can only be called once
    if (positions.size()!=0) throw "Runtime Error: Can only solve from a new game graph.";

    // Allocate initial state
    BitVectorDynamic initialPosition = problem.getInitialStates();
    positions.push_back(Position(initialPosition,problem,*this));
    positionNumberLookup[initialPosition] = positions.size()-1;

    std::list<int> statesToExplore;
    statesToExplore.push_back(0);
    return safetyPreSolve(eagerExploration,statesToExplore);
}

bool ExplicitGameSolver::safetyPreSolve(bool eagerExploration, std::list<int> &statesToExplore) {
    // Every state has one of two stages:
    // - "Found"
    // - "Explored"
    // The initial state has been found at this point, but not explored.
    // Explore the initial state now.

    // Idea: During state exploration, the transition relation out of a state is found. Only minimal successors
    // are found.
    //
    // Initially, we perform *safety exploration*. For every explored state and every possible input we search
    // if for one output, we find an already explored state. If that is the case, the input need not be further explored.
    // If that is not the case, the process recurses.
    //
    // After exploration, safety solving takes place. This can remove some states from consideration, making
    // other states not fully explored. The list "otherStatesDependingOnThisOne" of the now losing states is
    // used to figure out where to re-explore.

    // Build TODO list and add initial state
    std::list<std::pair<int,int> > stateInputPairsNotYetWinning;

    // Big "while something to be done" list.
    while ((statesToExplore.size()>0) || (stateInputPairsNotYetWinning.size()>0)) {

        // std::cerr << "SafetyPreSolve Exploring...\n";

        if (stateInputPairsNotYetWinning.size()>0) {

            // Ok, some state input pair is not yet winning
            std::pair<int,int> stateInputPair = stateInputPairsNotYetWinning.front();

#ifndef NDEBUG
            std::cerr << "State/Input pair: "  << stateInputPair.first << "," << stateInputPair.second << std::endl;
#endif

            stateInputPairsNotYetWinning.pop_front();
            bool becameLosing = false;

            // Already winning or losing? No need to explore then
            if (positions[stateInputPair.first].deadEndWinningStatus==0) {

                // Ok, otherwise explore
                unsigned int nextTransitionNumber = ++(positions[stateInputPair.first].lastOutgoingTransitionsAlreadyExplored[stateInputPair.second]);

                if (nextTransitionNumber>=positions[stateInputPair.first].outgoingTransitionsPerEnvironmentInput[stateInputPair.second].size()) {
                    // Ok, no transition left? Then losing!
                    becameLosing = true;
                } else {
                    int successorState = positions[stateInputPair.first].outgoingTransitionsPerEnvironmentInput[stateInputPair.second][nextTransitionNumber].target;

                    // Successor state losing?
                    if (positions[successorState].deadEndWinningStatus==-1) {
                        // ...then try again next round!
                        stateInputPairsNotYetWinning.push_back(stateInputPair);
                    } else if (positions[successorState].couldUseExploration()) {
                        // Explore and register...
                        std::cerr << "Explore and register: " << successorState << std::endl;
                        statesToExplore.push_back(successorState);
                        positions[successorState].otherStatesDependingOnThisOneForSafetyWinning.push_back(stateInputPair);
                    } else {
                        // Ok, then just register
#ifndef NDEBUG
                        std::cerr << "Just register: " << successorState << std::endl;
#endif
                        positions[successorState].otherStatesDependingOnThisOneForSafetyWinning.push_back(stateInputPair);
                    }
                }
            }

            // Ok, now losing? Then we need to report this to the state depending on this one
            if (becameLosing) {
                positions[stateInputPair.first].deadEndWinningStatus = -1;
                stateInputPairsNotYetWinning.insert(stateInputPairsNotYetWinning.end(),
                    positions[stateInputPair.first].otherStatesDependingOnThisOneForSafetyWinning.begin(),
                    positions[stateInputPair.first].otherStatesDependingOnThisOneForSafetyWinning.end());
            }

        } else {

            // Need to explore some additional state
            int positionNumber = statesToExplore.front();
            statesToExplore.pop_front();

            // Only explore if still unexplored -- it can happen that we try to
            // explore twice when the state is used multiple times as transition successor before
            // being explored.
            if (positions[positionNumber].couldUseExploration()) {

                unsigned int numberOfPositionsBefore = positions.size();
                explorePosition(positionNumber);

                // Eager exploration? Then explore new states right now...
                if (eagerExploration) {
                    while (numberOfPositionsBefore<positions.size()) {
                        explorePosition(numberOfPositionsBefore++);
                    }
                }

                // Not yet winning
                positions[positionNumber].lastOutgoingTransitionsAlreadyExplored = std::vector<int>();
                for (unsigned int i=0;i<positions[positionNumber].outgoingTransitionsPerEnvironmentInput.size();i++) {
                    positions[positionNumber].lastOutgoingTransitionsAlreadyExplored.push_back(-1);
                    stateInputPairsNotYetWinning.push_back(std::pair<int,int>(positionNumber,i));
                }
            }
        }
    }

    // Winning in the safety game?
    return positions[0].deadEndWinningStatus!=-1;
}

void ExplicitGameSolver::gameGraphToDotOutput(bool drawLeavingEdges, bool cutGraph) {
    std::cout << "digraph {\n";

    std::set<unsigned int> reachable;
    if (cutGraph) {
        findReachableStatesInCurrentStrategy(reachable);
    } else {
        for (unsigned int i=0;i<positions.size();i++) reachable.insert(i);
    }

    // Allocate positions
    for (unsigned int positionNumber=0;positionNumber<positions.size();positionNumber++) {
        if (reachable.count(positionNumber)>0) {
            std::cout << "p" << positionNumber << "[ label=\"";
            bool first=true;
            for (unsigned int i=0;i<problem.assumptions.getNofStates();i++) {
                if (!(positions[positionNumber].position.isBitSet(i))) {
                    if (first) {
                        first=false;
                    } else {
                        std::cout << ",";
                    }
                    std::cout << "a" << i;
                }
            }
            for (unsigned int i=0;i<problem.guarantees.getNofStates();i++) {
                if (positions[positionNumber].position.isBitSet(i+problem.assumptions.getNofStates())) {
                    if (first) {
                        first=false;
                    } else {
                        std::cout << ",";
                    }
                    std::cout << "g" << i;
                }
            }

            // Unexplored?
            if (positions[positionNumber].isUnexplored()) std::cout << "/U";

            // Winning?
            if (positions[positionNumber].deadEndWinningStatus==1) std::cout << "/W";
            if (positions[positionNumber].deadEndWinningStatus==-1) std::cout << "/L";

            std::cout << "\"];\n";
        }
    }

    // Transitions
    for (unsigned int positionNumber=0;positionNumber<positions.size();positionNumber++) {
        if (reachable.count(positionNumber)>0) {
            for (unsigned int envEvent=0;envEvent<problem.inputEvents.size();envEvent++) {
                if (positions[positionNumber].outgoingTransitionsPerEnvironmentInput.size()>envEvent) {
                    unsigned int currentTransitionNumber = 0;
                    for (auto transition : positions[positionNumber].outgoingTransitionsPerEnvironmentInput[envEvent]) {
                        if (reachable.count(transition.target)>0) {
                            if (!cutGraph || positions[positionNumber].deadEndWinningStatus==0) {
                                std::cout << "p" << positionNumber << "-> p" << transition.target;

                                // Label
                                std::cout << "[label=\"" << problem.inputEvents[envEvent] << "/";
                                bool first = true;
                                for (auto it : transition.outputActions) {
                                    if (first) {
                                        first = false;
                                    } else {
                                        std::cout << ",";
                                    }
                                    std::cout << problem.outputEvents[it];
                                }

                                // Leaving?
                                if (drawLeavingEdges) {
                                    for (unsigned int i=0;i<assumptionAutomatonStateToNumberOfRejectingStateMapper.size();i++) {
                                        if (transition.leftAssumptionStates.isBitSet(i)) {
                                            std::cout << ";";
                                            std::cout << "a" << assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i];
                                        }
                                    }
                                    for (unsigned int i=0;i<guaranteeAutomatonStateToNumberOfRejectingStateMapper.size();i++) {
                                        if (transition.leftGuaranteeStates.isBitSet(i)) {
                                            std::cout << ";";
                                            std::cout << "g" << guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i];
                                        }
                                    }
                                }

                                std::cout << "\"";

                                if (positions[positionNumber].deadEndWinningStatus==0) {
                                    if (positions[positionNumber].lastOutgoingTransitionsAlreadyExplored.size()>envEvent) {
                                        unsigned int transitionNo = positions[positionNumber].lastOutgoingTransitionsAlreadyExplored[envEvent];
                                        if (transitionNo==currentTransitionNumber) {
                                            std::cout << ",color=red";
                                        }
                                    }
                                }

                                // Strategy draw
                                bool blue = false;
                                std::ostringstream labels;
                                for (unsigned int g=0;g<guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();g++) {
                                    assert(strategy.size()>g);
                                    auto it = strategy[g].find(std::pair<unsigned int,unsigned int>(positionNumber,envEvent));
                                    if ((it!=strategy[g].end()) && (it->second==currentTransitionNumber)) {
                                        if (!blue) {
                                            std::cout << ",penwidth=3";
                                            labels << "G" << g;
                                        } else {
                                            labels << ",G" << g;
                                        }
                                        blue = true;
                                    }
                                }
                                if (blue) {
                                    std::cout << ",taillabel=\"" << labels.str() << "\"";
                                }

                                std::cout << "];\n";
                                currentTransitionNumber++;
                            }
                        }
                    }
                }
            }
        }
    }

    // End
    std::cout << "}\n";


}


#ifndef NO_ANTICHAINS

//================================================
// Regular version with improvements
//================================================
/**
 * @brief Explores one particular state - this means to compute the possible output sequences for
 * each input and to "find" the respective successor states
 * @param stateNumber the number of the state to explore.
 */
void ExplicitGameSolver::explorePosition(int positionNumber) {

#ifndef NDEBUG
    std::cerr << "ExplorePosition: " << positionNumber << std::endl;
#endif

    for (unsigned int input=0;input<problem.inputEvents.size();input++) {
        positions[positionNumber].outgoingTransitionsPerEnvironmentInput.push_back(std::vector<Transition>());

        // Construct initial combined bitvector that contains the starting state
        // and the information that so far, no rejecting state has been left.
        BitVectorDynamic initialCombination(bitvectorSizeCombinedStateAndRejectingStateTuples);
        initialCombination.inplaceOrLargerBitvectorAgainstSmallerBitvector(positions[positionNumber].position);
        // Nothing left - for guarantee states that is bad
        for (auto it : guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper) {
            if (it!=-1) initialCombination.setBit(it);
        }

        // First, compute intermediate combination after the input only
        BitVectorDynamic succCombination = forwardStepStateExploration(initialCombination,input);

#ifndef NDEBUG
        std::cerr << "SuccCombination for input " << input << ": " << *(succCombination.data) << std::endl;
#endif

        // Now compute which outputs are allowed.
        BinaryAntichain<true> chainBestSuccessorsLeftCombinations;
        BinaryAntichain<true> chainBestSuccessorsLeftCombinationsAfterDone;
        std::unordered_map<BitVectorDynamic,std::vector<unsigned int> > potentialTransitions;
        std::unordered_map<BitVectorDynamic,std::vector<unsigned int> > potentialTransitionsAfterDone;
        chainBestSuccessorsLeftCombinations.addWhenBitvectorIsKnownToBeIncomparableToAllExistingElementsInTheAntichain(succCombination);
        potentialTransitions[succCombination] = std::vector<unsigned int>();

        // Saturate the outputs -- BFS style to prefer short action sequences!
        std::list<BitVectorDynamic> todo;
        todo.push_back(succCombination);
        while (todo.size()!=0) {
            BitVectorDynamic thisOne = todo.front();
            todo.pop_front();

            // Other than done
            for (unsigned int i=1;i<problem.outputEvents.size();i++) {
                BitVectorDynamic next = forwardStepStateExploration(thisOne,i+problem.inputEvents.size());
                if (chainBestSuccessorsLeftCombinations.add(next)) {
                    potentialTransitions[next] = potentialTransitions[thisOne];
                    auto &ref = potentialTransitions[next];
                    ref.push_back(i);
                    todo.push_back(next);
                }
            }

            // Done
            BitVectorDynamic next = forwardStepStateExploration(thisOne,0+problem.inputEvents.size());
            if (chainBestSuccessorsLeftCombinationsAfterDone.add(next)) {
                potentialTransitionsAfterDone[next] = potentialTransitions[thisOne];
                auto &ref = potentialTransitionsAfterDone[next];
                ref.push_back(0);
            }
        }

        // Ok, we have all the successors now. Let's build the states
        BinaryAntichainBase::iterator it(chainBestSuccessorsLeftCombinationsAfterDone);
        while (it.next()) {
            const BitVectorDynamic &thisSucc = it.element();
            BitVectorDynamic onlyState = thisSucc.computeShorterCopy(nofAssumptionAndGuaranteeStates);

            // State exists?
            auto finder = positionNumberLookup.find(onlyState);
            int targetPositionNumber;
            if (finder==positionNumberLookup.end()) {
                // New state!
                positions.push_back(Position(onlyState,problem,*this));
                positionNumberLookup[onlyState] = positions.size()-1;
                targetPositionNumber = positions.size()-1;
            } else {
                // Old state!
                targetPositionNumber = finder->second;
            }


            // Add transition
            auto &transitionDump = positions[positionNumber].outgoingTransitionsPerEnvironmentInput.back();

            transitionDump.push_back(Transition());
            auto &thisTransition = transitionDump.back();
            thisTransition.target = targetPositionNumber;
#ifndef NDEBUG
            std::cerr << "TPN:" << targetPositionNumber << std::endl;
#endif
            thisTransition.outputActions = potentialTransitionsAfterDone[thisSucc];
            thisTransition.leftAssumptionStates = BitVectorDynamic(bitvectorLengthRejectingAssumptionAutomatonStatesLeft);
            thisTransition.leftGuaranteeStates = BitVectorDynamic(bitvectorLengthRejectingGuaranteeAutomatonStatesLeft);

            // Assumption leaving?
            for (unsigned int i=0;i<assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();i++) {
                if (thisSucc.isBitSet(assumptionAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]])) {
                    // Not Leaving with the state
                    thisTransition.leftAssumptionStates.setBit(i);
                } else if (positions[positionNumber].position.isBitSet(assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i])) {
                    // Not in the state before
                    thisTransition.leftAssumptionStates.setBit(i);
                } else if (thisSucc.isBitSet(assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i])) {
                    // Not in the state afterwars
                    thisTransition.leftAssumptionStates.setBit(i);
                }
            }

            // Guarantee leaving?
            for (unsigned int i=0;i<guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();i++) {
                if (!(thisSucc.isBitSet(guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]]))) {
                    // Not Leaving with the state
                    thisTransition.leftGuaranteeStates.setBit(i);
                } else if (!(positions[positionNumber].position.isBitSet(guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]+problem.assumptions.getNofStates()))) {
                    // Not in the state before
                    thisTransition.leftGuaranteeStates.setBit(i);
                } else if (!(thisSucc.isBitSet(guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]+problem.assumptions.getNofStates()))) {
                    // Not in the state afterwars
                    thisTransition.leftGuaranteeStates.setBit(i);
                }
            }

        }
    }

}

#else


//================================================
// Version without Antichains
//================================================
/**
 * @brief Explores one particular state - this means to compute the possible output sequences for
 * each input and to "find" the respective successor states
 * @param stateNumber the number of the state to explore.
 */
void ExplicitGameSolver::explorePosition(int positionNumber) {

#ifndef NDEBUG
    std::cerr << "ExplorePosition: " << positionNumber << std::endl;
#endif

    for (unsigned int input=0;input<problem.inputEvents.size();input++) {
        positions[positionNumber].outgoingTransitionsPerEnvironmentInput.push_back(std::vector<Transition>());

        // Construct initial combined bitvector that contains the starting state
        // and the information that so far, no rejecting state has been left.
        BitVectorDynamic initialCombination(bitvectorSizeCombinedStateAndRejectingStateTuples);
        initialCombination.inplaceOrLargerBitvectorAgainstSmallerBitvector(positions[positionNumber].position);
        // Nothing left - for guarantee states that is bad
        for (auto it : guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper) {
            if (it!=-1) initialCombination.setBit(it);
        }

        // First, compute intermediate combination after the input only
        BitVectorDynamic succCombination = forwardStepStateExploration(initialCombination,input);

#ifndef NDEBUG
        std::cerr << "SuccCombination for input " << input << ": " << *(succCombination.data) << std::endl;
#endif

        // Now compute which outputs are allowed.
        std::unordered_set<BitVectorDynamic> chainBestSuccessorsLeftCombinations;
        std::unordered_set<BitVectorDynamic> chainBestSuccessorsLeftCombinationsAfterDone;
        std::unordered_map<BitVectorDynamic,std::vector<unsigned int> > potentialTransitions;
        std::unordered_map<BitVectorDynamic,std::vector<unsigned int> > potentialTransitionsAfterDone;
        chainBestSuccessorsLeftCombinations.insert(succCombination);
        potentialTransitions[succCombination] = std::vector<unsigned int>();

        // Saturate the outputs -- BFS style to prefer short action sequences!
        std::list<BitVectorDynamic> todo;
        todo.push_back(succCombination);
        while (todo.size()!=0) {
            BitVectorDynamic thisOne = todo.front();
            todo.pop_front();

            // Other than done
            for (unsigned int i=1;i<problem.outputEvents.size();i++) {
                BitVectorDynamic next = forwardStepStateExploration(thisOne,i+problem.inputEvents.size());
                if (chainBestSuccessorsLeftCombinations.count(next)==0) {
                    chainBestSuccessorsLeftCombinations.insert(next);
                    potentialTransitions[next] = potentialTransitions[thisOne];
                    auto &ref = potentialTransitions[next];
                    ref.push_back(i);
                    todo.push_back(next);
                }
            }

            // Done
            BitVectorDynamic next = forwardStepStateExploration(thisOne,0+problem.inputEvents.size());
            if (chainBestSuccessorsLeftCombinationsAfterDone.count(next)==0) {
                chainBestSuccessorsLeftCombinationsAfterDone.insert(next);
                potentialTransitionsAfterDone[next] = potentialTransitions[thisOne];
                auto &ref = potentialTransitionsAfterDone[next];
                ref.push_back(0);
            }
        }

        // Ok, we have all the successors now. Let's build the states
        for (const BitVectorDynamic &thisSucc : chainBestSuccessorsLeftCombinationsAfterDone) {
            BitVectorDynamic onlyState = thisSucc.computeShorterCopy(nofAssumptionAndGuaranteeStates);

            // State exists?
            auto finder = positionNumberLookup.find(onlyState);
            int targetPositionNumber;
            if (finder==positionNumberLookup.end()) {
                // New state!
                positions.push_back(Position(onlyState,problem,*this));
                positionNumberLookup[onlyState] = positions.size()-1;
                targetPositionNumber = positions.size()-1;
            } else {
                // Old state!
                targetPositionNumber = finder->second;
            }


            // Add transition
            auto &transitionDump = positions[positionNumber].outgoingTransitionsPerEnvironmentInput.back();

            transitionDump.push_back(Transition());
            auto &thisTransition = transitionDump.back();
            thisTransition.target = targetPositionNumber;
#ifndef NDEBUG
            std::cerr << "TPN:" << targetPositionNumber << std::endl;
#endif
            thisTransition.outputActions = potentialTransitionsAfterDone[thisSucc];
            thisTransition.leftAssumptionStates = BitVectorDynamic(bitvectorLengthRejectingAssumptionAutomatonStatesLeft);
            thisTransition.leftGuaranteeStates = BitVectorDynamic(bitvectorLengthRejectingGuaranteeAutomatonStatesLeft);

            // Assumption leaving?
            for (unsigned int i=0;i<assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();i++) {
                if (thisSucc.isBitSet(assumptionAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]])) {
                    // Not Leaving with the state
                    thisTransition.leftAssumptionStates.setBit(i);
                } else if (positions[positionNumber].position.isBitSet(assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i])) {
                    // Not in the state before
                    thisTransition.leftAssumptionStates.setBit(i);
                } else if (thisSucc.isBitSet(assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i])) {
                    // Not in the state afterwars
                    thisTransition.leftAssumptionStates.setBit(i);
                }
            }

            // Guarantee leaving?
            for (unsigned int i=0;i<guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();i++) {
                if (!(thisSucc.isBitSet(guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]]))) {
                    // Not Leaving with the state
                    thisTransition.leftGuaranteeStates.setBit(i);
                } else if (!(positions[positionNumber].position.isBitSet(guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]+problem.assumptions.getNofStates()))) {
                    // Not in the state before
                    thisTransition.leftGuaranteeStates.setBit(i);
                } else if (!(thisSucc.isBitSet(guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]+problem.assumptions.getNofStates()))) {
                    // Not in the state afterwars
                    thisTransition.leftGuaranteeStates.setBit(i);
                }
            }

        }
    }

}




#endif // End Anti-chains/non-antichains version

/**
 * @brief Computes the combination of successor state and rejecting state left tuple
 *        from a given source tuple and chosen action. The rejecting state information
 *        is assumed to be located right after the state information in the bitvectors,
 *        and we always take the disjunction between the left tuples for the actions.
 *        This allows us to aggregate the information for enumerate the best possible transitions
 *        (for the system player) into a single antichain when exploring states
 *        (i.e., computing the successor states).
 *
 * @param source combination of successor state and rejecting state left tuple
 * @param nofOverallAction the action to be executed
 * @return
 */
BitVectorDynamicNoBitCount ExplicitGameSolver::forwardStepStateExploration(BitVectorDynamicNoBitCount &sourceStateAndRejectingStates, int nofOverallAction) const {

    // Build default source/target tuple
    assert(sourceStateAndRejectingStates.lng!=0);
    BitVectorDynamicNoBitCount target = sourceStateAndRejectingStates;
    // Reset reachable states
    target |= forwardAssumptionClearingMask;
    target &= forwardGuaranteeClearingMask;

    /*for (unsigned int i=0;i<problem.assumptions.getNofStates();i++) {
        target.setBit(i);
    }
    for (unsigned int j=0;j<problem.guarantees.getNofStates();j++) {
        target.clearBit(j+problem.assumptions.getNofStates());
    }*/

#ifndef NDEBUG
    std::cerr << "SRC: " << std::hex << *(sourceStateAndRejectingStates.data) << ", act: " << std::dec << nofOverallAction << std::endl;
#endif

    // Assumptions
    std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t> *currentAssumptionStates = forwardStepAssumptionAllData[nofOverallAction];
    std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t> *endAssumptionStates = forwardStepAssumptionAllData[nofOverallAction] + problem.assumptions.getNofStates();

    while (currentAssumptionStates!=endAssumptionStates) {

        std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t> &current = *currentAssumptionStates;

        if (!(sourceStateAndRejectingStates.data[std::get<1>(current)] & std::get<0>(current))) {
            target &= std::get<3>(current);
            if (std::get<2>(current)) {
                target.data[std::get<4>(current)] |= std::get<5>(current);
                assert(std::get<4>(current)!=-1);
            }
        } else {
            if (std::get<4>(current)!=-1) {
                target.data[std::get<4>(current)] |= std::get<5>(current);
            }
        }
        currentAssumptionStates++;
    }

    // Guarantees


    std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t> *currentGuaranteeStates = forwardStepGuaranteeAllData[nofOverallAction];
    std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t> *endGuaranteeStates = forwardStepGuaranteeAllData[nofOverallAction] + problem.guarantees.getNofStates();
    while (currentGuaranteeStates!=endGuaranteeStates) {

        std::tuple<uint64_t,int,bool,BitVectorDynamicNoBitCount,int,uint64_t> &current = *currentGuaranteeStates;

        if (sourceStateAndRejectingStates.data[std::get<1>(current)] & std::get<0>(current)) {
            target |= std::get<3>(current);
            if (std::get<2>(current)) {
                target.data[std::get<4>(current)] &= std::get<5>(current);
                assert(std::get<4>(current)!=-1);
            }
        } else {
            if (std::get<4>(current)!=-1) {
                target.data[std::get<4>(current)] &= std::get<5>(current);
            }
        }
        currentGuaranteeStates++;
    }

    // Guarantees
    /*
    for (unsigned int i=0;i<problem.guarantees.getNofStates();i++) {
        bool left;

        if (sourceStateAndRejectingStates.isBitSet(i+problem.assumptions.getNofStates())) {
            // target |= forwardGuaranteeMaskPerPredActionAndStateCombination[i][nofOverallAction];
            left = forwardGuaranteeLeftPerPredActionAndStateCombination[i][nofOverallAction];
        } else {
            left = true;
        }

        if (left && problem.guarantees.rejectingStates[i]) {
            assert(guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[i]!=-1);
#ifndef NDEBUG
            std::cerr << "MAPG: " <<guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[i] << std::endl;
#endif
            // target.clearBit(guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[i]);
        }
    }*/

    // Old guarantees
    /*for (unsigned int i=0;i<problem.guarantees.getNofStates();i++) {
        bool left = true;
        for (auto &it : problem.guarantees.transitions[i]) {
            if (it.second.isBitSet(nofOverallAction)) {
                if (sourceStateAndRejectingStates.isBitSet(i+problem.assumptions.getNofStates())) {
                    target.setBit(it.first+problem.assumptions.getNofStates());
                    if (it.first==i) {
                        left = false;
                    }
                }
            }
        }
        if (left && problem.guarantees.rejectingStates[i]) {
            assert(guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[i]!=-1);
#ifndef NDEBUG
            std::cerr << "MAPG: " <<guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[i] << std::endl;
#endif
            target.clearBit(guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[i]);
        }
    }*/


#ifndef NDEBUG
    std::cerr << "DEST: " << std::hex << *(target.data) << std::dec << std::endl;
#endif
    return target;
}

/**
 * @brief This function enumerates alternative transitions for input Event "inputEvent" from
 * position "thisState" of the game. The alternative transitions should be the "best ones" for which the successor
 * position is dominated by dominatingPosition as far as the assumptions are concerned.
 *
 * This function is used to make the extracted strategies "nicer" - it finds alternative transitions
 * that, if the oroginal transition is expendable, will be used instead.
 */
void ExplicitGameSolver::addAssumptionDominatedOutgoingTransitions(unsigned int thisState, unsigned int inputEvent, unsigned int dominatingPosition) {


    // Construct initial combined bitvector that contains the starting state
    // and the information that so far, no rejecting state has been left.
    BitVectorDynamic initialCombination(bitvectorSizeCombinedStateAndRejectingStateTuples);
    initialCombination.inplaceOrLargerBitvectorAgainstSmallerBitvector(positions[thisState].position);
    // Nothing left - for guarantee states that is bad
    for (auto it : guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper) {
        if (it!=-1) initialCombination.setBit(it);
    }

    // First, compute intermediate combination after the input only
    BitVectorDynamic succCombination = forwardStepStateExploration(initialCombination,inputEvent);

    // std::cerr << "SuccDOMINATEDCombination for input " << inputEvent << ": " << *(succCombination.data) << std::endl;

    // Now compute which outputs are allowed.
    std::unordered_set<BitVectorDynamic> setBestSuccessorsLeftCombinations;
    BinaryAntichain<true> chainBestSuccessorsLeftCombinationsAfterDone;
    std::unordered_map<BitVectorDynamic,std::vector<unsigned int> > potentialTransitions;
    std::unordered_map<BitVectorDynamic,std::vector<unsigned int> > potentialTransitionsAfterDone;
    setBestSuccessorsLeftCombinations.insert(succCombination);
    potentialTransitions[succCombination] = std::vector<unsigned int>();

    // Saturate the outputs -- BFS style to prefer short action sequences!
    std::list<BitVectorDynamic> todo;
    todo.push_back(succCombination);
    while (todo.size()!=0) {
        BitVectorDynamic thisOne = todo.front();
        todo.pop_front();

        // Other than done
        for (unsigned int i=1;i<problem.outputEvents.size();i++) {
            BitVectorDynamic next = forwardStepStateExploration(thisOne,i+problem.inputEvents.size());
            if (setBestSuccessorsLeftCombinations.count(next)==0) {
                setBestSuccessorsLeftCombinations.insert(next);
                potentialTransitions[next] = potentialTransitions[thisOne];
                auto &ref = potentialTransitions[next];
                ref.push_back(i);
                todo.push_back(next);
            }
        }

        // Done
        BitVectorDynamic next = forwardStepStateExploration(thisOne,0+problem.inputEvents.size());

        // Dominated by the "dominatingPosition"?
        bool dominated = false;
        bool leq = true;
        for (unsigned int i=0;i<problem.assumptions.getNofStates();i++) {
            if (positions[dominatingPosition].position.isBitSet(i)) {
                if (next.isBitSet(i)) {
                    // Both the same.
                } else {
                    // Ok, this is not a good candidate.
                    leq = false;
                }
            } else {
                if (next.isBitSet(i)) {
                    // The next one is not in an assumption automaton state in which this one is.
                    dominated = true;
                } else {
                    // Both the same
                }
            }
        }

        if (dominated && leq) {
            if (chainBestSuccessorsLeftCombinationsAfterDone.add(next)) {
                potentialTransitionsAfterDone[next] = potentialTransitions[thisOne];
                auto &ref = potentialTransitionsAfterDone[next];
                ref.push_back(0);
            }
        }
    }

    // Ok, we have all the successors now. Let's build the states
    BinaryAntichainBase::iterator it(chainBestSuccessorsLeftCombinationsAfterDone);
    while (it.next()) {
        const BitVectorDynamic &thisSucc = it.element();
        BitVectorDynamic onlyState = thisSucc.computeShorterCopy(nofAssumptionAndGuaranteeStates);

        // State exists?
        auto finder = positionNumberLookup.find(onlyState);
        int targetPositionNumber;
        if (finder==positionNumberLookup.end()) {
            // New state!
            positions.push_back(Position(onlyState,problem,*this));
            positionNumberLookup[onlyState] = positions.size()-1;
            targetPositionNumber = positions.size()-1;
        } else {
            // Old state!
            targetPositionNumber = finder->second;
        }


        // Add transition
        auto &transitionDump = positions[thisState].outgoingTransitionsPerEnvironmentInput[inputEvent];

        transitionDump.push_back(Transition());
        auto &thisTransition = transitionDump.back();
        thisTransition.target = targetPositionNumber;
        //std::cerr << "TPN:" << targetPositionNumber << std::endl;
        thisTransition.outputActions = potentialTransitionsAfterDone[thisSucc];
        thisTransition.leftAssumptionStates = BitVectorDynamic(bitvectorLengthRejectingAssumptionAutomatonStatesLeft);
        thisTransition.leftGuaranteeStates = BitVectorDynamic(bitvectorLengthRejectingGuaranteeAutomatonStatesLeft);

        // Assumption leaving?
        for (unsigned int i=0;i<assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();i++) {
            if (thisSucc.isBitSet(assumptionAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]])) {
                // Not Leaving with the state
                thisTransition.leftAssumptionStates.setBit(i);
            } else if (positions[thisState].position.isBitSet(assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i])) {
                // Not in the state before
                thisTransition.leftAssumptionStates.setBit(i);
            } else if (thisSucc.isBitSet(assumptionAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i])) {
                // Not in the state afterwars
                thisTransition.leftAssumptionStates.setBit(i);
            }
        }

        // Guarantee leaving?
        for (unsigned int i=0;i<guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();i++) {
            if (!(thisSucc.isBitSet(guaranteeAutomatonStateToCombinedStateAndLeftInformationBitvectorPositionMapper[guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]]))) {
                // Not Leaving with the state
                thisTransition.leftGuaranteeStates.setBit(i);
            } else if (!(positions[thisState].position.isBitSet(guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]+problem.assumptions.getNofStates()))) {
                // Not in the state before
                thisTransition.leftGuaranteeStates.setBit(i);
            } else if (!(thisSucc.isBitSet(guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper[i]+problem.assumptions.getNofStates()))) {
                // Not in the state afterwars
                thisTransition.leftGuaranteeStates.setBit(i);
            }
        }

    }
}


void ExplicitGameSolver::findReachableStatesInCurrentStrategy(std::set<unsigned int> &foundStorageSet) {

    // Find reachable states
    std::list<unsigned int> todo;
    todo.push_back(0);
    foundStorageSet.insert(0);
    while (todo.size()!=0) {
        unsigned int thisOne = *todo.begin();
        // std::cerr << "NICEPROCIT2X" << thisOne << "," << problem.inputEvents.size() << "," << guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size() << "\n";
        todo.pop_front();

        // No follow if dead end
        if (positions[thisOne].deadEndWinningStatus!=1) {
            for (unsigned int inputEvent=0;inputEvent<problem.inputEvents.size();inputEvent++) {
                for (unsigned int goal=0;goal<guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();goal++) {
                    std::pair<unsigned int, unsigned int> search(thisOne,inputEvent);
                    auto it = strategy[goal].find(search);
                    if (it!=strategy[goal].end()) {
                        unsigned int nofTrans = it->second;
                        assert(thisOne<positions.size());
                        assert(positions[thisOne].outgoingTransitionsPerEnvironmentInput.size()>inputEvent);
                        assert(nofTrans<positions[thisOne].outgoingTransitionsPerEnvironmentInput[inputEvent].size());
                        unsigned int targetState = positions[thisOne].outgoingTransitionsPerEnvironmentInput[inputEvent][nofTrans].target;
                        if (foundStorageSet.count(targetState)==0) {
                            todo.push_back(targetState);
                            foundStorageSet.insert(targetState);
                        }
                    }
                }
            }
        }
    }

}


/**
 * @brief By default, the strategies computed here are not very "nice" --
 * they start threads even when this is not necessary if the resulting successor state
 * looks better. This is to be avoided.
 */
void ExplicitGameSolver::makeNicerStrategy() {

    // Go through the states and try to make the strategy "nicer". Do it in reachability-first style
    std::list<unsigned int> processedStates;

    while (true) {

        //std::cerr << "NICEPROCIT\n";
        std::set<unsigned int> found;
        findReachableStatesInCurrentStrategy(found);

        for (auto it : processedStates) {
            found.erase(it);
        }

        if (found.size()==0) return; // All processed, strategy is complete

        // Process the first state.
        unsigned int thisState = *(found.begin());
        processedStates.push_back(thisState);

        // std::cerr << "NICEPROC: " << thisState << std::endl;

        // If this one is plain winning, remove transitions to make the strategy shorter
        if (positions[thisState].deadEndWinningStatus==1) {
            positions[thisState].outgoingTransitionsPerEnvironmentInput.clear();
        } else {


            // Go through the events and check if there is a strictly nicer variant.
            for (unsigned int inputEvent=0;inputEvent<problem.inputEvents.size();inputEvent++) {

                unsigned int posStartingTransitions = 0;

                while (posStartingTransitions < positions[thisState].outgoingTransitionsPerEnvironmentInput[inputEvent].size()) {

                    std::set<unsigned int> startingTransitionLocations;
                    std::vector<Transition> startingTransitions;
                    for (unsigned int goal=0;goal<guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();goal++) {
                        auto currentStrategyChoice = strategy[goal][std::pair<unsigned int,unsigned int>(thisState,inputEvent)];
                        if (startingTransitionLocations.count(currentStrategyChoice)==0) {
                            startingTransitions.push_back(positions[thisState].outgoingTransitionsPerEnvironmentInput[inputEvent][currentStrategyChoice]);
                            startingTransitionLocations.insert(currentStrategyChoice);
                            assert(currentStrategyChoice<positions[thisState].outgoingTransitionsPerEnvironmentInput[inputEvent].size());
                        }
                    }
                    // std::cerr << "NICESTARTINGTRANSITIONS " << inputEvent << ":";
                    // for (auto it : startingTransitions) std::cerr << " " << it.target;
                    // std::cerr << std::endl;

                    // Step 1: To keep the safety winning states correct,
                    // we first add the new states, do a safety winning/exploration step.
                    unsigned int oldNofStates = positions.size();
                    addAssumptionDominatedOutgoingTransitions(thisState,inputEvent,startingTransitions[posStartingTransitions].target);
                    // gameGraphToDotOutput(true);
                    std::list<int> statesToExplore;
                    for (unsigned int i=oldNofStates;i<positions.size();i++) statesToExplore.push_back(i);
                    safetyPreSolve(true,statesToExplore);

                    // Now we replace the transitions and then solve the game

                    // Replace the first transition by strictly nicer ones.
                    positions[thisState].outgoingTransitionsPerEnvironmentInput[inputEvent].clear();

                    // Add the "before" transitions back
                    for (unsigned int i=0;i<posStartingTransitions;i++) {
                        positions[thisState].outgoingTransitionsPerEnvironmentInput[inputEvent].push_back(startingTransitions[i]);
                    }
                    addAssumptionDominatedOutgoingTransitions(thisState,inputEvent,startingTransitions[posStartingTransitions].target);
                    for (unsigned int i=posStartingTransitions+1;i<startingTransitions.size();i++) {
                        positions[thisState].outgoingTransitionsPerEnvironmentInput[inputEvent].push_back(startingTransitions[i]);
                    }

                    // Do game solving.
                    bool winning = solve();
                    //throw 123;

                    if (!winning || (winningPositions.count(thisState)==0)) {
                        positions[thisState].outgoingTransitionsPerEnvironmentInput[inputEvent] = startingTransitions;
                        posStartingTransitions++;
                        // std::cerr << "NICEFAILED" << thisState << "," << inputEvent << "," << posStartingTransitions << "\n";

                        //gameGraphToDotOutput(true);
                        // We need to resolve, as in the next round, the current strategy will be read again.
                        bool winning = solve();
                        //gameGraphToDotOutput(true);
                        if (!winning) throw "Internal solving error.\n";

                    } else {
                        // Cool! We can keep it this way and try again.
                        // Dominated transition has already been removed.
                        // std::cerr << "NICESUCEED\n";

                    }
                }
            }

        }
    }
}



void ExplicitGameSolver::dumpStrategy() {

    // Header: Actions
    std::cout << "ACTIONS " << problem.inputEvents.size() << " " << problem.outputEvents.size() << "\n";
    for (auto it : problem.inputEvents) std::cout << it << "\n";
    for (auto it : problem.outputEvents) std::cout << it << "\n";

    // Header: States
    std::cout << "STATES " << positions.size() << "\n";

    std::set<unsigned int> reachableStates;
    findReachableStatesInCurrentStrategy(reachableStates);

    // Transitions
    std::cout << "TRANSITIONS\n";
    for (unsigned int goal=0;goal<guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();goal++) {
        // std::cout << "M" << strategy[goal].size() << std::endl;
        for (unsigned int pos : reachableStates) {
            if (positions[pos].deadEndWinningStatus==0) {
                for (unsigned int event=0;event<problem.inputEvents.size();event++) {
                    std::pair<unsigned int, unsigned int> search(pos,event);
                    // std::cout << "C:" << search.first << search.second << std::endl;
                    if (strategy[goal].find(search)!=strategy[goal].end()) {
                        unsigned int trans = strategy[goal][search];
                        std::cout << goal << " " << pos << " " << event;
                        for (unsigned int i : positions[pos].outgoingTransitionsPerEnvironmentInput[event][trans].outputActions)
                            std::cout << " " << i;
                        if (positions[pos].outgoingTransitionsPerEnvironmentInput[event][trans].leftGuaranteeStates.isBitSet(goal)) {
                            std::cout << " " << (goal+1) % guaranteeAutomatonNumberOfRejectingStateToOverallStateNumberMapper.size();
                        } else {
                            std::cout << " " << goal;
                        }
                        std::cout << " " << positions[pos].outgoingTransitionsPerEnvironmentInput[event][trans].target << std::endl;
                    }
                }
            }
        }
    }
    std::cout << "ENDTRANSITIONS\n";

    // Dump done!

}

void ExplicitGameSolver::showForwardSequence(std::string caseString) {

    BitVectorDynamicNoBitCount state(bitvectorSizeCombinedStateAndRejectingStateTuples);
    state |= forwardAssumptionClearingMask;
    state &= forwardGuaranteeClearingMask;

    std::vector<std::string> parts = splitAndStrip(caseString,',');

    // Parse initial state
    std::string initialStatePos(parts[0]+"\n");
    std::string rest = "";
    char type = ' ';
    for (unsigned int pos=0;pos<initialStatePos.size();pos++) {
        if ((initialStatePos[pos]=='a') || (initialStatePos[pos]=='g') || (initialStatePos[pos]=='\n')) {
            if (rest!="") {
                std::istringstream is(rest);
                int nr;
                is >> nr;
                if (is.fail()) throw "Illegal initial state.";
                if (type=='a') state.clearBit(nr);
                else if (type=='g') state.setBit(nr+problem.assumptions.getNofStates());
                else throw 123;
            }
            type = initialStatePos[pos];
            rest = "";
        } else {
            rest = rest + initialStatePos[pos];
        }
    }

    // Build sequence
    std::vector<int> decisions;
    for (unsigned int i=1;i<parts.size();i++) {
        std::istringstream is(parts[i]);
        int dec;
        is >> dec;
        if (is.fail()) throw "Illegal action";
        if (dec<0) throw "Decision<0";
        if (dec>=(int)(problem.inputEvents.size()+problem.outputEvents.size())) throw "Action number too large";
        decisions.push_back(dec);
    }
    decisions.push_back(-1);

    std::cout << "Trace:\n";

    for (unsigned int j=0;j<decisions.size();j++) {
        std::cout << "State ";
        for (unsigned int i=0;i<problem.assumptions.getNofStates();i++) {
            if (!(state.isBitSet(i))) {
                std::cout << "a" << i;
            }
        }
        for (unsigned int i=0;i<guaranteeAutomatonStateToNumberOfRejectingStateMapper.size();i++) {
            if (state.isBitSet(i+problem.assumptions.getNofStates())) {
                std::cout << "g" << i;
            }
        }
        std::cout << "\n";
        int dec = decisions[j];
        if (dec>=0) {
            std::cout << " -> ";
            if (dec<(int)(problem.inputEvents.size())) std::cout << problem.inputEvents[dec];
            else std::cout << problem.outputEvents[dec-problem.inputEvents.size()];
            state = forwardStepStateExploration(state,dec);
            std::cout << "\n";
        }
    }


}
