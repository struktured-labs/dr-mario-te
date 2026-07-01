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

// SYMS CLASS (contains all model state)
class alignas(VL_CACHE_LINE_BYTES)VCoproDrMario__Syms final : public VerilatedSyms {
  public:
    // INTERNAL STATE
    VCoproDrMario* const __Vm_modelp;
    VlDeleter __Vm_deleter;
    bool __Vm_didInit = false;

    // MODULE INSTANCE STATE
    VCoproDrMario___024root        TOP;

    // CONSTRUCTORS
    VCoproDrMario__Syms(VerilatedContext* contextp, const char* namep, VCoproDrMario* modelp);
    ~VCoproDrMario__Syms();

    // METHODS
    const char* name() { return TOP.name(); }
};

#endif  // guard
