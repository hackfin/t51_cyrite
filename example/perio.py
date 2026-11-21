# Peripheral I/O for dummy 8051
#
# Some of them are fake, some of them actually work.
# However, we don't do any extensive verification of them.
#

from cyhdl import *
from cyrite.auxiliaries.xhdl import vhdlaux as vh

from myirl.lists import SigArray
from myirl.targets.verilog import Verilog
from myirl.emulation.process import LoopSupportMixin
from myirl.library.tristate import *
from myirl.kernel.loops import range_, Iterator, LoopGen, For
from myirl.kernel import sig as base
from myirl.kernel._types import SignalSlice

from .mmr import MMRSignal, IOPortType

Bool = Signal.Type(bool)

# Imports for 'gpio_core':
# from system_map import *
class _SigArray(SigArray):
	sigclass = Verilog.WIRE

class BulkSelect(TristateSignal, LoopSupportMixin):
	"""Bulk style tri-state where each bit determines the direction"""

	def __init__(self, *args):
		super().__init__(*args)
		self.initialize()

	def __getitem__(self, sl):
		if isinstance(sl, base.Var):
			return SignalSlice(self, sl)

	@hdlmacro
	def select(self, data_a, data_b, sel):
		sa = _SigArray([ bool(0) for _ in range(data_a.size())])

		yield [
			self.For(i = range_(data_a.size()))(
				sa[self.lref('i')].set(
					TernaryIf(
						(sel[self.lref('i')] == True),
						data_a[self.lref('i')],
						data_b[self.lref('i')],
					)
				)
			)
		]
		yield [
			self.set(concat(*reversed(sa)))
		]


@block
def i8051port_core(
	# signals:
	clk : ClkSignal,
	reset : ResetSignal,
	pio,
	px_in : Signal.Output,
	px_out : Signal,
	io_rd : Bool
	): 
	"""The simple 8051 port is just a push I/O. However, it has a quirk:
The `io_rd` line selects whether the actually set output or the real input
pad is read. This is required for the bit set/clear feature"""


	# Ports are high (Z) by default
	# This is encoded in the <default> field of the register in the
	# XML description


	@always(px_out, pio.gpio_in, io_rd)
	def select_io():
		if io_rd:
			px_in.next = px_out
		else:
			px_in.next = pio.gpio_in

#	@always_seq(clk.posedge)
#	def trigger_wr():
#		if px_selw:
#			data.next = px_out

	###### Wirings: ######
	_wires_ = [
		pio.gpio_out.wireup(px_out),
	]



	return locals()


@block
def gpio_core(
	# signals:
	clk : ClkSignal,
	reset : ResetSignal,
	pio,
	px_out : Signal,
	px_in : Signal.Output,
	px_dir : Signal,
	): 
	"This one uses direction control with tristate, in fact."

	# Types

	# Const

	# Signals

	N = len(pio.gpio_dir)

	gpio_in = pio.gpio_in
	gpio_out = pio.gpio_out
	gpio_dir = pio.gpio_dir

	r = BulkSelect(N * 'Z')
	
	_logic = [
		r.select(gpio_in, gpio_out, gpio_dir)
	]
		
	###### Wirings: ######
	_wires_ = [
		# stat.GPIO_OUT				 @assign@ ( gpio_value ),
		px_in                        @assign@ ( r ),
		gpio_dir					 @assign@ ( px_dir ),
		gpio_out					 @assign@ ( px_out ),
	]


	return locals()

Bool = Signal.Type(bool)
Byte = Signal.Type(intbv()[8:])

@block
def emulation(
	# signals:
	clk : ClkSignal,
	reset : ResetSignal,
	lcd7 : Bool.Output,
	spicon : Byte,
	select_con : Bool
):

	counter = Signal(intbv()[8:])
	state = Bool(0)
	
	@always_seq(clk.posedge, reset)
	def worker():
		if state == False:
			if select_con:
				counter.next = 4
				state.next = True
				lcd7.next = False
		else:
			counter.next = counter - 1
			if counter == 0:
				state.next = False
				lcd7.next = True

	return instances()
