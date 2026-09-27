// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VCoproDrMario.h for the primary calling header

#include "VCoproDrMario__pch.h"
#include "VCoproDrMario___024root.h"

void VCoproDrMario___024root___ico_sequent__TOP__0(VCoproDrMario___024root* vlSelf);

void VCoproDrMario___024root___eval_ico(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_ico\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1ULL & vlSelfRef.__VicoTriggered.word(0U))) {
        VCoproDrMario___024root___ico_sequent__TOP__0(vlSelf);
    }
}

extern const VlUnpacked<CData/*0:0*/, 256> VCoproDrMario__ConstPool__TABLE_hf9320a1f_0;
extern const VlUnpacked<CData/*0:0*/, 128> VCoproDrMario__ConstPool__TABLE_h2335744c_0;
extern const VlUnpacked<CData/*0:0*/, 128> VCoproDrMario__ConstPool__TABLE_h3046dbb4_0;
extern const VlUnpacked<CData/*3:0*/, 2048> VCoproDrMario__ConstPool__TABLE_h00ffe440_0;
extern const VlUnpacked<CData/*1:0*/, 2048> VCoproDrMario__ConstPool__TABLE_h8ffa5a2b_0;
extern const VlUnpacked<CData/*0:0*/, 512> VCoproDrMario__ConstPool__TABLE_hafeef89d_0;
extern const VlUnpacked<CData/*0:0*/, 8192> VCoproDrMario__ConstPool__TABLE_hc377d77d_0;

VL_INLINE_OPT void VCoproDrMario___024root___ico_sequent__TOP__0(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___ico_sequent__TOP__0\n"); );
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
    CData/*6:0*/ __Vtableidx8;
    __Vtableidx8 = 0;
    // Body
    vlSelfRef.CoproDrMario__DOT__ce = vlSelfRef.ce;
    vlSelfRef.CoproDrMario__DOT__enable = vlSelfRef.enable;
    vlSelfRef.CoproDrMario__DOT__prg_ain = vlSelfRef.prg_ain;
    vlSelfRef.CoproDrMario__DOT__prg_read = vlSelfRef.prg_read;
    vlSelfRef.CoproDrMario__DOT__prg_write = vlSelfRef.prg_write;
    vlSelfRef.CoproDrMario__DOT__prg_din = vlSelfRef.prg_din;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__reset 
        = vlSelfRef.CoproDrMario__DOT__cpu_rst;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__RDY 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__RDY;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rst 
        = vlSelfRef.CoproDrMario__DOT__cpu_rst;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wslot 
        = vlSelfRef.CoproDrMario__DOT__lev_wslot;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_sl 
        = vlSelfRef.CoproDrMario__DOT__lev_a_sl;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_o4 
        = vlSelfRef.CoproDrMario__DOT__lev_a_o4;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_col 
        = vlSelfRef.CoproDrMario__DOT__lev_a_col;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_ca 
        = vlSelfRef.CoproDrMario__DOT__lev_a_ca;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_cb 
        = vlSelfRef.CoproDrMario__DOT__lev_a_cb;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_fix 
        = vlSelfRef.CoproDrMario__DOT__lev_a_fix;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_chw 
        = vlSelfRef.CoproDrMario__DOT__lev_a_chw;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__address_b 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sr_addr;
    vlSelfRef.CoproDrMario__DOT__wram__DOT__address_b 
        = vlSelfRef.CoproDrMario__DOT__hb_addr;
    vlSelfRef.CoproDrMario__DOT__wram__DOT__data_b 
        = vlSelfRef.CoproDrMario__DOT__hb_din;
    vlSelfRef.CoproDrMario__DOT__wram__DOT__wren_b 
        = vlSelfRef.CoproDrMario__DOT__hb_we;
    vlSelfRef.prg_dout = vlSelfRef.CoproDrMario__DOT__wram__DOT__q_b;
    vlSelfRef.CoproDrMario__DOT__prg_dout = vlSelfRef.CoproDrMario__DOT__wram__DOT__q_b;
    vlSelfRef.CoproDrMario__DOT__ram_b_q = vlSelfRef.CoproDrMario__DOT__wram__DOT__q_b;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c 
        = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r 
        = (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo) 
                   >> 3U));
    vlSelfRef.CoproDrMario__DOT__lev_sco = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sco;
    vlSelfRef.CoproDrMario__DOT__ram_a_q = vlSelfRef.CoproDrMario__DOT__wram__DOT__q_a;
    vlSelfRef.CoproDrMario__DOT__lev_win = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__win;
    vlSelfRef.CoproDrMario__DOT__lev_strand = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__strand;
    vlSelfRef.CoproDrMario__DOT__lev_legal = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__legal;
    vlSelfRef.CoproDrMario__DOT__lev_done = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done;
    vlSelfRef.CoproDrMario__DOT__lev_rvc = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_cells;
    vlSelfRef.CoproDrMario__DOT__lev_rvv = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_vir;
    vlSelfRef.CoproDrMario__DOT__lev_imm = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__imm;
    vlSelfRef.CoproDrMario__DOT__lev_dv_fallback = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dv_fallback;
    vlSelfRef.CoproDrMario__DOT__lev_chain = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AN = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__N;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotq 
        = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__q_b));
    vlSelfRef.CoproDrMario__DOT__cpu_rst_src = ((0U 
                                                 != (IData)(vlSelfRef.CoproDrMario__DOT__rst_cnt)) 
                                                | (IData)(vlSelfRef.CoproDrMario__DOT__parked));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_pix 
        = (0x7fU & ((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk))
                     ? ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i) 
                        - (IData)(8U)) : ((2U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk))
                                           ? ((IData)(8U) 
                                              + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i))
                                           : ((3U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk))
                                               ? ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i) 
                                                  - (IData)(1U))
                                               : ((IData)(1U) 
                                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i))))));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_phas 
        = (((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk)) 
            & (0U != (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i) 
                              >> 3U)))) | (((2U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk)) 
                                            & (0xfU 
                                               != (0xfU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i) 
                                                      >> 3U)))) 
                                           | (((3U 
                                                == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk)) 
                                               & (0U 
                                                  != 
                                                  (7U 
                                                   & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i)))) 
                                              | ((4U 
                                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk)) 
                                                 & (7U 
                                                    != 
                                                    (7U 
                                                     & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i)))))));
    vlSelfRef.CoproDrMario__DOT__clk = vlSelfRef.clk;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AZ = 
        (1U & (~ (IData)((0U != (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__OUT)))));
    vlSelfRef.CoproDrMario__DOT__copro_sel = ((IData)(vlSelfRef.enable) 
                                              & (0x5000U 
                                                 == 
                                                 (0xfe00U 
                                                  & (IData)(vlSelfRef.prg_ain))));
    __Vtableidx3 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__plp) 
                     << 7U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__load_reg) 
                                << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__write_register 
        = VCoproDrMario__ConstPool__TABLE_hf9320a1f_0
        [__Vtableidx3];
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__HC = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__HC;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rdy_h_sq 
        = ((4U <= (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_hi) 
                    - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_lo)) 
                   - (IData)(1U))) ? VL_EXTEND_II(18,9, 
                                                  ([&]() {
                    vlSelfRef.__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__n 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_h;
                    vlSelfRef.__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__Vfuncout 
                        = (0x1ffU & ((IData)(vlSelfRef.__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__n) 
                                     * (IData)(vlSelfRef.__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__n)));
                }(), (IData)(vlSelfRef.__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__Vfuncout)))
            : 0U);
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AV = 
        ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__AI7) 
         ^ ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__BI7) 
            ^ ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CO) 
               ^ (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__N))));
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
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_qb 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__q_b;
    vlSelfRef.CoproDrMario__DOT__clk_cpu = vlSelfRef.clk_cpu;
    CoproDrMario__DOT__cpu6502__DOT____Vcellinp__ALU__BCD 
        = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adc_bcd) 
           & (0xdU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCH 
        = (0xffU & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC) 
                    >> 8U));
    __Vtableidx2 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__store) 
                     << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__WE = 
        VCoproDrMario__ConstPool__TABLE_h3046dbb4_0
        [__Vtableidx2];
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__P = 
        (0x30U | ((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__N) 
                    << 7U) | ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__V) 
                              << 6U)) | ((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__D) 
                                           << 3U) | 
                                          ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__I) 
                                           << 2U)) 
                                         | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__Z) 
                                             << 1U) 
                                            | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C)))));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[1U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [1U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[2U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [2U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[3U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [3U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[4U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [4U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[5U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [5U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[6U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [6U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[7U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [7U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[8U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [8U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[9U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [9U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xaU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xaU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xbU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xbU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xcU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xcU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xdU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xdU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xeU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xeU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xfU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xfU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x10U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x10U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x11U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x11U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x12U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x12U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x13U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x13U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x14U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x14U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x15U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x15U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x16U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x16U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x17U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x17U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x18U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x18U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x19U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x19U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x20U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x20U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x21U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x21U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x22U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x22U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x23U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x23U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x24U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x24U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x25U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x25U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x26U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x26U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x27U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x27U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x28U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x28U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x29U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x29U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x30U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x30U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x31U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x31U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x32U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x32U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x33U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x33U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x34U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x34U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x35U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x35U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x36U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x36U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x37U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x37U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x38U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x38U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x39U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x39U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x40U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x40U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x41U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x41U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x42U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x42U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x43U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x43U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x44U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x44U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x45U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x45U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x46U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x46U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x47U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x47U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x48U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x48U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x49U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x49U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x50U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x50U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x51U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x51U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x52U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x52U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x53U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x53U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x54U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x54U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x55U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x55U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x56U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x56U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x57U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x57U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x58U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x58U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x59U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x59U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x60U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x60U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x61U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x61U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x62U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x62U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x63U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x63U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x64U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x64U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x65U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x65U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x66U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x66U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x67U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x67U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x68U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x68U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x69U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x69U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x70U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x70U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x71U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x71U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x72U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x72U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x73U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x73U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x74U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x74U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x75U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x75U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x76U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x76U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x77U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x77U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x78U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x78U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x79U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x79U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [0U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[1U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [1U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [1U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[2U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [2U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [2U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[3U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [3U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [3U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[4U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [4U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [4U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[5U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [5U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [5U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[6U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [6U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [6U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[7U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [7U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [7U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[8U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [8U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [8U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[9U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [9U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [9U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xaU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xaU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xaU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xbU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xbU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xbU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xcU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xcU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xcU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xdU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xdU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xdU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xeU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xeU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xeU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xfU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xfU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xfU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x10U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x10U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x10U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x11U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x11U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x11U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x12U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x12U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x12U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x13U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x13U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x13U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x14U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x14U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x14U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x15U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x15U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x15U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x16U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x16U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x16U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x17U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x17U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x17U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x18U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x18U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x18U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x19U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x19U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x19U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x20U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x20U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x20U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x21U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x21U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x21U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x22U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x22U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x22U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x23U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x23U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x23U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x24U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x24U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x24U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x25U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x25U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x25U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x26U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x26U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x26U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x27U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x27U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x27U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x28U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x28U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x28U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x29U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x29U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x29U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x30U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x30U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x30U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x31U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x31U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x31U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x32U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x32U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x32U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x33U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x33U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x33U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x34U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x34U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x34U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x35U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x35U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x35U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x36U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x36U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x36U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x37U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x37U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x37U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x38U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x38U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x38U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x39U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x39U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x39U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x40U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x40U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x40U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x41U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x41U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x41U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x42U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x42U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x42U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x43U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x43U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x43U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x44U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x44U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x44U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x45U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x45U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x45U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x46U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x46U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x46U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x47U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x47U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x47U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x48U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x48U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x48U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x49U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x49U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x49U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x50U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x50U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x50U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x51U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x51U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x51U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x52U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x52U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x52U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x53U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x53U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x53U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x54U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x54U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x54U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x55U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x55U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x55U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x56U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x56U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x56U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x57U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x57U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x57U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x58U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x58U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x58U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x59U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x59U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x59U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x60U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x60U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x60U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x61U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x61U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x61U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x62U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x62U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x62U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x63U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x63U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x63U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x64U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x64U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x64U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x65U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x65U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x65U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x66U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x66U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x66U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x67U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x67U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x67U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x68U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x68U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x68U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x69U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x69U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x69U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x70U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x70U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x70U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x71U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x71U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x71U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x72U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x72U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x72U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x73U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x73U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x73U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x74U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x74U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x74U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x75U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x75U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x75U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x76U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x76U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x76U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x77U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x77U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x77U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x78U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x78U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x78U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x79U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x79U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x79U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[1U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [1U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[2U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [2U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[3U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [3U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[4U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [4U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[5U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [5U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[6U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [6U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[7U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [7U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[8U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [8U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[9U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [9U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xaU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xaU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xbU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xbU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xcU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xcU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xdU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xdU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xeU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xeU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xfU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xfU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x10U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x10U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x11U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x11U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x12U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x12U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x13U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x13U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x14U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x14U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x15U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x15U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x16U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x16U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x17U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x17U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x18U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x18U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x19U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x19U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x20U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x20U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x21U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x21U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x22U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x22U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x23U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x23U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x24U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x24U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x25U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x25U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x26U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x26U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x27U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x27U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x28U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x28U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x29U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x29U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x30U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x30U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x31U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x31U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x32U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x32U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x33U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x33U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x34U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x34U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x35U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x35U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x36U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x36U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x37U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x37U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x38U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x38U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x39U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x39U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x40U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x40U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x41U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x41U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x42U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x42U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x43U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x43U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x44U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x44U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x45U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x45U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x46U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x46U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x47U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x47U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x48U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x48U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x49U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x49U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x50U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x50U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x51U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x51U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x52U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x52U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x53U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x53U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x54U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x54U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x55U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x55U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x56U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x56U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x57U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x57U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x58U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x58U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x59U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x59U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x60U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x60U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x61U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x61U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x62U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x62U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x63U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x63U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x64U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x64U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x65U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x65U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x66U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x66U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x67U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x67U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x68U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x68U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x69U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x69U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x70U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x70U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x71U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x71U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x72U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x72U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x73U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x73U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x74U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x74U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x75U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x75U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x76U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x76U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x77U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x77U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x78U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x78U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x79U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x79U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7fU]);
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_shift_right 
        = (((0xdU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
            | ((0x24U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
               | (0x23U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) 
           & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__shift_right));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CO;
    __Vtableidx5 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__backwards) 
                     << 0xaU) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__op) 
                                  << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op 
        = VCoproDrMario__ConstPool__TABLE_h00ffe440_0
        [__Vtableidx5];
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCL 
        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__OUT;
    __Vtableidx4 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__dst_reg) 
                     << 9U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__index_y) 
                                << 8U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__src_reg) 
                                           << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regsel 
        = VCoproDrMario__ConstPool__TABLE_h8ffa5a2b_0
        [__Vtableidx4];
    vlSelfRef.CoproDrMario__DOT__DI = ((IData)(vlSelfRef.CoproDrMario__DOT__sel_vec_d)
                                        ? ((IData)(vlSelfRef.CoproDrMario__DOT__ab0_d)
                                            ? 0xbfU
                                            : 0x80U)
                                        : ((IData)(vlSelfRef.CoproDrMario__DOT__sel_rom_d)
                                            ? (IData)(vlSelfRef.CoproDrMario__DOT__rom_q)
                                            : ((IData)(vlSelfRef.CoproDrMario__DOT__sel_lev_d)
                                                ? (IData)(vlSelfRef.CoproDrMario__DOT__lev_q)
                                                : ((IData)(vlSelfRef.CoproDrMario__DOT__sel_ram_d)
                                                    ? (IData)(vlSelfRef.CoproDrMario__DOT__wram__DOT__q_a)
                                                    : 0xffU))));
    vlSelfRef.CoproDrMario__DOT__wram__DOT__clock_b 
        = vlSelfRef.CoproDrMario__DOT__clk;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__Z 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AZ;
    vlSelfRef.copro_sel = vlSelfRef.CoproDrMario__DOT__copro_sel;
    if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adj_bcd) {
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adc_bcd) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADJL 
                = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__HC)
                    ? 6U : 0U);
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADJH 
                = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO)
                    ? 6U : 0U);
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADJL 
                = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__HC)
                    ? 0U : 0xaU);
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADJH 
                = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO)
                    ? 0U : 0xaU);
        }
    } else {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADJL = 0U;
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADJH = 0U;
    }
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__V 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AV;
    vlSelfRef.CoproDrMario__DOT__wram__DOT__clock_a 
        = vlSelfRef.CoproDrMario__DOT__clk_cpu;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__clk 
        = vlSelfRef.CoproDrMario__DOT__clk_cpu;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__clk 
        = vlSelfRef.CoproDrMario__DOT__clk_cpu;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__BCD 
        = CoproDrMario__DOT__cpu6502__DOT____Vcellinp__ALU__BCD;
    vlSelfRef.CoproDrMario__DOT__WE = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__WE;
    CoproDrMario__DOT____VdfgRegularize_hb6d3a560_2_3 
        = ((~ (IData)(vlSelfRef.CoproDrMario__DOT__cpu_rst)) 
           & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__WE));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
        [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo];
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__right 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_shift_right;
    __Vtableidx1 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__backwards) 
                     << 8U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO) 
                                << 7U) | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge) 
                                           << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_inc 
        = VCoproDrMario__ConstPool__TABLE_hafeef89d_0
        [__Vtableidx1];
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
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__op 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AXYS
        [vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regsel];
    CoproDrMario__DOT__cpu6502__DOT____VdfgExtracted_hdce86eaa__0 
        = (0x100U | vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AXYS
           [vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regsel]);
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DI = vlSelfRef.CoproDrMario__DOT__DI;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR = 
        ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge)
          ? 0U : ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IRHOLD_valid)
                   ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IRHOLD)
                   : (IData)(vlSelfRef.CoproDrMario__DOT__DI)));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX 
        = vlSelfRef.CoproDrMario__DOT__DI;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__clk 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__clk;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__clock_a 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__clk;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__clock_b 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__clk;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CI 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CI;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__adder_CI 
        = ((~ ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_shift_right) 
               | (3U == (3U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__alu_op) 
                               >> 2U))))) & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CI));
    if ((0x20U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if ((0x10U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
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
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
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
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
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
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & 0U);
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                            ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                            : (0x100U | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD)));
                }
            }
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC)
                    : ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC)));
        } else {
            if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
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
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
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
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & 0U);
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
                }
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            }
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
        }
    } else if ((0x10U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if ((8U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & 0U);
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
                }
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
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC));
            }
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                    ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC)
                    : ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC)));
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
            if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                            = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                            = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                    } else {
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                    }
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                            ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL))
                            : (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD)));
                }
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
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
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
        }
    } else if ((8U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
            if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD;
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                }
            } else {
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__load_only)
                                     ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile)));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                        = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge)
                            ? (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH) 
                                << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL))
                            : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & 0U);
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
                }
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            }
        } else if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
                    = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge)
                        ? (0xefU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__P))
                        : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__P));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__res)
                        ? 0xfffcU : ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge)
                                      ? 0xfffaU : 0xfffeU));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                    = (0x100U | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
            }
        } else {
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
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
        }
    } else {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO 
            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile;
        if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                        = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCL));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & 0U);
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL));
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                        = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI = 0U;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
                }
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX));
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCL;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
                } else {
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                        = (0xffU & 0U);
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
                    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB 
                        = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                            << 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL));
                }
            }
        } else {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC;
            if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                                 ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regfile)));
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
            } else {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI 
                    = (0xffU & 0U);
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI 
                    = ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                        ? 0U : (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX));
            }
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
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__BI 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__BI;
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

void VCoproDrMario___024root___eval_triggers__ico(VCoproDrMario___024root* vlSelf);

bool VCoproDrMario___024root___eval_phase__ico(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_phase__ico\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    CData/*0:0*/ __VicoExecute;
    // Body
    VCoproDrMario___024root___eval_triggers__ico(vlSelf);
    __VicoExecute = vlSelfRef.__VicoTriggered.any();
    if (__VicoExecute) {
        VCoproDrMario___024root___eval_ico(vlSelf);
    }
    return (__VicoExecute);
}

void VCoproDrMario___024root___eval_act(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_act\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
}

void VCoproDrMario___024root___nba_sequent__TOP__0(VCoproDrMario___024root* vlSelf);
void VCoproDrMario___024root___nba_sequent__TOP__1(VCoproDrMario___024root* vlSelf);
void VCoproDrMario___024root___nba_sequent__TOP__2(VCoproDrMario___024root* vlSelf);
void VCoproDrMario___024root___nba_sequent__TOP__3(VCoproDrMario___024root* vlSelf);
void VCoproDrMario___024root___nba_sequent__TOP__4(VCoproDrMario___024root* vlSelf);
void VCoproDrMario___024root___nba_sequent__TOP__5(VCoproDrMario___024root* vlSelf);
void VCoproDrMario___024root___nba_sequent__TOP__6(VCoproDrMario___024root* vlSelf);
void VCoproDrMario___024root___nba_sequent__TOP__7(VCoproDrMario___024root* vlSelf);
void VCoproDrMario___024root___nba_comb__TOP__0(VCoproDrMario___024root* vlSelf);

void VCoproDrMario___024root___eval_nba(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_nba\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VCoproDrMario___024root___nba_sequent__TOP__0(vlSelf);
    }
    if ((3ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VCoproDrMario___024root___nba_sequent__TOP__1(vlSelf);
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VCoproDrMario___024root___nba_sequent__TOP__2(vlSelf);
    }
    if ((5ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VCoproDrMario___024root___nba_sequent__TOP__3(vlSelf);
    }
    if ((1ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VCoproDrMario___024root___nba_sequent__TOP__4(vlSelf);
    }
    if ((3ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VCoproDrMario___024root___nba_sequent__TOP__5(vlSelf);
    }
    if ((5ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VCoproDrMario___024root___nba_sequent__TOP__6(vlSelf);
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VCoproDrMario___024root___nba_sequent__TOP__7(vlSelf);
    }
    if ((5ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VCoproDrMario___024root___nba_comb__TOP__0(vlSelf);
    }
}

extern const VlUnpacked<CData/*0:0*/, 16384> VCoproDrMario__ConstPool__TABLE_h5eb454e9_0;
extern const VlUnpacked<CData/*3:0*/, 16384> VCoproDrMario__ConstPool__TABLE_hc29132ea_0;

VL_INLINE_OPT void VCoproDrMario___024root___nba_sequent__TOP__0(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___nba_sequent__TOP__0\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    SData/*8:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__3__Vfuncout;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__3__Vfuncout = 0;
    CData/*4:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__3__n;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__3__n = 0;
    SData/*8:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__4__Vfuncout;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__4__Vfuncout = 0;
    CData/*4:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__4__n;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__4__n = 0;
    SData/*8:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__5__Vfuncout;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__5__Vfuncout = 0;
    CData/*4:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__5__n;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__5__n = 0;
    SData/*8:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__6__Vfuncout;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__6__Vfuncout = 0;
    CData/*4:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__6__n;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__6__n = 0;
    SData/*8:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__7__Vfuncout;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__7__Vfuncout = 0;
    CData/*4:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__7__n;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__7__n = 0;
    SData/*8:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__8__Vfuncout;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__8__Vfuncout = 0;
    CData/*4:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__8__n;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__8__n = 0;
    SData/*8:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__9__Vfuncout;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__9__Vfuncout = 0;
    CData/*4:0*/ __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__9__n;
    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__9__n = 0;
    SData/*13:0*/ __Vtableidx7;
    __Vtableidx7 = 0;
    CData/*2:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__bl_rq;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__bl_rq = 0;
    IData/*31:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_fire;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_fire = 0;
    IData/*31:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_used;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_used = 0;
    CData/*5:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__st;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_mode;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_mode = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__holes;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__holes = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__setup;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__setup = 0;
    SData/*10:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution = 0;
    SData/*9:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__buried;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__buried = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__anyvir;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__anyvir = 0;
    SData/*12:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60 = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__wc;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__wc = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__seen;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__seen = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__cmd_l;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__cmd_l = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__node_leaf;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__node_leaf = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_cells;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_cells = 0;
    CData/*5:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_vir;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_vir = 0;
    VlWide<4>/*127:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__markb;
    VL_ZERO_W(128, __Vdly__CoproDrMario__DOT__leafeval__DOT__markb);
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__anyclear;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__anyclear = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__chain;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__chain = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__chain_bonus;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__chain_bonus = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__fullscan;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__fullscan = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp = 0;
    SData/*9:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__od_bur;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__od_bur = 0;
    SData/*9:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_bur;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_bur = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__od_rdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__od_rdy = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_rdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_rdy = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__od_vrdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__od_vrdy = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_vrdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_vrdy = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__od_set;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__od_set = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_set;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_set = 0;
    SData/*12:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_matched;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_matched = 0;
    SData/*10:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_pol;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_pol = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_holes;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_holes = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dphase;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dphase = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__strand;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__strand = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__str_i;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__str_i = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp2;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp2 = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__cpw_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__cpw_p = 0;
    SData/*8:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__sr_addr;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__sr_addr = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__fo1;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__fo1 = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__off_b;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__off_b = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__off_a;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__off_a = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__pca;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__pca = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__pcb;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__pcb = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__li;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__srun;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__srun = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__smcol;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__smcol = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__soff;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__soff = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__srstart;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__srstart = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_m;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_m = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_vir;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_vir = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_i;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_i = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__gr;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__gr = 0;
    CData/*2:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__gc;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__gc = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__gmoved;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__gmoved = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__g_has;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__g_has = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__g_k0;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__g_k0 = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__g_k1;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__g_k1 = 0;
    CData/*2:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__g_cell;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__g_cell = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_isrep;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_isrep = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_occ;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_occ = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_vir;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_vir = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_blk0;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_blk0 = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__g_do;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__g_do = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__gk1;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__gk1 = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__vo;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vo = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__run_h;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_h = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__run_v;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_v = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__p = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__span_lo;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__span_lo = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__span_hi;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__span_hi = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_lo;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_lo = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_hi;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_hi = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_maxh;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_maxh = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_holes;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_holes = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_toprisk;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_toprisk = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_spawn;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_spawn = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_setup;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_setup = 0;
    SData/*10:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_pol;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_pol = 0;
    SData/*9:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_buried;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_buried = 0;
    SData/*12:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_matched;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_matched = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_rdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_rdy = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_vrdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_vrdy = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__base_anyvir;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_anyvir = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh_p = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__holes_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__holes_p = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk_p = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn_p = 0;
    CData/*7:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__setup_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__setup_p = 0;
    SData/*10:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution_p = 0;
    SData/*9:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__buried_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__buried_p = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext_p = 0;
    SData/*15:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy_p = 0;
    SData/*12:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60_p = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt = 0;
    CData/*6:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dbur_new;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dbur_new = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dcolstep;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dcolstep = 0;
    CData/*2:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dcol;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dcol = 0;
    CData/*4:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__drow;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__drow = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dlmask;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dlmask = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dwrow;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dwrow = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dwsecond;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dwsecond = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dws;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dws = 0;
    CData/*3:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__dwhi;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dwhi = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_c;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_c = 0;
    CData/*0:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_p = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_u;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_u = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_d;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_d = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_l;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_l = 0;
    CData/*1:0*/ __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_r;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_r = 0;
    CData/*7:0*/ __VdlyVal__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0;
    __VdlyVal__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0 = 0;
    CData/*1:0*/ __VdlyDim0__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0;
    __VdlyDim0__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0;
    __VdlySet__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0 = 0;
    CData/*2:0*/ __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v0;
    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v0 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v0;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v0 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v0;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v0 = 0;
    CData/*2:0*/ __VdlyVal__CoproDrMario__DOT__leafeval__DOT__blink__v0;
    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__blink__v0 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__blink__v0;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__blink__v0 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__blink__v0;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__blink__v0 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v0;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v0 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v1;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v1 = 0;
    CData/*2:0*/ __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v1;
    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v1 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v1;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v1 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v1;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v1 = 0;
    CData/*2:0*/ __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v2;
    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v2 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v2;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v2 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v2;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v2 = 0;
    CData/*2:0*/ __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v3;
    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v3 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v3;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v3 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v3;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v3 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v4;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v4 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v4;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v4 = 0;
    CData/*2:0*/ __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v5;
    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v5 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v5;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v5 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v5;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v5 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v6;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v6 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v6;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v6 = 0;
    CData/*2:0*/ __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v7;
    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v7 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v7;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v7 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v7;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v7 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v8;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v8 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v8;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v8 = 0;
    CData/*4:0*/ __VdlyVal__CoproDrMario__DOT__leafeval__DOT__colh__v8;
    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__colh__v8 = 0;
    CData/*2:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__colh__v8;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__colh__v8 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v8;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v8 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v9;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v9 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v9;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v9 = 0;
    CData/*6:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v10;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v10 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v10;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v10 = 0;
    CData/*7:0*/ __VdlyVal__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0;
    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0 = 0;
    SData/*8:0*/ __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0;
    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0 = 0;
    CData/*0:0*/ __VdlySet__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0 = 0;
    // Body
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0 = 0U;
    __VdlySet__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0 = 0U;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_mode 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_mode;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__delta_mode;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__maxh;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__holes 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__holes;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__toprisk;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__spawn;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__setup 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__setup;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pollution;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__buried 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__buried;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rdy_ext;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vrdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__anyvir 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__anyvir;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__matched60;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__wc = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__seen 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__seen;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fillcnt;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curcol;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curlen;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vseen;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__cmd_l 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cmd_l;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__node_leaf 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__node_leaf;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[0U] 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__markb[0U];
    __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[1U] 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__markb[1U];
    __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[2U] 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__markb[2U];
    __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[3U] 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__markb[3U];
    __Vdly__CoproDrMario__DOT__leafeval__DOT__anyclear 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__anyclear;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__chain_bonus 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain_bonus;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__fullscan 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fullscan;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__od_bur 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_bur;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_bur 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_bur;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__od_rdy 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_rdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_rdy 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_rdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__od_vrdy 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_vrdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_vrdy 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_vrdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__od_set 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_set;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_set 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_set;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_matched 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dd_matched;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_pol 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dd_pol;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_holes 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dd_holes;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dphase 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dphase;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__str_i 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__fo1 = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fo1;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__pca = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pca;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__pcb = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pcb;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__li = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scnt;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__srun 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__smcol 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__smcol;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__soff 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__soff;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__srstart 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_vir 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_vir;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__gr = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__gc = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__gmoved 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gmoved;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__g_has 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_has;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__g_k1 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k1;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__g_cell 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_cell;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_isrep 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_isrep;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_occ 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_occ;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_vir 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_vir;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_blk0 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_blk0;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_v 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_v;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__p = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_lo 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_lo;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_hi 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_hi;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_maxh 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_maxh;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_holes 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_holes;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_toprisk 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_toprisk;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_spawn 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_spawn;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_setup 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_setup;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_pol 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_pol;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_buried 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_buried;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_matched 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_matched;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_rdy 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_rdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_vrdy 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_vrdy;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_anyvir 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_anyvir;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__maxh_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__holes_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__holes_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__toprisk_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__spawn_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__setup_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__setup_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pollution_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__buried_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__buried_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rdy_ext_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vrdy_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__matched60_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dstep;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dscnt;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsoff;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dbur_new 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dbur_new;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dcolstep 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcolstep;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dcol 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcol;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__drow 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drow;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dlmask 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dlmask;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dwrow 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dwsecond 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwsecond;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dws = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__dwhi 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwhi;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_c 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_c;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_u 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_u;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_d 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_d;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_l 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_l;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_r 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_r;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__blink__v0 = 0U;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_cells 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_cells;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_vir 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_vir;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__chain 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__strand 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__strand;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__sr_addr 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sr_addr;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v0 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v1 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v8 = 0U;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_h 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_h;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__span_lo 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_lo;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__span_hi 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_hi;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__vo = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp2 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__off_b 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__off_a 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__g_k0 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k0;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__gk1 = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gk1;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__cpw_p 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cpw_p;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_i 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_m 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_m;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__g_do 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_do;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__bl_rq 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_rq;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_fire 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__byp_fire;
    __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_used 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__byp_used;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v0 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v1 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v2 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v3 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v4 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v5 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v6 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v7 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v8 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v9 = 0U;
    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v10 = 0U;
    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_we) {
        __VdlyVal__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0 
            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_wd;
        __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0 
            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_wa;
        __VdlySet__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0 = 1U;
    }
    if (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge) 
         & (0xbU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge = 0U;
    }
    if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__write_register) {
        __VdlyVal__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0 
            = ((0x1aU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))
                ? (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX)
                : ((0xf0U & ((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                               >> 4U) + (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADJH)) 
                             << 4U)) | (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                                                + (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADJL)))));
        __VdlyDim0__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0 
            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regsel;
        __VdlySet__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0 = 1U;
    }
    __Vdly__CoproDrMario__DOT__leafeval__DOT__bl_rq 
        = (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we) 
            & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa) 
               == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra)))
            ? (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd)
            : vlSelfRef.CoproDrMario__DOT__leafeval__DOT__blink
           [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra]);
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_1 = 0U;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__q_a 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem
        [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_wa];
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__N 
        = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp) 
                 >> 7U));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__HC 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_HC;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__q_b 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem
        [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sr_addr];
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__cond_code 
        = (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR) 
                 >> 5U));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__BI7 
        = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_BI) 
                 >> 7U));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__AI7 
        = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AI) 
                 >> 7U));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CO 
        = (IData)((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp) 
                    >> 8U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CO9)));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIHOLD 
        = vlSelfRef.CoproDrMario__DOT__DI;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__OUT 
        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC = 
        (0xffffU & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_temp) 
                    + (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC_inc)));
    vlSelfRef.CoproDrMario__DOT__sel_rom_d = vlSelfRef.CoproDrMario__DOT__a_rom;
    vlSelfRef.CoproDrMario__DOT__sel_vec_d = vlSelfRef.CoproDrMario__DOT__a_vec;
    vlSelfRef.CoproDrMario__DOT__sel_ram_d = vlSelfRef.CoproDrMario__DOT__a_ram;
    vlSelfRef.CoproDrMario__DOT__ab0_d = (1U & (IData)(vlSelfRef.CoproDrMario__DOT__AB));
    vlSelfRef.CoproDrMario__DOT__rom_q = vlSelfRef.CoproDrMario__DOT__rom
        [(0x3fffU & (IData)(vlSelfRef.CoproDrMario__DOT__AB))];
    vlSelfRef.CoproDrMario__DOT__wram__DOT__q_a = vlSelfRef.CoproDrMario__DOT__wram__DOT__mem
        [vlSelfRef.CoproDrMario__DOT__a_addr];
    vlSelfRef.CoproDrMario__DOT__lev_q = (0xffU & (
                                                   (8U 
                                                    & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                    ? 
                                                   ((4U 
                                                     & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                     ? 
                                                    ((2U 
                                                      & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                      ? 
                                                     ((1U 
                                                       & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                       ? (IData)(vlSelfRef.CoproDrMario__DOT__lev_done)
                                                       : (IData)(vlSelfRef.CoproDrMario__DOT__lev_chain))
                                                      : 
                                                     ((1U 
                                                       & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                       ? (IData)(vlSelfRef.CoproDrMario__DOT__lev_dv_fallback)
                                                       : 
                                                      ((IData)(vlSelfRef.CoproDrMario__DOT__lev_imm) 
                                                       >> 8U)))
                                                     : 
                                                    ((2U 
                                                      & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                      ? 
                                                     ((1U 
                                                       & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                       ? (IData)(vlSelfRef.CoproDrMario__DOT__lev_imm)
                                                       : (IData)(vlSelfRef.CoproDrMario__DOT__lev_rvv))
                                                      : 
                                                     ((1U 
                                                       & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                       ? (IData)(vlSelfRef.CoproDrMario__DOT__lev_rvc)
                                                       : 
                                                      ((0xeU 
                                                        == 
                                                        (0xfU 
                                                         & ((IData)(vlSelfRef.CoproDrMario__DOT__AB) 
                                                            >> 4U)))
                                                        ? (IData)(vlSelfRef.CoproDrMario__DOT__lev_legal)
                                                        : (IData)(vlSelfRef.CoproDrMario__DOT__lev_done)))))
                                                    : 
                                                   ((4U 
                                                     & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                     ? (IData)(vlSelfRef.CoproDrMario__DOT__lev_done)
                                                     : 
                                                    ((2U 
                                                      & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                      ? 
                                                     ((1U 
                                                       & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                       ? (IData)(vlSelfRef.CoproDrMario__DOT__lev_strand)
                                                       : (IData)(vlSelfRef.CoproDrMario__DOT__lev_win))
                                                      : 
                                                     ((1U 
                                                       & (IData)(vlSelfRef.CoproDrMario__DOT__AB))
                                                       ? 
                                                      ((IData)(vlSelfRef.CoproDrMario__DOT__lev_sco) 
                                                       >> 8U)
                                                       : (IData)(vlSelfRef.CoproDrMario__DOT__lev_sco))))));
    vlSelfRef.CoproDrMario__DOT__sel_lev_d = vlSelfRef.CoproDrMario__DOT__a_lev;
    __Vtableidx7 = (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR) 
                     << 6U) | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state));
    if (VCoproDrMario__ConstPool__TABLE_h5eb454e9_0
        [__Vtableidx7]) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__op 
            = VCoproDrMario__ConstPool__TABLE_hc29132ea_0
            [__Vtableidx7];
    }
    if ((((((0x21U != (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
            & (0x22U != (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
           & (0x1eU != (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
          & (0x1fU != (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) 
         & (0x20U != (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABL 
            = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ABH 
            = (0xffU & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB) 
                        >> 8U));
    }
    if ((1U & (~ (IData)(vlSelfRef.CoproDrMario__DOT__cpu_rst)))) {
        if (((0x1eU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
             | (0x21U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IRHOLD 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX;
        }
    }
    if ((0xbU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__I = 1U;
    } else if ((0x27U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__I 
            = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                     >> 2U));
    } else if ((0x24U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__sei) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__I = 1U;
        }
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__cli) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__I = 0U;
        }
    } else if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__plp) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__I 
                = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                         >> 2U));
        }
    }
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adj_bcd 
        = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adc_sbc) 
           & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__D));
    if ((0x2eU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__N 
            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AN;
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__Z 
            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AZ;
    } else if ((0x27U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__N 
            = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                     >> 7U));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__Z 
            = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                     >> 1U));
    } else if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__plp) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__N 
                = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                         >> 7U));
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__Z 
                = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                         >> 1U));
        } else {
            if ((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__load_reg) 
                  & (1U != (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regsel))) 
                 | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__compare))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__N 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AN;
            }
            if (((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__load_reg) 
                   & (1U != (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__regsel))) 
                  | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__compare)) 
                 | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__bit_ins))) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__Z 
                    = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AZ;
            }
        }
    } else if (((0xdU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
                & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__bit_ins))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__N 
            = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                     >> 7U));
    }
    if (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__shift) 
         & (0x2eU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C 
            = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO;
    } else if ((0x27U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C 
            = (1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX));
    } else if (((~ (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__write_back)) 
                & (0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        if ((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adc_sbc) 
              | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__shift)) 
             | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__compare))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__CO;
        } else if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__plp) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C 
                = (1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD));
        } else {
            if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__sec) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C = 1U;
            }
            if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__clc) {
                vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C = 0U;
            }
        }
    }
    if (__VdlySet__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AXYS[__VdlyDim0__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0] 
            = __VdlyVal__CoproDrMario__DOT__cpu6502__DOT__AXYS__v0;
    }
    if (vlSelfRef.CoproDrMario__DOT__cpu_rst) {
        __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_fire = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__byp_fire 
            = __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_fire;
        __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_used = 0U;
    } else {
        if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we) 
             & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa) 
                == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra)))) {
            __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_fire 
                = ((IData)(1U) + vlSelfRef.CoproDrMario__DOT__leafeval__DOT__byp_fire);
            if ((((((0x35U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)) 
                    | (0x36U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                   | (0x37U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                  | (0x1bU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                 | (0x38U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_used 
                    = ((IData)(1U) + vlSelfRef.CoproDrMario__DOT__leafeval__DOT__byp_used);
            }
        }
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__byp_fire 
            = __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_fire;
    }
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__byp_used 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__byp_used;
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0] 
            = __VdlyVal__CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem__v0;
    }
    if (vlSelfRef.CoproDrMario__DOT__cpu_rst) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IRHOLD_valid = 0U;
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__res = 1U;
    } else {
        if (((0x1eU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
             | (0x21U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IRHOLD_valid = 1U;
        } else if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IRHOLD_valid = 0U;
        }
        if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__res = 0U;
        }
    }
    if ((0x27U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__V 
            = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                     >> 6U));
    } else if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adc_sbc) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__V 
                = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AV;
        }
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__clv) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__V = 0U;
        }
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__plp) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__V 
                = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                         >> 6U));
        }
    } else if (((0xdU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
                & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__bit_ins))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__V 
            = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                     >> 6U));
    }
    if (((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
         | (8U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adc_bcd 
            = ((0x61U == (0xe3U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
               && (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__D));
    }
    if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__brk 
            = (0U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__php 
            = (8U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__shift_right 
            = (0x42U == (0xc3U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__inc 
            = ((0xe6U == (0xe7U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
               || (0xc8U == (0xdfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__rotate 
            = ((0x2aU == (0xafU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
               || (0x26U == (0xa7U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__load_only 
            = (0xa0U == (0xe0U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__dst_reg 
            = ((((0xe8U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)) 
                 || (0xcaU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                || (0xa2U == (0xe3U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))))
                ? 2U : (((8U == (0xbfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                         || (0x9aU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                         ? 1U : ((((0x88U == (0xbfU 
                                              & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                                   || (0xa4U == (0xe7U 
                                                 & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                                  || (0xa0U == (0xf7U 
                                                & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))))
                                  ? 3U : 0U)));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__src_reg 
            = ((0xbaU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))
                ? 1U : (((((0x86U == (0xe7U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                           || (0x8aU == (0xebU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                          || (0xe0U == (0xf3U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                         || (0xcaU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))
                         ? 2U : (((((0x84U == (0xe7U 
                                               & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                                    || (0x98U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                                   || (0xc0U == (0xf3U 
                                                 & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                                  || (0x88U == (0xbfU 
                                                & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))))
                                  ? 3U : 0U)));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__index_y 
            = (((0x11U == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                || (0x96U == (0xd7U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
               || (9U == (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))));
    }
    if (vlSelfRef.CoproDrMario__DOT__cpu_rst) {
        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_cpw = 0U;
        __Vdly__CoproDrMario__DOT__leafeval__DOT__base_mode = 0U;
        __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dv_fallback = 0U;
    } else {
        if (((IData)(vlSelfRef.CoproDrMario__DOT__lev_wr_board) 
             & (0U == (IData)(vlSelfRef.CoproDrMario__DOT__lev_wslot)))) {
            __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v0 
                = vlSelfRef.CoproDrMario__DOT__lev_enc;
            __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v0 
                = (0x7fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AB));
            __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v0 = 1U;
        }
        if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_we) {
            __VdlyVal__CoproDrMario__DOT__leafeval__DOT__blink__v0 
                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wd;
            __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__blink__v0 
                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_wa;
            __VdlySet__CoproDrMario__DOT__leafeval__DOT__blink__v0 = 1U;
        }
        if (((((((((0U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)) 
                   | (0x11U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                  | (0x1cU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                 | (0x1aU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                | (0x1bU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
               | (0x12U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
              | (0x13U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
             | (0x14U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)))) {
            if ((0U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (((IData)(vlSelfRef.CoproDrMario__DOT__lev_start) 
                     | (IData)(vlSelfRef.CoproDrMario__DOT__lev_cmd_go))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 0U;
                    if (((IData)(vlSelfRef.CoproDrMario__DOT__lev_start) 
                         | (1U == (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO))))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__base_mode = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__holes = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__setup = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__buried = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__anyvir = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60 = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__wc = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__seen = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 1U;
                    } else if (((2U == (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO))) 
                                | (3U == (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO))))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__cmd_l 
                            = (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x11U;
                    } else if ((4U == (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO)))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__node_leaf = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__base_mode = 0U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__legal = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_cells = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_vir = 0U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__imm = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[0U] = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[1U] = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[2U] = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[3U] = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__anyclear = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__chain = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__chain_bonus = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__fullscan = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x12U;
                    } else if ((6U == (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO)))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__base_mode = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__node_leaf = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__holes = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__setup = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__buried = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__anyvir = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60 = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__wc = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__seen = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen = 0U;
                        __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v0 = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 1U;
                        __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v1 = 1U;
                    } else if ((7U == (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO)))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__node_leaf = 0U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dv_fallback = 0U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__legal = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_cells = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_vir = 0U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__imm = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[0U] = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[1U] = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[2U] = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[3U] = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__anyclear = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__chain = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__chain_bonus = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__fullscan = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__od_bur = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_bur = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__od_rdy = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_rdy = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__od_vrdy = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_vrdy = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__od_set = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_set = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_matched = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_pol = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_holes = 0U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__affbit[0U] = 0U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__affbit[1U] = 0U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__affbit[2U] = 0U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__affbit[3U] = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dphase = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x12U;
                    } else if ((8U == (0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DO)))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__strand = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__str_i = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x39U;
                    }
                }
            } else if ((0x11U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp2 = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__cpw_p = 0U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__sr_addr 
                    = ((IData)(vlSelfRef.CoproDrMario__DOT__lev_a_sl) 
                       << 7U);
                if ((2U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cmd_l))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x1cU;
                } else {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_cpw = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x38U;
                }
            } else if ((0x1cU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__sr_addr 
                    = (0x1ffU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sr_addr)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x1aU;
            } else if ((0x1aU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__sr_addr 
                    = (0x1ffU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sr_addr)));
                __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v1 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotq;
                __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v1 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2;
                __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v1 = 1U;
                if ((0x7fU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp2 
                        = (0x7fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2)));
                }
            } else if ((0x1bU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if ((0x7fU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cpw_p))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_cpw = 0U;
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__cpw_p 
                        = (0x7fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cpw_p)));
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra 
                        = (0x7fU & ((IData)(2U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cpw_p)));
                }
            } else if ((0x12U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (((0x10U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp)) 
                     | vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                     [((0x78U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp) 
                                 << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_col))])) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fo1 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp;
                    if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4))) {
                        if ((7U == (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_col))) {
                            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 1U;
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
                        } else {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x13U;
                        }
                    } else if ((2U <= (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__off_b 
                            = ((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp) 
                                          - (IData)(1U)) 
                                         << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_col));
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__legal = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x14U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__off_a 
                            = ((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp) 
                                          - (IData)(2U)) 
                                         << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_col));
                    } else {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
                    }
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp = 0U;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp)));
                }
            } else if ((0x13U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (((0x10U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp)) 
                     | vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                     [((0x78U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp) 
                                 << 3U)) | (7U & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_col))))])) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fo2b__DOT__fom 
                        = (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fo1) 
                            < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp))
                            ? (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fo1)
                            : (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp));
                    if ((1U <= (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fo2b__DOT__fom))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__off_a 
                            = ((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fo2b__DOT__fom) 
                                          - (IData)(1U)) 
                                         << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_col));
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__legal = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x14U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__off_b 
                            = ((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fo2b__DOT__fom) 
                                          - (IData)(1U)) 
                                         << 3U)) | 
                               (7U & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_col))));
                    } else {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
                    }
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp)));
                }
            } else {
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4))) {
                    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v2 
                        = vlSelfRef.CoproDrMario__DOT__lev_a_cb;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__pca 
                        = vlSelfRef.CoproDrMario__DOT__lev_a_cb;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__pcb 
                        = vlSelfRef.CoproDrMario__DOT__lev_a_ca;
                    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v3 
                        = vlSelfRef.CoproDrMario__DOT__lev_a_ca;
                } else {
                    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v2 
                        = vlSelfRef.CoproDrMario__DOT__lev_a_ca;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__pca 
                        = vlSelfRef.CoproDrMario__DOT__lev_a_ca;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__pcb 
                        = vlSelfRef.CoproDrMario__DOT__lev_a_cb;
                    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v3 
                        = vlSelfRef.CoproDrMario__DOT__lev_a_cb;
                }
                __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v2 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a;
                __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v2 = 1U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x33U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep = 1U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt = 8U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__srun = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__smcol = 0U;
                __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v3 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b;
                __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v3 = 1U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__soff 
                    = (0x78U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a));
            }
        } else if (((((((((0x15U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)) 
                          | (0x16U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                         | (0x17U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                        | (0x2eU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                       | (0x35U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                      | (0x36U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                     | (0x37U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                    | (0x38U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)))) {
            if ((0x15U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scan__DOT__c_ 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                    [(0x7fU & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__soff))];
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scan__DOT__brk 
                    = ((0U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scan__DOT__c_)) 
                       | ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scan__DOT__c_) 
                          != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__smcol)));
                if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scan__DOT__brk) 
                     & (4U <= (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun)))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 1U;
                    if ((0U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 2U;
                    if ((1U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep)) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep)) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep)))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 3U;
                    if ((2U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 1U)) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 1U)) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 1U)))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 4U;
                    if ((3U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(3U) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(3U) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(3U) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 5U;
                    if ((4U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 2U)) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 2U)) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 2U)))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 6U;
                    if ((5U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(5U) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(5U) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(5U) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 7U;
                    if ((6U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(6U) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(6U) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(6U) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 8U;
                    if ((7U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(7U) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(7U) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(7U) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 9U;
                    if ((8U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 3U)) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 3U)) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 3U)))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xaU;
                    if ((9U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(9U) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(9U) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(9U) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xbU;
                    if ((0xaU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xaU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xaU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xaU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xcU;
                    if ((0xbU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xbU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xbU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xbU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xdU;
                    if ((0xcU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xcU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xcU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xcU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xeU;
                    if ((0xdU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xdU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xdU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xdU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xfU;
                    if ((0xeU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xeU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xeU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xeU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0x10U;
                    if ((0xfU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xfU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xfU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xfU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                }
                if ((0U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scan__DOT__c_))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__srun = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__smcol = 0U;
                } else if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scan__DOT__c_) 
                            != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__smcol))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__smcol 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scan__DOT__c_;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__srstart 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__soff;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__srun = 1U;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__srun 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun)));
                }
                if ((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scnt))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x16U;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__soff 
                        = (0xffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__soff) 
                                    + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt 
                        = (0x1fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scnt) 
                                    - (IData)(1U)));
                }
            } else if ((0x16U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if ((4U <= (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 1U;
                    if ((0U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 2U;
                    if ((1U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep)) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep)) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep)))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 3U;
                    if ((2U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 1U)) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 1U)) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 1U)))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 4U;
                    if ((3U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(3U) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(3U) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(3U) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 5U;
                    if ((4U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 2U)) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 2U)) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 2U)))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 6U;
                    if ((5U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(5U) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(5U) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(5U) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 7U;
                    if ((6U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(6U) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(6U) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(6U) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 8U;
                    if ((7U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(7U) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(7U) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(7U) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 9U;
                    if ((8U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 3U)) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 3U)) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      VL_SHIFTL_III(7,32,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep), 3U)))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xaU;
                    if ((9U < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(9U) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(9U) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(9U) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xbU;
                    if ((0xaU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xaU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xaU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xaU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xcU;
                    if ((0xbU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xbU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xbU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xbU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xdU;
                    if ((0xcU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xcU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xcU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xcU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xeU;
                    if ((0xdU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xdU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xdU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xdU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0xfU;
                    if ((0xeU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xeU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xeU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xeU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__i = 0x10U;
                    if ((0xfU < (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[(3U 
                                                                         & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                                             + 
                                                                             ((IData)(0xfU) 
                                                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                                                            >> 5U))] 
                            = (__Vdly__CoproDrMario__DOT__leafeval__DOT__markb[
                               (3U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                       + ((IData)(0xfU) 
                                          * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))) 
                                      >> 5U))] | ((IData)(1U) 
                                                  << 
                                                  (0x1fU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart) 
                                                      + 
                                                      ((IData)(0xfU) 
                                                       * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep))))));
                    }
                }
                __Vdly__CoproDrMario__DOT__leafeval__DOT__smcol = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__srun = 0U;
                if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fullscan) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__feol__DOT__nx 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fli)));
                    if ((0x17U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fli))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp2 = 0U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x35U;
                    } else {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fli 
                            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__feol__DOT__nx;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x15U;
                        if ((0x10U > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__feol__DOT__nx))) {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__soff 
                                = (0x78U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__feol__DOT__nx) 
                                            << 3U));
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep = 1U;
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt = 8U;
                        } else {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__soff 
                                = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__feol__DOT__nx));
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep = 8U;
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt = 0x10U;
                        }
                    }
                } else if ((0U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__soff 
                        = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep = 8U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt = 0x10U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x15U;
                } else if ((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__soff 
                        = (0x78U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt = 8U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 2U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x15U;
                } else if ((2U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__soff 
                        = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep = 8U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt = 0x10U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 3U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x15U;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp2 = 0U;
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x35U;
                }
            } else if ((0x17U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_m 
                    = (1U & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__markb[
                             ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2) 
                              >> 5U)] >> (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2))));
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_rq;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x2eU;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_vir 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                    [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2];
                __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_i 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2;
            } else if ((0x2eU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_pixr 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_pix;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_unl 
                    = ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_phas) 
                       & (~ (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__markb[
                             ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_pix) 
                              >> 5U)] >> (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_pix)))));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x30U;
            } else if ((0x35U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x17U;
            } else if ((0x36U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x18U;
            } else if ((0x37U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x29U;
            } else {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra = 1U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x1bU;
            }
        } else if (((((((((0x33U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)) 
                          | (0x30U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                         | (0x31U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                        | (0x32U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                       | (0x2bU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                      | (0x18U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                     | (0x2fU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                    | (0x2cU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)))) {
            if ((0x33U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x15U;
            } else if ((0x30U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x2bU;
            } else if ((0x31U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x2cU;
            } else if ((0x32U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x2dU;
            } else if ((0x2bU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_m) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_cells 
                        = (0x7fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_cells)));
                    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_vir) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_vir 
                            = (0x3fU & ((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_vir)));
                    }
                    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v4 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i;
                    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v4 = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__anyclear = 1U;
                }
                if ((0x7fU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__gr = 0xeU;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__gc = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__gmoved = 0U;
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra = 0x70U;
                    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__delta_mode) {
                        if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__anyclear) 
                             | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_m))) {
                            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dv_fallback = 1U;
                            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 1U;
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode = 0U;
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
                        } else {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x20U;
                        }
                    } else if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__anyclear) 
                                | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_m))) {
                        if ((0xfU != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain))) {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__chain 
                                = (0xfU & ((IData)(1U) 
                                           + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain)));
                            if ((1U <= (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain))) {
                                __Vdly__CoproDrMario__DOT__leafeval__DOT__chain_bonus 
                                    = (0xffffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain_bonus) 
                                                  + 
                                                  ((IData)(vlSelfRef.CoproDrMario__DOT__lev_a_chw) 
                                                   << 2U)));
                            }
                        }
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x36U;
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x19U;
                    }
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp2 
                        = (0x7fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2)));
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra 
                        = (0x7fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x35U;
                }
            } else if ((0x18U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0 
                    = (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr) 
                        << 3U) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc));
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__lk 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_rq;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__haspt = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x2fU;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k1 = 0U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__isrep = 1U;
                if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__lk))) {
                    if ((1U & (~ ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__lk) 
                                  >> 1U)))) {
                        if ((1U & (~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__lk)))) {
                            if (((7U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc)) 
                                 & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                                 [(0x7fU & ((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0)))])) {
                                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__haspt = 1U;
                                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k1 
                                    = (0x7fU & ((IData)(1U) 
                                                + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0)));
                            }
                        }
                    }
                } else if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__lk))) {
                    if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__lk))) {
                        if (((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc)) 
                             & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                             [(0x7fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0) 
                                        - (IData)(1U)))])) {
                            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__isrep = 0U;
                        }
                    } else if (((0xfU != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr)) 
                                & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                                [(0x7fU & ((IData)(8U) 
                                           + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0)))])) {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__isrep = 0U;
                    }
                } else if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__lk))) {
                    if (((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr)) 
                         & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                         [(0x7fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0) 
                                    - (IData)(8U)))])) {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__haspt = 1U;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k1 
                            = (0x7fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0) 
                                        - (IData)(8U)));
                    }
                }
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__blk 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                    [(0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0)))];
                if ((((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__haspt) 
                      & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                      [(0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k1)))]) 
                     & ((0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k1))) 
                        != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0)))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__blk = 1U;
                }
                __Vdly__CoproDrMario__DOT__leafeval__DOT__g_has 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__haspt;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__g_k0 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__g_k1 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k1;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__g_cell 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                    [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0];
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_lnk 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__lk;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_isrep 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__isrep;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_occ 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                    [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0];
                __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_vir 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                    [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0];
                __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_blk0 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                    [(0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0)))];
            } else if ((0x2fU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grvd__DOT__blk 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_blk0;
                if ((((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_has) 
                      & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                      [(0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k1)))]) 
                     & ((0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k1))) 
                        != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k0)))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grvd__DOT__blk = 1U;
                }
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x31U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__g_do 
                    = ((((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_occ) 
                         & (~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_vir))) 
                        & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_isrep)) 
                       & (~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__grvd__DOT__blk)));
            } else {
                if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_do) {
                    __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v5 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_cell;
                    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v5 
                        = (0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k0)));
                    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v5 = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__gmoved = 1U;
                    __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v6 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k0;
                    __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v6 = 1U;
                }
                if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_do) 
                     & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_has))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__gk1 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k1;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x37U;
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k1;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x36U;
                    if ((7U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__gc = 0U;
                        if ((0U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr))) {
                            if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gmoved) 
                                 | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_do))) {
                                __Vdly__CoproDrMario__DOT__leafeval__DOT__gr = 0xeU;
                                __Vdly__CoproDrMario__DOT__leafeval__DOT__gmoved = 0U;
                                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra = 0x70U;
                            } else {
                                __Vdly__CoproDrMario__DOT__leafeval__DOT__st 
                                    = ((IData)(vlSelfRef.CoproDrMario__DOT__lev_a_fix)
                                        ? 0x2aU : 0x19U);
                            }
                        } else {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__gr 
                                = (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr) 
                                           - (IData)(1U)));
                            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra 
                                = (0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr) 
                                             - (IData)(1U)) 
                                            << 3U));
                        }
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__gc 
                            = (7U & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc)));
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra 
                            = (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr) 
                                << 3U) | (7U & ((IData)(1U) 
                                                + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc))));
                    }
                }
            }
        } else if (((((((((0x29U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)) 
                          | (0x2dU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                         | (0x2aU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                        | (0x19U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                       | (1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                      | (2U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                     | (3U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                    | (4U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)))) {
            if ((0x29U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__g_cell 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                    [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gk1];
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_lnk 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_rq;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x32U;
            } else if ((0x2dU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v7 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_cell;
                __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v7 
                    = (0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gk1)));
                __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v7 = 1U;
                if ((7U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__gc = 0U;
                    if ((0U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__gmoved = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__gr = 0xeU;
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra = 0x70U;
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__gr 
                            = (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr) 
                                       - (IData)(1U)));
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra 
                            = (0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr) 
                                         - (IData)(1U)) 
                                        << 3U));
                    }
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__gc 
                        = (7U & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc)));
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_ra 
                        = (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr) 
                            << 3U) | (7U & ((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc))));
                }
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x36U;
                __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v8 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gk1;
                __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v8 = 1U;
            } else if ((0x2aU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[0U] = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[1U] = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[2U] = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[3U] = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__anyclear = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__fullscan = 1U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fli = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__soff = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep = 1U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt = 8U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__srun = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__smcol = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x15U;
            } else if ((0x19U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__imm 
                    = (0xffffU & ((((IData)(0xb4U) 
                                    * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_vir)) 
                                   + ((IData)(0xaU) 
                                      * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_cells))) 
                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain_bonus)));
                if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__node_leaf) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__holes = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__setup = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__buried = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__anyvir = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60 = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wc = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__seen = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 1U;
                } else {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
                }
            } else if ((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                    [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                       << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))]) {
                    if ((1U & (~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__seen)))) {
                        if (((0x1fU & ((IData)(0x10U) 
                                       - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_))) 
                             > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__maxh))) {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh 
                                = (0x1fU & ((IData)(0x10U) 
                                            - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)));
                        }
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__seen = 1U;
                        if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_mode) {
                            __VdlyVal__CoproDrMario__DOT__leafeval__DOT__colh__v8 
                                = (0x1fU & ((IData)(0x10U) 
                                            - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)));
                            __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__colh__v8 
                                = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc));
                            __VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v8 = 1U;
                        }
                    }
                    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                        [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                           << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))]) {
                        if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curcol) 
                             == vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                             [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))])) {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60 
                                = (0x1fffU & ((IData)(0x30U) 
                                              + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__matched60)));
                        }
                        if ((2U > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vseen))) {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__buried 
                                = (0x3ffU & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__buried) 
                                              + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fillcnt)) 
                                             - (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curcol) 
                                                 == 
                                                 vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                                 [(
                                                   ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                                    << 3U) 
                                                   | (7U 
                                                      & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))])
                                                 ? (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curlen)
                                                 : 0U)));
                        }
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__anyvir = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen 
                            = (0x1fU & ((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vseen)));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                    } else if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curcol) 
                                == vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                   << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))])) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen 
                            = (0x1fU & ((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curlen)));
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol 
                            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                            [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                               << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))];
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 1U;
                    }
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fillcnt)));
                    if ((3U > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk 
                            = (0xffU & ((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__toprisk)));
                    }
                    if (((4U > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)) 
                         & ((3U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)) 
                            | (4U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn 
                            = (0xffU & ((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__spawn)));
                    }
                } else {
                    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__seen) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__holes 
                            = (0xffU & ((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__holes)));
                    }
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                }
                if ((0xfU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__seen = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen = 0U;
                    if ((7U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__vo = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 2U;
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__wc 
                            = (0xfU & ((IData)(1U) 
                                       + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)));
                    }
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ 
                        = (0xfU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)));
                }
            } else if ((2U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                    [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo]) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_h = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_v = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 3U;
                } else if ((0x7fU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wc = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0xeU;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vo 
                        = (0x7fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo)));
                }
            } else if ((3U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if ((((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)) 
                      & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                         [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                            << 3U) | (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p) 
                                            - (IData)(1U))))] 
                         == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col))) 
                     & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                     [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                        << 3U) | (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p) 
                                        - (IData)(1U))))])) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_h 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_h)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                        = (0x1fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p) 
                                    - (IData)(1U)));
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__span_lo 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 4U;
                }
            } else if (((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_lo)) 
                        & ((~ vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                            [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                               << 3U) | (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_lo) 
                                               - (IData)(1U))))]) 
                           | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                              [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                                 << 3U) | (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_lo) 
                                                 - (IData)(1U))))] 
                              == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col))))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__span_lo 
                    = (0x1fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_lo) 
                                - (IData)(1U)));
            } else {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 5U;
            }
        } else if (((((((((5U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)) 
                          | (6U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                         | (7U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                        | (8U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                       | (9U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                      | (0xaU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                     | (0xbU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                    | (0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)))) {
            if ((5U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if ((((7U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)) 
                      & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                      [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                         << 3U) | (7U & ((IData)(1U) 
                                         + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p))))]) 
                     & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                        [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                           << 3U) | (7U & ((IData)(1U) 
                                           + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p))))] 
                        == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col)))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_h 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_h)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)));
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__span_hi 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 6U;
                }
            } else if ((6U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (((7U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_hi)) 
                     & ((~ vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                         [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                            << 3U) | (7U & ((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_hi))))]) 
                        | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                           [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                              << 3U) | (7U & ((IData)(1U) 
                                              + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_hi))))] 
                           == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col))))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__span_hi 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_hi)));
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 7U;
                }
            } else if ((7U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if ((((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)) 
                      & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                      [((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p) 
                                   - (IData)(1U)) << 3U)) 
                        | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))]) 
                     & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                        [((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p) 
                                     - (IData)(1U)) 
                                    << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))] 
                        == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col)))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_v 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_v)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                        = (0x1fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p) 
                                    - (IData)(1U)));
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_lo 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 8U;
                }
            } else if ((8U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_lo)) 
                     & ((~ vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                         [((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_lo) 
                                      - (IData)(1U)) 
                                     << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))]) 
                        | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                           [((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_lo) 
                                        - (IData)(1U)) 
                                       << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))] 
                           == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col))))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_lo 
                        = (0x1fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_lo) 
                                    - (IData)(1U)));
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 9U;
                }
            } else if ((9U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if ((((0xfU != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)) 
                      & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                      [((0x78U & (((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)) 
                                  << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))]) 
                     & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                        [((0x78U & (((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)) 
                                    << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))] 
                        == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col)))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_v 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_v)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)));
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_hi 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0xaU;
                }
            } else if ((0xaU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (((0xfU != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_hi)) 
                     & ((~ vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                         [((0x78U & (((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_hi)) 
                                     << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))]) 
                        | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                           [((0x78U & (((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_hi)) 
                                       << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))] 
                           == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col))))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_hi 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_hi)));
                } else if ((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dphase))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x24U;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0xbU;
                }
            } else if ((0xbU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if ((((((7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)) 
                        != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c)) 
                       & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                       [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                          << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)))]) 
                      & (~ vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                         [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                            << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)))])) 
                     & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                        [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r) 
                           << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)))] 
                        != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col)))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution 
                        = (0x7ffU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pollution)));
                }
                if ((7U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0xcU;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)));
                }
            } else {
                if ((((((0xfU & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)) 
                        != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r)) 
                       & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                       [((0x78U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p) 
                                   << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))]) 
                      & (~ vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                         [((0x78U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p) 
                                     << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))])) 
                     & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                        [((0x78U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p) 
                                    << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c))] 
                        != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col)))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution 
                        = (0x7ffU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pollution)));
                }
                if ((0xfU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0xdU;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p)));
                }
            }
        } else if (((((((((0xdU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)) 
                          | (0xeU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                         | (0xfU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                        | (0x10U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                       | (0x1dU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                      | (0x20U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                     | (0x1fU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                    | (0x28U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)))) {
            if ((0xdU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fin__DOT__hq 
                    = ((4U <= (0x1fU & ((IData)(1U) 
                                        + ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_hi) 
                                           - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_lo)))))
                        ? ([&]() {
                            __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__3__n 
                                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_h;
                            __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__3__Vfuncout 
                                = (0x1ffU & ((IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__3__n) 
                                             * (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__3__n)));
                        }(), (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__3__Vfuncout))
                        : 0U);
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fin__DOT__vq 
                    = ((4U <= (0x1fU & ((IData)(1U) 
                                        + ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_hi) 
                                           - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_lo)))))
                        ? ([&]() {
                            __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__4__n 
                                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_v;
                            __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__4__Vfuncout 
                                = (0x1ffU & ((IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__4__n) 
                                             * (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__4__n)));
                        }(), (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__4__Vfuncout))
                        : 0U);
                if ((0x7fU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wc = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0xeU;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vo 
                        = (0x7fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 2U;
                }
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fin__DOT__mx 
                    = (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fin__DOT__hq) 
                        > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fin__DOT__vq))
                        ? (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fin__DOT__hq)
                        : (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fin__DOT__vq));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext 
                    = (0xffffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rdy_ext) 
                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fin__DOT__mx)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy 
                    = (0xffffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vrdy) 
                                  + VL_EXTEND_II(16,9, 
                                                 ([&]() {
                                    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__5__n 
                                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_v;
                                    __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__5__Vfuncout 
                                        = (0x1ffU & 
                                           ((IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__5__n) 
                                            * (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__5__n)));
                                }(), (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__5__Vfuncout)))));
            } else if ((0xeU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__c0 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                    [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                       << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))];
                if ((((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__c0)) 
                      & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                         [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                            << 3U) | (7U & ((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))))] 
                         == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__c0))) 
                     & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                        [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                           << 3U) | (7U & ((IData)(2U) 
                                           + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))))] 
                        == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__c0)))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__t 
                        = (((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                             [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                             & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                   << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                                == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__c0))) 
                            | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                  << 3U) | (7U & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                     << 3U) | (7U & 
                                               ((IData)(1U) 
                                                + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__c0)))) 
                           | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                              [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                 << 3U) | (7U & ((IData)(2U) 
                                                 + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))))] 
                              & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                 [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                    << 3U) | (7U & 
                                              ((IData)(2U) 
                                               + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))))] 
                                 == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__c0))));
                    if (((~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__t)) 
                         & (0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))) {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__t 
                            = (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                  << 3U) | (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc) 
                                                  - (IData)(1U))))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                     << 3U) | (7U & 
                                               ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc) 
                                                - (IData)(1U))))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__c0)));
                    }
                    if (((~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__t)) 
                         & (5U > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))) {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__t 
                            = (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                  << 3U) | (7U & ((IData)(3U) 
                                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                     << 3U) | (7U & 
                                               ((IData)(3U) 
                                                + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__c0)));
                    }
                    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suh__DOT__t) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__setup 
                            = (0xffU & ((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__setup)));
                    }
                }
                if ((5U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wc = 0U;
                    if ((0xfU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0xfU;
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ 
                            = (0xfU & ((IData)(1U) 
                                       + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)));
                    }
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wc 
                        = (0xfU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)));
                }
            } else if ((0xfU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__c0 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                    [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                       << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))];
                if ((((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__c0)) 
                      & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                         [((0x78U & (((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)) 
                                     << 3U)) | (7U 
                                                & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                         == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__c0))) 
                     & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                        [((0x78U & (((IData)(2U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)) 
                                    << 3U)) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                        == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__c0)))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__t 
                        = (((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                             [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                             & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                   << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                                == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__c0))) 
                            | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [((0x78U & (((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)) 
                                           << 3U)) 
                                 | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [((0x78U & (((IData)(1U) 
                                               + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)) 
                                              << 3U)) 
                                    | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__c0)))) 
                           | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                              [((0x78U & (((IData)(2U) 
                                           + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)) 
                                          << 3U)) | 
                                (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                              & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                 [((0x78U & (((IData)(2U) 
                                              + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)) 
                                             << 3U)) 
                                   | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                                 == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__c0))));
                    if (((~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__t)) 
                         & (0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)))) {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__t 
                            = (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                            - (IData)(1U)) 
                                           << 3U)) 
                                 | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_) 
                                               - (IData)(1U)) 
                                              << 3U)) 
                                    | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__c0)));
                    }
                    if (((~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__t)) 
                         & (0xdU > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)))) {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__t 
                            = (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [((0x78U & (((IData)(3U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)) 
                                           << 3U)) 
                                 | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [((0x78U & (((IData)(3U) 
                                               + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)) 
                                              << 3U)) 
                                    | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__c0)));
                    }
                    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__suv__DOT__t) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__setup 
                            = (0xffU & ((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__setup)));
                    }
                }
                if ((0xdU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ = 0U;
                    if ((7U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x10U;
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__wc 
                            = (0xfU & ((IData)(1U) 
                                       + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc)));
                    }
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_ 
                        = (0xfU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_)));
                }
            } else if ((0x10U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_mode) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_maxh 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__maxh;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_holes 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__holes;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_toprisk 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__toprisk;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_spawn 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__spawn;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_setup 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__setup;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_pol 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pollution;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_buried 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__buried;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_matched 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__matched60;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_rdy 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rdy_ext;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_vrdy 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vrdy;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_anyvir 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__anyvir;
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__base_mode = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__win 
                        = (1U & (~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__anyvir)));
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh_p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__maxh;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__holes_p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__holes;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk_p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__toprisk;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn_p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__spawn;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__setup_p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__setup;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution_p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pollution;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__buried_p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__buried;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext_p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rdy_ext;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy_p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vrdy;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60_p 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__matched60;
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__win 
                        = (1U & (~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__anyvir)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x1dU;
                }
            } else if ((0x1dU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sco 
                    = (0xffffU & (((((((((((IData)(0x1388U) 
                                           - ((IData)(0xcU) 
                                              * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__maxh_p))) 
                                          - ((IData)(0x14U) 
                                             * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__holes_p))) 
                                         - ((IData)(0x5aU) 
                                            * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__toprisk_p))) 
                                        - ((IData)(0x96U) 
                                           * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__spawn_p))) 
                                       + VL_SHIFTL_III(16,16,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__setup_p), 5U)) 
                                      + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__matched60_p)) 
                                     - ((IData)(0x30U) 
                                        * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__buried_p))) 
                                    + VL_SHIFTL_III(16,16,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rdy_ext_p), 3U)) 
                                   + VL_SHIFTL_III(16,16,32, (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vrdy_p), 3U)) 
                                  - ((IData)(6U) * (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pollution_p))));
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 1U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
            } else if ((0x20U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dnew__DOT__ga 
                    = (0xffU & (((IData)(0xfU) - vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh
                                 [(7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a))]) 
                                - (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                           >> 3U))));
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dnew__DOT__gb 
                    = (0xffU & (((IData)(0xfU) - vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh
                                 [(7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b))]) 
                                - (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b) 
                                           >> 3U))));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_holes 
                    = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4))
                        ? (0xffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dnew__DOT__ga) 
                                    + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dnew__DOT__gb)))
                        : 0U);
                __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep = 1U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt = 8U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x1fU;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_matched 
                    = (0x1fffU & (((((0xfU != (0xfU 
                                               & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                                  >> 3U))) 
                                     & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                                     [(0x7fU & ((IData)(8U) 
                                                + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a)))]) 
                                    & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                       [(0x7fU & ((IData)(8U) 
                                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a)))] 
                                       == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pca)))
                                    ? 0x30U : 0U) + 
                                  ((((0xfU != (0xfU 
                                               & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b) 
                                                  >> 3U))) 
                                     & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                                     [(0x7fU & ((IData)(8U) 
                                                + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b)))]) 
                                    & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                       [(0x7fU & ((IData)(8U) 
                                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b)))] 
                                       == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pcb)))
                                    ? 0x30U : 0U)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
                    = (0x78U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a));
            } else if ((0x1fU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                     [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsoff] 
                     & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                        [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsoff] 
                        != ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li))
                             ? (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pcb)
                             : (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pca))))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_pol 
                        = (0x7ffU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dd_pol)));
                }
                if ((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dscnt))) {
                    if ((0U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
                            = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep = 8U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt = 0x10U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 1U;
                    } else if ((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
                            = (0x78U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt = 8U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 2U;
                    } else if ((2U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
                            = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep = 8U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt = 0x10U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 3U;
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dbur_new = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dcolstep = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dcol 
                            = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__drow = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x21U;
                    }
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
                        = (0x7fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsoff) 
                                    + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dstep)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt 
                        = (0x1fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dscnt) 
                                    - (IData)(1U)));
                }
            } else {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hha 
                    = (0x1fU & ((IData)(0x10U) - (0xfU 
                                                  & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                                     >> 3U))));
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hhb 
                    = (0x1fU & ((IData)(0x10U) - (0xfU 
                                                  & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b) 
                                                     >> 3U))));
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hmax 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_maxh;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__holes 
                    = (0xffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_holes) 
                                + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dd_holes)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__setup 
                    = (0xffU & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_setup) 
                                 - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_set)) 
                                + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_set)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution 
                    = (0x7ffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_pol) 
                                 + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dd_pol)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__buried 
                    = (0x3ffU & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_buried) 
                                  - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_bur)) 
                                 + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_bur)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext 
                    = (0xffffU & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_rdy) 
                                   - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_rdy)) 
                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_rdy)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy 
                    = (0xffffU & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_vrdy) 
                                   - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_vrdy)) 
                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_vrdy)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60 
                    = (0x1fffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_matched) 
                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dd_matched)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__anyvir 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_anyvir;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x10U;
                if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hha) 
                     > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hmax))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hmax 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hha;
                }
                if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hhb) 
                     > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hmax))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hmax 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hhb;
                }
                __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hmax;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk 
                    = (0xffU & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_toprisk) 
                                 + (3U > (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                                  >> 3U)))) 
                                + (3U > (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b) 
                                                 >> 3U)))));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn 
                    = (0xffU & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_spawn) 
                                 + ((4U > (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                                   >> 3U))) 
                                    & ((3U == (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a))) 
                                       | (4U == (7U 
                                                 & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a)))))) 
                                + ((4U > (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b) 
                                                  >> 3U))) 
                                   & ((3U == (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b))) 
                                      | (4U == (7U 
                                                & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b)))))));
            }
        } else if (((((((((0x21U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)) 
                          | (0x26U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                         | (0x34U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                        | (0x23U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                       | (0x22U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                      | (0x24U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                     | (0x25U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) 
                    | (0x27U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st)))) {
            if ((0x21U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                    [((0x78U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drow) 
                                << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcol))]) {
                    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                        [((0x78U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drow) 
                                    << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcol))]) {
                        if ((2U > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vseen))) {
                            vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dbur__DOT__excess 
                                = (0x1fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fillcnt) 
                                            - (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curcol) 
                                                == 
                                                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                                [((0x78U 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drow) 
                                                      << 3U)) 
                                                  | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcol))])
                                                ? (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curlen)
                                                : 0U)));
                            if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dbur_new) {
                                __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_bur 
                                    = (0x3ffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_bur) 
                                                 + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dbur__DOT__excess)));
                            } else {
                                __Vdly__CoproDrMario__DOT__leafeval__DOT__od_bur 
                                    = (0x3ffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_bur) 
                                                 + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dbur__DOT__excess)));
                            }
                        }
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen 
                            = (0x1fU & ((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vseen)));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                    } else if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curcol) 
                                == vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                [((0x78U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drow) 
                                            << 3U)) 
                                  | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcol))])) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen 
                            = (0x1fU & ((IData)(1U) 
                                        + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curlen)));
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol 
                            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                            [((0x78U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drow) 
                                        << 3U)) | (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcol))];
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 1U;
                    }
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fillcnt)));
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                }
                if ((0xfU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drow))) {
                    if ((((0U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcolstep)) 
                          & ((IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4) 
                             >> 1U)) & ((7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b)) 
                                        != (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a))))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dcolstep = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dcol 
                            = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__drow = 0U;
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dphase 
                            = ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dbur_new)
                                ? 1U : 2U);
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dlmask 
                            = (3U | ((8U & ((IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4) 
                                            << 2U)) 
                                     | (4U & ((~ ((IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4) 
                                                  >> 1U)) 
                                              << 2U))));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
                            = (0x78U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt = 8U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x23U;
                    }
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__drow 
                        = (0x1fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drow)));
                }
            } else if ((0x26U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen = 0U;
                __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v9 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a;
                __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v9 = 1U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__dbur_new = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__dcolstep = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__drow = 0U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x34U;
                __VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v10 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b;
                __VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v10 = 1U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__dcol 
                    = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a));
            } else if ((0x34U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x21U;
            } else if ((0x23U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                    [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsoff]) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__vo 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsoff;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_h = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__run_v = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 3U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__p 
                        = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsoff));
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x22U;
                }
            } else if ((0x22U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                if ((1U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dscnt))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
                        = (0x7fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsoff) 
                                    + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dstep)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt 
                        = (0x1fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dscnt) 
                                    - (IData)(1U)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x23U;
                } else if ((0U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
                        = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep = 8U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt = 0x10U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x23U;
                } else if (((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li)) 
                            & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dlmask) 
                               >> 2U))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
                        = (0x78U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep = 1U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt = 8U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 2U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x23U;
                } else if (((3U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li)) 
                            & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dlmask) 
                               >> 3U))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff 
                        = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep = 8U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt = 0x10U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__li = 3U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x23U;
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dphase = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dwrow 
                        = (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                   >> 3U));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dwsecond = 0U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x25U;
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dws 
                        = ((2U <= (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a)))
                            ? (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                     - (IData)(2U)))
                            : 0U);
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dwhi 
                        = ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4))
                            ? ((5U >= (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b)))
                                ? (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b))
                                : 5U) : ((5U >= (7U 
                                                 & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a)))
                                          ? (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a))
                                          : 5U));
                }
            } else if ((0x24U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__hq 
                    = ((4U <= (0x1fU & ((IData)(1U) 
                                        + ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_hi) 
                                           - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_lo)))))
                        ? ([&]() {
                            __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__6__n 
                                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_h;
                            __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__6__Vfuncout 
                                = (0x1ffU & ((IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__6__n) 
                                             * (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__6__n)));
                        }(), (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__6__Vfuncout))
                        : 0U);
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__vq 
                    = ((4U <= (0x1fU & ((IData)(1U) 
                                        + ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_hi) 
                                           - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_lo)))))
                        ? ([&]() {
                            __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__7__n 
                                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_v;
                            __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__7__Vfuncout 
                                = (0x1ffU & ((IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__7__n) 
                                             * (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__7__n)));
                        }(), (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__7__Vfuncout))
                        : 0U);
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x22U;
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__mx 
                    = (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__hq) 
                        > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__vq))
                        ? (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__hq)
                        : (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__vq));
                if ((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dphase))) {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_rdy 
                        = (0xffffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_rdy) 
                                      + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__mx)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_vrdy 
                        = (0xffffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_vrdy) 
                                      + VL_EXTEND_II(16,9, 
                                                     ([&]() {
                                        __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__8__n 
                                            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_v;
                                        __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__8__Vfuncout 
                                            = (0x1ffU 
                                               & ((IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__8__n) 
                                                  * (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__8__n)));
                                    }(), (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__8__Vfuncout)))));
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__od_rdy 
                        = (0xffffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_rdy) 
                                      + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__mx)));
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__od_vrdy 
                        = (0xffffU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_vrdy) 
                                      + VL_EXTEND_II(16,9, 
                                                     ([&]() {
                                        __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__9__n 
                                            = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_v;
                                        __Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__9__Vfuncout 
                                            = (0x1ffU 
                                               & ((IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__9__n) 
                                                  * (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__9__n)));
                                    }(), (IData)(__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__9__Vfuncout)))));
                }
            } else if ((0x25U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__c0 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                    [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                       << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)))];
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__tt = 0U;
                if ((((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__c0)) 
                      & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                         [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                            << 3U) | (7U & ((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws))))] 
                         == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__c0))) 
                     & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                        [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                           << 3U) | (7U & ((IData)(2U) 
                                           + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws))))] 
                        == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__c0)))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__tt 
                        = (((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                             [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                                << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)))] 
                             & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                                   << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)))] 
                                == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__c0))) 
                            | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                                  << 3U) | (7U & ((IData)(1U) 
                                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws))))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                                     << 3U) | (7U & 
                                               ((IData)(1U) 
                                                + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws))))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__c0)))) 
                           | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                              [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                                 << 3U) | (7U & ((IData)(2U) 
                                                 + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws))))] 
                              & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                 [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                                    << 3U) | (7U & 
                                              ((IData)(2U) 
                                               + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws))))] 
                                 == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__c0))));
                    if (((~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__tt)) 
                         & (0U != (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws))))) {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__tt 
                            = (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                                  << 3U) | (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws) 
                                                  - (IData)(1U))))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                                     << 3U) | (7U & 
                                               ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws) 
                                                - (IData)(1U))))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__c0)));
                    }
                    if (((~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__tt)) 
                         & (5U > (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws))))) {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__tt 
                            = (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                                  << 3U) | (7U & ((IData)(3U) 
                                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws))))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow) 
                                     << 3U) | (7U & 
                                               ((IData)(3U) 
                                                + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws))))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__c0)));
                    }
                    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dseth__DOT__tt) {
                        if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dbur_new) {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_set 
                                = (0xffU & ((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_set)));
                        } else {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__od_set 
                                = (0xffU & ((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_set)));
                        }
                    }
                }
                if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws) 
                     >= (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwhi))) {
                    if ((1U & ((~ ((IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4) 
                                   >> 1U)) & (~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwsecond))))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dwrow 
                            = (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b) 
                                       >> 3U));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dwsecond = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dws 
                            = ((2U <= (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a)))
                                ? (7U & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                         - (IData)(2U)))
                                : 0U);
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dwrow 
                            = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dwsecond = 0U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x27U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dws 
                            = ((2U <= (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                               >> 3U)))
                                ? (0xfU & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                            >> 3U) 
                                           - (IData)(2U)))
                                : 0U);
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dwhi 
                            = (0xfU & ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4))
                                        ? ((0xdU >= 
                                            (0xfU & 
                                             ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                              >> 3U)))
                                            ? ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                               >> 3U)
                                            : 0xdU)
                                        : ((0xdU >= 
                                            (0xfU & 
                                             ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b) 
                                              >> 3U)))
                                            ? ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b) 
                                               >> 3U)
                                            : 0xdU)));
                    }
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dws 
                        = (0xfU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)));
                }
            } else {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__c0 
                    = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                    [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws) 
                       << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))];
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__tt = 0U;
                if ((((0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__c0)) 
                      & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                         [((0x78U & (((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)) 
                                     << 3U)) | (7U 
                                                & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                         == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__c0))) 
                     & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                        [((0x78U & (((IData)(2U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)) 
                                    << 3U)) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                        == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__c0)))) {
                    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__tt 
                        = (((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                             [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws) 
                                << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                             & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                [(((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws) 
                                   << 3U) | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                                == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__c0))) 
                            | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [((0x78U & (((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)) 
                                           << 3U)) 
                                 | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [((0x78U & (((IData)(1U) 
                                               + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)) 
                                              << 3U)) 
                                    | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__c0)))) 
                           | (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                              [((0x78U & (((IData)(2U) 
                                           + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)) 
                                          << 3U)) | 
                                (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                              & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                 [((0x78U & (((IData)(2U) 
                                              + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)) 
                                             << 3U)) 
                                   | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                                 == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__c0))));
                    if (((~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__tt)) 
                         & (0U != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)))) {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__tt 
                            = (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws) 
                                            - (IData)(1U)) 
                                           << 3U)) 
                                 | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [((0x78U & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws) 
                                               - (IData)(1U)) 
                                              << 3U)) 
                                    | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__c0)));
                    }
                    if (((~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__tt)) 
                         & (0xdU > (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)))) {
                        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__tt 
                            = (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                               [((0x78U & (((IData)(3U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)) 
                                           << 3U)) 
                                 | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                               & (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                                  [((0x78U & (((IData)(3U) 
                                               + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)) 
                                              << 3U)) 
                                    | (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow)))] 
                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__c0)));
                    }
                    if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__tt) {
                        if (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dbur_new) {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_set 
                                = (0xffU & ((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_set)));
                        } else {
                            __Vdly__CoproDrMario__DOT__leafeval__DOT__od_set 
                                = (0xffU & ((IData)(1U) 
                                            + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_set)));
                        }
                    }
                }
                if (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws) 
                     >= (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwhi))) {
                    if ((IData)((((IData)(vlSelfRef.CoproDrMario__DOT__lev_a_o4) 
                                  >> 1U) & (~ (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwsecond))))) {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dwrow 
                            = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b));
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dwsecond = 1U;
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__dws 
                            = ((2U <= (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                               >> 3U)))
                                ? (0xfU & (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a) 
                                            >> 3U) 
                                           - (IData)(2U)))
                                : 0U);
                    } else {
                        __Vdly__CoproDrMario__DOT__leafeval__DOT__st 
                            = ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dbur_new)
                                ? 0x26U : 0x28U);
                    }
                } else {
                    __Vdly__CoproDrMario__DOT__leafeval__DOT__dws 
                        = (0xfU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws)));
                }
            }
        } else if ((0x39U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
            __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_c 
                = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i];
            __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x3aU;
            __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_p 
                = (vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of
                   [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i] 
                   & (~ vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of
                      [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i]));
            __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_u 
                = ((8U <= (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i))
                    ? vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                   [(0x7fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i) 
                              - (IData)(8U)))] : 0U);
            __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_d 
                = ((0x77U >= (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i))
                    ? vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                   [(0x7fU & ((IData)(8U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i)))]
                    : 0U);
            __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_l 
                = ((0U != (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i)))
                    ? vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                   [(0x7fU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i) 
                              - (IData)(1U)))] : 0U);
            __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_r 
                = ((7U != (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i)))
                    ? vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
                   [(0x7fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i)))]
                    : 0U);
        } else if ((0x3aU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st))) {
            if ((((((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_p) 
                    & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_c) 
                       != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_u))) 
                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_c) 
                      != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_d))) 
                  & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_c) 
                     != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_l))) 
                 & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_c) 
                    != (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_r)))) {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__strand 
                    = (0x7fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__strand)));
            }
            if ((0x7fU == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i))) {
                vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done = 1U;
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
            } else {
                __Vdly__CoproDrMario__DOT__leafeval__DOT__str_i 
                    = (0x7fU & ((IData)(1U) + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i)));
                __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0x39U;
            }
        } else {
            __Vdly__CoproDrMario__DOT__leafeval__DOT__st = 0U;
        }
    }
    if (((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)) 
         | (8U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state)))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adc_sbc 
            = (0x61U == (0x63U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)));
    }
    if ((0x27U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__D 
            = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DIMUX) 
                     >> 3U));
    } else if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__sed) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__D = 1U;
        }
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__cld) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__D = 0U;
        }
        if (vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__plp) {
            vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__D 
                = (1U & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD) 
                         >> 3U));
        }
    }
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AN = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__N;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__HC = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__HC;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sl_qb 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__q_b;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AV = 
        ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__AI7) 
         ^ ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__BI7) 
            ^ ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CO) 
               ^ (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__N))));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AZ = 
        (1U & (~ (IData)((0U != (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__OUT)))));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCH 
        = (0xffU & ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC) 
                    >> 8U));
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PCL 
        = (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__PC));
    vlSelfRef.CoproDrMario__DOT__ram_a_q = vlSelfRef.CoproDrMario__DOT__wram__DOT__q_a;
    vlSelfRef.CoproDrMario__DOT__DI = ((IData)(vlSelfRef.CoproDrMario__DOT__sel_vec_d)
                                        ? ((IData)(vlSelfRef.CoproDrMario__DOT__ab0_d)
                                            ? 0xbfU
                                            : 0x80U)
                                        : ((IData)(vlSelfRef.CoproDrMario__DOT__sel_rom_d)
                                            ? (IData)(vlSelfRef.CoproDrMario__DOT__rom_q)
                                            : ((IData)(vlSelfRef.CoproDrMario__DOT__sel_lev_d)
                                                ? (IData)(vlSelfRef.CoproDrMario__DOT__lev_q)
                                                : ((IData)(vlSelfRef.CoproDrMario__DOT__sel_ram_d)
                                                    ? (IData)(vlSelfRef.CoproDrMario__DOT__wram__DOT__q_a)
                                                    : 0xffU))));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotq 
        = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__q_b));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_mode 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_mode;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__delta_mode 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__delta_mode;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__maxh 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__holes 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__holes;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__toprisk 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__spawn 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__setup 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__setup;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pollution 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__buried 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__buried;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rdy_ext 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vrdy 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__anyvir 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__anyvir;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__matched60 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wc 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__wc;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wr_ 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__wr_;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__seen 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__seen;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fillcnt 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__fillcnt;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curcol 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__curcol;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__curlen 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__curlen;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vseen 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__vseen;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cmd_l 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__cmd_l;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__node_leaf 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__node_leaf;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__markb[0U] 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[0U];
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__markb[1U] 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[1U];
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__markb[2U] 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[2U];
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__markb[3U] 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__markb[3U];
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__anyclear 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__anyclear;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain_bonus 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__chain_bonus;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fullscan 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__fullscan;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_bur 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__od_bur;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_bur 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_bur;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_rdy 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__od_rdy;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_rdy 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_rdy;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_vrdy 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__od_vrdy;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_vrdy 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_vrdy;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__od_set 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__od_set;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__nd_set 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__nd_set;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dd_matched 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_matched;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dd_pol 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_pol;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dd_holes 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dd_holes;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dphase 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dphase;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__str_i 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__str_i;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fo1 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__fo1;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pca 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__pca;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pcb 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__pcb;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__li 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__li;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sstep 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__sstep;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__scnt 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__scnt;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srun 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__srun;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__smcol 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__smcol;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__soff 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__soff;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__srstart 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__srstart;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_vir 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_vir;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gr 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__gr;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gc 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__gc;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gmoved 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__gmoved;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_has 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__g_has;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k1 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__g_k1;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_cell 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__g_cell;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_isrep 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_isrep;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_occ 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_occ;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_vir 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_vir;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ga_blk0 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__ga_blk0;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_v 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__run_v;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__p = __Vdly__CoproDrMario__DOT__leafeval__DOT__p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_lo 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_lo;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vspan_hi 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__vspan_hi;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_maxh 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_maxh;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_holes 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_holes;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_toprisk 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_toprisk;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_spawn 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_spawn;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_setup 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_setup;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_pol 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_pol;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_buried 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_buried;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_matched 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_matched;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_rdy 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_rdy;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_vrdy 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_vrdy;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__base_anyvir 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__base_anyvir;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__maxh_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__maxh_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__holes_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__holes_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__toprisk_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__toprisk_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__spawn_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__spawn_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__setup_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__setup_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__pollution_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__pollution_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__buried_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__buried_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rdy_ext_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__rdy_ext_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vrdy_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__vrdy_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__matched60_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__matched60_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dstep 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dstep;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dscnt 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dscnt;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dsoff 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dsoff;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dbur_new 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dbur_new;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcolstep 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dcolstep;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dcol 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dcol;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__drow 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__drow;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dlmask 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dlmask;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwrow 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dwrow;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwsecond 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dwsecond;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dws 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dws;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dwhi 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__dwhi;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_c 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_c;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_u 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_u;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_d 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_d;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_l 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_l;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rs_r 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__rs_r;
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__blink__v0) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__blink[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__blink__v0] 
            = __VdlyVal__CoproDrMario__DOT__leafeval__DOT__blink__v0;
    }
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_cells 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_cells;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_vir 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__rv_vir;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__chain;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__strand 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__strand;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sr_addr 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__sr_addr;
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v0) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh[0U] = 0U;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v1) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh[1U] = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh[2U] = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh[3U] = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh[4U] = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh[5U] = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh[6U] = 0U;
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh[7U] = 0U;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__colh__v8) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__colh[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__colh__v8] 
            = __VdlyVal__CoproDrMario__DOT__leafeval__DOT__colh__v8;
    }
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_h 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__run_h;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_lo 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__span_lo;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_hi 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__span_hi;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bl_rq 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__bl_rq;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__vo;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__fwp2 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__fwp2;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_b 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__off_b;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__off_a 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__off_a;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_k0 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__g_k0;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__gk1 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__gk1;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__cpw_p 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__cpw_p;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_i;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__st 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__st;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_m 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__ap_m;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__g_do 
        = __Vdly__CoproDrMario__DOT__leafeval__DOT__g_do;
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v0) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v0] 
            = __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v0;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v1) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v1] 
            = __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v1;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v2) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v2] 
            = __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v2;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v3) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v3] 
            = __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v3;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v4) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v4] = 0U;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v5) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v5] 
            = __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v5;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v6) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v6] = 0U;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v7) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v7] 
            = __VdlyVal__CoproDrMario__DOT__leafeval__DOT__bcell__v7;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v8) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v8] = 0U;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v9) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v9] = 0U;
    }
    if (__VdlySet__CoproDrMario__DOT__leafeval__DOT__bcell__v10) {
        vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell[__VdlyDim0__CoproDrMario__DOT__leafeval__DOT__bcell__v10] = 0U;
    }
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADJL 
        = ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adj_bcd)
            ? ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__adc_bcd)
                ? ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__HC)
                    ? 6U : 0U) : ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__HC)
                                   ? 0U : 0xaU)) : 0U);
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__V 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AV;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__Z 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__AZ;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__DI = vlSelfRef.CoproDrMario__DOT__DI;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ADD 
        = vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__OUT;
    vlSelfRef.CoproDrMario__DOT__lev_done = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__done;
    vlSelfRef.CoproDrMario__DOT__lev_dv_fallback = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__dv_fallback;
    vlSelfRef.CoproDrMario__DOT__lev_legal = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__legal;
    vlSelfRef.CoproDrMario__DOT__lev_rvc = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_cells;
    vlSelfRef.CoproDrMario__DOT__lev_rvv = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rv_vir;
    vlSelfRef.CoproDrMario__DOT__lev_imm = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__imm;
    vlSelfRef.CoproDrMario__DOT__lev_chain = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__chain;
    vlSelfRef.CoproDrMario__DOT__lev_strand = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__strand;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__address_b 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sr_addr;
    vlSelfRef.CoproDrMario__DOT__lev_win = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__win;
    vlSelfRef.CoproDrMario__DOT__lev_sco = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__sco;
    if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__sei 
            = (0x78U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__cli 
            = (0x58U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__clv 
            = (0xb8U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__bit_ins 
            = (0x24U == (0xf7U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__load_reg 
            = (((((((((0xaU == (0x9fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                      || (1U == (0x83U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                     || (0x88U == (0xedU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                    || (0xa0U == (0xf1U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                   || (0xbaU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                  || (0xb4U == (0xf5U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
                 || (0xcaU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                || (0xa1U == (0xa3U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
               || (8U == (0x1fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__sec 
            = (0x38U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__clc 
            = (0x18U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__shift 
            = ((6U == (0x87U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
               || (0xaU == (0x8fU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__compare 
            = (((0xc0U == (0xdbU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))) 
                || (0xccU == (0xdfU & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR)))) 
               || (0xc1U == (0xe3U & (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR))));
    }
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__rdy_h_sq 
        = ((4U <= (((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_hi) 
                    - (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__span_lo)) 
                   - (IData)(1U))) ? VL_EXTEND_II(18,9, 
                                                  ([&]() {
                    vlSelfRef.__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__n 
                        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__run_h;
                    vlSelfRef.__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__Vfuncout 
                        = (0x1ffU & ((IData)(vlSelfRef.__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__n) 
                                     * (IData)(vlSelfRef.__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__n)));
                }(), (IData)(vlSelfRef.__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__Vfuncout)))
            : 0U);
    if ((0xcU == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__state))) {
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__sed 
            = (0xf8U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__cld 
            = (0xd8U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR));
        vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__plp 
            = (0x28U == (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IR));
    }
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_c 
        = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_r 
        = (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo) 
                   >> 3U));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_pix 
        = (0x7fU & ((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk))
                     ? ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i) 
                        - (IData)(8U)) : ((2U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk))
                                           ? ((IData)(8U) 
                                              + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i))
                                           : ((3U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk))
                                               ? ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i) 
                                                  - (IData)(1U))
                                               : ((IData)(1U) 
                                                  + (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i))))));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_phas 
        = (((1U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk)) 
            & (0U != (0xfU & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i) 
                              >> 3U)))) | (((2U == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk)) 
                                            & (0xfU 
                                               != (0xfU 
                                                   & ((IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i) 
                                                      >> 3U)))) 
                                           | (((3U 
                                                == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk)) 
                                               & (0U 
                                                  != 
                                                  (7U 
                                                   & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i)))) 
                                              | ((4U 
                                                  == (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_lk)) 
                                                 & (7U 
                                                    != 
                                                    (7U 
                                                     & (IData)(vlSelfRef.CoproDrMario__DOT__leafeval__DOT__ap_i)))))));
    if (vlSelfRef.CoproDrMario__DOT__lev_wr_arg) {
        if ((1U & (~ ((IData)(vlSelfRef.CoproDrMario__DOT__AB) 
                      >> 2U)))) {
            if ((1U & (~ ((IData)(vlSelfRef.CoproDrMario__DOT__AB) 
                          >> 1U)))) {
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__AB))) {
                    vlSelfRef.CoproDrMario__DOT__lev_a_col 
                        = (7U & (IData)(vlSelfRef.CoproDrMario__DOT__DO));
                }
                if ((1U & (~ (IData)(vlSelfRef.CoproDrMario__DOT__AB)))) {
                    vlSelfRef.CoproDrMario__DOT__lev_a_o4 
                        = (3U & (IData)(vlSelfRef.CoproDrMario__DOT__DO));
                }
            }
            if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__AB))) {
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__AB))) {
                    vlSelfRef.CoproDrMario__DOT__lev_a_cb 
                        = vlSelfRef.CoproDrMario__DOT__lev_colenc;
                }
                if ((1U & (~ (IData)(vlSelfRef.CoproDrMario__DOT__AB)))) {
                    vlSelfRef.CoproDrMario__DOT__lev_a_ca 
                        = vlSelfRef.CoproDrMario__DOT__lev_colenc;
                }
            }
        }
        if ((4U & (IData)(vlSelfRef.CoproDrMario__DOT__AB))) {
            if ((2U & (IData)(vlSelfRef.CoproDrMario__DOT__AB))) {
                if ((1U & (~ (IData)(vlSelfRef.CoproDrMario__DOT__AB)))) {
                    vlSelfRef.CoproDrMario__DOT__lev_a_chw 
                        = vlSelfRef.CoproDrMario__DOT__DO;
                }
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__AB))) {
                    vlSelfRef.CoproDrMario__DOT__lev_a_sl 
                        = (3U & (IData)(vlSelfRef.CoproDrMario__DOT__DO));
                }
            } else if ((1U & (~ (IData)(vlSelfRef.CoproDrMario__DOT__AB)))) {
                vlSelfRef.CoproDrMario__DOT__lev_a_sl 
                    = (3U & (IData)(vlSelfRef.CoproDrMario__DOT__DO));
            }
            if ((1U & (~ ((IData)(vlSelfRef.CoproDrMario__DOT__AB) 
                          >> 1U)))) {
                if ((1U & (IData)(vlSelfRef.CoproDrMario__DOT__AB))) {
                    vlSelfRef.CoproDrMario__DOT__lev_a_fix 
                        = (1U & (IData)(vlSelfRef.CoproDrMario__DOT__DO));
                }
            }
        }
    }
    if (((((IData)(vlSelfRef.CoproDrMario__DOT__WE) 
           & (~ (IData)(vlSelfRef.CoproDrMario__DOT__cpu_rst))) 
          & (IData)(vlSelfRef.CoproDrMario__DOT__a_lev)) 
         & (0xf3U == (0xffU & (IData)(vlSelfRef.CoproDrMario__DOT__AB))))) {
        vlSelfRef.CoproDrMario__DOT__lev_wslot = (3U 
                                                  & (IData)(vlSelfRef.CoproDrMario__DOT__DO));
    }
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[1U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [1U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[2U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [2U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[3U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [3U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[4U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [4U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[5U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [5U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[6U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [6U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[7U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [7U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[8U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [8U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[9U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [9U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xaU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xaU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xbU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xbU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xcU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xcU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xdU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xdU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xeU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xeU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0xfU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0xfU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x10U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x10U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x11U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x11U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x12U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x12U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x13U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x13U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x14U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x14U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x15U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x15U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x16U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x16U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x17U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x17U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x18U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x18U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x19U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x19U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x1fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x1fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x20U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x20U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x21U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x21U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x22U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x22U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x23U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x23U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x24U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x24U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x25U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x25U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x26U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x26U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x27U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x27U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x28U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x28U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x29U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x29U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x2fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x2fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x30U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x30U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x31U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x31U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x32U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x32U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x33U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x33U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x34U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x34U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x35U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x35U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x36U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x36U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x37U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x37U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x38U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x38U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x39U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x39U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x3fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x3fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x40U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x40U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x41U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x41U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x42U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x42U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x43U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x43U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x44U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x44U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x45U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x45U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x46U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x46U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x47U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x47U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x48U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x48U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x49U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x49U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x4fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x4fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x50U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x50U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x51U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x51U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x52U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x52U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x53U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x53U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x54U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x54U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x55U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x55U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x56U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x56U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x57U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x57U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x58U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x58U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x59U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x59U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x5fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x5fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x60U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x60U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x61U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x61U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x62U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x62U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x63U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x63U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x64U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x64U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x65U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x65U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x66U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x66U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x67U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x67U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x68U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x68U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x69U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x69U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x6fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x6fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x70U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x70U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x71U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x71U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x72U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x72U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x73U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x73U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x74U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x74U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x75U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x75U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x76U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x76U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x77U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x77U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x78U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x78U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x79U] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x79U]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7aU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7aU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7bU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7bU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7cU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7cU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7dU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7dU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7eU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7eU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__occ_of[0x7fU] 
        = (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                  [0x7fU]));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [0U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[1U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [1U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [1U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[2U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [2U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [2U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[3U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [3U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [3U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[4U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [4U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [4U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[5U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [5U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [5U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[6U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [6U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [6U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[7U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [7U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [7U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[8U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [8U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [8U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[9U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [9U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                  [9U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xaU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xaU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xaU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xbU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xbU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xbU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xcU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xcU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xcU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xdU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xdU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xdU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xeU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xeU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xeU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0xfU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0xfU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                    [0xfU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x10U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x10U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x10U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x11U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x11U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x11U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x12U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x12U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x12U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x13U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x13U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x13U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x14U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x14U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x14U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x15U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x15U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x15U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x16U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x16U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x16U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x17U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x17U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x17U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x18U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x18U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x18U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x19U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x19U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x19U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x1fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x1fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x1fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x20U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x20U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x20U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x21U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x21U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x21U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x22U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x22U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x22U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x23U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x23U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x23U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x24U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x24U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x24U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x25U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x25U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x25U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x26U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x26U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x26U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x27U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x27U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x27U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x28U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x28U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x28U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x29U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x29U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x29U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x2fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x2fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x2fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x30U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x30U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x30U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x31U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x31U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x31U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x32U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x32U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x32U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x33U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x33U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x33U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x34U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x34U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x34U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x35U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x35U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x35U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x36U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x36U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x36U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x37U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x37U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x37U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x38U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x38U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x38U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x39U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x39U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x39U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x3fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x3fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x3fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x40U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x40U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x40U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x41U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x41U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x41U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x42U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x42U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x42U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x43U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x43U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x43U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x44U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x44U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x44U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x45U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x45U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x45U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x46U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x46U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x46U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x47U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x47U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x47U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x48U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x48U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x48U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x49U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x49U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x49U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x4fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x4fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x4fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x50U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x50U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x50U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x51U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x51U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x51U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x52U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x52U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x52U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x53U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x53U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x53U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x54U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x54U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x54U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x55U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x55U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x55U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x56U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x56U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x56U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x57U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x57U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x57U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x58U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x58U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x58U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x59U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x59U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x59U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x5fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x5fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x5fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x60U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x60U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x60U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x61U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x61U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x61U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x62U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x62U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x62U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x63U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x63U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x63U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x64U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x64U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x64U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x65U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x65U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x65U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x66U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x66U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x66U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x67U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x67U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x67U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x68U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x68U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x68U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x69U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x69U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x69U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x6fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x6fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x6fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x70U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x70U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x70U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x71U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x71U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x71U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x72U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x72U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x72U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x73U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x73U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x73U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x74U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x74U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x74U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x75U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x75U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x75U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x76U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x76U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x76U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x77U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x77U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x77U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x78U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x78U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x78U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x79U] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x79U] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x79U])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7aU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7aU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7aU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7bU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7bU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7bU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7cU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7cU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7cU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7dU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7dU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7dU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7eU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7eU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7eU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vir_of[0x7fU] 
        = ((vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
            [0x7fU] >> 2U) & (0U != (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
                                     [0x7fU])));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[1U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [1U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[2U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [2U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[3U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [3U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[4U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [4U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[5U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [5U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[6U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [6U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[7U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [7U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[8U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [8U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[9U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [9U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xaU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xaU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xbU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xbU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xcU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xcU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xdU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xdU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xeU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xeU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0xfU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0xfU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x10U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x10U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x11U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x11U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x12U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x12U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x13U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x13U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x14U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x14U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x15U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x15U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x16U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x16U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x17U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x17U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x18U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x18U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x19U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x19U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x1fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x1fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x20U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x20U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x21U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x21U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x22U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x22U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x23U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x23U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x24U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x24U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x25U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x25U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x26U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x26U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x27U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x27U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x28U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x28U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x29U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x29U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x2fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x2fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x30U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x30U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x31U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x31U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x32U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x32U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x33U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x33U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x34U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x34U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x35U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x35U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x36U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x36U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x37U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x37U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x38U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x38U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x39U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x39U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x3fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x3fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x40U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x40U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x41U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x41U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x42U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x42U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x43U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x43U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x44U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x44U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x45U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x45U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x46U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x46U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x47U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x47U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x48U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x48U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x49U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x49U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x4fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x4fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x50U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x50U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x51U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x51U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x52U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x52U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x53U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x53U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x54U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x54U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x55U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x55U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x56U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x56U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x57U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x57U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x58U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x58U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x59U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x59U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x5fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x5fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x60U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x60U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x61U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x61U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x62U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x62U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x63U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x63U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x64U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x64U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x65U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x65U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x66U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x66U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x67U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x67U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x68U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x68U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x69U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x69U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x6fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x6fU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x70U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x70U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x71U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x71U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x72U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x72U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x73U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x73U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x74U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x74U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x75U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x75U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x76U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x76U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x77U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x77U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x78U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x78U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x79U] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x79U]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7aU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7aU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7bU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7bU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7cU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7cU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7dU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7dU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7eU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7eU]);
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of[0x7fU] 
        = (3U & vlSelfRef.CoproDrMario__DOT__leafeval__DOT__bcell
           [0x7fU]);
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__P = 
        (0x30U | ((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__N) 
                    << 7U) | ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__V) 
                              << 6U)) | ((((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__D) 
                                           << 3U) | 
                                          ((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__I) 
                                           << 2U)) 
                                         | (((IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__Z) 
                                             << 1U) 
                                            | (IData)(vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C)))));
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__v_col 
        = vlSelfRef.CoproDrMario__DOT__leafeval__DOT__col_of
        [vlSelfRef.CoproDrMario__DOT__leafeval__DOT__vo];
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_col 
        = vlSelfRef.CoproDrMario__DOT__lev_a_col;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_chw 
        = vlSelfRef.CoproDrMario__DOT__lev_a_chw;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_fix 
        = vlSelfRef.CoproDrMario__DOT__lev_a_fix;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_cb 
        = vlSelfRef.CoproDrMario__DOT__lev_a_cb;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_ca 
        = vlSelfRef.CoproDrMario__DOT__lev_a_ca;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_sl 
        = vlSelfRef.CoproDrMario__DOT__lev_a_sl;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__a_o4 
        = vlSelfRef.CoproDrMario__DOT__lev_a_o4;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__wslot 
        = vlSelfRef.CoproDrMario__DOT__lev_wslot;
}
