from cyhdl import *

import sys
sys.path.insert(0, ".")


from cyrite.simulation import icarus

from myirl.library.architecture import Architecture


from t51.example.soc import MyPlatform, MyPlatformCosim

class MyArch(Architecture):
	def __init__(self, lang = "verilog"):
		if lang == "verilog":
			self.sim_class = icarus.ICARUS
			self.target_class = targets.verilog.Verilog
		else:
			raise ValueError("Unknown target specification", lang)



def test_build(arch, firmware = None, output_dir = "/tmp"):

	try:
		m = MyPlatform("mysoc", arch, binary = firmware)
	except IndexError as e:
		e.args += ("Expects firmware image as argument", )
		raise e

	m.build(output_dir)
		

if __name__ == "__main__":
	from yosys.simulator import CXXRTLVerilog

	print("DEBUG PATH", sys.path)

	if sys.argv[1] == "cxxrtl":
		arch = CXXRTLVerilog
		m = MyPlatformCosim("module", CXXRTLVerilog, sys.argv[2])
		m.build("/tmp")
	else:
		arch = MyArch(sys.argv[1])
		test_build(arch, sys.argv[2], sys.argv[3])
