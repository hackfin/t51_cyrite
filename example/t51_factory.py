# T8051 factory
#
# (c) 2026, section5.se
#

from cyhdl import *
from .sigtypes import *

from t51.rtl.cyhdl.t51 import T51_Base, Monitor
# Enhanced (Testing only):
# from .x51.t51_base import T51_Base
# from .x51.monitor import Monitor
from t51.rtl.cyhdl import cyhdl_work as work
from cyrite.library.counter.counter import Counter

from .factory import MyPort, AnalogPin
from myirl.library.dontcare import Open

from .wishbone import WishboneBus

from .sfr8051_nxp_80c552 import rmap_sfr_8xc552, Device_nxp_8xc552 as Device
from .sfr8051 import SFRBusSimple, SFRMap

from cyrite.library.soc import RegisterSignal

from . import mmr as _mmr
from myirl.library.bulksignals import BulkWrapperSig as Bulk
from cyrite.library.soc import Reg, BF, RegisterSignal

@container
class PipePort:
	_inputs = [ "rx", "busy" ]
	_outputs = [ "en_tx", "en_rx", "tx"]
	_other = []

	def __init__(self, _S):
		Bool = _S.Type(bool)
		Byte = _S.Type(intbv()[8:])
		self.busy = Bool()
		self.en_tx, self.en_rx = Bool(), Bool()	
		self.rx, self.tx = Byte(), Byte()


	@hdlmacro
	def wireup(self, other):
		yield [
			other.busy      .wireup (self.busy),
			other.data_in   .wireup (self.rx),
			self.tx         .wireup (other.data_out),
			self.en_tx      .wireup (other.wr),
			self.en_rx      .wireup (other.rd),
		]

class CherryPickingRegSig(RegisterSignal):

	@hdlmacro
	def wireup(self, other):
		"""Wireup macro that connects port inputs and outputs
`other` can be:
* A MMR port only"""
		# _in = self._sigdict['read']
		_input, _output, _select = other.read, other.write, other.select


		# READONLY ports are assigned to MMR inputs
		# WRITEONLY pins are driven by MMR outputs
		_out = self._sigdict['read']
		_in = self._sigdict['write']
		if self.is_set(self.VOLATILE):
			_sel = self._sigdict['select']
		else:
			_sel = None

		# print("DEBUG PORT CHILDREN", _output.members())
		for bfn, bf in self._template.members().items():
			if bf.is_set(bf.READONLY):
				s = getattr(_out, bfn)
				d = getattr(_input, bfn)
				yield [ d.wireup(s) ]
			else:
				d = getattr(_in, bfn)
				s = getattr(_output, bfn)
				yield [ d.wireup(s) ]

		if not _sel is None:
			print("Wiring select pins", self.identifier, self.select.members(), _select.members())
			# Construct select signal from MMR bulk:
			s = getattr(_select, "%s_sel_w" % self.identifier)
			yield [ _sel.sel_w.wireup(s) ]
			
	


class NXP80C552_SFRDevice(Device, SFRMap):
	"""The 80C552 SFR map description. Implements a basic mockup of the
80C552 sufficient for some I/O"""

	from .perio import i8051port_core
	from .sfrperio import uart as fakeuart, timer

	# Do not mock up the timer by default:
	USE_TIMER_MOCKUP = False
	# Important to use delayed write, otherwise the pipelined t51 will
	# get the Port I/O set/clr via bit commands wrong with the simple
	# gpio core.
	#
	if not hasattr(SFRMap, "DELAYED_WRITE_ADDRESS"):
		raise ValueError("Your cyhdl SoC MMR generator is not up to date")

	DELAYED_WRITE_ADDRESS = True

	SCON_REG = rmap_sfr_8xc552.reg_S1CON

	@hdlmacro
	def genlogic(self, ifl, irq, irq_r, trigger, sel = None):
		if irq_r is None:
			yield [
				irq.set(ifl & trigger)
			]
		else:
			yield [
				self.If(ifl == False).Then(
					irq.set(False)
				).Elif(trigger == False).Then(
					irq.set(~irq_r)
				).Else(
					irq.set(sel)
				)
			]

	@cyrite_factory.block_component
	def mockup_perio(self,
		clk: ClkSignal,
		reset: ResetSignal,
		mmrbus : _mmr.MMRSignal.reverse(),
		pio, 
		# pio : panel.PanelSignals,
	):
		"""Some mockup peripherals that don't need much logic, but don't
make sense as synthesized cores either"""

# ADC part
		adc_running = Bool()
		c = Counter(5, 0)

		@always_seq(clk.posedge, reset)
		def adc_logic():
			if adc_running:
				if c == 28:
					adc_running.next = False
					mmrbus.read.ADCI.next = True
				else:
					c.next = c + 1
			elif mmrbus.select.ADCON_sel_w:
				if mmrbus.write.ADCS:
					adc_running.next = True
					c.reset()
				if mmrbus.write.ADCI == 0:
					mmrbus.read.ADCI.next = False
				
		wiring = [
			mmrbus.read.ADCH.wireup (pio.ain[10:2]),
			mmrbus.read.ADC1.wireup (pio.ain[1]),
			mmrbus.read.ADC0.wireup (pio.ain[0]),
		]
		return instances()

	@cyrite_factory.block_component
	def irq_logic(self,
		clk : ClkSignal,
		reset : ResetSignal,
		irqio : Signal,
		stat : Bulk,   #Those are arbitrary bulk signal inputs
		cfg : Bulk
	): 
		"""Here we collect all peripheral interrupt signals and map
them to a request line"""


		I = [ Bool() for _ in range(len(irqio.int_rq)) ]
		R, W = stat, cfg

		int0_r, int1_r = [ Signal(intbv()[2:]) for _ in range(2) ]

		ext_irq_flag = Bool()

		wirings = [
			irqio.int_rq .wireup (concat(*reversed(I)) ),
			irqio.int_prio .wireup (concat(
				"000",
				"0", W.PAD, W.PS1, W.PS0, W.PT1, W.PX1, W.PT0, W.PX0,
				)
			)
		]

		EA = W.EA

		# Note: 'W' flags are config flags, 'R' flags are event/status flags
		# set by hardware
		# They may have W0C or W1C counterparts in the 'W' section, so
		# don't mix them up!

		# Make sure channel numbers match

		if self.USE_TIMER_MOCKUP:
			timer_logic = [ "Use timer mockup, do not wire timer flags",
				self.genlogic(EA & W.ET0, I[1], None, ext_irq_flag),
			]

			@always_seq(clk.posedge, reset)
			def irq_clear_logic():
				"External timer mockup logic reset"
				if irqio.ext_irq[0] &  ~ext_irq_flag:
					ext_irq_flag.next = True
				elif irqio.irq_ack[1]:
					ext_irq_flag.next = False

		else:
			timer_logic = [
				self.genlogic(EA & W.EX0, I[0], int0_r[1], W.IT0, R.IE0), # Timer
				self.genlogic(EA & W.ET0, I[1], None, R.TF0),
				self.genlogic(EA & W.EX1, I[2], int1_r[1], W.IT1, R.IE1), # Timer
				self.genlogic(EA & W.ET1, I[3], None, R.TF1),
			]

			
		@always(clk.posedge)
		def irq_worker():
			"Here we do the IRQ input to core wiring, in fact"
			# But note we do the ACK wiring elsewhere: TMR01
			# Disabled real timer irqs:

			# Mockup timer
			timer_logic
			self.genlogic(EA & W.ES0, I[4], None, R.RI | R.TI), # UART
			self.genlogic(EA & W.ES1, I[5], None, R.SI), # I2C
			# self.genlogic(EA & W.EAD, I[10], None, R.ADCI), # ADC

		# Remove timer_logic macro from instances, otherwise we will
		# generate connections outside the process
		inst = instances()
		del inst['timer_logic']
		return inst

	def register_peripheral_implementation(self):
		"Register cores with their identifiers (dict keys)"
		return {
			'irqlogic_core' : self.irq_logic,
			'gpio_core' : self.i8051port_core,
			'uart_core' : self.fakeuart.uartio_model,
			'tmr01_core' : self.timer.timer,
			# 'i2c_core' : self.i2c_core.i2c_80c552_master,
			'mockup_perio' : self.mockup_perio,
			# 'mockup_i2c' : self.mockup_i2cpanel,
		}

	def create_irqlogic(self, portid, iface, ci, sfrport):

		regs = {
			'IP0' : ( "IP0", "RW" ),
			'IP1' : ( "IP1", "RW" ),
			'TCON' : ( "TCON", "RW" ),
			'IEN0' : ( "IEN0", "RW" ),
			'IEN1' : ( "IEN1", "RW" ),
			'S0CON' : ( "S0CON", "RW" ),
			'S1CON' : ( "S1CON", "RW" ),
		}

		sfrpart = self.mmr_slice(sfrport, regs)
	
		inst = self.generate_perio_inst('irqlogic_core', {
			**ci,
			'irqio' : iface.portdict[portid][0].port,
			'stat' : sfrpart.read,
			'cfg' : sfrpart.write,
		} )

		inst.rename(portid + '_core')

		return inst


	def create_gpio(self, portid, iface, ci, sfrport):
		"""Create a 8051 port. Retrieves the SFR port I/O by the register
identifier from the register_map dictionary"""
		try:
			px_in = getattr(sfrport.read, portid + '_i')
		except AttributeError as e:
			e.args += ("Faulty Px descriptor in XML, require a readonly port",)
			raise e
		px_out = getattr(sfrport.write, portid)

		inst = self.generate_perio_inst('gpio_core', {
			**ci,
			'pio' : iface.portdict[portid][0].port,
			'px_in' : px_in,
			'px_out' : px_out,
		} )

		inst.rename(portid + '_core')

		return inst

	def create_timer(self, portid, iface, ci, sfrport):
		"Create a basic 8051 combined 0/1 timer"


		regs = {
			"TMOD" : ("TMOD", "RW"),
			"TCON" : ("TCON", "RW"),
			"TH0" : ("TH0", "WO"),
			"TH0_r" : ("TH0_r", "RO"),
			"TH1" : ("TH1", "WO"),
			"TH1_r" : ("TH1_r", "RO"),
			"TL0" : ("TL0", "WO"),
			"TL0_r" : ("TL0_r", "RO"),
			"TL1" : ("TL1", "WO"),
			"TL1_r" : ("TL1_r", "RO"),
		}

		sfrpart = self.mmr_slice(sfrport, regs)

		inst = self.generate_perio_inst('tmr01_core', {
			**ci,
			'sfr' : sfrpart,
			'pio' : iface.portdict[portid][0].port,
		} )

		return inst

	def create_uart(self, portid, iface, ci, sfrport):
		i = portid[-1]
		uartio = iface.portdict[portid][0].port

		# We need to slice the relevant part out of the SFR signal
		# in order to avoid driver collisions within the hierarchy

		regs = {
			'cfg'     : ( "S0CON", "RW" ),
			'buf_in'  : ( "S0BUF_r", "RO" ),
			'buf_out' : ( "S0BUF", "WO" ),
		}

		sfrpart = self.mmr_slice(sfrport, regs)

		inst = self.generate_perio_inst('uart_core', {
			**ci,
			'uartio' : uartio,
			'sfr' : sfrpart,
		} )

		inst.rename(portid + '_core')

		return inst

	def create_mockup(self, portid, iface, ci, sfrport):
		port = iface.portdict[portid][0].port

		regs = {
			'ADCH'     : ( "ADCH", "RO" ),
			'ADCON'    : ( "ADCON", "RW" ),
		}

		sfrpart = self.mmr_slice(sfrport, regs)

		inst = self.generate_perio_inst('mockup_perio', {
				**ci,
				'pio'      : port,
				'mmrbus'   : sfrpart,
			}
		)

		inst.rename(portid + '_core')
		return inst


class T51_SoC(T51_Base):
	# The SoC setup with a generated SFR map option
	USE_HEXFILE = True

	# Here we import a HDL ROM implementation. Its content
	# is created on the fly, see also USE_HEXFILE
	from t51.rtl.cyhdl.cyhdl_work.rom52 import rom52

	# Enable to use the external timer mockup pin
	BIDIR, IN, OUT = range(3)

	PINMAP = {

		'p0' : [
			( 'AD0', BIDIR),
			( 'AD1', BIDIR),
			( 'AD2', BIDIR),
			( 'AD3', BIDIR),
			( 'AD4', BIDIR),
			( 'AD5', BIDIR),
			( 'AD6', BIDIR),
			( 'AD7', BIDIR),
		],

		'p1' : [
			( 'P10', OUT),
			( 'P11', BIDIR),
			( 'P12', OUT),
			( 'P13', OUT),
			( 'P14', OUT),
			( 'P15', IN),
			( 'P16', BIDIR),
			( 'P17', BIDIR),
		],


		'p2' : [
			( 'A8', OUT),
			( 'A9', OUT),
			( 'A10', OUT),
			( 'A11', OUT),
			( 'A12', OUT),
			( 'A13', OUT),
			( 'A14', OUT),
			( 'A15', OUT),
		],

		'p3' : [
			( 'RXD', IN),
			( 'TXD', OUT),
			( 'DISP_INT', IN),
			( 'A16', OUT),
			( 'A18', OUT),
			( 'A17', OUT),
			( 'WR', OUT),
			( 'RD', OUT),
		],

		'p4' : [
			( 'P40', OUT),
			( 'P41', OUT),
			( 'P42', OUT),
			( 'P43', OUT),
			( 'P44', OUT),
			( 'P45', OUT),
			( 'P46', OUT),
			( 'P47', OUT),
		],

	}

	NUMPORTS = 5

	regmap = lambda MAP, name : [ BF(x[0], i, i, flags = x[1]) \
		for i, x in enumerate(MAP[name]) ]

	class PortSpec(Reg):
		pass

	Reg_p0 = PortSpec(8, regmap(PINMAP, 'p0'))
	Reg_p1 = PortSpec(8, regmap(PINMAP, 'p1'))
	Reg_p2 = PortSpec(8, regmap(PINMAP, 'p2'))
	Reg_p3 = PortSpec(8, regmap(PINMAP, 'p3'))
	Reg_p4 = PortSpec(8, regmap(PINMAP, 'p4'))


	def __init__(self, name, target, binary):
		# Get the SFR map description:
		super().__init__(name, target)
		self._sfrdevice = NXP80C552_SFRDevice(self.architecture, rmap_sfr_8xc552)
		self.firmware = binary

	@cyrite_factory.block_component
	def soc_t8052NG(self,
		clk : ClkSignal, reset : ResetSignal,
		p0 : MyPort, p1 : MyPort, p2 : MyPort,
		p3 : MyPort, p4: MyPort,
		analog_in       : AnalogPin,
		pipeio          : PipePort,
		xram_en         : Bool,
		xram            : WishboneBus.reverse(),
		ROMADDRESSWIDTH : int = 16,
		XRAMADDRESSWIDTH : int = 16,
	):
		"""Generated map via mmr_perio"""

		# RAM signals
		ram_rdata = Byte()
		ram_do = Byte()
		ram_wdata = Byte()
		ram_access = Bool()
		ram_addr = Addr16()
		ram_addr_r = Addr16()
		ram_rd, ram_wr = [ Bool() for _ in range(2) ]
		ram_rd = Bool()

		ext_ram_en = xram_en

		mux_sel = Bool()
		mux_sel_r = Bool()

		# Instance a SFR bus:
		sfr = SFRBusSimple()

		# io_addr_r = Signal(intbv()[6+1:0])

		# Create an instance so we automatically include its elaborated
		# objects:
		lib = self._sfrdevice
		
		#
		# Generate peripherals
		sfr_inst, sfr_interface = self._sfrdevice.generate_mmr_perio(
			clk = clk,
			reset = reset,
			ce = True,
			bus = sfr
		)

		# And wire them up
		mpio = sfr_interface['MOCK_PERIO']

		wirings = [
			mpio.ain .wireup (analog_in),
			p0.wireup(sfr_interface['P0']),
			p1.wireup(sfr_interface['P1']),
			p2.wireup(sfr_interface['P2']),
			p3.wireup(sfr_interface['P3']),
			p4.wireup(sfr_interface['P4']),
		]

		uart = sfr_interface['SER0']
		irqio = sfr_interface['IRQ']
		tmr = sfr_interface['TMR01']

		int_acc = irqio.int_rq.clone()

		# UART wirings:
		wirings += [
			pipeio     .wireup (uart),
		]

		if lib.USE_TIMER_MOCKUP:
			wirings += [
				irqio.irq_ack .wireup (int_acc),
			]
		else: # For the real timer
			wirings += [
				tmr.int_ack   .wireup (concat(int_acc[3], int_acc[1])),
			]

		# Async selection logic:
		@always(xram.ack, ext_ram_en, ram_access)
		def select_ready():    
			# ternary:		  
			if (xram.ack == False)  &  ((ext_ram_en & ram_access) == True): 
				ready.next = False
			else:
				ready.next = True

		@always_seq(clk.posedge, reset)
		def mux_sel_delay():	
			# io_addr_r.next = io_addr
			if ready  ==  True:			   
				ram_addr_r.next = ram_addr
			mux_sel_r.next = mux_sel

		@always(ram_rd, ram_wr)
		def select_ram_access():	
			# ternary:		  
			if (ram_rd | ram_wr)  ==  True:		   
				ram_access.next = True
			else:
				ram_access.next = False

		@always(ram_do, mux_sel_r, xram.datao)
		def select_ram_read():	  
			# ternary:		  
			if mux_sel_r  ==  False:		
				ram_rdata.next = ram_do
			else:
				ram_rdata.next = xram.datao


############################################################################	# ROM INSTANCE
		rom_addr = Addr16()
		rom_data = Byte()

		if self.firmware is None:
			raise ValueError("Firmware argument must be given")

		with open(self.firmware, "rb") as f:
			ROM_DATA = f.read()
			f.close()
		
		 # instance 'rom52'
		rom = self.rom52(
			clk = clk,
			a = rom_addr,
			d = rom_data,
			INITDATA = ROM_DATA,
			HEXFILE = "output/rom52.hex" if self.USE_HEXFILE else None
		)

		# Need separate signal due to autocasting not working
		# for expressions

		# The external Static RAM
		ram = work.ssram(
			clk = clk,
			ce_n = ext_ram_en,
			we_n = ~ram_wr,
			a = xram.adr[XRAMADDRESSWIDTH:0],
			din = ram_wdata,
			dout = ram_do
		)

		ram_cycle = Bool()
		iram_wr = Bool()
		iram_addr = Byte()
		iram_wdata = Byte()
		ready = Bool()


############################################################################

		# Special flag for port core to select actual data
		# being read. Used for bit clr/set.

		# Dummy monitor, currently not exposed
		
		 # instance 't51'
		core51 = self.t51(
			clk            = clk,
			rst_n          = reset,
			ready          = ready,
			rom_addr       = rom_addr,
			rom_data       = rom_data,
			ram_addr       = ram_addr,
			ram_rdata      = ram_rdata,
			ram_wdata      = ram_wdata,
			ram_rd         = ram_rd,
			ram_wr         = ram_wr,
			ram_cycle      = ram_cycle,
			int_trig       = irqio.int_rq, # Interrupt request line
			int_prio       = irqio.int_prio, # Custom IRQ priority
			int_acc        = int_acc,
			sfr_rd_rmw     = sfr.rmw, # I/O port read selector
			sfr_wr         = sfr.we,
			sfr_addr       = sfr.addr,
			sfr_wdata      = sfr.idata,
			sfr_rdata_in   = sfr.odata,
			# These are actually unused here
			iram_wr        = iram_wr,
			iram_addr      = iram_addr,
			iram_wdata     = iram_wdata,
			mon            = None,

			DUALBUS = True,
			RAMADDRESSWIDTH = 8,
		)

		stb = ext_ram_en & ram_access

		# BUS and SFR wirings:
		bus_wiring = [
			sfr.re.wireup(~sfr.we),

			# Wishbone bus signals:
			xram.adr        @assign@       ( ram_addr_r  ),
			xram.datai      @assign@       ( ram_wdata  ),
			xram.cyc        @assign@       ( stb  ),
			xram.stb        @assign@       ( stb  ),
			xram.we         @assign@       ( ram_wr  ),
			# XRAM/RAM selector
			mux_sel         @assign@       ( ext_ram_en  ),
		]

		return instances()

