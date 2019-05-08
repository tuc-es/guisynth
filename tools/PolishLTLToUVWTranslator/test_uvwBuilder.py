#!/usr/bin/env python3
import unittest
import parser
import uvwBuilder
import sys
import time

class TestBuilder(unittest.TestCase):

    def testUVWSizeUnminimized(self):
        listOfTestCases = [
            ("LTL G F a",3),
            ("LTL || a b",2),
            ("LTL || G a G b",5), # The error state gets duplicated
        ]
        for (ltl,expectedSize) in listOfTestCases:
            formulaNode = parser.computeNNF(parser.simplifyTree(parser.elimImplies(parser.parse(ltl))))
            uvw = uvwBuilder.constructUVW(formulaNode)
            uvw.removeUnreachableStates()
            assert len(uvw.stateNames)==expectedSize

    def testUVWSizeMinimized(self):
        listOfTestCases = [
            ("LTL G F a",3),
            ("LTL || a b",2),
            ("LTL || G a G b",4),
            ("LTL && G a G b",2),
            ("LTL || G F a G F b",3),
            ("LTL && G F a G F b",4),
            ("LTL || || G a G b G c",8),
            ("LTL || G a G ~ a",4),
            ("LTL F || F a F b",2),
            ("LTL F && ~ a a",1),
            ("LTL U && ~ a G b && a F d",4),
            ("LTL U ! buttonB.click & buttonB.click U ! idle buttonA.enable", 3),
            ("LTL | G ! buttonB.click U ! buttonB.click & buttonB.click U ! idle buttonA.enable", 3),
            ("LTL G | G ! buttonB.click U ! buttonB.click & buttonB.click U ! idle buttonA.enable", 3)
        ]
        for (ltl,expectedSize) in listOfTestCases:
            formulaNode = parser.computeNNF(parser.simplifyTree(parser.elimImplies(parser.parse(ltl))))
            assert parser.isATreeAcceptedByANonTerminalOfOurUVWGrammar(formulaNode,"Phi")
            uvw = uvwBuilder.constructUVW(formulaNode)
            #print(uvw)
            uvw.removeUnreachableStates()
            #print(uvw)
            uvw.simulationBasedMinimization()
            uvw.removeUnreachableStates()
            #print(uvw)
            uvw.mergeEquivalentlyReachableStates()
            #print(uvw)
            uvw.removeForwardReachableBackwardSimulatingStates()
            #print(uvw)
            if len(uvw.stateNames)!=expectedSize:
                print("Unexpected size:")
                print(ltl)
                print(uvw)
                sys.stdout.flush()
            assert len(uvw.stateNames)==expectedSize
            #print("ok.")

    def testSomeErrorCases(self):

        # Illegal UVW parsing from strings
        uvw = uvwBuilder.UVW()
        uvw.ddMgr.declare('a','b')
        uvwBuilder.UVW.parseFromUVWDescription(uvw.ddMgr,"2(i)-[a]->2,2(i)-[b]->2")
        with self.assertRaises(Exception):
            uvwBuilder.UVW.parseFromUVWDescription(uvw.ddMgr,"2(i)-[a]->2,2(i)-[b]->2,1(ik)-[True]->1")

        # Throw exception if not in NNF
        with self.assertRaises(Exception):
            formulaNode = parser.simplifyTree(parser.parse("LTL G ~ G a"))
            uvw = uvwBuilder.constructUVW(formulaNode)

        # Throw exception if there is still a "->" in the LTL formula
        with self.assertRaises(Exception):
            formulaNode = parser.simplifyTree(parser.parse("LTL G -> a b"))
            uvw = uvwBuilder.constructUVW(formulaNode)


    def testSimpleChainDecomposition(self):
        listOfTestCases = [
            ("LTL G F a",["1(i)-[True]->1,1-[~a]->2,2(r)-[~a]->2"],True),
            ("LTL && G a G F b",["1(i)-[True]->1,1-[~a]->0","1(i)-[True]->1,1-[~b]->2,2(r)-[~b]->2"],True),
            ("LTL && X G a G F b",["2(i)-[True]->1,1-[True]->1,1-[~a]->0","1(i)-[True]->1,1-[~b]->2,2(r)-[~b]->2"],True),
            ("LTL && G a G F b",["1(i)-[True]->1,1-[~a]->0"],False),
            ("LTL && G F a G F b",["1(i)-[True]->1,1-[~a]->2,2(r)-[~a]->2","1(i)-[True]->1,1-[~b]->2,2(r)-[~b]->2"],True),
            ("LTL && && G F ~ c G F a G F b",["1(i)-[True]->1,1-[c]->2,2(r)-[c]->2", "1(i)-[True]->1,1-[~a]->2,2(r)-[~a]->2","1(i)-[True]->1,1-[~b]->2,2(r)-[~b]->2"],True),
            ("LTL U U a b c",["1(ir)-[~c]->1,1-[~b & ~c]->2,2(r)-[~b]->2,2-[~a & ~b]->0","1(ir)-[~c]->1,1-[~c & ~b & ~a]->0"],True)
        ]

        for (ltl,expectedChains,should) in listOfTestCases:
            formulaNode = parser.computeNNF(parser.simplifyTree(parser.parse(ltl)))
            uvw = uvwBuilder.constructUVW(parser.Node(parser.NodeTypes.OR,[formulaNode])) # Test single-element or along the way
            uvw.removeUnreachableStates()
            uvw.simulationBasedMinimization()
            uvw.removeUnreachableStates()
            uvw.mergeEquivalentlyReachableStates()
            uvw.removeForwardReachableBackwardSimulatingStates()
            decomposedUVWs = uvw.decomposeIntoSimpleChains()
            expectedUVWs = [uvwBuilder.UVW.parseFromUVWDescription(uvw.ddMgr,a) for a in expectedChains]

            #print("----orig----",file=sys.stderr)
            #print(uvw,file=sys.stderr)

            #print("----decomposed----",file=sys.stderr)
            #for a in decomposedUVWs:
            #    print(a,file=sys.stderr)

            # Check if for every expected UVW, there is an equivalent UVW in the decomposed chains
            # and vice versa
            foundAll = True
            for (set1,set2) in [(expectedUVWs,decomposedUVWs),(decomposedUVWs,expectedUVWs)]:
                for a in set1:
                    foundThisOne = False
                    for b in set2:
                        if uvwBuilder.UVW.isBisimulationEquivalent(a,b):
                            foundThisOne = True
                    foundAll = foundAll and foundThisOne

            assert should == foundAll


    def testSomeConcreteTrees(self):
        listOfTestCases = [
            ("LTL G F a","1(i)-[True]->1,1-[~a]->2,2(r)-[~a]->2",True),
            ("LTL G F a","1(i)-[True]->1,1-[~a]->2,2(r)-[a]->2",False),
            ("LTL && G a G b","1(i)-[True]->1,1-[~a | ~b]->0",True),
            ("LTL && G F a G F b","1(i)-[True]->1,1-[~a]->2,2(r)-[~a]->2",False),
            ("LTL && G F a G F b","1(i)-[True]->1,1-[~a]->2,2(r)-[~a]->2,1-[~b]->3,3(r)-[~b]->3",True),
            ("LTL U a b","1(ir)-[a & ~b]->1,1-[~a & ~b]->0",True),
            ("LTL R b a","1(i)-[a & ~b]->1,1-[~a]->0",True),
            ("LTL U a b","1(i)-[a & ~b]->1,1-[~a & ~b]->0",False),
            ("LTL R b a","1(ir)-[a & ~b]->1,1-[~a & ~b]->0",False),
            ("LTL X && G a G a","1(ir)-[True]->2,2-[True]->2,2-[~a]->0",True),
            ("LTL && && X G b X G a X G && c ~ d","1(ir)-[True]->2,2-[True]->2,2-[~a | ~b | ~c | d]->0",True),
            ("LTL X && && X X G a X G a X X X G a","1(i)-[True]->2,2-[True]->3,3-[True]->3,3-[~a]->0",True),
            ("LTL F && ~ a a","1(i)-[True]->0",True),
            ("LTL || a ~ a","",True),
            ("LTL U a U b c","1(ir)-[~c & a]->1,1-[~a & ~c]->2,1-[~a & ~b & ~c]->0,2(r)-[~c]->2,2-[~b & ~c]->0",True),
            ("LTL U U a b c","1(ir)-[~c]->1,1-[~a & ~b & ~c]->0,1-[~b & ~c]->2,2(r)-[~b]->2,2-[~a & ~b]->0",True),
            ("LTL && G -> && a b F || c d G -> a F c","1(i)-[True]->1,1-[a]->2,2(r)-[~c]->2",False),
            ("LTL && G -> && a b F || c d G -> a F c","1(i)-[True]->1,1-[a & ~c]->2,2(r)-[~c]->2",True),
            ("LTL G R a b","1(i)-[True]->1,1-[~b]->0",True),
            ("LTL G R a R b c","1(i)-[True]->1,1-[~c]->0",True),
        ]
        for (ltl,expectedResult,should) in listOfTestCases:
            formulaNode = parser.computeNNF(parser.elimImplies(parser.simplifyTree(parser.parse(ltl))))
            uvw = uvwBuilder.constructUVW(formulaNode)
            uvw.removeUnreachableStates()
            uvw.simulationBasedMinimization()
            uvw.removeUnreachableStates()
            uvw.mergeEquivalentlyReachableStates()
            uvw.removeForwardReachableBackwardSimulatingStates()

            referenceUVW = uvwBuilder.UVW.parseFromUVWDescription(uvw.ddMgr,expectedResult)
            try:
                assert parser.isATreeAcceptedByANonTerminalOfOurUVWGrammar(formulaNode,"Phi")
                assert should == uvwBuilder.UVW.isBisimulationEquivalent(uvw,referenceUVW)
                if should:
                    assert len(uvw.transitions) <= len(referenceUVW.transitions) # Not too large
            except AssertionError:
                print("LTL:",ltl)
                print("Expected:",referenceUVW)
                print("Got:",uvw)
                raise

            # Test if this terminates
            uvw.toNeverClaim()


if __name__ == '__main__':
    unittest.main()
