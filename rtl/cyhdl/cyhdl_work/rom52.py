from cyhdl import *

from myirl.library.memory import MemArray


@block
def rom52(
	clk : ( ClkSignal, type(None)),
	i : Signal,
	o : Signal.Output,
	INITDATA : list):

	"""Simple ROM implementation. If clk is None, create an asynchronous ROM"""

	l = 2 ** len(i)
	assert len(INITDATA) == l

	n = o.size()

	rom = MemArray([ intbv(j)[n:] for j in INITDATA], init = True)

	if clk is None:
		@always_comb
		def worker():
			o.next = rom[i]
	else:
		@always(clk.posedge)
		def worker():
			o.next = rom[i]

	return locals()
