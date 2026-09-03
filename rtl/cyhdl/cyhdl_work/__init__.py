# Work library.
#
# All local modifications and configurations typically go in here
# during the prototyping phase / transition from VHDL to cyhdl.
#
from .rom52 import rom52
from .ssram import ssram
from .t51_ram import t51_ram


from myirl.library.portion import PASignal

from cyrite.library.soc import BF, Reg

from cyhdl import intbv, Signal

class RegisterSignal(PASignal):
	"""Custom registersignal built from a partially assigneable signal"""
	def __init__(self, name, d):
		bf = []
		lsb = 0
		msb = 0
		for k, n in d.items():
			msb += n -1
			bf.append(BF(k, msb, lsb))
			lsb += n
			msb += 1


		r = Reg(msb, bf)
		super().__init__(intbv()[msb:], name = name)
		self._reg = r

	def __getattr__(self, name):
		bf = self._reg.bfmap[name]
		return self[bf.as_slice()]

	
	def assign(self, **d):
		return self._reg.assign(self, **d)

from myirl.kernel.extensions import UserProxyType

class _intbv(intbv, UserProxyType):
	pass


from myirl.library.dontcare import DontCare

from myirl.kernel.sensitivity import Generator, genprocess_ctx
from myirl.kernel.sig import ConstSig


UNDEFINED8 = DontCare(8, "-")

class Decoder(Generator):
	"""Decoder generator"""
	class decoder_single_instance:
		pass

	def __init__(self, func, ns, addr, addr_r, wr):
		self.addr = addr
		self.addr_r = addr_r
		self.wr = wr
		self.logic = self._logic()
		self.ns = ns
		super().__init__(func)

	def __call__(self, context):

		_if = context.If

		n = self.addr.size()

		d = self.func()

		c = 0
		for k, i in d.items():
			a = getattr(self.ns, k)
			logic0 = context.If(self.addr == ConstSig(a, n)).Then (
				i[0].set(True)
			).Else(
				i[0].set(False)
			)
			logic1 = context.If(self.addr_r == ConstSig(a, n)).Then (
				i[1].set(self.wr)
			).Else(
				i[1].set(False)
			)


			@genprocess_ctx(self.addr, self.addr_r, self.wr)
			def lut_proc(context):
				 yield [ logic0, logic1 ]
			
			lut_proc.rename("proc_%s" % k)
			c += 1
			self.add_instance(lut_proc)


def decoder_generator(ns, addr, addr_r, io_wr):

	def proc_deco(func):
		return Decoder(func, ns, addr, addr_r, io_wr)

	return proc_deco



