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
from itertools import chain # combine ranges

__author__ = 'Matthias "matthiaskrgr" Krüger'


parser = argparse.ArgumentParser()
parser.add_argument("infile", help="file to be converted to flif", type=str)
parser.add_argument("-i", "--interlace", help="force interlacing (default: find out best)", action='store_true')
parser.add_argument("-n", "--nointerlace", help="force interlacing off (default: find out best)", action='store_true')
parser.add_argument("-d", "--debug", help="print output of all runs at end", action='store_true')
parser.add_argument("-b", "--bruteforce", help="bruteforce compression values, taking AGES", action='store_true')
parser.add_argument("-c", "--compare", help="compare to default flif compression", action='store_true')


args = parser.parse_args()


if args.compare:
	COMPARE=True
else:
	COMPARE=False

if args.debug:
	DEBUG=True
else:
	DEBUG=False

INFILE=args.infile

interlace_flag="--no-interlace" # default: false
INTERLACE=False
INTERLACE_FORCE=False

if args.interlace:
	interlace_flag="--interlace"
	INTERLACE=True
	INTERLACE_FORCE=True # do we force true or false?
	best_interl = True

if args.nointerlace:
	interlace_flag="--no-interlace"
	INTERLACE=False
	INTERLACE_FORCE=True # do we force true or false?
	best_interl = False

if args.bruteforce:
	BRUTEFORCE=True
else:
	BRUTEFORCE=False

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
	print(progress_array[arr_index] + " " + str(count) + " N" + str(N) + " S" + str(S) + " M" + str(M) + " D" + str(D) + " P" + str(P)  + " ACB:" + str(ACB) + " interlace:" + str(INTERLACE) + ", " + "size: " + str(size_new) + " b        ", end="\r",flush=True)




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

inf={'path': INFILE, 'sizeByte': os.path.getsize(INFILE), 'colors': len(Counter(img).items()), 'sizeX': im.size[0], 'sizeY': im.size[1], 'px': im.size[0]*im.size[1]}

print(inf['path'] + "; dimensions: "  + str(inf['sizeX']) +"×"+ str(inf['sizeY']) + ", " + str(inf['sizeX']*inf['sizeY']) + " px, " + str(inf['colors']) + " unique colors," + " " + str(inf['sizeByte']) + " b")
size_orig = inf['sizeByte']

 
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


#defaults:
N = 0 # avoid undecl var
S = 40 # must at least be 1
M = 50 # can be 0
D = 30 # must at least be 1
P = 1024
ACB=False
#INTERLACE=False  # set above
best_dict={'count': -1, 'N': 0, 'S': 40, 'M': 50, 'D': 30, 'P': 1024, 'ACB': False, 'INT': False, 'size': size_orig}


count = 0 # how many recompression attempts did we take?
best_count = 0 # what was the smallest compression so far?

size_new = size_best = os.path.getsize(INFILE)

try: # catch KeyboardInterrupt

	#do a default flif run:
	if (COMPARE):
		proc = subprocess.Popen([flif_binary, INFILE,  '/dev/stdout'], stdout=subprocess.PIPE)
		output_flifdefault = proc.stdout.read()
		size_flifdefault = sys.getsizeof(output_flifdefault)

	if (DEBUG):
		debug_array=[]
		debug_dict = {'Nr': '', 'N':'', 'S':"", 'M':"", 'D':"", 'P': "", 'ACB': "", 'INT':"", 'size':""}


	if not BRUTEFORCE:
		# MANIAC learning          -r, --repeats=N          MANIAC learning iterations (default: N=3)
		for N in list(range(0, range_N)):
			showActivity()
			proc = subprocess.Popen([flif_binary, '-r', str(N), INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
			count +=1
			output = proc.stdout.read()
			size_new = sys.getsizeof(output)

			if (DEBUG):
				debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'P':P, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

			if (((best_dict['size'] > size_new) or (((count==1) and (size_new < size_orig))))): # new file is smaller
				size_increased_times_N = 0 # reset break-counter
				output_best = output
				print("{count}, N {N}, S {S}, M {M}, D {D}, P {P}, ACB=Auto, INTERLACE={INT}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, P=P, INT=INTERLACE, size=size_new, run_best="orig" if (count == 1) else best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
				best_dict['size'] = size_new
				best_dict['count'] = count
				best_dict['N'] = N
				arr_index = 0
			else:
				size_increased_times_N += 1
				if (size_increased_times_N >= giveUp_N):
					break; # break out of loop, we have wasted enough time here

		N = best_dict['N']
		size_increased_times = size_increased_times_N = 0

		# if N== 0 / no maniac tree, skip the rest
		if (best_dict['N'] != 0):
			for S in list(range(1, range_S, 1)):
				if (S <= 4):  # skip S 1-4, it takes too much ram.
					continue
				showActivity()
				proc = subprocess.Popen([flif_binary,'-r', str(best_dict['N']), '-S', str(S),  INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
				count +=1
				output = proc.stdout.read()
				size_new = sys.getsizeof(output)

				if (DEBUG):
					debug_array.append([{'Nr':count, 'N':best_dict['N'], 'S':S, 'M':M, 'D':D, 'P':P, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

				if (best_dict['size'] > size_new): # new file is better
					print("{count}, N {N}, S {S}, M {M}, D {D}, P {P}, ACB=Auto, INTERLACE={INT}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=best_dict['N'], S=S, M=M, D=D, P=P, INT=INTERLACE, size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
					best_dict['S'] = S
					output_best = output
					best_dict['size'] = size_new
					best_dict['count'] = count
					size_increased_times = 0
					arr_index = 0
				else:
					size_increased_times += 1
					if (size_increased_times >= giveUp_S):
						break;
			S = best_dict['S']
			size_increased_times = 0
			# we can't change step after entering the loop because list(range(1, var)) is precalculated
			# use different loop type

			D=1
			D_step = 1
			D_step_upped = False # if True; D_step == 10
			while (D < range_D):
				showActivity()
				proc = subprocess.Popen([flif_binary,'-r', str(best_dict['N']),'-S', str(best_dict['S']), '-D', str(D),  INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
				count +=1
				output = proc.stdout.read()
				size_new = sys.getsizeof(output)

				if (DEBUG):
					debug_array.append([{'Nr':count, 'N':str(best_dict['N']), 'S':str(best_dict['S']), 'M':M, 'D':D, 'P':P, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


				if (best_dict['size'] > size_new): # new file is better
					print("{count}, N {N}, S {S}, M {M}, D {D}, P {P}, ACB=Auto, INTERLACE={INT}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=str(best_dict['N']), S=str(best_dict['S']), M=M, D=D, P=P, INT=INTERLACE, size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
					best_dict['D'] = D
					output_best=output
					best_dict['size'] = size_new
					best_dict['count'] = count
					size_increased_times = 0
					arr_index = 0
				else:
					size_increased_times += 1
					if ((D >= 100) and (not D_step_upped)):
						D_step = 10
						D_step_upped = True

					if (size_increased_times >= give_up_after):
						break;

				if (D >= range_D):
					break
				D += D_step
			D = best_dict['D']


			size_increased_times = 0
			for M in list(range(0, range_M, 1)):
				showActivity()
				proc = subprocess.Popen([flif_binary,'-r', str(best_dict['N']),'-M', str(M), '-S', str(best_dict['S']), '-D', str(best_dict['D']),  INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
				count +=1
				output = proc.stdout.read()
				size_new = sys.getsizeof(output)

				if (DEBUG):
					debug_array.append([{'Nr':count, 'N':str(best_dict['N']), 'S':str(best_dict['S']), 'M':M, 'D':str(best_dict['D']), 'P':P, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


				if (best_dict['size'] > size_new): # new file is better
					print("{count}, N {N}, S {S}, M {M}, D {D}, P {P}, ACB=Auto, INTERLACE={INT}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=str(best_dict['N']), S=str(best_dict['S']), M=M, D=str(best_dict['D']), P=P, INT=INTERLACE, size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
					best_dict['M'] = M
					output_best=output
					best_dict['size']=size_new
					best_dict['count'] = count
					size_increased_times = 0
					arr_index = 0
				else:
					size_increased_times += 1
					if (size_increased_times >= give_up_after):
						break;
			M = best_dict['M']



			size_increased_times = 0

			Prange = set(chain(range(0, 11), range(inf['colors']-5, inf['colors']+10)))
			for P in Prange:
				showActivity()
				if ((P < 0) or (P > 30000)) : # in case inf['colors']  is >5
					continue
				proc = subprocess.Popen([flif_binary,'-r', str(best_dict['N']),'-M', str(best_dict['M']), '-S', str(best_dict['S']), '-D', str(best_dict['D']), '-p', str(P),  INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
				count +=1
				output = proc.stdout.read()
				size_new = sys.getsizeof(output)

				if (DEBUG):
					debug_array.append([{'Nr':count, 'N':str(best_dict['N']), 'S':str(best_dict['S']), 'M':str(best_dict['M']), 'D':str(best_dict['D']), 'P':P, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


				if (best_dict['size'] > size_new): # new file is better
					print("{count}, N {N}, S {S}, M {M}, D {D}, P {P}, ACB=Auto, INTERLACE={INT}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=str(best_dict['N']), S=str(best_dict['S']), M=str(best_dict['M']), D=str(best_dict['D']), P=P, INT=INTERLACE, size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
					output_best=output
					best_dict['size']=size_new
					best_dict['count'] = count
					best_dict['P'] = P
					size_increased_times = 0
					arr_index = 0


			P = best_dict['P']

			# don't remove this, it still pays out here and there
			size_increased_times_N = 0 # reset since first run
			for N in list(range(0, range_N)):
				showActivity()
				proc = subprocess.Popen([flif_binary,  '-M', str(best_dict['M']), '-S', str(best_dict['S']), '-D', str(best_dict['D']), '-p', str(best_dict['P']),  '-r', str(N), INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
				count +=1
				output = proc.stdout.read()
				size_new = sys.getsizeof(output)

				if (DEBUG):
					debug_array.append([{'Nr':count, 'N':str(N), 'S':str(best_dict['S']), 'M':str(best_dict['M']), 'D':str(best_dict['D']), 'P':str(best_dict['P']), 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


				if (best_dict['size'] > size_new): # new file is smaller
					size_increased_times_N = 0 # reset break-counter
					output_best = output
					print("{count}, N {N}, S {S}, M {M}, D {D}, P {P}, ACB=Auto, INTERLACE={INT}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=best_dict['S'], M=best_dict['M'], D=best_dict['D'], P=best_dict['P'], INT=INTERLACE, size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
					best_dict['count'] = count
					best_dict['size'] = size_new
					best_dict['N'] = N
					arr_index = 0
				else:
					size_increased_times_N += 1
					if (size_increased_times_N >= best_dict['N'] + 4):
						break; # break out of loop, we have wasted enough time here
			N = best_dict['N']
		else: #   (best_dict['N'] == 0),  still try P
			size_increased_times = 0

			Prange = set(chain(range(0, 11), range(inf['colors']-5, inf['colors']+10)))
			for P in Prange:
				showActivity()
				if ((P < 0) or (P > 30000)) : # in case inf['colors']  is >5
					continue
				proc = subprocess.Popen([flif_binary,'-r', str(best_dict['N']),'-M', str(best_dict['M']), '-S', str(best_dict['S']), '-D', str(best_dict['D']), '-p', str(P),  INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
				count +=1
				output = proc.stdout.read()
				size_new = sys.getsizeof(output)

				if (DEBUG):
					debug_array.append([{'Nr':count, 'N':str(best_dict['N']), 'S':str(best_dict['S']), 'M':str(best_dict['M']), 'D':str(best_dict['D']), 'P':P, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


				if (best_dict['size'] > size_new): # new file is better
					print("{count}, N {N}, S {S}, M {M}, D {D}, P {P}, ACB=Auto, INTERLACE={INT}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=str(best_dict['N']), S=str(best_dict['S']), M=str(best_dict['M']), D=str(best_dict['D']), P=P, INT=INTERLACE, size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
					output_best=output
					best_dict['size']=size_new
					best_dict['count'] = count
					best_dict['P'] = P
					size_increased_times = 0
					arr_index = 0


			P = best_dict['P']



		# auto color buckets:

		best_ACB="Auto"
		for acb in "--acb", "--no-acb":
			showActivity()
			proc = subprocess.Popen([flif_binary, acb,  '-M', str(best_dict['N']), '-S', str(best_dict['S']), '-D', str(best_dict['D']), '-p', str(best_dict['P']),   '-r', str(best_dict['N']), INFILE, interlace_flag, '/dev/stdout'], stdout=subprocess.PIPE)
			count +=1
			output = proc.stdout.read()
			size_new = sys.getsizeof(output)

			if (acb == "--acb"):
				ACB=True
			elif (acb == "--no-acb"):
				ACB=False

			if (DEBUG):
				debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'P':P, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


			if (best_dict['size'] >= size_new): # new file is smaller
				size_increased_times_N = 0 # reset break-counter
				output_best = output
				if (best_dict['size'] > size_new): # is actually better,  hack to avoid "-0 b"
					print("{count}, N {N}, S {S}, M {M}, D {D}, P {P}, ACB={ACB}, INTERLACE={INT}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=best_dict['N'], S=best_dict['S'], M=best_dict['M'], D=best_dict['D'], P=best_dict['P'], INT=INTERLACE, ACB=str(ACB), size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
				best_dict['count'] = count
				best_dict['size'] = size_new
				arr_index = 0
				best_dict['ACB'] = ACB
		ACB = best_dict['ACB']



		if not (INTERLACE_FORCE):
			best_interl = False
			for interl in "--no-interlace", "--interlace":
				showActivity()
				proc = subprocess.Popen([flif_binary, acb,  '-M', str(best_dict['M']), '-S', str(best_dict['S']), '-D', str(best_dict['D']), '-p', str(best_dict['P']),  '-r', str(best_dict['N']), INFILE, interl, '/dev/stdout'], stdout=subprocess.PIPE)
				count +=1
				output = proc.stdout.read()
				size_new = sys.getsizeof(output)


				if (interl == "--interlace"):
					INTERL=True
				elif (interl == "--no-interlace"):
					INTERL=False

				if (DEBUG):
					debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'P':P, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


				if (best_dict['size'] > size_new): # new file is smaller
					size_increased_times_N = 0 # reset break-counter
					output_best = output
					if (best_dict['size'] > size_new): # is actually better,  hack to avoid "-0 b"
						print("{count}, N {N}, S {S}, M {M}, D {D}, P {P}, ACB {ACB}, INTERLACE {INTERL}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=best_dict['N'], S=best_dict['S'], M=best_dict['M'], D=best_dict['D'], P=best_dict['P'], ACB=str(ACB), INTERL=INTERL, size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
					best_dict['count'] = count
					best_dict['size'] = size_new
					best_dict['INT'] = INTERL
					arr_index = 0
					best_interl=INTERL
			INTERLACE = best_dict['INT']

	else: # brutefoce == true
		best_N=0
		count = 0
		good_S_M_D = [0, 0, 0]
		best_ACB = True
		best_interl = True
		size_best=os.path.getsize(INFILE)
	# N, S, M, D, acb, interlacing
		for N in list(range(0, range_N)):
			for S in list(range(1, range_S, 1)):
				D=1
				D_step = 1
				step_upped = False
				while (D < range_D):
					if (D >= 100):
						D += 100
					else:
						D += 1
					for M in list(range(0, range_M, 1)):
						for acb in "--acb", "--no-acb":
							for interl in "--no-interlace", "--interlace":
								#print(str(N) + " " + str(S) + " " + str(D) + " " + str(M) + " " + str(acb) + " " + str(interl))
								showActivity()
								proc = subprocess.Popen([flif_binary, acb,  '-M', str(M), '-S', str(S), '-D', str(D),   '-r', str(N), str(INFILE), str(interl), '/dev/stdout'], stdout=subprocess.PIPE)
								count +=1
								output = proc.stdout.read()
								size_new = sys.getsizeof(output)

								if (interl == "--no-interlace"):
									INTERLACE=False
								else:
									INTERLACE=True

								if (acb == "--acb"):
									ACB=True
								elif (acb == "--no-acb"):
									ACB=False

								if (DEBUG):
									debug_array.append([{'Nr':count, 'N':N, 'S':S, 'M':M, 'D':D, 'P':P, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


								if (size_new < best_dict['size']): # new file is smaller
									output_best = output
									best_dict['count']=count
									print("{count}, N {N}, S {S}, M {M}, D {D}, P {P}, ACB {ACB}, interlace: {INTERLACE}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, M=M, D=D, P=P, ACB=str(ACB), INTERLACE=str(INTERLACE), size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
									best_dict['size'] = size_new
									best_dict['N'] = N
									best_dict['INT'] = INTERLACE
									best_dict['S'] = S
									best_dict['M'] = M
									best_dict['D'] = D
									best_dict['ACB'] = ACB



	

	if COMPARE: # how does flifcrush compare to default flif conversion?
		diff_to_flif_byte = best_dict['size'] - size_flifdefault
		if (diff_to_flif_byte > 0):
			print("WARNING, FLIFCRUSH FAILED reducing size, please report!")
		diff_to_flif_perc = (((size_flifdefault-best_dict['size']) / best_dict['size'])*100)
		print("\n\nComparing flifcrush (" + str(best_dict['size']) +" b) to default flif (" + str(size_flifdefault)  + " b): " + str(diff_to_flif_byte) + " b which are " + str(diff_to_flif_perc)[:6] + " %")


	# write final best file

	if output_best != "none":
		OUTFILE=".".join(INFILE.split(".")[:-1])+".flif" # split by ".", rm last elm, join by "." and add "flif" extension
		with open(OUTFILE, "w+b") as f:
			f.write(output_best)
			f.close

		size_flif=os.path.getsize(OUTFILE)
		size_orig=os.path.getsize(INFILE)
		print("reduced from {size_orig}b to {size_flif}b ({size_diff}b, {perc_change} %) via [{bestoptim}] and {cnt} flif calls.\n\n".format(size_orig = os.path.getsize(INFILE), size_flif=size_flif, size_diff=(size_flif - size_orig), perc_change=str(((size_flif-size_orig) / size_orig)*100)[:6],  bestoptim=str("N=" + str(best_dict['N']) + "  S=" + str(best_dict['S']) + "  M=" + str(best_dict['M'])+ "  D=" + str(best_dict['D']) + "  P=" + str(best_dict['P']) + "  ACB=" + str(best_dict['ACB']) + "  INTERLACE=" + str(best_dict['INT'])), cnt=str(count)), end="\r",flush=True)
	else:
		print("WARNING: could not reduce size              ")
		sys.exit(0)

	if (DEBUG):
		for index, val in enumerate(debug_array):
			print("run:", val[0]['Nr'], "  N:", val[0]['N'],"  S:",  val[0]['S'],"   M:",  val[0]['M'],"  D:", val[0]['D'],"  P:", val[0]['P'], "ACB", val[0]['ACB'],"INT", val[0]['INT'], "  size:", val[0]['size'] )
except KeyboardInterrupt:
	try: # double ctrl+c shall quit immediately
		print("\nSaving file..")
		if output_best != "none":
			OUTFILE=".".join(INFILE.split(".")[:-1])+".flif" # split by ".", rm last elm, join by "." and add "flif" extension
			with open(OUTFILE, "w+b") as f:
				f.write(output_best)
				f.close

			size_flif=os.path.getsize(OUTFILE)
			size_orig=os.path.getsize(INFILE)
			print("reduced from {size_orig}b to {size_flif}b ({size_diff}b, {perc_change} %) via [{bestoptim}] and {cnt} flif calls.\n\n".format(size_orig = os.path.getsize(INFILE), size_flif=size_flif, size_diff=(size_flif - size_orig), perc_change=str(((size_flif-size_orig) / size_orig)*100)[:6],  bestoptim=str("N=" + str(best_dict['N']) + "  S=" + str(best_dict['S']) + "  M=" + str(best_dict['M'])+ "  D=" + str(best_dict['D']) + "  P=" + str(best_dict['P']) + "  ACB=" + str(best_dict['ACB']) + "  INTERLACE=" + str(best_dict['INT'])), cnt=str(count)), end="\r",flush=True)
		else:
			print("WARNING: could not reduce size              ")
			sys.exit(0)
	except KeyboardInterrupt: # double ctrl+c
		print("Terminated by user")

