from cyhdl import Signal, intbv

Bool = Signal.Type(bool)
Nibble = Signal.Type(intbv()[4:])
Byte = Signal.Type(intbv()[8:])
Addr8 = Signal.Type(intbv()[8:])
Addr16 = Signal.Type(intbv()[16:])
Word   = Signal.Type(intbv()[32:])
Bit4 = Nibble
