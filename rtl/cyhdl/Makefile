# Conversion makefile VHDL -> cyhdl
include ~/src/masoc/convert.mk

CURDIR = $(shell pwd)

%.py: ../vhdl/%.vhd
	$(V2C) $< -d -w $(CURDIR)/work/work-obj93.cf

%.py: %.vhdl
	$(V2C) $< -d -w $(CURDIR)/work/work-obj93.cf

%_Pack.py: ../vhdl/%_Pack.vhd
	$(V2C) $< -d -l -w $(CURDIR)/work/work-obj93.cf

%.py: ../../bench/vhdl/%.vhd
	$(V2C) $< -d -w $(CURDIR)/work/work-obj93.cf

NOT_CONVERTING = T51_RAM

MODULES = \
				SSRAMX    T51_Pack  T51_TC01  T8032 \
				ROM52_BASIC  T51_ALU   T51_Port  T51_TC2   T8052 \
				SSRAM2       T51_Glue  T51_UART \
				SSRAM        T51_MD    T51s      T51

CYHDLFILES = $(MODULES:%=%.py)


all: $(CYHDLFILES)
				
