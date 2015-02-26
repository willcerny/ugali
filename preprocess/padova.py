#!/usr/bin/env python
"""
Download Padova isochrones from:
http://stev.oapd.inaf.it/cgi-bin/cmd

Adapted from ezpadova by Morgan Fouesneau:
https://github.com/mfouesneau/ezpadova

"""
import os
from urllib import urlencode
from urllib2 import urlopen
from StringIO import StringIO
import zlib
import re
import subprocess
from collections import OrderedDict as odict

import numpy as np
from ugali.utils.logger import logger
from ugali.utils.shell import mkdir
from ugali.analysis.isochrone2 import PadovaIsochrone,OldPadovaIsochrone

defaults_27 = {
    'cmd_version': 2.7,
    'submit_form': 'Submit',
    'isoc_kind': 'parsec_CAF09_v1.2S',
    'eta_reimers': 0.2,
    'photsys_file': 'tab_mag_odfnew/tab_mag_decam.dat',
    'kind_cspecmag': 'aringer09',
    'dust_sourceC': 'nodustC', 
    'dust_sourceM': 'nodustM', 
    'imf_file': 'tab_imf/imf_chabrier_lognormal.dat',
    'isoc_val': 0,
    'isoc_age': 1e9,
    'isoc_zeta': 2e-4,
    'isoc_lage0':6.602,   #Minimum allowed age
    'isoc_lage1':10.1303, #Maximum allowed age
    'isoc_z0':0.0001,     #Minimum allowed metallicity  
    'isoc_z1':0.03,       #Maximum allowed metallicity
    'output_kind': 0,
    'output_evstage': 1,
    'output_gzip': 0,
    }

class Padova(object):
    defaults = defaults_27

    def __init__(self,survey='des',**kwargs):
        self.survey=survey

    #params2filename = OldPadovaIsochrone.params2filename
    #filename2params = OldPadovaIsochrone.filename2params
    params2filename = PadovaIsochrone.params2filename
    filename2params = PadovaIsochrone.filename2params

    def create_grid(self,abins,zbins):
        arange = np.linspace(abins[0],abins[1],abins[2]+1)
        zrange = np.logspace(np.log10(zbins[0]),np.log10(zbins[1]),zbins[2]+1)
        aa,zz = np.meshgrid(arange,zrange)
        return aa.flatten(),zz.flatten()

    def run(self,grid=None,outdir=None,force=False):
        if grid is None:
            aa,zz = self.create_grid()
        else:
            aa,zz = grid
        for a,z in zip(aa,zz):
            try: 
                self.download(a,z,outdir,force)
            except RuntimeError, msg:
                logger.warning(msg)

    def download(self,age,metallicity,outdir=None,force=False):
        """
        Check valid parameter range and download isochrones from:
        http://stev.oapd.inaf.it/cgi-bin/cmd
        """
        epsilon = 1e-4
        lage = np.log10(age*1e9)
        lage_min,lage_max = self.defaults['isoc_lage0'],self.defaults['isoc_lage1']
        if not (lage_min-epsilon < lage <lage_max+epsilon):
            msg = 'Age outside of valid range: %g [%g < log(age) < %g]'%(lage,lage_min,lage_max)
            raise RuntimeError(msg)

        z_min,z_max = self.defaults['isoc_z0'],self.defaults['isoc_z1']
        if not (z_min <= metallicity <= z_max):
            msg = 'Metallicity outside of valid range: %g [%g < z < %g]'%(metallicity,z_min,z_max)
            raise RuntimeError(msg)

        survey=self.survey.lower()
        if survey=='des':
            photsys_file='tab_mag_odfnew/tab_mag_decam.dat'
        elif survey=='sdss':
            photsys_file='tab_mag_odfnew/tab_mag_sloan.dat'
        else:
            msg = 'Unrecognized survey: %s'%survey
            raise RuntimeError(msg)

        if outdir is None: outdir = './'
        mkdir(outdir)

        basename = self.params2filename(age,metallicity)
        outfile = os.path.join(outdir,basename)
            
        if os.path.exists(outfile) and not force:
            logger.warning("Found %s; skipping..."%(outfile))
            return

        logger.info("Downloading isochrone: %s (age=%.2fGyr, metallicity=%g)"%(basename,age,metallicity))

        d = dict(self.defaults)
        d['photsys_file'] = photsys_file
        d['isoc_age']     = age * 1e9
        d['isoc_zeta']    = metallicity

        server = 'http://stev.oapd.inaf.it'
        url = server + '/cgi-bin/cmd_%s'%d['cmd_version']
        logger.info("Accessing %s..."%url)

        q = urlencode(d)
        logger.debug(url+'?'+q)
        c = urlopen(url, q).read()
        aa = re.compile('output\d+')
        fname = aa.findall(c)
        if len(fname) > 0:
            out = '{0}/~lgirardi/tmp/{1}.dat'.format(server, fname[0])
            cmd = 'wget %s -O %s'%(out,outfile)
            logger.debug(cmd)
            stdout = subprocess.check_output(cmd,shell=True,stderr=subprocess.STDOUT)
            logger.debug(stdout)
        else:
            #print(c)
            raise RuntimeError('Server Response is incorrect')

if __name__ == "__main__":
    import ugali.utils.parser
    description = "Download isochrones"
    parser = ugali.utils.parser.Parser(description=description)
    parser.add_config()
    parser.add_debug()
    parser.add_verbose()
    parser.add_force()
    parser.add_argument('-a','--age',default=None,type=float)
    parser.add_argument('-z','--metallicity',default=None,type=float)
    opts = parser.parse_args()

    from ugali.utils.config import Config
    config = Config(opts.config)

    #outdir = '/u/ki/kadrlica/des/isochrones/v1'
    #outdir = '/u/ki/kadrlica/sdss/isochrones/v2'
    outdir = '/u/ki/kadrlica/des/isochrones/v2'
    outdir = '/u/ki/kadrlica/des/isochrones/v3'
    survey = config['data']['survey']
    p = Padova(survey=survey)
    abins = config['binning']['age']
    zbins = config['binning']['z']

    abins = np.arange(1,13.5,0.1)
    zbins = np.arange(1e-4,1e-3,1e-5)
    if opts.age is not None: abins = [opts.age]
    if opts.metallicity is not None: zbins = [opts.metallicity]
    grid = [g.flatten() for g in np.meshgrid(abins,zbins)]
        
    #grid = p.create_grid(abins,zbins)
    #grid = OldPadovaIsochrone.create_grid()
    #grid = np.meshgrid((10**np.arange(9.9,10.15,0.05))/1e9,np.array([0.12,0.15,0.19,0.24,0.30,0.38,0.48,0.6])*1e-3)
    #cut = (grid[0] > 0.5)
    #grid = (grid[0][cut],grid[1][cut])
    #grid = np.meshgrid(np.arange(1,13.5),np.arange(1e-4,1e-3,5e-5)

    print "Ages:"
    print np.unique(grid[0])
    print "Metallicities:"
    print np.unique(grid[1])
    p.run(grid=grid,outdir=outdir,force=opts.force)
