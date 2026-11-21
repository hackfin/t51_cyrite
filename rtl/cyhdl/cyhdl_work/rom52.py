from cyhdl import *

from myirl.library.memory import MemArray
from .aux_rom import HexROMGenerator


@block
def rom52(
	clk : ( ClkSignal, type(None)),
	a : Signal,
	d : Signal.Output,
	INITDATA : list, HEXFILE = None):

	"""Simple ROM implementation. If clk is None, create an asynchronous ROM"""

	l = 2 ** len(a)
	assert len(INITDATA) == l

	n = d.size()

	# Write a hexfile with the init values:
	
	rom = MemArray([ intbv(j)[n:] for j in INITDATA], init = HEXFILE is None)

	if isinstance(a, intbv):
		i = a
	else:
		u_index = Signal(intbv()[a.size():])

		wirings = [
			u_index.set(a)
		]

		i = u_index


	if not HEXFILE is None:
		rom_init = HexROMGenerator(HEXFILE, rom)
		rom_init.emit(INITDATA)

	if clk is None:
		@always_comb
		def worker():
			d.next = rom[i]
	else:
		@always(clk.posedge)
		def worker():
			d.next = rom[i]

	return locals()
