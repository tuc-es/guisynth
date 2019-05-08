GUISynth - Reactive Synthesis of Graphical User Interface Glue Code
===================================================================
This repository contains a tool-chain to synthesize glue code for graphical user interfaces. In particular, it contains:

1. A translator from LTL to universal very-weak automata
2. An explicit-state game solver for games build from environment assumptions and system specifications written as universal very weak automata
3. A so-called _orchestrator_ that reads a specification from file together with a layout file for a Android cell phone application, trandlates the specifications to UVWs, runs the game solver and translates the computed strategy to Java code for Android applications if the specification is realizable.

The tools run under linux, and a few packages should be installed to get everything to run. Python2 and Python3 are needed along with LaTeX/pdflatex, qmake, and a working C++ compiler chain (e.g., the GNU C++ compiler).

Please check out this repository with `git checkout <URL> --resursive`.


Setting up & Compiling instructions:
====================================

1. Download spot:
   ```
   cd lib
   git clone https://gitlab.lrde.epita.fr/spot/spot.git
   cd spot
   git checkout b7cd47563259cda43d74926a7aa2b9f5eb770bac
   autoreconf -i
   ./configure --disable-devel
   make
   cd ../..
   ```
    
   Look for compulation errors along the way and download missing packages, etc.
   For instance, the "byacc", "bison", or "flex" packages may be missing. You may have to rerun the commands from "./configure" afterwards.
    
2. Compile LTLToPolish:
   ```
   cd tools/LTLToPolish
   qmake Tool.pro
   make
   cd ../..
   ```
    
3. Compile the game solver
   ```
   cd tools/ExplicitGameSolver/
   qmake Tool.pro
   make
   ```
    
   If this fails because "libpopcnt" is missing, then you did not check out the repository with the "--recursive" option. In this case, you need to run the following command from the main folder/directory of the repository:

   ```
   git submodule update --init --recursive
   ```
    
4. Get Timeout tool (for the benchmarks only):

   ```
   cd tools; wget https://raw.githubusercontent.com/pshved/timeout/edb59c93c167c15ede5ccc2795e1abee25ebf9b4/timeout; chmod +x timeout; cd ..
   ```
   
5. Compile slugs (for the benchmarks only):
   ```
   cd lib/slugs/src
   make
   cd ../../..
   ```
   
6. Check out and compile Strix (for the benchmarks only):
   ```
   cd lib
   git clone https://gitlab.lrz.de/i7/strix.git
   cd strix
   git submodule init
   git submodule update
   make
   ```

   It is quite possible that additional packages have to be downloaded to get Strix to run. Details can be found [https://gitlab.lrz.de/i7/strix//blob/master/doc/BUILDING.md here].

Running some Experiments
====================================
In order to rerun the original experiments (after compiling the game solver and the LTLToPolish tools), the following commands can be used:

```
cd experiments/ExplicitGameSolverEvaluation
./makeMakefile.py
make
pdflatex main.tex
pdflatex main.tex
cd ../..
```

Note that the computation of all experiments takes ~24 hours. You can add the parameter "-j2" or "-j4" after "make" to parallelize the computation, but the reported performance will become worse in this way. The results are stored in the "experiments/ExplicitGameSolverEvaluation/main.pdf" file if the call to pdflatex succeeds.
