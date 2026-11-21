
from cyhdl import *
import myirl

from myirl.composite import Composite
from cyrite.examples.libprimitives import delayed

Bool = Signal.Type(bool)



class derived_strobe(Composite):
	_signed = False

	def __init__(self, clk, sig, RISING = True):
		self.q = sig.clone()
		self.clk = clk

		s1 = sig.clone()

		@myirl.genprocess(clk, EDGE=clk.POS)
		def worker():
			yield [
				s1.set(sig)
			]
		
		if RISING:
			logic = [ self.q.set(sig & ~s1) ]
		else:
			logic = [ self.q.set(~sig & s1) ]

		super().__init__([logic, worker])

	def get(self):
		return self.q

	def get_sources(self, sigs):
		s = self.clk
		sigs[s.identifier] = s
		
	def get_drivers(self, sigs):
		s = self.q
		sigs[s.identifier] = s

class SPIFactory:
	"""SPI slave auxiliaries"""
	derived_strobe = derived_strobe
	delayed = delayed

	@cyrite_factory.block_component
	def spi_slave(self,
		clk : ClkSignal,
		sck  : Bool,
		cs   : Bool,
		si   : Bool,
		so   : Bool.Output, 
		din  : Signal,
		dout : Signal.Output,
		store : Bool.Output,
		N = 8,
		MSBFIRST = True):
		sr = Signal(intbv(0)[N:])
		# c = Counter(3, 0)
		c = Signal(intbv()[3:])

		# We might get rid of the `clk` master clock for
		# more speed. See derived versions of this class.

		ce_high = self.derived_strobe(clk, sck)

		ce_low = self.derived_strobe(clk, sck, RISING = False)

		rx_complete, load_en = [ Bool() for _ in range(2) ]

		load = delayed(clk, True, rx_complete, DEPTH = 3)

		reset = ResetSignal(True, True, isasync = True)

		if MSBFIRST:
			shifted = concat(sr[N-1:], si)
			shiftout = sr[-1]
		else:
			shifted = concat(si, sr[:1])
			shiftout = sr[0]

		@always(clk.posedge)
		def worker():
			if reset == True:
				c.next = 0
				rx_complete.next = False
			elif ce_high == True:
				sr.next = shifted

				if c == N-1:
					c.next = 0
					rx_complete.next = True
				else:
					c.next = c + 1
			elif load == True:
				sr.next = din
			else:
				rx_complete.next = False

		@always(clk.posedge)
		def so_buffer():
			if ce_low == True:
				so.next = shiftout

		wires = [
			reset.wireup(cs),
			dout.wireup(sr),
			store.wireup(rx_complete),
		]

		return instances()


