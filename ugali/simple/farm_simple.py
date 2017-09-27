#!/usr/bin/env python
"""
Perform simple binning search
"""
__author__ = "Sidney Mau"

import os
import time
import subprocess
import glob
import pyfits
import healpy
import numpy

import ugali.utils.healpix

import yaml

############################################################

with open('config.yaml', 'r') as ymlfile:
    cfg = yaml.load(ymlfile)

nside = cfg['nside']
datadir = cfg['datadir']

results_dir = os.path.join(os.getcwd(), cfg['results_dir'])
if not os.path.exists(results_dir):
    os.mkdir(results_dir)

infiles = glob.glob('%s/cat_hpx_*.fits'%(datadir))

############################################################

print('Pixelizing...')
pix_nside = [] # Equatorial coordinates, RING ordering scheme
for infile in infiles:
    pix_nside.append(int(infile.split('.fits')[0].split('_')[-1]))

############################################################

for ii in range(0, len(pix_nside)):
    ra, dec = ugali.utils.healpix.pixToAng(nside, pix_nside[ii])

    print('({}/{})').format(ii, len(pix_nside))

    batch = 'csub -n 20 '
    command = 'python search_algorithm.py %.2f %.2f'%(ra, dec)
    command_queue = batch + command
    print command_queue
    #os.system('./' + command) # Run locally
    os.system(command_queue) # Submit to queue
