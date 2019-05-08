#!/usr/bin/env python3
import sys
import string
import re
from enum import Enum



class NodeTypes(Enum):
    GLOBALLY = 1
    FINALLY = 2
    NEXT = 3
    NOT = 4
    PROPOSITION = 5
    CONSTANT = 6
    UNTIL = 7
    OR = 8
    AND = 9
    IMPLIES = 10
    RELEASE = 11



class Node(object):
    def __init__(self, value, children = []):
        self.value = value
        self.children = children
        assert isinstance(self.value, NodeTypes)

    def __str__(self, level=0):
        if self.value==NodeTypes.PROPOSITION:
            return "\t"*level+self.children+"\n"
        elif self.value==NodeTypes.CONSTANT:
            return "\t"*level+str(self.children)+"\n"
        ret = "\t"*level+repr(self.value)+"\n"
        for child in self.children:
            ret += child.__str__(level+1)
        return ret

    def __hash__(self):
        return hash(tuple([self.value]+[hash(a) for a in self.children]))

    def __eq__(self,other):
        if self.value != other.value:
            return False
        if len(self.children) != len(other.children):
            return False
        for i in range(0,len(self.children)):
            if not self.children[i].__eq__(other.children[i]):
                return False
        return True

    def isNegatedVersionOfOtherNNFNode(self,other):
        # Check correct type
        if other.value==NodeTypes.NOT:
            return other.children[0] == self
        if self.value==NodeTypes.NOT:
            return self.children[0] == other
        if self.value==NodeTypes.AND:
            if other.value!=NodeTypes.OR:
                return False
        if self.value==NodeTypes.OR:
            if other.value!=NodeTypes.AND:
                return False
        if self.value==NodeTypes.GLOBALLY:
            if other.value!=NodeTypes.FINALLY:
                return False
        if self.value==NodeTypes.NEXT:
            if other.value!=NodeTypes.NEXT:
                return False
        if self.value==NodeTypes.PROPOSITION:
            return False
        for (base,cpy) in [(other.children,self.children),(self.children,other.children)]:
            for c1 in base:
                found = False
                for c2 in cpy:
                    # with open("smack.txt","a") as outFile:
                    #     outFile.write("a: ",str(c1),"\n")
                    #     outFile.write("b: ",str(c2),"\n")
                    #     outFile.write("res: ",c1.isNegatedVersionOfOtherNNFNode(c2),"\n")
                    if c1.isNegatedVersionOfOtherNNFNode(c2):
                        found = True
                if not found:
                    return False
        return True

    def __repr__(self):
        return self.__str__()

    def toPolishLTL(self):
        if self.value==NodeTypes.AND:
            return "& "*(len(self.children)-1)+" ".join([a.toPolishLTL() for a in self.children])
        if self.value==NodeTypes.OR:
            return "| "*(len(self.children)-1)+" ".join([a.toPolishLTL() for a in self.children])
        assert not self.value==NodeTypes.IMPLIES # not implemented
        if self.value==NodeTypes.GLOBALLY:
            return "G "+self.children[0].toPolishLTL()
        if self.value==NodeTypes.FINALLY:
            return "F "+self.children[0].toPolishLTL()
        if self.value==NodeTypes.NEXT:
            return "X "+self.children[0].toPolishLTL()
        if self.value==NodeTypes.NOT:
            return "! "+self.children[0].toPolishLTL()
        if self.value==NodeTypes.UNTIL:
            return "U "+self.children[0].toPolishLTL()+" "+self.children[1].toPolishLTL()
        if self.value==NodeTypes.RELEASE:
            return "R "+self.children[0].toPolishLTL()+" "+self.children[1].toPolishLTL()
        if self.value==NodeTypes.PROPOSITION:
            return self.children
        if self.value==NodeTypes.CONSTANT:
            if self.children[0]:
                return "1"
            else:
                return "0"
        raise Exception("Unsupported node type: "+str(self.value))



def recurseParse(parts):
    if len(parts)==0:
        raise Exception("Error reading the input formula: the formula is too short")
    elif parts[0]=="1":
        return (Node(NodeTypes.CONSTANT,[True]),parts[1:])
    elif parts[0]=="0":
        return (Node(NodeTypes.CONSTANT,[False]),parts[1:])
    elif parts[0]=="G":
        (result,rest) = recurseParse(parts[1:])
        return (Node(NodeTypes.GLOBALLY,[result]),rest)
    elif parts[0]=="F":
        (result,rest) = recurseParse(parts[1:])
        return (Node(NodeTypes.FINALLY,[result]),rest)
    elif parts[0]=="X":
        (result,rest) = recurseParse(parts[1:])
        return (Node(NodeTypes.NEXT,[result]),rest)
    elif parts[0]=="~" or parts[0]=="!":
        (result,rest) = recurseParse(parts[1:])
        return (Node(NodeTypes.NOT,[result]),rest)
    elif parts[0]=="U":
        (result,rest) = recurseParse(parts[1:])
        (result2,rest2) = recurseParse(rest)
        return (Node(NodeTypes.UNTIL,[result,result2]),rest2)
    elif parts[0]=="W":
        (result,rest) = recurseParse(parts[1:])
        (result2,rest2) = recurseParse(rest)
        return (Node(NodeTypes.RELEASE,[result2,Node(NodeTypes.OR,[result,result2])]),rest2)
    elif parts[0]=="R":
        (result,rest) = recurseParse(parts[1:])
        (result2,rest2) = recurseParse(rest)
        return (Node(NodeTypes.RELEASE,[result,result2]),rest2)
    elif parts[0]=="||" or parts[0]=="|":
        (result,rest) = recurseParse(parts[1:])
        (result2,rest2) = recurseParse(rest)
        return (Node(NodeTypes.OR,[result,result2]),rest2)
    elif parts[0]=="&&" or parts[0]=="&":
        (result,rest) = recurseParse(parts[1:])
        (result2,rest2) = recurseParse(rest)
        return (Node(NodeTypes.AND,[result,result2]),rest2)
    elif parts[0]=="->":
        (result,rest) = recurseParse(parts[1:])
        (result2,rest2) = recurseParse(rest)
        return (Node(NodeTypes.IMPLIES,[result,result2]),rest2)
    else:
        regex = re.compile('[A-Za-z]+[a-zA-Z0-9\.]*|\"[a-z0-9A-Z\_\-\+\[\]\.\@\=]*\"')
        match = regex.match(parts[0])
        if match is None:
            raise Exception("Error reading the input formula: don't know what to do with '"+parts[0]+"'.")
        if match.end()!=len(parts[0]):
            raise Exception("Error reading the input formula: the proposition '"+parts[0]+"' has stray characters. I am only parsing the first",match.end(),"characters")
        return (Node(NodeTypes.PROPOSITION,parts[0]),parts[1:])




def simplifyTree(node):
    if node.value == NodeTypes.PROPOSITION:
        return node
    elif node.value == NodeTypes.CONSTANT:
        return node
    elif node.value == NodeTypes.GLOBALLY:
        subtree = simplifyTree(node.children[0])
        if subtree.value==NodeTypes.GLOBALLY:
            return subtree
        else:
            return Node(NodeTypes.GLOBALLY,[subtree])
    elif node.value == NodeTypes.FINALLY:
        subtree = simplifyTree(node.children[0])
        if subtree.value==NodeTypes.FINALLY:
            return subtree
        else:
            return Node(NodeTypes.FINALLY,[subtree])
    elif node.value == NodeTypes.AND:
        newChildren = [simplifyTree(a) for a in node.children]
        newChildrenAnds = [a for a in newChildren if a.value == NodeTypes.AND]
        newChildrenRest = [a for a in newChildren if a.value != NodeTypes.AND]
        allOperands = [c for a in newChildrenAnds for c in a.children ]+newChildrenRest
        if len(allOperands)==1:
            return allOperands[0]
        else:
            return Node(NodeTypes.AND,allOperands)
    elif node.value == NodeTypes.OR:
        newChildren = [simplifyTree(a) for a in node.children]
        newChildrenOrs = [a for a in newChildren if a.value == NodeTypes.OR]
        newChildrenRest = [a for a in newChildren if a.value != NodeTypes.OR]
        allOperands = [c for a in newChildrenOrs for c in a.children ]+newChildrenRest
        if len(allOperands)==1:
            return allOperands[0]
        else:
            return Node(NodeTypes.OR,allOperands)
    elif node.value==NodeTypes.NOT:
        child = simplifyTree(node.children[0])
        if child.value==NodeTypes.NOT:
            return child.children[0]
        else:
            return Node(NodeTypes.NOT,[child])
    else:
        return Node(node.value,[simplifyTree(a) for a in node.children])


def elimImplies(formula):
    if formula.value==NodeTypes.IMPLIES:
        assert len(formula.children) == 2
        notNode = Node(NodeTypes.NOT,[elimImplies(formula.children[0])])
        return Node(NodeTypes.OR, [notNode, elimImplies(formula.children[1])])
    elif formula.value == NodeTypes.PROPOSITION:
        return formula
    elif formula.value == NodeTypes.CONSTANT:
        return formula
    else:
        childList = []
        for a in formula.children:
            childList.append(elimImplies(a))
        return Node(formula.value, childList)


def computeNNF(formula, negated=False):
    if formula.value == NodeTypes.PROPOSITION:
        if negated:
            return Node(NodeTypes.NOT, [Node(NodeTypes.PROPOSITION,formula.children)])
        else:
            return formula
    elif formula.value == NodeTypes.NOT:
        assert len(formula.children)==1
        return computeNNF(formula.children[0], not negated)
    elif formula.value == NodeTypes.GLOBALLY:
        if negated:
            return Node(NodeTypes.FINALLY,[computeNNF(formula.children[0],negated)])
        else:
            return Node(NodeTypes.GLOBALLY,[computeNNF(formula.children[0],negated)])
    elif formula.value == NodeTypes.FINALLY:
        if negated:
            return Node(NodeTypes.GLOBALLY,[computeNNF(formula.children[0],negated)])
        else:
            return Node(NodeTypes.FINALLY,[computeNNF(formula.children[0],negated)])
    elif formula.value == NodeTypes.NEXT:
        return Node(NodeTypes.NEXT,[computeNNF(formula.children[0],negated)])
    elif formula.value == NodeTypes.OR:
        if negated:
            return Node(NodeTypes.AND,[computeNNF(a,negated) for a in formula.children])
        else:
            return Node(NodeTypes.OR,[computeNNF(a,negated) for a in formula.children])
    elif formula.value == NodeTypes.AND:
        if negated:
            return Node(NodeTypes.OR,[computeNNF(a,negated) for a in formula.children])
        else:
            return Node(NodeTypes.AND,[computeNNF(a,negated) for a in formula.children])
    elif formula.value == NodeTypes.UNTIL:
        if negated:
            return Node(NodeTypes.RELEASE,[computeNNF(a,negated) for a in formula.children])
        else:
            return Node(NodeTypes.UNTIL,[computeNNF(a,negated) for a in formula.children])
    elif formula.value == NodeTypes.RELEASE:
        if negated:
            return Node(NodeTypes.UNTIL,[computeNNF(a,negated) for a in formula.children])
        else:
            return Node(NodeTypes.RELEASE,[computeNNF(a,negated) for a in formula.children])
    elif formula.value == NodeTypes.CONSTANT:
        assert len(formula.children)==1
        if negated:
            return Node(NodeTypes.CONSTANT,[not formula.children[0]])
        else:
            return Node(NodeTypes.CONSTANT,[formula.children[0]])
    else:
        raise Exception("Don't know what to do with the node type "+str(formula.value))


def printTreeWithSupportedAnnotatedNonterminalsForUVWGrammar(tree):

    def recurse(tree, level=0):
        if tree.value==NodeTypes.PROPOSITION:
            return "\t"*level+tree.children+"\n"
        elif tree.value==NodeTypes.CONSTANT:
            return "\t"*level+str(tree.children)+"\n"
        ret = "\t"*level+repr(tree.value)
        for g in ["Phi","Psi","NT"]:
            if isATreeAcceptedByANonTerminalOfOurUVWGrammar(tree,g):
                ret = ret + " "+g
        ret = ret + "\n"
        for child in tree.children:
            ret +=recurse(child,level+1)
        return ret

    print(recurse(tree),file=sys.stderr)

def isATreeAcceptedByANonTerminalOfOurUVWGrammar(node,nonterminalName):
    if (nonterminalName == "Phi" and isATreeAcceptedByANonTerminalOfOurUVWGrammar(node,"Psi")):
        return True
    if (nonterminalName == "Psi" and isATreeAcceptedByANonTerminalOfOurUVWGrammar(node,"NT")):
        return True
    if (nonterminalName == "Phi" and node.value == NodeTypes.GLOBALLY):
        a = isATreeAcceptedByANonTerminalOfOurUVWGrammar(node.children[0], "Phi")
        if a:
            return True
    if (nonterminalName == "Phi" and node.value == NodeTypes.NEXT):
        a = isATreeAcceptedByANonTerminalOfOurUVWGrammar(node.children[0], "Phi")
        if a:
            return True
    if (nonterminalName == "Phi" and node.value == NodeTypes.AND):
        a=True
        for c in node.children:
            a = a and isATreeAcceptedByANonTerminalOfOurUVWGrammar(c, "Phi")
        if a:
            return True
    if (nonterminalName == "Phi" and node.value == NodeTypes.OR):
        a=True
        for c in node.children:
            a = a and isATreeAcceptedByANonTerminalOfOurUVWGrammar(c, "Phi")
        if a:
            return True
    if (nonterminalName == "Psi" and node.value == NodeTypes.FINALLY):
        a = isATreeAcceptedByANonTerminalOfOurUVWGrammar(node.children[0], "Psi")
        if a:
            return True
    if (nonterminalName == "Psi" and node.value == NodeTypes.OR):
        a=True
        for c in node.children:
            a = a and isATreeAcceptedByANonTerminalOfOurUVWGrammar(c, "Psi")
        if a:
            return True
    if (nonterminalName == "NT" and node.value == NodeTypes.PROPOSITION):
        return True
    if (nonterminalName == "NT" and node.value == NodeTypes.NOT):
        assert len(node.children)==1
        assert node.children[0].value == NodeTypes.PROPOSITION
        return True
    if (nonterminalName == "NT" and node.value == NodeTypes.OR):
        a=True
        for c in node.children:
            a = a and isATreeAcceptedByANonTerminalOfOurUVWGrammar(c, "NT")
        if a:
            return True
    if (nonterminalName == "NT" and node.value == NodeTypes.AND):
        a=True
        for c in node.children:
            a = a and isATreeAcceptedByANonTerminalOfOurUVWGrammar(c, "NT")
        if a:
            return True
    if (nonterminalName == "Phi" and node.value == NodeTypes.RELEASE):
        assert len(node.children)==2
        a = isATreeAcceptedByANonTerminalOfOurUVWGrammar(node.children[0], "Psi")
        b = isATreeAcceptedByANonTerminalOfOurUVWGrammar(node.children[1], "Phi")
        if a and b:
            return True
    if (nonterminalName == "Psi" and node.value == NodeTypes.UNTIL):
        assert len(node.children)==2
        a = isATreeAcceptedByANonTerminalOfOurUVWGrammar(node.children[0], "Phi")
        b = isATreeAcceptedByANonTerminalOfOurUVWGrammar(node.children[1], "Psi")
        if a and b:
            return True
    if (nonterminalName == "NT" and node.value == NodeTypes.CONSTANT):
        return True

    # Extensions for Maidl's grammar
    if (nonterminalName == "Phi" and node.value == NodeTypes.UNTIL):
        assert len(node.children)==2
        a = False
        b = False
        if node.children[0].value == NodeTypes.AND:
            a = True
            ntS = list([])
            phi = None
            for c in node.children[0].children:
                if isATreeAcceptedByANonTerminalOfOurUVWGrammar(c, "NT"):
                    ntS.append(c)
                else:
                    if phi is None:
                        phi = c
                    else:
                        a = False
            a &= len(ntS)>0
        elif isATreeAcceptedByANonTerminalOfOurUVWGrammar(node.children[0],"NT"):
            # Special case: there is only one non-temporal conjunct left of the non-terminal.
            ntS = [node.children[0]]
            a = True
            phi = None
        if a:
            if node.children[1].value == NodeTypes.AND:
                if len(node.children[1].children)==2:
                    if len(ntS)==1:
                        b = node.children[1].children[0].isNegatedVersionOfOtherNNFNode(ntS[0])
                    else:
                        b = node.children[1].children[0].isNegatedVersionOfOtherNNFNode(Node(NodeTypes.AND,ntS))
                    b = b & isATreeAcceptedByANonTerminalOfOurUVWGrammar(node.children[1].children[1], "Phi")
        if a and b:
            return True

    # All other cases
    return False


def parse(formula):
    tokens = formula.split(" ")
    assert tokens[0]=="LTL"
    (result,rest) = recurseParse(tokens[1:])
    assert len(rest)==0
    return result


if __name__ == '__main__':
    formula = "LTL G | ! a X U ! b c"

    tree = parse(formula)
    print(tree)
    tree = simplifyTree(tree)
    print(tree)
    print(computeNNF(tree))
    print(isATreeAcceptedByANonTerminalOfOurUVWGrammar(tree, "Phi"))
