"""Improved CyHDL T51_MD: 8x8 multiplier + 8-step restoring divider.

Same entity interface as the original VHDL, but NOT a clone.  Differences:

  * Result is stable.  The original 4-bit Cnt wrapped 15 -> 0 and restarted
    shifting on the finished result.  Here Cnt saturates at 8 (done) and the
    result and Div_Rdy then hold for as long as ACC/B stay unchanged.
  * No Old_B register: the latched divisor tmp3 already is the previous B.
  * No ACC = B / ACC < B shortcuts: the iteration handles them (Q = 1, R = 0
    and Q = 0, R = ACC).  Only B = 0 is special: it finishes immediately.
  * No 'started' flag.  Registers have defined power-up values that already
    form a consistent state (inputs 0/0, B = 0 -> OV and Rdy set).
  * Div_Q is wired straight from the working register tmp1 (no copy).
  * Div_OV is just (divisor = 0), derived from the latched divisor.

Behaviour: when ACC or B differs from the value seen at the previous clock
edge, the divider restarts at that edge.  After a restart with B /= 0, Div_Rdy
goes high after 8 further edges; with B = 0, Div_Rdy and Div_OV are high right
after the restart edge.  Div_Q = {remainder, quotient}.  For B = 0, Div_Q is
don't-care (here it shows {0, ACC}).  While Div_Rdy is low, Div_Q shows the
intermediate working value.

Multiplier is unchanged.  Strict-syntax rule: no and / or / not anywhere.
"""
from cyhdl import *

from .cyhdl_work.types import *


@block
def t51_md(
        clk: ClkSignal,
        acc: Byte,
        b: Byte,
        mul_q: Word.Output,       # ASSUMPTION: 16-bit type is called `Word`
        mul_ov: Bool.Output,
        div_q: Word.Output,
        div_ov: Bool.Output,
        div_rdy: Bool.Output):

    "Multiplier (combinational) and restoring divider (clocked)."

    # registers (power-up state: inputs 0/0, divisor 0 -> done, OV)
    old_acc = Signal(intbv(0)[8:])
    tmp1 = Signal(intbv(0)[16:])       # {remainder, quotient} working register
    tmp3 = Signal(intbv(0)[8:])        # latched divisor (= B at last restart)
    cnt = Signal(intbv(8)[4:])         # 0..7 running, 8 = done (saturates)

    # combinational helpers
    tmp1_sh = Signal(intbv(0)[16:])    # tmp1 shifted left, bit 0 = 0
    tmp2 = Signal(intbv(0)[9:])        # {1, tmp1_sh(15:8)} - tmp3
    tmp1_step = Signal(intbv(0)[16:])  # tmp1 after one compare/subtract step
    changed = Signal(bool(0))          # ACC or B differs from last edge

    @always_comb
    def mul_proc():
        mul_q.next = acc * b
        mul_ov.next = (acc * b) > 255

    @always_comb
    def shift_proc():
        tmp1_sh.next = concat(tmp1[15:0], False)

    @always_comb
    def sub_proc():
        tmp2.next = concat(True, tmp1_sh[16:8]) - tmp3

    @always_comb
    def step_proc():
        if tmp2[8]:
            tmp1_step.next = concat(tmp2[8:0], tmp1_sh[8:1], True)
        else:
            tmp1_step.next = tmp1_sh

    @always_comb
    def changed_proc():
        if old_acc != acc:
            changed.next = 1
        elif tmp3 != b:
            changed.next = 1
        else:
            changed.next = 0

    @always_comb
    def out_proc():
        div_q.next = tmp1
        div_rdy.next = cnt[3]
        div_ov.next = tmp3 == 0

    @always(clk.posedge)
    def div_proc():
        old_acc.next = acc
        if changed:
            tmp1.next = concat(intbv(0)[8:], acc)
            tmp3.next = b
            if b == 0:
                cnt.next = 8               # nothing to iterate: done at once
            else:
                cnt.next = 0
        elif cnt < 8:                      # running; at 8 (done) hold result
            tmp1.next = tmp1_step
            cnt.next = cnt + 1

    return (mul_proc, shift_proc, sub_proc, step_proc, changed_proc,
            out_proc, div_proc)
