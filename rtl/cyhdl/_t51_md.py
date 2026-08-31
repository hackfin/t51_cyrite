from cyhdl import *

from cyhdl_work.types import *

@block
def t51_md(
    clk: ClkSignal,
    acc: Byte,
    b: Byte,
    mul_q: Word.Output,
    mul_ov: Bool.Output,
    div_q: Word.Output,
    div_ov: Bool.Output,
    div_rdy: Bool.Output,
):
    old_acc = Byte()
    old_b = Byte()

    # registered state formerly held in variables
    tmp1 = Word()
    cnt = Nibble()

    # combinational intermediates
    mul_tmp = Word()
    tmp2 = Signal(intbv()[9:])
    tmp3 = Byte()

    # next-state signals
    tmp1_next = Word()
    cnt_next = Nibble()
    old_acc_next = Byte()
    old_b_next = Byte()

    div_q_next = Word()
    div_ov_next = Bool()
    div_rdy_next = Bool()

    # ------------------------------------------------------------------
    # multiplier
    # ------------------------------------------------------------------

    @always_comb
    def multiply():
        mul_tmp.next = acc * b
        mul_q.next = mul_tmp
        mul_ov.next = mul_tmp[16:8] != 0

    # ------------------------------------------------------------------
    # combinational division logic
    # ------------------------------------------------------------------

    @always_comb
    def divide_comb():
        tmp3.next = b

        # defaults
        tmp1_next.next = tmp1
        cnt_next.next = cnt
        old_acc_next.next = old_acc
        old_b_next.next = old_b

        div_q_next.next = div_q
        div_ov_next.next = False
        div_rdy_next.next = cnt[3]

        if b == 0:
            div_q_next.next = 0
            div_ov_next.next = True
            div_rdy_next.next = True

        elif acc == b:
            div_q_next.next = 1

        elif acc < b:
            div_q_next.next = concat(acc, 0)
            div_rdy_next.next = True

        elif cnt[3] == False:
            tmp2.next = concat(True, tmp1[8:16]) - concat(False, tmp3)

            tmp1_next.next = concat(
                tmp1[7:16],
                False,
            )

            if tmp2[8]:
                tmp1_next.next = concat(
                    tmp2[0:8],
                    True,
                )

            div_q_next.next = tmp1_next

        # new division operation
        if (old_acc != acc) | (old_b != b):
            tmp1_next.next = concat(False, acc)
            cnt_next.next = 0
            div_rdy_next.next = False
            old_acc_next.next = acc
            old_b_next.next = b

        else:
            cnt_next.next = cnt + 1

    # ------------------------------------------------------------------
    # registers
    # ------------------------------------------------------------------

    @always_seq(clk.posedge)
    def registers():
        old_acc.next = old_acc_next
        old_b.next = old_b_next

        tmp1.next = tmp1_next
        cnt.next = cnt_next

        div_q.next = div_q_next
        div_ov.next = div_ov_next
        div_rdy.next = div_rdy_next

    return instances()
