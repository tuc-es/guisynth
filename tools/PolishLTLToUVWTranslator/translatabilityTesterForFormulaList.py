#!/usr/bin/env python3
import parser
import sys
import uvwBuilder

# Main
if __name__ == '__main__':

	if len(sys.argv)<2:
		print("Error: Need a formula file name!",file=sys.stderr)
		sys.exit(1)

	with open(sys.argv[1],"r") as inFile:
		formulaTxt = inFile.readlines()

    # Assuming the LTL specification is for a never claim
	nofFormulas = 0
	nofFormulasInGrammar = 0
	for line in formulaTxt:
		line = line.strip()
		if len(line)>0:
			assert line[0:4]=="LTL "

            # formulaTxt = "LTL F && c F && b F a" ----> Does not work according to the grammar
			formulaNode = parser.computeNNF(parser.simplifyTree(parser.elimImplies(parser.parse(line))))
			if parser.isATreeAcceptedByANonTerminalOfOurUVWGrammar(formulaNode,"Phi"):
				print(line)
				nofFormulasInGrammar +=1


                # print("================Constructing UVW================",file=sys.stderr)
				uvw = uvwBuilder.constructUVW(formulaNode)
                # print("================Original Automaton================",file=sys.stderr)
                #print(uvw)
				uvw.removeUnreachableStates()
                # print("================Removed Unreachable States================",file=sys.stderr)
                #print(uvw)

				uvw.simulationBasedMinimization()
				uvw.mergeEquivalentlyReachableStates()
				uvw.removeForwardReachableBackwardSimulatingStates()
				uvw.removeUnreachableStates()


                #print("Not parsed:",formulaNode.toPolishLTL())
			nofFormulas += 1



	print("Number of LTL formulas accepted by our grammar:",nofFormulasInGrammar,"out of",nofFormulas)
