GUISynth - Reactive Synthesis of Graphical User Interface Glue Code
===================================================================
This repository contains a tool-chain to synthesize glue code for graphical user interfaces, written by Ruediger Ehlers and Keerthi Adabala. In particular, this repository contains:

1. A translator from LTL to universal very-weak automata
2. An explicit-state game solver for games build from environment assumptions and system specifications written as universal very weak automata
3. A so-called _orchestrator_ that reads a specification file together with a layout file for a Android cell phone application, trandlates the specifications to UVWs, runs the game solver and translates the computed strategy to Java code for Android applications if the specification is realizable.

The tools run under Linux, and a few packages should be installed to get everything running. Python in versions 2.X and 3.X are needed along with LaTeX/pdflatex, qmake, and a working C++ compiler chain (e.g., the GNU C++ compiler).

Please check out this repository with `git checkout <URL> --recursive`.


Setting up & Compiling instructions:
====================================

1. Download [spot](https://spot.lrde.epita.fr/):
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
   
5. Compile the [slugs](https://github.com/verifiablerobotics/slugs) reactive synthesis tool (for the benchmarks only):
   ```
   cd lib/slugs/src
   make
   cd ../../..
   ```
   
6. Check out and compile the [Strix](https://strix.model.in.tum.de/) reactive synthesis tool (for the benchmarks only):
   ```
   cd lib
   git clone https://gitlab.lrz.de/i7/strix.git
   cd strix
   git submodule init
   git submodule update
   make
   ```

   It is quite possible that additional packages have to be downloaded to get Strix to run. Details can be found [here](https://gitlab.lrz.de/i7/strix//blob/master/doc/BUILDING.md).

Running Some Experiments
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

Note that the computation of all experiments takes ~24 hours. You can add the parameter "-j2" or "-j4" after "make" to parallelize the computation to 2 or 4 cores, but the reported performance will become worse in this way. A memory limit of 6 GB per process is set, so that a sufficient amount of memory for all processes run in parallel should be available. The results are stored in the "experiments/ExplicitGameSolverEvaluation/main.pdf" file if the call to pdflatex succeeds.


Case study
====================================
An expense splitting Android application case study is available [here](https://github.com/tuc-es/ExpenseSplit), where the GUISynth framework was used to synthesize the GUI glue code. The project contains the specification and a script to use the GUISynth framework to resynthesize for a potentially modified specification.

We also provide the case study specifications in the [TLSF format](https://arxiv.org/abs/1604.02284) (as used by the [SyntCOMP](http://www.syntcomp.org/) reactive synthesis competition) [here](https://github.com/tuc-es/guisynth/raw/master/experiments/ExplicitGameSolverEvaluation/CostSplitGUISpecificationsTLSF.zip).
