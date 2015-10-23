#!/usr/bin/python3

#    flifcrush - tries to reduce FLIF files in size
#    Copyright (C) 2015  Matthias Krüger

#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 1, or (at your option)
#    any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston MA  02110-1301 USA


import subprocess
import sys
import os

__author__ = 'Matthias "matthiaskrgr" Krüger'

# check for flif
flif_binary = ""
try:
	flif_path = os.environ['FLIF']
	if os.path.isfile(flif_path):
		flif_binary = flif_path
except KeyError: # env var not set, check if /usr/bin/flif exists
	if (flif_binary == ""):
		if (os.path.isfile("/usr/bin/flif")):
			flif_binary = "/usr/bin/flif"
		else:
			print("Error: no flif binary found, please use 'export FLIF=/path/to/flif'")
			quit()


 # check if we have an input file
try:
	INFILE=sys.argv[1]
	print(INFILE)
except IndexError:
	print("Error: no input file given.")
	quit()

size_orig = os.path.getsize(INFILE)


range_N = 10 # default: 3 // try: 0-20
range_S = 1000 # default: 50  // try: 1-200
range_M = 1000 # default: 5461*8*5 ? // try 
range_D = 1000 # default: // try  1-200

giveUp_N = 4
giveUp_SMD= 100

size_increased_times=0
_range=10
size_best = -1337
for N in list(range(range_N)):
	proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(N), INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
	if (N == 0): #first run, initialize
		N_best=0
		output_best = proc.stdout.read()
		size_best = sys.getsizeof(output_best)
		print("run {run}, size {size} b, better than before which was {size_orig} b ({size_change} b)".format(run=N, size=size_best, size_orig=size_orig, size_change=size_best-size_orig, minusperc="1"))
		continue

	output = proc.stdout.read()
	size = sys.getsizeof(output)


	if ((size_best > size) or (size_best == -1337)): # new file is smaller
		size_increased_times = 0
		output_best = output

		print("run {run}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b)".format(run=N, size=size, run_best=N_best, size_best=size_best, size_change=size_best-size))
		N_best = N
		size_best = size
	else:
		print("run {run}, size {size} b".format(run=N, size=size))
		size_increased_times += 1
		if (size_increased_times == giveUp_N): # if size increases 4 times in a row, break
			size_increased_times = 0
			break; # do NOT quit, we need to write the file






print("S")

size_orig = size_best

for S in list(range(1, range_S, 1)):
	proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(N_best),'-S', str(S),  INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
	if (S == 1): #first run, initialize
		#size_orig=size_best # need new value here
		S_best=1
		#output_best = proc.stdout.read()
		#size_best = sys.getsizeof(output_best)
		print("run S {run}, size {size} b, better than before which was {size_orig} b ({size_change} b)....".format(run=S, size=size_best, size_orig=size_orig, size_change=size_best-size_orig, minusperc="1"))
		continue

	output = proc.stdout.read()
	size = sys.getsizeof(output)


	if (size_best > size): # new file is smaller
		size_increased_times = 0
		output_best = output

		print("run S {run}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b)".format(run=S, size=size, run_best=S_best, size_best=size_best, size_change=size_best-size))
		S_best = S
		size_best = size
	else:
		print("run S {run}, size {size} b".format(run=S, size=size))
		size_increased_times += 1
		if (size_increased_times == giveUp_SMD): # if size increases 4 times in a row, break
			size_increased_times = 0
			break; # do NOT quit, we need to write the file



size_best = sys.getsizeof(output_best)




print("M")

size_orig = size_best

for M in list(range(1, range_M, 1)):
	proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(N_best),'-S', str(S_best), '-M', str(M),  INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
	if (M == 1): #first run, initialize
		#size_orig=size_best # need new value here
		M_best=1
		#output_best = proc.stdout.read()
		#size_best = sys.getsizeof(output_best)
		print("run M {run}, size {size} b, better than before which was {size_orig} b ({size_change} b)...".format(run=M, size=size_best, size_orig=size_orig, size_change=size_best-size_orig, minusperc="1"))
		continue

	output = proc.stdout.read()
	size = sys.getsizeof(output)


	if (size_best > size): # new file is smaller
		size_increased_times = 0
		output_best = output

		print("run M {run}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b)".format(run=M, size=size, run_best=M_best, size_best=size_best, size_change=size_best-size))
		M_best = M
		size_best = size
	else:
		print("run M {run}, size {size} b".format(run=M, size=size))
		size_increased_times += 1
		if (size_increased_times == giveUp_SMD): # if size increases 4 times in a row, break
			size_increased_times = 0
			break; # do NOT quit, we need to write the file



size_best = sys.getsizeof(output_best)




print("D")

size_orig = size_best

for D in list(range(1, range_D, 1)):
	proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(N_best), '-S', str(S_best), '-M', str(M_best), '-D', str(D),  INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
	if (D == 1): #first run, initialize
		#size_orig=size_best # need new value here
		D_best=1
		#output_best = proc.stdout.read()
		#size_best = sys.getsizeof(output_best)
		print("run D {run}, size {size} b, better than before which was {size_orig} b ({size_change} b)...".format(run=D, size=size_best, size_orig=size_orig, size_change=size_best-size_orig, minusperc="1"))
		continue

	output = proc.stdout.read()
	size = sys.getsizeof(output)


	if (size_best > size): # new file is smaller
		size_increased_times = 0
		output_best = output

		print("run D {run}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b)".format(run=D, size=size, run_best=D_best, size_best=size_best, size_change=size_best-size))
		D_best = D
		size_best = size
	else:
		print("run D {run}, size {size} b".format(run=D, size=size))
		size_increased_times += 1
		if (size_increased_times == giveUp_SMD): # if size increases 4 times in a row, break
			size_increased_times = 0
			break; # do NOT quit, we need to write the file





# write final best file

OUTFILE="/tmp/out_final.flif"
with open(OUTFILE, "r+b") as f:
	f.write(output)
	f.close


size_flif = os.path.getsize(OUTFILE)
print("reduced from {size_orig} to {size_flif} ( {size_diff})".format(size_orig = os.path.getsize(INFILE), size_flif=size_flif, size_diff =size_flif - size_orig))
