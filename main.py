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



global arr_index
global progress_array
arr_index = 0
progress_array=["|", "/", "-", "\\",]
#progress_array=[".", "o", "0", "O", "O", "o", "."]


def showActivity():
	global arr_index
	arr_index = arr_index + 1
	if (arr_index == len(progress_array)):
		arr_index = 0
	print(progress_array[arr_index], end="\r",flush=True)
	return


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

# avoid undecl var:
N=0
S=0
M=0
D=0


range_N = 10   # default: 3 // try: 0-20
range_S = 1000 # default: 40  // try: 1-200
range_M = 1000 # default: 30  // try: 1-200
range_D = 1000 # default: 50  // try  1-200

giveUp_N = 4
giveUp_S = 100
giveUp_D = 100
giveUp_M = 100


size_increased_times_N=0
size_increased_times_D=0
size_increased_times_M=0
size_increased_times_S=0

size_best = -1337
count= 0
# MANIAC learning          -r, --repeats=N          MANIAC learning iterations (default: N=3)
for N in list(range(range_N)):
	proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(N), INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
	count +=1
	if (N == 0): #first run, initialize
		N_best=0
		output_best = proc.stdout.read()
		size_best = sys.getsizeof(output_best)
		print("N {N}, S {S}, M {M},D {D}, size {size} b, better than before which was {size_orig} b ({size_change} b)".format(N=N, S=S, M=M, D=D, size=size_best, size_orig=size_orig, size_change=size_best-size_orig, minusperc="1"))
		continue

	output = proc.stdout.read()
	size = sys.getsizeof(output)

	if ((size_best > size) or (size_best == -1337)): # new file is smaller
		size_increased_times_N = 0
		output_best = output
		print("N {N}, S {S}, M {M},D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b)".format(N=N, S=S, M=M, D=D, size=size, run_best=N_best, size_best=size_best, size_change=size_best-size))
		N_best = N
		size_best = size


		# -S, --split-threshold=T  MANIAC tree growth control (default: T=40)
		size_orig = size_best
		size_increased_times_S = 0
		for S in list(range(1, range_S, 1)):
			proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(N_best),'-S', str(S),  INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
			count +=1
			if (S == 1): #first run, initialize
				#size_orig=size_best # need new value here
				S_best=1
				#output_best = proc.stdout.read()
				#size_best = sys.getsizeof(output_best)
				print("N {N}, S {S}, M {M},D {D}, size {size} b, better than before which was {size_orig} b ({size_change} b)....".format(N=N, S=S, M=M, D=D, size=size_best, size_orig=size_orig, size_change=size_best-size_orig, minusperc="1"))
				continue

			output = proc.stdout.read()
			size = sys.getsizeof(output)


			if (size_best > size): # new file is smaller
				size_increased_times_S = 0
				output_best = output

				print("N {N}, S {S}, M {M},D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b)".format(N=N, S=S, M=M, D=D, size=size, run_best=S_best, size_best=size_best, size_change=size_best-size))
				S_best = S
				size_best = size

				size_best = sys.getsizeof(output_best)

				#-M, --min-size=M         MANIAC leaves post-pruning (default: M=50)
				size_orig = size_best
				usize_increased_times_M = 0
				for M in list(range(1, range_M, 1)):
					proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(N_best),'-S', str(S_best), '-M', str(M),  INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
					count +=1
					if (M == 1): #first run, initialize
						#size_orig=size_best # need new value here
						M_best=1
						#output_best = proc.stdout.read()
						#size_best = sys.getsizeof(output_best)
						print("N {N}, S {S}, M {M}, D {D}, size {size} b, better than before which was {size_orig} b ({size_change} b)...".format(N=N, S=S, M=M, D=D, size=size_best, size_orig=size_orig, size_change=size_best-size_orig, minusperc="1"))
						continue

					output = proc.stdout.read()
					size = sys.getsizeof(output)

					if (size_best > size): # new file is smaller
						size_increased_times_M = 0
						output_best = output

						print("N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b)".format(N=N, S=S, M=M, D=D, size=size, run_best=M_best, size_best=size_best, size_change=size_best-size))
						M_best = M
						size_best = size

						size_best = sys.getsizeof(output_best)

						#   -D, --divisor=D          MANIAC node count divisor (default: D=30)
						size_increased_times_D = 0
						size_orig = size_best

						for D in list(range(1, range_D, 1)):
							proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(N_best), '-S', str(S_best), '-M', str(M_best), '-D', str(D),  INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
							count +=1
							if (D == 1): #first run, initialize
								#size_orig=size_best # need new value here
								D_best=1
								#output_best = proc.stdout.read()
								#size_best = sys.getsizeof(output_best)
								print("N {N}, S {S}, M {M}, D {D}, size {size} b, better than before which was {size_orig} b ({size_change} b)...".format(N=N, S=S, M=M, D=D, size=size_best, size_orig=size_orig, size_change=size_best-size_orig, minusperc="1"))
								continue

							output = proc.stdout.read()
							size = sys.getsizeof(output)


							if (size_best > size): # new file is smaller
								size_increased_times_D = 0
								output_best = output

								print("N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b)".format(N=N, S=S, M=M, D=D, size=size, run_best=D_best, size_best=size_best, size_change=size_best-size))
								D_best = D
								size_best = size
							else: # D
								#print("run D {run}, size {size} b".format(run=D, size=size))
								size_increased_times_D += 1
								showActivity() # print that we are still running
								if (size_increased_times_D == giveUp_D): # give up if we didn't make many progress for so many times
									size_increased_times = 0
									break;

					else: # M
						#print("run M {run}, size {size} b".format(run=M, size=size))
						size_increased_times_M += 1
						showActivity()
						if (size_increased_times_M == giveUp_M):
							size_increased_times_M = 0
							break;

			else: # S
				#print("run S {run}, size {size} b".format(run=S, size=size))
				size_increased_times_S += 1
				showActivity()
				if (size_increased_times_S == giveUp_S):
					size_increased_times_S = 0
					break;

	else: # N
		#print("run {run}, size {size} b".format(run=N, size=size))
		size_increased_times_N += 1
		showActivity()
		if (size_increased_times_N == giveUp_N):
			size_increased_times_N = 0
			break;


# write final best file

OUTFILE="/tmp/out_final.flif"
with open(OUTFILE, "w+b") as f:
	f.write(output_best)
	f.close

size_flif=os.path.getsize(OUTFILE)
size_orig=os.path.getsize(INFILE)
print("reduced from {size_orig} to {size_flif} ( {size_diff})".format(size_orig = os.path.getsize(INFILE), size_flif=size_flif, size_diff =size_flif - size_orig))
print("called flif " + str(count) + " times")
