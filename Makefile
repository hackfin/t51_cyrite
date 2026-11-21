clean:
	-rm runtime/*.so
	-rm output/rom52.hex
	$(MAKE) -C example/firmware clean

init: all
	sh recipes/proj_verilog.sh example/firmware/build/hello.bin

all:
	$(MAKE) -C example/firmware all


run: all
	sh recipes/run.sh example/firmware/build/hello.bin



.PHONY: run
