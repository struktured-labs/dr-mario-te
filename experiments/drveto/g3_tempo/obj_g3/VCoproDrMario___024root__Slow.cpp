// Verilated -*- C++ -*-
// DESCRIPTION: Verilator output: Design implementation internals
// See VCoproDrMario.h for the primary calling header

#include "VCoproDrMario__pch.h"
#include "VCoproDrMario__Syms.h"
#include "VCoproDrMario___024root.h"

// Parameter definitions for VCoproDrMario___024root
constexpr CData/*6:0*/ VCoproDrMario___024root::CoproDrMario__DOT__WIN;
constexpr CData/*1:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__SEL_A;
constexpr CData/*1:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__SEL_S;
constexpr CData/*1:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__SEL_X;
constexpr CData/*1:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__SEL_Y;
constexpr CData/*3:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__OP_OR;
constexpr CData/*3:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__OP_AND;
constexpr CData/*3:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__OP_EOR;
constexpr CData/*3:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__OP_ADD;
constexpr CData/*3:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__OP_SUB;
constexpr CData/*3:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__OP_ROL;
constexpr CData/*3:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__OP_A;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__ABS0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__ABS1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__ABSX0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__ABSX1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__ABSX2;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__BRA0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__BRA1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__BRA2;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__BRK0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__BRK1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__BRK2;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__BRK3;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__DECODE;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__FETCH;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__INDX0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__INDX1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__INDX2;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__INDX3;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__INDY0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__INDY1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__INDY2;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__INDY3;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__JMP0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__JMP1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__JMPI0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__JMPI1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__JSR0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__JSR1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__JSR2;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__JSR3;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__PULL0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__PULL1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__PULL2;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__PUSH0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__PUSH1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__READ;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__REG;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__RTI0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__RTI1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__RTI2;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__RTI3;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__RTI4;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__RTS0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__RTS1;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__RTS2;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__RTS3;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__WRITE;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__ZP0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__ZPX0;
constexpr CData/*5:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__ZPX1;
constexpr CData/*7:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__ZEROPAGE;
constexpr CData/*7:0*/ VCoproDrMario___024root::CoproDrMario__DOT__cpu6502__DOT__STACKPAGE;
constexpr CData/*2:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__LK_NONE;
constexpr CData/*2:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__LK_UP;
constexpr CData/*2:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__LK_DOWN;
constexpr CData/*2:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__LK_LEFT;
constexpr CData/*2:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__LK_RIGHT;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_IDLE;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_COLWALK;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_VNEXT;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_HRUN_L;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_HSPAN_L;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_HRUN_R;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_HSPAN_R;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_VRUN_U;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_VSPAN_U;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_VRUN_D;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_VSPAN_D;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_POLROW;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_POLCOL;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_VFIN;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_SETUP_H;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_SETUP_V;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DONE;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_COPY;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_FO1;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_FO2;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_PLACE;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_SCAN;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_EOL;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_APPLY;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_GRAV;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_RESDONE;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_CP_R;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_CP_W;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_CP_P;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DONE2;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DPOL;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DNEW;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DBUR;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DADV;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DRV;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DRVFIN;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DSETH;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DUNPL;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DSETV;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DCOMB;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_GRAV2;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_FPREP;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_APPLY_P;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_GRAV_D;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_APPLY_U;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_GRAV_MA;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_GRAV2MA;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_PLACE_B;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_DUNPL_B;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_APPLY_W;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_GRAV_W;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_GRAV2_W;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_CP_W_P;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_APPLY2;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_GRAV_M;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_GRAV2M;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_STR_R;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__S_STR_D;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__slotram__DOT__widthad_a;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__leafeval__DOT__slotram__DOT__width_a;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__wram__DOT__widthad_a;
constexpr IData/*31:0*/ VCoproDrMario___024root::CoproDrMario__DOT__wram__DOT__width_a;


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
