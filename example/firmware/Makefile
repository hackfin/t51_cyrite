# Makefile to build hello.bin
#
# Run
# > make all
#
SDCC ?= sdcc
PORT ?= mcs51
MODEL ?= small
BUILD_DIR ?= build
TARGET := $(BUILD_DIR)/hello
OBJCOPY ?= objcopy
DIS51 ?= d52

.PHONY: all clean disasm

all: $(TARGET).bin

$(BUILD_DIR):
	mkdir -p $@

$(TARGET).ihx: main.c | $(BUILD_DIR)
	$(SDCC) -m$(PORT) --model-$(MODEL) -o $@ $<

$(TARGET).bin: $(TARGET).ihx
	$(OBJCOPY) -I ihex -O binary --gap-fill 0xFF --pad-to 0x10000 $< $@

disasm: $(TARGET).d52

$(TARGET).d52: $(TARGET).ihx
	d52 -t -d -h $<

clean:
	rm -rf $(BUILD_DIR) *.asm *.ihx *.lk *.lst *.map *.mem *.rel *.rst *.sym

