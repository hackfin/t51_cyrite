# Internal T51 RAM
#
# (c) 2026, section5.se

from cyhdl import *

from .types import *

from myirl.library.memory import MemArray

@block
def t51_ram(
	clk         : ClkSignal,
	rst_n       : ResetSignal,
	are         : Bool,
	wr          : Bool,
	din         : Byte,
	int_addra   : Byte,
	int_addra_r : Byte.Output,
	int_addrb   : Byte,
	mem_a       : Byte.Output,
	mem_b       : Byte.Output,
	INIT = True
):
	"""T51 internal RAM. We use a rather generic model here for simulation
only"""
	int_addra_r_i = int_addra_r.clone()

	wirings = [
		int_addra_r  .wireup  (int_addra_r_i)
	]

	n = 2 ** int_addra.size()

	rambuf_a, rambuf_b = [
		MemArray( [intbv()[8:] for _ in range(n) ], init = INIT ) for _ in range(2)
	]


	@always(clk.posedge)
	def worker():
		if are:
			mem_a.next = rambuf_a[int_addra]
			mem_b.next = rambuf_b[int_addrb]

		if wr:
			rambuf_a[int_addra_r_i].next = din
			rambuf_b[int_addra_r_i].next = din

			if int_addra_r_i == int_addra:
				mem_a.next = din
			if int_addra_r_i == int_addrb:
				mem_b.next = din

		int_addra_r_i.next = int_addra
				
	return locals()
