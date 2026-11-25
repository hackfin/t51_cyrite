# T51 cyrite SoC example

The t51 is a legacy VHDL project, I believe the original authors are
Daniel Wallner and Andreas Voggeneder. It was up-ported to cyhdl to
create 8051 based SoCs and co-simulation environments for legacy platforms
and 8051 derivatives being no longer produced.

It is targeted at developers familiar with Linux, Python, C and some
hardware design language who might want to trace functionality down to
the core.

The particular goal of this setup:
* Emit VHDL or Verilog sources for synthesis
* Co-Simulate an virtualized chip as executable against mockup
  hardware constructs via Python co-routines

This README will be short on the technical side, as various AI agents
will be able to help you with understanding the code or on how to run docker
containers on your particular OS. Also, some AI was involved in porting
the existing VHDL code, but not in writing this README (apart from ASCII
art generation).

## Usage

Assuming you're a linux user with a working docker service, you are ready
to go with the scripts in `recipes`.
If not, you might either:
* Consult AI how to get Docker running on your platform
* Use an online service where you can run docker containers
* Use the Jupyter notebook binder service below

### JupyterLab notebook on mybinder.org

You can run the container online as virtual machine with a Jupyter lab
instance that allows you to run Python snippets interactively.
In future, this might serve more as a tutorial than this README.

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/hackfin/t51_cyrite/cyhdlport?urlpath=lab/tree/index.ipynb)

### Local (Linux host) execution

For compiling the supplied example code, you might want to install sdcc and
objcopy:

```
sudo apt-get install sdcc binutils
```

Then you can use the Make rules.

1. Build firmware, hex file and verilog output: `make all init`
2. Run the co-simulation: `make run`
3. Clean up the build: `make clean`

When you make changes to the firmware, you need to clean the build
before running again, as a true hardware ROM is generated and hence
recompilation is required. Ad-hoc loading into a pseudo-ROM is not supported
in this setup.

## Implementation details

The original VHDL source was translated into the **cyhdl** Python dialect which
is syntactically close to MyHDL. This hierarchy has a similar structure as
the corresponding VHDL project, with some modifications made to turn it into
a class structure for more flexibility with respect to testing and
configureability. From this design, we emit Verilog for yosys in this case
and compile it into an executable virtualized hardware model.

More details about differences to MyHDL and coding guidelines are found in the
[cyrite.howto](https://github.com/hackfin/cyrite.howto.git)


## Co-Simulation Introduction

The reason for the cyrite port was the requirement to build a mockup
simulation for 8051 based hardware with a firmware image without sources
(although AI could be used to reverse it).

Apart from a classic HDL simulation which is mostly deterministic, or
allows only simulator specific hardware-in-the-loop setups (for instance
VPI or VHPI that talk to external processes using virtual interfaces),
a cyrite featured testbed allows you to loop in just anything at any time via
Python. This works using a simple thin layer between a rudimentary Python
simulator and a compiler-featured backend such as CXXRTL.

The cyrite ecosystem with its co-simulation functionality is provided
as external docker container. To elaborate the cyhdl description into a
target language, various scripts are provided that start the docker container
on supported systems (Debian based or other Linux distributions).

The basic simulation example provided in `example/soc.py` demonstrates
on how a compiled virtual hardware model runs alongside Python with
cycle accurate scheduling, meaning that a python co-routine can interact
with the hardware.

In the test bench `testbench52` you will for instance find several
sequences that run virtually in parallel with each other. The cyrite simulation
'scheduler' handles all yield based wait cycles in a similar way as the
built-in simulation feature of the MyHDL concept.

The `main()` sequence has the control over the entire simulation duration.
Other sequences create continuous stimuli, the `pipeio_handling()` routine
in particular listens to pipe events that are triggered by writing to
the UART SFRs from the hello example.

## Emitting HDL

This command emits a set of Verilog files:

```
	sh recipes/proj_verilog.sh example/firmware/build/hello.bin  
```

This `.bin` file is a binary image of the entire 8051 ROM. In the given example
configuration, it will build a ROM description with this content.
A CoSimulation variant on the other side may allow to run a virtual ROM
implementation that can be read out/written using a backdoor channel.

If the docker container is not present, it is pulled from a repository
first. This may take some time. If your machine is unable to run a docker
container, you may as well play with it online from inside a browser.

This may be elaborated at a later stage. For now, you might have to do
your own research which online docker playground fits best.

## System on Chip concept

The 8051 family uses special function registers (SFRs) to control its
peripherals. These are a flat register map in the internal 128 byte page
above 0x80 that are in this implementation particularely decoded using
the cyrite MMR generator library.

The MMR bulk signal with .read, .write. and .select children route to each
relevant peripheral IP core of the `mmr_perio` subsystem.

All address decoding logic is created from the register map description
given in the SFR map definition `sfr8051_<arch>.py`.


```
             +----------------------+
             |       8051 CPU       |
             |                      |
             |--------------------- |
             |       SFR MAP        |
             +----------+-----------+
                        |
              =====  MMR/SFR BUS  ==============
              |          |          |          |
         +----+---+ +----+---+ +----+---+ +----+---+
         |  GPIO  | |  UART  | |  SPI   | |  TIMER |
         |   IP   | |   IP   | |   IP   | |   IP   |
         +----+---+ +----+---+ +----+---+ +----+---+
              |          |          |          |
           LEDs /     TX / RX    MOSI/MISO    IRQ
           Buttons               SCLK / CS
```

Connecting configureable IP to the CPU core is part of the
architectural description of a `Device` class, which handles
configuration of various sorts. On the other hand, a `Factory` type class
handles the platform architecture and possible I/O with externally
co-simulated devices.

Please note an important limitation: The SFR generator coming with this
release implements volatile registers in a way not fully compatible with
legacy 8051 peripherals. This means that a particular scheme must be followed
for programming.

### Naming and IP cores

SFRs break down to bit fields in the SFR description. A child signal is
created per bitfield, hence the golden rule for 8051 SFR maps applies:

**Bitfields must have unique names**

If no bit field definitions are present in a register, the register identifier
is used.

When external IP cores are included that have particular control and status
signals, you may have to wire them manually inside the `.create_<core>`
methods of the factory.

## Simulation

The associated default docker container features the conversion to
Verilog and the simulation with the ICARUS VERILOG simulator.
Plus, it emits directly to yosys via Verilog and hence compiles synthesizeable
constructs into a CXXRTL module that can be co-simulated against.

The basic simulation features simply emit an example setup into a virtual
hardware and run some stimuli.

### HDL simulation

For a HDL target, the unit under test and the test bench are emitted to HDL.
The UUT is here the synthesizeable part, the test bench a sequence that
works in simulation only.

This example is not yet written.

### Co-Simulation

Using the CXXRTL back end, a virtual UUT is run against a true Python
test bench that can access external tools, draw a trace, communicate with
a web browser through web sockets, etc. Using a factory, a multiple
target simulation can be designed that uses simple basic stimuli in the HDL
variant, but more complex I/O to virtual interfaces using the Co-Simulation
target. CXXRTL allows to plug in any sort of blackbox hardware that does
something behind a C++-API, for instance:

* A virtual UART talking via a pipe to a host process
* A virtual framebuffer simulating a display

This first basic example does not make use of any virtual interfaces. When
running this script, the HDL description is transpiled to Verilog,
read into yosys and compiled into a CXXRTL object:

```
	sh recipes/run.sh example/firmware/build/hello.bin
```

The result is a `*.vcd` file containing a large wave trace, plus a
DLL in `runtime/`. Since the source directory is mounted locally,
the `*.so` file is persistent, hence not recompiled unless specified
explitely. If you make changes to the actual core, you need to erase
the `runtime/*.so`. However, changes to the test bench or co-routines
run in the Python domain, hence no recompilation is needed.

## Developer area

Here are a few notes on how to program the CPU in order to generate new
firmware or extend it using custom SFRs.

### Compiling code

There might be a need to re-compile existing code. There are various
compilers still being maintained for the 8051 architecture, such as
Keil and SDCC. Since the initial goal of this project however was a mock up
only, there are no "supply packages" coming with this code.

However, you will find an `example/firmware` directory providing a hello
world that would work on a basic 8051. It should output a "Hello World"
on the UART mockup example, plus toggle a P0 pin using the timer interrupt.

After you have run the example, a `*.vcd` trace will be left for you
in the current output directory. You can view the trace using GTKWave:

```
gtkwave output/t51sim.vcd example/hello.sav
```

This will provide you with the means to inspect all synthesized signals
down to the core.

One particular point though: The SFR description would allow to emit
headers to C or any other programming language. This is outside the scope
of this project, but is covered by a cyrite extension being mostly
compatible with the XML concept from the
[MaSoCist project](https://github.com/hackfin/MaSoCist).

### Derival and Factories

The typical design construct used is represented by a `Factory` class. It
contains testbench, top level unit under test and possibly some target
synthesis rules. Upon construction, it is passed an `Architecture`,
which in most cases is simply a HDL simulator (included here: Icarus Verilog).

Let's list a few entry points and hints on how to extend the SFR map or
create a new 8051 derivate.

1) The `T51_Base` class contains the actual implementation of the T51
   cyrite port. It implements the basic requirements of SFRs from the 8051
   specification, plus adds a Monitor structure for later extension.

2) The `.soc_t8052NG` block component extends the core by some logic:
   * External memory and ROM handling
   * Wishbone bus towards outside
   * The SFR interface which is created during instance of the derived
     SoC class

3) The general idea behind this structure is:
   * Never change anything in a super class unless it really fixes a bug
   * Add features in derived classes only

Improvements and suggestions welcome.

### Open issues and pitfalls

This is mostly considered a hack, not a extensively verified setup.
Parts of it have been co-verified against their HDL implementation just to
see if they are doing the same. These are not included in this project
due to tool dependencies.
Since the main purpose is a simulation mock up, you might not want to use the
generated hardware description for any safety relevant project.

Moreover, the 0xa5 opcode does not allow looping in user defined handlers.
This will not be addressed, as there is no intention to use 8051 for new
projects, is it?

Now, there is another tricky detail: The previous SFR generator had only
limited support for VOLATILE type register bits, meaning it would only
allow W1C (write-one-to-clear) or W0C behaviour. However, original
8051 hardware would show different behaviour.

This has a particular impact on program flow. See `PITFALL` in
`example/firmware/main.c`. In this setup, we use custom setters, even
though volatile bits are marked as `W0C`.

