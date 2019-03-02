#!/usr/bin/env python

# Merge ring by ring fit parameters from Bbarolo tables

import os
from astropy.table import Table,Column,vstack,hstack
import numpy as np

bbdir = '/Volumes/Data/tonywong/sharenb/bbarolo_7as/'
runs=['gal_nrad8','gal_nrad8_smolist','gal_nrad8_vdisp8','gal_nrad8_vdisp8_smolist']
#runs=['bb_fitvd_dilmsk','bb_fitvd_bbmsk','bb_fixvd_dilmsk','bb_fixvd_bbmsk']

with open(bbdir+'detected.txt') as f:
    namelist = f.read().splitlines()
gallist = [gal for gal in namelist if not gal.startswith("#")]

# Write the rotation curve tables

for run in runs:
    tablelist_run=[]
    print('Beginning run',run,'for ringlogs')

    for gal in gallist:
        tablelist_rings=[]

        for ringlog in ['ringlog1','ringlog2']:
            # --- Try to read the table
            if not os.path.isfile(bbdir+run+'/output/'+gal[:8]+'/'+ringlog+'.txt'):
                # gal[:8] is because the rest of the characters are truncated.
                continue
            try:
                gal_ringlog = Table.read(bbdir+run+'/output/'+gal[:8]+'/'+ringlog+'.txt',format='ascii')
            except:
                print('reading '+ringlog+' for '+gal+' failed, probably because table is empty')
                continue
            gal_ringlog.remove_columns(['RAD(Kpc)', 'Z0(pc)', 'SIG(E20)', 'VRAD(km/s)'])
            parlabel = {
                "RAD(arcs)" : 'bbRad',
                "VROT(km/s)" : 'bbVrot',
                "E_VROT1" : 'bbVrot_e1',
                "E_VROT2" : 'bbVrot_e2',
                "DISP(km/s)" : 'bbVdisp',
                "E_DISP1" : 'bbVdisp_e1',
                "E_DISP2" : 'bbVdisp_e2',
                "XPOS(pix)" : 'bbXpos',
                "E_XPOS1" : 'bbXpos_e1',
                "E_XPOS2" : 'bbXpos_e2',
                "YPOS(pix)" : 'bbYpos',
                "E_YPOS1" : 'bbYpos_e1',
                "E_YPOS2" : 'bbYpos_e2',
                "VSYS(km/s)" : 'bbVmean',
                "E_VSYS1" : 'bbVmean_e1',
                "E_VSYS2" : 'bbVmean_e2',
                "P.A.(deg)" : 'bbPA',
                "E_PA1" : 'bbPA_e1',
                "E_PA2" : 'bbPA_e2',
                "INC(deg)" : 'bbInc',
                "E_INC1" : 'bbInc_e1',
                "E_INC2" : 'bbInc_e2',
                "Z0(arcs)" : 'bbZ0'
            }
            # --- Assemble the output table in the right order
            ordlist = []
            for label in parlabel:
                if label in gal_ringlog.colnames:
                    gal_ringlog.rename_column(label, parlabel[label])
                    ordlist.append(parlabel[label])
            outtable = gal_ringlog[ordlist]
            nrows = len(outtable)
            
            # --- Add the Galaxy Name
            gname = Column([gal]*nrows, name='bbName', description='Galaxy Name')
            outtable.add_column(gname, index=0)

            # --- Add info on which parameters fitted
            parfile_path = bbdir+run+'/param_'+gal+'.par'
            with open(parfile_path) as parfile:
                parfile_lines = parfile.read().splitlines()
            freepars = [line for line in parfile_lines if line.startswith('FREE')][0]
            freepars = freepars.split()[1:]
            # tabulate the fit parameters
            freelbl = {
                'VROT' : 'bbVrotfit',
                'VDISP' : 'bbVdispfit',
                'XPOS' : 'bbXposfit',
                'YPOS' : 'bbYposfit',
                'VSYS' : 'bbVsysfit',
                'PA' : 'bbPAfit',
                'INC' : 'bbIncfit',
            }
            for bblabel in freelbl:
                newcol = Column([0]*nrows, name=freelbl[bblabel])
                if bblabel not in freepars:
                    outtable.add_column(newcol)
                else:
                    if ringlog == 'ringlog2':
                        if bblabel not in ['VROT', 'VDISP']:
                            newcol[:] = -1
                        else:  # These are always fit ring by ring
                            newcol[:] = 1
                    else:
                        newcol[:] = 1
                    outtable.add_column(newcol)

            # --- Add info on fitting method
            fval = [line for line in parfile_lines if line.startswith('FTYPE')][0].split()[1]
            wval = [line for line in parfile_lines if line.startswith('WFUNC')][0].split()[1]
            ftype = Column([int(fval)]*nrows, name='bbFtype', description=
                'Function to minimize: 1=chi-squared, 2=|mod-obs|')
            wfunc = Column([int(wval)]*nrows, name='bbWfunc', description=
                'Weighting function: 0=uniform, 1=|cos|, 2=cos^2')
            outtable.add_column(ftype)
            outtable.add_column(wfunc)

            # --- Set flag to 1 if any plot is missing
            badflag = Column([0]*nrows, name='bbFlag')
            plot_paths=['/plot_pv_local.pdf','/plot_parameters.pdf','/plot_maps_local.pdf','/plot_chanmaps_local.pdf']
            for plot_path in plot_paths:
                if not os.path.isfile(bbdir+run+'/output/'+gal[:8]+plot_path): 
                    badflag[:] = 1
                    break
            outtable.add_column(badflag)
            tablelist_rings.append(outtable)

        # -- Combine tables for a given galaxy
        # some gals only have ringlog1, or no ringlog at all since it is missing from that run
        if len(tablelist_rings)==0:
            continue
        elif len(tablelist_rings)==1:
            t_gal=tablelist_rings[0]
        else:
            t_gal=vstack(tablelist_rings)
        tablelist_run.append(t_gal)

    # -- Combine tables for all galaxies
    t_run = vstack(tablelist_run)
    fitparam = list(freelbl.values())
    kmsparam = [label for label in t_run.colnames if 'V' in label]
    degparam = [label for label in t_run.colnames if any(str in label for str in ['Inc','PA'])]
    arcsparam = ['bbRad', 'bbZ0']
    pixparam = [label for label in t_run.colnames if any(str in label for str in ['X','Y'])]
    t_run['bbVmean'].description = 'Systemic velocity in radio defn, LSR frame'
    t_run['bbRad'].description = 'Galactocentric radius of ring'
    t_run['bbZ0'].description = 'Scale height of disk in arcsec'
    t_run['bbFlag'].description = '=1 when some ringlog exits, but Bbarolo fails to produce at least one of the plots'
    for col in fitparam:
        t_run[col].description = '0=fixed to input value; 1=fitted per ring; -1=fixed to mean value of previous fit'
    for col in kmsparam:
        t_run[col].unit = 'km/s'
    for col in degparam:
        t_run[col].unit = 'deg'
    for col in arcsparam:
        t_run[col].unit = 'arcsec'
    for col in pixparam:
        t_run[col].unit = 'pixel'
    t_run.write(run+'.csv',overwrite=True,delimiter=',',format='ascii.ecsv')


# Write the radial profile tables

cols_keep = ['RADIUS','NPIX','SURFDENS','ERR_SD']
densepars = ['SURFDENS','ERR_SD']

for run in runs:
    densprof_run=[]
    print('Beginning run',run,'for densprof')
    for gal in gallist:
        if not os.path.isfile(bbdir+run+'/output/'+gal[:8]+'/'+'densprof'+'.txt'):
            continue
        try:
            gal_densprof = Table.read(bbdir+run+'/output/'+gal[:8]+'/'+'densprof'+'.txt',
                    format='ascii.commented_header',header_start=13)
        except:
            print('reading densprof for '+gal+' failed, probably because the table is empty')
            continue
        densprof_table = gal_densprof[cols_keep]
        gname = Column([gal]*len(gal_densprof), name='bbName')
        densprof_table.add_column(gname, index=0)

        densprof_run.append(densprof_table)
        
    t_run_densprof = vstack(densprof_run)
    t_run_densprof.meta['comments'] = ''
    t_run_densprof['RADIUS'].unit = 'arcsec'
    t_run_densprof['NPIX'].description = 'number of pixels in ring'
    for col in densepars:
        t_run_densprof[col].unit = '(Jy*km/s)/arcsec**2'
    t_run_densprof['SURFDENS'].description = 'average intensity in ring, not corrected for inclination'
    t_run_densprof['ERR_SD'].description = 'standard deviation of intensity in ring'
    
    t_run_densprof.write(run+'_densprof.csv',overwrite=True,delimiter=',',format='ascii.ecsv')
