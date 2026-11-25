# SFR I/O memory mapped register wrapper for 8051 architectures
#
#
# (c) 2025, section5.se
#
from cyhdl import *
from . import mmr
from myirl.kernel import sensitivity

Bool = Signal.Type(bool)
Byte = Signal.Type(intbv()[8:])

class sfrio(mmr.IOPortType):
	_inputs = [ 'gin' ]
	_outputs = [ 'gout' ]
	_other = []

	def __init__(self, Signal = Signal):
		self.gin = Bool()
		self.gout = Bool()

@container()
class SFRBus:
	def __init__(self, ram):
		# self._ram = ram
		self.waddr = Signal(intbv()[7:])
		self.raddr = Signal(intbv()[7:])
		self.idata = ram.din.clone()
		self.odata = ram.dout.clone()
		self.we = Bool()
		self.re = Bool()

	@hdlmacro
	def wireup(self, other):
		yield [
			self.waddr.wireup(other.waddr[7:]),
			self.raddr.wireup(other.raddr[7:]),
			self.idata.wireup(other.din),
			self.we.wireup(other.wren_sfr),
			self.re.wireup(other.rden_sfr),
		]

@container()
class SFRBusSimple:
	def __init__(self):
		# self._ram = ram
		self.addr = Signal(intbv()[7:])
		self.idata = Byte()
		self.odata = Byte()
		self.we = Bool()
		self.re = Bool()
		self.rmw = Bool() # Read mode
		self.int0 = Bool() # interrupt pins
		self.int1 = Bool()

	@hdlmacro
	def wireup(self, other):
		yield [
			self.addr.wireup(other.addr[7:]),
			self.idata.wireup(other.din),
			self.we.wireup(other.wren_sfr),
			self.re.wireup(other.rden_sfr),
		]
	

class _NewSFR(mmr.MMRSignal):
	pass



class MMRSlice(mmr.MMRSignal):
	"Create a subset of this MMR signal with a different mapping"

	def __init__(self, name, other, mapping):

		inputs, outputs, select_sigs = self.populate(mapping)

		input_container  = self.create(name, 'read',
			self.link_signals(other.read, inputs), ())
		output_container = self.create(name, 'write',
			self.link_signals(other.write, outputs), ())
		select_container = self.create(name, 'sel',
			self.link_signals(other.select, select_sigs.items()), ())

		sigs = { }

		if input_container is not None:
			sigs['read'] = input_container

		if output_container is not None:
			output_container._output = True
			output_container._aux = False
			sigs['write'] = output_container

		if select_container is not None:
			select_container._aux = True # Always input
			sigs['select'] = select_container

		super().__init__(name, sigs, template = mapping, virtual = False)

	def link_signals(self, other, sigdesc):
		"Link signals to other"

		d = {}

		for n, _ in sigdesc:
			d[n] = getattr(other, n)


		return d

	def alias(self, name):
		signals = {}
		# Walk the bulk I/O members:
		for n, s in self._members.items():
			nn = name + '_' + n
			sig = s.alias(nn)
			signals[n] = sig
		# Use the __new__ method to bypass __init__
		cls = type(self)
		clone = cls.__new__(cls)

		mmr.MMRSignal.__init__(clone, name, signals,
			template = self._template, virtual = True)

		return clone

class Lookup:
	def __init__(self, rmap):
		for k, i in rmap.items():
			setattr(self, i[0], k[0])

	def iterate(self):
		for k, i in self.__dict__.items():
			yield k, i

class ExtendedDeviceClass(mmr.DeviceClass):
	"""Here we add our grainy bit access SFR extension"""
	MMRSignal = _NewSFR # Override

class SFRMap(ExtendedDeviceClass):
	"""The Special function register map class contains the I/O architecture
for a particular 8051 derivative. Normally, you would inherit from it and
add your own implementations."""

	READ_ASYNC = True # Do not change this, it's core specific
	_debug_ = True

	USE_TIMER_MOCKUP = True

	def __init__(self, arch, rmap_sfr):

		super().__init__("sfr8051", arch)

		self.instances = {
			'sfr' : [ rmap_sfr, sfrio, 1, 8, {} ]
		}


		# Inverse table to lookup register symbols
		self.lookup = { (i[0], k[1]) : (i[1], k) for k, i in rmap_sfr.register_map.items() }
	
		# Here we define the device/peripheral architecture.
		# Each peripheral instances has an identifier, a method
		# to create it and a I/O port that is allocated in the top level
		# interface.

		# A logic gen either returns one instance or a tuple of several
		# instances. It is normally implemented by the derived class,
		# and calls .generate_perio_inst() to create a "slot" for the device
		# under a specific identifier. Using this identifier, the deriving
		# device registers the actual peripheral cores using
		# .register_peripheral_implementation()

		self.device_architecture = {
			# ID             logic_gen              port def
			'IRQ'        : ( self.create_irqlogic,  self.irq  ),
			'P0'         : ( self.create_gpio,      self.gpio  ),
			'P1'         : ( self.create_gpio,      self.gpio  ),
			'P2'         : ( self.create_gpio,      self.gpio  ),
			'P3'         : ( self.create_gpio,      self.gpio  ),
			'P4'         : ( self.create_gpio,      self.gpio  ),
			'SER0'       : ( self.create_uart,      self.uart ),
			'MOCK_PERIO' : ( self.create_mockup,    self.analog_io ),
		}

		if not self.USE_TIMER_MOCKUP:
			self.device_architecture['TMR01'] = \
				( self.create_timer,     self.timer.TimerSignals)

		#
		# Peripheral architecture:
		self.config = {
			'IRQ' : {'size' : 11}
		}

	@container(mmr.IOPortType)
	class irq:
		"The signal port class for the IRQ logic"
		_inputs = [ 'ext_irq', 'irq_ack' ]
		_outputs = ['int_rq', 'int_prio']
		_other = []
		
		def __init__(self, size, Signal = Signal):
			# self.ie = Signal(bool())
			# interrupt acknowledge is custom-wired:
			# External aux interrupts
			self.ext_irq = Signal(intbv()[4:])


			self.irq_ack = Signal(intbv()[size:])

			self.int_rq = Signal(intbv()[size:])
			self.int_prio = Signal(intbv()[size:])

	@container(mmr.IOPortType)
	class gpio:
		"The signal port class for the GPIO unit"
		_inputs = ['gpio_in',]
		_outputs = ['gpio_out','gpio_dir',]
		_other = []
		
		def __init__(self, Signal = Signal):
			self.gpio_in = Signal(intbv()[7+1:0])
			self.gpio_out = Signal(intbv()[7+1:0])
			self.gpio_dir = Signal(intbv()[7+1:0])

	@container(mmr.IOPortType)
	class uart:
		"The signal port class for the UART unit"
		_inputs = ['data_in', 'ready', 'busy']
		_outputs = ['data_out','wr', 'rd']
		_other = []
		
		def __init__(self, Signal = Signal):
			self.data_in = Signal(intbv()[7+1:0])
			self.data_out = Signal(intbv()[7+1:0])
			self.ready = Bool()
			self.busy = Bool()
			self.wr = Bool()
			self.rd = Bool()

	@container(mmr.IOPortType)
	class analog_io:
		_inputs = ['ain']
		_outputs = [ ]
		_other = []

		def __init__(self):
			self.ain = Signal(intbv()[10:])

	@container(mmr.IOPortType)
	class i2cio:
		_inputs = ['sdai', 'scli']
		_outputs = ['sdao', 'sclo']
		_other = []

		def __init__(self):
			self.scli = Bool()
			self.sdai = Bool()
			self.sclo = Bool()
			self.sdao = Bool()

	@container(mmr.IOPortType)
	class emu:
		_inputs = ['lcd7',]
		_outputs = []
		_other = []
		
		def __init__(self, Signal = Signal):
			self.lcd7 = Signal(bool())

############################################################################	
# Auxiliaries

	def mmr_slice(self, sfr, registers):
		"""Slice the entire SFR MMR port into a particular port only containing
the signals relevant to the given registers"""

		from myirl.kernel._types import CustomSignal
		new_map = {}

		for n, access in registers.values():
			record = self.lookup[(n, access)]
			new_map[record[1]] = (n, record[0])

		sl = MMRSlice("mmrslice", sfr, new_map)

		return sl


	def generate_toplevel_interface(self):
		"""Here we define the top level I/O port map. We refer to their
identifiers in the `plugins` method below"""
		interface = {}
		for k, i in self.device_architecture.items():
			if k in self.config:
				kwargs = self.config[k]
			else:
				kwargs = {}

			interface[k] = i[1](**kwargs)

		return interface

	def plugins(self, clk, reset, ce, bus, mmr, interface):
		"""This handles the plugged in peripheral I/O (perio) cores.
For each SFR map, these need to be customized.
The logic generators are passed several interfaces, last the memory register
I/O port which is constructed internally from the register_map definition
in the device specific sfr8051_<arch>.py module,
"""

		c = self.get_instance("mmr_perio")

		# Each core has at least these signals in the interface:
		common_interface = {
			'clk' : clk,
			'reset' : reset, # 'ce' : ce, 
			'io_rd' : bus.rmw
		}

		instances = []

		for k, i in self.device_architecture.items():
			# Call logic generator
			inst = i[0](k, c.interface, common_interface, mmr)
			if isinstance(inst, tuple):
				instances += inst
			else:
				instances.append(inst)

		return instances


############################################################################
	@block_component
	def mmr_perio(self,
		clk : ClkSignal,
		reset : ResetSignal,
		ce	: Bool,
		bus,
		**interface
	):
		"SFR specific (overriden) peripheral I/O module"

		# SFR uses a simple flat mapping. Therefore we need no
		# complicated mmr_decoder structure

		class T:
			ClkSignal = ClkSignal
			Signal = Signal
			ResetSignal = ResetSignal

		sfr_addr = self.Signal(intbv()[7:])

		_g = self.instances['sfr'][0]
		generator = _g('sfr', self.architecture, addr_shift = 0)

		_mmr = mmr.MMRSignal('sfr_t', template = generator.register_map)

		# _mmr.dump_children()

		_interface = { 'mmr' :_mmr }

		inst_dec = self.mmr_decode(generator,
			clk = clk,
			reset = reset,
			ce = ce,
			we = bus.we,
			re = bus.re,
			addr = sfr_addr,
			data_in = bus.idata,
			data_out = bus.odata,
			REGDESC = generator.register_map,
			**_interface
		)

		# Fixme: SFR should only have one address. We don't need dual port..
		if hasattr(bus, 'addr'):
			sfr_wires = [
				sfr_addr.wireup(bus.addr)
			]
		else:
			@sensitivity.process(bus.we, bus.re)
			def mux_sfraddr(logic):
				logic += [
					logic.If(bus.we).Then(
						sfr_addr.set(bus.waddr)
					).Else(
						sfr_addr.set(bus.raddr)
					)
				]
		
		inst = self.plugins(clk, reset, ce, bus, _mmr, interface)

		return instances()
