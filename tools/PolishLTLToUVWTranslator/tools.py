import os, sys
# Tools



def pickOneFromEachSet(subsets):
    if len(subsets)<2:
        return subsets
    all = []
    for a in subsets[0]:
        for b in pickOneFromEachSet(subsets[1:]):
            all.append([a]+b)
    return all
