#!/usr/bin/env python3
#
# The functions to build a UVW from an LTL formula (for elements in our
# grammar)
#
# TODO:
# -> Rename "parser.py"
# -> Unify spaces/tabs
# -> Clarity which functions generate UVWs without FALSE-transitions and
#    without states without self-loops and either incoming or outgoing edges
# -> Unify the indexing of the computed simulation relation and the computed
#    reachability implication - the former are indexed by the position in the
#    reserve topological ordering, the latter by the state number
# -> TODO for Keerthi: This grammar can be extended! E.g., (phi U (a & F c)) should
#    be no problem. Also the Meidl-Special case of (phi & local) U (phi & !local)
#    for a sub-formula without temporal operators "local" should be supported.
import sys
import string
import re
import dd
import typing
import copy
from functools import reduce
from dd.autoref import BDD
from parser import Node, NodeTypes
import parser

class UVW:
    def __init__(self,ddMgr = None):
        """Initializes the UVW. There is always a fail state with no. 0"""
        self.stateNames = ["reject"] # Init with reject stat
        self.rejecting = [True]
        if ddMgr is None:
            self.ddMgr = BDD()
        else:
            self.ddMgr = ddMgr
        self.transitions = [[(0,self.ddMgr.true)]]
        self.initialStates = []
        self.propositions = []
        self.labelToStateAndActivatingMapper = {}

    def inGameSolverFormat(self, singleAction = False):

        resultLines = []

        if singleAction:
            allowedActions = self.ddMgr.true

            # At most one variable is true
            for varName in self.ddMgr.vars:
                for varNameOther in self.ddMgr.vars:
                    if varNameOther!=varName:
                        allowedActions = allowedActions & ( ~(self.ddMgr.var(varNameOther)) |  ~(self.ddMgr.var(varName)))

            # One of them is True
            thisOne = self.ddMgr.false
            for varName in self.ddMgr.vars:
                thisOne = thisOne | self.ddMgr.var(varName)

            # allowedActions = allowedActions & thisOne   <--- There could be actions not in the spec

        #Define STATES
        for i,a in enumerate(self.stateNames):
            flags = []
            if i in self.initialStates:
                flags.append("initial")
            if self.rejecting[i]:
                flags.append("reject")
            flags = " ".join(flags)
            if len(flags)>0:
                flags = " "+flags
            resultLines.append("State **TYPE** "+"q"+str(i)+flags)


        # Define transitions
        for i,a in enumerate(self.stateNames):
            for (j,b) in self.transitions[i]:

                while b!=self.ddMgr.false:
                    # Generate minterm for transition
                    rest = b
                    conditionParts = []
                    if singleAction:
                        if b==allowedActions:
                            conditionParts = ["TRUE"]
                            rest = self.ddMgr.true
                        else:
                            for p in self.propositions:
                                if ~(self.ddMgr.var(p)) & b == ~(self.ddMgr.var(p)) & allowedActions:
                                    conditionParts = ["! "+p]
                                    rest = self.ddMgr.true
                            if conditionParts==[]:
                                for p in self.propositions:
                                    if not (self.ddMgr.var(p) & b == self.ddMgr.false):
                                        conditionParts = [p]
                                        rest = self.ddMgr.var(p)
                            if conditionParts==[]:
                                # All other remaining case - Is there any?
                                print("C3",file=sys.stderr)
                                for p in self.propositions:
                                    if self.ddMgr.forall([p],(rest & self.ddMgr.var(p)))!=rest:
                                        if (rest & self.ddMgr.var(p))==self.ddMgr.false:
                                            conditionParts.append("! "+p)
                                            rest = rest & ~(self.ddMgr.var(p))
                                        else:
                                            conditionParts.append(p)
                                            rest = rest & (self.ddMgr.var(p))
                    else:
                        for p in self.propositions:
                            if self.ddMgr.forall([p],(rest & self.ddMgr.var(p)))!=rest:
                                if (rest & self.ddMgr.var(p))==self.ddMgr.false:
                                    conditionParts.append("! "+p)
                                    rest = rest & ~(self.ddMgr.var(p))
                                else:
                                    conditionParts.append(p)
                                    rest = rest & (self.ddMgr.var(p))
                    b = b & ~rest
                    if len(conditionParts)>0:
                        # We know that there can only be one event at a time -- Remove negated ones if possible
                        label = "& "*(len(conditionParts)-1)+" ".join(conditionParts)
                        resultLines.append("Transition **TYPE** q"+str(i)+" "+label+" q"+str(j))
                    else:
                        resultLines.append("Transition **TYPE** q"+str(i)+" TRUE q"+str(j))
        return "\n".join(resultLines)




    def toNeverClaim(self):
        # Never claim header
        resultLines = ["never { /* Subformulas covered by this Never Claim:"]
        for i in self.initialStates:
            if len(self.stateNames[i])>100:
                resultLines.append("  - "+self.stateNames[i][0:100]+"...")
            else:
                resultLines.append("  - "+self.stateNames[i])
        resultLines.append(" */")

        # Assign state names
        neverClaimStateNames = ["T"+str(i) for i in range(0,len(self.transitions))]
        assert self.rejecting[0]
        neverClaimStateNames[0] = "all"
        for i in self.initialStates:
            neverClaimStateNames[i] = neverClaimStateNames[i]+"_init"
        for i in range(0,len(self.transitions)):
            if self.rejecting[i]:
                neverClaimStateNames[i] = "accept_"+neverClaimStateNames[i]

        # Other states
        for i in range(1,len(self.transitions)):
            resultLines.append(neverClaimStateNames[i]+":")
            resultLines.append("  // "+str(self.stateNames[i]))
            resultLines.append("  if")
            for (a,b) in self.transitions[i]:
                while b!=self.ddMgr.false:
                    # Generate minterm for transition
                    rest = b
                    conditionParts = []
                    for p in self.propositions:
                        if self.ddMgr.exist([p],(rest & self.ddMgr.var(p)))!=rest:
                            if (rest & self.ddMgr.var(p))==self.ddMgr.false:
                                conditionParts.append("! "+p)
                                rest = rest & ~(self.ddMgr.var(p))
                            else:
                                conditionParts.append(p)
                                rest = rest & (self.ddMgr.var(p))
                    b = b & ~rest
                    if len(conditionParts)>0:
                        resultLines.append("  :: ("+" && ".join(conditionParts)+") -> goto "+neverClaimStateNames[a])
                    else:
                        resultLines.append("  :: (1) -> goto "+neverClaimStateNames[a])
            resultLines.append("  fi")

        # First state is special case
        resultLines.append(neverClaimStateNames[0]+":\n  skip")

        resultLines.append("}")
        return "\n".join(resultLines)

    @staticmethod
    def isBisimulationEquivalent(uvw1Pre,uvw2):
        # Make a copy as we are going to modify it - but the BDD manager must be the same
        uvw1 = UVW(uvw1Pre.ddMgr)
        uvw1.stateNames = copy.copy(uvw1Pre.stateNames)
        uvw1.rejecting = copy.copy(uvw1Pre.rejecting)
        uvw1.transitions = copy.copy(uvw1Pre.transitions)
        uvw1.initialStates = copy.copy(uvw1Pre.initialStates)
        uvw1.propositions = None # Not needed in the following - this is a temporary copy

        # Merge the new states in / the initial states stay unmerged
        oldNofStates = len(uvw1.rejecting)
        uvw1.rejecting = uvw1.rejecting + uvw2.rejecting
        uvw1.stateNames = uvw1.stateNames + uvw2.stateNames
        for i in range(0,len(uvw2.transitions)):
            uvw1.transitions.append([(a+oldNofStates,b) for (a,b) in uvw2.transitions[i]])

        # Get simulation relation
        (bottomUpOrder,reverseBottomUpOrder) = uvw1.getBottomUpAndReverseBottomUpOrder()
        backwardSimulation = uvw1.computeSimulationRelation(bottomUpOrder,reverseBottomUpOrder)

        # Check now that for each initial state in A there is one simulating one in B
        otherInitialStates = [a+oldNofStates for a in uvw2.initialStates]
        for (reference,duplicates) in [(uvw1.initialStates,otherInitialStates),(otherInitialStates,uvw1.initialStates)]:
            for a in reference:
                found = False
                for b in duplicates:
                    if backwardSimulation[reverseBottomUpOrder[a]][reverseBottomUpOrder[b]]:
                        found = True
                if not found:
                    return False

        # Found no counter-example ---> equivalent
        return True


    @staticmethod
    def parseFromUVWDescription(ddMgr,description):
        """Parses a UVW from a textual description consisting of the transitions of the UVW, where
           state names from which a transition originate can be labeled by whether they are rejecting and initial."""
        uvw = UVW(ddMgr)
        transitions = description.split(",")
        if transitions==[""]: # Special case: Nothing to parse ---> No transition
            transitions = []
        for transition in transitions:
            transition = transition.strip()
            (fromState,rest) = tuple(transition.split("-["))
            (condition,targetState) = tuple(rest.split("]->"))
            fromStateAttributes=""
            if "(" in fromState:
                (fromState,fromStateAttributes) = tuple(fromState.split("("))
            fromStateNo = int(fromState)
            toStateNo = int(targetState)

            # Make new state
            while len(uvw.rejecting)<=max(fromStateNo,toStateNo):
                newStateNr = len(uvw.rejecting)
                uvw.stateNames.append(str(newStateNr))
                uvw.rejecting.append(False)
                uvw.transitions.append([])

            # Add from state attributes
            for a in fromStateAttributes:
                if a==")" or a==",":
                    pass
                elif a=="i":
                    if not fromStateNo in uvw.initialStates:
                        uvw.initialStates.append(fromStateNo)
                elif a=="r":
                    uvw.rejecting[fromStateNo] = True
                else:
                    raise Exception("Unknown state attribute:"+str(a))

            # Parse transition
            uvw.transitions[fromStateNo].append((toStateNo,uvw.ddMgr.add_expr(condition)))
        return uvw


    def __str__(self):
        assert len(self.rejecting) == len(self.stateNames)
        assert len(self.transitions) == len(self.stateNames)
        result = "UVW with " + str(len(self.rejecting))+" states and initial states "+str(self.initialStates)+":\n"
        for i in range(0,len(self.rejecting)):
            result = result + " - State No. "+str(i)+" with name "+self.stateNames[i]
            if self.rejecting[i]:
                result = result + " (rej.)"
            result = result + ":\n"
            for a in self.transitions[i]:
                result = result + "   - t.t.s. "+str(a[0])+" for "+a[1].to_expr()+"\n"
        return result

    def __del__(self):
        # First delete the transitions, as only then, all BDD nodes are freed.
        del self.transitions
        self.ddMgr = None

    def addStateButNotNewListOfTransitionsForTheNewState(self,stateName,rejecting=False):
        self.stateNames.append(stateName)
        self.rejecting.append(rejecting)
        return len(self.stateNames)-1

    def makeTransientStatesNonRejecting(self):
        for i in range(0,len(self.stateNames)):
            if self.rejecting[i]:
                foundLoop = False
                for (a,b) in self.transitions[i]:
                    if a==i:
                        foundLoop = True
                if not foundLoop:
                    self.rejecting[i] = False

    def restrictToTheCaseThatThereCanOnlyBeOneActionAtATime(self):
        # Build BDD for the allowed character combinations
        allowedActions = self.ddMgr.true

        # At most one variable is true
        for varName in self.ddMgr.vars:
            for varNameOther in self.ddMgr.vars:
                if varNameOther!=varName:
                    allowedActions = allowedActions & ( ~(self.ddMgr.var(varNameOther)) |  ~(self.ddMgr.var(varName)))

        # One of them is True
        thisOne = self.ddMgr.false
        for varName in self.ddMgr.vars:
            thisOne = thisOne | self.ddMgr.var(varName)

        # allowedActions = allowedActions & thisOne <---- There could be actions not mentioned in the spec

        # Clean up the transitions
        oldTransitions = self.transitions
        for fromStateNo in range(0,len(oldTransitions)):
            t = []
            for (toStateNo,expr) in oldTransitions[fromStateNo]:
                expr = expr & allowedActions
                if expr != self.ddMgr.false:
                    t.append((toStateNo,expr))
            uvw.transitions[fromStateNo] = t


    def removeUnreachableStates(self):
        # Obtain list of reachable states
        # Assumes that there are no transitions labeled by FALSE
        reachable = [False for i in self.rejecting]
        reachable[0] = True
        todo = copy.copy(self.initialStates)
        for a in self.initialStates:
            reachable[a] = True
        while len(todo)>0:
            thisOne = todo[0]
            todo = todo[1:]
            for (a,b) in self.transitions[thisOne]:
                assert b!=self.ddMgr.false
                if not reachable[a]:
                    reachable[a] = True
                    todo.append(a)

        # Get renumeration list
        stateMapper = []
        stateMapperSoFar = 0
        for i in range(0,len(reachable)):
            if reachable[i]:
                stateMapper.append(stateMapperSoFar)
                stateMapperSoFar += 1
            else:
                stateMapper.append(None)

        # Move state numbers
        self.labelToStateAndActivatingMapper = {} # Purge as this modfies the automaton

        newStateNames = [self.stateNames[i] for i in range(0,len(self.stateNames)) if reachable[i]]
        self.stateNames = newStateNames

        # 2. Rejecting
        newRejecting = [self.rejecting[i] for i in range(0,len(self.rejecting)) if reachable[i]]
        self.rejecting = newRejecting

        # 3. Rejecting
        newTransitions = []
        for i in range(0,len(self.transitions)):
            if reachable[i]:
                newTransitions.append([])
                for (a,b) in self.transitions[i]:
                    newTransitions[-1].append((stateMapper[a],b))
        self.transitions = newTransitions

        # 4. Initial states
        self.initialStates = [stateMapper[a] for a in self.initialStates]


    def getBottomUpAndReverseBottomUpOrder(self):
        # 1. Compute a bottom-up ordering of all states
        bottomUpOrder = []
        while len(bottomUpOrder)!=len(self.stateNames):
            for i in range(0,len(self.stateNames)):
                allDone = reduce(lambda x,y: x and y, [a in bottomUpOrder or a==i for (a,b) in self.transitions[i]])
                if not i in bottomUpOrder and allDone:
                    bottomUpOrder.append(i)

        # 1b. Reverse bottom up order
        reverseBottomUpOrder = copy.copy(bottomUpOrder)
        for i in range(0,len(bottomUpOrder)):
            reverseBottomUpOrder[bottomUpOrder[i]] = i

        return (bottomUpOrder,reverseBottomUpOrder)


    def computeSimulationRelation(self,bottomUpOrder,reverseBottomUpOrder):
        # 2. Compute simulation relation
        simulationRelation = []
        for orderPosA in range(0,len(bottomUpOrder)):
            simulationForA = []
            simulationRelation.append(simulationForA)
            stateA = bottomUpOrder[orderPosA]
            for orderPosB in range(0,len(bottomUpOrder)):
                stateB = bottomUpOrder[orderPosB]

                # Check whether state A accepts at least as much as state B does
                # This means that for every action in automaton A, there must be one in B to a state that is at least as restrictive.
                # Double-Self-loops are fine if we do not have that state A is rejecting but state B is not
                simIsFine = True
                for (dest,destCond) in self.transitions[stateA]:
                    # Try to discharge all elements of destCond
                    restCond = destCond
                    for (destB,destCondB) in self.transitions[stateB]:
                        if dest==stateA and destB==stateB:
                            if (not self.rejecting[dest]) or self.rejecting[destB]:
                                restCond = restCond & ~(destCond & destCondB)
                        else:
                            posA = reverseBottomUpOrder[dest]
                            posB = reverseBottomUpOrder[destB]
                            if simulationRelation[posA][posB]:
                                restCond = restCond & ~(destCond & destCondB)
                    simIsFine = simIsFine and (restCond == self.ddMgr.false)

                simulationForA.append(simIsFine)
        return simulationRelation


    def findReachabilityImplyingStates(self,bottomUpOrder: typing.List[int]) -> typing.List[typing.List[bool]]:
        """Computes a list a such that a[i][j] is True whenever being in state i implies also being in state j."""
        reachabilityImplications = [[False for i in range(0,len(bottomUpOrder))] for j in range(0,len(bottomUpOrder))]

        # Compute inverse transitions
        inverseTransitions = [[] for i in bottomUpOrder]
        for i in range(0,len(self.transitions)):
            for (a,b) in self.transitions[i]:
                inverseTransitions[a].append((i,b))

        # Compute reachability implying states
        for aIndex in range(len(bottomUpOrder)-1,-1,-1):
            for bIndex in range(len(bottomUpOrder)-1,-1,-1):
                aState = bottomUpOrder[aIndex]
                bState = bottomUpOrder[bIndex]

                # Check if for every incoming transition to state "a", there is
                # a corresponding on the state "b"
                foundUnimplyingCase = False

                # Check initial
                if (aState in self.initialStates) and not (bState in self.initialStates):
                    foundUnimplyingCase = True

                # Check the rest
                for (a,b) in inverseTransitions[aState]:
                    rest = b
                    for (c,d) in inverseTransitions[bState]:

                        # Self-loops must be contained
                        if (a==aState) and (c==bState):
                            rest = rest & ~d
                        elif reachabilityImplications[a][c]:
                            rest = rest & ~d
                    if rest!=self.ddMgr.false:
                        foundUnimplyingCase = True

                # Store results
                reachabilityImplications[aState][bState] = not foundUnimplyingCase

        return reachabilityImplications

    def computeTransitiveClosureOfTransitionRelation(self):
        result = set([])

        for a in range(0,len(self.transitions)):
            result.add((a,a))
        for i,a in enumerate(self.transitions):
            for (b,c) in a:
                result.add((i,b))

        lastResult = set([])
        while len(result)!=len(lastResult):
            lastResult = result
            result = set([])
            for (a,b) in lastResult:
                result.add((a,b))
                for (c,d) in lastResult:
                    if c==b:
                        result.add((a,d))
        return result

    def mergeEquivalentlyReachableStates(self):

        # 1. Compute a bottom-up ordering of all states
        (bottomUpOrder,reverseBottomUpOrder) = self.getBottomUpAndReverseBottomUpOrder()

        # 2. Compute simulation relation
        forwardSimulation = self.findReachabilityImplyingStates(bottomUpOrder)

        # 2b. Compute transitive closure of transition relation
        transitiveClosureOfTransitionRelation = self.computeTransitiveClosureOfTransitionRelation()

        # 3. Print forward simulation
        # for i in range(0,len(self.transitions)):
        #    for j in range(0,len(self.transitions)):
        #        if forwardSimulation[i][j]:
        #            print("REachImply: "+str(bottomUpOrder[i])+","+str(bottomUpOrder[j]))
        #print("Bottom Up Order:",bottomUpOrder)
        #print("Closure:",transitiveClosureOfTransitionRelation)

        # 4. Forward bisimulation merge State Mapper Computation

        stateMapper = {}
        for j in range(len(bottomUpOrder)-1,-1,-1):
            for i in range(0,j):
                if forwardSimulation[bottomUpOrder[i]][bottomUpOrder[j]] and forwardSimulation[bottomUpOrder[j]][bottomUpOrder[i]]:
                    if not bottomUpOrder[i] in stateMapper:
                        if not (bottomUpOrder[j],bottomUpOrder[i]) in transitiveClosureOfTransitionRelation:
                            stateMapper[bottomUpOrder[i]] = bottomUpOrder[j]

        # print("StateMapper: ",stateMapper)
        # print("This means: ",[(bottomUpOrder[a],bottomUpOrder[b]) for (a,b) in stateMapper.items()])

        # 5. Redirect
        for i in range(0,len(bottomUpOrder)):
            if i in stateMapper:
                self.stateNames[stateMapper[i]] = "& "+ self.stateNames[stateMapper[i]] + " " + self.stateNames[i]
                for (a,b) in self.transitions[i]:
                    self.transitions[stateMapper[i]].append((a,b))
                self.transitions[i] = []


        # 6. Clean up
        self.removeStatesWithoutOutgoingTransitions()
        self.mergeTransitionsBetweenTheSameStates()
        self.removeUnreachableStates()

    def removeForwardReachableBackwardSimulatingStates(self):

        # 1. Compute a bottom-up ordering of all states
        (bottomUpOrder,reverseBottomUpOrder) = self.getBottomUpAndReverseBottomUpOrder()

        # 2. Compute simulation relation --> Indices are over the state numbers!
        forwardSimulation = self.findReachabilityImplyingStates(bottomUpOrder)

        # 2. Compute backward simulation relation --> Indices are over the order in the bottom up order
        backwardSimulation = self.computeSimulationRelation(bottomUpOrder,reverseBottomUpOrder)

        # 3. Find out which state is reachable from which other states
        reachabilityRelation = []
        for i in range(0,len(bottomUpOrder)):
            reachable = set([i])
            todo = set([i])
            while len(todo)>0:
                thisOne = todo.pop()
                for (a,b) in self.transitions[thisOne]:
                    if not a in reachable:
                        assert b!=self.ddMgr.false
                        reachable.add(a)
                        todo.add(a)
            thisList = []
            for a in range(0,len(bottomUpOrder)):
                thisList.append(a in reachable)
            reachabilityRelation.append(thisList)

        # Print reachability relation
        # print("Reachability Relation:")
        # for a in range(0,len(bottomUpOrder)):
        #     for b in range(0,len(bottomUpOrder)):
        #         if reachabilityRelation[a][b]:
        #             print ("Reach:",a,b)

        # 3. Print forward simulation
        # for i in range(0,len(self.transitions)):
        #     for j in range(0,len(self.transitions)):
        #         if forwardSimulation[i][j]:
        #             print("REachImply: "+str(i)+","+str(j))

        # print("Simulation:")
        # for orderPosA in range(0,len(bottomUpOrder)):
        #     for orderPosB in range(0,len(bottomUpOrder)):
        #         if (backwardSimulation[orderPosA][orderPosB]):
        #             print("States "+str(bottomUpOrder[orderPosA])+" "+str(bottomUpOrder[orderPosB])+" sim\n")


        # 4. Remove states that are removable
        for backwardSimulationPositionA in range(0,len(backwardSimulation)):
            for backwardSimulationPositionB in range(0,len(backwardSimulation)):
                if backwardSimulationPositionA!=backwardSimulationPositionB:
                    if backwardSimulation[backwardSimulationPositionA][backwardSimulationPositionB]:

                        # We know that A accepts at least as much as B
                        stateA = bottomUpOrder[backwardSimulationPositionA]
                        stateB = bottomUpOrder[backwardSimulationPositionB]

                        sys.stdout.flush()
                        if forwardSimulation[stateA][stateB]:
                            # We know that B is reached at least as easily as state A
                            # print("Merging candidates",stateA,"and",stateB,file=sys.stderr)
                            # old:
                            # if not reachabilityRelation[stateA][stateB] and not reachabilityRelation[stateB][stateA]:
                            if not reachabilityRelation[stateB][stateA]:
                                # Get rid of A
                                # print("Removing state",stateA,"because of state ",stateB,file=sys.stderr)
                                self.transitions[stateA] = []
                                # Reroute all transitions to State A to State B
                                for i in range(0,len(self.transitions)):
                                    self.transitions[i] = [(a if a!=stateA else stateB,b) for (a,b) in self.transitions[i]]

                            elif not reachabilityRelation[stateA][stateB] and self.rejecting[stateA] == self.rejecting[stateB]:
                                # print("Merger:",self.rejecting,file=sys.stderr)
                                # print("old uvw:",self,file=sys.stderr)
                                self.transitions[stateB].extend([(stateB,cond) for (a,cond) in self.transitions[stateA] if a==stateA])
                                self.transitions[stateB].extend([(a,cond) for (a,cond) in self.transitions[stateA] if a!=stateA])
                                self.transitions[stateA] = []
                                for i in range(0,len(self.transitions)):
                                    self.transitions[i] = [(a if a!=stateA else stateB,b) for (a,b) in self.transitions[i]]


        # Some states may have no outgoing transitions now. Remove them!
        self.removeStatesWithoutOutgoingTransitions()
        self.mergeTransitionsBetweenTheSameStates() # State merging could have caused a disbalance here.
        self.removeUnreachableStates() # State merging could have caused a disbalance here.


    def removeStatesWithoutOutgoingTransitions(self):
        """Removes all states without outgoing transitions. Assumes that all FALSE-transitions have already been removed,
           otherwise some states may remain"""
        assert len(self.rejecting)==len(self.transitions)
        assert len(self.rejecting)==len(self.stateNames)
        emptyStates = [len(self.transitions[i])==0 for i in range(0,len(self.transitions))]
        stateMapper = {}
        self.labelToStateAndActivatingMapper = {} # Purge as this modfies the automaton
        nofStatesSoFar = 0
        for i in range(0,len(self.transitions)):
            if emptyStates[i]:
                stateMapper[i] = None
            else:
                stateMapper[i] = nofStatesSoFar
                nofStatesSoFar += 1
        self.transitions = [[(stateMapper[a],b) for (a,b) in self.transitions[i] if not emptyStates[a]] for i in range(0,len(self.transitions)) if not emptyStates[i]]
        self.stateNames = [self.stateNames[i] for i in range(0,len(self.stateNames)) if not emptyStates[i]]
        self.rejecting = [self.rejecting[i] for i in range(0,len(self.rejecting)) if not emptyStates[i]]
        self.initialStates = [stateMapper[a] for a in self.initialStates if not emptyStates[a]]
        assert len(self.rejecting)==len(self.transitions)
        assert len(self.rejecting)==len(self.stateNames)

    def mergeTransitionsBetweenTheSameStates(self):
        for i in range(0,len(self.transitions)):
            allTrans = {}
            for (a,b) in self.transitions[i]:
                if a in allTrans:
                    allTrans[a] = allTrans[a] | b
                else:
                    if b!=self.ddMgr.false:
                        allTrans[a] = b
            self.transitions[i] = [(a,allTrans[a]) for a in allTrans]

    def simulationBasedMinimization(self):
        """Perform simulation-based minimization. States that are bisimilar are always made equivalent"""

        # 1. Compute a bottom-up ordering of all states
        (bottomUpOrder,reverseBottomUpOrder) = self.getBottomUpAndReverseBottomUpOrder()

        # 2. Compute simulation relation
        simulationRelation = self.computeSimulationRelation(bottomUpOrder,reverseBottomUpOrder)

        # 3. Print Simulation relation
        # print("Simulation:")
        # for orderPosA in range(0,len(bottomUpOrder)):
        #     for orderPosB in range(0,len(bottomUpOrder)):
        #         if (simulationRelation[orderPosA][orderPosB]):
        #             print("States "+str(bottomUpOrder[orderPosA])+" "+str(bottomUpOrder[orderPosB])+" sim\n")

        # 4. Minimize using bisimulation
        #    -> prepare state mapper
        stateMapper = {}
        for j in range(0,len(bottomUpOrder)):
            found = False
            for i in range(0,j):
                if simulationRelation[i][j] and simulationRelation[j][i]:
                    if not found:
                        stateMapper[bottomUpOrder[j]] = bottomUpOrder[i]
                        found = True
            if not found:
                stateMapper[bottomUpOrder[j]] = bottomUpOrder[j]

        # Renumber according to state wrapper
        for i in range(0,len(bottomUpOrder)):
            newTransitions = []
            for (a,b) in self.transitions[i]:
                newTransitions.append((stateMapper[a],b))
            self.transitions[i] = newTransitions
        self.initialStates = [stateMapper[a] for a in self.initialStates]


    def decomposeIntoSimpleChains(self):
        self.mergeTransitionsBetweenTheSameStates()
        result = []

        def recurse(result,pathSoFar):
            # print("Rec:",pathSoFar)
            lastState = pathSoFar[-1]
            foundSucc = False
            foundSelfLoop = False
            for (a,b) in self.transitions[lastState]:
                if a==lastState:
                    foundSelfLoop=True
                    pathSoFar.append(b)
                    # print("MK:",a,b.to_expr())
            if not foundSelfLoop:
                pathSoFar.append(None)
            for (a,b) in self.transitions[lastState]:
                if a!=lastState:
                    foundSucc = True
                    recurse(result,pathSoFar+[b,a])
            if not foundSucc:
                # final!
                novo = UVW(self.ddMgr)
                novo.propositions = copy.copy(self.propositions)
                for i in range(0,(len(pathSoFar)+1)//3):
                    currentState = pathSoFar[i*3]
                    # print("CS:",currentState,pathSoFar[i*3+1])
                    if currentState!=0:
                        novo.addStateButNotNewListOfTransitionsForTheNewState(self.stateNames[currentState],self.rejecting[currentState])
                        novo.transitions.append([])
                        stateNo = len(novo.transitions)-1
                    else:
                        stateNo = 0
                    if (i==0):
                        novo.initialStates.append(stateNo)
                    if not pathSoFar[i*3+1] is None:
                        novo.transitions[stateNo].append((stateNo,pathSoFar[i*3+1]))
                        # print("Reg:",pathSoFar[i*3+1].to_expr(),stateNo,i)
                    if len(pathSoFar)>i*3+2:
                        if pathSoFar[i*3+3]==0:
                            nextState = 0
                        else:
                            nextState = stateNo+1
                        novo.transitions[stateNo].append((nextState,pathSoFar[i*3+2]))
                        # print("TRANS:",stateNo,nextState,pathSoFar[i*3+2].to_expr())
                novo.mergeTransitionsBetweenTheSameStates()
                result.append(novo)

        for i in self.initialStates:
            recurse(result,[i])
        return result


def parseNonTemporalSubformula(node,uvw):
    """Parse a boolean expression to BDD Form. Returns None if the node is
       not a boolean expression."""
    if node.value==NodeTypes.AND:
        subnodes = [parseNonTemporalSubformula(a,uvw) for a in node.children]
        if None in subnodes:
            return None
        return reduce(lambda x,y : x & y,subnodes)
    if node.value==NodeTypes.OR:
        subnodes = [parseNonTemporalSubformula(a,uvw) for a in node.children]
        if None in subnodes:
            return None
        return reduce(lambda x,y : x | y,subnodes)
    if node.value==NodeTypes.NOT:
        assert len(node.children)==1
        subresult = parseNonTemporalSubformula(node.children[0],uvw)
        if subresult is None:
            raise Exception("This function must only be called on formulas in NNF form.")
        return ~subresult
    if node.value==NodeTypes.PROPOSITION:
        if not node.children in uvw.propositions:
            uvw.propositions.append(node.children)
            uvw.ddMgr.declare(node.children)
        return uvw.ddMgr.var(node.children)
    if node.value==NodeTypes.CONSTANT:
        if node.children[0]:
            return ~ uvw.ddMgr.false
        else:
            return uvw.ddMgr.false
    return None

def constructUVWRecurse(node,uvw):
    """Recursive build function for the LTL->UVW translation.
       Returns a pair of UVW set of starting states and an "EXIT" condition in BDD form.
       The latter can be None if this is undefined.
       """

    # Cache lookup
    thisNodePolish = node.toPolishLTL()
    if thisNodePolish in uvw.labelToStateAndActivatingMapper:
        return uvw.labelToStateAndActivatingMapper[thisNodePolish]

    # Case Missing: F(a & F b)

    # 1. See if this is non-temporal
    nt = parseNonTemporalSubformula(node,uvw)
    if not nt is None:
        if nt!=uvw.ddMgr.false:
            newStateNo = uvw.addStateButNotNewListOfTransitionsForTheNewState(node.toPolishLTL(),node)
            uvw.transitions.append([(0,~nt)])
            uvw.labelToStateAndActivatingMapper[thisNodePolish] = ([newStateNo],nt)
            return ([newStateNo],nt)
        else:
            uvw.labelToStateAndActivatingMapper[thisNodePolish] = ([0],nt)
            return ([0],nt)

    # 2. Cover the "Globally something case" -> Phi
    if node.value == NodeTypes.GLOBALLY:
        assert len(node.children)==1
        (uvwSubnodes,exitCondition) = constructUVWRecurse(node.children[0],uvw)
        newStateNo = uvw.addStateButNotNewListOfTransitionsForTheNewState(node.toPolishLTL(),False)
        uvw.transitions.append([(a,b) for k in uvwSubnodes for (a,b) in uvw.transitions[k]]+[(newStateNo,uvw.ddMgr.true)])
        uvw.labelToStateAndActivatingMapper[thisNodePolish] = ([newStateNo],None)
        return ([newStateNo],None)

    # 3. Cover the "Next something case" -> Phi
    if node.value == NodeTypes.NEXT:
        assert len(node.children)==1
        (uvwSubnodes,exitCondition) = constructUVWRecurse(node.children[0],uvw)
        newStateNo = uvw.addStateButNotNewListOfTransitionsForTheNewState(node.toPolishLTL(),False)
        uvw.transitions.append([(a,uvw.ddMgr.true) for a in uvwSubnodes])
        uvw.labelToStateAndActivatingMapper[thisNodePolish] = ([newStateNo],None)
        return ([newStateNo],None)

    # 4. Cover the "And" case -- not atomic --> Phi
    if node.value == NodeTypes.AND:
        newStates = reduce(lambda x,y: (x[0]+y[0],x[1]), [constructUVWRecurse(a,uvw) for a in node.children])[0]
        uvw.labelToStateAndActivatingMapper[thisNodePolish] = (newStates,None)
        return (newStates,None)

    # 4. Cover the "Or" case -- could be Phi or Psi
    if node.value == NodeTypes.OR:

        # Operate pairwise
        if len(node.children)==1:
            return constructUVWRecurse(node.children[0],uvw)

        (initialA,filterA) = constructUVWRecurse(node.children[0],uvw)
        if len(node.children)==2:
            (initialB,filterB) = constructUVWRecurse(node.children[1],uvw)
        else:
            (initialB,filterB) = constructUVWRecurse(Node(NodeTypes.OR,node.children[1:]),uvw)

        # Product -- Init
        todo = [(a,b) for a in initialA for b in initialB]
        mapper = {}
        for (a,b) in todo:
            mapper[(a,b)] = uvw.addStateButNotNewListOfTransitionsForTheNewState("|| "+uvw.stateNames[a]+" "+uvw.stateNames[b],uvw.rejecting[a] and uvw.rejecting[b])

        # Product -- iterate through todo list.
        while len(todo)>0:
            thisOne = todo[0]
            todo = todo[1:]

            # Go through all products
            outTrans = []
            for (targetA,condA) in uvw.transitions[thisOne[0]]:
                for (targetB,condB) in uvw.transitions[thisOne[1]]:
                    if (condA & condB)!=uvw.ddMgr.false:
                        if not (targetA,targetB) in mapper:
                            mapper[(targetA,targetB)] = uvw.addStateButNotNewListOfTransitionsForTheNewState("|| "+uvw.stateNames[targetA]+" "+uvw.stateNames[targetB],uvw.rejecting[targetA] and uvw.rejecting[targetB])
                            todo.append((targetA,targetB))
                        outTrans.append((mapper[(targetA,targetB)],condA & condB))
            uvw.transitions.append(outTrans)

        # Done!
        if (filterA is None) or (filterB is None):
            uvw.labelToStateAndActivatingMapper[thisNodePolish] = ([mapper[(a,b)] for a in initialA for b in initialB],None)
            return ([mapper[(a,b)] for a in initialA for b in initialB],None)
        else:
            uvw.labelToStateAndActivatingMapper[thisNodePolish] = ([mapper[(a,b)] for a in initialA for b in initialB],filterA | filterB)
            return ([mapper[(a,b)] for a in initialA for b in initialB],filterA | filterB)

    # 5. Finally
    if node.value == NodeTypes.FINALLY:
        (subnodes,activator) = constructUVWRecurse(node.children[0],uvw)
        newStateNo = uvw.addStateButNotNewListOfTransitionsForTheNewState(node.toPolishLTL(),True)
        uvw.transitions.append([(newStateNo,~activator)])
        uvw.labelToStateAndActivatingMapper[thisNodePolish] = ([newStateNo],activator)
        return ([newStateNo],activator)

    # 5. Until
    if node.value == NodeTypes.UNTIL:
        (rightPartNodes,rightPartActivator) = constructUVWRecurse(node.children[1],uvw)
        (leftPartNodes,leftPartActivator) = constructUVWRecurse(Node(NodeTypes.OR,[node.children[0],node.children[1]]),uvw)
        if not rightPartActivator is None: # Could be a "Maidl's grammar extension"
            newStateNo = uvw.addStateButNotNewListOfTransitionsForTheNewState(node.toPolishLTL(),True)
            uvw.transitions.append([(newStateNo,~rightPartActivator)]+[(a,b) for k in leftPartNodes for (a,b) in uvw.transitions[k]])
            uvw.labelToStateAndActivatingMapper[thisNodePolish] = ([newStateNo],rightPartActivator)
            return ([newStateNo],rightPartActivator)

    # 5. Release
    if node.value == NodeTypes.RELEASE:
        # In a release node, when the release happens, the guarded condition still needs to hold.
        (leftPartNodes,leftPartActivator) = constructUVWRecurse(node.children[0],uvw)
        (leftPartNodes,doesnotMatter) = constructUVWRecurse(node.children[1],uvw)
        # (leftPartNodes,leftPartActivatorIgnored) = constructUVWRecurse(Node(NodeTypes.AND,[node.children[0],node.children[1]]),uvw) # TODO: Check if we can just use the leftPartNodesa
        (rightPartNodes,rightPartActivator) = constructUVWRecurse(Node(NodeTypes.OR,[node.children[0],node.children[1]]),uvw)
        assert not leftPartActivator is None
        newStateNo = uvw.addStateButNotNewListOfTransitionsForTheNewState(node.toPolishLTL(),False)
        uvw.transitions.append([(newStateNo,~leftPartActivator)]+[(a,b) for k in rightPartNodes for (a,b) in uvw.transitions[k]]+[(a,b & leftPartActivator) for k in leftPartNodes for (a,b) in uvw.transitions[k]])
        uvw.labelToStateAndActivatingMapper[thisNodePolish] = ([newStateNo],leftPartActivator)
        return ([newStateNo],leftPartActivator)

    # 6. Cover Maidl's (p & Phi) U (!p & Phi) case
    if node.value == NodeTypes.UNTIL:

        # Restructure childrenA
        if node.children[0].value == NodeTypes.AND:
            allChildrenA = [constructUVWRecurse(a,uvw) for a in node.children[0].children]
        else:
            allChildrenA = [constructUVWRecurse(node.children[0],uvw)]

        if node.children[1].value == NodeTypes.AND:
            # Let's see if we can use Maidl's case
            allChildrenB = [constructUVWRecurse(a,uvw) for a in node.children[1].children]

            # Merge into the relevant cases
            nonTemporalA = None
            nonTemporalB = None
            failed = False # If matching has failed
            activA = uvw.ddMgr.true
            activB = uvw.ddMgr.true

            # Handle Children A
            for (uvwSubnodes,exitCondition) in allChildrenA:
                isTemporal = True
                for subnode in uvwSubnodes:
                    if len(uvw.transitions[subnode])==0:
                        return constructUVWRecurse(node.children[1],uvw)
                    elif len(uvw.transitions[subnode])==1:
                        (k,l) = uvw.transitions[subnode][0]
                        if k!=0:
                            isTemporal = False
                        else:
                            activA &= ~l
                if not isTemporal:
                    if nonTemporalA is None:
                        nonTemporalA = (uvwSubnodes,exitCondition)
                    else:
                        failed = True

            # Handle Children B
            for (uvwSubnodes,exitCondition) in allChildrenB:
                isTemporal = True
                for subnode in uvwSubnodes:
                    if len(uvw.transitions[subnode])==0:
                        return constructUVWRecurse([0],None) # Cannot exit
                    elif len(uvw.transitions[subnode])==1:
                        (k,l) = uvw.transitions[subnode][0]
                        if k!=0:
                            isTemporal = False
                        else:
                            activB &= ~l
                if not isTemporal:
                    if nonTemporalB is None:
                        nonTemporalB = (uvwSubnodes,exitCondition)
                    else:
                        failed = True

            # Did we get a split?
            if (not failed) and ((activA & activB)==uvw.ddMgr.false):

                # Then build new node!
                newStateNo = uvw.addStateButNotNewListOfTransitionsForTheNewState(node.toPolishLTL(),True)
                uvw.transitions.append([(newStateNo,activA)])
                if not (((~activA) & (~activB))==uvw.ddMgr.false):
                    uvw.transitions[-1].append((0,(~activA) & (~activB)))
                for (uvwSubnodes,exitCondition) in allChildrenA:
                    for subnode in uvwSubnodes:
                        for (target,cond) in uvw.transitions[subnode]:
                            # print ("L",target,(cond & ~activB).to_expr())
                            uvw.transitions[-1].append((target,cond & activA))
                for (uvwSubnodes,exitCondition) in allChildrenB:
                    for subnode in uvwSubnodes:
                        for (target,cond) in uvw.transitions[subnode]:
                            # print ("K",target,(cond & activB).to_expr())
                            uvw.transitions[-1].append((target,cond & activB))

                # print("Final Transitions:")
                # for (a,b) in uvw.transitions[-1]:
                #     print (a,b.to_expr())
                uvw.labelToStateAndActivatingMapper[thisNodePolish] = ([newStateNo],None)
                return ([newStateNo],None)


    raise Exception("Unsupported Node Type for to UVW translation: "+str(node.value))

def constructUVW(node):
    """Takes an LTL formula in node form and constructs a UVW object that is
       equivalent to the formula."""
    uvw = UVW()
    uvw.initialStates = constructUVWRecurse(node,uvw)[0]
    uvw.mergeTransitionsBetweenTheSameStates() # Can be the case for OR nodes.
    uvw.removeStatesWithoutOutgoingTransitions() # Can be the case now that some FALSE transtions have been removed
    return uvw

# ================
# Main -- Translator for the GUI synthesis tool
# ================
if __name__ == '__main__':

    filename = None
    singleActionOptimization = False
    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            if arg=="--singleAction":
                singleActionOptimization = True
            else:
                print("Error: Do not understand the parameter '"+str(arg)+"'.",file=sys.stderr)
                sys.exit(1)
        else:
            if not filename is None:
                print("Error: Multiple file names given.",file=sys.stderr)
                sys.exit(1)
            filename = arg

    if filename is None:
        print("Error: Need a formula file name!",file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1],"r") as inFile:
    	formulaTxt = inFile.readline().strip()

    # Assuming the LTL specification is for a never claim
    assert formulaTxt[0:4]=="LTL "

    formulaNode = parser.computeNNF(parser.simplifyTree(parser.elimImplies(parser.parse(formulaTxt))))
    if not parser.isATreeAcceptedByANonTerminalOfOurUVWGrammar(formulaNode,"Phi"):
        print("Error: Input is not in the supported LTL fragment.",file=sys.stderr)
        parser.printTreeWithSupportedAnnotatedNonterminalsForUVWGrammar(formulaNode)
        sys.exit(1)

    print("================Constructing UVW================",file=sys.stderr)
    uvw = constructUVW(formulaNode)
    if singleActionOptimization:
        uvw.restrictToTheCaseThatThereCanOnlyBeOneActionAtATime()
    print("================Original Automaton================",file=sys.stderr)
    # print(uvw,file=sys.stderr)
    # These two are needed in case "restrictToTheCaseThatThereCanOnlyBeOneActionAtATime" disconnected states
    # as otherwise the later simulationBasedMinimization may fail.
    uvw.removeUnreachableStates()
    uvw.removeStatesWithoutOutgoingTransitions()
    print("================Removed Unreachable States================",file=sys.stderr)
    # print(uvw,file=sys.stderr)
    uvw.simulationBasedMinimization()

    print("================Before merging equivalently reachable states================",file=sys.stderr)
    # print(uvw,file=sys.stderr)
    uvw.mergeEquivalentlyReachableStates()

    print("================Before removing forward simulatable states================",file=sys.stderr)
    # print(uvw,file=sys.stderr)

    uvw.removeForwardReachableBackwardSimulatingStates()
    uvw.removeUnreachableStates()
    uvw.makeTransientStatesNonRejecting()

    print(uvw.inGameSolverFormat(singleActionOptimization))
