# Dockerfile for building ENCIDER (KLEE 1.4.0 fork, LLVM 3.8) -- UNTESTED: not yet built.
# Derived from ENCIDER's INSTALL.txt. The Dockerfile bundled in ENCIDER/klee/ is upstream
# KLEE's (Ubuntu 14.04, LLVM 3.4) and does not match ENCIDER's LLVM 3.8 requirement.
FROM ubuntu:16.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl ca-certificates libcap-dev git cmake libncurses5-dev \
      python-minimal python-pip python3 python3-pip unzip bison flex \
      libtcmalloc-minimal4 libgoogle-perftools-dev libsqlite3-dev zlib1g-dev \
      clang-3.8 llvm-3.8 llvm-3.8-dev llvm-3.8-tools \
      z3 libz3-dev \
    && rm -rf /var/lib/apt/lists/*
# NOTE: INSTALL.txt asks for Z3 >= 4.4; confirm the Ubuntu 16.04 z3 package version
# (`z3 --version`) and build Z3 from source if it is older. [TBD]

RUN pip3 install tabulate lit==0.5.0   # lit version pinned for Python 3.5 [TBD: verify]

# Pin the exact ENCIDER commit audited in Section VI-D of the paper.
RUN git clone https://github.com/sysrel/ENCIDER.git /opt/ENCIDER \
 && cd /opt/ENCIDER && git checkout 2e5408387fa48923128bae73529401ff34e70937

# ENCIDER's CMake project lives in the klee/ subdirectory of the repository.
RUN mkdir /opt/encider_build && cd /opt/encider_build \
 && cmake -DENABLE_SOLVER_Z3=ON -DENABLE_SOLVER_STP=OFF \
          -DENABLE_UNIT_TESTS=OFF -DENABLE_SYSTEM_TESTS=OFF \
          -DENABLE_POSIX_RUNTIME=OFF -DENABLE_TCMALLOC=ON \
          -DLLVM_CONFIG_BINARY=/usr/bin/llvm-config-3.8 \
          -DLLVMCC=/usr/bin/clang-3.8 -DLLVMCXX=/usr/bin/clang++-3.8 \
          /opt/ENCIDER/klee \
 && make -j"$(nproc)"

ENV ENCIDER=/opt/encider_build/bin/klee
WORKDIR /work
