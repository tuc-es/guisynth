#include <iostream>
#include <cassert>
#include <cstdlib>
// #include "spot/misc/game.hh"
#include "spot/tl/formula.hh"
#include "spot/tl/parse.hh"
#include "spot/parsetl/parsetl.hh"
#include "spot/tl/environment.hh"

using namespace spot;

void printPolish(const formula &f) {

    op o = f.kind();

    switch (o) {
    case op::ff:
        std::cout << " 0";
        break;
    case op::tt:
        std::cout << " 1";
        break;
    case op::ap:
        std::cout << " " << f;
        break;
    case op::And:
        for (unsigned int i=0;i<f.size()-1;i++) std::cout << " &";
        for (unsigned int i=0;i<f.size();i++) printPolish(f[i]);
        break;
    case op::Or:
        for (unsigned int i=0;i<f.size()-1;i++) std::cout << " |";
        for (unsigned int i=0;i<f.size();i++) printPolish(f[i]);
        break;
    case op::Not:
        std::cout << " !";
        printPolish(f[0]);
        break;
    case op::F:
        std::cout << " F";
        printPolish(f[0]);
        break;
    case op::G:
        std::cout << " G";
        printPolish(f[0]);
        break;
    case op::U:
        std::cout << " U";
        printPolish(f[0]);
        printPolish(f[1]);
        break;
    case op::W:
        std::cout << " W";
        printPolish(f[0]);
        printPolish(f[1]);
        break;
    case op::R:
        std::cout << " R";
        printPolish(f[0]);
        printPolish(f[1]);
        break;
    case op::X:
        std::cout << " X";
        printPolish(f[0]);
        break;
    case op::Implies:
        std::cout << " ->";
        printPolish(f[0]);
        printPolish(f[1]);
        if (f.size()!=2) throw "Error: Assuming that every implication operator has exactly two operands.";
        break;
    case op::Xor:
        for (unsigned int i=0;i<f.size()-1;i++) std::cout << " ^";
        for (unsigned int i=0;i<f.size();i++) printPolish(f[i]);
        break;
    default:
        std::cerr << "Error: Unsupported operands.";
        throw 0;
    }
}

int main(int argc, char** argv)
{
    (void)argv;
    (void)argc;
    try {

      std::string input;
      while (std::getline(std::cin,input)) {
          //const char *input = argv[1];


          spot::environment& env(spot::default_environment::instance());

          auto pf = spot::parse_infix_psl(input.c_str(), env, false);
          int exit_code = pf.format_errors(std::cerr);
          if ((exit_code)==0)  {
            formula f = pf.f;
            std::cout << "LTL";
            printPolish(f);
            std::cout << std::endl;
          } else {
              return 1;
          }
      }
    } catch (const char *error) {
        std::cerr << error << std::endl;
        return 1;
    }
}
