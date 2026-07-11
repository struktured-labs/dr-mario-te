// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design internal header
// See VLeafEval.h for the primary calling header

#ifndef VERILATED_VLEAFEVAL___024ROOT_H_
#define VERILATED_VLEAFEVAL___024ROOT_H_  // guard

#include "verilated.h"


class VLeafEval__Syms;

class alignas(VL_CACHE_LINE_BYTES) VLeafEval___024root final : public VerilatedModule {
  public:

    // DESIGN SPECIFIC STATE
    VL_IN8(clk,0,0);
    VL_IN8(rst,0,0);
    VL_IN8(wr,0,0);
    VL_IN8(waddr,6,0);
    VL_IN8(wdata,2,0);
    VL_IN8(start,0,0);
    VL_OUT8(done,0,0);
    VL_OUT8(win,0,0);
    CData/*4:0*/ LeafEval__DOT__st;
    CData/*3:0*/ LeafEval__DOT__wc;
    CData/*3:0*/ LeafEval__DOT__wr_;
    CData/*4:0*/ LeafEval__DOT__maxh;
    CData/*7:0*/ LeafEval__DOT__holes;
    CData/*7:0*/ LeafEval__DOT__toprisk;
    CData/*7:0*/ LeafEval__DOT__spawn;
    CData/*7:0*/ LeafEval__DOT__setup;
    CData/*0:0*/ LeafEval__DOT__anyvir;
    CData/*0:0*/ LeafEval__DOT__seen;
    CData/*4:0*/ LeafEval__DOT__fillcnt;
    CData/*6:0*/ LeafEval__DOT__vo;
    CData/*3:0*/ LeafEval__DOT__v_r;
    CData/*2:0*/ LeafEval__DOT__v_c;
    CData/*1:0*/ LeafEval__DOT__v_col;
    CData/*4:0*/ LeafEval__DOT__run_h;
    CData/*4:0*/ LeafEval__DOT__run_v;
    CData/*4:0*/ LeafEval__DOT__p;
    CData/*4:0*/ LeafEval__DOT__span_lo;
    CData/*4:0*/ LeafEval__DOT__span_hi;
    CData/*4:0*/ LeafEval__DOT__vspan_lo;
    CData/*4:0*/ LeafEval__DOT__vspan_hi;
    CData/*1:0*/ LeafEval__DOT__suh__DOT__c0;
    CData/*0:0*/ LeafEval__DOT__suh__DOT__t;
    CData/*1:0*/ LeafEval__DOT__suv__DOT__c0;
    CData/*0:0*/ LeafEval__DOT__suv__DOT__t;
    CData/*0:0*/ __VstlFirstIteration;
    CData/*0:0*/ __Vtrigprevexpr___TOP__clk__0;
    CData/*0:0*/ __VactContinue;
    VL_OUT16(sco,15,0);
    SData/*10:0*/ LeafEval__DOT__pollution;
    SData/*9:0*/ LeafEval__DOT__buried;
    SData/*15:0*/ LeafEval__DOT__rdy_ext;
    SData/*15:0*/ LeafEval__DOT__vrdy;
    SData/*8:0*/ LeafEval__DOT__fin__DOT__hq;
    SData/*8:0*/ LeafEval__DOT__fin__DOT__vq;
    SData/*8:0*/ LeafEval__DOT__fin__DOT__mx;
    IData/*31:0*/ __VactIterCount;
    VlUnpacked<CData/*2:0*/, 128> LeafEval__DOT__bcell;
    VlUnpacked<CData/*1:0*/, 128> LeafEval__DOT__col_of;
    VlUnpacked<CData/*0:0*/, 128> LeafEval__DOT__occ_of;
    VlUnpacked<CData/*0:0*/, 128> LeafEval__DOT__vir_of;
    VlTriggerVec<1> __VstlTriggered;
    VlTriggerVec<1> __VactTriggered;
    VlTriggerVec<1> __VnbaTriggered;

    // INTERNAL VARIABLES
    VLeafEval__Syms* const vlSymsp;

    // CONSTRUCTORS
    VLeafEval___024root(VLeafEval__Syms* symsp, const char* v__name);
    ~VLeafEval___024root();
    VL_UNCOPYABLE(VLeafEval___024root);

    // INTERNAL METHODS
    void __Vconfigure(bool first);
};


#endif  // guard
