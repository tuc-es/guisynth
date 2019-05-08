#ifndef __BINARY_ANTICHAIN_HPP__
#define __BINARY_ANTICHAIN_HPP__

#include <vector>
#include <list>
#include <limits>
#include <algorithm>
#include "pareto_enumerator_bool.hpp"
#include "bitvector.hpp"

class BinaryAntichainBase {
protected:
    std::vector<std::list<BitVectorDynamic > > bitSetsByLength;

    bool findAntichainElement(std::list<BitVectorDynamic > &list, BitVectorDynamic &bitset) {
        for (std::list<BitVectorDynamic >::iterator it = list.begin();it!=list.end();) {
            if (bitset==*it) return true;
        }
        return false;
    }

public:

    BinaryAntichainBase() {};

    /* Iterator */
    class iterator {
        const BinaryAntichainBase &chain;
        int currentSize;
        std::list<BitVectorDynamic>::const_iterator it;
    public:
        iterator(const BinaryAntichainBase &a) : chain(a) { currentSize = -1; }
        bool next() {
            if (currentSize==-1) {
                currentSize = 0;
                if (chain.bitSetsByLength.size()==0) return false;
                it = chain.bitSetsByLength[currentSize].begin();
            } else {
                it++;
            }
            while (true) {
                if (it==chain.bitSetsByLength[currentSize].end()) {
                    currentSize++;
                    if ((unsigned int)currentSize>=chain.bitSetsByLength.size()) return false;
                    it = chain.bitSetsByLength[currentSize].begin();
                } else {
                    return true;
                }
            }
        }
        const BitVectorDynamic &element() const {
            return *it;
        }
    };



    void addWhenBitvectorIsKnownToBeIncomparableToAllExistingElementsInTheAntichain(const BitVectorDynamic &bv) {
        // Make the vector large enough
        size_t nofBitsSet = bv.getNofBitsSet();
        if (bitSetsByLength.size()<nofBitsSet+1) bitSetsByLength.resize(nofBitsSet+1);

        // Finally store
        bitSetsByLength[nofBitsSet].push_back(bv);
    }




    size_t size() {
        unsigned int sum = 0;
        for (const auto &it1 : bitSetsByLength) {
            sum += it1.size();
        }
        return sum;
    }

    /**
     * @brief add Adds a clause to the clause set. Warning: Clause is modified (by sorting the literals) along the way.
     * @param clause The clause to be added.
     */
    /*bool checkSubsumption(std::vector<int> &clause, std::list<std::vector<int> > &list) {
        const int maxINT = std::numeric_limits<int>::max();
        clause.push_back(maxINT);
        for (std::list<std::vector<int> >::iterator it = list.begin();it!=list.end();) {
            std::vector<int>::iterator it2 = clause.begin();
            for (auto lit : *it) {
                while (*it2<lit) {
                    it2++;
                }
                if (*it2==maxINT) goto continueOuter;
                if (*it2==lit) {
                    it2++;
                } else {
                    goto continueOuter;
                }
            }
            // Ok, found subsumption.
            clause.pop_back();
            //std::cerr << "(M3)";
            return true;
        continueOuter:
            it++;
        }
        clause.pop_back();
        return false;
    }


public:

    void addWhileKnowingThatTheNewClauseIsNotSubsumed(std::vector<int> &clause) {
        std::sort(clause.begin(),clause.end());
        for (unsigned int i=clause.size()+1;i<clausesByLength.size();i++) {
            //std::cerr << "(";
            //addAfterItIsClearThatTheNewClauseCannotBeSubset(clause,clausesByLength[i]);
            //std::cerr << ")";
        }
        if (clausesByLength.size()<=clause.size()) clausesByLength.resize(clause.size()+1);
        //clausesByLength[clause.size()].push_back(clause);

    }

    void add(std::vector<int> &clause) {
        // Returns if something has been added
        //std::cerr << ".";
        std::sort(clause.begin(),clause.end());
        for (unsigned int i=0;i<std::min(clause.size(),clausesByLength.size());i++) {
            //std::cerr << "[";
            if (checkSubsumption(clause,clausesByLength[i])) {
                //std::cerr << "CONTAINED!\n";
                return;
            }
            //std::cerr << "]";
        }
        if (clausesByLength.size()>clause.size()) {
            //if (std::find(clausesByLength[clause.size()].begin(), clausesByLength[clause.size()].end(), clause)!=clausesByLength[clause.size()].end()) return;
            if (findClause(clausesByLength[clause.size()],clause)) {
                //std::cerr << "CONTAINED!\n";
                return;
            }
        }
        for (unsigned int i=clause.size()+1;i<clausesByLength.size();i++) {
            //std::cerr << "(";
            addAfterItIsClearThatTheNewClauseCannotBeSubset(clause,clausesByLength[i]);
            //std::cerr << ")";
        }
        if (clausesByLength.size()<=clause.size()) clausesByLength.resize(clause.size()+1);
        clausesByLength[clause.size()].push_back(clause);
    }


    std::vector<std::list<std::vector<int> > > const &getClauses() const { return clausesByLength; }
    */
};


template<bool b> class BinaryAntichain {
    template<bool d> friend inline bool operator == (const BinaryAntichain<d> &one, const BinaryAntichain<d> &other);
};

template<> class BinaryAntichain<false> : public BinaryAntichainBase {
public:

    template<bool b> friend inline bool operator == (const BinaryAntichain<b> &one, const BinaryAntichain<b> &other);

    bool hasElementGreaterThanOrEqualTo(const BitVectorDynamic &bv) const {
        unsigned int nofBitsSet = bv.getNofBitsSet();
        for (unsigned int i=nofBitsSet;i<bitSetsByLength.size();i++) {
            for (const auto &it : bitSetsByLength[i]) {
                if (it >= bv) return true;
            }
        }
        return false;
    }

    static BinaryAntichain<false> computeIntersection(std::vector<BinaryAntichain<false>> const &components, unsigned int nofBits) {

        auto oracle = [components](const std::vector<bool> &point ) {
            BitVectorDynamic bv((point.size()+BitVectorDynamic::nofBitsPerElement-1)/BitVectorDynamic::nofBitsPerElement);
            for (unsigned int i=0;i<point.size();i++) if (!(point[i])) bv.setBit(i);
            for (const auto &it : components) {
                if (!(it.hasElementGreaterThanOrEqualTo(bv))) return false;
            }
            return true;
        };

        std::list<std::vector<bool> > optimalCases = paretoenumeratorBool::enumerateParetoFront(oracle,nofBits);

        // Translate back to antichain
        BinaryAntichain<false> antichain;
        for (auto &it : optimalCases) {
            BitVectorDynamic bv((nofBits+BitVectorDynamic::nofBitsPerElement-1)/BitVectorDynamic::nofBitsPerElement);
            for (unsigned int i=0;i<it.size();i++) {
                if (!(it[i])) bv.setBit(i); // Complement because the pareto front enumerator worked on complemented elements
            }
            antichain.addWhenBitvectorIsKnownToBeIncomparableToAllExistingElementsInTheAntichain(bv);
        }

        return antichain;

    }

    BinaryAntichain computeNewChainWithClearedBit(unsigned int whichBit) const {
        BinaryAntichain ret;
        BinaryAntichain::iterator it(*this);
        while (it.next()) {
            BitVectorDynamic thisTarget = it.element();
            thisTarget.clearBit(whichBit);
            ret.add(thisTarget);
        }
        return ret;
    }

    void add(const BinaryAntichain &ac) {
        BinaryAntichain::iterator it(ac);
        while (it.next()) {
            const BitVectorDynamic &thisTarget = it.element();
            add(thisTarget);
        }
    }

    bool add(const BitVectorDynamic &bv) {
        size_t nofBitsSet = bv.getNofBitsSet();

        // Check if subsumed
        for (unsigned int i=nofBitsSet;i<bitSetsByLength.size();i++) {
            for (const auto &it : bitSetsByLength[i]) {
                if (it >= bv) return false;
            }
        }

        // Remove subsumed
        unsigned int limit = std::min(nofBitsSet,bitSetsByLength.size());
        for (unsigned int i=0;i<limit;i++) {
            std::list<BitVectorDynamic>::iterator it = bitSetsByLength[i].begin();
            while (it!=bitSetsByLength[i].end()) {
                if (*it <= bv) {
                    std::list<BitVectorDynamic>::iterator it2 = it;
                    it2++;
                    bitSetsByLength[i].erase(it);
                    it = it2;
                } else {
                    it++;
                }
            }
        }

        // Make the vector large enough
        if (bitSetsByLength.size()<nofBitsSet+1) bitSetsByLength.resize(nofBitsSet+1);

        // Finally store
        bitSetsByLength[nofBitsSet].push_back(bv);
        return true;
    }


    BinaryAntichain<false>() {};
    inline BinaryAntichain<false>(const std::vector<std::vector<int> > chainData, unsigned int nofBitvectorWords) {
        for (auto &cd : chainData) {
            BitVectorDynamic bv(nofBitvectorWords);
            for (auto m : cd) {
                if (m<0) throw "Error using BinaryAntichain constructor from vector of vector (A)";
                if (m>(int)(nofBitvectorWords*BitVectorDynamic::nofBitsPerElement)) throw "Error using BinaryAntichain constructor from vector of vector (B)";
                bv.setBit(m);
            }
            add(bv);
        }
    }

};



template<> class BinaryAntichain<true> : public BinaryAntichainBase {
public:

    template<bool b> friend inline bool operator == (const BinaryAntichain<b> &one, const BinaryAntichain<b> &other);

    bool hasElementLessThanOrEqualTo(const BitVectorDynamic &bv) const {
        unsigned int nofBitsSet = bv.getNofBitsSet();
        for (unsigned int i=nofBitsSet;i<bitSetsByLength.size();i++) {
            for (const auto &it : bitSetsByLength[i]) {
                if (it <= bv) return true;
            }
        }
        return false;
    }


    void add(const BinaryAntichain &ac) {
        BinaryAntichain::iterator it(ac);
        while (it.next()) {
            const BitVectorDynamic &thisTarget = it.element();
            add(thisTarget);
        }
    }

    bool add(const BitVectorDynamic &bv) {
        size_t nofBitsSet = bv.getNofBitsSet();

        // Check if subsumed
        for (unsigned int i=0;i<std::min(nofBitsSet+1,bitSetsByLength.size());i++) {
            for (const auto &it : bitSetsByLength[i]) {
                if (it <= bv) return false;
            }
        }

        // Remove subsumed
        for (unsigned int i=nofBitsSet+1;i<bitSetsByLength.size();i++) {
            std::list<BitVectorDynamic>::iterator it = bitSetsByLength[i].begin();
            while (it!=bitSetsByLength[i].end()) {
                if (*it >= bv) {
                    std::list<BitVectorDynamic>::iterator it2 = it;
                    it2++;
                    bitSetsByLength[i].erase(it);
                    it = it2;
                } else {
                    it++;
                }
            }
        }

        // Make the vector large enough
        if (bitSetsByLength.size()<nofBitsSet+1) bitSetsByLength.resize(nofBitsSet+1);

        // Finally store
        bitSetsByLength[nofBitsSet].push_back(bv);
        return true;
    }


    BinaryAntichain<true>() {};
    inline BinaryAntichain<true>(const std::vector<std::vector<int> > chainData, unsigned int nofBitvectorWords) {
        for (auto &cd : chainData) {
            BitVectorDynamic bv(nofBitvectorWords);
            for (auto m : cd) {
                if (m<0) throw "Error using BinaryAntichain constructor from vector of vector (A)";
                if (m>(int)(nofBitvectorWords*BitVectorDynamic::nofBitsPerElement)) throw "Error using BinaryAntichain constructor from vector of vector (B)";
                bv.setBit(m);
            }
            add(bv);
        }
    }

};




template<bool direction> inline bool operator != (const BinaryAntichain<direction> &one, const BinaryAntichain<direction> &other) {
    return !(one==other);
}

template<bool direction> inline bool operator == (const BinaryAntichain<direction> &one, const BinaryAntichain<direction> &other) {

    unsigned int minSize = std::min(one.bitSetsByLength.size(),other.bitSetsByLength.size());

    for (unsigned int i=other.bitSetsByLength.size();i<one.bitSetsByLength.size();i++) {
        if (one.bitSetsByLength[i].size()!=0) return false;
    }

    for (unsigned int i=one.bitSetsByLength.size();i<other.bitSetsByLength.size();i++) {
        if (other.bitSetsByLength[i].size()!=0) return false;
    }

    for (unsigned int i=0;i<minSize;i++) {
        if (other.bitSetsByLength[i].size()!=one.bitSetsByLength[i].size()) return false;
        for (auto &it1 : one.bitSetsByLength[i]) {
            bool found = false;
            for (auto &it2 : other.bitSetsByLength[i]) {
                if (it1==it2) found = true;
            }
            if (!found) return false;
        }
    }
    return true;

}




#endif
