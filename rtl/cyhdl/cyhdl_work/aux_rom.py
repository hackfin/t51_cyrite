# ROM creation auxiliaries


from cyhdl import *
import struct
import pytest

from myirl.kernel import sensitivity

# import intelhex


class _HexROMGenerator(sensitivity.Generator):
	"""HEX ROM generator
Prevents us from emitting verilog that yosys can't digest well..."""
	def __init__(self, hexfile, memarray, startaddr = 0):
		self.hexfile = hexfile
		self.memarray = memarray
		self.startaddr = startaddr
		self.wsize = memarray[0].size()
		self.logic = sensitivity.LogicContext()
		sensitivity.TracebackObject.__init__(self, depth = 1)

	def gen(self):
		a = Signal(intbv()[self.wsize:])
		yield [ a.set(self.memarray[0]) ]
		
	def emit_verilog(self, ctx):
		_verilog = """
	initial begin
		$readmemh("%s", %s, %s);
	end
""" % (self.hexfile, self.memarray.identifier, self.startaddr)

		ctx.output(_verilog)

	def emit_vhdl(self, ctx):
		_vhdl = """
		type ram_t is array(0 to %d-1) of unsigned(%d-1 downto 0);

		impure function init_ram() return ram_t is
			file hexfile : text open read_mode is "%s";
			variable l : line;
			variable hw : unsigned(%d-1 downto 0);
			variable initmem : ram_t := (others => (others => '0'));
		begin
			for i in 0 to %d-1 loop
				exit when endfile(hexfile);
				readline(hexfile, l);
				report "read: " & l.all;
				hread(l, hw);
				initmem(i) := hw;
			end loop;

			return initmem;
		end function;
""" % (len(self.memarray), self.wsize, self.hexfile, self.wsize, len(self.memarray))


	def emit_rtl(self, ctx):
		assert False


	def __call__(self, ctx):
		tgt = ctx.target

		if tgt.lang == 'VHDL':
			self.emit = self.emit_vhdl
		elif tgt.lang == 'Verilog':
			self.emit = self.emit_verilog
		else:
			self.emit = self.emit_rtl

		seq = self.gen()
		for i in seq:
			self.logic += seq

class HexROMGenerator(_HexROMGenerator):


	def write_rawhex32(self, filename, data):
		data = data.tobinstr()


		with open(filename, "w") as hexfile:
			ds = ">L"

			l = len(data)
			i = 0

			s = ""
			while (i < l):
					chunk = data[i:i+4]
					words = struct.unpack(ds, chunk)
					s += '%08x\n' % words
					i += 4

			hexfile.write(s)
			hexfile.close()

	def write_rawhex8(self, filename, data):
		with open(filename, "w") as hexfile:
			ds = ">L"

			l = len(data)
			i = 0

			s = ""
			for chunk in data:
				s += '%02x\n' % chunk

			hexfile.write(s)
			hexfile.close()

	def emit(self, data, filename = None):
		filename = self.hexfile if filename is None else filename

		self.write_rawhex8(filename, data)
