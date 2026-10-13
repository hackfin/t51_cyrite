from cyhdl import *
from cyrite.auxiliaries.xhdl import vhdlaux as vh

from .types import *

from myirl.library.memory import MemArray

# Imports for 'ssram':

@block
def ssram(
	# signals:
	clk							: Bool,
	ce_n						: Bool,
	we_n						: Bool,
	a							: Signal,
	din							: Signal,
	dout						: Signal.Output,
	):
	"behaviour"

	ADDRWIDTH = a.size()
	DATAWIDTH = din.size()

	SIZE = 2 ** ADDRWIDTH
	ram = MemArray([ intbv(j)[DATAWIDTH:] for j in range(SIZE)])

	a1 = a.clone()
	
	@always(clk.posedge)
	def worker():
		a1.next = a
		if ce_n == False and we_n == False:
			ram[a].next = din

	async_read = [
		dout.set(ram[a1])
	]

	return locals()
