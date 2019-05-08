#!/usr/bin/env python3
import unittest
import parser
import sys

class TestParser(unittest.TestCase):

    def testSomeFormulasToBeParsable(self):
        parser.parse("LTL G F a")
        parser.parse("LTL R G a F b")

    def testSomeFormulasToBeUnparsable(self):
        with self.assertRaises(Exception):
            parser.parse("LTL G F U a")
        with self.assertRaises(Exception):
            parser.parse("LTL G F R a")
        with self.assertRaises(Exception):
            parser.parse("LTL U a")

    def testSomeConcreteTrees(self):
        tree = parser.parse("LTL G F a")
        assert tree.value == parser.NodeTypes.GLOBALLY
        assert tree.children[0].value == parser.NodeTypes.FINALLY
        assert tree.children[0].children[0].value == parser.NodeTypes.PROPOSITION
        assert tree.children[0].children[0].children == "a"

    def testNegationNormalForm(self):
        listOfTestCases = [
            ("LTL ~ G F a","LTL F G ~ a"),
            ("LTL ~ || a b","LTL && ~ a ~ b"),
            ("LTL ~ ~ ~ G F ~ a","LTL F G a"),
            ]
        for (before,after) in listOfTestCases:
            tree1 = parser.parse(before)
            tree2 = parser.parse(after)
            nnf = parser.computeNNF(tree1)
            assert str(nnf) == str(tree2)

    def testSimplify(self):
        listOfTestCases = [
            ("LTL G G F a","LTL G F a"),
            ("LTL F F ~ ~ a","LTL F a")
            ]
        for (before,after) in listOfTestCases:
            tree1 = parser.parse(before)
            tree2 = parser.parse(after)
            simpler = parser.simplifyTree(tree1)
            assert str(simpler) == str(tree2)

    def testElimImplies(self):
        listOfTestCases = [
            ("LTL -> G a F a","LTL || ~ G a F a"),
            ("LTL F ~ a","LTL F ~ a"),
            ("LTL -> a -> b c","LTL || ~ a || ~ b c")
            ]
        for (before,after) in listOfTestCases:
            tree1 = parser.parse(before)
            tree2 = parser.parse(after)
            simpler = parser.elimImplies(tree1)
            assert str(simpler) == str(tree2)

    def testIsATreeAcceptedByANonTerminalOfOurUVWGrammar(self):
        listOfTestCases = [
            ("LTL a","Phi",True),
            ("LTL G F G a","Phi",False),
            ("LTL G F b","Phi",True),
            ("LTL ~ G F b","Phi",False),
            ("LTL F G b","Phi",False),
            ("LTL F b","Psi",True),
            ("LTL G F b","Psi",False),
            ("LTL U a U b c","Phi",True),
            ("LTL G U & F p G q & ! p G k","Phi",False), # Maidl's original grammar
            ("LTL G U & p G q & ! F k G k","Phi",False), # Maidl's original grammar
            ("LTL G U & p G q & ! p G k","Phi",True), # Maidl's original grammar
            ("LTL G U & p G q & r G k","Phi",False), # Maidl's original grammar
            ("LTL G U & & p q G r & ! & p q G k","Phi",True), # Maidl's original grammar
            ("LTL G U & & p q G r & | ! p ! q G k","Phi",True), # Maidl's original grammar
            ("LTL G U & & p q G r & | ! p q G k","Phi",False), # Maidl's original grammar
            ]
        for (ltl,nonterminal,shouldBeAccepted) in listOfTestCases:
            tree1 = parser.parse(ltl)
            tree2 = parser.simplifyTree(tree1)
            tree3 = parser.elimImplies(tree2)
            tree4 = parser.computeNNF(tree3)
            isAccepted = parser.isATreeAcceptedByANonTerminalOfOurUVWGrammar(tree4,nonterminal)
            assert isAccepted == shouldBeAccepted

    def testTreesinUVWGrammar(self):
        listOfTestCases = [
        #Spinroot Example:Blue Spec TM Specification
            ("LTL G | ! a X U ! b c",True),
            ("LTL G | & ! a ! b X U ! c | a d",True),
            ("LTL G | & ! a ! b X U ! c a",True),
            ("LTL G | | ! a ! b X U ! c d",True),
            ("LTL G | | ! a ! b X U ! c & a d",True),
        #Spinroot Example: CORBA General Inter-Orb Protocol
            ("LTL | G ! p U q r",True),
            ("LTL G | | ! q G ! r U ! r p",True),
            ("LTL G | ! p F s",True),
            ("LTL | G ! p U ! p & ! p s",True),
            ("LTL G | | ! q G ! r U ! p r",True),
            ("LTL G | | ! q G ! r U & ! p ! r | r U & p ! r | r U ! p r",True),
        #Spinroot Example:PLC Control Schedule
            ("LTL & G F | ! a b G F | ! a c",True),
        #Spinroot Example:Space Craft Controller
            ("LTL G | ! a F b",True),
            ("LTL G | ! a F | b c",True),
        #Spinroot Example:Group Address Registration Protocol
            ("LTL G | ! p F G q",False),
        #Spinroot Example: Needham-Schroeder Public Key Protocol
            ("LTL G | G ! p U ! p q",True),
        #Spinroot Example: Cardiac pacemaker model
            ("LTL G | ! p F & & q r s",True),
            ("LTL G | ! p r",True),
            ("LTL G & | ! p ! q | ! r s",True),
            ("LTL G & p | ! q r",True),
            ("LTL G | | ! p ! q & r s",True),
            ("LTL G | & & ! p ! q ! r F x",True),
        #Example Anderson from paper 'IS THERE A BEST BUCHI AUTOMATA FOR EXPLICIT MC'
            ("LTL G -> | | ap0 ap1 ap2 F ap3",True),
            ("LTL ! G -> | | ap0 ap1 ap2 F ap3",False),
            ("LTL G -> ! ap0 F ap0",True),
            ("LTL ! G -> ! ap0 F ap0",False),
            ("LTL G F | ap0 ap1",True),
            ("LTL ! G F | ap0 ap1",False),
            ("LTL G -> | | ap0 ap1 ap2 F ap3",True),
            ("LTL ! G -> | | ap0 ap1 ap2 F ap3",False),
            ("LTL G -> ! ap0 F ap0",True),
            ("LTL ! G -> ! ap0 F ap0",False),
            ("LTL G F | | ap0 ap1 ap2",True),
            ("LTL ! G F | | ap0 ap1 ap2",False),
            ("LTL G -> | | ap0 ap1 ap2 F ap3",True),
            ("LTL ! G -> | | ap0 ap1 ap2 F ap3",False),
            ("LTL G -> ! ap0 F ap0",True),
            ("LTL ! G -> ! ap0 F ap0",False),
            ("LTL G F | | ap0 ap1 ap2",True),
            ("LTL ! G F | | ap0 ap1 ap2",False),
            ("LTL G -> | | ap0 ap1 ap2 F ap3",True),
            ("LTL ! G -> | | ap0 ap1 ap2 F ap3",False),
            ("LTL G -> ! ap0 F ap0",True),
            ("LTL ! G -> ! ap0 F ap0",False),
            ("LTL G F | | | ap0 ap1 ap2 ap3",True),
            ("LTL ! G F | | | ap0 ap1 ap2 ap3",False),
            ("LTL G -> | | ap0 ap1 ap2 F ap3",True),
            ("LTL ! G -> | | ap0 ap1 ap2 F ap3",False),
            ("LTL G -> ! ap0 F ap0",True),
            ("LTL ! G -> ! ap0 F ap0",False),
            ("LTL G F | | | | ap0 ap1 ap2 ap3 ap4",True),
            ("LTL ! G F | | | | ap0 ap1 ap2 ap3 ap4",False),
            ("LTL G -> | | ap0 ap1 ap2 F ap3",True),
            ("LTL ! G -> | | ap0 ap1 ap2 F ap3",False),
            ("LTL G -> ! ap0 F ap0",True),
            ("LTL ! G -> ! ap0 F ap0",False),
            ("LTL G F | | | | | ap0 ap1 ap2 ap3 ap4 ap5",True),
            ("LTL ! G F | | | | | ap0 ap1 ap2 ap3 ap4 ap5",False),
            ("LTL G -> | | ap0 ap1 ap2 F ap3",True),
            ("LTL ! G -> | | ap0 ap1 ap2 F ap3",False),
            ("LTL G -> ! ap0 F ap0",True),
            ("LTL ! G -> ! ap0 F ap0",False),
            ("LTL G F | | | | | ap0 ap1 ap2 ap3 ap4 ap5",True),
            ("LTL ! G F | | | | | ap0 ap1 ap2 ap3 ap4 ap5",False),
            ("LTL G -> | | ap0 ap1 ap2 F ap3",True),
            ("LTL ! G -> | | ap0 ap1 ap2 F ap3",False),
            ("LTL G -> ! ap0 F ap0",True),
            ("LTL ! G -> ! ap0 F ap0",False),
            ("LTL G F | | | | | | ap0 ap1 ap2 ap3 ap4 ap5 ap6",True),
            ("LTL ! G F | | | | | | ap0 ap1 ap2 ap3 ap4 ap5 ap6",False),
            ]
        for (ltl,shouldBeAccepted) in listOfTestCases:
            tree1 = parser.parse(ltl)
            tree2 = parser.simplifyTree(tree1)
            tree3 = parser.elimImplies(tree2)
            tree4 = parser.computeNNF(tree3)
            isAccepted = parser.isATreeAcceptedByANonTerminalOfOurUVWGrammar(tree4,"Phi")
            assert isAccepted == shouldBeAccepted


if __name__ == '__main__':
    unittest.main()
