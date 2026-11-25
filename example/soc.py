"""System on chip factory for T51

"""

from cyhdl import *
from t51.example.t51_factory import T51_SoC, Monitor, PipePort
from t51.example.mockup_perio.spi import SPIFactory
from t51.example.factory import MyPort, Bool, Port8051Raw
from t51.example.wishbone import WishboneBus
from myirl.targets import common
from myirl.library.dontcare import Open

from mockup_perio.cmos4xxx import hef4094b, cd4021, cd4051b
import time

from cyrite.simulation.simulator import CoSimulator

@container
class AnalogInputs:
	_inputs = [
		"extctrl",
		"gt5",
		"gt4",
		"gt11",
		"gt3x",
		"gt1",
		"gt2",
		"lp",
		"hp",
		"service",
		"gt10",
		"gt8",
		"gt6",
		"gt3",
		"vvp",
		"gt9"
	]
	_outputs = []
	_other = []

	def __init__(self, ctx):
		self.extctrl, \
		self.gt5, \
		self.gt4, \
		self.gt11, \
		self.gt3x, \
		self.gt1, \
		self.gt2, \
		self.lp, \
		self.hp, \
		self.service, \
		self.gt10, \
		self.gt8, \
		self.gt6, \
		self.gt3, \
		self.vvp, \
		self.gt9 = [ ctx.Signal(intbv()[10:]) for _ in range(16) ]




class MyPlatform(T51_SoC, SPIFactory):
	BIDIR, IN, OUT = range(3)


	PINMAP = {
		'p1' : [
			( 'P1.0_UNUSED', OUT),
			( 'RTC_IO', BIDIR),
			( 'P1.2_UNUSED', OUT),
			( 'RTC_SR_CLK', OUT),
			( 'SRO_DAT', OUT),
			( 'SRI_DAT', IN),
			( 'I2C_SCL', BIDIR),
			( 'I2C_SDA', BIDIR),
		],

		'p4' : [
			( 'FLASH_CS', OUT),
			( 'RTC_CS', OUT),
			( 'RAM_CS', OUT),
			( 'P4.3_UNUSED', OUT),
			( 'SRO_LAT', OUT),
			( 'SRI_LAT', OUT),
			( 'P4.6_UNUSED', OUT),
			( 'SRI_CLK', OUT),
		],


		'sr_4021' : [
			( 'unused0' , IN ), # D0
			( 'PIN4' , IN ),
			( 'PIN5' , IN ),
			( 'PIN6' , IN ),
			( 'PIN13' , IN ),  # Phase L3
			( 'PIN11' , IN ),  # Phase L2
			( 'PIN9' , IN ),   # Phase L1
			( 'unused1' , IN ), # D7
		],

		# 4094 output mapping
		'sr_4094' : [
			( 's1' , OUT),
			( 's2' , OUT),
			( 'EL3' , OUT),
			( 'P1' , OUT),
			( 'VXV' , OUT),
			( 'P2' , OUT),
			( 'COMP' , OUT),
			( 'P3' , OUT),

			( 'A_SEL0' , OUT),
			( 'A_SEL1' , OUT),
			( 'A_SEL2' , OUT),
			( 'A_INH' , OUT),
			( 'LARM_RELAY' , OUT),
			( 'EL6' , OUT),
			( 'LED_RED' , OUT), # alarm
			( 'LOW' , OUT), # What is this one for?

		]
	}

	PortSpec = T51_SoC.PortSpec

	# Override definition with our pin wiring:
	Reg_p1 = PortSpec(8, T51_SoC.regmap(PINMAP, 'p1'))
	Reg_p4 = PortSpec(8, T51_SoC.regmap(PINMAP, 'p4'))

	Reg_sro = PortSpec(8, T51_SoC.regmap(PINMAP, 'sr_4094'))
	Reg_sri = PortSpec(8, T51_SoC.regmap(PINMAP, 'sr_4021'))

	@cyrite_factory.block_component
	def platform_mine(self,
		clk : ClkSignal,
		reset : ResetSignal,
		dout : MyPort,
		din : MyPort,
		ain : AnalogInputs,
		pipe : PipePort,
		seconds_tick : Bool,
		):
		"The SoC setup for T51. Everything in here is on a hardware level."

		xram = WishboneBus(ADDR_W = 16, DATA_W = 8)

		xram_we_s  = xram.we
		xram_stb_s = xram.stb
		xram_cyc_s = xram.cyc
		xram_ack_s = xram.ack
		#
		xram_dati_s = xram.datai
		xram_adr_s  = xram.adr
		xram_dato_s = xram.datao

		rxd = Bool()
		rxd_isout = Bool()
		rxd_out = Bool()
		txd = Bool()

		# Ports:
		mp = [ MyPort("rp%d" % i, template = t, Signal = self.Signal) for i, t in enumerate([
			self.Reg_p0,
			self.Reg_p1,
			self.Reg_p2,
			self.Reg_p3,
			self.Reg_p4
		]) ]

		# Input port maping to 4021
		sr_in = Signal(intbv()[8:])
		sr_out = Signal(intbv()[16:])

		port_wiring = [
			din.assign(sr_in),
			dout.compose(sr_out),
		]

		rtc_clk = Bool()
		rtc_clk = mp[1].write.RTC_SR_CLK

		AnalogPin = Signal.Type(intbv()[10:])

		analog_in = AnalogPin()
		analog_0 = AnalogPin()
		analog_1 = AnalogPin()
		analog_sel = Signal(intbv()[4:])

		# All platform specific wirings we must do before instancing
		# the CPU:
		# self._memory_select = mp[4].write.RAM_CS

		xram_en = Bool()

		# p_o = [ Byte() for i in range(self.NUMPORTS) ]
		# p_i = [ Byte() for i in range(self.NUMPORTS) ]
		int0 = Signal(bool(False))

		# Instance the SoC.
		# Note the xram_en input. This determines which RAM port
		# is used.
		u0 = self.soc_t8052NG(
			clk = clk,
			reset = reset,
			p0 = mp[0],
			p1 = mp[1],
			p2 = mp[2],
			p3 = mp[3],
			p4 = mp[4],
			analog_in = analog_in,
			pipeio = pipe,
			xram_en = xram_en,
			xram = xram,
			ROMADDRESSWIDTH = 16,
			XRAMADDRESSWIDTH = 16
		)

		# Instance shift registers
		# Instead of manual cascading, we just use a longer sr_out

		perio_4094_cascade = hef4094b(clk = clk,
			shift = mp[1].write.RTC_SR_CLK,
			ser   = mp[1].write.SRO_DAT,
			latch = mp[4].write.SRO_LAT,
			q = sr_out)

		perio_4021 = cd4021(clk = clk,
			shift = mp[4].write.SRI_CLK,
			latch = mp[4].write.SRI_LAT,
			p_in  = sr_in,
			serial_in = False,
			q5    = Open(1),
			q6    = Open(1),
			q7    = mp[1].read.SRI_DAT)


		# ANALOG muxer input section
		a = ain

		perio_4051_a = cd4051b(clk,
				a.hp, \
				a.service, \
				a.gt10, \
				a.gt8, \
				a.gt6, \
				a.gt3, \
				a.vvp, \
				a.gt9,
			inhibit = False,
			address = analog_sel[3:],
			q = analog_0
		)

		perio_4051_b = cd4051b(clk,
				a.extctrl, \
				a.gt5, \
				a.gt4, \
				a.gt11, \
				a.gt3x, \
				a.gt1, \
				a.gt2, \
				a.lp, \
			inhibit = False,
			address = analog_sel[3:],
			q = analog_1
		)

		# we don't tristate, hence we mux
		@always_comb
		def adc_mux_select():
			if analog_sel[3]:
				analog_in.next = analog_0
			else:
				analog_in.next = analog_1
	

		_wires_ = [
			xram_en                      @assign@ ( mp[4].write.RAM_CS ),
			xram_ack_s                   @assign@ ( xram_stb_s ),
			int0                         @assign@ ( False ),
			analog_sel.wireup( concat(
				dout.write.A_INH,
				dout.write.A_SEL2,
				dout.write.A_SEL1,
				dout.write.A_SEL0,
			))
		]


		# Wire up in and out with the 8051 in/out ports, correspondingly

		return instances()


	def create_top(self):
		Signal = self.Signal
		ClkSignal = self.ClkSignal
		ResetSignal = self.ResetSignal

		pipe = PipePort(self.Signal)

		clk = ClkSignal()
		reset = ResetSignal(False, False)

		sensors = AnalogInputs(self)

		tick = self.Signal(bool())

		# Create I/O port according to the Reg_* mappings
		digital_out_port = MyPort("DOUT", template = self.Reg_sro,
			Signal = self.Signal)
		digital_in_port = MyPort("DIN", template = self.Reg_sri,
			Signal = self.Signal)
		
		inst_soc = self.platform_mine(clk = clk, reset = reset,
			dout = digital_out_port, din = digital_in_port,
			pipe = pipe,
			ain = sensors,
			seconds_tick = tick)

		return inst_soc

	def build(self, output_dir):

		if isinstance(self.architecture, type) and issubclass(self.architecture, CoSimulator):
			tb = self.testbench52()
			tb.run(20000, debug = False, wavetrace = "output/t51sim.vcd", recompile = False)
		else:
			top = self.create_top()
			tgt = self.architecture.target_class()
			files = top.elab(tgt, elab_all = True, outpath = output_dir)
			print("Created files:", files)



class MyPlatformCosim(MyPlatform):
	"""The mock up platform with a UART coroutine
This actually just monitors a write access to the UART tx register
"""
	@cyrite_factory.testbench("ns")
	def testbench52(self,
		# signals:
	): 
		"The Co-Simulation bench"

		# Make sure to use self.Signal:
		Signal = self.Signal
		ClkSignal = self.ClkSignal
		ResetSignal = self.ResetSignal

		clk = ClkSignal()
		reset = ResetSignal(False, False)

		sensors = AnalogInputs(self)
		pipe = PipePort(self.Signal)

		tick = Signal(bool())

		# Create I/O port according to the Reg_* mappings
		digital_out_port = MyPort("DOUT", template = self.Reg_sro,
			Signal = Signal)
		digital_in_port = MyPort("DIN", template = self.Reg_sri,
			Signal = Signal)
		
		inst_soc = self.platform_mine(clk = clk, reset = reset,
			dout = digital_out_port, din = digital_in_port,
			pipe = pipe,
			ain = sensors,
			seconds_tick = tick)

		@self.always(delay(1))
		def clkgen():
			clk.next = ~clk

		@self.sequence
		def pipeio_handling():
			"Pipe I/O handler coroutine"
			print("PIPE I/O handler listening")
			yield delay(100)
			while True:
				if pipe.en_tx:
					pipe.busy.next = True
					print(f"> '{chr(int(pipe.tx.evaluate()))}'")
					yield clk.posedge
					pipe.busy.next = False
				# Make sure to not forget any wait cycle
				yield clk.posedge

		@self.sequence
		def rtc_mockup():
			"Create a user defined seconds tick"
			while True:
				yield delay(1_000_000)
				yield clk.posedge
				tick.next = True
				yield clk.posedge
				tick.next = False

		@self.sequence
		def io_stim():
			"Run a continuous phase stimulus"
			a = 0b001
			while True:
				digital_in_port.read.PIN9.next = (a & 1) != 0
				digital_in_port.read.PIN11.next = ((a >> 1) & 1) != 0
				digital_in_port.read.PIN13.next = ((a >> 2) & 1) != 0
				yield delay(10000)
				a = a >> 1 | (a & 1) << 2

		@self.sequence
		def main():
			print("Starting simulation")
			# init:

			yield delay(20)
			reset.next = True
			print("Reset released")
			print("Running...")

			# Set pin 5 (input only)
			yield delay(20)

			print("Enter loop")
			now = time.time()

			for i in range(20):
				print(f"@TICK [{self.now()}/{int(time.time()-now)}s]")
				yield delay(1_000_000)

			raise StopSimulation

		return locals()

