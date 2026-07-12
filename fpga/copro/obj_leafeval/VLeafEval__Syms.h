// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Symbol table internal header
//
// Internal details; most calling programs do not need this header,
// unless using verilator public meta comments.

#ifndef VERILATED_VLEAFEVAL__SYMS_H_
#define VERILATED_VLEAFEVAL__SYMS_H_  // guard

#include "verilated.h"

// INCLUDE MODEL CLASS

#include "VLeafEval.h"

// INCLUDE MODULE CLASSES
#include "VLeafEval___024root.h"

// DPI TYPES for DPI Export callbacks (Internal use)

// SYMS CLASS (contains all model state)
class alignas(VL_CACHE_LINE_BYTES)VLeafEval__Syms final : public VerilatedSyms {
  public:
    // INTERNAL STATE
    VLeafEval* const __Vm_modelp;
    VlDeleter __Vm_deleter;
    bool __Vm_didInit = false;

    // MODULE INSTANCE STATE
    VLeafEval___024root            TOP;

    // SCOPE NAMES
    VerilatedScope __Vscope_LeafEval;

    // CONSTRUCTORS
    VLeafEval__Syms(VerilatedContext* contextp, const char* namep, VLeafEval* modelp);
    ~VLeafEval__Syms();

    // METHODS
    const char* name() { return TOP.name(); }
};

#endif  // guard
