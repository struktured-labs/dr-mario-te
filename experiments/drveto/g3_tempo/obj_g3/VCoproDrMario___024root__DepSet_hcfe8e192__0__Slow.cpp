// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VCoproDrMario.h for the primary calling header

#include "VCoproDrMario__pch.h"
#include "VCoproDrMario___024root.h"

VL_ATTR_COLD void VCoproDrMario___024root___eval_static__TOP(VCoproDrMario___024root* vlSelf);

VL_ATTR_COLD void VCoproDrMario___024root___eval_static(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_static\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    VCoproDrMario___024root___eval_static__TOP(vlSelf);
}

VL_ATTR_COLD void VCoproDrMario___024root___eval_static__TOP(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_static__TOP\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelfRef.CoproDrMario__DOT__rst_cnt = 0x1fU;
    vlSelfRef.CoproDrMario__DOT__parked = 1U;
    vlSelfRef.CoproDrMario__DOT__rst_m = 1U;
    vlSelfRef.CoproDrMario__DOT__cpu_rst = 1U;
    vlSelfRef.CoproDrMario__DOT__lev_a_fix = 0U;
    vlSelfRef.CoproDrMario__DOT__lev_a_chw = 0U;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__C = 0U;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__Z = 0U;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__I = 0U;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__D = 0U;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__V = 0U;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__N = 0U;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_edge = 0U;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI_1 = 0U;
}

VL_ATTR_COLD void VCoproDrMario___024root___eval_initial__TOP(VCoproDrMario___024root* vlSelf);

VL_ATTR_COLD void VCoproDrMario___024root___eval_initial(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_initial\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    VCoproDrMario___024root___eval_initial__TOP(vlSelf);
    vlSelfRef.__Vtrigprevexpr___TOP__clk_cpu__0 = vlSelfRef.clk_cpu;
    vlSelfRef.__Vtrigprevexpr___TOP__clk__0 = vlSelfRef.clk;
    vlSelfRef.__Vtrigprevexpr___TOP__CoproDrMario__DOT__cpu_rst__0 
        = vlSelfRef.CoproDrMario__DOT__cpu_rst;
}

VL_ATTR_COLD void VCoproDrMario___024root___eval_initial__TOP(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_initial__TOP\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    VlWide<4>/*127:0*/ __Vtemp_1;
    // Body
    __Vtemp_1[0U] = 0x2e686578U;
    __Vtemp_1[1U] = 0x5f726f6dU;
    __Vtemp_1[2U] = 0x6f70726fU;
    __Vtemp_1[3U] = 0x63U;
    VL_READMEM_N(true, 8, 16384, 0, VL_CVT_PACK_STR_NW(4, __Vtemp_1)
                 ,  &(vlSelfRef.CoproDrMario__DOT__rom)
                 , 0, ~0ULL);
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__IRQ = 0U;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__NMI = 0U;
    vlSelfRef.CoproDrMario__DOT__cpu6502__DOT__RDY = 1U;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__data_b = 0U;
    vlSelfRef.CoproDrMario__DOT__leafeval__DOT__slotram__DOT__wren_b = 0U;
}

VL_ATTR_COLD void VCoproDrMario___024root___eval_final(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_final\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VCoproDrMario___024root___dump_triggers__stl(VCoproDrMario___024root* vlSelf);
#endif  // VL_DEBUG
VL_ATTR_COLD bool VCoproDrMario___024root___eval_phase__stl(VCoproDrMario___024root* vlSelf);

VL_ATTR_COLD void VCoproDrMario___024root___eval_settle(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_settle\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    IData/*31:0*/ __VstlIterCount;
    CData/*0:0*/ __VstlContinue;
    // Body
    __VstlIterCount = 0U;
    vlSelfRef.__VstlFirstIteration = 1U;
    __VstlContinue = 1U;
    while (__VstlContinue) {
        if (VL_UNLIKELY((0x64U < __VstlIterCount))) {
#ifdef VL_DEBUG
            VCoproDrMario___024root___dump_triggers__stl(vlSelf);
#endif
            VL_FATAL_MT("/home/struktured/projects/dr-mario-tempo-wt/experiments/drveto/g3_tempo/../../../fpga/copro/CoproDrMario.sv", 22, "", "Settle region did not converge.");
        }
        __VstlIterCount = ((IData)(1U) + __VstlIterCount);
        __VstlContinue = 0U;
        if (VCoproDrMario___024root___eval_phase__stl(vlSelf)) {
            __VstlContinue = 1U;
        }
        vlSelfRef.__VstlFirstIteration = 0U;
    }
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VCoproDrMario___024root___dump_triggers__stl(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___dump_triggers__stl\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1U & (~ vlSelfRef.__VstlTriggered.any()))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelfRef.__VstlTriggered.word(0U))) {
        VL_DBG_MSGF("         'stl' region trigger index 0 is active: Internal 'stl' trigger - first iteration\n");
    }
}
#endif  // VL_DEBUG

void VCoproDrMario___024root___ico_sequent__TOP__0(VCoproDrMario___024root* vlSelf);

VL_ATTR_COLD void VCoproDrMario___024root___eval_stl(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_stl\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1ULL & vlSelfRef.__VstlTriggered.word(0U))) {
        VCoproDrMario___024root___ico_sequent__TOP__0(vlSelf);
    }
}

VL_ATTR_COLD void VCoproDrMario___024root___eval_triggers__stl(VCoproDrMario___024root* vlSelf);

VL_ATTR_COLD bool VCoproDrMario___024root___eval_phase__stl(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___eval_phase__stl\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Init
    CData/*0:0*/ __VstlExecute;
    // Body
    VCoproDrMario___024root___eval_triggers__stl(vlSelf);
    __VstlExecute = vlSelfRef.__VstlTriggered.any();
    if (__VstlExecute) {
        VCoproDrMario___024root___eval_stl(vlSelf);
    }
    return (__VstlExecute);
}

#ifdef VL_DEBUG
VL_ATTR_COLD void VCoproDrMario___024root___dump_triggers__ico(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___dump_triggers__ico\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1U & (~ vlSelfRef.__VicoTriggered.any()))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelfRef.__VicoTriggered.word(0U))) {
        VL_DBG_MSGF("         'ico' region trigger index 0 is active: Internal 'ico' trigger - first iteration\n");
    }
}
#endif  // VL_DEBUG

#ifdef VL_DEBUG
VL_ATTR_COLD void VCoproDrMario___024root___dump_triggers__act(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___dump_triggers__act\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1U & (~ vlSelfRef.__VactTriggered.any()))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelfRef.__VactTriggered.word(0U))) {
        VL_DBG_MSGF("         'act' region trigger index 0 is active: @(posedge clk_cpu)\n");
    }
    if ((2ULL & vlSelfRef.__VactTriggered.word(0U))) {
        VL_DBG_MSGF("         'act' region trigger index 1 is active: @(posedge clk)\n");
    }
    if ((4ULL & vlSelfRef.__VactTriggered.word(0U))) {
        VL_DBG_MSGF("         'act' region trigger index 2 is active: @(posedge CoproDrMario.cpu_rst)\n");
    }
}
#endif  // VL_DEBUG

#ifdef VL_DEBUG
VL_ATTR_COLD void VCoproDrMario___024root___dump_triggers__nba(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___dump_triggers__nba\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    if ((1U & (~ vlSelfRef.__VnbaTriggered.any()))) {
        VL_DBG_MSGF("         No triggers active\n");
    }
    if ((1ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VL_DBG_MSGF("         'nba' region trigger index 0 is active: @(posedge clk_cpu)\n");
    }
    if ((2ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VL_DBG_MSGF("         'nba' region trigger index 1 is active: @(posedge clk)\n");
    }
    if ((4ULL & vlSelfRef.__VnbaTriggered.word(0U))) {
        VL_DBG_MSGF("         'nba' region trigger index 2 is active: @(posedge CoproDrMario.cpu_rst)\n");
    }
}
#endif  // VL_DEBUG

VL_ATTR_COLD void VCoproDrMario___024root___ctor_var_reset(VCoproDrMario___024root* vlSelf) {
    (void)vlSelf;  // Prevent unused variable warning
    VCoproDrMario__Syms* const __restrict vlSymsp VL_ATTR_UNUSED = vlSelf->vlSymsp;
    VL_DEBUG_IF(VL_DBG_MSGF("+    VCoproDrMario___024root___ctor_var_reset\n"); );
    auto& vlSelfRef = std::ref(*vlSelf).get();
    // Body
    vlSelf->clk = VL_RAND_RESET_I(1);
    vlSelf->clk_cpu = VL_RAND_RESET_I(1);
    vlSelf->ce = VL_RAND_RESET_I(1);
    vlSelf->enable = VL_RAND_RESET_I(1);
    vlSelf->prg_ain = VL_RAND_RESET_I(16);
    vlSelf->prg_read = VL_RAND_RESET_I(1);
    vlSelf->prg_write = VL_RAND_RESET_I(1);
    vlSelf->prg_din = VL_RAND_RESET_I(8);
    vlSelf->prg_dout = VL_RAND_RESET_I(8);
    vlSelf->copro_sel = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__clk = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__clk_cpu = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__ce = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__enable = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__prg_ain = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__prg_read = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__prg_write = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__prg_din = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__prg_dout = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__copro_sel = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__AB = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__DO = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__WE = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__rst_cnt = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__parked = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu_rst_src = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__rst_m = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu_rst = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__DI = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__a_ram_lo = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__a_ram_st = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__a_ram = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__a_rom = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__a_vec = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__a_lev = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__a_addr = VL_RAND_RESET_I(12);
    vlSelf->CoproDrMario__DOT__lev_wr_board = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__lev_start = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__lev_cmd_go = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__lev_wr_arg = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__lev_enc = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__lev_lnk = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__lev_colenc = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__lev_wslot = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__lev_a_o4 = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__lev_a_sl = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__lev_a_ca = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__lev_a_cb = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__lev_a_col = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__lev_a_fix = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__lev_a_chw = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__lev_done = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__lev_win = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__lev_legal = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__lev_sco = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__lev_imm = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__lev_rvc = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__lev_rvv = VL_RAND_RESET_I(6);
    vlSelf->CoproDrMario__DOT__lev_chain = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__lev_dv_fallback = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__lev_strand = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__lev_q = VL_RAND_RESET_I(8);
    for (int __Vi0 = 0; __Vi0 < 16384; ++__Vi0) {
        vlSelf->CoproDrMario__DOT__rom[__Vi0] = VL_RAND_RESET_I(8);
    }
    vlSelf->CoproDrMario__DOT__rom_q = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__ram_a_q = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__ram_b_q = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT____Vcellinp__wram__wren_a = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__sel_ram_d = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__sel_rom_d = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__sel_vec_d = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__sel_lev_d = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__ab0_d = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__hb_addr = VL_RAND_RESET_I(12);
    vlSelf->CoproDrMario__DOT__hb_din = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__hb_we = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__clk = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__reset = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__AB = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__DI = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__DO = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__WE = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__IRQ = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__NMI = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__RDY = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__PC = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ABL = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ABH = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ADD = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__DIHOLD = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__DIHOLD_valid = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__DIMUX = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__IRHOLD = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__IRHOLD_valid = VL_RAND_RESET_I(1);
    for (int __Vi0 = 0; __Vi0 < 4; ++__Vi0) {
        vlSelf->CoproDrMario__DOT__cpu6502__DOT__AXYS[__Vi0] = VL_RAND_RESET_I(8);
    }
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__C = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__Z = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__I = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__D = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__V = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__N = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__AZ = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__AV = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__AN = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__HC = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__AI = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__BI = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__IR = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__CI = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__CO = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__PCH = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__PCL = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__NMI_edge = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__regsel = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__regfile = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__P = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__state = VL_RAND_RESET_I(6);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__PC_inc = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__PC_temp = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__src_reg = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__dst_reg = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__index_y = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__load_reg = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__inc = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__write_back = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__load_only = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__store = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__adc_sbc = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__compare = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__shift = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__rotate = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__backwards = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__cond_true = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__cond_code = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__shift_right = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__alu_shift_right = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__op = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__alu_op = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__adc_bcd = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__adj_bcd = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__bit_ins = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__plp = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__php = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__clc = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__sec = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__cld = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__sed = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__cli = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__sei = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__clv = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__brk = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__res = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__write_register = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ADJL = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ADJH = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__NMI_1 = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__clk = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__op = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__right = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__AI = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__BI = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CI = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CO = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__BCD = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__OUT = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__V = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__Z = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__N = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__HC = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__RDY = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__AI7 = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__BI7 = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_logic = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_BI = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_l = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_h = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__adder_CI = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__HC9 = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__CO9 = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__cpu6502__DOT__ALU__DOT__temp_HC = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__clk = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rst = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__wr = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__waddr = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__wdata = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__wlnk = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__wslot = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__start = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__cmd = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__cmd_go = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__a_sl = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__a_o4 = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__a_col = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__a_ca = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__a_cb = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__a_fix = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__a_chw = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__done = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__sco = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__win = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__legal = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rv_cells = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rv_vir = VL_RAND_RESET_I(6);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__imm = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__chain = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dv_fallback = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__strand = VL_RAND_RESET_I(7);
    for (int __Vi0 = 0; __Vi0 < 128; ++__Vi0) {
        vlSelf->CoproDrMario__DOT__leafeval__DOT__bcell[__Vi0] = VL_RAND_RESET_I(3);
    }
    for (int __Vi0 = 0; __Vi0 < 128; ++__Vi0) {
        vlSelf->CoproDrMario__DOT__leafeval__DOT__blink[__Vi0] = VL_RAND_RESET_I(3);
    }
    vlSelf->CoproDrMario__DOT__leafeval__DOT__bl_ra = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__bl_rq = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__byp_fire = VL_RAND_RESET_I(32);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__byp_used = VL_RAND_RESET_I(32);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ap_phas = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ap_pix = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__bl_wa = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__bl_wd = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__bl_we = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__sr_addr = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__cpw_p = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__sr_waddr = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__sl_we = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__sl_cpw = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__sl_wa = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__sl_wd = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__sl_qb = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotq = VL_RAND_RESET_I(3);
    for (int __Vi0 = 0; __Vi0 < 128; ++__Vi0) {
        vlSelf->CoproDrMario__DOT__leafeval__DOT__col_of[__Vi0] = VL_RAND_RESET_I(2);
    }
    for (int __Vi0 = 0; __Vi0 < 128; ++__Vi0) {
        vlSelf->CoproDrMario__DOT__leafeval__DOT__occ_of[__Vi0] = VL_RAND_RESET_I(1);
    }
    for (int __Vi0 = 0; __Vi0 < 128; ++__Vi0) {
        vlSelf->CoproDrMario__DOT__leafeval__DOT__vir_of[__Vi0] = VL_RAND_RESET_I(1);
    }
    vlSelf->CoproDrMario__DOT__leafeval__DOT__cmd_l = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__st = VL_RAND_RESET_I(6);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__node_leaf = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fo1 = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fo2 = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fwp = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__off_a = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__off_b = VL_RAND_RESET_I(7);
    VL_RAND_RESET_W(128, vlSelf->CoproDrMario__DOT__leafeval__DOT__markb);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__str_i = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rs_c = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rs_u = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rs_d = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rs_l = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rs_r = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rs_p = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__li = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__soff = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__sstep = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__scnt = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__srun = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__smcol = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__srstart = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fwp2 = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__anyclear = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__gr = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__gc = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__gmoved = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__gk1 = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__g_do = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__g_has = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ga_isrep = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ga_occ = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ga_vir = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ga_blk0 = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__chain_bonus = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__g_k0 = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__g_k1 = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__g_cell = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__g_lnk = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ap_m = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ap_vir = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ap_lk = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ap_i = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ap_unl = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__ap_pixr = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fullscan = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fli = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__wc = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__wr_ = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__maxh = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__holes = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__toprisk = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__spawn = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__setup = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__pollution = VL_RAND_RESET_I(11);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__buried = VL_RAND_RESET_I(10);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__matched60 = VL_RAND_RESET_I(13);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rdy_ext = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__vrdy = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__anyvir = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__seen = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fillcnt = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__curcol = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__curlen = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__vseen = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__maxh_p = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__holes_p = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__toprisk_p = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__spawn_p = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__setup_p = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__pollution_p = VL_RAND_RESET_I(11);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__buried_p = VL_RAND_RESET_I(10);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rdy_ext_p = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__vrdy_p = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__matched60_p = VL_RAND_RESET_I(13);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_mode = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__delta_mode = VL_RAND_RESET_I(1);
    for (int __Vi0 = 0; __Vi0 < 8; ++__Vi0) {
        vlSelf->CoproDrMario__DOT__leafeval__DOT__colh[__Vi0] = VL_RAND_RESET_I(5);
    }
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_maxh = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_holes = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_toprisk = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_spawn = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_setup = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_pol = VL_RAND_RESET_I(11);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_buried = VL_RAND_RESET_I(10);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_matched = VL_RAND_RESET_I(13);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_rdy = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_vrdy = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__base_anyvir = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__od_bur = VL_RAND_RESET_I(10);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__nd_bur = VL_RAND_RESET_I(10);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__od_rdy = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__nd_rdy = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__od_vrdy = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__nd_vrdy = VL_RAND_RESET_I(16);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__od_set = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__nd_set = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dd_matched = VL_RAND_RESET_I(13);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dd_pol = VL_RAND_RESET_I(11);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dd_holes = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__pca = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__pcb = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dsoff = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dscnt = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dstep = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dphase = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__daff = VL_RAND_RESET_I(7);
    VL_RAND_RESET_W(128, vlSelf->CoproDrMario__DOT__leafeval__DOT__affbit);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dcol = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__drow = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dbur_new = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dcolstep = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dlmask = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dws = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dwhi = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dwrow = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dwsecond = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__vo = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__v_r = VL_RAND_RESET_I(4);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__v_c = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__v_col = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__run_h = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__run_v = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__p = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__span_lo = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__span_hi = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__vspan_lo = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__vspan_hi = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__rdy_h_sq = VL_RAND_RESET_I(18);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__i = VL_RAND_RESET_I(32);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fo2b__DOT__fom = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__scan__DOT__brk = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__scan__DOT__c_ = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__feol__DOT__nx = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__grv__DOT__lk = VL_RAND_RESET_I(3);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__grv__DOT__isrep = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__grv__DOT__haspt = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__grv__DOT__blk = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__grv__DOT__dofall = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__grv__DOT__k0 = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__grv__DOT__k1 = VL_RAND_RESET_I(7);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__grvd__DOT__blk = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fin__DOT__hq = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fin__DOT__vq = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__fin__DOT__mx = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__suh__DOT__c0 = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__suh__DOT__t = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__suv__DOT__c0 = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__suv__DOT__t = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dnew__DOT__ga = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dnew__DOT__gb = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hha = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hhb = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dcomb__DOT__hmax = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dbur__DOT__excess = VL_RAND_RESET_I(5);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__hq = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__vq = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__drvfin__DOT__mx = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dseth__DOT__c0 = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dseth__DOT__tt = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__c0 = VL_RAND_RESET_I(2);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__dsetv__DOT__tt = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__clock_a = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__address_a = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__data_a = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__wren_a = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__q_a = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__clock_b = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__address_b = VL_RAND_RESET_I(9);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__data_b = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__wren_b = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__q_b = VL_RAND_RESET_I(8);
    for (int __Vi0 = 0; __Vi0 < 512; ++__Vi0) {
        vlSelf->CoproDrMario__DOT__leafeval__DOT__slotram__DOT__mem[__Vi0] = VL_RAND_RESET_I(8);
    }
    vlSelf->CoproDrMario__DOT__wram__DOT__clock_a = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__wram__DOT__address_a = VL_RAND_RESET_I(12);
    vlSelf->CoproDrMario__DOT__wram__DOT__data_a = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__wram__DOT__wren_a = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__wram__DOT__q_a = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__wram__DOT__clock_b = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__wram__DOT__address_b = VL_RAND_RESET_I(12);
    vlSelf->CoproDrMario__DOT__wram__DOT__data_b = VL_RAND_RESET_I(8);
    vlSelf->CoproDrMario__DOT__wram__DOT__wren_b = VL_RAND_RESET_I(1);
    vlSelf->CoproDrMario__DOT__wram__DOT__q_b = VL_RAND_RESET_I(8);
    for (int __Vi0 = 0; __Vi0 < 4096; ++__Vi0) {
        vlSelf->CoproDrMario__DOT__wram__DOT__mem[__Vi0] = VL_RAND_RESET_I(8);
    }
    vlSelf->__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__Vfuncout = VL_RAND_RESET_I(9);
    vlSelf->__Vfunc_CoproDrMario__DOT__leafeval__DOT__sq__2__n = VL_RAND_RESET_I(5);
    vlSelf->__Vdly__CoproDrMario__DOT__cpu6502__DOT__state = VL_RAND_RESET_I(6);
    vlSelf->__VdlyVal__CoproDrMario__DOT__wram__DOT__mem__v0 = VL_RAND_RESET_I(8);
    vlSelf->__VdlyDim0__CoproDrMario__DOT__wram__DOT__mem__v0 = VL_RAND_RESET_I(12);
    vlSelf->__VdlySet__CoproDrMario__DOT__wram__DOT__mem__v0 = 0;
    vlSelf->__VdlyVal__CoproDrMario__DOT__wram__DOT__mem__v1 = VL_RAND_RESET_I(8);
    vlSelf->__VdlyDim0__CoproDrMario__DOT__wram__DOT__mem__v1 = VL_RAND_RESET_I(12);
    vlSelf->__VdlySet__CoproDrMario__DOT__wram__DOT__mem__v1 = 0;
    vlSelf->__Vtrigprevexpr___TOP__clk_cpu__0 = VL_RAND_RESET_I(1);
    vlSelf->__Vtrigprevexpr___TOP__clk__0 = VL_RAND_RESET_I(1);
    vlSelf->__Vtrigprevexpr___TOP__CoproDrMario__DOT__cpu_rst__0 = VL_RAND_RESET_I(1);
}
