#ifndef __TOOLS_HPP__
#define __TOOLS_HPP__

#include <string>
#include <sstream>
#include <iostream>
#include <vector>

inline std::string strip(std::string in) {
    size_t left = 0;
    while (in.size()>left) {
        switch (in[left]) {
        case ' ':
        case '\n':
        case '\t':
            left++;
            break;
        default:
            {
                size_t right = in.size();
                while (right>left) {
                    switch (in[right-1]) {
                    case ' ':
                    case '\n':
                    case '\t':
                        right--;
                        break;
                    default:
                        return in.substr(left,right-left);
                    }
                }
                return "";
            }
        }
    }
    return "";
}


inline std::vector<std::string> splitAndStrip(std::string inParts, char delimiter = ' ') {
    std::vector<std::string> parts;
    inParts = strip(inParts);
    while (inParts!="") {
        size_t index = inParts.find(delimiter);
        parts.push_back(strip(inParts.substr(0,index)));
        if (index==std::string::npos) return parts;
        inParts = strip(inParts.substr(index+1,std::string::npos));
    }
    return parts;
}


inline bool checkStringVectorEquivalence(const std::vector<std::string> &a, const std::vector<std::string> &b) {
    if (a.size()!=b.size()) return false;
    for (unsigned int i=0;i<a.size();i++) {
        if (a[i]!=b[i]) return false;
    }
    return true;
}

inline std::string toString(std::vector<bool> const &a) {
    std::ostringstream o;
    for (auto i : a) {
        if (i) o << "1"; else o << "0";
    }
    return o.str();
}

inline std::string toString(std::vector<int> const &a) {
    std::ostringstream o;
    bool first = false;
    for (auto i : a) {
        if (first) {
            first = false;
        } else {
            o << ",";
        }
        o << i;
    }
    return o.str();
}

namespace std {
    template<> struct hash<std::vector<int> > {
    public:
        size_t operator()(const std::vector<int> &vec) const  {
            std::size_t hash = 1337;
            for (int k : vec) {
                hash ^= k + 0x1337 + (k >> 7);
            }
            return hash;
        }
    };
}



#endif
