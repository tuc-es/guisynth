# QMake Build file
CFLAGS += -g -fpermissive

QMAKE_LFLAGS_X86_64 = -arch x86_64

QMAKE_CFLAGS_X86_64 = -arch x86_64
QMAKE_CXXFLAGS_X86_64 = -arch x86_64

QMAKE_CFLAGS_RELEASE += -g \
    $$BDDFLAGS
QMAKE_CXXFLAGS_RELEASE += -g -std=c++17 \
    $$BDDFLAGS
QMAKE_CFLAGS_DEBUG += -g -Wall -Wextra \
    $$BDDFLAGS
QMAKE_CXXFLAGS_DEBUG += -g -Wall -Wextra -std=c++17 \
    $$BDDFLAGS

TEMPLATE = app \
    console
CONFIG += release
CONFIG -= app_bundle
CONFIG -= qt
HEADERS += 

SOURCES += ltl2polish.cc 

TARGET = ltl2polish
INCLUDEPATH = ../../lib/spot ../../lib/spot/buddy/src

LIBS += -static -L../../lib/spot/spot -L../../lib/spot/spot/.libs -L../../lib/spot/spot/tl/.libs -ltl -lspot


PKGCONFIG += 
QT -= gui \
    core
