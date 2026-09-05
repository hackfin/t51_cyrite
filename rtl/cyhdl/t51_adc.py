# T51 ADC mockup core
#

from cyhdl import *
from cyrite.auxiliaries.xhdl import vhdlaux as vh
from . import cyhdl_work as work
from cyrite.library.counter.counter import Counter as Counter
from .cyhdl_work.types import *

@block
def t51_adc(
	# signals:
	clk							: Signal.Type(vh.std_logic),
	rst_n						: Signal.Type(vh.std_logic),
	sel							: Signal.Type(intbv()[2:]),
	rd_rmw						: Signal.Type(vh.std_logic),
	wr							: Signal.Type(vh.std_logic),
	data_in						: Signal.Type(vh.std_logic_vector, 7+1 - 0),
	data_out					: Signal.Type(vh.std_logic_vector, 7+1 - 0).Output,
	analog_in					: Signal.Type(intbv()[10:]),
	analog_sel                  : Signal.Type(intbv()[3:]).Output
	):
	
	"A simple mockup of the ADC registers of the NXP 8xC552"

	adcon = work.RegisterSignal("adcon", {
			"AADR" : 3,
			"ADCS" : 1,
			"ADCI" : 1,
			"ADEX" : 1,
			"ADVH" : 2, # Higher ADC value bits
		}
	)
	
	state_t = enum("IDLE", "RUN", "READY")

	state = Signal(state_t.IDLE)

	count = Counter(6, 0)

	pending = Bool()

	@always(sel, analog_in)
	def select_io():
		if sel == 1:
			data_out.next = analog_in[10:2]
		elif sel == 2:
			data_out.next = adcon
		else:
			data_out.next = 0

	@always_seq(clk.posedge, rst_n)
	def config_worker():	
		# Hack:
		adcon.ADCI.next = pending
		if state == state_t.READY:
			adcon.ADCS.next = False
		if wr  ==  True: # Assume we are not writing to the ADCH reg
			# Otherwise we HAVE TO delay the .sel flag
			# Write flags, except ADCI
			adcon.collect(data_in, w0c = [ "ADCI" ] )

		adcon.ADVH.next = analog_in[2:]

	@always_seq(clk.posedge, rst_n)
	def fsm():
		if state == state_t.IDLE:
			if adcon.ADCS and not adcon.ADCI:
				state.next = state_t.RUN
				count.reset()
		elif state == state_t.RUN:
			count.next = count + 1
			if count == 50:
				state.next = state_t.READY
				pending.next = True
		else:
			if adcon.ADCI == False:
				state.next = state_t.IDLE
				pending.next = False

	wires = [
		analog_sel.wireup(adcon.AADR),
	]

	return instances()
