// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table internal header
//
// Internal details; most calling programs do not need this header,
// unless using verilator public meta comments.

#ifndef VERILATED_VCOPRODRMARIO__SYMS_H_
#define VERILATED_VCOPRODRMARIO__SYMS_H_  // guard

#include "verilated.h"

// INCLUDE MODEL CLASS

#include "VCoproDrMario.h"

// INCLUDE MODULE CLASSES
#include "VCoproDrMario___024root.h"

// DPI TYPES for DPI Export callbacks (Internal use)

// SYMS CLASS (contains all model state)
class alignas(VL_CACHE_LINE_BYTES)VCoproDrMario__Syms final : public VerilatedSyms {
  public:
    // INTERNAL STATE
    VCoproDrMario* const __Vm_modelp;
    VlDeleter __Vm_deleter;
    bool __Vm_didInit = false;

    // MODULE INSTANCE STATE
    VCoproDrMario___024root        TOP;

    // SCOPE NAMES
    VerilatedScope __Vscope_CoproDrMario;
    VerilatedScope __Vscope_CoproDrMario__cpu6502;
    VerilatedScope __Vscope_CoproDrMario__cpu6502__ALU;
    VerilatedScope __Vscope_CoproDrMario__leafeval;
    VerilatedScope __Vscope_CoproDrMario__leafeval__dbur;
    VerilatedScope __Vscope_CoproDrMario__leafeval__dcomb;
    VerilatedScope __Vscope_CoproDrMario__leafeval__dnew;
    VerilatedScope __Vscope_CoproDrMario__leafeval__drvfin;
    VerilatedScope __Vscope_CoproDrMario__leafeval__dseth;
    VerilatedScope __Vscope_CoproDrMario__leafeval__dsetv;
    VerilatedScope __Vscope_CoproDrMario__leafeval__feol;
    VerilatedScope __Vscope_CoproDrMario__leafeval__fin;
    VerilatedScope __Vscope_CoproDrMario__leafeval__fo2b;
    VerilatedScope __Vscope_CoproDrMario__leafeval__grv;
    VerilatedScope __Vscope_CoproDrMario__leafeval__grvd;
    VerilatedScope __Vscope_CoproDrMario__leafeval__scan;
    VerilatedScope __Vscope_CoproDrMario__leafeval__slotram;
    VerilatedScope __Vscope_CoproDrMario__leafeval__suh;
    VerilatedScope __Vscope_CoproDrMario__leafeval__suv;
    VerilatedScope __Vscope_CoproDrMario__wram;
    VerilatedScope __Vscope_TOP;

    // CONSTRUCTORS
    VCoproDrMario__Syms(VerilatedContext* contextp, const char* namep, VCoproDrMario* modelp);
    ~VCoproDrMario__Syms();

    // METHODS
    const char* name() { return TOP.name(); }
};

#endif  // guard
