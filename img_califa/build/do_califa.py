#!/usr/bin/env python

# Combine the CALIFA data into binary tables.

import glob
import os
from astropy.table import Table, Column, join, vstack
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from reproject import reproject_interp
import sys
sys.path.append('../../edge_pydb')
from fitsextract import fitsextract, getlabels

codir = '../../img_comom/fitsdata/'
cadir = '../fitsdata/'
prodtype = ['ELINES', 'SFH', 'SSP', 'indices', 'flux_elines']

for prod in prodtype:
    zsel, labels, units, nsel = getlabels(prod)
    filelist = [fn for fn in glob.glob(cadir+'*'+prod+'*.fits.gz')
            if not os.path.basename(fn).startswith('x')]
    print('\n',filelist)
    tablelist=[]
    for file in filelist:
        base = os.path.basename(file)
        if prod not in ['indices', 'flux_elines']:
            gal = base.split('.')[0]
        elif prod == 'indices':
            gal = base.split('.')[2]
        else:
            gal = base.split('.')[1]

        print('\nWorking on galaxy {} product {} nsel={}'.format(
            gal, prod, nsel))

        # Generate output header using CO astrometry
        cohd = fits.getheader(codir+gal+'.co.smo7_dil.mom0.fits.gz')
        cahd = fits.getheader(cadir+'x'+base, ignore_missing_end=True)
        outhd = cahd.copy()
        for key in ['NAXIS1', 'NAXIS2', 'CTYPE1', 'CTYPE2', 'CRVAL1', 'CRVAL2', 
                    'CRPIX1', 'CRPIX2', 'CDELT1', 'CDELT2']:
            outhd[key] = cohd[key]
        cdkeys = ['CD1_1','CD1_2','CD2_1','CD2_2','CD1_3','CD2_3','CD3_1','CD3_2','CD3_3']
        for key in cdkeys:
            if key in outhd.keys():
                del outhd[key]

        # First process the native resolution file since it has the astrometry
        hdu = fits.open(cadir+'x'+base, ignore_missing_end=True)[0]
        hdu.data[hdu.data==0] = np.nan
        newim,foot = reproject_interp(hdu, outhd, independent_celestial_slices=True)
        #fits.writeto(base.replace('fits','rgd.fits'), newim, outhd, overwrite=True)
        tab0 = fitsextract(newim, header=outhd, keepnan=True, stride=[3,3,1], 
            bunit=units, lbl=labels, zselect=zsel, suffix='_rg')

        # Then process the smoothed file
        hdu = fits.open(cadir+base, ignore_missing_end=True)[0]
        hdu.data[hdu.data==0] = np.nan
        hdu.header = cahd
        newim,foot = reproject_interp(hdu, outhd, independent_celestial_slices=True)
        #fits.writeto(base.replace('fits','sm.fits'), newim, outhd, overwrite=True)
        tab1 = fitsextract(newim, header=outhd, keepnan=True, stride=[3,3,1], 
            bunit=units, lbl=labels, zselect=zsel, suffix='_sm')

        joint=join(tab0,tab1)

        gname = Column([np.string_(gal)]*len(joint), name='Name', 
                       description='Galaxy Name')
        joint.add_column(gname, index=0)
        #print(joint[20:50])
        tablelist.append(joint)

    if len(tablelist) > 0:
        t_merge = vstack(tablelist)
    print(t_merge.colnames)
    print('There are',len(t_merge),'rows')
    if (len(filelist) > 1):
        outname = 'edge'
    else:
        outname = gal
    t_merge.write('../'+outname+'.'+prod+'.hdf5', path='data', overwrite=True, 
                serialize_meta=True, compression=True)
