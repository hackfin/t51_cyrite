ARG IMAGE="hackfin/cyrite:slim-0.4.rc0"

FROM $IMAGE as base

ARG MY_USER="cyrite"
ENV HOME /home/${MY_USER}

USER root

RUN apt-get update -qq \
	&& apt-get -y install --no-install-recommends \
	sdcc

RUN apt-get purge -y --auto-remove ghdl iverilog \
    && rm -rf /var/lib/apt/lists/*


COPY --chown=${MY_USER}:users ./ ${HOME}/t51_cyrite
COPY --chown=${MY_USER}:users ./doc/index.ipynb ${HOME}

USER ${MY_USER}

ENV PATH "$PATH:${HOME}/.local/bin"
ENV LD_LIBRARY_PATH=/usr/lib/yosys

WORKDIR ${HOME}

