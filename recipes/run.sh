#!/bin/sh

IMAGE="hackfin/cyrite:slim-0.4.rc0"

PROJDIR=/home/cyrite/proj
T51=`pwd`
PYTHONPATH=$T51
OUTPUT=output

# Created libraries will be persistent in runtime/
[ -e runtime ] || mkdir runtime && chmod o+rw runtime
[ -e build ] || mkdir build && chmod o+rw build

docker run -it --rm -v$T51:$PROJDIR \
	-w $PROJDIR \
	-e PYTHONPATH=$PYTHONPATH \
	-e LD_LIBRARY_PATH=/usr/lib/yosys \
	$IMAGE \
	python3 $PROJDIR/example/convert.py cxxrtl $1 $OUTPUT
