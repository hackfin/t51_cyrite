from cyhdl import *
from cyrite.auxiliaries.xhdl import vhdlaux as vh

from cyhdl_work.types import *

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
	
	ADDRWIDTH					: vh.integer = 11,
	DATAWIDTH					: vh.integer = 8): 
	"behaviour"


	SIZE = 2 ** ADDRWIDTH
	ram = MemArray([ intbv(j)[DATAWIDTH:] for j in range(SIZE)])
	
	@always(clk.posedge)
	def worker():
		if ce_n == False:
			dout.next = ram[a]
			if we_n == False:
				ram[a].next = din


	return locals()
