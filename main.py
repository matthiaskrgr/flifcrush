#!/usr/bin/env python3

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


# colors for stdout
txt_ul = TXT_UL = '\033[04m' # underline
txt_res = TXT_RES = '\033[0m' #reset

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
global output_best
output_best="none"
global arr_index
global progress_array
arr_index = 0
#progress_array="|/-\\"
#progress_array=".o0OOo."
progress_array=" ▁▂▃▄▅▆▇█▇▆▅▄▃▁"
arrlen=len(progress_array)

# prints activity indicator (some kind of ascii 'animation')
def showActivity(func_arg, size_new):
	global arr_index
	arr_index+=1
	if (arr_index == arrlen):
		arr_index = 0
	diff_best = best_dict['size'] - size_new
	
	print(progress_array[arr_index] + " " + str(count) + ": "  + str(func_arg) +  ", size: " + str(size_new) + " b        ", end="\r",flush=True)

# save .flif file that had the best combination of parameters 
def save_file():
	global output_best
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
		size_diff = size_orig - best_dict['size']

		print("\033[K", end="")
		print("reduced from " + str(size_orig) + " b to "+ str(best_dict['size']) + " ( -"+ str(size_diff) + " b, "+ str((( best_dict['size'] - size_orig)/ size_orig )*100)[:6] + " %) " + str(count) +  " flif calls.\n\n")
		#print("reduced from {size_orig}b to {size_flif}b ({size_diff}b, {perc_change} %) via \n [{bestoptim}] and {cnt} flif calls.\n\n".format(size_orig = os.path.getsize(INFILE), size_flif=size_flif, size_diff=(size_flif - size_orig), perc_change=str(((size_flif-size_orig) / size_orig)*100)[:6],  bestoptim=str("maniac repeats:" + str(best_dict['maniac_repeats']) + " maniac_threshold:" + str(best_dict['maniac_threshold']) + " maniac_min_size:" + str(best_dict['maniac_min_size'])+ " maniac_divisor:" + str(best_dict['maniac_divisor']) + " max_palette_size:" + str(best_dict['max_palette_size']) + " chance-cutoff:" + str(best_dict['chance_cutoff'])  + " chance-alpha:" + str(best_dict['chance_alpha']) +  " ACB:" + str(best_dict['ACB']) + " INTERLACE:" + str(best_dict['INT']) + " PLC:" + str(best_dict['PLC']) + " RGB:" +  str(best_dict['RGB']) +  " A:" + str(best_dict['A'])), cnt=str(count)), end="\r")

		if (best_dict['size'] > size_orig):
			print("WARNING: failed to reduce size")

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

def pct_of_best(size_new):
	# if best size was 100 and new file is 50, return  50 %
	pct = str(((size_new - best_dict['size']) / best_dict['size'])*100)
	pct = "-0.000" if ("e" in pct) else pct[:6] # due to too-early [:6], '8.509566454608271e-07' would become "8.509"
	return pct


def crush_maniac_repeats(): # -N 
	# globals we modify
	global best_dict
	global count
	global arr_index
	global output_best

	# locals
	range_maniac_repeats = 20 # try 0 -20
	max_attempts = 5 # give up after 5 unsuccesfull attempts
	failed_attempts = 0

	for maniac_repeats in range(0, range_maniac_repeats):
		count += 1
		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(maniac_repeats)), 				# <-
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])),
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(best_dict['max_palette_size'])),

			best_dict['interlace'].flag,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			best_dict['no_ycocg'].flag,
			best_dict['keep_invisible_rgb'].flag,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity("maniac repeats: " + str(maniac_repeats), size_new)

		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':maniac_repeats, 'maniac_threshold':maniac_threshold, 'maniac_min_size':maniac_min_size, 'maniac_divisor':maniac_divisor, 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

		if ((best_dict['size'] > size_new) or (count==1)): # new file is smaller // count==1: make sure best_dict is filled with first values we obtain. this way we still continue crushing even if initial N-run does not reduce size smaller than size_orig
			failed_attempts = 0 # reset break-counter
			output_best = output
			if (size_orig > size_new):

				#run_best = "orig" if (count == 1) else best_dict['count']

				size_change = best_dict['size']-size_new
				perc_change = pct_of_best(size_new)
				print("\033[K", end="")
				print(
					 str(count) +
					 " maniac:[ " +  TXT_UL + "repeat: " + str(maniac_repeats) + TXT_RES +
					 " threshold: " + str(best_dict['maniac_threshold']) +
					 " min_size: " + str(best_dict['maniac_min_size']) +
					 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac

					 " chance:[ cutoff: " + str(best_dict['chance_cutoff']) +
					 " alpha: " + str(best_dict['chance_alpha']) + " ] " + # ] chance
					 " palette: " + str(best_dict['max_palette_size']) +

					 " itlc: " + str(best_dict['interlace'].bool) +
					 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
					 " Cbuck: " + str(best_dict['force_color_buckets'].bool) +
					 " no_ycocg: " + str(best_dict['no_ycocg'].bool) +
					 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

					 " size " + str(size_new) + " b " +
					 "-" + str(size_change) + " b " +
					 perc_change + " %")

			best_dict['size'] = size_new
			best_dict['count'] = count
			best_dict['maniac_repeats'] = maniac_repeats
			arr_index = 0
		else: # file is not smaller
			failed_attempts += 1
			if (failed_attempts >= max_attempts):
				return; # break out of loop, we have wasted enough time here


def crush_maniac_threshold(): # -T
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	#locals
	range_maniac_threshold = 40
	max_attempts = 40
	failed_attempts = 0

	for maniac_threshold in range(1, range_maniac_threshold):

		# skip maniac_threshold 1-4, it takes too much ram in extreme cases
		if (maniac_threshold <= 4):  
			continue

		count += 1

		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(maniac_threshold)),				# <-
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])),
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(best_dict['max_palette_size'])),

			best_dict['interlace'].flag,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			best_dict['no_ycocg'].flag,
			best_dict['keep_invisible_rgb'].flag,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 


		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity(("maniac threshold: " + str(maniac_threshold)), size_new)



		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':best_dict['maniac_repeats'], 'maniac_threshold':maniac_threshold, 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size': max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

		if (best_dict['size'] > size_new): # new file is smaller 
			failed_attempts = 0 # reset break-counter
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)
			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " " + TXT_UL + "threshold: " + str(maniac_threshold) + TXT_RES +
				 " min_size: " + str(best_dict['maniac_min_size']) +
				 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac

				 " chance:[ cutoff: " + str(best_dict['chance_cutoff']) +
				 " alpha: " + str(best_dict['chance_alpha']) + " ] " + # ] chance
				 " palette: " + str(best_dict['max_palette_size']) +

				 " itlc: " + str(best_dict['interlace'].bool) +
				 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
				 " Cbuck: " + str(best_dict['force_color_buckets'].bool) +
				 " no_ycocg: " + str(best_dict['no_ycocg'].bool) +
				 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['size'] = size_new
			best_dict['count'] = count
			best_dict['maniac_threshold'] = maniac_threshold
			arr_index = 0
		else:
			failed_attempts += 1
			if (failed_attempts >= max_attempts):
				return;


def crush_maniac_divisor(): # -D
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	#locals
	range_maniac_divisor = 268435455
	maniac_divisor = 1
	maniac_divisor_step = 1
	maniac_divisor_step_upped = 0 # if True; maniac_divisor_step == 10
	failed_attempts = 0
	max_attempts = 200
	while (maniac_divisor < range_maniac_divisor):
		count +=1


		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(maniac_divisor)), 				# <-
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(best_dict['max_palette_size'])),

			best_dict['interlace'].flag,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			best_dict['no_ycocg'].flag,
			best_dict['keep_invisible_rgb'].flag,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity("maniac divisor: " + str(maniac_divisor), size_new)

		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size': max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


		if (best_dict['size'] > size_new): # new file is smaller 
			failed_attempts = 0 # reset break-counter
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)
			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " threshold: " + str(best_dict['maniac_threshold']) + 
				 " min_size: " + str(best_dict['maniac_min_size']) +
				" " + TXT_UL +  "divisor: " + str(maniac_divisor) + TXT_RES + " ] " + # ] maniac      <----

				 " chance:[ cutoff: " + str(best_dict['chance_cutoff']) +
				 " alpha: " + str(best_dict['chance_alpha']) + " ] " + # ] chance
				 " palette: " + str(best_dict['max_palette_size']) +

				 " itlc: " + str(best_dict['interlace'].bool) +
				 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
				 " Cbuck: " + str(best_dict['force_color_buckets'].bool) +
				 " no_ycocg: " + str(best_dict['no_ycocg'].bool) +
				 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['size'] = size_new
			best_dict['count'] = count
			best_dict['maniac_divisor'] = maniac_divisor
			arr_index=0
		else:
			failed_attempts += 1
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
			if (failed_attempts >= max_attempts):
				if (maniac_divisor < 268435453): # try max maniac_divisor
					maniac_divisor = 268435454
					continue
				break;

		if (maniac_divisor >= range_maniac_divisor):
			break
		maniac_divisor += maniac_divisor_step


def crush_maniac_min_size(): # -M
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	#locals
	range_maniac_min_size = 3000
	max_attempts = 200
	failed_attempts = 0


	for maniac_min_size in range(0, range_maniac_min_size):
		count +=1

		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size': max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])
			
		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])), 
			('--maniac-min-size=' + str(maniac_min_size)),				# <-

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(best_dict['max_palette_size'])),

			best_dict['interlace'].flag,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			best_dict['no_ycocg'].flag,
			best_dict['keep_invisible_rgb'].flag,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity("maniac min size: " + str(maniac_min_size), size_new)

		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size': max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


		if (best_dict['size'] > size_new): # new file is smaller 
			failed_attempts = 0 # reset break-counter
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)
			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " threshold: " + str(best_dict['maniac_threshold']) + 
				 " " + TXT_UL + "min_size: " + str(maniac_min_size)  + TXT_RES +                           #  <----
				 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac     

				 " chance:[ cutoff: " + str(best_dict['chance_cutoff']) +
				 " alpha: " + str(best_dict['chance_alpha']) + " ] " + # ] chance
				 " palette: " + str(best_dict['max_palette_size']) +

				 " itlc: " + str(best_dict['interlace'].bool) +
				 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
				 " Cbuck: " + str(best_dict['force_color_buckets'].bool) +
				 " no_ycocg: " + str(best_dict['no_ycocg'].bool) +
				 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['maniac_min_size'] = maniac_min_size
			best_dict['size'] = size_new
			best_dict['count'] = count
			failed_attempts = 0
			arr_index = 0
		else:
			failed_attempts += 1
			if (failed_attempts >= max_attempts):
				break;



def crush_chance_cutoff():
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	#locals
	range_chance_cutoff = 128
	failed_attempts = 0
	max_attempts=200

	for chance_cutoff in range(1, range_chance_cutoff):
		count += 1

		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])), 
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(chance_cutoff)),					# <-
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(best_dict['max_palette_size'])),

			best_dict['interlace'].flag,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			best_dict['no_ycocg'].flag,
			best_dict['keep_invisible_rgb'].flag,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity("chance cutoff: " + str(chance_cutoff), size_new)


		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


		if (best_dict['size'] > size_new): # new file is smaller 
			failed_attempts = 0 # reset break-counter
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)
			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " threshold: " + str(best_dict['maniac_threshold']) + 
				 " min_size: " + str(best_dict['maniac_min_size'])  + 
				 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac     

				 " chance:[ "+ TXT_UL + "cutoff: "  + str(chance_cutoff) +  TXT_RES +                           #  <----
				 " alpha: " + str(best_dict['chance_alpha']) + " ] " + # ] chance
				 " palette: " + str(best_dict['max_palette_size']) +

				 " itlc: " + str(best_dict['interlace'].bool) +
				 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
				 " Cbuck: " + str(best_dict['force_color_buckets'].bool) +
				 " no_ycocg: " + str(best_dict['no_ycocg'].bool) +
				 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['chance_cutoff'] = chance_cutoff
			best_dict['size'] = size_new
			best_dict['count'] = count
			failed_attempts = 0
			arr_index = 0
		else:
			failed_attempts += 1
			if (failed_attempts >= max_attempts):
				break;





def crush_chance_alpha(): # -Z
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	#locals
	range_chance_alpha = 128
	failed_attempts = 0
	max_attempts=200

	for chance_alpha in range(2, range_chance_alpha):
		count += 1

		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])), 
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(chance_alpha)),			# <-
			('--max-palette-size=' + str(best_dict['max_palette_size'])),

			best_dict['interlace'].flag,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			best_dict['no_ycocg'].flag,
			best_dict['keep_invisible_rgb'].flag,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity("chance alpha: " + str(chance_alpha), size_new)


		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':maniac_min_size, 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])


		if (best_dict['size'] > size_new): # new file is smaller 
			failed_attempts = 0 # reset break-counter
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)
			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " threshold: " + str(best_dict['maniac_threshold']) + 
				 " min_size: " + str(best_dict['maniac_min_size'])  + 
				 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac     

				 " chance:[ cutoff: "  + str(best_dict['chance_cutoff']) + 
				 " "+ TXT_UL + "alpha: " + str(best_dict['chance_alpha']) + TXT_RES + " ] " + # ] chance              # <---.
				 " palette: " + str(best_dict['max_palette_size']) +

				 " itlc: " + str(best_dict['interlace'].bool) +
				 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
				 " Cbuck: " + str(best_dict['force_color_buckets'].bool) +
				 " no_ycocg: " + str(best_dict['no_ycocg'].bool) +
				 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['chance_alpha'] = chance_alpha
			best_dict['size'] = size_new
			best_dict['count'] = count
			failed_attempts = 0
			arr_index = 0
		else:
			failed_attempts += 1
			if (failed_attempts >= max_attempts):
				break;


def crush_max_palette_size():
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	#locals
	range_chance_alpha = 128
	failed_attempts = 0
	max_attempts=200


	max_palette_size_range = set(chain(range(0, 11), range(inf['colors']-5, inf['colors']+10)))
	for max_palette_size in max_palette_size_range:
		# according to flif code -32000 is also valid, perhaps try this at some point
		if ((max_palette_size < 0) or (max_palette_size > 32000)) : # in case inf['colors']  is >5
			continue

		count +=1


		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])), 
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(max_palette_size)),			#<-

			best_dict['interlace'].flag,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			best_dict['no_ycocg'].flag,
			best_dict['keep_invisible_rgb'].flag,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity(("max palette size: " + str(max_palette_size)), size_new)


		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':str(best_dict['maniac_min_size']), 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])



		if (best_dict['size'] > size_new): # new file is smaller 
			failed_attempts = 0 # reset break-counter
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)
			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " threshold: " + str(best_dict['maniac_threshold']) + 
				 " min_size: " + str(best_dict['maniac_min_size'])  + 
				 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac     

				 " chance:[ cutoff: "  + str(best_dict['chance_cutoff']) + 
				 " alpha: " + str(best_dict['chance_alpha']) +  " ] " + # ] chance
				 " "+ TXT_UL + "palette: " + str(best_dict['max_palette_size']) + TXT_RES +                 # <---.

				 " itlc: " + str(best_dict['interlace'].bool) +
				 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
				 " Cbuck: " + str(best_dict['force_color_buckets'].bool) +
				 " no_ycocg: " + str(best_dict['no_ycocg'].bool) +
				 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['max_palette_size'] = max_palette_size
			best_dict['size'] = size_new
			best_dict['count'] = count
			failed_attempts = 0
			arr_index = 0
		else:
			failed_attempts += 1
			if (failed_attempts >= max_attempts):
				break;





def crush_keep_invisible_rgb():
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	for keep_invisible_rgb in True, False:
		count +=1

		flagstr = ("--keep-invisible-rgb" if (keep_invisible_rgb) else "")

		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])), 
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(best_dict['max_palette_size'])),

			best_dict['interlace'].flag,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			best_dict['no_ycocg'].flag,
			flagstr,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity("keep invisibler rgb: " + str(keep_invisible_rgb), size_new)


		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':str(best_dict['maniac_min_size']), 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

		if (best_dict['size'] > size_new): # new file is smaller 
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)

			best_dict['keep_invisible_rgb'] = best_dict['keep_invisible_rgb']._replace(flag=flagstr)
			best_dict['keep_invisible_rgb'] = best_dict['keep_invisible_rgb']._replace(bool=keep_invisible_rgb)

			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " threshold: " + str(best_dict['maniac_threshold']) + 
				 " min_size: " + str(best_dict['maniac_min_size'])  + 
				 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac     

				 " chance:[ cutoff: "  + str(best_dict['chance_cutoff']) + 
				 " alpha: " + str(best_dict['chance_alpha']) +  " ] " + # ] chance
				 " palette: " + str(best_dict['max_palette_size']) + 

				 " itlc: " + str(best_dict['interlace'].bool) +
				 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
				 " Cbuck: " + str(best_dict['force_color_buckets'].bool) +
				 " no_ycocg: " + str(best_dict['no_ycocg'].bool) +
				 " " +  TXT_UL + "inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) + TXT_RES + #    < ------

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['size'] = size_new
			best_dict['count'] = count
			arr_index = 0











def crush_force_color_buckets():
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	for force_color_buckets in True, False:
		count +=1

		flagstr = ("--force-color-buckets" if (force_color_buckets) else "--no-color-buckets")

		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])), 
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(best_dict['max_palette_size'])),

			best_dict['interlace'].flag,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			flagstr,
			best_dict['keep_invisible_rgb'].flag,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity("force color buckets: " + str(force_color_buckets), size_new)


		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':str(best_dict['maniac_min_size']), 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

		if (best_dict['size'] > size_new): # new file is smaller 
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)

			best_dict['force_color_buckets'] = best_dict['force_color_buckets']._replace(flag=flagstr)
			best_dict['force_color_buckets'] = best_dict['force_color_buckets']._replace(bool=force_color_buckets)

			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " threshold: " + str(best_dict['maniac_threshold']) + 
				 " min_size: " + str(best_dict['maniac_min_size'])  + 
				 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac     

				 " chance:[ cutoff: "  + str(best_dict['chance_cutoff']) + 
				 " alpha: " + str(best_dict['chance_alpha']) +  " ] " + # ] chance
				 " palette: " + str(best_dict['max_palette_size']) + 

				 " itlc: " + str(best_dict['interlace'].bool) +
				 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
				 " " +  TXT_UL + "Cbuck: " + str(best_dict['force_color_buckets'].bool) + TXT_RES + # <-
				 " no_ycocg: " + str(best_dict['no_ycocg'].bool) +
				 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['size'] = size_new
			best_dict['count'] = count
			arr_index = 0



def crush_no_ycocg():
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	for force_no_ycocg in True, False:
		count +=1

		flagstr = ("--no-ycocg" if (force_no_ycocg) else "")

		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])), 
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(best_dict['max_palette_size'])),

			best_dict['interlace'].flag,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			flagstr,
			best_dict['keep_invisible_rgb'].flag,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity("no ycocg " + str(force_no_ycocg), size_new)


		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':str(best_dict['maniac_min_size']), 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

		if (best_dict['size'] > size_new): # new file is smaller 
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)

			best_dict['no_ycocg'] = best_dict['no_ycocg']._replace(flag=flagstr)
			best_dict['no_ycocg'] = best_dict['no_ycocg']._replace(bool=force_no_ycocg)

			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " threshold: " + str(best_dict['maniac_threshold']) + 
				 " min_size: " + str(best_dict['maniac_min_size'])  + 
				 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac     

				 " chance:[ cutoff: "  + str(best_dict['chance_cutoff']) + 
				 " alpha: " + str(best_dict['chance_alpha']) +  " ] " + # ] chance
				 " palette: " + str(best_dict['max_palette_size']) + 

				 " itlc: " + str(best_dict['interlace'].bool) +
				 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
				 " Cbuck: " + str(best_dict['force_color_buckets'].bool) +
				 " " +  TXT_UL + "no_ycocg: " + str(best_dict['no_ycocg'].bool) + TXT_RES + # <-
				 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['size'] = size_new
			best_dict['count'] = count
			arr_index = 0

def crush_no_channel_compact():
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	for no_channel_compact in True, False:
		count +=1

		flagstr = ("--no-channel-compact" if (no_channel_compact) else "")

		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])), 
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(best_dict['max_palette_size'])),


			best_dict['interlace'].flag,
			flagstr,
			best_dict['force_color_buckets'].flag,
			best_dict['no_ycocg'].flag,
			best_dict['keep_invisible_rgb'].flag,

			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity("no channel compact: " + str(no_channel_compact), size_new)


		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':str(best_dict['maniac_min_size']), 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

		if (best_dict['size'] > size_new): # new file is smaller 
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)

			best_dict['no_channel_compact'] = best_dict['no_channel_compact']._replace(flag=flagstr)
			best_dict['no_channel_compact'] = best_dict['no_channel_compact']._replace(bool=no_channel_compact)

			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " threshold: " + str(best_dict['maniac_threshold']) + 
				 " min_size: " + str(best_dict['maniac_min_size'])  + 
				 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac     

				 " chance:[ cutoff: "  + str(best_dict['chance_cutoff']) + 
				 " alpha: " + str(best_dict['chance_alpha']) +  " ] " + # ] chance
				 " palette: " + str(best_dict['max_palette_size']) + 

				 " itlc: " + str(best_dict['interlace'].bool) +
				 " " +  TXT_UL + "no_CC: " + str(best_dict['no_channel_compact'].bool) + TXT_RES +  # <- 
				 " Cbuck: " + str(best_dict['force_color_buckets'].bool) + 
				 " no_ycocg: " + str(best_dict['no_ycocg'].bool) +
				 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['size'] = size_new
			best_dict['count'] = count
			arr_index = 0




def crush_interlace():
	# globals
	global best_dict
	global count
	global arr_index
	global output_best

	for interlace in True, False:
		count +=1

		flagstr = ("--interlace" if (interlace) else "--no-interlace")

		raw_command = [
			flif_binary,
			flif_to_flif,

			('--maniac-repeats=' + str(best_dict['maniac_repeats'])),
			('--maniac-threshold=' + str(best_dict['maniac_threshold'])),
			('--maniac-divisor=' + str(best_dict['maniac_divisor'])), 
			('--maniac-min-size=' + str(best_dict['maniac_min_size'])),

			('--chance-cutoff=' + str(best_dict['chance_cutoff'])),
			('--chance-alpha=' + str(best_dict['chance_alpha'])),
			('--max-palette-size=' + str(best_dict['max_palette_size'])),

			flagstr,
			best_dict['no_channel_compact'].flag,
			best_dict['force_color_buckets'].flag,
			best_dict['no_ycocg'].flag,
			best_dict['keep_invisible_rgb'].flag,





			INFILE,
			interlace_flag,
			'/dev/stdout',
		] # = raw_command 

		sanitized_command = [x for x in raw_command if x ] # remove empty elements, if any
		output = subprocess.Popen(sanitized_command, stdout=subprocess.PIPE).stdout.read()
		size_new = sys.getsizeof(output)
		showActivity("interlace: " + str(interlace), size_new)


		#if (DEBUG):
		#	debug_array.append([{'Nr':count, 'maniac_repeats':str(best_dict['maniac_repeats']), 'maniac_threshold':str(best_dict['maniac_threshold']), 'maniac_min_size':str(best_dict['maniac_min_size']), 'maniac_divisor':str(best_dict['maniac_divisor']), 'max_palette_size':max_palette_size, 'ACB':ACB, 'INT': INTERLACE, 'size': size_new}])

		if (best_dict['size'] > size_new): # new file is smaller 
			output_best = output
			size_change = best_dict['size']-size_new
			perc_change = pct_of_best(size_new)

			best_dict['interlace'] = best_dict['interlace']._replace(flag=flagstr)
			best_dict['interlace'] = best_dict['interlace']._replace(bool=interlace)

			print("\033[K", end="")
			print(
				 str(count) +
				 " maniac [ repeat: " + str(best_dict['maniac_repeats']) +
				 " threshold: " + str(best_dict['maniac_threshold']) + 
				 " min_size: " + str(best_dict['maniac_min_size'])  + 
				 " divisor: " + str(best_dict['maniac_divisor']) + " ] " + # ] maniac     

				 " chance:[ cutoff: "  + str(best_dict['chance_cutoff']) + 
				 " alpha: " + str(best_dict['chance_alpha']) +  " ] " + # ] chance
				 " palette: " + str(best_dict['max_palette_size']) + 

				" " +  TXT_UL + "itlc: " + str(best_dict['interlace'].bool) + TXT_RES  + # <<---
				 " no_CC: " + str(best_dict['no_channel_compact'].bool) +
				 " Cbuck: " + str(best_dict['force_color_buckets'].bool) + 
				 + " no_ycocg: " + str(best_dict['no_ycocg'].bool) +  
				 " inv_rgb: " + str(best_dict['keep_invisible_rgb'].bool) +

				 " size " + str(size_new) + " b " +
				 "-" + str(size_change) + " b " +
				 perc_change + " %")

			best_dict['size'] = size_new
			best_dict['count'] = count
			arr_index = 0





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

	current_file = 0
	for INFILE in input_files: # iterate over every file that we go
		current_file += 1
		file_count_str = "(" + str(current_file) + "/" + str(len(input_files)) + ") " # X/Yth file
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

		print(file_count_str + inf['path'] + "; dimensions: "  + str(inf['sizeX']) +"×"+ str(inf['sizeY']) + ", " + str(inf['sizeX']*inf['sizeY']) + " px, " + str(inf['colors']) + " unique colors," + " " + str(inf['sizeByte']) + " b")
		size_orig = inf['sizeByte']
		size_before_glob  += size_orig


		# use named tuples for boolean cmdline flags
		Boolflag = namedtuple('boolflag', 'flag bool') # define the structure

		global best_dict
		# these have to be the flif default values
		best_dict={'count': -1,
				'maniac_repeats': 0, # 3
				'maniac_threshold': 40,
				'maniac_min_size': 50,
				'maniac_divisor': 30,
				'max_palette_size': 1024,
				'chance_cutoff': 2,
				'chance_alpha': 19,
				'interlace':  Boolflag("--no-interlace", False),
				'no_channel_compact': Boolflag('--no-channel-compact', True),
				'force_color_buckets': Boolflag('', False), #--force-color-buckets
				'no_ycocg': Boolflag("", False), # --no-ycocg
				'keep_invisible_rgb':  Boolflag("--keep-invisible-rgb", False),
				'size': size_orig,
				}


		global count
		count = 0 # how many recompression attempts did we take?
		best_count = 0 # what was the smallest compression so far?

		size_new = size_best = os.path.getsize(INFILE)

		if (COMPARE):  #do a default flif run with no special arguments
			proc = subprocess.Popen([flif_binary, INFILE, '/dev/stdout'], stdout=subprocess.PIPE)
			output_flifdefault = proc.stdout.read()
			size_flifdefault = sys.getsizeof(output_flifdefault)
			size_flifdefault_glob += size_flifdefault

		if (DEBUG):
			debug_array=[]
			debug_dict = {'Nr': '', 'maniac_repeats':'', 'maniac_threshold':"", 'maniac_min_size':"", 'maniac_divisor':"", 'max_palette_size': "", 'ACB': "", 'INT':"", 'size':""}

		max_iterations = 5
		it = 0
		#best_dict['maniac_repeats'] = 
		while (it != max_iterations):
			sze_beginning = best_dict['size']
			crush_maniac_threshold()
			crush_maniac_divisor()
			crush_maniac_min_size()
			crush_max_palette_size()
			crush_chance_cutoff()
			crush_chance_alpha()
			crush_keep_invisible_rgb()
			crush_force_color_buckets()
			crush_no_ycocg()
			crush_no_channel_compact()
			crush_interlace()
			crush_maniac_repeats()

			# if iteration didn't reduce anything, stop'
			it+=1
			if (sze_beginning == best_dict['size']):
				break


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



