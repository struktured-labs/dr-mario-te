// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VLeafEval.h for the primary calling header

#include "VLeafEval__pch.h"
#include "VLeafEval__Syms.h"
#include "VLeafEval___024root.h"

void VLeafEval___024root___ctor_var_reset(VLeafEval___024root* vlSelf);

VLeafEval___024root::VLeafEval___024root(VLeafEval__Syms* symsp, const char* v__name)
    : VerilatedModule{v__name}
    , vlSymsp{symsp}
 {
    // Reset structure values
    VLeafEval___024root___ctor_var_reset(this);
}

void VLeafEval___024root::__Vconfigure(bool first) {
    (void)first;  // Prevent unused variable warning
}

VLeafEval___024root::~VLeafEval___024root() {
}
