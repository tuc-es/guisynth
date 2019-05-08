#include "bitvector.hpp"
#include "tests.hpp"
#include "gameSolvingProblem.hpp"
#include "explicitGameSolver.hpp"
#include <iostream>


int main(int nofArgs, const char **args) {
    try {
    
        // Parse parameters
        std::string inputFile = "";
        std::string stateSequenceTest = "";

        bool makeNicerStrategy = false;
        bool drawGraph = false;
        bool cutGraph = false;
        bool getNofPositions = false;
        for (int i=1;i<nofArgs;i++) {
            if (args[i][0]=='-') {
                std::string param = args[i];
                if (param=="--tests") {
                    runAllTests(false);
                    return 0;
                } else if (param=="--tests-all") {
                    runAllTests(true);
                    return 0;
                } else if (param=="--graph") {
                    drawGraph = true;
                } else if (param=="--cutgraph") {
                    cutGraph = true;
                } else if (param=="--nice") {
                    makeNicerStrategy = true;
                } else if (param=="--debugsequence") {
                    if (i>=nofArgs-1) throw "Error: Need sequence after '--debugsequence'";
                    stateSequenceTest = args[i+1];
                    i++;
                } else if (param=="--getNofPositions") {
                    getNofPositions = true;
                } else {
                    std::cerr << "Error: Did not understand parameter '" << param << "'.\n";
                    return 1;
                }
            } else {
                if (inputFile=="") {
                    inputFile = args[i];
                } else {
                    throw "Error: More than one input file name given.";
                }
            }
        }

        if (inputFile=="") {
            std::cerr << "Error: No input filename given.\n";
            return 1;
        }

        // Perform game solving.
        GameSolvingProblem problem(inputFile.c_str());

        ExplicitGameSolver solver(problem);

        // Debug
        if (stateSequenceTest!="") {
            solver.showForwardSequence(stateSequenceTest);
        } else {
            bool isRealizable = solver.safetyPreSolve(true);

            // If safety pre-solving worked, then do a full solving step.
            if (isRealizable) isRealizable = solver.solve();

            if (isRealizable && makeNicerStrategy) solver.makeNicerStrategy();

            if (drawGraph) {
                solver.gameGraphToDotOutput(true,cutGraph);
                if (isRealizable) {
                    std::cout << "/*\nREALIZABLE\n*/\n";
                } else {
                    std::cout << "/*\nUNREALIZABLE\n*/\n";
                }                
            } else {
                if (isRealizable) {
                    std::cout << "REALIZABLE\n";
                    solver.dumpStrategy();
                } else {
                    std::cout << "UNREALIZABLE\n";
                }
            }
            if (getNofPositions) std::cerr << "#Positions: " << solver.getNofPositions() << "\n";
        }


    } catch (const char *c) {
        std::cout.flush();
        std::cerr << "Error: " << c << std::endl;
        return 1;
    } catch (const std::string c) {
        std::cout.flush();
        std::cerr << "Error: " << c << std::endl;
        return 1;
    } catch (int a) {
        std::cout.flush();
        std::cerr << "An internal error occurred.\n";
        return 1;
    }

}
