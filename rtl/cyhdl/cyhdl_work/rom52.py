from cyhdl import *

from myirl.library.memory import MemArray
from .aux_rom import HexROMGenerator


@block
def rom52(
	clk : ( ClkSignal, type(None)),
	a : Signal,
	d : Signal.Output,
	INITDATA : list, USE_HEX = False):

	"""Simple ROM implementation. If clk is None, create an asynchronous ROM"""

	l = 2 ** len(a)
	assert len(INITDATA) == l

	n = d.size()

	# Write a hexfile with the init values:
	
	

	rom = MemArray([ intbv(j)[n:] for j in INITDATA], init = not USE_HEX)

	if isinstance(a, intbv):
		i = a
	else:
		u_index = Signal(intbv()[a.size():])

		wirings = [
			u_index.set(a)
		]

		i = u_index


	if USE_HEX:
		rom_init = HexROMGenerator("/tmp/rom52.hex", rom)
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
