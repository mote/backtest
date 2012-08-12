#!/usr/bin/env python

import sys

if len(sys.argv) != 2:
	print "usage: ./foo <file>"
	sys.exit(1)

infile = sys.argv[1]

f = open(infile, 'r')
hdr = f.readline()
lines = f.readlines()
lines.reverse()
print hdr,
for l in lines:
	print l,


