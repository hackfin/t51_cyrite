# 8051 timer 0/1 reimplementation in cyHDL
#
# (c) 2026, <hackfin@section5.ch>
#
# Can opensource
#
from .. import mmr
from cyhdl import *

Bool = Signal.Type(bool)

@container
class TimerSignals:
	"Timer 1/2 signals, routed to pad"
	_inputs = [ "t0", "t1",
		"int0", "int1", # External interrupts (not related to timer)
		# We might move these out of this hierarchy, really
		"int_ack",
	]
	_outputs = [ "irq" ]
	_other = []

	def __init__(self, tick_period = None):
		self.t0 = Bool()
		self.t1 = Bool()
		self.int0 = Bool()
		self.int1 = Bool()
		self.int_ack = Signal(intbv()[2:])
		self.irq = Bool()

	@cyrite_method.sequence
	def reset(self):
		self.int0.next = True # Low active
		self.int1.next = True
		self.t0.next = False
		self.t1.next = False
		self.int_ack.next = 0
		print("Timer signals to default")

	@cyrite_method.sequence
	def pulse0(self, clk, n):
		self.t0.next = True
		yield n * (clk.posedge, )
		self.t0.next = False
		yield 4 * (clk.posedge, )

	@cyrite_method.sequence
	def pulse1(self, clk, n):
		self.t1.next = True
		yield n * (clk.posedge, )
		self.t1.next = False
		yield 4 * (clk.posedge, )

@block
def timer(clk : ClkSignal, reset : ResetSignal,
	pio : TimerSignals,
	sfr : mmr.RegisterSignal.reverse(),
	FASTCOUNT : bool = False
	):

	"Timer reimplementation using next generation SFR architecture"

	# No longer partially assigneable:
	cnt0, \
	cnt1 = [ Signal(modbv()[16:0]) for _ in range(2) ]

	cnt0_inc_l, cnt0_inc_h, \
	cnt1_inc_l, cnt1_inc_h	= [ Signal(modbv()[8:0]) for _ in range(4) ]
	tick0 = Signal(bool())
	tick1 = Signal(bool())
	tick12 = Signal(bool())

	of0, of1 = [ Signal(bool()) for _ in range(2) ]

	# Default 11 to not trigger an IRQ at start
	int_r = [ Signal(intbv(0b11)[2:]) for _ in range(2) ]

	UPPER = slice(16, 8)
	LOWER = slice(8, 0)

	tmod = sfr.write
	tcon = sfr.write
	tcon_status = sfr.read

	# Must use separate signals
	TH0_sel_w = sfr.select.TH0_sel_w
	TL0_sel_w = sfr.select.TL0_sel_w
	TH1_sel_w = sfr.select.TH1_sel_w
	TL1_sel_w = sfr.select.TL1_sel_w
	
	# This is for the read register part
	wirings = [
		sfr.read.TH0_r    @assign@   ( cnt0[UPPER] ),
		sfr.read.TL0_r    @assign@   ( cnt0[LOWER] ),
		sfr.read.TH1_r    @assign@   ( cnt1[UPPER] ),
		sfr.read.TL1_r    @assign@   ( cnt1[LOWER] ),

		cnt0_inc_l	.set   ( cnt0[LOWER] + 1 ),
		cnt0_inc_h	.set   ( cnt0[UPPER] + 1 ),
		cnt1_inc_l	.set   ( cnt1[LOWER] + 1 ),
	]

	
	irq_wiring = [
		pio.irq   .wireup (tcon_status.IE0 | tcon_status.IE1 )
	]

	@always_seq(clk.posedge, reset)
	def irq_event():	
		"""Handles IRQ events and the corresponding flags. These are
not directly related to the timer core, but the 8051 does it that way."""
		int_r[0].next = concat(int_r[0][0], pio.int0)
		int_r[1].next = concat(int_r[1][0], pio.int1)

		if tcon.IT0:
			if pio.int_ack[0]:
				tcon_status.IE0.next = False
			if int_r[0] == 0b10:
				tcon_status.IE0.next = True
		else:
			tcon_status.IE0.next = ~int_r[0][0]

		# And same for the I.1 flags:
		if tcon.IT1:
			if pio.int_ack[1]:
				tcon_status.IE1.next = False
			if int_r[1] == 0b10:
				tcon_status.IE1.next = True
		else:
			tcon_status.IE1.next = ~int_r[1][0]

	# Wire overflow flags to register directly
	overflow_wiring = [
		tcon_status.TF0.wireup(of0),
		tcon_status.TF1.wireup(of1),
	]
	
	@always_seq(clk.posedge, reset)
	def timer_count():	
		# async mux statements:		   
	
		# Auto-Clear:
		if pio.int_ack[0]:
			of0.next = False
		if pio.int_ack[1]:
			of1.next = False

		if tmod.MOD0	==	0b00:			 
			if tick0  ==  True:				   
				cnt0.next = cnt0[13:] + 1
				if cnt0  ==  0b1111111111111:					 
					of0.next = True
		elif tmod.MOD0	==	0b01:			 
			if tick0  ==  True:				   
				cnt0.next = cnt0 + 1
				if cnt0  ==  0b1111111111111111:					
					of0.next = True
		elif tmod.MOD0	==	0b10:			 
			if tick0  ==  True:				   
				cnt0.next = concat( cnt0[UPPER], cnt0_inc_l )
				if cnt0[LOWER]	==	0b11111111:					   
					cnt0.next = concat(cnt0[UPPER], cnt0[UPPER])
					of0.next = True
		# Combined timer:
		elif tmod.MOD0	== 0b11:			 
			if tick0  ==  True:				   
				cnt0.next = concat( cnt0[UPPER], cnt0_inc_l )
				if cnt0[LOWER]	==	0b11111111:					   
					of0.next = True
			of1.next = False

			if tcon.TR1:
				if tick12 == True:				 
					cnt0.next = concat(cnt0_inc_h, cnt0[LOWER])
					if cnt1[UPPER]	==	0b11111111:					
						of1.next = True

		else:
			pass

		if tmod.MOD1	==	0b00:			 
			if tick1  ==  True:				   
				cnt1.next = cnt1[13:0] + 1
				if cnt1[13:0]  ==  0b1111111111111:					 
					of1.next = True
		elif tmod.MOD1	==	0b01:			 
			if tick1  ==  True:				   
				cnt1.next = (cnt1 + 1)
				if cnt1  ==  0b1111111111111111:					
					of1.next = True
		elif tmod.MOD1	==	0b10:			 
			if tick1  ==  True:				   
				cnt1.next = concat (cnt1[UPPER], cnt1_inc_l )
				if cnt1[LOWER]	==	0b11111111:					   
					cnt1.next = concat(cnt1[UPPER], cnt1[UPPER])
					of1.next = True

		else:
			# XXX Mode 3 not covered for timer 1
			pass


		# All previous assignments are overridden by writes
		if TH0_sel_w  ==  True:			   
			cnt0.next = concat( sfr.write.TH0, cnt0[LOWER] )
		elif TL0_sel_w	==	True:			   
			cnt0.next = concat( cnt0[UPPER], sfr.write.TL0 )
		elif TH1_sel_w	==	True:			   
			cnt1.next = concat( sfr.write.TH1, cnt1[LOWER] )
		elif TL1_sel_w	==	True:			   
			cnt1.next = concat( cnt1[UPPER], sfr.write.TL1 )

	t0_r = Signal(intbv()[2:])
	t1_r = Signal(intbv()[2:])
	i0_r = int_r[0]  # Trace visibility (auto-rename)
	i1_r = int_r[1]

	prescaler = Signal(intbv()[4:])

	if FASTCOUNT:
		tick12_assign = [ tick12.wireup(True) ]
	else:
		@always_seq(clk.posedge, reset)
		def tick12_gen():	
			if prescaler  ==  0b1011:			 
				prescaler.next = 0b0000
				tick12.next = True
			else:
				tick12.next = False
				prescaler.next = (prescaler + 1)

	@always_seq(clk.posedge, reset)
	def timer_logic():	
		# Taken over from the VHDL implentation
		tick0.next = False
		tick1.next = False
		# Timer running?
		if tcon.TR0:
			if ((i0_r[1] == True) | (tmod.GATE0 == False)):
				if tmod.CT0	==	True:				 
					tick0.next = (t0_r[0] & ~t0_r[1])
				else:
					tick0.next = tick12

		if tcon.TR1:
			if ((i1_r[1] == True) | (tmod.GATE1 == False)): 
				if tmod.CT1	==	True:				 
					tick1.next = (t1_r[0] & ~t1_r[1])
				else:
					tick1.next = tick12

		t0_r.next = concat(t0_r[0], pio.t0)
		t1_r.next = concat(t1_r[0], pio.t1)

	return instances()

class SFRMap(mmr.Generator):
	"A SFR map generator with only the timer register MMR description"
	default_size = 8
	BF = mmr.BF
	WRITE_TRIGGER = mmr.Reg.WRITEONLY | mmr.Reg.VOLATILE
	reg_TL0 = mmr.Reg(default_size, [], flags = WRITE_TRIGGER)
	reg_TH0 = mmr.Reg(default_size, [], flags = WRITE_TRIGGER)
	reg_TL1 = mmr.Reg(default_size, [], flags = WRITE_TRIGGER)
	reg_TH1 = mmr.Reg(default_size, [], flags = WRITE_TRIGGER)
	reg_TL0_r = mmr.Reg(default_size, [], flags = mmr.Reg.READONLY)
	reg_TH0_r = mmr.Reg(default_size, [], flags = mmr.Reg.READONLY)
	reg_TL1_r = mmr.Reg(default_size, [], flags = mmr.Reg.READONLY)
	reg_TH1_r = mmr.Reg(default_size, [], flags = mmr.Reg.READONLY)


	reg_TMOD = mmr.Reg(default_size, [
			# TMOD
			BF("GATE1", 15, 15),
			BF("CT1", 14, 14),
			BF("MOD1", 12, 13),
			BF("GATE0", 11, 11),
			BF("CT0", 10, 10), # Counter operation
			BF("MOD0", 8, 9),
		]
	)
	reg_TCON = mmr.Reg(default_size, [
			BF("TF1", 7, 7, flags = BF.READONLY),
			BF("TR1", 6, 6),
			BF("TF0", 5, 5, flags = BF.READONLY),
			BF("TR0", 4, 4),
			BF("IE1", 3, 3, flags = BF.READONLY),
			BF("IT1", 2, 2),
			BF("IE0", 1, 1, flags = BF.READONLY),
			BF("IT0", 0, 0),
		],
		flags = mmr.Reg.VOLATILE
	)

	register_map = {
		(0x01, "WO") : [ "TL0", reg_TL0 ],
		(0x02, "WO") : [ "TH0", reg_TH0 ],
		(0x11, "WO") : [ "TL1", reg_TL0 ],
		(0x12, "WO") : [ "TH1", reg_TH0 ],
		(0x01, "RO") : [ "TL0", reg_TL0_r ],
		(0x02, "RO") : [ "TH0", reg_TH0_r ],
		(0x11, "RO") : [ "TL1", reg_TL0_r ],
		(0x12, "RO") : [ "TH1", reg_TH0_r ],
		(0x20, "WO") : [ "TCON", reg_TCON ],
		(0x20, "RO") : [ "TCON_r", reg_TCON ],
		(0x20, "RW") : [ "TMOD", reg_TMOD ],
	}


class TimerTest(cyrite_factory.Module, SFRMap):
	HALF_PERIOD = 2 # half period duration in testbench units (ns)
	TimerSignals = TimerSignals
	BF = mmr.BF
	intbv = intbv

	@cyrite_method.sequence
	def tcon_init(self, sfr):
		sfr.write.CT0.next = False
		sfr.write.CT1.next = False
		sfr.write.GATE0.next = False
		sfr.write.GATE1.next = False
		sfr.write.MOD0.next = 2 # Timer mode
		sfr.write.MOD1.next = 0 # Timer mode
		sfr.write.IT0.next = True # Edge
		sfr.write.IT1.next = False

	@cyrite_method.sequence
	def config_period(self, clk, sfr, which, pval):
		period = self.intbv(pval)[16:]
		sfr.select.TL0_sel_w.next = False
		sfr.select.TH0_sel_w.next = False
		sfr.select.TL1_sel_w.next = False
		sfr.select.TH1_sel_w.next = False

		yield clk.posedge
		if which == 1:
			sfr.write.TL1.next = period[8:]
			sfr.write.TH1.next = period[16:8]
			yield clk.posedge
			sfr.select.TL1_sel_w.next = True
			sfr.select.TH1_sel_w.next = True
			yield clk.posedge
			sfr.select.TL1_sel_w.next = False
			sfr.select.TH1_sel_w.next = False

		else:
			sfr.write.TL0.next = period[8:]
			sfr.write.TH0.next = period[16:8]
			yield clk.posedge
			sfr.select.TL0_sel_w.next = True
			sfr.select.TH0_sel_w.next = True
			yield clk.posedge
			sfr.select.TL0_sel_w.next = False
			sfr.select.TH0_sel_w.next = False

		# Pulse to signal write event:

	@cyrite_method.sequence
	def test_timer(self, clk, pio, sfr):
		pio.reset()

		yield from self.config_period(clk, sfr, 0, 200)
		yield from self.config_period(clk, sfr, 1, 144)

		yield delay(10)
		
		yield from self.tcon_init(sfr)
		yield delay(200)
		sfr.write.TR0.next = True # Kick timer
		yield delay(10)
		sfr.write.TR1.next = True # Kick timer
	
	
	@cyrite_factory.testbench('ns')
	def tb_timer(self):
		sfr = mmr.MMRSignal("timer_sfr", template = self.register_map)
		pio = self.TimerSignals(self.HALF_PERIOD * 2)
		clk = ClkSignal()
		reset = ResetSignal(True, True)
		uut = timer(clk, reset, pio, sfr)

		@self.always(delay(self.HALF_PERIOD))
		def clkgen():
			clk.next = ~clk

		@self.sequence
		def main():
			yield delay(10)
			reset.next = False

			yield from self.test_timer(clk, pio, sfr)

			yield delay(100000)
			raise StopSimulation

		return instances()


from cyrite.simulation import icarus

def test_timer():
	t = TimerTest("timer01", icarus.ICARUS)
	tb = t.tb_timer()

	tb.run(20000, debug = True, wavetrace = "/tmp/timer.vcd")

if __name__ == "__main__":
	test_timer()
