#include "tools.hpp"
#include "binaryAntichain.hpp"
#include "bitvector.hpp"
#include "gameSolvingProblem.hpp"
#include <cstdlib>
#include <sstream>
#include <tuple>
#include <functional>
#include <string>
#include <algorithm>
#include "tests.hpp"

// How often should randomized tests be repeated?
constexpr unsigned int STANDARD_TEST_LENGTH = 100;

// Macro for running tests
#define TEST(a) { if (!(a)) { std::ostringstream ss; ss << "Test in line " << __LINE__ << " of source file " << __FILE__ << " failed"; throw ss.str(); } }

#define TEST_ANTICHAIN_EQUIVALENCE(a,b) { \
    if (!(a==b)) { \
        std::ostringstream ss; ss << "Test in line " << __LINE__ << " of source file " << __FILE__ << " failed - Antichains are different.\n"; \
        ss << "First antichain: "; \
        { BinaryAntichain<false>::iterator it(a); \
        while (it.next()) { \
            const BitVectorDynamic &thisTarget = it.element(); \
            ss << "("; \
            for (unsigned int i=0;i<thisTarget.getNofBits();i++) { \
                if (thisTarget.isBitSet(i)) ss << "," << i; \
            } \
            ss << ") "; \
        } } \
        ss << "\nSecond antichain: "; \
        { BinaryAntichain<false>::iterator it(b); \
        while (it.next()) { \
            const BitVectorDynamic &thisTarget = it.element(); \
            ss << "("; \
            for (unsigned int i=0;i<thisTarget.getNofBits();i++) { \
                if (thisTarget.isBitSet(i)) ss << "," << i; \
            } \
            ss << ") "; \
        } } \
        throw ss.str(); \
    } \
}

#define TEST_THROW(a) { bool passed=true; try { \
    { a } \
    passed = false; \
} catch (const char *c) {} catch (std::exception &e) {} catch (std::string e) {} if (!passed) { \
    std::ostringstream ss; ss << "Test in line " << __LINE__ << " of source file " << __FILE__ << " failed - Exception expected."; \
    throw ss.str(); \
} }

void runBitVectorTest() {
    std::cerr << "Running BitVectorTest\n";

    srand(123);

    // 0. Test the "countBits" feature of binaryAntichain
    TEST(BitVectorDynamic::countBitsSet(0)==0);
    TEST(BitVectorDynamic::countBitsSet(64)==1);
    TEST(BitVectorDynamic::countBitsSet(3)==2);
    TEST(BitVectorDynamic::countBitsSet(64+32+65536+1)==4);
    std::cout << "BitCount test A passed\n";

    // 0b. Test <= and >= operations
    {
        BitVectorDynamic first(4);
        first.setBit(4);
        first.setBit(7);
        BitVectorDynamic second(4);
        second.setBit(4);
        TEST(second<=first);
        TEST(first>=second);
        second.setBit(7);
        TEST(first==second);

        BitVectorDynamic third(4);
        BitVectorDynamic fourth(4);
        third.setBit(51);
        fourth.setBit(33);
        TEST(!(fourth<=first));
        TEST(!(third<=fourth));
        fourth.setBit(53);
        TEST(!(third<=fourth));
        fourth.setBit(51);
        TEST(third<=fourth);
        std::cout << "BitCount test A2 passed\n";
    }

    // 1. Test all operations by doing random checks and
    //    then counting the number of bits
    for (unsigned int i=0;i<STANDARD_TEST_LENGTH;i++) {
        uint64_t baseA = 0;
        uint64_t baseB = 0;
        BitVectorDynamic bv(2);

        std::vector<std::tuple<uint64_t,uint64_t,BitVectorDynamic> > stack;

        for (unsigned int j=0;j<64;j++) {
            unsigned int bit = rand() % 128;
            unsigned int op = rand() % 10;
            if (op==0) {
                if (bit<64) baseA |= ((uint64_t)1<<bit);
                else baseB |= ((uint64_t)1<<(bit-64));
                bv.setBit(bit);
            } else if (op==1) {
                if (bit<64) baseA &= ~((uint64_t)1<<bit);
                else baseB &= ~((uint64_t)1<<(bit-64));
                bv.clearBit(bit);
            } else if (op==2) {
                stack.push_back(std::make_tuple(baseA,baseB,bv) );
            } else if (op==3) {
                if (stack.size()>0) {
                    unsigned int pos = rand() % stack.size();
                    baseA |= std::get<0>(stack[pos]);
                    baseB |= std::get<1>(stack[pos]);
                    bv |= std::get<2>(stack[pos]);
                }
            } else if (op==4) {
                if (stack.size()>0) {
                    unsigned int pos = rand() % stack.size();
                    baseA &= std::get<0>(stack[pos]);
                    baseB &= std::get<1>(stack[pos]);
                    bv &= std::get<2>(stack[pos]);
                }
            } else if (op==5) {
                if (stack.size()>0) {
                    unsigned int pos = rand() % stack.size();
                    baseA ^= std::get<0>(stack[pos]);
                    baseB ^= std::get<1>(stack[pos]);
                    bv ^= std::get<2>(stack[pos]);
                }
            } else if (op==6) {
                if (stack.size()>0) {
                    unsigned int posA = rand() % stack.size();
                    unsigned int posB = rand() % stack.size();
                    baseA = std::get<0>(stack[posA]) | std::get<0>(stack[posB]);
                    baseB = std::get<1>(stack[posA]) | std::get<1>(stack[posB]);
                    bv = std::get<2>(stack[posA]) | std::get<2>(stack[posB]);
                }
            } else if (op==7) {
                if (stack.size()>0) {
                    unsigned int posA = rand() % stack.size();
                    unsigned int posB = rand() % stack.size();
                    baseA = std::get<0>(stack[posA]) & std::get<0>(stack[posB]);
                    baseB = std::get<1>(stack[posA]) & std::get<1>(stack[posB]);
                    bv = std::get<2>(stack[posA]) & std::get<2>(stack[posB]);
                }
            } else if (op==8) {
                if (stack.size()>0) {
                    unsigned int posA = rand() % stack.size();
                    unsigned int posB = rand() % stack.size();
                    baseA = std::get<0>(stack[posA]) ^ std::get<0>(stack[posB]);
                    baseB = std::get<1>(stack[posA]) ^ std::get<1>(stack[posB]);
                    bv = std::get<2>(stack[posA]) ^ std::get<2>(stack[posB]);
                }
            } else if (op==9) {
                bv.invert();
                baseA = ~baseA;
                baseB = ~baseB;
            }

        }
        TEST(baseA==bv.getChunk(0));
        TEST(baseB==bv.getChunk(1));
        TEST(BitVectorDynamic::countBitsSet(baseA)+BitVectorDynamic::countBitsSet(baseB)==bv.getNofBitsSet());

    }
    std::cout << "BitCount test B passed\n";
}


void runAntichainTests() {
    std::cerr << "Running Antichains Test\n";

    // Test 0: Trivial test
    {
        BinaryAntichain<false> antichain;
        BitVectorDynamic bv(2);
        bv.setBit(10);
        antichain.add(bv);
        TEST(antichain.size()==1);
        bv.setBit(20);
        antichain.add(bv);
        TEST(antichain.size()==1);
        std::cout << "Antichain test 1 passed.\n";
    }

    // Test 0: Trivial test - B
    {
        BinaryAntichain<true> antichain;
        BitVectorDynamic bv(2);
        bv.setBit(10);
        antichain.add(bv);
        TEST(antichain.size()==1);
        bv.setBit(20);
        antichain.add(bv);
        TEST(antichain.size()==1);
        std::cout << "Antichain test 1b passed.\n";
    }

    // Test 0c: Smallest elements must go
    {
        BinaryAntichain<true> antichain;

        std::vector<int> elements = {2,10,20,7};

        for (unsigned int a : elements) {
            for (unsigned int b : elements) {
                if (a!=b) {
                    BitVectorDynamic bv(2);
                    bv.setBit(a);
                    bv.setBit(b);
                    antichain.add(bv);
                }
             }
        }

        TEST(antichain.size()==6);

        for (unsigned int a : elements) {
            BitVectorDynamic bv(2);
            bv.setBit(a);
            antichain.add(bv);
        }

        TEST(antichain.size()==4);

        std::cout << "Antichain test 0c passed.\n";
    }


    // Test 0c: Largest elements must stay
    {
        BinaryAntichain<false> antichain;

        std::vector<int> elements = {2,10,20,7};

        for (unsigned int a : elements) {
            for (unsigned int b : elements) {
                if (a!=b) {
                    BitVectorDynamic bv(2);
                    bv.setBit(a);
                    bv.setBit(b);
                    antichain.add(bv);
                }
             }
        }

        TEST(antichain.size()==6);

        for (unsigned int a : elements) {
            BitVectorDynamic bv(2);
            bv.setBit(a);
            antichain.add(bv);
        }

        TEST(antichain.size()==6);

        std::cout << "Antichain test 0d passed.\n";
    }


    // Test 0b: EmptyIterator -- Should not crash
    {
        BinaryAntichain<false> antichain;
        auto it = BinaryAntichain<false>::iterator(antichain);
        while (it.next()) {
            // Do nothing.
        }
    }

    // Test F1 -- Intersection
    {
        std::vector<BinaryAntichain<false>> comp = {BinaryAntichain<false>({{1}},1),BinaryAntichain<false>({{2}},1)};
        BinaryAntichain<false> c = BinaryAntichain<false>::computeIntersection(comp,2);
        TEST_ANTICHAIN_EQUIVALENCE(c,BinaryAntichain<false>({{}},2));
    }

    // Test F2 -- Intersection
    {
        std::vector<BinaryAntichain<false>> comp = {BinaryAntichain<false>({{2,3}},1),BinaryAntichain<false>({{1,2}},1)};
        BinaryAntichain<false> c = BinaryAntichain<false>::computeIntersection(comp,5);
        TEST_ANTICHAIN_EQUIVALENCE(c,BinaryAntichain<false>({{2}},5));
    }

    // Test F3 -- Intersection
    {
        std::vector<BinaryAntichain<false>> comp = {BinaryAntichain<false>({{1,2,3,4,5},{0,2,3,4,5}},1),BinaryAntichain<false>({{0,1,3,4,5},{0,1,2,4,5}},1),BinaryAntichain<false>({{0,1,2,3,4},{0,1,2,3,5}},1)};
        BinaryAntichain<false> c = BinaryAntichain<false>::computeIntersection(comp,6);
        TEST_ANTICHAIN_EQUIVALENCE(c,BinaryAntichain<false>({{0,2,4},{1,2,4},{0,3,4},{1,3,4},{0,2,5},{1,2,5},{0,3,5},{1,3,5}},6));
    }

    std::cout << "Binary antichain test F passed\n";



    // Test A -- one bit per chain
    for (unsigned int i=0;i<STANDARD_TEST_LENGTH;i++) {
        BinaryAntichain<false> antichain;
        BitVectorDynamic allBits(2);
        for (unsigned int j=0;j<20;j++) {
            BitVectorDynamic bv(2);
            size_t nofBit = rand() % 128;
            bv.setBit(nofBit);
            antichain.add(bv);
            allBits.setBit(nofBit);
        }
        TEST(antichain.size()==allBits.getNofBitsSet());
    }
    std::cout << "Binary antichain test A passed\n";

    // Test B -- multichain
    for (unsigned int i=0;i<STANDARD_TEST_LENGTH;i++) {
        BinaryAntichain<false> antichain;
        for (unsigned int j=0;j<100;j++) {
            BitVectorDynamic bv(2);
            for (int k=0;k<rand()*3+1;k++) {
                size_t nofBit = rand() % 128;
                bv.setBit(nofBit);
            }
            antichain.add(bv);
        }
        TEST(antichain.size()<=100);
    }
    std::cout << "Binary antichain test B passed\n";

    // Test C -- Radical deletion
    for (unsigned int i=0;i<STANDARD_TEST_LENGTH;i++) {
        BinaryAntichain<false> antichain;
        for (unsigned int j=0;j<100;j++) {
            BitVectorDynamic bv(2);
            for (int k=0;k<rand()*3+1;k++) {
                size_t nofBit = rand() % 128;
                bv.setBit(nofBit);
            }
            antichain.add(bv);
        }
        BitVectorDynamic bv(2);
        for (unsigned int i=0;i<128;i++) bv.setBit(i);
        antichain.add(bv);
        TEST(antichain.size()==1);
    }
    std::cout << "Binary antichain test C passed\n";

    // Test D -- Go "full"
    {
        BinaryAntichain<false> antichain;
        for (unsigned int i=0;i<120;i++) {
            BitVectorDynamic bv(3);
            bv.setBit(i);
            antichain.add(bv);
        }
        for (unsigned int i=0;i<120;i++) {
            for (unsigned int j=0;j<120;j++) {
                BitVectorDynamic bv(3);
                bv.setBit(i);
                bv.setBit(j);
                antichain.add(bv);
            }
        }
        for (unsigned int i=0;i<120;i++) {
            for (unsigned int j=0;j<120;j++) {
                for (unsigned int k=0;k<10;k++) {
                    BitVectorDynamic bv(3);
                    bv.setBit(i);
                    bv.setBit(j);
                    bv.setBit(k+130);
                    antichain.add(bv);
                }
            }
        }
        TEST(antichain.size()==120*119/2*10);
    }
    std::cout << "Binary antichain test D passed\n";


    // Test E -- Equvality test
    {
        BinaryAntichain<false> antichainA;
        BinaryAntichain<false> antichainB;

        BitVectorDynamic bv1(3);
        bv1.setBit(3);
        bv1.setBit(4);
        antichainA.add(bv1);
        bv1.setBit(5);
        antichainB.add(bv1);
        TEST(!(antichainA==antichainB));

        antichainA.add(bv1);
        TEST(antichainA==antichainB);


        BitVectorDynamic bv3(3);
        bv3.setBit(103);
        bv3.setBit(104);
        antichainA.add(bv1);
        antichainB.add(bv1);
        TEST(antichainA==antichainB);
    }
    std::cout << "Binary antichain test E passed\n";


}

void runToolsTest() {

    std::cerr << "Running Tools Test\n";

    // Strip function
    TEST(strip(std::string("bla"))=="bla");
    TEST(strip(std::string("bla "))=="bla");
    TEST(strip(std::string(" bla"))=="bla");
    TEST(strip(std::string(" bla "))=="bla");
    TEST(strip(std::string(" \t "))=="");
    TEST(strip(std::string(" \ta "))=="a");
    TEST(strip(std::string("\n\ta \n"))=="a");
    TEST(strip(std::string(" \t\n\n   \t \n "))=="");
    std::cout << "StringStrip function test passed.\n";

    // Split
    TEST(checkStringVectorEquivalence(splitAndStrip("Hello 123 123"),{"Hello","123","123"}));
    TEST(checkStringVectorEquivalence(splitAndStrip("Hello 123   123 \n\n"),{"Hello","123","123"}));
    TEST(checkStringVectorEquivalence(splitAndStrip("   \n\n"),{}));
    std::cout << "StringSplit function test passed.\n";

    // ... Other functions ....
}


void runParsingTests() {
    std::cerr << "Running ParsingTests\n";

    TEST_THROW({
        const char *spec =
            "UVWBasedGame\n"
            "Input waste\n"
            "Output done\n"
            "Input X\n"
            "Input U\n"
            "Output U\n"
            "State Guarantees q0 initial\n"
            "State Guarantees q1 reject\n"
            "Transition Guarantees q0 TRUE q0\n"
            "Transition Guarantees q0 U q1\n"
            "Transition Guarantees q1 ! X q1\n";

        std::istringstream is(spec);
        GameSolvingProblem prob(is);
    });

    TEST_THROW({
        const char *spec =
            "UVWBasedGame\n"
            "Input waste\n"
            "Output done\n"
            "Input X\n"
            "Input U\n"
            "Output U2\n"
            "State Guarantees q0 initial\n"
            "State Guarantees q1 reject\n"
            "State Guarantees q0 reject\n"
            "Transition Guarantees q0 TRUE q0\n"
            "Transition Guarantees q0 U q1\n"
            "Transition Guarantees q1 ! X q1\n";

        std::istringstream is(spec);
        GameSolvingProblem prob(is);
    });

    // Test if assumption and guarantee rejecting states are added automatically.
    {
        std::istringstream is("UVWBasedGame\nInput notused\nOutput done\n");
        GameSolvingProblem prob(is);
        TEST(prob.assumptions.getNofStates()==1);
        TEST(prob.guarantees.getNofStates()==1);
        TEST(prob.assumptions.rejectingStates[0]);
        TEST(prob.guarantees.rejectingStates[0]);
    }

};







void runAllTests(bool extendedSet) {

    // All standard tests except for the ones below
    if (extendedSet) {
        runToolsTest();
        runBitVectorTest();
        runAntichainTests();

    }

    runParsingTests();

    // Final message
    if (extendedSet)
        std::cout << "============== All tests successfully ran ==============\n";
    else
        std::cout << "============== A selection of tests was successfully run ==============\n";
}
