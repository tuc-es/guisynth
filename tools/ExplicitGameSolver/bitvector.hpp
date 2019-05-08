#ifndef __BIT_VECTOR_HPP___
#define __BIT_VECTOR_HPP___

#include <cassert>
#include <iostream>
#include <cstring>
#include "libpopcnt.h"

class BitVectorBase {
public:
    size_t lng;
    uint64_t *data;
};

class BitVectorDynamic;
typedef BitVectorDynamic BitVectorDynamicNoBitCount;



class BitVectorDynamic : public BitVectorBase {
public:

    static constexpr unsigned int nofBitsPerElement = 64;

    inline BitVectorDynamic(size_t _lng) {
        lng = _lng;
        data = new uint64_t[lng];
        memset(data,0,sizeof(uint64_t)*lng);
    }
    inline BitVectorDynamic() {
        lng = 0;
        data = 0;
    }

    inline BitVectorDynamic(BitVectorDynamicNoBitCount &&other) {
        lng = std::move(other.lng);
        data = std::move(other.data);
        other.data = 0;
    }

    inline ~BitVectorDynamic() {
        if (data!=0) delete[] data;
    }

    inline void setNofBits(unsigned int nofBits) {
        if (data!=0) delete[] data;
        lng = (nofBits+63)/64;
        data = new uint64_t[lng];
        memset(data,0,sizeof(uint64_t)*lng);
    }

    inline void inplaceOrLargerBitvectorAgainstSmallerBitvector(const BitVectorDynamic &other) {
        for (unsigned int i=0;i<other.lng;i++) {
            data[i] |= other.data[i];
        }
    }

    inline BitVectorDynamicNoBitCount computeShorterCopy(unsigned int nofBits) const {
        BitVectorDynamicNoBitCount copy(*this);
        copy.data[nofBits/64] &= (0xFFFFFFFFFFFFFFFF >> (64-(nofBits % 64)));
        return copy;
    }

    static inline BitVectorDynamic fromBitvectorDynamic(const BitVectorDynamic &other) {
        BitVectorDynamic b;
        b.lng = other.lng;
        b.data = new uint64_t[b.lng];
        memcpy(b.data,other.data,sizeof(uint64_t)*b.lng);
        return b;
    }

    inline BitVectorDynamic(const BitVectorDynamicNoBitCount &other) {
        lng = other.lng;
        data = new uint64_t[lng];
        memcpy(data,other.data,sizeof(uint64_t)*lng);
    }

    inline BitVectorDynamicNoBitCount& operator=(const BitVectorDynamicNoBitCount &other) {
        if (data!=0) delete[] data;
        lng = other.lng;
        data = new uint64_t[lng];
        memcpy(data,other.data,sizeof(uint64_t)*lng);
        return *this;
    }

    inline BitVectorDynamicNoBitCount& operator=(BitVectorDynamicNoBitCount &&other) {
        if (data!=0) delete[] data;
        lng = std::move(other.lng);
        data = std::move(other.data);
        other.data = 0;
        return *this;
    }

    inline static size_t countBitsSet(uint64_t data) {
        return popcnt64(data);
    }

    inline size_t getNofBitsSet() const {
        size_t val = 0;
        for (unsigned int i=0;i<lng;i++) {
            val += popcnt64(data[i]);
        }
        return val;
    }

    inline BitVectorDynamicNoBitCount operator ^ (const BitVectorDynamicNoBitCount &other) const {
        BitVectorDynamicNoBitCount newOne;
        newOne.lng = lng;
        newOne.data = new uint64_t[lng];
        for (unsigned int i=0;i<lng;i++) {
            newOne.data[i] = data[i] ^ other.data[i];
        }
        return newOne;
    }

    inline BitVectorDynamicNoBitCount operator & (const BitVectorDynamicNoBitCount &other) const {
        BitVectorDynamicNoBitCount newOne;
        newOne.lng = lng;
        newOne.data = new uint64_t[lng];
        for (unsigned int i=0;i<lng;i++) {
            newOne.data[i] = data[i] & other.data[i];
        }
        return newOne;
    }


    inline  BitVectorDynamicNoBitCount operator | (const  BitVectorDynamicNoBitCount &other) const {
        BitVectorDynamicNoBitCount newOne;
        newOne.lng = lng;
        newOne.data = new uint64_t[lng];
        for (unsigned int i=0;i<lng;i++) {
            newOne.data[i] = data[i] | other.data[i];
        }
        return newOne;
    }

    inline  BitVectorDynamicNoBitCount& operator |= (const  BitVectorDynamicNoBitCount &other) {
        for (unsigned int i=0;i<lng;i++) {
            data[i] |= other.data[i];
        }
        return *this;
    }
    inline  BitVectorDynamicNoBitCount& operator ^= (const  BitVectorDynamicNoBitCount &other) {
        for (unsigned int i=0;i<lng;i++) {
            data[i] ^= other.data[i];
        }
        return *this;
    }

    inline  BitVectorDynamicNoBitCount& operator &= (const  BitVectorDynamicNoBitCount &other) {
        for (unsigned int i=0;i<lng;i++) {
            data[i] &= other.data[i];
        }
        return *this;
    }

    friend inline bool operator == (const  BitVectorDynamicNoBitCount &one, const BitVectorDynamicNoBitCount &other);
    friend inline bool operator >= (const  BitVectorDynamicNoBitCount &one, const BitVectorDynamicNoBitCount &other);
    friend inline bool operator <= (const  BitVectorDynamicNoBitCount &one, const BitVectorDynamicNoBitCount &other);

    inline void clear() {
        memset(data,0,sizeof(uint64_t)*lng);
    }

    inline void fill() {
        memset(data,255,sizeof(uint64_t)*lng);
    }

    inline void setBit(int pos) {
        size_t word = pos/64;
        size_t bit = pos % 64;
        size_t mask = ((uint64_t)1 << bit);
        *((data+word)) |= mask;
    }

    inline void clearBit(int pos) {
        size_t word = pos/64;
        size_t bit = pos % 64;
        size_t mask = ((uint64_t)1 << bit);
        *((data+word)) &= ~mask;
    }

    inline bool isBitSet(unsigned int pos) const {
        size_t word = pos/64;
        size_t bit = pos % 64;
        size_t mask = ((uint64_t)1 << bit);
        size_t dataBefore = *((data+word));
        return ((dataBefore & mask)!=0);
    }

    inline size_t getHash() const {
        std::hash<uint64_t> baseHasher;
        size_t base = 0;
        for (unsigned int i=0;i<lng;i++) {
            base = (base << 13) + baseHasher(data[i])+0xcafe1337;
        }
        return base;
    }

    inline bool isSubsetOf(const BitVectorDynamicNoBitCount &other) const {
        for (unsigned int i=0;i<lng;i++) {
            if (data[i] & (~(other.data[i]))) return false;
        }
        return true;
    }

    inline unsigned int getMinBitSet() const {
        for (unsigned int i=0;i<lng;i++) {
            long pos = __builtin_ffsl(data[i]);
            if (pos!=0) {
                return pos-1+64*i;
            }
        }
        return 64*lng;
    }

    inline unsigned int getNofBits() const {
        return lng*64;
    }

    inline uint64_t getChunk(int pos) const {
        return data[pos];
    }

    inline void invert() {
        for (unsigned int i=0;i<lng;i++) {
            data[i] = ~data[i];
        }
    }

    inline bool completementIntersectsWith(const BitVectorDynamicNoBitCount &other) {
        for (unsigned int i=0;i<lng;i++) {
            if (~data[i] & other.data[i]) return true;
        }
        return false;
    }


};

inline BitVectorDynamic &fromBitVectorDynamicNoBitCount(BitVectorDynamicNoBitCount &other) {
    return other;
}

inline bool operator ==(const BitVectorDynamic &one, const BitVectorDynamic &other) {
    return memcmp(one.data,other.data,one.lng*sizeof(uint64_t))==0;
}

inline bool operator >=(const BitVectorDynamic &one, const BitVectorDynamic &other) {
    assert(one.lng==other.lng);
    for (unsigned int i=0;i<one.lng;i++) {
        uint64_t a = ~one.data[i] & other.data[i];
        if (a>0) return false;
    }
    return true;
}

inline bool operator <=(const BitVectorDynamic &one, const BitVectorDynamic &other) {
    return other >= one;
}

namespace std {
    template<> struct hash<BitVectorDynamic> {
        inline std::size_t operator()(const BitVectorDynamic& d) const {
            return d.getHash();
        }
    };
}




#endif
