NVCC = /usr/local/cuda-6.0/bin/nvcc
FLAGS = -lm -g -Wall -O3 -funroll-loops
EXE = correlate
FILE = x64correlator.c

all: $(EXE)

correlate: $(FILE)
	gcc $(FILE) -o $(EXE) $(FLAGS)

run: $(EXE)
	./correlate data/OFF.bin

debug: $(EXE)
	ddd correlate -x dddinit

.PHONY: run all debug clean

