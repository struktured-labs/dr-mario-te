// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VCoproDrMario.h for the primary calling header

#include "VCoproDrMario__pch.h"
#include "VCoproDrMario___024root.h"

VL_INLINE_OPT void VCoproDrMario___024root___nba_sequent__TOP__1(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___nba_sequent__TOP__1\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__VdlySet__CoproDrMario__DOT__wram__DOT__mem__v0 = 0U;
    vlSelfRef.__VdlySet__CoproDrMario__DOT__wram__DOT__mem__v1 = 0U;
}

VL_INLINE_OPT void VCoproDrMario___024root___nba_sequent__TOP__2(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___nba_sequent__TOP__2\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    SData/*11:0*/ __Vfunc_CoproDrMario__DOT__xlate__0__Vfuncout;
    __Vfunc_CoproDrMario__DOT__xlate__0__Vfuncout = 0;
    SData/*8:0*/ __Vfunc_CoproDrMario__DOT__xlate__0__a;
    __Vfunc_CoproDrMario__DOT__xlate__0__a = 0;
    SData/*11:0*/ __Vfunc_CoproDrMario__DOT__xlate__1__Vfuncout;
    __Vfunc_CoproDrMario__DOT__xlate__1__Vfuncout = 0;
    SData/*8:0*/ __Vfunc_CoproDrMario__DOT__xlate__1__a;
    __Vfunc_CoproDrMario__DOT__xlate__1__a = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__rst_cnt;
    __Vdly__CoproDrMario__DOT__rst_cnt = 0;
    // Body
    __Vdly__CoproDrMario__DOT__rst_cnt = vlSelfRef.CoproDrMario__DOT__rst_cnt;
    if (vlSelfRef.CoproDrMario__DOT__hb_we) {
        vlSelfRef.__VdlyVal__CoproDrMario__DOT__wram__DOT__mem__v1 
            = vlSelfRef.CoproDrMario__DOT__hb_din;
        vlSelfRef.__VdlyDim0__CoproDrMario__DOT__wram__DOT__mem__v1 
            = vlSelfRef.CoproDrMario__DOT__hb_addr;
        vlSelfRef.__VdlySet__CoproDrMario__DOT__wram__DOT__mem__v1 = 1U;
    }
    vlSelfRef.CoproDrMario__DOT__wram__DOT__q_b = vlSelfRef.CoproDrMario__DOT__wram__DOT__mem
        [vlSelfRef.CoproDrMario__DOT__hb_addr];
    if ((((IData)(vlSelfRef.ce) & (IData)(vlSelfRef.prg_write)) 
         & (IData)(vlSelfRef.CoproDrMario__DOT__copro_sel))) {
        if ((0x84U == (0x1ffU & (IData)(vlSelfRef.prg_ain)))) {
            __Vdly__CoproDrMario__DOT__rst_cnt = 0x1fU;
            vlSelfRef.CoproDrMario__DOT__hb_din = 0U;
            vlSelfRef.CoproDrMario__DOT__parked = 0U;
            vlSelfRef.CoproDrMario__DOT__hb_addr = 0x8ffU;
        } else {
            vlSelfRef.CoproDrMario__DOT__hb_din = vlSelfRef.prg_din;
            __Vfunc_CoproDrMario__DOT__xlate__0__a 
                = (0x1ffU & (IData)(vlSelfRef.prg_ain));
            __Vfunc_CoproDrMario__DOT__xlate__0__Vfuncout 
                = ((IData)((0U == (0x180U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))))
                    ? (0x500U | (0x7fU & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a)))
                    : ((IData)((0x80U == (0x180U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))))
                        ? ((0x40U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                            ? 0x8feU : ((0x20U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                         ? 0x8feU : 
                                        ((0x10U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                          ? 0x8feU : 
                                         ((8U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                           ? ((4U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                               ? 0x8feU
                                               : ((2U 
                                                   & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                                   ? 0x8feU
                                                   : 
                                                  ((1U 
                                                    & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                                    ? 0x8feU
                                                    : 0x83aU)))
                                           : ((4U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                               ? ((2U 
                                                   & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                                   ? 
                                                  ((1U 
                                                    & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                                    ? 0x839U
                                                    : 0x835U)
                                                   : 
                                                  ((1U 
                                                    & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                                    ? 0x834U
                                                    : 0x8ffU))
                                               : ((2U 
                                                   & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                                   ? 
                                                  ((1U 
                                                    & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                                    ? 0x827U
                                                    : 0x826U)
                                                   : 
                                                  ((1U 
                                                    & (IData)(__Vfunc_CoproDrMario__DOT__xlate__0__a))
                                                    ? 0x825U
                                                    : 0x824U)))))))
                        : 0x8feU));
            vlSelfRef.CoproDrMario__DOT__hb_addr = __Vfunc_CoproDrMario__DOT__xlate__0__Vfuncout;
        }
        vlSelfRef.CoproDrMario__DOT__rst_cnt = __Vdly__CoproDrMario__DOT__rst_cnt;
        vlSelfRef.CoproDrMario__DOT__hb_we = 0U;
        vlSelfRef.CoproDrMario__DOT__hb_we = 1U;
    } else {
        if (((0U != (IData)(vlSelfRef.CoproDrMario__DOT__rst_cnt)) 
             & (~ (IData)(vlSelfRef.CoproDrMario__DOT__parked)))) {
            __Vdly__CoproDrMario__DOT__rst_cnt = (0x1fU 
                                                  & ((IData)(vlSelfRef.CoproDrMario__DOT__rst_cnt) 
                                                     - (IData)(1U)));
        }
        vlSelfRef.CoproDrMario__DOT__rst_cnt = __Vdly__CoproDrMario__DOT__rst_cnt;
        vlSelfRef.CoproDrMario__DOT__hb_we = 0U;
        __Vfunc_CoproDrMario__DOT__xlate__1__a = (0x1ffU 
                                                  & (IData)(vlSelfRef.prg_ain));
        __Vfunc_CoproDrMario__DOT__xlate__1__Vfuncout 
            = ((IData)((0U == (0x180U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))))
                ? (0x500U | (0x7fU & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a)))
                : ((IData)((0x80U == (0x180U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))))
                    ? ((0x40U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                        ? 0x8feU : ((0x20U & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                     ? 0x8feU : ((0x10U 
                                                  & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                  ? 0x8feU
                                                  : 
                                                 ((8U 
                                                   & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                   ? 
                                                  ((4U 
                                                    & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                    ? 0x8feU
                                                    : 
                                                   ((2U 
                                                     & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                     ? 0x8feU
                                                     : 
                                                    ((1U 
                                                      & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                      ? 0x8feU
                                                      : 0x83aU)))
                                                   : 
                                                  ((4U 
                                                    & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                    ? 
                                                   ((2U 
                                                     & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                     ? 
                                                    ((1U 
                                                      & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                      ? 0x839U
                                                      : 0x835U)
                                                     : 
                                                    ((1U 
                                                      & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                      ? 0x834U
                                                      : 0x8ffU))
                                                    : 
                                                   ((2U 
                                                     & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                     ? 
                                                    ((1U 
                                                      & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                      ? 0x827U
                                                      : 0x826U)
                                                     : 
                                                    ((1U 
                                                      & (IData)(__Vfunc_CoproDrMario__DOT__xlate__1__a))
                                                      ? 0x825U
                                                      : 0x824U)))))))
                    : 0x8feU));
        vlSelfRef.CoproDrMario__DOT__hb_addr = __Vfunc_CoproDrMario__DOT__xlate__1__Vfuncout;
    }
    vlSelfRef.prg_dout = vlSelfRef.CoproDrMario__DOT__wram__DOT__q_b;
    vlSelfRef.CoproDrMario__DOT__prg_dout = vlSelfRef.CoproDrMario__DOT__wram__DOT__q_b;
    vlSelfRef.CoproDrMario__DOT__ram_b_q = vlSelfRef.CoproDrMario__DOT__wram__DOT__q_b;
    vlSelfRef.CoproDrMario__DOT__wram__DOT__wren_b 
        = vlSelfRef.CoproDrMario__DOT__hb_we;
    vlSelfRef.CoproDrMario__DOT__wram__DOT__data_b 
        = vlSelfRef.CoproDrMario__DOT__hb_din;
    vlSelfRef.CoproDrMario__DOT__wram__DOT__address_b 
        = vlSelfRef.CoproDrMario__DOT__hb_addr;
}

VL_INLINE_OPT void VCoproDrMario___024root___nba_sequent__TOP__3(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___nba_sequent__TOP__3\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state;
    if (vlSelfRef.CoproDrMario__DOT__cpu_rst) {
        vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state = 8U;
    } else if (((((((((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
                      | (0x2fU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                     | (0x30U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                    | (0x31U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                   | (0U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                  | (1U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                 | (2U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                | (3U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if (((((((((0U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)) 
                       | (0x20U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                      | (0x2cU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                     | (0x40U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                    | (0x4cU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                   | (0x60U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                  | (0x6cU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                 | (8U == (0xbfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))))) {
                vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state 
                    = ((0U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))
                        ? 8U : ((0x20U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))
                                 ? 0x1aU : ((0x2cU 
                                             == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))
                                             ? 0U : 
                                            ((0x40U 
                                              == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))
                                              ? 0x25U
                                              : ((0x4cU 
                                                  == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))
                                                  ? 0x16U
                                                  : 
                                                 ((0x60U 
                                                   == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))
                                                   ? 0x2aU
                                                   : 
                                                  ((0x6cU 
                                                    == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))
                                                    ? 0x18U
                                                    : 0x21U)))))));
            } else if (((((((((0x28U == (0xbfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                              | (0x18U == (0x9fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                             | (0x80U == (0x9dU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                            | (0x8cU == (0x9fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                           | (0x88U == (0x8fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                          | (1U == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                         | (4U == (0x1cU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                        | (9U == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))))) {
                vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state 
                    = ((0x28U == (0xbfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                        ? 0x1eU : ((0x18U == (0x9fU 
                                              & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                    ? 0x24U : ((0x80U 
                                                == 
                                                (0x9dU 
                                                 & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                                ? 0xdU
                                                : (
                                                   (0x8cU 
                                                    == 
                                                    (0x9fU 
                                                     & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                                    ? 0U
                                                    : 
                                                   ((0x88U 
                                                     == 
                                                     (0x8fU 
                                                      & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                                     ? 0x24U
                                                     : 
                                                    ((1U 
                                                      == 
                                                      (0x1fU 
                                                       & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                                      ? 0xeU
                                                      : 
                                                     ((4U 
                                                       == 
                                                       (0x1cU 
                                                        & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                                       ? 0x2fU
                                                       : 0xdU)))))));
            } else if (((((((((0xdU == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                              | (0xeU == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                             | (0x10U == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                            | (0x11U == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                           | (0x14U == (0x1cU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                          | (0x19U == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                         | (0x1cU == (0x1cU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                        | (0xaU == (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))))) {
                vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state 
                    = ((0xdU == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                        ? 0U : ((0xeU == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                 ? 0U : ((0x10U == 
                                          (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                          ? 5U : ((0x11U 
                                                   == 
                                                   (0x1fU 
                                                    & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                                   ? 0x12U
                                                   : 
                                                  ((0x14U 
                                                    == 
                                                    (0x1cU 
                                                     & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                                    ? 0x30U
                                                    : 
                                                   ((0x19U 
                                                     == 
                                                     (0x1fU 
                                                      & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                                     ? 2U
                                                     : 
                                                    ((0x1cU 
                                                      == 
                                                      (0x1cU 
                                                       & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                                                      ? 2U
                                                      : 0x24U)))))));
            }
        } else {
            vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state 
                = ((0x2fU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__write_back)
                        ? 0x23U : 0xdU) : ((0x30U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                            ? 0x31U
                                            : ((0x31U 
                                                == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                ? ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__write_back)
                                                    ? 0x23U
                                                    : 0xdU)
                                                : (
                                                   (0U 
                                                    == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                    ? 1U
                                                    : 
                                                   ((1U 
                                                     == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                     ? 
                                                    ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__write_back)
                                                      ? 0x23U
                                                      : 0xdU)
                                                     : 
                                                    ((2U 
                                                      == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                      ? 3U
                                                      : 
                                                     ((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO) 
                                                        | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__store)) 
                                                       | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__write_back))
                                                       ? 4U
                                                       : 0xdU)))))));
        }
    } else if (((((((((4U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
                      | (0xeU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                     | (0xfU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                    | (0x10U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                   | (0x11U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                  | (0x12U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                 | (0x13U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                | (0x14U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state 
            = ((4U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                ? ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__write_back)
                    ? 0x23U : 0xdU) : ((0xeU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                        ? 0xfU : ((0xfU 
                                                   == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                   ? 0x10U
                                                   : 
                                                  ((0x10U 
                                                    == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                    ? 0x11U
                                                    : 
                                                   ((0x11U 
                                                     == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                     ? 0xdU
                                                     : 
                                                    ((0x12U 
                                                      == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                      ? 0x13U
                                                      : 
                                                     ((0x13U 
                                                       == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                       ? 0x14U
                                                       : 
                                                      (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO) 
                                                        | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__store))
                                                        ? 0x15U
                                                        : 0xdU))))))));
    } else if (((((((((0x15U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
                      | (0x23U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                     | (0x2eU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                    | (0xdU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                   | (0x24U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                  | (0x21U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                 | (0x22U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                | (0x1eU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state 
            = ((0x15U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                ? 0xdU : ((0x23U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                           ? 0x2eU : ((0x2eU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                       ? 0xdU : ((0xdU 
                                                  == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                  ? 0xcU
                                                  : 
                                                 ((0x24U 
                                                   == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                   ? 0xcU
                                                   : 
                                                  ((0x21U 
                                                    == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                    ? 0x22U
                                                    : 
                                                   ((0x22U 
                                                     == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                     ? 0xcU
                                                     : 0x1fU)))))));
    } else if (((((((((0x1fU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
                      | (0x20U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                     | (0x1aU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                    | (0x1bU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                   | (0x1cU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                  | (0x1dU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                 | (0x25U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                | (0x26U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state 
            = ((0x1fU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                ? 0x20U : ((0x20U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                            ? 0xcU : ((0x1aU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                       ? 0x1bU : ((0x1bU 
                                                   == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                   ? 0x1cU
                                                   : 
                                                  ((0x1cU 
                                                    == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                    ? 0x1dU
                                                    : 
                                                   ((0x1dU 
                                                     == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                     ? 0xdU
                                                     : 
                                                    ((0x25U 
                                                      == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                      ? 0x26U
                                                      : 0x27U)))))));
    } else if (((((((((0x27U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
                      | (0x28U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                     | (0x29U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                    | (0x2aU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                   | (0x2bU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                  | (0x2cU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                 | (0x2dU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                | (5U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state 
            = ((0x27U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                ? 0x28U : ((0x28U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                            ? 0x29U : ((0x29U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                        ? 0xcU : ((0x2aU 
                                                   == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                   ? 0x2bU
                                                   : 
                                                  ((0x2bU 
                                                    == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                    ? 0x2cU
                                                    : 
                                                   ((0x2cU 
                                                     == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                     ? 0x2dU
                                                     : 
                                                    ((0x2dU 
                                                      == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                      ? 0xdU
                                                      : 
                                                     ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__cond_true)
                                                       ? 6U
                                                       : 0xcU))))))));
    } else if (((((((((6U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
                      | (7U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                     | (0x16U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                    | (0x17U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                   | (0x18U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                  | (0x19U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                 | (8U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
                | (9U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state 
            = ((6U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO) 
                    ^ (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__backwards))
                    ? 7U : 0xcU) : ((7U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                     ? 0xcU : ((0x16U 
                                                == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                ? 0x17U
                                                : (
                                                   (0x17U 
                                                    == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                    ? 0xcU
                                                    : 
                                                   ((0x18U 
                                                     == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                     ? 0x19U
                                                     : 
                                                    ((0x19U 
                                                      == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                      ? 0x16U
                                                      : 
                                                     ((8U 
                                                       == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                                       ? 9U
                                                       : 0xaU)))))));
    } else if ((0xaU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state = 0xbU;
    } else if ((0xbU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state = 0x16U;
    }
}

extern const VlUnpacked<CData/*0:0*/, 128> VCoproDrMario__ConstPool__TABLE_h2335744c_0;

VL_INLINE_OPT void VCoproDrMario___024root___nba_sequent__TOP__4(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___nba_sequent__TOP__4\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    CData/*6:0*/ __Vtableidx8;
    __Vtableidx8 = 0;
    // Body
    if (vlSelfRef.CoproDrMario__DOT____Vcellinp__wram__wren_a) {
        vlSelfRef.__VdlyVal__CoproDrMario__DOT__wram__DOT__mem__v0 
            = vlSelfRef.CoproDrMario__DOT__DO;
        vlSelfRef.__VdlyDim0__CoproDrMario__DOT__wram__DOT__mem__v0 
            = vlSelfRef.CoproDrMario__DOT__a_addr;
        vlSelfRef.__VdlySet__CoproDrMario__DOT__wram__DOT__mem__v0 = 1U;
    }
    __Vtableidx8 = ((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__N) 
                      << 6U) | ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__V) 
                                << 5U)) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C) 
                                            << 4U) 
                                           | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__Z) 
                                               << 3U) 
                                              | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__cond_code))));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__cond_true 
        = VCoproDrMario__ConstPool__TABLE_h2335744c_0
        [__Vtableidx8];
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CO;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__backwards 
        = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                 >> 7U));
    if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__store 
            = ((0x84U == (0xe5U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
               || (0x81U == (0xe3U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__write_back 
            = ((6U == (0x87U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
               || (0xc6U == (0xc7U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))));
    }
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADJH 
        = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adj_bcd)
            ? ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adc_bcd)
                ? ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO)
                    ? 6U : 0U) : ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO)
                                   ? 0U : 0xaU)) : 0U);
    vlSelfRef.CoproDrMario__DOT__cpu_rst = vlSelfRef.CoproDrMario__DOT__rst_m;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX 
        = vlSelfRef.CoproDrMario__DOT__DI;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR = 
        ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge)
          ? 0U : ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IRHOLD_valid)
                   ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IRHOLD)
                   : (IData)(vlSelfRef.CoproDrMario__DOT__DI)));
    vlSelfRef.CoproDrMario__DOT__rst_m = vlSelfRef.CoproDrMario__DOT__cpu_rst_src;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__reset 
        = vlSelfRef.CoproDrMario__DOT__cpu_rst;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rst 
        = vlSelfRef.CoproDrMario__DOT__cpu_rst;
}

VL_INLINE_OPT void VCoproDrMario___024root___nba_sequent__TOP__5(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___nba_sequent__TOP__5\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if (vlSelfRef.__VdlySet__CoproDrMario__DOT__wram__DOT__mem__v0) {
        vlSelfRef.CoproDrMario__DOT__wram__DOT__mem[vlSelfRef.__VdlyDim0__CoproDrMario__DOT__wram__DOT__mem__v0] 
            = vlSelfRef.__VdlyVal__CoproDrMario__DOT__wram__DOT__mem__v0;
    }
    if (vlSelfRef.__VdlySet__CoproDrMario__DOT__wram__DOT__mem__v1) {
        vlSelfRef.CoproDrMario__DOT__wram__DOT__mem[vlSelfRef.__VdlyDim0__CoproDrMario__DOT__wram__DOT__mem__v1] 
            = vlSelfRef.__VdlyVal__CoproDrMario__DOT__wram__DOT__mem__v1;
    }
}

VL_INLINE_OPT void VCoproDrMario___024root___nba_sequent__TOP__6(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___nba_sequent__TOP__6\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state 
        = vlSelfRef.__Vdly__CoproDrMario__DOT__cpu6502__DOT__state;
}

VL_INLINE_OPT void VCoproDrMario___024root___nba_sequent__TOP__7(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___nba_sequent__TOP__7\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.CoproDrMario__DOT__cpu_rst_src = ((0U 
                                                 != (IData)(vlSelfRef.CoproDrMario__DOT__rst_cnt)) 
                                                | (IData)(vlSelfRef.CoproDrMario__DOT__parked));
}

extern const VlUnpacked<CData/*0:0*/, 256> VCoproDrMario__ConstPool__TABLE_hf9320a1f_0;
extern const VlUnpacked<CData/*0:0*/, 512> VCoproDrMario__ConstPool__TABLE_hafeef89d_0;
extern const VlUnpacked<CData/*0:0*/, 128> VCoproDrMario__ConstPool__TABLE_h3046dbb4_0;
extern const VlUnpacked<CData/*0:0*/, 8192> VCoproDrMario__ConstPool__TABLE_hc377d77d_0;
extern const VlUnpacked<CData/*3:0*/, 2048> VCoproDrMario__ConstPool__TABLE_h00ffe440_0;
extern const VlUnpacked<CData/*1:0*/, 2048> VCoproDrMario__ConstPool__TABLE_h8ffa5a2b_0;

VL_INLINE_OPT void VCoproDrMario___024root___nba_comb__TOP__0(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___nba_comb__TOP__0\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    CData/*0:0*/ CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_2;
    CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_2 = 0;
    CData/*0:0*/ CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_3;
    CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_3 = 0;
    CData/*0:0*/ CoproDrMario__DOT__cpu6502__DOT____Vcellinp__ALU__BCD;
    CoproDrMario__DOT__cpu6502__DOT____Vcellinp__ALU__BCD = 0;
    SData/*15:0*/ CoproDrMario__DOT__cpu6502__DOT____VdfgExtracted_hdce86eaa__0;
    CoproDrMario__DOT__cpu6502__DOT____VdfgExtracted_hdce86eaa__0 = 0;
    SData/*8:0*/ __Vtableidx1;
    __Vtableidx1 = 0;
    CData/*6:0*/ __Vtableidx2;
    __Vtableidx2 = 0;
    CData/*7:0*/ __Vtableidx3;
    __Vtableidx3 = 0;
    SData/*10:0*/ __Vtableidx4;
    __Vtableidx4 = 0;
    SData/*10:0*/ __Vtableidx5;
    __Vtableidx5 = 0;
    SData/*12:0*/ __Vtableidx6;
    __Vtableidx6 = 0;
    // Body
    __Vtableidx3 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__plp) 
                     << 7U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__load_reg) 
                                << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__write_register 
        = VCoproDrMario__ConstPool__TABLE_hf9320a1f_0
        [__Vtableidx3];
    __Vtableidx1 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__backwards) 
                     << 8U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO) 
                                << 7U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge) 
                                           << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_inc 
        = VCoproDrMario__ConstPool__TABLE_hafeef89d_0
        [__Vtableidx1];
    CoproDrMario__DOT__cpu6502__DOT____Vcellinp__ALU__BCD 
        = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adc_bcd) 
           & (0xdU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)));
    __Vtableidx2 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__store) 
                     << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__WE = 
        VCoproDrMario__ConstPool__TABLE_h3046dbb4_0
        [__Vtableidx2];
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_shift_right 
        = (((0xdU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
            | ((0x24U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
               | (0x23U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) 
           & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__shift_right));
    __Vtableidx6 = (((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__load_only) 
                       << 0xcU) | ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__compare) 
                                   << 0xbU)) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO) 
                                                 << 0xaU) 
                                                | ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__inc) 
                                                   << 9U))) 
                    | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__shift) 
                        << 8U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C) 
                                   << 7U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__rotate) 
                                              << 6U) 
                                             | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CI = 
        VCoproDrMario__ConstPool__TABLE_hc377d77d_0
        [__Vtableidx6];
    __Vtableidx5 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__backwards) 
                     << 0xaU) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__op) 
                                  << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op 
        = VCoproDrMario__ConstPool__TABLE_h00ffe440_0
        [__Vtableidx5];
    __Vtableidx4 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__dst_reg) 
                     << 9U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__index_y) 
                                << 8U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__src_reg) 
                                           << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regsel 
        = VCoproDrMario__ConstPool__TABLE_h8ffa5a2b_0
        [__Vtableidx4];
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__BCD 
        = CoproDrMario__DOT__cpu6502__DOT____Vcellinp__ALU__BCD;
    vlSelfRef.CoproDrMario__DOT__WE = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__WE;
    CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_3 
        = ((~ (IData)(vlSelfRef.CoproDrMario__DOT__cpu_rst)) 
           & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__WE));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__right 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_shift_right;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CI 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CI;
    if ((0x20U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if ((0x10U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
        } else if ((8U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC)
                    : ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC)));
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                = ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX)
                    : ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX)));
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                = ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? 0U : ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                             ? 0U : ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                      ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX))));
        }
    } else if ((0x10U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if ((8U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC)
                    : ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC)));
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                = ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX)
                        : 0U) : ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                  ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX)));
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                            ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                            : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC))
                    : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC));
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
        }
    } else if ((8U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                    = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX));
            } else if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge)
                        ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
            }
        } else if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__res)
                        ? 0xfffcU : ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge)
                                      ? 0xfffaU : 0xfffeU));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
            }
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
        }
    } else if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                        << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCL));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH) 
                        << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
            }
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCL)
                    : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX));
        }
    } else {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
            = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX)
                : ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX)));
    }
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__BI 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__op 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__adder_CI 
        = ((~ ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_shift_right) 
               | (3U == (3U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op) 
                               >> 2U))))) & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CI));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AXYS
        [vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regsel];
    CoproDrMario__DOT__cpu6502__DOT____VdfgExtracted_hdce86eaa__0 
        = (0x100U | vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AXYS
           [vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regsel]);
    if ((0x20U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if ((0x10U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
            if ((8U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            } else if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            } else if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            } else if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD;
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            }
        } else if ((8U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                            = vlSelfRef.CoproDrMario__DOT__DI;
                    } else {
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD;
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                            = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL));
                    }
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                            ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC)
                            : (0x100U | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD)));
                }
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                            = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                            = (0x100U | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                    } else {
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                            = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                            = CoproDrMario__DOT__cpu6502__DOT____VdfgExtracted_hdce86eaa__0;
                    }
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & 0U);
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                            ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                            : (0x100U | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD)));
                }
            }
        } else if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
            if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = (0x100U | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? (IData)(CoproDrMario__DOT__cpu6502__DOT____VdfgExtracted_hdce86eaa__0)
                        : (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL)));
            }
        } else if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH) 
                        << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL));
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__php)
                        ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__P)
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = CoproDrMario__DOT__cpu6502__DOT____VdfgExtracted_hdce86eaa__0;
            }
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                = (0xffU & ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                             ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile)
                             : 0U));
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
        }
    } else if ((0x10U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if ((8U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                 ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile)));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                            ? (0x100U | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                            : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC));
            } else if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCL;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = (0x100U | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCH;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = CoproDrMario__DOT__cpu6502__DOT____VdfgExtracted_hdce86eaa__0;
                }
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC));
            }
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
            if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                            ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                            : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC))
                        : ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                            ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL))
                            : (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))));
            } else if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD;
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & 0U);
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = vlSelfRef.CoproDrMario__DOT__DI;
                }
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
            }
        }
    } else if ((8U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
            if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD;
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                }
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                 ? ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__load_only)
                                     ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile))
                                 : 0U));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            }
        } else if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge)
                        ? (0xefU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__P))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__P));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = (0x100U | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
            }
        } else if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCL;
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                = (0x100U | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCH;
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                = CoproDrMario__DOT__cpu6502__DOT____VdfgExtracted_hdce86eaa__0;
        }
    } else {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
        if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & 0U);
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL));
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                }
            } else if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                        << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL));
            }
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                = (0xffU & ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                             ? ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                 ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile))
                             : 0U));
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                        << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                    : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC));
        }
    }
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cmd 
        = (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO) 
                   >> 0U));
    vlSelfRef.CoproDrMario__DOT__DO = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO;
    vlSelfRef.CoproDrMario__DOT__lev_colenc = ((0U 
                                                == 
                                                (3U 
                                                 & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO)))
                                                ? 1U
                                                : (
                                                   (1U 
                                                    == 
                                                    (3U 
                                                     & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO)))
                                                    ? 2U
                                                    : 3U));
    vlSelfRef.CoproDrMario__DOT__lev_lnk = ((4U == 
                                             (0xfU 
                                              & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO) 
                                                 >> 4U)))
                                             ? 2U : 
                                            ((5U == 
                                              (0xfU 
                                               & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO) 
                                                  >> 4U)))
                                              ? 1U : 
                                             ((6U == 
                                               (0xfU 
                                                & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO) 
                                                   >> 4U)))
                                               ? 4U
                                               : ((7U 
                                                   == 
                                                   (0xfU 
                                                    & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO) 
                                                       >> 4U)))
                                                   ? 3U
                                                   : 0U))));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__AI 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_logic 
        = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op))
            ? ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op))
                ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI)
                : ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI) 
                   ^ (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI)))
            : ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op))
                ? ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI) 
                   & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI))
                : ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI) 
                   | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI))));
    if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_shift_right) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_logic 
            = ((0x100U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI) 
                          << 8U)) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CI) 
                                      << 7U) | (0x7fU 
                                                & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI) 
                                                   >> 1U))));
    }
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__waddr 
        = (0x7fU & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB) 
                    >> 0U));
    vlSelfRef.CoproDrMario__DOT__AB = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB;
    vlSelfRef.CoproDrMario__DOT__a_rom = (2U == (3U 
                                                 & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB) 
                                                    >> 0xeU)));
    vlSelfRef.CoproDrMario__DOT__a_vec = (0x7ffeU == 
                                          (0x7fffU 
                                           & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB) 
                                              >> 1U)));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sr_waddr 
        = (((IData)(vlSelfRef.CoproDrMario__DOT__lev_wslot) 
            << 7U) | (0x7fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB)));
    vlSelfRef.CoproDrMario__DOT__a_ram_lo = (0U == 
                                             (0xfU 
                                              & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB) 
                                                 >> 0xcU)));
    vlSelfRef.CoproDrMario__DOT__a_ram_st = (0x61U 
                                             == (0xffU 
                                                 & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB) 
                                                    >> 8U)));
    vlSelfRef.CoproDrMario__DOT__a_lev = (0x70U == 
                                          (0xffU & 
                                           ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB) 
                                            >> 8U)));
    vlSelfRef.CoproDrMario__DOT__wram__DOT__data_a 
        = vlSelfRef.CoproDrMario__DOT__DO;
    vlSelfRef.CoproDrMario__DOT__lev_enc = ((0xffU 
                                             == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO))
                                             ? 0U : 
                                            (((0xdU 
                                               == (0xfU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO) 
                                                      >> 4U))) 
                                              << 2U) 
                                             | (IData)(vlSelfRef.CoproDrMario__DOT__lev_colenc)));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wlnk 
        = vlSelfRef.CoproDrMario__DOT__lev_lnk;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_BI 
        = (0xffU & ((8U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op))
                     ? ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op))
                         ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_logic))
                     : ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op))
                         ? (~ (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI))
                         : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI))));
    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_cpw) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_wa 
            = (((IData)(vlSelfRef.CoproDrMario__DOT__lev_a_sl) 
                << 7U) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cpw_p));
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_wd 
            = (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_rq) 
                << 3U) | vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
               [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cpw_p]);
    } else {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_wa 
            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sr_waddr;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_wd 
            = (((IData)(vlSelfRef.CoproDrMario__DOT__lev_lnk) 
                << 3U) | (IData)(vlSelfRef.CoproDrMario__DOT__lev_enc));
    }
    vlSelfRef.CoproDrMario__DOT__a_addr = (0xfffU & 
                                           ((IData)(vlSelfRef.CoproDrMario__DOT__a_ram_st)
                                             ? (0x800U 
                                                | (0xffU 
                                                   & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB)))
                                             : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB)));
    vlSelfRef.CoproDrMario__DOT__a_ram = ((IData)(vlSelfRef.CoproDrMario__DOT__a_ram_lo) 
                                          | (IData)(vlSelfRef.CoproDrMario__DOT__a_ram_st));
    CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_2 
        = ((IData)(CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_3) 
           & (IData)(vlSelfRef.CoproDrMario__DOT__a_lev));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wdata 
        = vlSelfRef.CoproDrMario__DOT__lev_enc;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_l 
        = (0x1fU & (((0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_logic)) 
                     + (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_BI))) 
                    + (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__adder_CI)));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__address_a 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_wa;
    vlSelfRef.CoproDrMario__DOT__wram__DOT__address_a 
        = vlSelfRef.CoproDrMario__DOT__a_addr;
    vlSelfRef.CoproDrMario__DOT____Vcellinp__wram__wren_a 
        = ((IData)(CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_3) 
           & (IData)(vlSelfRef.CoproDrMario__DOT__a_ram));
    vlSelfRef.CoproDrMario__DOT__lev_wr_arg = ((IData)(CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_2) 
                                               & (IData)(
                                                         (0xe0U 
                                                          == 
                                                          (0xf8U 
                                                           & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB)))));
    vlSelfRef.CoproDrMario__DOT__lev_start = ((IData)(CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_2) 
                                              & (0xf8U 
                                                 == 
                                                 (0xffU 
                                                  & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB))));
    vlSelfRef.CoproDrMario__DOT__lev_cmd_go = ((IData)(CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_2) 
                                               & (0xf4U 
                                                  == 
                                                  (0xffU 
                                                   & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB))));
    vlSelfRef.CoproDrMario__DOT__lev_wr_board = ((~ 
                                                  ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB) 
                                                   >> 7U)) 
                                                 & (IData)(CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_2));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__data_a 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_wd;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__HC9 
        = ((IData)(CoproDrMario__DOT__cpu6502__DOT____Vcellinp__ALU__BCD) 
           & (5U <= (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_l) 
                           >> 1U))));
    vlSelfRef.CoproDrMario__DOT__wram__DOT__wren_a 
        = vlSelfRef.CoproDrMario__DOT____Vcellinp__wram__wren_a;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__start 
        = vlSelfRef.CoproDrMario__DOT__lev_start;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cmd_go 
        = vlSelfRef.CoproDrMario__DOT__lev_cmd_go;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr 
        = vlSelfRef.CoproDrMario__DOT__lev_wr_board;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 0U;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_we 
        = (((IData)(vlSelfRef.CoproDrMario__DOT__lev_wr_board) 
            & (0U != (IData)(vlSelfRef.CoproDrMario__DOT__lev_wslot))) 
           | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_cpw));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd = 0U;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa = 0U;
    if (((IData)(vlSelfRef.CoproDrMario__DOT__lev_wr_board) 
         & (0U == (IData)(vlSelfRef.CoproDrMario__DOT__lev_wslot)))) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd 
            = vlSelfRef.CoproDrMario__DOT__lev_lnk;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
            = (0x7fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB));
    } else if (((((((((0x1aU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)) 
                      | (0x14U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                     | (0x33U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                    | (0x30U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                   | (0x2bU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                  | (0x31U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                 | (0x2cU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                | (0x32U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)))) {
        if ((0x1aU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd 
                = (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_qb) 
                         >> 3U));
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2;
        } else if ((0x14U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd 
                = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4))
                    ? 4U : 2U);
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a;
        } else if ((0x33U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd 
                = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4))
                    ? 3U : 1U);
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b;
        } else if ((0x30U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
            if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_m) 
                 & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_unl))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd = 0U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_pixr;
            }
        } else if ((0x2bU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
            if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_m) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd = 0U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i;
            }
        } else if ((0x31U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
            if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_do) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd = 0U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k0;
            }
        } else if ((0x2cU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
            if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_do) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_lnk;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
                    = (0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k0)));
            }
        } else {
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd = 0U;
            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gk1;
        }
    } else if ((0x2dU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd 
            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_lnk;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
            = (0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gk1)));
    } else if ((0x26U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a;
    } else if ((0x34U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we = 1U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa 
            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b;
    }
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_HC 
        = (IData)((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_l) 
                    >> 4U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__HC9)));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__wren_a 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_we;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_h 
        = (0x1fU & ((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_logic) 
                      >> 4U) + (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_BI) 
                                        >> 4U))) + (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_HC)));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp 
        = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_h) 
            << 4U) | (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_l)));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CO9 
        = ((IData)(CoproDrMario__DOT__cpu6502__DOT____Vcellinp__ALU__BCD) 
           & (5U <= (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_h) 
                           >> 1U))));
}

void VCoproDrMario___024root___eval_triggers__act(VCoproDrMario___024root* vlSelf);
void VCoproDrMario___024root___eval_act(VCoproDrMario___024root* vlSelf);

bool VCoproDrMario___024root___eval_phase__act(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_phase__act\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    VlTriggerVec<3> __VpreTriggered;
    CData/*0:0*/ __VactExecute;
    // Body
    VCoproDrMario___024root___eval_triggers__act(vlSelf);
    __VactExecute = vlSelfRef.__VactTriggered.any();
    if (__VactExecute) {
        __VpreTriggered.andNot(vlSelfRef.__VactTriggered, vlSelfRef.__VnbaTriggered);
        vlSelfRef.__VnbaTriggered.thisOr(vlSelfRef.__VactTriggered);
        VCoproDrMario___024root___eval_act(vlSelf);
    }
    return (__VactExecute);
}

void VCoproDrMario___024root___eval_nba(VCoproDrMario___024root* vlSelf);

bool VCoproDrMario___024root___eval_phase__nba(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_phase__nba\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    CData/*0:0*/ __VnbaExecute;
    // Body
    __VnbaExecute = vlSelfRef.__VnbaTriggered.any();
    if (__VnbaExecute) {
        VCoproDrMario___024root___eval_nba(vlSelf);
        vlSelfRef.__VnbaTriggered.clear();
    }
    return (__VnbaExecute);
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VCoproDrMario___024root___dump_triggers__ico(VCoproDrMario___024root* vlSelf);
#endif  // VL_DEBUG
bool VCoproDrMario___024root___eval_phase__ico(VCoproDrMario___024root* vlSelf);
#ifdef VL_DEBUG
VL_ATTR_COLD void VCoproDrMario___024root___dump_triggers__nba(VCoproDrMario___024root* vlSelf);
#endif  // VL_DEBUG
#ifdef VL_DEBUG
VL_ATTR_COLD void VCoproDrMario___024root___dump_triggers__act(VCoproDrMario___024root* vlSelf);
#endif  // VL_DEBUG

void VCoproDrMario___024root___eval(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    IData/*31:0*/ __VicoIterCount;
    CData/*0:0*/ __VicoContinue;
    IData/*31:0*/ __VnbaIterCount;
    CData/*0:0*/ __VnbaContinue;
    // Body
    __VicoIterCount = 0U;
    vlSelfRef.__VicoFirstIteration = 1U;
    __VicoContinue = 1U;
    while (__VicoContinue) {
        if (VL_UNLIKELY((0x64U < __VicoIterCount))) {
#ifdef VL_DEBUG
            VCoproDrMario___024root___dump_triggers__ico(vlSelf);
#endif
            VL_FATAL_MT("/home/struktured/projects/dr-mario-tempo-wt/experiments/drveto/g3_tempo/../../../fpga/copro/CoproDrMario.sv", 22, "", "Input combinational region did not converge.");
        }
        __VicoIterCount = ((IData)(1U) + __VicoIterCount);
        __VicoContinue = 0U;
        if (VCoproDrMario___024root___eval_phase__ico(vlSelf)) {
            __VicoContinue = 1U;
        }
        vlSelfRef.__VicoFirstIteration = 0U;
    }
    __VnbaIterCount = 0U;
    __VnbaContinue = 1U;
    while (__VnbaContinue) {
        if (VL_UNLIKELY((0x64U < __VnbaIterCount))) {
#ifdef VL_DEBUG
            VCoproDrMario___024root___dump_triggers__nba(vlSelf);
#endif
            VL_FATAL_MT("/home/struktured/projects/dr-mario-tempo-wt/experiments/drveto/g3_tempo/../../../fpga/copro/CoproDrMario.sv", 22, "", "NBA region did not converge.");
        }
        __VnbaIterCount = ((IData)(1U) + __VnbaIterCount);
        __VnbaContinue = 0U;
        vlSelfRef.__VactIterCount = 0U;
        vlSelfRef.__VactContinue = 1U;
        while (vlSelfRef.__VactContinue) {
            if (VL_UNLIKELY((0x64U < vlSelfRef.__VactIterCount))) {
#ifdef VL_DEBUG
                VCoproDrMario___024root___dump_triggers__act(vlSelf);
#endif
                VL_FATAL_MT("/home/struktured/projects/dr-mario-tempo-wt/experiments/drveto/g3_tempo/../../../fpga/copro/CoproDrMario.sv", 22, "", "Active region did not converge.");
            }
            vlSelfRef.__VactIterCount = ((IData)(1U) 
                                         + vlSelfRef.__VactIterCount);
            vlSelfRef.__VactContinue = 0U;
            if (VCoproDrMario___024root___eval_phase__act(vlSelf)) {
                vlSelfRef.__VactContinue = 1U;
            }
        }
        if (VCoproDrMario___024root___eval_phase__nba(vlSelf)) {
            __VnbaContinue = 1U;
        }
    }
}

#ifdef VL_DEBUG
void VCoproDrMario___024root___eval_debug_assertions(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_debug_assertions\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if (VL_UNLIKELY((vlSelfRef.clk & 0xfeU))) {
        Verilated::overWidthError("clk");}
    if (VL_UNLIKELY((vlSelfRef.clk_cpu & 0xfeU))) {
        Verilated::overWidthError("clk_cpu");}
    if (VL_UNLIKELY((vlSelfRef.ce & 0xfeU))) {
        Verilated::overWidthError("ce");}
    if (VL_UNLIKELY((vlSelfRef.enable & 0xfeU))) {
        Verilated::overWidthError("enable");}
    if (VL_UNLIKELY((vlSelfRef.prg_read & 0xfeU))) {
        Verilated::overWidthError("prg_read");}
    if (VL_UNLIKELY((vlSelfRef.prg_write & 0xfeU))) {
        Verilated::overWidthError("prg_write");}
}
#endif  // VL_DEBUG
