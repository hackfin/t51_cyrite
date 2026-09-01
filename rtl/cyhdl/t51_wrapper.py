# Contains the VHDL wrapper blackbox for the T8052 top 8052 implementation
#
from myirl.blackbox_ext import blackbox_vhdl
from cyhdl import *
from cyrite.auxiliaries.xhdl import vhdlaux as vh

_Bool = Signal.Type(bool)
_IOPort = Signal.Type(vh.std_logic_vector, 8)
_Byte = Signal.Type(vh.std_logic_vector, 8)
_Addr16 = Signal.Type(vh.std_logic_vector, 16)

import os

@blackbox_vhdl(path_prefix = os.path.dirname("../vhdl/T51_8052.vhd") )
def t8052(
	# signals:
	clk							: ClkSignal,
	rst_n						: ResetSignal,
	p0_in						: _IOPort,
	p1_in						: _IOPort,
	p2_in						: _IOPort,
	p3_in						: _IOPort,
	p0_out						: _IOPort.Output,
	p1_out						: _IOPort.Output,
	p2_out						: _IOPort.Output,
	p3_out						: _IOPort.Output,
	int0						: _Bool,
	int1						: _Bool,
	t0							: _Bool,
	t1							: _Bool,
	t2							: _Bool,
	t2ex						: _Bool,
	rxd							: _Bool,
	rxd_iso						: _Bool.Output,
	rxd_o						: _Bool.Output,
	txd							: _Bool.Output,
	xram_we_o					: _Bool.Output,
	xram_stb_o					: _Bool.Output,
	xram_cyc_o					: _Bool.Output,
	xram_ack_i					: _Bool,
	xram_dat_o					: _Byte.Output,
	xram_adr_o					: _Addr16.Output,
	xram_dat_i					: _Byte,
	*,
	TRISTATE					: int = 0,
	ROMADDRESSWIDTH				: int = 16,
	IRAMADDRESSWIDTH			: int = 8,
	XRAMADDRESSWIDTH			: int = 11): 
	"Blackbox wrapper for original VHDL code of T51"


