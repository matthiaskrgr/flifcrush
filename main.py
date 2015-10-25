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




'''
to be faster: first calculate SMD with -r 1, then bruteforce best r value

'''

global arr_index
global progress_array
arr_index = 0
#progress_array=["|", "/", "-", "\\",]
#progress_array=[".", "o", "0", "O", "O", "o", "."]
progress_array=["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▁"]
arrlen=len(progress_array)

def showActivity():
	global arr_index
	arr_index = arr_index + 1
	if (arr_index == arrlen):
		arr_index = 0
	print(progress_array[arr_index], end="\r",flush=True)
	#return

debug_array=[]
#debug_dict = {'Nr': '', 'N':'', 'S':"", 'M':"", 'D':"", 'size':""}
#debug_arry.append([{'N':N, 'S':S, 'M':M, 'D':D,'size': size}])



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
N = S = M = D = 0
size_increased_times_N = size_increased_times_D = size_increased_times_M = size_increased_times_S = 0


range_N = 20   # default: 3 // try: 0-20
range_S = 600 # default: 40  // try: 1-100
range_M = 600 # default: 30  // try: 1-100
range_D = 600 # default: 50  // try  1-100

give_up_after = 200

#defaults:
S=40
M=30
D=50

# if we did this many attempts without getting better results, give up
giveUp_N = 5
giveUp_S = 200
giveUp_D = 100
giveUp_M = 200

count = 0 # how many recompression attempts did we take?
best_count=0 # what was the smallest compression so far?

size_new = size_best = os.path.getsize(INFILE)

# -M can be 0
# -S and -D must at least be 1


# -r is said to be independent of the other parameters





# do a first -n run






range_N=20

size_orig=os.path.getsize(INFILE)


size_increased_times_N_first=0

first_best_N=0
# MANIAC learning          -r, --repeats=N          MANIAC learning iterations (default: N=3)
for N in list(range(0, range_N)):
	proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif', '-r', str(N), INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
	count +=1


	output = proc.stdout.read()
	size_new = sys.getsizeof(output)
	debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'size': size_new}])

	if (((size_best > size_new) or ((N==0) and size_new < size_orig))) : # new file is smaller
		size_increased_times_N_first = 0 # reset break-counter
		output_best = output
		print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
		best_count=count
		size_best = size_new
		best_N_first=N
	else:
		size_increased_times_N += 1
		showActivity()
		if (size_increased_times_N_first >= 5):
			break; # break out of loop, we have wasted enough time here

best_N= best_N_first
N=0 # reset N






#order: s, d, m, n
N = best_N =1

size_increased_times = 0
good_S_M_D=["40","30","50"]
for S in list(range(1, range_S, 1)):
	#print('S'+ str(S))
	#size_increased_times_M = 0
	proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(1), '-S', str(S),  INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
	count +=1
	output = proc.stdout.read()
	size_new = sys.getsizeof(output)
	if (size_best > size_new): # new file is better
		print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
		good_S_M_D[0]=S
		output_best = output
		size_best = size_new
		best_count = count
		size_increased_times = 0
	else:
		showActivity()
#				print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
		size_increased_times += 1
		if (size_increased_times >= give_up_after):
			break;
S = good_S_M_D[0]
#print(good_S_M_D)
#quit()

size_increased_times = 0
for D in list(range(1, range_D, 1)):
	#print('D'+ str(D))
	#size_increased_times_M = 0
	proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(1),'-S', str(good_S_M_D[0]), '-D', str(D),  INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
	count +=1
	output = proc.stdout.read()
	size_new = sys.getsizeof(output)
	if (size_best > size_new): # new file is better
		print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
		good_S_M_D[2]=D
		output_best=output
		size_best=size_new
		best_count = count
		size_increased_times = 0
	else:
		showActivity()
#				print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
		#size_increased_times += 1
		size_increased_times += 1
		if (size_increased_times >= give_up_after):
			break;
D = good_S_M_D[2]



size_increased_times = 0
for M in list(range(0, range_M, 1)):
	#print('M'+ str(M))
	#size_increased_times_M = 0
	proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif','-r', str(1),'-M', str(M), '-S', str(good_S_M_D[0]), '-D', str(good_S_M_D[2]),  INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
	count +=1
	output = proc.stdout.read()
	size_new = sys.getsizeof(output)
	if (size_best > size_new): # new file is better
		print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
		good_S_M_D[1]=M
		output_best=output
		size_best=size_new
		best_count = count
		size_increased_times = 0
	else:
		showActivity()
#				print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
		#size_increased_times += 1
		size_increased_times += 1
		if (size_increased_times >= give_up_after):
			break;

M = good_S_M_D[1]



#best_N=1
# MANIAC learning          -r, --repeats=N          MANIAC learning iterations (default: N=3)
for N in list(range(0, range_N)):
	proc = subprocess.Popen(['/home/matthias/vcs/github/FLIF/flif',  '-M', str(good_S_M_D[1]), '-S', str(good_S_M_D[0]), '-D', str(good_S_M_D[2]),   '-r', str(N), INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
	count +=1
	#if (N == 1): #first run, initialize
		#print("first run, orig size")
		#size_new = size_best = os.path.getsize(INFILE) #size of png
		#debug_array.append([{'Nr': 0, 'N':N, 'S':S, 'M':M, 'D':D, 'size': size_new}])
		#print("0, N {N}, S {S}, M {M}, D {D}, size {size} b, (original size)".format(N=N, S=S, M=M, D=D, size=size_new))

	output = proc.stdout.read()
	size_new = sys.getsizeof(output)
	debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'size': size_new}])

	if (size_best > size_new): # new file is smaller
		size_increased_times_N = 0 # reset break-counter
		output_best = output
		print("{count}, N {N}, S {S}, M {M}, D {D}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, size=size_new, run_best=best_count, size_best=size_best, size_change=size_best-size_new, perc_change=str(((size_new-size_best) / size_best)*100)[:6]))
		best_count=count
		size_best = size_new
		best_N=N
	else:
		size_increased_times_N += 1
		showActivity()
		if (size_increased_times_N >= giveUp_N):
			break; # break out of loop, we have wasted enough time here

#print("best N: " + str(best_N))
#print(good_S_M_D)


print("N=" + str(best_N) + "  S=" + str(good_S_M_D[0]) + "  M=" + str(good_S_M_D[1])+ "  D=" + str(good_S_M_D[2]))



# write final best file

OUTFILE=INFILE+".flif"
with open(OUTFILE, "w+b") as f:
	f.write(output_best)
	f.close

size_flif=os.path.getsize(OUTFILE)
size_orig=os.path.getsize(INFILE)
print("\nreduced from {size_orig}b to {size_flif}b ({size_diff}b, {perc_change} %)".format(size_orig = os.path.getsize(INFILE), size_flif=size_flif, size_diff=(size_flif - size_orig), perc_change=str(((size_flif-size_orig) / size_orig)*100)[:6]))
print("called flif " + str(count) + " times")


#			print debug information
#for index, val in enumerate(debug_array):
#		print("index:", index, "  val:", val[0]['Nr'], "  N:", val[0]['N'],"  S:",  val[0]['S'],"   M:",  val[0]['M'],"  D:", val[0]['D'],"  size:", val[0]['size'] )
