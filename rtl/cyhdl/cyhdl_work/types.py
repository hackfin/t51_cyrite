# common used work types:

from cyhdl import *

Bool = Signal.Type(bool)
Byte = Signal.Type(intbv()[8:])
Nibble = Signal.Type(intbv()[4:])
Addr16 = Signal.Type(intbv()[16:])
Word = Signal.Type(intbv()[16:])

from cyrite.auxiliaries.xhdl import vhdlaux as vh

IOPort = Byte
