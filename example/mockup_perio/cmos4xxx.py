from cyhdl import *

Bool = Signal.Type(bool)
Byte = Signal.Type(intbv()[8:])
from myirl.kernel.sig import ConstSig

@block
def hef4094b(clk: ClkSignal,
	shift : Bool,
	ser : Bool,
	latch : Bool,
	q : Signal.Output,
	qs1 : Bool.Output = None,
	qs2 : Bool.Output = None
	):
	"""
	HEF 4094B-like behavioral model (no STB): latch transfers shift register to outputs.

	Behavior:
	  - On clk.posedge: shift right; new ser bit enters shift_reg[0]
	  - On latch.posedge: q <= shift_reg
	  - Cascade taps (combinational): qs1 = shift_reg[7], qs2 = shift_reg[0]
	  - Optional OE (active-high): if oe=0, q is driven to 0
	"""

	shift_reg = q.clone()
	shift_d, shift_strobe = [ Bool() for _ in range(2) ]
	latch_d, latch_strobe = [ Bool() for _ in range(2) ]

	@always(clk.posedge)
	def sample_inputs():
		shift_d.next = shift
		latch_d.next = latch

	logic = [
		shift_strobe.set(shift & ~shift_d),
		latch_strobe.set(latch & ~latch_d),
	]

	@always(clk.posedge)
	def shift_proc():
		if shift_strobe:
			# shift_reg.next = concat(ser, shift_reg[:1])
			shift_reg.next = concat(shift_reg[-1:], ser)

	@always(clk.posedge)
	def latch_proc():
		if latch_strobe:
			q.next = shift_reg

	if qs1 is not None or qs2 is not None:
		@always_comb
		def cascade_proc():
			if qs1 is not None:
				qs1.next = shift_reg[-1]  # MSB-end tap
			if qs2 is not None:
				qs2.next = shift_reg[0]  # LSB-end tap

	return instances()



@block
def cd4021(
	clk		  : ClkSignal,		  # system clock
	shift	  : Bool,	   # shift input, clk sync
	latch	  : Bool,	   # LATCH (parallel load control)
	p_in	  : Byte,		# 8-bit parallel input bus (P1..P8)
	serial_in : Bool,  # serial input used when shifting (Ds / Serial in)
	q5		  : Bool.Output,
	q6		  : Bool.Output,
	q7		  : Bool.Output # exposed outputs
):
	"""
	CD4021-like model with your pin naming assumption:
	  - latch=1 loads parallel inputs into internal register
	  - latch=0 shifts on rising edge of clk (Q7 shifts out first, as serial output)
	  - only Q5,Q6,Q7 are modeled as outputs

	Internal bit mapping to match your exposed pins:
	  internal r[5] -> q5
	  internal r[6] -> q6
	  internal r[7] -> q7
	"""

	r = Signal(intbv(0)[8:])  # r[7] corresponds to q7

	shift_d, shift_strobe = [ Bool() for _ in range(2) ]

	@always(clk.posedge)
	def sample_inputs():
		shift_d.next = shift

	logic = [
		shift_strobe.set(shift & ~shift_d),
	]


	@always(clk.posedge)
	def shift_or_load():
		if latch: # level sensitive
			r.next = p_in
		elif shift_strobe:
			r.next = concat(r[-1:], serial_in)

	drive_out = [
		q5.wireup ( r[5] ),
		q6.wireup ( r[6] ),
		q7.wireup ( r[7] ),
	]

	return instances()


@hdlmacro
def muxer(ctx, inh, sel, channels, q):
	"Procedurally generated muxer"
	walk = ctx.If(inh == True).Then(
			q.set(0)
		)
	for i in range(2**len(sel)):
		walk = walk.Elif(sel == ConstSig(i, len(sel))).Then(
			q.set(channels[i])
		)

	yield [ walk ]
			


@block
def cd4051b(
	clk : ClkSignal,
	c0 : Signal,
	c1 : Signal,
	c2 : Signal,
	c3 : Signal,
	c4 : Signal,
	c5 : Signal,
	c6 : Signal,
	c7 : Signal,
	q : Signal.Output,
	address : Signal.Type(intbv()[3:]),
	inhibit : Bool
):
	"""
	Clocked behavioral model of an 8-channel CD4051B analog mux.

	Parameters
	----------
	clk:
		System clock.

	channels:
		List of 8 N-bit analog signals.

	q:
		N-bit analog value representing the Z/common terminal.

	address:
		3-bit channel selection.

	inhibit:
		Active-high inhibit.
		0 = mux enabled
		1 = mux disabled

	The mux output is updated on the rising edge of clk.
	"""

	channels = [ c0, c1, c2, c3, c4, c5, c6, c7 ]

	@always(clk.posedge)
	def mux_logic():
		muxer(mux_logic, inhibit, address, channels, q)

	return mux_logic


