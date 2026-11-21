# 8051 standard fake UART re-implementation
#
# This is the naked I/O wrapper, not doing any serialization.
#

from cyhdl import *
from cyrite.library.soc import Reg, BF, RegisterSignal
from .. import mmr

@block
def uartio_model(
	clk: ClkSignal,
	reset: ResetSignal,
	uartio,
	sfr : mmr.RegisterSignal.reverse(),
):
	"The model variant using the uartio port"
	tx_pending = Signal(bool(0))
	rx_latched = Signal(bool(0))
	rx_byte = Signal(intbv(0)[8:])

	t_txstate = enum('IDLE', 'WAIT_DONE')
	tx_state = Signal(t_txstate.IDLE)

	TI_sel = sfr.select.S0BUF_sel_w

	@always_seq(clk.posedge, reset)
	def seq():
		uartio.wr.next = 0
		uartio.rd.next = 0

		if sfr.select.S0BUF_sel_w: # Triggering write
			uartio.data_out.next = sfr.write.S0BUF
			uartio.wr.next = 1
			tx_pending.next = 1

		if sfr.select.S0BUF_r_sel_r: # Triggering read
			if rx_latched:
				sfr.read.S0BUF_r.next = rx_byte
			elif uartio.ready:
				sfr.read.S0BUF_r.next = uartio.data_in

		if tx_state == t_txstate.IDLE:
			if tx_pending:
				tx_state.next = t_txstate.WAIT_DONE
		elif tx_state == t_txstate.WAIT_DONE:
			if not uartio.busy:
				sfr.read.TI.next = 1
				tx_pending.next = 0
				tx_state.next = t_txstate.IDLE

		if sfr.write.REN and uartio.ready and not rx_latched:
			uartio.rd.next = 1
			rx_byte.next = uartio.data_in
			rx_latched.next = 1
			sfr.read.RI.next = 1
			sfr.read.RB8.next = 0

		if TI_sel:
			sfr.read.TI.next = sfr.write.TI

		if not sfr.write.REN:
			rx_latched.next = 0

	return instances()

