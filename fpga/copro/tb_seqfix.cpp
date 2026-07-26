// Isolate the CMD-7 -> CMD-4 cross-command corruption (the P3 delta bug).
// For each board group in leafeval_node_cases.txt: pick a NON-CLEARING placement as the
// delta (CMD-6 base once, then CMD-7), then WITHOUT reset run a fresh full CMD-4 NODE on a
// second placement (via CMD-2 cur<-slot1) and compare its leaf to the reset+CMD-4 reference.
// Dumps which sco COMPONENT diverges -> names the stale register CMD-7 leaves behind.
#include "VLeafEval.h"
#include "VLeafEval___024root.h"
#include "verilated.h"
#include <cstdio>
#include <cstring>

static VLeafEval* t;
static void tick(){ t->clk=0; t->eval(); t->clk=1; t->eval(); }
static void reset(){ t->rst=1; t->wr=0; t->cmd_go=0; tick(); tick(); t->rst=0; tick(); }
static void load(const int* b, int slot){
  t->wslot=slot;
  for(int i=0;i<128;i++){ int e=0; if(b[i]!=0xFF) e=((((b[i]&0xF0)==0xD0)?1:0)<<2)|((b[i]&3)+1);
    t->wr=1; t->waddr=i; t->wdata=e; tick(); }
  t->wr=0; t->wslot=0;
}
static void run(int cmd,int o4,int col,int ca,int cb,int sl=0){
  t->a_o4=o4; t->a_col=col; t->a_ca=ca+1; t->a_cb=cb+1; t->a_sl=sl;
  t->cmd=cmd; t->cmd_go=1; tick(); t->cmd_go=0;
  long c=0; while(!t->done && c<200000){ tick(); c++; }
}
#define P(f) ((long)t->rootp->LeafEval__DOT__##f)

struct Comp { int sco,setup,buried,rdy,vrdy,holes,matched,maxh,tr,spawn,pol,imm,win,leg; };
static Comp grab(){ Comp c;
  c.sco=(short)t->sco; c.setup=P(setup); c.buried=P(buried); c.rdy=P(rdy_ext); c.vrdy=P(vrdy);
  c.holes=P(holes); c.matched=P(matched60); c.maxh=P(maxh); c.tr=P(toprisk); c.spawn=P(spawn);
  c.pol=P(pollution); c.imm=(int)t->imm; c.win=(int)t->win; c.leg=(int)t->legal; return c; }
static void diff(const char*tag,Comp r,Comp s){
  if(memcmp(&r,&s,sizeof r)==0){ return; }
  printf("  [%s] MISMATCH ref->seq:",tag);
  #define D(f) if(r.f!=s.f) printf(" " #f "=%d->%d",r.f,s.f);
  D(sco)D(setup)D(buried)D(rdy)D(vrdy)D(holes)D(matched)D(maxh)D(tr)D(spawn)D(pol)D(imm)D(win)D(leg)
  printf("\n");
}

struct Case{ int b[128],o4,col,ca,cb; };
int main(int argc,char**argv){
  Verilated::commandArgs(argc,argv);
  FILE*g=fopen("leafeval_node_cases.txt","r"); if(!g){printf("no corpus\n");return 1;}
  int n; if(fscanf(g,"%d",&n)!=1)return 1;
  static Case cs[20000]; int m=0;
  for(int k=0;k<n&&k<20000;k++){ Case&c=cs[m];
    for(int i=0;i<128;i++) if(fscanf(g,"%x",&c.b[i])!=1)return 1;
    int lg,ce,vi,im,sc,wi; if(fscanf(g,"%d %d %d %d %d %d %d %d %d %d",&c.o4,&c.col,&c.ca,&c.cb,&lg,&ce,&vi,&im,&sc,&wi)!=10)return 1;
    int nb; for(int i=0;i<128;i++) if(fscanf(g,"%x",&nb)!=1)return 1;
    m++;
  }
  fclose(g);
  t=new VLeafEval; reset();

  int groups=0, bad=0, shown=0;
  int i=0;
  while(i<m){
    int j=i+1; while(j<m && memcmp(cs[j].b,cs[i].b,sizeof cs[i].b)==0) j++;
    int gN=j-i; groups++;
    if(gN>=2){
      // node placement np = each placement; the "delta history" before it = ALL placements in the
      // group run as CMD-7 (with the firmware's clearing fallback), base latched once, CUR held.
      for(int np=0; np<gN; np++){ Case&c=cs[i+np];
        // REFERENCE: fresh reset + CMD-4 on placement np
        reset(); load(c.b,0); run(4,c.o4,c.col,c.ca,c.cb); Comp ref=grab();
        // SEQUENCE: base once, then CMD-7 over EVERY placement (fallback-faithful), CUR=parent held
        reset(); load(cs[i].b,0); load(cs[i].b,1);
        run(6,0,0,0,0);                               // CMD-6 base latch (once)
        for(int p=0;p<gN;p++){ Case&d=cs[i+p];
          run(7,d.o4,d.col,d.ca,d.cb);                // CMD-7 delta
          if(t->dv_fallback){                          // clearing -> firmware fallback (_e_dnode)
            run(2,0,0,0,0,1);                          // CUR<-slot1
            run(4,d.o4,d.col,d.ca,d.cb);               // full NODE
            run(2,0,0,0,0,1);                          // CUR<-slot1 (restore for next delta)
          }
        }
        run(2,0,0,0,0,1);                             // CUR<-slot1 restore
        run(4,c.o4,c.col,c.ca,c.cb);                  // CMD-4 fresh node on placement np
        Comp seq=grab();
        if(memcmp(&ref,&seq,sizeof ref)!=0){ bad++;
          if(shown<12){ shown++;
            printf("grp@%d gN=%d np=%d(o4=%d col=%d)\n",i,gN,np,c.o4,c.col);
            diff("CMD7seq->CMD4",ref,seq); } }
      }
    }
    i=j;
  }
  // === PERMANENT REGRESSION: an ILLEGAL-landing CMD-7 (col=7 horizontal -> off-board, leg=0) must
  // not leak delta_mode into the NEXT fresh command. Pre-fix this corrupted CMD-4/CMD-1 (delta_mode
  // stale -> resolve-completion takes the delta path). Gated on LEGAL reference nodes (the firmware
  // never consumes an illegal node's leaf). Fixed RTL: 0/0; unfixed RTL: many (positive control).
  int e4=0, e1=0, e6=0, nlegal=0;
  for(int p=0;p<m;p++){ Case&c=cs[p];
    reset(); load(c.b,0); run(4,c.o4,c.col,c.ca,c.cb); Comp ref4=grab();
    if(!ref4.leg) continue;
    nlegal++;
    // (1) illegal CMD-7 -> CMD-4 NODE  (NODE vector)
    reset(); load(c.b,0); load(c.b,1);
    run(7,3,7,0,0); run(2,0,0,0,0,1); run(4,c.o4,c.col,c.ca,c.cb);
    { Comp x=grab(); if(memcmp(&ref4,&x,sizeof ref4)!=0){ e4++; if(e4<=4){printf("[NODE] case %d:",p); diff("ill7->CMD4",ref4,x);} } }
    // (2) illegal CMD-7 -> CMD-1 LEAF  (LEAF vector); reference = fresh CMD-1 on the same board.
    // CMD-1 does not produce legal/imm (they persist stale), so those fields are excluded.
    reset(); load(c.b,0); run(1,0,0,0,0); Comp ref1=grab(); ref1.leg=0; ref1.imm=0;
    reset(); load(c.b,0); load(c.b,1);
    run(7,3,7,0,0); run(2,0,0,0,0,1); run(1,0,0,0,0);
    { Comp x=grab(); x.leg=0; x.imm=0; if(memcmp(&ref1,&x,sizeof ref1)!=0){ e1++; if(e1<=4){printf("[LEAF] case %d:",p); diff("ill7->CMD1",ref1,x);} } }
    // (3) illegal CMD-7 -> CMD-6 BASE -> CMD-4 NODE  (BASE-entry defense-in-depth)
    reset(); load(c.b,0); load(c.b,1);
    run(7,3,7,0,0); run(6,0,0,0,0); run(2,0,0,0,0,1); run(4,c.o4,c.col,c.ca,c.cb);
    { Comp x=grab(); if(memcmp(&ref4,&x,sizeof ref4)!=0){ e6++; if(e6<=4){printf("[BASE] case %d:",p); diff("ill7->CMD6->CMD4",ref4,x);} } }
  }
  int total = bad + e4 + e1 + e6;
  printf("SEQFIX: %d groups; CMD7seq->CMD4=%d (legal deltas)\n",groups,bad);
  printf("  illegal-exit regression (LEGAL ref nodes: %d/%d):\n",nlegal,m);
  printf("    ill7->CMD4 (NODE): %d\n",e4);
  printf("    ill7->CMD1 (LEAF): %d\n",e1);
  printf("    ill7->CMD6->CMD4 (BASE): %d\n",e6);
  printf("%s: total mismatches=%d\n", total? "SEQFIX FAIL":"SEQFIX PASS", total);
  delete t; return total?1:0;
}
