# Wishbone bus structures
#

from cyhdl import *
from myirl.simulation import SimulationError
import myirl


@container
class WishboneBus:
	"""Support for CoSimulation only. Verilog/VHDL will throw errors in some
macros"""
	_inputs = [ 'adr', 'datai', 'seli', 'cyc', 'stb', 'we', 'select_dat' ]
	_outputs = [ 'datao', 'selo', 'ack', 'inta' ]
	_other = [ 'clk', 'rst' ]

	_timeout = 200

	SimulationError = SimulationError

	def __init__(self, ctx = myirl, ADDR_W = 32, DATA_W = 32):
		Select = ctx.Signal.Type(intbv()[4:])
		Bool = ctx.Signal.Type(bool)

		self.clk = ctx.ClkSignal()
		self.adr = ctx.Signal(intbv()[ADDR_W:])
		self.datai = ctx.Signal(intbv()[DATA_W:])
		self.datao = ctx.Signal(intbv()[DATA_W:])
		self.seli, self.selo = [ Select() for _ in range(2) ]
		self.ack, self.cyc, self.stb, self.we = [ Bool() for _ in range(4) ]
		self.inta = Bool()
		self.select_dat = Bool()
		self.rst = ctx.ResetSignal(False, True)
		print("DEBUG TARGET", type(ctx).__mro__)
		self.If = ctx.If
		# Simulation only:
		if hasattr(ctx, "While"):
			self.While = ctx.While
		

	# Simulation auxiliaries:
	@cyrite_method.sequence
	def reset(self, t):
		self.adr.next = 0
		self.datai.next = 0
		self.stb.next = False
		self.we.next = False
		self.cyc.next = False
		self.rst.next = True
		yield delay(t)
		self.rst.next = False
		yield delay(1)


	@cyrite_method.sequence
	def read(self, clk, adr, ACK = False):
		"Co-Simulation only, for the moment"
		yield clk.posedge
		self.adr.next = adr
		self.stb.next = True
		self.we.next = False
		self.cyc.next = True
		yield clk.posedge
		self.stb.next = False
		if ACK:
			timeout = self._timeout
			while self.ack == False:
				timeout -= 1
				if timeout == 0:
					raise self.SimulationError("READ: ACK timeout")
				yield clk.posedge
		self.cyc.next = False
		yield clk.negedge

	@cyrite_method.sequence
	def _write(self, clk, adr, data):
		yield clk.posedge
		self.adr.next = adr
		self.datai.next = data
		self.stb.next = True
		self.we.next = True
		self.cyc.next = True
		yield clk.posedge
		self.stb.next = False
		# self.we.next = False

	@cyrite_method.sequence
	def _ack(self, clk):
		timeout = self._timeout
		while self.ack == False:
			timeout = timeout - 1
			if timeout == 0:
				raise self.SimulationError("WRITE: ACK timeout")
			yield clk.posedge

	
	@cyrite_method.sequence
	def write(self, clk, adr, data, ACK = False):
		yield from self._write(clk, adr, data)
		if ACK:
			yield from self._ack(clk)
		self.cyc.next = False
		yield clk.negedge


	@cyrite_method.function
	def forward(self, other):
		self.stb.next = other.stb
		self.adr.next = other.adr
		self.cyc.next = other.cyc
		self.we.next = other.we
		self.select_dat.next = other.select_dat
		self.seli.next = other.seli
		self.datai.next = other.datai
		other.datao.next = self.datao
		other.ack.next = self.ack

	@cyrite_method.function
	def release(self):
		self.stb.next = False
		self.cyc.next = False
		self.we.next = False

