#include "pareto_enumerator_bool.hpp"
#include <iostream>
#include <set>

/*
 * This is
 *   pareto_enumerator_bool.cpp
 * that is part of the ParetoFrontEnumerationAlgorithm library, available from
 *   https://github.com/progirep/ParetoFrontEnumerationAlgorithm
 *
 * Is ia a library for enumerating all elements of a Pareto front for a
 * multi-criterial optimization problem for which all optimization objectives
 * have a finite range.
 *
 * The library and all of its files are distributed under the following license:
 *
 * -----------------------------------------------------------------------------
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2015-2016 Ruediger Ehlers
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

namespace paretoenumeratorBool {

    inline bool vectorOfBoolIsSmaller(const std::vector<bool>& a, const std::vector<bool> &b) {
        const size_t size = a.size();
        for (size_t i = 0;i<size;i++) {
            if (!(b[i]) && a[i]) return false;
            if (b[i]!=a[i]) {
                // We continue the outer loop now here as this is
                // faster than storing whether a smaller
                // element has been found in a flag.
                for (i++;i<size;i++) {
                    if (!(b[i]) && a[i]) return false;
                }
                return true;
            }
        }
        return false;
    }

    inline bool vectorOfBoolIsLeq(const std::vector<bool>& a, const std::vector<bool> &b) {
        const size_t size = a.size();
        for (size_t i = 0;i<size;i++) {
            if (!(b[i]) && a[i]) return false;
        }
        return true;
    }

    /**
     * @brief Removes all dominating elements from a set of search space points
     * @param input The initial set of points
     * @return The cleaned set of points
     */
    std::list<std::vector<bool> > cleanParetoFront(const std::list<std::vector<bool> > &input) {
        std::set<std::vector<bool> > cleanedElements;
        for (auto const &it : input) {
            bool foundSmaller = false;
            for (const auto &it2 : input) {
                if (vectorOfBoolIsSmaller(it,it2)) {
                    foundSmaller = true;
                    break;
                }
            }
            if (!foundSmaller) cleanedElements.insert(it);
        }
        return std::list<std::vector<bool>>(cleanedElements.begin(),cleanedElements.end());
    }


    /**
     * @brief A class that buffers negative results from the feasibility function so that no
     * redundant calls are made to it.
     *
     * Dominated points are removed from the buffer
     */
    class NegativeResultBuffer {
        std::list<std::vector<bool> > oldValueBuffer;
    public:
        bool isContained(const std::vector<bool> &data) {
            for (auto const &a : oldValueBuffer) {
                if (vectorOfBoolIsLeq(data,a)) return true;
            }
            return false;
        }

        void addPoint(const std::vector<bool> &data) {
            for (auto it = oldValueBuffer.begin();it!=oldValueBuffer.end();) {
                if (vectorOfBoolIsLeq(*it,data)) {
                    it = oldValueBuffer.erase(it);
                } else {
                    it++;
                }
            }
            oldValueBuffer.push_back(data);
        }
    };


    /**
     * @brief Main function of the pareto front element enumeration algorithm
     * @param fn the feasibility function
     * @param limits the upper and lower bounds of the objective values. In every pair, the minimal value comes first.
     * @return the list of Pareto points.
     */
    std::list<std::vector<bool> > enumerateParetoFront(std::function<bool(const std::vector<bool> &)> fn, unsigned int nofDimensions) {

        // Reserve the sets "P" and "S" from the paper
        std::list<std::vector<bool> > paretoFront;
        std::list<std::vector<bool> > coParetoElements;

        // Negative result buffer
        NegativeResultBuffer negativeResultBuffer;

        // Add the maximal element to the coParetoElements
        {
            std::vector<bool> maximalElement;
            for (unsigned int i=0;i<nofDimensions;i++) {
                maximalElement.push_back(true);
            }
            coParetoElements.push_back(maximalElement);
        }

        // Main loop
        while (!coParetoElements.empty()) {
            std::vector<bool> &testPoint = coParetoElements.front();
            if (!(negativeResultBuffer.isContained(testPoint))) {

                if (fn(testPoint)) {
                    // A Pareto point is missing. Let us find where exactly it is.
                    // We need to work on a copy of the point in order not to spoil
                    // the point form the coParetoElements
                    std::vector<bool> x = testPoint;
                    for (unsigned int i=0;i<nofDimensions;i++) {
                        if (x[i]) {
                            x[i] = false;

                            if (negativeResultBuffer.isContained(x)) {
                                x[i] = true;
                            } else if (fn(x)) {
                                // Ok, can stay like this
                            } else {
                                negativeResultBuffer.addPoint(x);
                                x[i] = true;
                            }
                        }
                    }
                    paretoFront.push_back(x);

                    // Now update all points in the coParetoFront
                    std::list<std::vector<bool> > coParetoElementsMod;
                    for (auto const &y : coParetoElements) {
                        if (!vectorOfBoolIsLeq(x,y)) {
                            coParetoElementsMod.push_back(y);
                        } else {
                            for (unsigned int i=0;i<nofDimensions;i++) {
                                if (x[i]) {
                                    coParetoElementsMod.push_back(y);
                                    std::vector<bool> &mod = coParetoElementsMod.back();
                                    mod[i] = false;
                                }
                            }
                        }
                    }
                    coParetoElements = cleanParetoFront(coParetoElementsMod);

                } else {
                    // Get rid of this point in the co-Pareto front and add to the negative results buffer
                    negativeResultBuffer.addPoint(testPoint);
                    coParetoElements.pop_front();
                }
            } else {
                // Get rid of this point in the co-Pareto front
                coParetoElements.pop_front();
            }
        }
        return paretoFront;
    }

} // End of namespace
