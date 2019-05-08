# QMake Build file
# QMAKE_CC = clang
# QMAKE_LINK_C = clang
# QMAKE_CXX = clang++
# QMAKE_LINK = clang++

    QMAKE_CFLAGS_RELEASE += -g -Wall -Wextra
    QMAKE_CXXFLAGS_RELEASE += -g -std=c++17 -Wall -Wextra
    DEFINES += NDEBUG


    # QMAKE_CFLAGS_DEBUG += -g -Wall -Wextra -fsanitize=address
    # QMAKE_CXXFLAGS_DEBUG += -g -std=c++17 -Wall -Wextra -fsanitize=address
    # QMAKE_LFLAGS = -fsanitize=address




TEMPLATE = app \
    console
CONFIG += release
CONFIG -= app_bundle
CONFIG -= qt

PKGCONFIG +=
QT -= gui \
    core


HEADERS += tests.hpp binaryAntichain.hpp bitvector.hpp gameSolvingProblem.hpp tools.hpp \
    modifiedParetoFrontEnumerationLibrary/pareto_enumerator_bool.hpp \
    explicitGameSolver.hpp

SOURCES += main.cpp tests.cpp gameSolvingProblem.cpp \
    modifiedParetoFrontEnumerationLibrary/pareto_enumerator_bool.cpp \
    explicitGameSolver.cpp


TARGET = gamesolver
INCLUDEPATH = ../../lib/libpopcnt modifiedParetoFrontEnumerationLibrary/

LIBS += 
