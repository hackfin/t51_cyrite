#!/bin/sh

IMAGE="hackfin/cyrite:slim-0.4.rc0"

PROJDIR=/home/cyrite/proj
T51=`pwd`
PYTHONPATH=$T51
PROJ="$T51/example/convert.py verilog"
OUTPUT=output

[ -e $OUTPUT ] || mkdir $OUTPUT && chmod o+rw $OUTPUT

docker run -it --rm -v$T51:$PROJDIR \
	-w $PROJDIR \
	-e PYTHONPATH=$PYTHONPATH \
	-e LD_LIBRARY_PATH=/usr/lib/yosys \
	$IMAGE \
	python3 $PROJDIR/example/convert.py verilog $1 $OUTPUT
