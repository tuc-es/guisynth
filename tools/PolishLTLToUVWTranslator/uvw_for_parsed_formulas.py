#!/usr/bin/env python3
import parser
import uvwBuilder
import sys

# Main
if __name__ == '__main__':

	if len(sys.argv)<2:
		print("Error: Need a formula file name!",file=sys.stderr)
		sys.exit(1)

	with open(sys.argv[1],"r") as inFile:
		formulaTxt = inFile.readlines()

    # Assuming the LTL specification is for a never claim
	
	for line in formulaTxt:
		line = line.strip()
		if len(line)>0:
			assert line[0:4]=="LTL "
			#line = "LTL ! "+line[4:]
			
			formulaNode = parser.computeNNF(parser.simplifyTree(parser.elimImplies(parser.parse(line))))
			assert parser.isATreeAcceptedByANonTerminalOfOurUVWGrammar(formulaNode,"Phi")

            # formulaTxt = "LTL F && c F && b F a" ----> Does not work according to the grammar
			print("================Constructing UVW================",file=sys.stderr)
			uvw = uvwBuilder.constructUVW(formulaNode)
			print("================Original Automaton================",file=sys.stderr)
    		# print(uvw)
			uvw.removeUnreachableStates()
			print("================Removed Unreachable States================",file=sys.stderr)
			# print(uvw)
			uvw.simulationBasedMinimization()
			uvw.mergeEquivalentlyReachableStates()
			uvw.removeForwardReachableBackwardSimulatingStates()
			uvw.removeUnreachableStates()

    		# print("================Original Automaton================")

    		# Monolithic?
		if len(sys.argv)>2 and sys.argv[2]=="--split":
			for a in uvw.decomposeIntoSimpleChains():
				print(a.toNeverClaim())
				print("")
		else:
			print(uvw.toNeverClaim())
			
				
				
			
