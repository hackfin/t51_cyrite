# Cut down temporary mmr wrapper

from cyhdl import *
from myirl.kernel._types import ContainerBase, ContainerExtension, _LogicBool
from myirl.kernel import sensitivity
from cyrite.library.soc.registersignal import \
	_RegisterSignal, RegisterSignal, BF
from myirl.library.bulksignals import ContainerGen, BulkGen
from cyrite.library.soc.mmrfactory import MMRGenerator
from cyrite.library.soc.mmr import Reg
from myirl.library.vhdlpackage import StubLib

from myirl.kernel.components import Comment
Bool = Signal.Type(bool)
from myirl.kernel.sig import ConstSig


class IOMixin(ContainerExtension):
	"We silently mix in a method for all of these"
	@hdlmacro
	def wireup(self, other):
		yield "DEBUG: IOMixin wireup"
		for o in self._outputs:
			direction = other._iomap[o]
			if direction is not None:
				src = getattr(self, o)
				dst = getattr(other, o)
				yield dst.wireup(src)
		for i in self._inputs:
			dst = getattr(self, i)
			src = getattr(other, i)
			yield dst.wireup(src)

	def as_unrolled(self):
		"""Return a copy of this container as bulk signal that is unrolled
in the interface"""
		template = self._template
		
		iomap = {}
		for n in self._outputs:
			iomap[n] = True
		for n in self._inputs:
			iomap[n] = False
		for n in self._other:
			iomap[n] = False

		uc = _IO_UnrollGen()
		uc._iomap = iomap
		uc._type = _IO_Unroll
		uc._cls = template

		uc._targets = uc.supported_targets()

		# Fix up I/O:

		return uc()
		
class IOPortType(CONTAINER_INTERFACE):
	_container_type = IOMixin

class RegMacros:
	def get_read(self, name):
		try:
			return getattr(self, name)
		except KeyError as e:
			e.args += (f"Only members found: {self.members()}",)
			raise e

	def get_write(self, name):
		try:
			return getattr(self, name)
		except KeyError as e:
			e.args += (f"Only members found: {self.members()}",)
			raise e

	@sensitivity.hdlmacro
	def set_members(self, data, name, reg):
		logic = []

		l = reg.members().items()
		# We can safely assume all registers have bitfield members.
		# If they did not, we made them have in our RegisterSignal impl

		if len(l) == 0:
			msig = self.get_write(name)
			logic.append(msig.set(data[reg.size():]))
			yield logic
			return

		for bfn, bfd in l:
			if bfn[0] != '_':
				if (bfd.flags & bfd.READONLY) == 0:
					msig = self.get_write(bfn)
					logic.append(msig.set(data[bfd.as_slice()]))

		yield logic

	def assign_members(self, name, data, mmr, reg, compose):
		"""Grainy composition of `data` out of the available sources.
These are either:
- Register bit entity members of ourselves (self) holding a configuration
- Volatile bit mappings to signals from the peripheral (mmr)
 """
		d = {}

		if reg.is_set(reg.WRITEONLY):
			logic = [ Comment("writeonly") ]

		l = reg.members().items()
		for bfn, bfd in l:
			if bfn[0] == '_':
				continue
			if bfd.is_set(bfd.READONLY):
				# Now if we got a readonly one, loop it in into the
				# assignment directly from the mmr port (these
				# are readonly or WxC bits)
				s = getattr(mmr.read, bfn)
				d[bfn] = s
			elif not bfd.is_set(bfd.WRITEONLY):
				msig = self.get_read(bfn)
				d[bfn] = msig
			else:
				pass

		if len(l) == 0:
			# raise ValueError("No bitfield members in %s" % name)
			return [
				Comment("NO MEMBERS : %s" % name),
				data.set(self.get_read(name))
			]


		if compose:
			logic = [ data.set(reg.compose(**d)) ]
		else:
			assert False # Unsupported here
		return logic



class _RegSignal(RegMacros, _RegisterSignal):
	def bitfield_id(self, reg, bf):
		# return reg[0] + '_' + bf
		return bf # No bitfield name collisions

	def get_bitfields(self, n, reg):
		_bitfields = list(filter(lambda x: x[0][0] != '_', reg.members().items()))

		if len(_bitfields) == 0:
			bf = BF(n, reg.size()-1, 0)
			# bf.flags = reg._flags
			_bitfields = [(n, bf)]

		return _bitfields

	def get_write(self, name):
		return getattr(self.write, name)

	def get_read(self, name):
		return getattr(self.read, name)

	def append_list(self, bfl, i, _bitfields):
		for bk, bi in _bitfields:
			krb = self.bitfield_id(i, bk)
			bfl.append((krb, bi))

	def populate(self, rdict):
		m = 0
		# Walk the register map with the following rules:
		#
		# * When register is VOLATILE, create a select signal
		#	(common to all containing bitfields)


		bitfields_read = []
		bitfields_write = []
		select_sigs = {}

		for k, i in rdict.items():
			n, reg = i

			if n[0] == '_':
				continue
			# Maximum size of registers found:
			if m < reg.size():
				m = reg.size()

			_bitfields = self.get_bitfields(n, reg)

			# Select signals PER REGISTER:
			if reg.is_set(reg.VOLATILE):
				if not reg.is_set(reg.READONLY):
					select_sigs["%s_sel_w" % n] = Signal(bool(0))
				if not reg.is_set(reg.WRITEONLY):
					select_sigs["%s_sel_r" % n] = Signal(bool(0))

			# When writeonly, we have a direct line to the core
			if reg.is_set(reg.WRITEONLY):
				self.append_list(bitfields_write, i, _bitfields)
			elif reg.is_set(reg.READONLY):
				self.append_list(bitfields_read, i, _bitfields)
			else:
				# We only have a read wire when we are volatile
				if reg.is_set(reg.VOLATILE):
					self.append_list(bitfields_read, i, _bitfields)
				# Note that a WxC type is void when register not volatile	
				self.append_list(bitfields_write, i, _bitfields)
			

		# Now filter per BF access flags:
		is_write = lambda t: (t[1].is_set(BF.WRITEONLY) or not t[1].is_set(BF.READONLY))
		is_read = lambda t: (t[1].is_set(BF.READONLY))

		# inputs = bitfields_write
		control = list(filter(is_write, bitfields_write))
		status = bitfields_read

		# We can still have READONLY bits in a default RW register:

		# status = list(status) + list(filter(is_read, bitfields_write))

		return status, control, select_sigs


class MMRSignal(_RegSignal):
	"""The MMR signal contains a `write`, `read` and `select` member, like
a register signal. However, it contains only interconnection signals
between decoder and core.

Note: Members (bit fields) prefixed with an underscore are considered
'reserved' and are not emitted.

"""
	bv = intbv

	def __init__(self, name, signals = None, parameters = None,
		template = None, virtual = None,
		Signal = Signal, no_bitfields = False):
		if name is None:
			name = kernel.utils.get_uuid('reg_')

		if no_bitfields:
			self.get_bitfields = self.get_fullreg

		rdict = template

		if signals is not None:
			# Important to pass 'twoway' in order to resolve
			# container members, like mmr.read, mmr.write, etc.
			super().__init__(name, signals, template = rdict, virtual = virtual,
				twoway = True)
			return
			
		if not isinstance(rdict, dict):
			raise TypeError("expects register dictionary as argument")

		inputs, outputs, select_sigs = self.populate(rdict)		
		input_container  = self.create(name, 'read',
			self.build_signals("in", inputs, Signal), ())
		output_container = self.create(name, 'write',
			self.build_signals("out", outputs, Signal), ())

		select_container = self.create(name, 'sel', select_sigs, ())

		sigs = {}
		
		if input_container is not None:
			sigs['read'] = input_container
		if output_container is not None:
			output_container._output = True
			output_container._aux = False
			sigs['write'] = output_container
		if select_container is not None:
			select_container._output = True
			sigs['select'] = select_container

		for n, s in sigs.items():
			s.rename(name + '_' + n)

		super().__init__(name, sigs, template = template, virtual = False,
			twoway = True)

	def get_fullreg(self, n, reg):
		bf = BF(n, reg.size()-1, 0)
		# bf.flags = reg._flags
		_bitfields = [(n, bf)]
		return _bitfields

	def match(self, *args):
		return True

	def dump_children(self):
		print("===== DEBUG MMR CHILDREN =====")
		print("DEBUG WRITE", self.write.members())
		if 'read' in self._sigdict:
			print("DEBUG READ", self.read.members())

	def get_select(self, name, which):
		return getattr(self.select, "%s_sel_%s" % (name, which))

	def get_sources(self, srcs):
		# We now consequently use the source/driver model
		if 'read' in self._sigdict:
			s = self.read
			srcs[s.identifier] = s

	def get_drivers(self, drvs):
		sigs = self.write,
		if 'select' in self._sigdict:
			sigs += self.select,
		for s in sigs:
			drvs[s.identifier] = s

class RegisterWrapper:
	"""Auxiliary class, allowing to create some register abstraction.
This classes .write() method differs from the classical Register.compose()
method as only assigned register bitfields are changed. The others are
left untouched and are cached internally."""

	Comment = Comment
	USE_ACK = True

	def __init__(self, bus, addr, regdesc, name = None):
		self.addr = addr
		self.regdesc = regdesc
		self.name = name
		self.bus = bus
		self.cache = {}
		self.compose = self.regdesc.compose

	def __getitem__(self, item):
		bf = self.regdesc.bf(item)
		return bf

	def _cache(self, d):
		for n, i in d.items():
			self.cache[n] = i

		return self.cache

	def cached_write(self, bitfields):
		"Changes cached bitfield values"
		c = self._cache(bitfields)
		return self.regdesc.compose(**c)

	@cyrite_method.sequence
	def write(self, clk, **bitfields):
		"Bus write sequence for bitfields"
		yield from self.bus.write(clk, self.addr, 
			self.cached_write(bitfields), ACK = self.USE_ACK)

	@cyrite_method.sequence
	def write_reg(self, clk, val):
		"Bus write sequence for register"
		self.Comment("Write to register %s: %x" % (self.name, val))
		yield from self.bus.write(clk, self.addr, val, ACK = self.USE_ACK)

	def match(self, sig, **bitfields):
		"Returns True when all given bitfields match in `sig`"
		v = sig.evaluate()
		mask = 0
		value = 0
		for n, i in bitfields.items():
			bf = self[n]
			m = bf.as_mask()
			value |= (i << bf.lsb) & m
			mask |= m

		if (v & mask) == value:
			return True

		return False

	def parse_value(self, value):
		if isinstance(value, int):
			pass
		elif isinstance(value, dict):
			value = self.regdesc.compose(**value)
			value = value.evaluate()
		else:
			raise TypeError("Unsupported value type %s" % type(value))

		return value

	@cyrite_method.sequence
	def _read(self, clk, out = None):
		yield from self.bus.read(clk, self.addr, ACK = self.USE_ACK)
		yield clk.posedge
		yield clk.posedge
		if out is None:
			print("READ", self.bus.datao)
		else:
			out.next = self.bus.datao

		yield clk.negedge # Make sure data is valid

	@cyrite_method.sequence
	def _read_verify(self, clk, value, scenario):
		yield from self.bus.read(clk, self.addr)
		yield clk.posedge
		yield clk.posedge
		print("READ VFY", self.bus.datao, type(value))
		assert self.bus.datao == value, scenario

	@cyrite_method.sequence
	def read_verify(self, clk, *args, **kwargs):
		"""This function accepts an integer argument or variable keywords
whose names must correspond to the register's bitfield. A value is constructed
out of the given keyword settings, leaving non-specified bitfields zero.
Unlike the .write() method, this is thus not caching unspecified bitfields.
The function will raise a ValueError if the composed value is not matching.
For now, only valid in a cosimulation context (not for HDL emission)"""

		# We need to determine the caller depth, individually
		scenario = debuginfo(4, 'read')

		# We have to do out of band tricks:
		if len(args) == 0:
			value = kwargs
		else:
			value = args[0]
		value = self.parse_value(value) # This is executed
		yield from self._read_verify(clk, value, scenario) # This is generated

class _Bulk(BulkGen):
	"""Bulk class for local register signals. These hold RW register
settings for the peripherals and are created as in and output, respectively.
Readonly registers are not instanced, as they are wired directly to the
peripheral."""
	def __call__(self, *args, **kwargs):
		inst = self._cls(*args, **kwargs)

		d = {}

		default = get_default(inst._template)

		for bfn, bf in inst._template.members().items():
			if (bf.flags & bf.READONLY) == 0:
				sz = bf.size()

				if default is None:
					val = default
				elif isinstance(default, str):
					j = inst._template._size - bf.msb
					k = inst._template._size - bf.lsb

					assert bf.lsb <= bf.msb

					val = default[j:k+1]

				elif isinstance(default, int):
					val = (bf.as_mask() & default) >> bf.lsb

				try:

					if sz == 1:
						if val is None:
							wire = bool()
						else:
							wire = bool(val)
					else:
						if val is None:
							wire = intbv()[sz:]
						else:
							wire = intbv(val)[sz:]

					d[bfn] = Signal(wire)
				except ValueError as e:
					e.args += (f"Illegal default for {bfn} : {val}", )
					raise e

		if len(d) == 0:
			d[inst.name] = Signal(intbv(default)[inst._template.size():])

		n = self._cls.__name__

		sign  = self.signature(self._cls, args, kwargs)
		if sign in self._registry:
			t = self._registry[sign]
		else:
			# Take our bases:
			bases = (self._cls, ) + self._cls.__bases__
			t = self.create(sign, d, bases) # Create sub class type
			self._register_type(t, sign)

		container = t()
		container._populate(d)

		return container

def get_default(template):
	if template._default is None:
		default = None
	elif template._default[:2] == "0x":
		default = int(template._default, 16)
	else:
		# If length matches size, we may allow
		# undefined bit fields. In this case, the default is
		# a string.
		if len(template._default) == template._size:
			default = template._default
		else:
			default = int(template._default)
		return template._default
	return default

def _extract_from(strval, sl):
	n = len(strval)
	if isinstance(sl, int):
		return strval[n-sl-1] # MSB right
	else:
		if sl.start > n:
			raise ValueError(f"Default string length mismatch: {n} > {sl.start}")
	
		return strval[n-sl.start:n-sl.stop]


def local_reg_signal(name, template):
	"Create a local register signal type"

	class LocalRegSignal(RegMacros):
		def __init__(self, name):
			self.name = name

		_template = template

		def populate_defaults(self, default):
			"""Replace init values according to default bits (string"""
			l = self._template.bfmap.items()
			# We can safely assume all registers have bitfield members.
			# If they did not, we made them have in our RegisterSignal impl

			if isinstance(default, int):
				for bfn, bfd in l:
					msig = getattr(self, bfn)
					initval = bfd.extract_from(default)
					if bfd.msb == bfd.lsb:
						msig._initval = _LogicBool(initval)
					else:
						msig._initval = intbv(initval)[bfd.msb+1:bfd.lsb]
			elif isinstance(default, str):
				# String, in this case, the wire type must allow a
				# matching initializer
				for bfn, bfd in l:
					msig = getattr(self, bfn)
					initval = _extract_from(default, bfd.as_slice())
					if bfd.msb == bfd.lsb:
						msig._initval = _LogicBool(initval)
					else:
						msig._initval = intbv(initval)[bfd.msb+1:bfd.lsb]
			else:
				raise TypeError(f"Unsupported default type {type(default)}")
			

	default = get_default(template)

	# Full signal?
	if len(template.bfmap) == 0:
		if default is None:
			wire = intbv()[template.size():]
		else:
			try:
				wire = intbv(default)[template.size():]
			except ValueError:
				print("Not setting default, unspecified:", default)
				wire = intbv(0)[template.size():]

		sig = Signal(wire)

	else:
		ctype = container(_Bulk)(LocalRegSignal)
		sig = ctype(name)
		if not default is None:
			sig.populate_defaults(default)

	sig.rename('RWreg_' + name)

	return sig

class Generator(MMRGenerator):
	Signal = Signal

	def __init__(self, name, compose = True, addr_shift = 0):
		super().__init__(name, compose)
		self.addr_shift = addr_shift # Shift constant address value

	def wireup_registers(self, localregs, mmr):
		"Wire up local registers to write (only) mmr wires"
		logic = []
		for rn, reg in localregs.items():
			if isinstance(reg, Signal):
				logic += [ getattr(mmr.write, rn).wireup(reg) ]
			elif reg is None:
				assert False, f"Reg {rn} is None"
			else:
				for n, bfsig in reg.members().items():
					if n[0] == '_':
						print("Notice: Skipping hidden bitfield (_ prefix) `%s`" % n)
					else:
						logic += [ getattr(mmr.write, n).wireup(bfsig) ]
		return logic

	def generate_reset_select(self, regmap, mmr):
		logic = []
		for rt, rdesc in regmap.items():
			a, _ = rt
			name, rd = rdesc[0], rdesc[1]
			if rd.has_select(Reg.READONLY):
				msig = mmr.get_select(name, 'w')
				logic += [ msig.set(False) ]
			elif rd.has_select(Reg.WRITEONLY):
				msig = mmr.get_select(name, 'r')
				logic += [ msig.set(False) ]

		return logic

	def create_case_constructs(self, logic, mmr, addr, idata, odata, local_registers, regmap, REPORT_ILLEGAL_ACCESS):
		cw, cr = [ logic.Case(addr) for _ in range(2) ]
		N = addr.size()

		mask = (1 << N) - 1

		for rt, rdesc in regmap.items():
			a, _ = rt

			a >>= self.addr_shift
			
			name, rd = rdesc[0], rdesc[1]

			maybe_read_sel = None
			maybe_read_clr = None
			maybe_write_sel = None
			maybe_write_clr = None

			if rd.has_select(Reg.READONLY):
				msig = mmr.get_select(name, 'w')
				maybe_write_sel = msig.set(True)
				maybe_write_clr = msig.set(False)
			elif rd.has_select(Reg.WRITEONLY):
				msig = mmr.get_select(name, 'r')
				maybe_read_sel = msig.set(True)
				maybe_read_clr = msig.set(False)

			if rd.is_set(Reg.READONLY):
				reg = mmr
			elif rd.is_set(Reg.WRITEONLY):
				reg = mmr
			else:
				reg = local_registers[name]
								
			s = ConstSig(a & mask, N)

			# If we can write, create according logic:
			if not rd.is_set(Reg.READONLY):
				if isinstance(reg, RegMacros):
					_set = reg.set_members(idata, name, rd)
				else:
					sz = reg.size()
					_set = reg.set(idata[sz:])

				cw = cw.When(s)(
					_set,
					maybe_write_sel
				)

			# If we can read, create logic, too
			if not rd.is_set(Reg.WRITEONLY):
				if isinstance(reg, RegMacros):
					_assign = reg.assign_members(name, odata, mmr,
						rd, compose = self.compose)
				else:
					_assign = [ odata.set(reg), Comment("SET") ]

				cr = cr.When(s)(
					Comment(f"READ_LOGIC {name}, {type(reg)}"),
					*_assign,
					maybe_read_sel
				)
				
		if REPORT_ILLEGAL_ACCESS:
			cw = cw.Other(sim.raise_(ValueError("Illegal WRITE address")))
			cr = cr.Other(sim.raise_(ValueError("Illegal READ address")))
		else:
			cw = cw.Other(maybe_write_clr)
			cr = cr.Other(maybe_read_clr)

		return cr, cw


	def generate_mmr_decoder(self,
		regmap, interface, clk, reset, ce, re, we, read_addr, write_addr,
			idata, odata,
				   REPORT_ILLEGAL_ACCESS = False,
				   RESET_DEFAULTS = False, READ_ASYNC = False):

		
		kwargs = { 'EDGE' : clk.POS }
		if RESET_DEFAULTS:
			kwargs['RESET'] = reset

		mmr = interface['mmr']

		# Local registers for storage of R/W bit fields (non-volatile)
		local_registers = {}
		for rt, rdesc in regmap.items():
			name, rd = rdesc[0], rdesc[1]
			if not rd.is_set(rd.READONLY) and not rd.is_set(rd.WRITEONLY):
				reg = local_reg_signal(name, template = rd)
				assert not reg is None
				local_registers[name] = reg
			elif rd.is_set(rd.READONLY):
				if not rd._default is None:
					print("Warning: RO value has default", name, rd._default)
			elif rd.is_set(rd.WRITEONLY):
				if not rd.has_bitfields():
					print("DEBUG SET WRITEONLY DEFAULT", name, rdesc[0], rd._default)
					mmr_sig = getattr(mmr.write, name)
					d = get_default(rd)
					if not d is None:
						mmr_sig._initval = d


		@sensitivity.process(clk, **kwargs)
		def worker(logic):
			"""Creates a case/when flow the procedural way"""

			cr, cw = self.create_case_constructs(logic, mmr, read_addr,
				idata, odata, local_registers, regmap,
				REPORT_ILLEGAL_ACCESS)			

			_if = logic.If(we == True).Then(cw).Elif(re == True).Then(cr)

			_if = logic.If(ce == True).Then( _if)
	 
			logic += [
				Comment("RESET"),
				 *self.generate_reset_select(regmap, mmr),
				 _if
			]

		@sensitivity.process(read_addr, ce, re)
		def read_async(logic):
			"""Creates a an async read decoder"""
			cr, _ = self.create_case_constructs(logic, mmr, read_addr,
				idata, odata, local_registers, regmap,
				REPORT_ILLEGAL_ACCESS)			

			_if = logic.If(re == True).Then(cr)

			_if = logic.If(ce == True).Then( _if)
	 
			logic += [ Comment("ASYNC_READ"), _if ]

		@sensitivity.process(clk, **kwargs)
		def write_sync(logic):
			"""Creates a separate synchronous write decoder"""

			_, cw = self.create_case_constructs(logic, mmr, write_addr,
				idata, odata, local_registers, regmap,
				REPORT_ILLEGAL_ACCESS)			

			_if = logic.If(we == True).Then(cw)

			_if = logic.If(ce == True).Then( _if)
	 
			logic += [
				 *self.generate_reset_select(regmap, mmr),
				 _if
			]

		try:
			_wirings = self.wireup_registers(local_registers, mmr)
		except KeyError as e:
			print("DEBUG: local registers", local_registers)
			e.args = ("Possible access mismatch between register/bitfield",) + \
				e.args
			raise e

		if READ_ASYNC:
			return read_async, write_sync, *_wirings
		else:
			return worker, *_wirings


class DeviceBase:
	"""The device base for more fine grained SoC or peripheral
address decoders.

Note the instancing options: An inherited class should set these.

READ_ASYNC: We read directly. This is not recommended for large register
            Mostly used on 8051 SFR designs.
DELAYED_WRITE: Delay the write address by one cycle. This is needed for
            some 8051 SFR implementations."""
	RegisterWrapper = RegisterWrapper
	READ_ASYNC = False # We use clk'posedge  reads by default
	DELAYED_WRITE_ADDRESS = False # no delayed write
	

	def get_reg(self, dev, name):
		"Gets the register wrapper for device and register name"
		return self.RegisterWrapper(self.bus, *dev[name], name = name)

	# The job is:
	# * Generate address decoders for each instance
	# * Instance a core for each instance
	#
	# Cores can be black boxes, as well. In this case, they are not
	# imported from the MMR module.

	def get_instance(self, name):
		for _, i in self.cache.items():
			if name == i.name:
				return i
		else:
			raise KeyError("Instance %s not found in parent" % name)

	def get_map(self, name, devno = None):
		devsel = self.device_enum[name]
		dev_offset = devsel << self.select_perio.stop
		if devno is not None:
			dev_index_bit = self.device_index[name]
			dev_offset += devno << dev_index_bit
		rmap = self._instances[name][0].register_map
		d = { k[0] : (i[0] + dev_offset, k[1]) for i, k in rmap.items() }
		return d

	def generate_toplevel_interface(self):
		d = {}
		for n, i in self.instances.items():
			_, io, num, param, _ = i

			if num > 1:
				for j in range(num):
					if io:
						p = io()
						d[n + '_%d_top' % j] = p
			else:
				if io:
					p = io()
					d[n + '_top'] = p

		return d


	def generate_selects(self, ce, bus):
		"Generate peripheral select (ce) signals"
		sel = {}

		perio_unit = bus.adr[self.select_perio] # Address portion for dev sel

		_logic = []
		for n, i in self.instances.items():
			num = i[2]
			index = self.device_enum[n]
			el = TernaryIf(perio_unit == index, ce, False)
			el.rename("ce_%s" % n)
			if num == 1:
				sel[n + '0'] = el
			else:
				idx = self.device_index[n]
				perio_index = bus.adr[idx]
				sel[n + 'ce' ] = el
				for j in range(num):
					t = TernaryIf(perio_index == j, el, False)
					t.rename('%s_idx%d' % (n, j))
					sel[n + "%d" % j] = t
		return sel

	@sensitivity.hdlmacro
	def bus_error(self, bus):
		"Override this HDL macro to signal a bus error"
		yield [ "No bus error" ]

	def get_portio(self, n):
		return self._instances[n][1]


	@block_component
	def mmr_decode(self,
		generator: PassThrough(MMRGenerator),
		clk : ClkSignal,
		reset : ResetSignal,
		ce	 : Bool,
		re	 : Bool,
		we	 : Bool,
		addr : Signal,
		data_in : Signal,
		data_out : Signal.Output,
		REGDESC : dict,
		**interface,
	):
		# We use a partially assigneable signal:
		
		idata = generator.PASignal(intbv()[len(data_out):])

		if self.READ_ASYNC:
			raddr = addr
			if self.DELAYED_WRITE_ADDRESS:
				waddr = addr.clone()

				@sensitivity.genprocess(clk, EDGE=clk.POS)
				def addr_register():
					yield [ waddr.set(addr) ]
			else:
				waddr = addr
		else:
			raddr = addr
			waddr = addr

		# Then generate the decoder from the register map description passed:
		wk = generator.generate_mmr_decoder(REGDESC, interface,
			clk, reset, ce, re, we, raddr, waddr, data_in, idata,
		   RESET_DEFAULTS = True, READ_ASYNC = self.READ_ASYNC)

		# @sensitivity.genprocess(clk, EDGE=clk.POS)
		# def drive():
		wires = [ data_out.wireup(idata) ]
				
		return locals()

	def create_decoder(self, name, iname, generator, j, signals, p, sel, mmr, strobe_we, strobe_re):

		# p.dout.rename(n + "%d" % j)
		# print("DEBUG Generator RUN", i[0])
		_ce = sel[name + '%d' % j]
		_mmr = mmr.clone("%s_%d" % (name, j))

		interface = { 'mmr' : _mmr }

		inst = self.mmr_decode(generator,
			clk = p.clk,
			reset = p.rst,
			ce = _ce,
			we = strobe_we,
			re = strobe_re,
			addr = p.addr,
			data_in = p.din,
			data_out = p.dout,
			REGDESC = generator.register_map,
			**interface
		)

		inst.rename_implementation(iname + '_decode')

		inst.rename("dec_%s_%d" % (name, j))
		self._inst[name + '_%d' % j] = inst # Store instances for later
		k = name + '_port%d' % j 
		signals[k] = p
		signals['mmr_%s_%d' % (name, j)] = _mmr # Save mmr port

		return inst


class DeviceClass(cyrite_factory.Module, DeviceBase):
	"""Device generator class
Generates the hardware structures for

- Address decoding for the local device register space
- Device index decoding

The device class creates stubs for the ip cores that are possibly
connected to the decoder. Those are actually connected/instanced upon
.configure().
"""

	# Here are few port descriptors:
	# These are part of the *fixed* core wrapper interface. They
	# must stick to this naming in particular.
	_iname = 'mmrbus'  # Memory mapped ctrl/stat interface
	_pio   = 'pio'	# Peripheral interface, routed to the top

	def __init__(self, name, arch, addr_shift = 0):
		self.bboxes = StubLib("local")
		super().__init__(name, arch)
		self.register_lib(self.bboxes)
		# self._io = {}
		self._inst = {}
		self.plugs = self.register_peripheral_implementation()
		self.plugged_instances = {}
		# Take over default instances
		self.instances = {}
		# self.lib = self # We point to ourselves for emission
		self.addr_shift = addr_shift
		self.acquired_instances = []

	def collect_unclaimed(self, td):
		pass

	def generate_perio_inst(self, name, interface):
		"""Generate a blackbox perio instance from the interface given.
This creates a stub for an existing core whose interface must
match the MMR Register API interface"""

		def _func(self, **x):
			pass


		if name in self.plugs:
			plug = self.plugs[name]

			pinst = plug(**interface)
			# We may get a blackbox from a plug again. In this case, pinst
			# is None.
			if pinst is not None:
				self.plugged_instances[name] = pinst

				# We have to manipulate the port direction for the
				# container alias in order to fake a .reverse() function,
				# unless the core properly specifies a .reverse() in the
				# interface (recommended practise).
				try:
					pio = pinst.interface.portdict[self._iname]
					pio[0].port._reverse = True
				except KeyError:
					pass
			inst = pinst
		else:
			f = _blackbox_named_component(name, _func)
			inst = f(self.bboxes, **interface)

		# At the same time, we check if we have support for a
		# the corresponding cyhdl modules.
		# The plug system may transform the interface

		return inst

	def configure(self, instances):
		"Configure instances. Basic version"
		for name, num in instances:
			self.instances[name] = self._instances[name]
				
	def create_instance(self, c, signals, param, mmr, inst_name, pname,
		cname = None):
		interface = {'clk' : signals['clk']}

		# Grab I/O descriptor:
		# iodesc = self.get_portio(inst_name)

		# Port I/O
		# MMR register interface:
		interface[self._iname] = mmr

		interface['reset'] = signals['reset']
		

		# Grab top level port I/O and map
		try:
			pio = c.interface.portdict[pname]
			interface[self._pio] = pio[0].port
		except KeyError as e:
			print("DEBUG NO I/O for port identifier %s" % pname, \
				inst_name, c.interface.portdict.keys())
			# This can happen with the sys core

		# Insert parameters:
		for pn, p in param.items():
			interface[pn] = p

		if cname is None:
			cname = inst_name

		inst = self.generate_perio_inst(cname + '_core', interface)

		return inst

	def create_core_stubs(self, signals, logic):
		for n, i in self.instances.items():
			_, io, num, _, param = i


			if num > 1:
				for j in range(num):
					mk = "mmr_%s_%d" % (n, j)
					mmr = signals[mk]

					pn = n + '_%d_top' % j
					inst = self.create_instance(c, signals, param, mmr, n, pn)
					inst.rename("core_%s_%d" % (n, j))

					logic += [ inst ]

			else:
				mk = "mmr_%s_0" % n
				mmr = signals[mk]

				pn = n + '_top'
				inst = self.create_instance(c, signals, param, mmr, n, pn)
				inst.rename("core_%s" % n)
				logic += [ inst ]


	def generate_mmr_perio(self, clk, reset, ce, bus, configuration = None):

		interface = self.generate_toplevel_interface()

		perio = self.mmr_perio(clk = clk, reset = reset, ce = ce, bus = bus,
			**interface)

		# Then overwrite the blackbox stubs via the
		# register_cores callback:
		for n, i in self.plugged_instances.items():
			self.bboxes.add_implementation(n, i)

		return perio, interface

	def build(self, target):
		#		inst.obj.ctx = self
		#		self.components.append(inst.name)
		#		self.cache[inst.name] = inst
		pass


