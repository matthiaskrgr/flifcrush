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
from collections import namedtuple
import argparse
from itertools import chain # combine ranges

import random # getrandomfilename
import string # getrandomfilename
__author__ = 'Matthias "matthiaskrgr" Krüger'

parser = argparse.ArgumentParser()
parser.add_argument("inpath", help="file or path (recursively) to be converted to flif", metavar='N', nargs='+', type=str)
parser.add_argument("-i", "--interlace", help="force interlacing (default: find out best)", action='store_true')
parser.add_argument("-n", "--nointerlace", help="force interlacing off (default: find out best)", action='store_true')
parser.add_argument("-d", "--debug", help="print output of all runs at end", action='store_true')
#parser.add_argument("-b", "--bruteforce", help="bruteforce compression values, takes AGES and might be outdated", action='store_true')
parser.add_argument("-c", "--compare", help="compare to default flif compression", action='store_true')
args = parser.parse_args()

COMPARE = (args.compare)
DEBUG = (args.debug)
INPATHS = args.inpath

interlace_flag="--no-interlace" # default: false
INTERLACE=False
INTERLACE_FORCE=False

# make these global to access them easily inside functions 
global size_before_glob, size_after_glob, files_count_glob, size_flifdefault_glob
size_before_glob = 0 # size of all images we process
size_after_glob = 0 # size of all flifs we generated
files_count_glob = 0  # number of files
size_flifdefault_glob = 0 # size of all images converted with flif default parameters

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

#BRUTEFORCE = (args.bruteforce)
BRUTEFORCE = False

output_best="none"
global arr_index
global progress_array
arr_index = 0
#progress_array=["|", "/", "-", "\\",]
#progress_array=[".", "o", "0", "O", "O", "o", "."]
progress_array=[" ", "▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▁"]
arrlen=len(progress_array)

# prints activity indicator (some kind of ascii 'animation')
def showActivity():
#	return
	global arr_index
	arr_index+=1
	if (arr_index == arrlen):
		arr_index = 0
	print(progress_array[arr_index] + " " + str(count) + " maniac_repeats" + str(maniac_repeats) + " maniac_threshold" + str(maniac_threshold) + " maniac_min_size" + str(maniac_min_size) + " maniac_divisor" + str(maniac_divisor) + " max_palette_size" + str(max_palette_size)  + " chance-cutoff" + str(chance_cutoff) + " chance-alpha" + str(chance_alpha) +  " interlace:" + str(INTERLACE) +  " force-color-buckets:" + str(force_color_buckets) + " no-channel-compact:" + str(no_channel_compact) +  "no-ycocq" + str(no_ycocq)   + " keep-invisible-rgb:" + str(keep_invisible_rgb) +  ", size: " + str(size_new) + " b        ", end="\r",flush=True)

# save .flif file that had the best combination of parameters 
def save_file():
	flif2flif = False # default, we need extra parameter if we convert .flif to -clif
	# if the condition is false, we didn't manage to reduce size
	if output_best != "none":
		OUTFILE=".".join(INFILE.split(".")[:-1])+".flif" # split by ".", rm last elm, join by "." and add "flif" extension

		if (OUTFILE == INFILE): # most likely flif fo flif crushing
			flif2flif = True
			OUTFILE=get_rand_filename()

		with open(OUTFILE, "w+b") as f:
			f.write(output_best)
			f.close

		size_flif=os.path.getsize(OUTFILE)
		size_orig=os.path.getsize(INFILE)

		if (flif2flif): # overwrite INFILE with OUTFILE
			os.remove(INFILE)
			os.rename(OUTFILE, INFILE) # rename outfile to infile

		# print some numbers
		global size_after_glob
		size_after_glob += size_flif
		print("\033[K", end="")
		print("reduced from {size_orig}b to {size_flif}b ({size_diff}b, {perc_change} %) via TODO and {cnt} flif calls.\n\n")
		#print("reduced from {size_orig}b to {size_flif}b ({size_diff}b, {perc_change} %) via \n [{bestoptim}] and {cnt} flif calls.\n\n".format(size_orig = os.path.getsize(INFILE), size_flif=size_flif, size_diff=(size_flif - size_orig), perc_change=str(((size_flif-size_orig) / size_orig)*100)[:6],  bestoptim=str("maniac repeats:" + str(best_dict['maniac_repeats']) + " maniac_threshold:" + str(best_dict['maniac_threshold']) + " maniac_min_size:" + str(best_dict['maniac_min_size'])+ " maniac_divisor:" + str(best_dict['maniac_divisor']) + " max_palette_size:" + str(best_dict['max_palette_size']) + " chance-cutoff:" + str(best_dict['chance_cutoff'])  + " chance-alpha:" + str(best_dict['chance_alpha']) +  " ACB:" + str(best_dict['ACB']) + " INTERLACE:" + str(best_dict['INT']) + " PLC:" + str(best_dict['PLC']) + " RGB:" +  str(best_dict['RGB']) +  " A:" + str(best_dict['A'])), cnt=str(count)), end="\r")
	else:
		print("\033[K", end="")
		print("WARNING: could not reduce size!")

# generates a name for a file that does not exist in current directory, used for tmp files
def get_rand_filename(): 
	# this prevents accidentally overwriting a preexisting file
	filename =''.join(random.choice(string.ascii_uppercase) for i in range(9))
	while (os.path.isfile(filename)): # if the name already exists, try again
		filename =''.join(random.choice(string.ascii_uppercase) for i in range(9))
	return filename


# make sure we know where flif binary is
flif_binary = ""
try: # search for "FLIF" enviromental variable first
	flif_path = os.environ['FLIF']
	if os.path.isfile(flif_path): # the variable actually points to a file
		flif_binary = flif_path
except KeyError: # env var not set, check if /usr/bin/flif exists
	if (flif_binary == ""):
		if (os.path.isfile("/usr/bin/flif")):
			flif_binary = "/usr/bin/flif"
		elif (os.path.isfile("/usr/share/bin/flif")):
			flif_binary = "/usr/share/bin/flif"
		else:
			print("Error: no flif binary found, please use 'export FLIF=/path/to/flif'")
			os.exit(1)


SUPPORTED_FILE_EXTENSIONS=['png', 'flif'] # @TODO add some more
input_files = []
try: # catch KeyboardInterrupt

	for path in INPATHS: # iterate over arguments
		if (os.path.isfile(path)): # inpath is not a directory but a file
			input_files.append(path) # add to list
		else:  # else walk recursively 
			for root, directories, filenames in os.walk(path): 
				for filename in filenames:
					if (filename.split('.')[-1] in SUPPORTED_FILE_EXTENSIONS): # check for valid filetypes
						input_files.append(os.path.join(root,filename)) # add to list

# generation of input_files list is done:


	for INFILE in input_files: # iterate over every file that we go
		flif_to_flif = ""
		files_count_glob += 1
		#output some metrics about the png that we are about to convert
		inf={'path': INFILE, 'sizeByte': 0, 'colors': 0, 'sizeX': 0, 'sizeY':0, 'px':0, 'filetype': INFILE.split('.')[-1]}

		if (inf['filetype'] == "flif"): # PIL does not know flif (yet...?), so we convert the .flif to .png, catch it, and get the amount of pixels
			flif_to_flif = "-t" # flif needs -t flag in case of flif to flif
			FIFO=get_rand_filename() + ".png" # make sure path does not exist before
			os.mkfifo(FIFO) # create named pipe
			subprocess.Popen([flif_binary, INFILE, FIFO])  # convert flif to png to get pixel data
			im = Image.open(FIFO) # <- png data
			os.remove(FIFO) # remove named pipe
		else:
			im = Image.open(INFILE)

		# @TODO: can we speed this up?
		# just for fun:
		img=[] # will contain px data
		for px in (im.getdata()): # iterate over the pixels of the input image so we can count the number of different colors
			img.append(px)

		inf={'path': INFILE, 'sizeByte': os.path.getsize(INFILE), 'colors': len(Counter(img).items()), 'sizeX': im.size[0], 'sizeY': im.size[1], 'px': im.size[0]*im.size[1], 'filetype': INFILE.split('.')[-1]}

		print(inf['path'] + "; dimensions: "  + str(inf['sizeX']) +"×"+ str(inf['sizeY']) + ", " + str(inf['sizeX']*inf['sizeY']) + " px, " + str(inf['colors']) + " unique colors," + " " + str(inf['sizeByte']) + " b")
		size_orig = inf['sizeByte']
		size_before_glob  += size_orig

		# how many attempts to try in worst case? ( check flif.cpp:400 and config.h)
		range_maniac_repeats = 20   # default: 3 // try: 0-20
		range_maniac_threshold = 600 # default: 40   // max: 100000
		range_maniac_min_size = 3000 # default: 30   // 0-inf
		range_maniac_divisor = 268435455 # default: 50  // try  1-100
		range_chance_cutoff = 128 # default: 2 //  range: 1 - 128  
		range_chance_alpha = 128 # default: 19  // range: 4 - 128

		# if we did this many attempts without getting better results, give up
		giveUp_maniac_repeats = 5
		giveUp_maniac_threshold = 100
		give_up_after = 200
		size_increased_times_maniac_repeats = 0


		#defaults:
		maniac_repeats = 0 # avoid undecl var
		maniac_threshold = 40 # must at least be 1
		maniac_min_size = 50 # can be 0
		maniac_divisor = 30 # must at least be 1
		max_palette_size = 1024
		chance_cutoff = 2 # must at least be 1
		chance_alpha = 19 # must at least be 4, is float


		interlace = False
		no_channel_compact = True  # plc
		force_color_buckets= True # acb
		no_ycocq =  True # !rgba
		keep_invisible_rgb = False #




		#ACB=False
		#PLC=True
		#RGB=False
		#A=False # --keep-alpha-zero

		#INTERLACE=False  # set above
		# PLC == false : passed -C or --no-plc
		# RGB == True : passed -R or --rgb

		# colors for stdout
		txt_ul = '\033[04m' # underline
		txt_res = '\033[0m' #reset

  # 'INT': False, 'force_color_buckets': False,  'no_channel_compact': True, 'no_ycocq':False, 'keep_invisible_rgb': False, 


		"""
		# --no-interlace  ; --interlace
		best_dict[interlace] = Boolflag("--no-interlace", False)

		# --no-channel-compact ; - 
		no_channel_compact = Boolflag('--no-channel-compact', True)
		
		# --no-force-color-buckets  ; --force-color-buckets
		force_color_buckets = Boolflag('--force-color-buckets', True)

		# --no-ycocq ;  - 
		no_ycocq = Boolflag("--no-ycocq", True)

		# --keep-invisible-rgb ; -
		keep_invisible_rgb = Boolflag("--keep-invisible-rgb", True)
		"""

		# use named tuples for boolean cmdline flags
		Boolflag = namedtuple('boolflag', 'flag bool') # define the structure

		best_dict={'count': -1,
				'maniac_repeats': 0,
				'maniac_threshold': 40,
				'maniac_min_size': 50,
				'maniac_divisor': 30,
				'max_palette_size': 1024,
				'chance_cutoff': 2,
				'chance_alpha': 19,
				'interlace':  Boolflag("--no-interlace", False),
				'no_channel_compact': Boolflag('--no-channel-compact', True),
				'force_color_buckets': Boolflag('--force-color-buckets', True),
				'no_ycocq': Boolflag("--no-ycocq", True),
				'keep_invisible_rgb':  Boolflag("--keep-invisible-rgb", False),
				'size': size_orig,
				}

# modify:
# best_dict['no_ycocq']._replace(bool=False)


		count = 0 # how many recompression attempts did we take?
		best_count = 0 # what was the smallest compression so far?

		size_new = size_best = os.path.getsize(INFILE)

		if (COMPARE):  #do a default flif run with no special arguments
			proc = subprocess.Popen([flif_binary, INFILE,  '/dev/stdout'], stdout=subprocess.PIPE)
			output_flifdefault = proc.stdout.read()
			size_flifdefault = sys.getsizeof(output_flifdefault)
			size_flifdefault_glob += size_flifdefault

		if (DEBUG):
			debug_array=[]
			debug_dict = {'Nr': '', 'maniac_repeats':'', 'maniac_threshold':"", 'maniac_min_size':"", 'maniac_divisor':"", 'max_palette_size': "", 'ACB': "", 'INT':"", 'size':""}

		if (not BRUTEFORCE):
			# MANIAC learning          -r, --repeats=N          MANIAC learning iterations (default: N=3)
			for maniac_repeats in list(range(0, range_maniac_repeats)):
				showActivity()

				raw_command = [flif_binary, flif_to_flif,('--maniac-repeats=' + str(maniac_repeats)), INFILE, interlace_flag, '/dev/stdout']
				sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
				proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

				count += 1
				output = proc.stdout.read()
				size_new = sys.getsizeof(output)

				if (DEBUG):
					debug_array.append([{'Nr':count, 'maniac_repeats':maniac_repeats, 'maniac_threshold':maniac_threshold, 'maniac_min_size':maniac_min_size, 'maniac_divisor':maniac_divisor, 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

				if ((best_dict['size'] > size_new) or (count==1)): # new file is smaller // count==1: make sure best_dict is filled with first values we obtain. this way we still continue crushing even if initial N-run does not reduce size smaller than size_orig
					size_increased_times_maniac_repeats = 0 # reset break-counter
					output_best = output
					if (size_orig > size_new):
						perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
						perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
						print("{count}, \033[04mmaniac_repeats {maniac_repeats}\033[0m, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, max_palette_size {max_palette_size}, ACB=Auto, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=maniac_repeats, maniac_threshold=maniac_threshold, maniac_min_size=maniac_min_size, maniac_divisor=maniac_divisor, max_palette_size=max_palette_size, A="", INT="", RGB="", PLC="", size=size_new, run_best="orig" if (count == 1) else best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
					best_dict['size'] = size_new
					best_dict['count'] = count
					best_dict['maniac_repeats'] = maniac_repeats
					arr_index = 0
				else:
					size_increased_times_maniac_repeats += 1
					if (size_increased_times_maniac_repeats >= giveUp_maniac_repeats):
						break; # break out of loop, we have wasted enough time here

			maniac_repeats = best_dict['maniac_repeats']
			size_increased_times = size_increased_times_maniac_repeats = 0

			# if maniac_repeats== 0 / no maniac tree, skip the rest
			if (best_dict['maniac_repeats'] != 0):
				for maniac_threshold in list(range(1, range_maniac_threshold, 1)):
					if (maniac_threshold <= 4):  # skip maniac_threshold 1-4, it takes too much ram in extreme cases
						continue
					showActivity()

					raw_command = [flif_binary, flif_to_flif, ('--maniac-repeats=' + str(best_dict['maniac_repeats'])), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])),  INFILE, interlace_flag, '/dev/stdout']
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)

					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':best_dict['maniac_repeats'], 'maniac_threshold':maniac_threshold, 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size': max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

					if (best_dict['size'] > size_new): # new file is better
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, maniac_repeats {maniac_repeats}, \033[04mmaniac_threshold {maniac_threshold}\033[0m, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, max_palette_size {max_palette_size}, ACB=Auto, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=best_dict['maniac_repeats'], maniac_threshold=maniac_threshold, maniac_min_size=maniac_min_size, maniac_divisor=maniac_divisor, max_palette_size=max_palette_size, A="", INT="", RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						best_dict['maniac_threshold'] = maniac_threshold
						output_best = output
						best_dict['size'] = size_new
						best_dict['count'] = count
						size_increased_times = 0
						arr_index = 0
					else:
						size_increased_times += 1
						if (size_increased_times >= giveUp_maniac_threshold):
							break;
				maniac_threshold = best_dict['maniac_threshold']
				size_increased_times = 0
				# we can't change step after entering the loop because list(range(1, var)) is precalculated
				# use different loop type

				maniac_divisor = 1
				maniac_divisor_step = 1
				maniac_divisor_step_upped = 0 # if True; maniac_divisor_step == 10
				while (maniac_divisor < range_maniac_divisor):
					showActivity()

					raw_command = [flif_binary, flif_to_flif, ('--maniac-repeats=' + str(best_dict['maniac_repeats'])),   ('--maniac-threshold=' + str(best_dict['maniac_threshold'])),   ('--maniac-divisor=' + str(maniac_divisor)),  INFILE, interlace_flag, '/dev/stdout']
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)

					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size': max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


					if (best_dict['size'] > size_new): # new file is better
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, maniac_repeats {maniac_repeats}, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, \033[04mmaniac_divisor {maniac_divisor}\033[0m, max_palette_size: {max_palette_size}, ACB=Auto, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=str(best_dict['maniac_repeats']), maniac_threshold=str(best_dict['maniac_threshold']), maniac_min_size=maniac_min_size, maniac_divisor=maniac_divisor, max_palette_size=max_palette_size, A="", INT="", RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						best_dict['maniac_divisor'] = maniac_divisor
						output_best=output
						best_dict['size'] = size_new
						best_dict['count'] = count
						size_increased_times = 0
						arr_index = 0
					else:
						size_increased_times += 1
						if ((maniac_divisor >= 100) and (maniac_divisor_step_upped == 0)): # increase the loop stepping to speed things up
							maniac_divisor_step = 10
							maniac_divisor_step_upped = 1
						if ((maniac_divisor >= 1000) and (maniac_divisor_step_upped == 1)):
							maniac_divisor_step = 100
							maniac_divisor_step_upped = 2
						if ((maniac_divisor >= 5000) and (maniac_divisor_step_upped == 2)):
							maniac_divisor_step = 1000
							maniac_divisor_step_upped = 3
						if ((maniac_divisor >= 13000) and (maniac_divisor_step_upped == 3)):
							maniac_divisor_step = 10000
							maniac_divisor_step_upped = 4
						if (size_increased_times >= give_up_after):
							if (maniac_divisor < 268435453): # try max maniac_divisor
								maniac_divisor = 268435454
								continue
							break;

					if (maniac_divisor >= range_maniac_divisor):
						break
					maniac_divisor += maniac_divisor_step
				maniac_divisor = best_dict['maniac_divisor']


				size_increased_times = 0
				for maniac_min_size in list(range(0, range_maniac_min_size, 1)):
					showActivity()


					raw_command = [flif_binary, flif_to_flif, ('--maniac-repeats=' + str(best_dict['maniac_repeats'])), ('--maniac-min-size=' + str(maniac_min_size)), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])), ('--maniac-divisor=' + str(best_dict['maniac_divisor'])),  INFILE, interlace_flag, '/dev/stdout']
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)

					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size': max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


					if (best_dict['size'] > size_new): # new file is better
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, maniac_repeats {maniac_repeats}, maniac_threshold {maniac_threshold}, \033[04mmaniac_min_size {maniac_min_size}\033[0m, maniac_divisor {maniac_divisor}, max_palette_size: {max_palette_size}, ACB=Auto, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=str(best_dict['maniac_repeats']), maniac_threshold=(best_dict['maniac_threshold']), maniac_min_size=maniac_min_size, maniac_divisor=str(best_dict['maniac_divisor']), max_palette_size=max_palette_size,  A="", INT="", RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						best_dict['maniac_min_size'] = maniac_min_size
						output_best=output
						best_dict['size'] = size_new
						best_dict['count'] = count
						size_increased_times = 0
						arr_index = 0
					else:
						size_increased_times += 1
						if (size_increased_times >= give_up_after):
							break;
				maniac_min_size = best_dict['maniac_min_size']



				size_increased_times = 0
				for chance_cutoff in list(range(1, range_chance_cutoff, 1)):
					showActivity()
					raw_command = [flif_binary, flif_to_flif,  ('--chance-cutoff=' + str(chance_cutoff)), ('--maniac-repeats=' + str(best_dict['maniac_repeats'])), ('--maniac-min-size=' + str(best_dict['maniac_min_size'])), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])),  ('--maniac-divisor=' + str(best_dict['maniac_divisor'])),  INFILE, interlace_flag, '/dev/stdout']
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)

					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


					if (best_dict['size'] > size_new): # new file is better
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early  [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, maniac_repeats {maniac_repeats}, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, max_palette_size: {max_palette_size}, \033[04mchance_cutoff {chance_cutoff}\033[0m, ACB=Auto, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=str(best_dict['maniac_repeats']), maniac_threshold=str(best_dict['maniac_threshold']), maniac_min_size=maniac_min_size, maniac_divisor=str(best_dict['maniac_divisor']), max_palette_size=max_palette_size,  A="", chance_cutoff=chance_cutoff, INT="", RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						best_dict['chance_cutoff'] = chance_cutoff
						output_best=output
						best_dict['size']=size_new
						best_dict['count'] = count
						size_increased_times = 0
						arr_index = 0
					else:
						size_increased_times += 1
						if (size_increased_times >= give_up_after):
							break;
				chance_cutoff = best_dict['chance_cutoff']


				size_increased_times = 0
				for chance_alpha in list(range(4, range_chance_alpha, 1)):
					showActivity()
					raw_command = [flif_binary, flif_to_flif, ('--chance-cutoff=' + str(best_dict['chance_cutoff'])),  ('--chance-alpha=' + str(chance_alpha)),         ('--maniac-repeats=' + str(best_dict['maniac_repeats'])), ('--maniac-min-size=' + str(best_dict['maniac_min_size'])), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])), ('--maniac-divisor=' + str(best_dict['maniac_divisor'])),  INFILE, interlace_flag, '/dev/stdout']
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)

					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


					if (best_dict['size'] > size_new): # new file is better
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, maniac_repeats {maniac_repeats}, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, max_palette_size: {max_palette_size}, chance_cutoff {chance_cutoff}, \033[04mchance_alpha {chance_alpha}\033[0m, ACB=Auto, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=str(best_dict['maniac_repeats']), maniac_threshold=str(best_dict['maniac_threshold']), maniac_min_size=maniac_min_size, maniac_divisor=str(best_dict['maniac_divisor']), max_palette_size=max_palette_size,  A="", chance_cutoff=chance_cutoff, chance_alpha=chance_alpha, INT="", RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						best_dict['chance_alpha'] = chance_alpha
						output_best=output
						best_dict['size']=size_new
						best_dict['count'] = count
						size_increased_times = 0
						arr_index = 0
					else:
						size_increased_times += 1
						if (size_increased_times >= give_up_after):
							break;
				chance_alpha = best_dict['chance_alpha']






				size_increased_times = 0
				for A in '--keep-alpha-zero', "":
					showActivity()

					raw_command =  [flif_binary,flif_to_flif,   ('--maniac-repeats=' + str(best_dict['maniac_repeats'])),    ('--chance-cutoff=' + str(best_dict['chance_cutoff'])),  ('--chance-alpha=' + str(best_dict['chance_alpha']))   , ('--maniac-min-size=' + str(best_dict['maniac_min_size'])), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])), ('--maniac-divisor=' + str(best_dict['maniac_divisor'])), A,  INFILE, interlace_flag, '/dev/stdout']
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)

					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


					if (best_dict['size'] > size_new): # new file is better
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, maniac_repeats {maniac_repeats}, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, max_palette_size: {max_palette_size}, ACB=Auto, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, \033[04mA={A}\033[0m, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=str(best_dict['maniac_repeats']), maniac_threshold=str(best_dict['maniac_threshold']), maniac_min_size=maniac_min_size, maniac_divisor=str(best_dict['maniac_divisor']), max_palette_size=max_palette_size, INT="", RGB="", PLC="", A=str(True if (A == "--keep-alpha-zero") else False), size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						best_dict['A'] = (A == "--keep-alpha-zero") # boolean
						#best_dict['A_arg'] = "--keep-alpha-zero" if (A) else "" # tring
						output_best=output
						best_dict['size']=size_new
						best_dict['count'] = count
						size_increased_times = 0
						arr_index = 0
					else:
						size_increased_times += 1
						if (size_increased_times >= give_up_after):
							break;
				A = best_dict['A']





				size_increased_times = 0

				max_palette_size_range = set(chain(range(0, 11), range(inf['colors']-5, inf['colors']+10)))
				for max_palette_size in max_palette_size_range:
					showActivity()
					if ((max_palette_size < 0) or (max_palette_size > 30000)) : # in case inf['colors']  is >5
						continue

					raw_command = [flif_binary,flif_to_flif,  ('--maniac-repeats=' + str(best_dict['maniac_repeats'])) ,('--chance-cutoff=' + str(best_dict['chance_cutoff'])),  ('--chance-alpha=' + str(best_dict['chance_alpha'])), ('--maniac-min-size=' + str(best_dict['maniac_min_size'])), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])), ('--maniac-divisor=' + str(best_dict['maniac_divisor'])),('--max-palette-size=' + str(max_palette_size)),  INFILE, interlace_flag, '/dev/stdout']
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)

					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':str(best_dict['maniac_min_size']), 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


					if (best_dict['size'] > size_new): # new file is better
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, maniac_repeats {maniac_repeats}, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, \033[04mmax_palette_size {max_palette_size}\033[0m, ACB=Auto, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=str(best_dict['maniac_repeats']), maniac_threshold=str(best_dict['maniac_threshold']), maniac_min_size=str(best_dict['maniac_min_size']), maniac_divisor=str(best_dict['maniac_divisor']), max_palette_size=max_palette_size, A=best_dict['A'], INT=INTERLACE, RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						output_best=output
						best_dict['size']=size_new
						best_dict['count'] = count
						best_dict['max_palette_size'] = max_palette_size
						size_increased_times = 0
						arr_index = 0


				max_palette_size = best_dict['max_palette_size']

				# don't remove this, it still pays out here and there
				size_increased_times_maniac_repeats = 0 # reset since first run
				for maniac_repeats in list(range(0, range_maniac_repeats)):
					showActivity()

					raw_command =  [flif_binary,flif_to_flif,  ('--maniac-repeats=' + str(maniac_repeats)),  ('--chance-cutoff=' + str(best_dict['chance_cutoff'])),  ('--chance-alpha=' + str(best_dict['chance_alpha'])),   ('--maniac-min-size=' + str(best_dict['maniac_min_size'])), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])), ('--maniac-divisor=' + str(best_dict['maniac_divisor'])),('--max-palette-size=' + str(best_dict['max_palette_size'])) ,  INFILE, interlace_flag, '/dev/stdout'] 
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)

					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':str(maniac_repeats), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':str(best_dict['maniac_min_size']), 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':str(best_dict['max_palette_size']), 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


					if (best_dict['size'] > size_new): # new file is smaller
						size_increased_times_maniac_repeats = 0 # reset break-counter
						output_best = output
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, \033[04mmaniac_repeats {maniac_repeats}\033[0m, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, max_palette_size: {max_palette_size}, ACB=Auto, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=maniac_repeats, maniac_threshold=best_dict['maniac_threshold'], maniac_min_size=best_dict['maniac_min_size'], maniac_divisor=best_dict['maniac_divisor'], max_palette_size=best_dict['max_palette_size'], A=best_dict['A'], INT=INTERLACE, RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						best_dict['count'] = count
						best_dict['size'] = size_new
						best_dict['maniac_repeats'] = maniac_repeats
						arr_index = 0
					else:
						size_increased_times_maniac_repeats += 1
						if (size_increased_times_maniac_repeats >= best_dict['maniac_repeats'] + 4):
							break; # break out of loop, we have wasted enough time here
				maniac_repeats = best_dict['maniac_repeats']
			else: #   (best_dict['maniac_repeats'] == 0),  still try P
				size_increased_times = 0

				max_palette_size_range = set(chain(range(0, 11), range(inf['colors']-5, inf['colors']+10)))
				for max_palette_size in max_palette_size_range:
					showActivity()
					if ((max_palette_size < 0) or (max_palette_size > 30000)) : # in case inf['colors']  is >5
						continue


					raw_command =  [flif_binary,flif_to_flif, ('--maniac-repeats=' + str(maniac_repeats))  , ('--chance-cutoff=' + str(best_dict['chance_cutoff'])),  ('--chance-alpha=' + str(best_dict['chance_alpha'])),  ('--maniac-min-size=' + str(best_dict['maniac_min_size'])), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])), ('--maniac-divisor=' + str(best_dict['maniac_divisor'])),    ('--max-palette-size=' + str(max_palette_size))   ,  INFILE, interlace_flag, '/dev/stdout']
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)


					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)

					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':str(best_dict['maniac_min_size']), 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


					if (best_dict['size'] > size_new): # new file is better
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, maniac_repeats {maniac_repeats}, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, \033[04mmax_palette_size {max_palette_size}\033[0m, ACB=Auto, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=str(best_dict['maniac_repeats']), maniac_threshold=str(best_dict['maniac_threshold']), maniac_min_size=str(best_dict['maniac_min_size']), maniac_divisor=str(best_dict['maniac_divisor']), max_palette_size=max_palette_size, A=best_dict['A'], INT=INTERLACE, RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						output_best=output
						best_dict['size']=size_new
						best_dict['count'] = count
						best_dict['max_palette_site'] = max_palette_size
						size_increased_times = 0
						arr_index = 0


				max_palette_size = best_dict['max_palette_size']



			# auto color buckets:

			best_ACB="Auto"
			for acb in "--acb", "--no-acb":
				showActivity()

				raw_command = [flif_binary,flif_to_flif, acb,  ('--maniac-repeats=' + str(maniac_repeats)),('--chance-cutoff=' + str(best_dict['chance_cutoff'])),  ('--chance-alpha=' + str(best_dict['chance_alpha'])),     ('--maniac-min-size=' + str(best_dict['maniac_min_size'])), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])), ('--maniac-divisor=' + str(best_dict['maniac_divisor'])),  ('--max-palette-size=' + str(max_palette_size)) ,  INFILE, interlace_flag, '/dev/stdout']
				sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
				proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

				count +=1
				output = proc.stdout.read()
				size_new = sys.getsizeof(output)

				ACB = (acb == "--acb")


				if (DEBUG):
					debug_array.append([{'Nr':count, 'maniac_repeats':maniac_repeats, 'maniac_threshold':maniac_threshold, 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


				if (best_dict['size'] >= size_new): # new file is smaller
					size_increased_times_maniac_repeats = 0 # reset break-counter
					output_best = output
					if (best_dict['size'] > size_new): # is actually better,  hack to avoid "-0 b"
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, maniac_repeats {maniac_repeats}, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, max_palette_size: {max_palette_size}, \033[04mACB={ACB}\033[0m, INTERLACE={INT}, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=best_dict['maniac_repeats'], maniac_threshold=best_dict['maniac_threshold'], maniac_min_size=best_dict['maniac_min_size'], maniac_divisor=best_dict['maniac_divisor'], max_palette_size=best_dict['max_palette_size'], A=best_dict['A'], INT="", ACB=str(ACB), RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
					best_dict['count'] = count
					best_dict['size'] = size_new
					arr_index = 0
					best_dict['ACB'] = ACB


			# check -C and -R and -C -R
			for plc_option in "--no-plc", "":
				for rgb_option in "--rgb", "":

					if (plc_option == rgb_option == ""): # none, skip
						continue

					PLC = ("--no-plc" == plc_option)
					RGB = ("--rgb" == rgb_option)


					raw_command  = [flif_binary,flif_to_flif, acb, ('--chance-cutoff=' + str(best_dict['chance_cutoff'])),  ('--chance-alpha=' + str(best_dict['chance_alpha'])),  ('--maniac-repeats=' + str(maniac_repeats)),   ('--maniac-min-size=' + str(best_dict['maniac_min_size'])), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])), ('--maniac-divisor=' + str(best_dict['maniac_divisor'])),('--max-palette-size=' + str(max_palette_size)), plc_option, rgb_option,  INFILE, interlace_flag, '/dev/stdout']
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

					showActivity()
					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)
					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':maniac_repeats, 'maniac_threshold':maniac_threshold, 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])
					if (best_dict['size'] > size_new): # new file is smaller
						if (size_orig > size_new):
							perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
							perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
							print("{count}, maniac_repeats {maniac_repeats}, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, max_palette_size: {max_palette_size}, ACB {ACB}, INTERLACE={INT}, \033[04mPLC={PLC}, RGB={RGB}\033[0m, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=best_dict['maniac_repeats'], maniac_threshold=best_dict['maniac_threshold'], maniac_min_size=best_dict['maniac_min_size'], maniac_divisor=best_dict['maniac_divisor'], max_palette_size=best_dict['max_palette_size'], A=best_dict['A'], ACB=str(ACB), INT="", RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						size_increased_times_maniac_repeats = 0 # reset break-counter
						output_best = output
						best_dict['count'] = count
						best_dict['size'] = size_new
						best_dict['PLC'] = PLC
						best_dict['RGB'] = RGB



			if not (INTERLACE_FORCE):
				best_interl = False
				for interl in "--no-interlace", "--interlace":
					showActivity()


					raw_command  =  [flif_binary,flif_to_flif,  ('--maniac-repeats=' + str(maniac_repeats)), acb, ('--chance-cutoff=' + str(best_dict['chance_cutoff'])),  ('--chance-alpha=' + str(best_dict['chance_alpha'])),     ('--maniac-min-size=' + str(best_dict['maniac_min_size'])), ('--maniac-threshold=' + str(best_dict['maniac_threshold'])), ('--maniac-divisor=' + str(best_dict['maniac_divisor'])), '-p', ('--max-palette-size=' + str(best_dict['max_palette_size'])), INFILE, interl, '/dev/stdout'] 
					sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
					proc = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE)

					count +=1
					output = proc.stdout.read()
					size_new = sys.getsizeof(output)


					INTERL = (interl == "--interlace")

					if (DEBUG):
						debug_array.append([{'Nr':count, 'maniac_repeats':maniac_repeats, 'maniac_threshold':maniac_threshold, 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


					if (best_dict['size'] > size_new): # new file is smaller
						size_increased_times_maniac_repeats = 0 # reset break-counter
						output_best = output
						if (best_dict['size'] > size_new): # is actually better,  hack to avoid "-0 b"
							if (size_orig > size_new):
								perc_change = str(((size_new-best_dict['size']) / best_dict['size'])*100)
								perc_change = "-0.000" if ("e" in perc_change) else perc_change[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
								print("{count}, maniac_repeats {maniac_repeats}, maniac_threshold {maniac_threshold}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, max_palette_size: {max_palette_size}, ACB {ACB}, \033[04mINTERLACE={INT} \033[0m, PLC={PLC}, RGB={RGB}, A={A}, size {size} b, (-{size_change} b, {perc_change}%)".format(count=count, maniac_repeats=best_dict['maniac_repeats'], maniac_threshold=best_dict['maniac_threshold'], umaniac_min_size=best_dict['maniac_min_size'], maniac_divisor=best_dict['maniac_divisor'], max_palette_size=best_dict['max_palette_size'], A=best_dict['A'], ACB="", INT="", RGB="", PLC="", size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=perc_change))
						best_dict['count'] = count
						best_dict['size'] = size_new
						best_dict['INT'] = INTERL
						arr_index = 0
						best_interl=INTERL
				#INTERLACE = best_dict['INT']


		else: # bruteforce == true
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
									proc = subprocess.Popen([flif_binary, flif_to_flif, acb,  '-M', str(M), '-S', str(S), '-D', str(D),   '-r', str(N), str(INFILE), str(interl), '/dev/stdout'], stdout=subprocess.PIPE)
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
										debug_array.append([{'Nr':count, 'N':N, 'S':S, 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


									if (size_new < best_dict['size']): # new file is smaller
										output_best = output
										best_dict['count']=count
										print("{count}, N {N}, S {S}, maniac_min_size {maniac_min_size}, maniac_divisor {maniac_divisor}, max_palette_size: {max_palette_size}, ACB {ACB}, interlace: {INTERLACE}, size {size} b, better than {run_best} which was {size_best} b (-{size_change} b, {perc_change}%)".format(count=count, N=N, S=S, maniac_min_size=maniac_min_size, maniac_divisor=maniac_divisor, max_palette_size=max_palette_size, ACB=str(ACB), INTERLACE=str(INTERLACE), size=size_new, run_best=best_dict['count'], size_best=best_dict['size'], size_change=best_dict['size']-size_new, perc_change=str(((size_new-best_dict['size']) / best_dict['size'])*100)[:6]))
										best_dict['size'] = size_new
										best_dict['N'] = N
										best_dict['INT'] = INTERLACE
										best_dict['S'] = S
										best_dict['M'] = M
										best_dict['D'] = D
										best_dict['ACB'] = ACB



		if (COMPARE): # how does flifcrush compare to default flif conversion?
			diff_to_flif_byte = best_dict['size'] - size_flifdefault
			if (best_dict['size'] > size_flifdefault):
				print("WARNING: flifcrush failed reducing reducing size better than default flif, please report!")
			diff_to_flif_perc = (((size_flifdefault-best_dict['size']) / best_dict['size'])*100)
			print("\033[K", end="") # clear previous line
			print("\nComparing flifcrush (" + str(best_dict['size']) +" b) to default flif (" + str(size_flifdefault)  + " b): " + str(diff_to_flif_byte) + " b which are " + str(diff_to_flif_perc)[:6] + " %")


		# write final best file
		save_file()

		if (DEBUG):
			for index, val in enumerate(debug_array):
				print("run:", val[0]['Nr'], "  maniac_repeats:", val[0]['maniac_repeats'],"  maniac_threshold:",  val[0]['maniac_threshold'],"   maniac_min_size:",  val[0]['maniac_min_size'],"  maniac_split_divisor:", val[0]['maniac_split_divisor'],"  max_palette_size:", val[0]['max_palette_size'], "ACB", val[0]['ACB'],"INT", val[0]['INT'], "  size:", val[0]['size'] )
	if (files_count_glob > 1):
		if (COMPARE):
			print("In total, reduced " + str(size_before_glob) + " b to " + str(size_after_glob) + " b, " + str(files_count_glob) + " files , " + str(((size_after_glob - size_before_glob)/size_before_glob)*100)[:6] + "%")
			print("Flif default would have been: " + str(size_flifdefault_glob) + " b")
		else:
			print("In total, reduced " + str(size_before_glob) + " b to " + str(size_after_glob) + " b, " + str(files_count_glob) + " files , " + str(((size_after_glob - size_before_glob)/size_before_glob)*100)[:6] + "%")
except KeyboardInterrupt:
	print("\033[K", end="") # clear previous line
	print("\rTermination requested, saving best file so far...\n")
	try: # double ctrl+c shall quit immediately
		save_file()
		if (files_count_glob > 1):
			if (COMPARE):
				print("In total, reduced " + str(size_before_glob) + " b to " + str(size_after_glob) + " b, " + str(files_count_glob) + " files , " + str(((size_after_glob - size_before_glob)/size_before_glob)*100)[:6] + "%")
				print("Flif default would have been: " + str(size_flifdefault_glob) + " b")
			else:
				print("In total, reduced " + str(size_before_glob) + " b to " + str(size_after_glob) + " b, " + str(files_count_glob) + " files , " + str(((size_after_glob - size_before_glob)/size_before_glob)*100)[:6] + "%")
	except KeyboardInterrupt: # double ctrl+c
		print("\033[K", end="") # clear previous line
		print("Terminated by user.")



