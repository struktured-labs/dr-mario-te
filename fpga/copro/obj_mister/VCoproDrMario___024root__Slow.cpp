// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VCoproDrMario.h for the primary calling header

#include "VCoproDrMario__pch.h"
#include "VCoproDrMario__Syms.h"
#include "VCoproDrMario___024root.h"

void VCoproDrMario___024root___ctor_var_reset(VCoproDrMario___024root* vlSelf);

VCoproDrMario___024root::VCoproDrMario___024root(VCoproDrMario__Syms* symsp, const char* v__name)
    : VerilatedModule{v__name}
    , vlSymsp{symsp}
 {
    // Reset structure values
    VCoproDrMario___024root___ctor_var_reset(this);
}

void VCoproDrMario___024root::__Vconfigure(bool first) {
    (void)first;  // Prevent unused variable warning
}

VCoproDrMario___024root::~VCoproDrMario___024root() {
}
