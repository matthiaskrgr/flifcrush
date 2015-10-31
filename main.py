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
from PIL import Image
from collections import Counter
import argparse

__author__ = 'Matthias "matthiaskrgr" Krüger'


parser = argparse.ArgumentParser()
parser.add_argument("infile", help="file to be converted to flif", type=str)
parser.add_argument("-i", "--interlace", help="enable interlacing (default: false)", action='store_true')
parser.add_argument("-d", "--debug", help="print output of all runs at end", action='store_true')
args = parser.parse_args()

if args.debug:
	DEBUG=True
else:
	DEBUG=False

INFILE=args.infile
if args.interlace:
	interlace_flag="--interlace"
else:
	interlace_flag="--no-interlace"


output_best="none"
global arr_index
global progress_array
arr_index = 0
#progress_array=["|", "/", "-", "\\",]
#progress_array=[".", "o", "0", "O", "O", "o", "."]
progress_array=[" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▁"]
arrlen=len(progress_array)

# prints activity indicator (some kind of ascii animation)
def showActivity():
	#return
	global arr_index
	arr_index+=1
	if (arr_index == arrlen):
		arr_index = 0
	print(progress_array[arr_index] + " " + str(count) + " N" + str(N) + " S" + str(S) + " M" + str(M) + " D" + str(D) + ", " + "size: " + str(size_new) + " b        ", end="\r",flush=True)




# make sure we know where flif binary is
flif_binary = ""
try:
	flif_path = os.environ['FLIF']
	if os.path.isfile(flif_path):
		flif_binary = flif_path
except KeyError: # env var not set, check if /usr/bin/flif exists
	if (flif_binary == ""):
		if (os.path.isfile("/usr/bin/flif")):
			flif_binary = "/usr/bin/flif"
		elif (os.path.isfile("/usr/share/bin/flif")):
			flif_binary = "/usr/share/bin/flif"
		else:
			print("Error: no flif binary found, please use 'export FLIF=/path/to/flif'")
			quit()

#output some metrics about the png that we are about to convert

im=Image.open(INFILE)
img=[] # will contain pixel data
for px in (im.getdata()):
	img.append(px)

unique_colors = len(Counter(img).items()) # get number of unique pixels
size_orig = os.path.getsize(INFILE) # size of the png
print("{inf}: {x}x{y}, {px} pixels, {uc} unique colors, {b} bytes".format(inf=INFILE, x=im.size[0], y=im.size[1], px=im.size[0]*im.size[1], uc=unique_colors, b=size_orig))






# how many max attempts (in "best" case)?
range_N = 20   # default: 3 // try: 0-20
range_S = 600 # default: 40  // try: 1-100
range_M = 600 # default: 30  // try: 1-100
range_D = 5000 # default: 50  // try  1-100


# if we did this many attempts without getting better results, give up
giveUp_N = 5
giveUp_S = 100
give_up_after = 200
size_increased_times_N = 0
size_increased_times_N_first = 0 # TODO: refactor this


#defaults:
N = 0 # avoid undecl var
S = 40 # must at least be 1
M = 50 # can be 0
D = 30 # must at least be 1


count = 0 # how many recompression attempts did we take?
best_count = 0 # what was the smallest compression so far?

size_new = size_best = os.path.getsize(INFILE)


if (DEBUG):
	debug_array=[]
	debug_dict = {'Nr': '', 'N':'', 'S':"", 'M':"", 'D':"", 'size':""}




first_best_N=best_N_first=0
# MANIAC learning          -r, --repeats=N          MANIAC learning iterations (default: N=3)
for N in list(range(0, range_N)):
	proc = subprocess.Popen([flif_binary, '-r', str(N), INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
	count +=1

	output = proc.stdout.read()
	size_new = sys.getsizeof(output)

	if (DEBUG):
		debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'size': size_new}])

	if (((size_best > size_new) or (((count==1) and (size_new < size_orig))))): # new file is smaller
		size_increased_times_N_first = 0 # reset break-counter
		output_best = output
		print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best="orig" if (count == 1) else best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
		best_count=count
		size_best = size_new
		best_N_first=N
		arr_index = 0
	else:
		size_increased_times_N_first += 1
		showActivity()
		if (size_increased_times_N_first >= giveUp_N):
			break; # break out of loop, we have wasted enough time here

best_N = best_N_first 


#order: n, s, d, m, n
N = best_N # was: 1 for performance
# TODO: make this -O0 flag

size_increased_times = 0
good_S_M_D=[S,M,D]

# if N== 0 / no maniac tree, skip the rest
if N != 0:
	for S in list(range(1, range_S, 1)):
		proc = subprocess.Popen([flif_binary,'-r', str(N), '-S', str(S),  INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
		count +=1
		output = proc.stdout.read()
		size_new = sys.getsizeof(output)

		if (DEBUG):
			debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'size': size_new}])

		if (size_best > size_new): # new file is better
			print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
			good_S_M_D[0]=S
			output_best = output
			size_best = size_new
			best_count = count
			size_increased_times = 0
			arr_index = 0
		else:
			showActivity()
			size_increased_times += 1
			if (size_increased_times >= giveUp_S):
				break;
	S = good_S_M_D[0]

	size_increased_times = 0
	# we can't change step after entering the loop because list(range(1, var)) is precalculated
	# use different loop type

	D=1
	D_step = 1
	step_upped = False
	while (D < range_D):
		proc = subprocess.Popen([flif_binary,'-r', str(N),'-S', str(good_S_M_D[0]), '-D', str(D),  INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
		count +=1
		output = proc.stdout.read()
		size_new = sys.getsizeof(output)

		if (DEBUG):
			debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'size': size_new}])

		if (size_best > size_new): # new file is better
			print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
			good_S_M_D[2]=D
			output_best=output
			size_best=size_new
			best_count = count
			size_increased_times = 0
			arr_index = 0
		else:
			showActivity()
			size_increased_times += 1
			if ((D >= 100) and (not step_upped)):
				D_step = 10
				step_upped = True

			if (size_increased_times >= give_up_after):
				break;

		if (D >= range_D):
			break
		D += D_step


	D = good_S_M_D[2]


	size_increased_times = 0
	for M in list(range(0, range_M, 1)):
		proc = subprocess.Popen([flif_binary,'-r', str(N),'-M', str(M), '-S', str(good_S_M_D[0]), '-D', str(good_S_M_D[2]),  INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
		count +=1
		output = proc.stdout.read()
		size_new = sys.getsizeof(output)

		if (DEBUG):
			debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'size': size_new}])

		if (size_best > size_new): # new file is better
			print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
			good_S_M_D[1]=M
			output_best=output
			size_best=size_new
			best_count = count
			size_increased_times = 0
			arr_index = 0
		else:
			showActivity()
			size_increased_times += 1
			if (size_increased_times >= give_up_after):
				break;

	M = good_S_M_D[1]


	# don't remove this, it still pays out here and there
	for N in list(range(0, range_N)):
		proc = subprocess.Popen([flif_binary,  '-M', str(good_S_M_D[1]), '-S', str(good_S_M_D[0]), '-D', str(good_S_M_D[2]),   '-r', str(N), INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
		count +=1
		output = proc.stdout.read()
		size_new = sys.getsizeof(output)


		if (DEBUG):
			debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'size': size_new}])

		if (size_best > size_new): # new file is smaller
			size_increased_times_N = 0 # reset break-counter
			output_best = output
			print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
			best_count=count
			size_best = size_new
			best_N=N
			arr_index = 0
		else:
			size_increased_times_N += 1
			showActivity()
			if (size_increased_times_N >= giveUp_N):
				break; # break out of loop, we have wasted enough time here

bestoptim="N=" + str(best_N) + "  S=" + str(good_S_M_D[0]) + "  M=" + str(good_S_M_D[1])+ "  D=" + str(good_S_M_D[2])



# write final best file

if output_best != "none":
	OUTFILE=".".join(INFILE.split(".")[:-1])+".flif" # split by ".", rm last elm, join by "." and add "flif" extension
	with open(OUTFILE, "w+b") as f:
		f.write(output_best)
		f.close

	size_flif=os.path.getsize(OUTFILE)
	size_orig=os.path.getsize(INFILE)
	print("reduced from {size_orig}b to {size_flif}b ({size_diff}b, {perc_change} %) via [{bestoptim}] and {cnt} flif calls.\n\n".format(size_orig = os.path.getsize(INFILE), size_flif=size_flif, size_diff=(size_flif - size_orig), perc_change=str(((size_flif-size_orig) / size_orig)*100)[:6],  bestoptim=bestoptim, cnt=str(count)), end="\r",flush=True)
else:
	print("WARNING: could not reduce size              ")
	sys.exit(0)

if (DEBUG):
	for index, val in enumerate(debug_array):
		print("run:", val[0]['Nr'], "  N:", val[0]['N'],"  S:",  val[0]['S'],"   M:",  val[0]['M'],"  D:", val[0]['D'],"  size:", val[0]['size'] )
