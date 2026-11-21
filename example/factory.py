from cyhdl import *

from myirl.kernel.extensions import Undefined
from myirl.blackbox_ext import blackbox_verilog, blackbox_cxxrtl
from cyrite.library.ram import sdpram
from cyrite.library.soc import Reg, BF, RegisterSignal

from .sigtypes import *


from myirl.library.memory import MemArray

from cyrite.simulation.simulator import HDLSimulator

import os
_here = os.path.dirname(__file__)

import intelhex

AnalogPin = Signal.Type(intbv()[10:])


class SDP_w(sdpram.MemPort_W):
	@hdlmacro
	def wireup(self, other, we):
		yield [
			"Write port",
			self.addr.wireup(other.waddr[len(self.addr):]),
			self.idata.wireup(other.din),
			self.we.wireup(we)
		]

class SDP_r(sdpram.MemPort_R):
	@hdlmacro
	def wireup(self, other):
		yield [
			"Read port, address only, data delayed",
			self.addr.wireup(other.raddr[len(self.addr):]),
		]
	


@blackbox_verilog(path_prefix = _here + "/t8051/src")
def core(
	clk : ClkSignal,
	rst : ResetSignal,
	rom_en : Bool.Output,
	rom_addr : Addr16.Output,
	rom_data : Byte,
	ram_rd_en: Bool.Output,
	ram_rd_addr : Addr16.Output,
	ram_rd_data : Byte,
	ram_wr_en : Bool.Output,
	ram_wr_addr : Addr16.Output,
	ram_wr_data : Byte.Output
	):
		"""This is the blackbox wrapper for the external T8051
implementation.
"""

class RomPort:
	@property
	def byte(self):
		return self.dout

class RamPort:
	pass

@blackbox_cxxrtl(path_prefix = _here, templates = "DWIDTH AWIDTH",
	template_header_class = True)
def bb_insn_rom(
	clk : ClkSignal, i : Signal, o : Signal.Output,
	*,
	DWIDTH : int = 8,
	AWIDTH : int = 16):

		"""Instruction rom, 8 or 32 bit
This is inferred as a CXXRTL blackbox only."""

@blackbox_cxxrtl(path_prefix = _here, templates = "AWIDTH",
	template_header_class = True)
def bb_insn_rom4x(
	clk : ClkSignal, i : Signal, o : Word.Output,
	*,
	AWIDTH : int = 16):

		"""Instruction rom, special 4x variant, outputting 4 consecutive
bytes from the given address (can be not-4-boundary)
This is inferred as a CXXRTL blackbox only."""


class Generic8051_Factory(cyrite_factory.Module):
	"""This is the somewhat generic class for a 8051 architecture"""

	SDP_r = SDP_r
	SDP_w = SDP_w


	def __init__(self, target, memory_file):
		super().__init__("gen8051", target)
		ext = memory_file.split('.')[-1]
		if ext.lower() == 'bin':
			self.binary = True
		else:
			self.binary = False
		self.file = memory_file
		self.Undefined = Undefined

		self.rom_data = self.create_rom_image()


		self.extra_files = [ self._prefix + "%s.v" % n for n in self._modules ]
		self.extra_files += self._arch_specific_files

	@container
	class _RomPort(RomPort):
		_inputs = [ 'en', 'addr' ]
		_outputs = [ 'dout' ]
		_other = []

		def __init__(self):
			self.en = Bool()
			self.addr = Addr16()
			self.dout = Byte()


	def create_rom_image(self):
		if self.binary:
			with open(self.file, 'br') as f:
				data = f.read()
				f.close()
			_bin = data
		else:
			data = intelhex.IntelHex(self.file)
			print("PROGRAM: 0x%x .. 0x%x" % (data.minaddr(), data.maxaddr()))
			_bin = data.tobinarray()

		_data = [ intbv(x)[8:] for x in _bin ]

		return _data

	@cyrite_factory.block_component
	def _insn_rom(self, 
		clk : ClkSignal, i : Signal, o : Signal.Output,
		rom : MemArray):

		@always(i)
		def worker():
			o.next = rom[i]

		return worker


	def create_insn_rom(self, clk, i, o, rom = None):
		# Switch instruction ROM between internal and blackbox:
		if issubclass(self.sim_class, HDLSimulator):
			print("DEBUG: Choose internal ROM for HDL")
			return self._insn_rom(clk, i, o, rom)
		else:
			print("DEBUG: Choose black box ROM for HDL, data width %d" % o.size())
			return bb_insn_rom(clk, i[:2], o, AWIDTH = i.size() - 2, DWIDTH = o.size())

class IRamPort:
	pass




@container
class Monitor:
	"Monitor interface for simulation purposes"
	_inputs = [ ]
	_outputs = [ 'sfraddr', 're', 'we', 'data' ]
	_other = []

	def __init__(self, _S):
		self.sfraddr = _S(intbv()[8:])
		self.re = _S(bool())
		self.we = _S(bool())
		self.data = _S(intbv()[8:])

class _Port8051Raw:
	pass


@container(CONTAINER_BULK)
class Port8051Raw(_Port8051Raw):
	def __init__(self):
		self.i = Byte()
		self.o = Byte()


class MyPort(RegisterSignal):
	@hdlmacro
	def compose(self, _output):
		_out = self._sigdict['write']
		for bfn, bf in self._template.members().items():
			if bf.is_set(bf.READONLY):
				self.all_write = False
			else:
				s = getattr(_out, bfn)
				yield [ s.wireup(_output[bf.as_slice()] ) ]

	@hdlmacro
	def wireup(self, other):
		"""Wireup macro that connects port inputs and outputs
`other` can be:
* a tuple (_input, output_)
* or one of the container types below:"""
		# _in = self._sigdict['read']
		if isinstance(other, tuple):
			_input, _output = other
		elif isinstance(other, _Port8051Raw):
			_input, _output = other.i, other.o
		else:
			_input, _output = other.gpio_in, other.gpio_out

		self.all_write = True
		yield [ self.compose(_output) ]
		
		# Need to guard not to return a [ None ]
		if not self.all_write:
			yield [ self.assign(_input) ]



