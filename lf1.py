#!/usr/bin/env python

## LOFAR pipeline script
## creates directory structure if first time run
## Writes torque submit scripts (bash) for:
##  - inspection plots
##  - downloading data
##  - processing calibrator
##
## for questions contact Leah Morabito (morabito@strw.leidenuniv.nl)
## last revised 29 Aug 2014 (fixed date comparison for use of fixbeaminfo, 
##                            added moving of fixinfo file to modeldirectory to download)

import glob
import os
import sys
import leahutil as lu
import shutil
import time
import subprocess
import argparse

##------------------- MAIN PROGRAM ----------------------

def pipeline(args):

    ##------------ INPUT PARAMETERS -------------

    ## required parameters
    obs_name = args.targetname
    rootdir = args.rootdir
    rootdir = rootdir.rstrip('/')
    myemail = args.myemail
    ltapswd = args.ltapw
    ltausername = args.ltaun
    lbaflag = args.lbaflag

    demix_skymodel = '/net/para33/data1/lofar/models/Ateam_LBA.sky' # standard for LBA
    rfi_model = '/net/para33/data1/lofar/models/LBAdefault.rfis'  # standard for LBA

    ## define the directories
    obsdir = rootdir + '/' + obs_name
    datadir = obsdir +'/PIPELINE'
    inspectiondir = obsdir +'/inspection'
    logdir = obsdir +'/logs'
    parsetdir = obsdir +'/parsets'
    modeldir = obsdir +'/models'
    torquedir = obsdir +'/torque'


    ## if running for the first time, create the directory structure
    if not os.path.isdir(obsdir):
        print 'First time creating observation script, also creating data directories ...'
        os.system('mkdir ' + obsdir)
        os.system('mkdir ' + datadir)
        os.system('mkdir ' + inspectiondir)
        os.system('mkdir ' + logdir)
        os.system('mkdir ' + parsetdir)
        os.system('mkdir ' + modeldir)
        os.system('mkdir ' + torquedir)
        print 'Data directories created.'
        print 'Top directory: ',obsdir
        print 'Data directory: ',datadir
        print 'Inspection directory: ',inspectiondir
        print 'Log directory: ',logdir
        print 'Parset directory: ',parsetdir
        print 'Model directory: ',modeldir
        print 'Torque scripts will be saved to: ',torquedir
	fixinfodir = modeldir + '/fixinfo'
        tgtid = raw_input('Enter the target obsid: L')
#	ynflag = raw_input('Is there more than one calibrator for this target? [y/n]: ')  # eventually need to deal with this
        calid = raw_input('Enter the calibrator obsid: L')
	calname = raw_input('Which calibrator are you using? Enter verbatim [3C196,3C295,CygA]: ')
        strgdir = raw_input('Where is your local long-term storage directory? [enter full path]: ')
	freqres = raw_input('Enter desired number of channels: ')
	timeres = raw_input('Enter desired time resolution (seconds): ')
        infofile = logdir + '/obsinfo.log'
        with open(infofile,'w') as g:
            g.write(tgtid)
            g.write('\n')
            g.write(calid)
            g.write('\n')
            g.write(strgdir)
            g.write('\n')
            g.write(freqres)
            g.write('\n')
            g.write(timeres)
            g.write('\n')
            g.write(calname)
        g.close()
    else:
        infofile = logdir + '/obsinfo.log'
        with open(infofile,'r') as g:
            lines = g.readlines()
        g.close()
        tgtid = lines[0]
        calid = lines[1]
        strgdir = lines[2]
	freqres = lines[3]
	timerest = lines[4]
	calname = lines[5]

    if calname == '3C196':
        skymodel='/net/para33/data1/lofar/models/3C196.4pts.skymodel'
    elif calname == '3C295':
        skymodel='/net/para33/data1/lofar/models/3C295_TWO_MSSS.skymodel'
    elif calname == 'CygA': 
        skymodel='/net/para33/data1/lofar/models/cyga.77mhz.si.model.bbs'

    ##------------ Write the inspection script -------------
    inspectionscript = torquedir + '/lp_inspection.' + obs_name + '.sh'
    with open(inspectionscript,'w') as f:
        f.write('#! /bin/bash\n')
        f.write('\n')
        f.write('# send email alerts to this address\n')
        f.write('#PBS -M {} \n'.format(myemail))
        f.write('# mail alerts for aborted job\n')
        f.write('#PBS -m a\n')
        f.write('\n')
        f.write('# set name of job\n')
        f.write('#PBS -N lp_inspection\n')
        f.write('\n')
        f.write('# join the output and error files and set the log location\n')
        f.write('#PBS -j oe\n')
        f.write('#PBS -o {} \n'.format(logdir))
        f.write('\n')
        f.write('# set max wallclock time and memory\n')
        f.write('#PBS -l walltime=100:00:00\n')
        f.write('#PBS -l mem=10G\n')
        f.write('\n')
        f.write('######################## END PBS ##\n\n')        
        f.write('## DIRECTORIES, Note no "/" at the end\n')
        f.write('# inspection directory\n')
        f.write('WORK_DIR={}\n'.format(inspectiondir))
        f.write('\n')
	inspid='22222'
        f.write('OBSN={}\n'.format(inspid))
        f.write(r'''HTTPPATH="https://proxy.lofar.eu/inspect/$OBSN/"''')
        f.write('\n\n')
        f.write('NCORES==${PBS_NUM_PPN}\n')
        f.write('export OMP_NUM_THREADS=$NCORES\n\n')
        f.write('######################## END OBSERVATION SPECIFICS ##\n\n')
        f.write('## bash stop on error ##\n')
        f.write('set -e\n\n')
        f.write('## change to work directory ##\n')
        f.write('cd ${WORK_DIR}\n\n')
        f.write('######################## END SOFTWARE CONFIGURATION ##\n\n')
        f.write('# download from the path\n')
        f.write('echo "downloading"\n')
        f.write('wget  -r -l1 --no-parent -A.jpg $HTTPPATH\n\n')
        f.write('mv proxy.lofar.eu/inspect/$OBSN/*jpg .\n')
        f.write('rm -rf  proxy.lofar.eu\n\n')
        f.write(r'''SBlist=`ls *timeseries-cs002* | cut -f3 -d'_'`''')
        f.write('\n\n')
        f.write('echo "combining images"\n')
        f.write('for SB in $SBlist; do\n')
        f.write('    echo ${SB}\n')
        f.write('    montage -label timeseries-cs002hba0 *${SB}_uv-timeseries-cs002hba0.jpg \ \n')
        f.write('            -label station-gain-cs002hba0 *${SB}_uv-station-gain-cs002hba0.jpg \ \n')
        f.write('            -label timeseries-cs004hba0 *${SB}_uv-timeseries-cs004hba0.jpg \ \n')
        f.write('            -label station-gain-cs004hba0 *${SB}_uv-station-gain-cs004hba0.jpg \ \n')
	if not lbaflag:
            f.write('            -label timeseries-rs307hba *${SB}_uv-timeseries-rs307hba.jpg \ \n')
            f.write('            -label station-gain-rs307hba *${SB}_uv-station-gain-rs307hba.jpg \ \n')
            f.write('            -label timeseries-rs508hba *${SB}_uv-timeseries-rs508hba.jpg \ \n')
            f.write('            -label station-gain-rs508hba *${SB}_uv-station-gain-rs508hba.jpg  \ \n')
        f.write('            -mode Concatenate  -tile 2x4 -pointsize 72 t1_${SB}.jpg \n')
        f.write('    montage -label flagged-standard-deviation *${SB}_uv-flagged-standard-deviation.jpg \ \n')
        f.write('            -label flagged-mean *${SB}_uv-flagged-mean.jpg \ \n')
        f.write('            -label flags *${SB}_uv-flags.jpg \ \n')
        f.write('            -label zeroes *${SB}_uv-zeroes.jpg  \ \n')
        f.write('            -mode Concatenate  -tile 2x2  -pointsize 72 t2_${SB}.jpg \n')
        f.write('    montage t1_${SB}.jpg  t2_${SB}.jpg -mode Concatenate  -tile 2x1 -title ${SB} -pointsize 96  ${SB}.jpg \n')
        f.write('done \n\n')
        f.write('rm -rf t1_SB*.jpg t2_SB*.jpg \n')
        f.write('# right now this command doesnt work \n')
        f.write('#ffmpeg -f image2 -r 10 -i SB%03d.jpg inspect.mp4 \n\n')
        f.write('################# done ########################## \n')
    f.close()



    ##------------ Write the dowload script -------------

    downloadscript = torquedir + '/lp_ltadownload.' + obs_name + '.sh'
    with open(downloadscript,'w') as f:
        f.write('#! /bin/bash\n')
        f.write('\n')
        f.write('# send email alerts to this address\n')
        f.write('#PBS -M {} \n'.format(myemail))
        f.write('# mail alerts for aborted job\n')
        f.write('#PBS -m a\n')
        f.write('\n')
        f.write('# set name of job\n')
        f.write('#PBS -N lp_ltadownload\n')
        f.write('\n')
        f.write('# join the output and error files and set the log location\n')
        f.write('#PBS -j oe\n')
        f.write('#PBS -o {} \n'.format(logdir))
        f.write('\n')
        f.write('# set max wallclock time and memory\n')
        f.write('#PBS -l walltime=100:00:00\n')
        f.write('#PBS -l mem=10G\n')
        f.write('\n')
        f.write('######################## END PBS ##\n\n')
        f.write('## DIRECTORIES, Note no "/" at the end\n')
        f.write('# Data download directory\n')
        f.write('DATA_DIR={}\n'.format(datadir))
        f.write('# log directory\n')
        f.write('LOGS_DIR={} \n'.format(logdir))
	f.write('# models directory\n')
	f.write('MODEL_DIR={}\n'.format(modeldir))
        f.write('\n')
        f.write('######################## END OBSERVATION SPECIFICS ##\n\n')
        f.write('## bash stop on error\n')
        f.write('set -e\n')
        f.write('## bash output things helpful for debugging ##\n')
        f.write('set -x\n\n')
	f.write('# source lofar software\n')
	f.write('source /home/wwilliams/.lofarinit.sh.20140724\n\n')
        f.write('# start job from the directory it was submitted\n')
        f.write('cd ${DATA_DIR}\n')
        f.write('\n')
        f.write('######################## END SOFTWARE CONFIGURATION ##\n\n')
        f.write('############################# DOWNLOAD FROM LTA ##\n\n')
        f.write('# this gets the files from the LTA, and will be serial so as not to clog the connection\n')
        f.write("wget -i $LOGS_DIR/html.txt --user={0} --password='{1}'\n".format(ltausername, ltapswd))
        f.write('# get an array of file names\n')
        f.write('FILES=(*tar)\n')
        f.write('# number of files\n')
        f.write('LENFILES=${#FILES[@]}\n')
        f.write('# rename them (based on subband) to avoid issues with the links in the downloaded name\n')
        f.write(r'''x=0; while [ $x -lt $LENFILES ]; POS=`expr "${FILES[$x]}" : '.*\_SB'`; do mv ${FILES[$x]} ${FILES[$x]:$POS-2}; let x=$x+1; done''')
        f.write('\n')
	f.write('# untar one file to get observation information\n')
	f.write('FILES=(*tar)\n')
	f.write('tar -xf ${FILES[0]}\n')
	f.write('# run msoverview\n')
	f.write(r'''MS=`ls -d L*MS`''')
	f.write('\n')
	f.write('msoverview in=${MS} verbose=T > ${LOGS_DIR}/sbinfo.log\n\n')
	f.write('rm -r L*MS\n\n')
	f.write('cp -r /net/para33/data1/morabito/lofar/scripts/fixinfo ${MODEL_DIR}/fixinfo\n\n')
        f.write('################# done ##########################\n')
    f.close()

    ##------------ Calibrator script --------------------------------
    
    calibratescript = torquedir + '/lp_calibrator.' + obs_name + '.sh'
    with open(calibratescript,'w') as f:
        f.write('#! /bin/bash\n')
        f.write('\n')
        f.write('# send email alerts to this address\n')
        f.write('#PBS -M {}\n'.format(myemail)) 
        f.write('# mail alerts for aborted job\n')
        f.write('#PBS -m a\n')
        f.write('\n')
        f.write('# set name of job\n')
        f.write('#PBS -N lp_processcalibrate\n') 
        f.write('\n')
        f.write('# join the output and error files and set the log location\n')
        f.write('#PBS -j oe\n')
        f.write('#PBS -o {} \n'.format(logdir))
        f.write('\n')
        f.write('# set max wallclock time and memory\n')
        f.write('#PBS -l walltime=100:00:00\n')
        f.write('#PBS -l mem=10G\n')
        f.write('\n')
        f.write('# use list of files to set up an array job\n') 
        dlfile = logdir + '/html.txt'
        if os.path.isfile(dlfile):
            with open(dlfile,'r') as g:
                lines = g.readlines()
            g.close()
            sblist = '#PBS -t '
            for line in lines:
                sbname = line[line.find('SB')+2:line.find('SB')+5]
                sblist = sblist + sbname + ','
            sblist = sblist.rstrip(',')
            f.write(sblist)
            f.write('\n')
	else:
	    f.write('##PBS -t 1,2,3\n') 
        f.write('\n')
        f.write('######################## END PBS ##############################################\n')
        f.write('\n')
        f.write('# Sub array pointing IDs\n')
        f.write('CALOBS=L{}\n'.format(calid))
        f.write('\n')
        f.write('## DIRECTORIES, Note no "/" at the end\n')
        f.write('# Data local long term storage\n')
        f.write('STORAGE_DIR={}\n'.format(strgdir)) #
        f.write('# Data working directory\n')
        f.write('WORK_DIR={}\n'.format(datadir)) 
        f.write('# calibrator directory\n')
        f.write('CAL_DIR=${WORK_DIR}/${CALOBS}\n') 
        f.write('# Directory with parsets\n')
        f.write('PARSET_DIR={}\n'.format(parsetdir)) 
        f.write('# Directory with models\n')
        f.write('MODEL_DIR={}\n'.format(modeldir)) 
        f.write('# log directory\n')
        f.write('LOGS_DIR={}\n'.format(logdir)) 
        f.write('\n')
        f.write('######################## END OBSERVATION SPECIFICS ##\n')
        f.write('\n')
        f.write('## bash stop on error ##\n')
        f.write('set -e\n')
        f.write('## bash output things helpful for debugging ##\n')
        f.write('set -x\n')
        f.write('\n')
        f.write('# source the lofar software\n')
        f.write('source /home/wwilliams/.lofarinit.sh.20140724\n')
        f.write('\n')
        f.write('# specify number of cores\n')
        f.write('NCORES=2\n') 
        f.write('export OMP_NUM_THREADS=${NCORES}\n')
        f.write('\n')
        f.write('# start job from the directory it was submitted\n')
        f.write('cd ${WORK_DIR}\n')
        f.write('\n')
        f.write('# create calbrator dirctory if it does not already exist\n')
        f.write(r'''if [ ! -d "${CAL_DIR}" ]; then''')
        f.write('\n')
        f.write('	mkdir -p ${CAL_DIR}\n')
        f.write('fi\n')
        f.write('\n')
        f.write('# create storage dirctory if it does not already exist\n')
        f.write(r'''if [ ! -d "${STORAGE_DIR}" ]; then''')
        f.write('\n')
        f.write('	mkdir -p ${STORAGE_DIR}\n')
        f.write('fi\n')
        f.write('\n')
        f.write('## get the SB number from the array id, pad with zeros ##\n')
        f.write(r'''SB=`printf "%03d" ${PBS_ARRAYID}`''')
        f.write('\n')
        f.write('\n')
        f.write('######################## END SOFTWARE CONFIGURATION ##############################\n')
        f.write('\n')
        f.write('############# DOWNLOAD FROM LTA SHOULD BE DONE FIRST SEPARATELY ##################\n')
        f.write('\n')
        f.write('#################### UNTAR DATA AND MOVE TO SB DIRECTORIES #######################\n')
        f.write('\n')
	f.write('cd ${WORK_DIR}\n\n')
        f.write('# untar the file\n')
        f.write('tar -xf SB${SB}*tar\n') 
        f.write('# remove the tar file\n')
        f.write('rm SB${SB}*tar\n') 
        f.write('\n')
        f.write('# get the pipeline ID from the beginning of the name\n')
        f.write(r'''OBSID=`ls -d L*${SB}*MS | cut -d'_' -f 1`''')
        f.write('\n')
        f.write('\n')
        f.write('# subband name\n')
        f.write(r'''SBNAME=`ls -d L*${SB}*MS | cut -d'_' -f 2`''')
        f.write('\n')
        f.write('\n')
        f.write('# make a directory\n')
        f.write('SB_WORK_DIR=${WORK_DIR}/${OBSID}\n')
        f.write(r'''if [ ! -d "${SB_WORK_DIR}/${SBNAME}" ]; then''')
        f.write('\n')
        f.write('	mkdir -p ${SB_WORK_DIR}/${SBNAME}\n')
        f.write('fi\n')
        f.write('\n')
        f.write(r'''MS=`ls -d L*${SB}*MS`''')
        f.write('\n')
        f.write('mv L*${SB}*MS ${SB_WORK_DIR}/${SBNAME}/${MS}\n')
        f.write('\n')
        f.write('############################# FIX THE BEAM INFO #################################\n')
        f.write('\n')
        f.write('# run this step only if fixinfo exists\n')
        f.write(r'''TMP=`grep "Observed from" ${LOGS_DIR}/sbinfo.log`''')
        f.write('\n')
        f.write(r'''TMP1=`echo ${TMP} | cut -d' ' -f 3`''')
        f.write('\n')
        f.write(r'''startdate=$(date -d `echo ${TMP1} | cut -d' ' -f 1` '+%s')''')
        f.write('\n')
        f.write(r'''d1=$(date -d "13-Feb-2013" '+%s')''')
        f.write('\n')
        f.write(r'''d2=$(date -d "10-Feb-2014" '+%s')''')
        f.write('\n')
        f.write('if [ ${startdate} -ge ${d1} ] && [ ${startdate} -le ${d2} ]; then\n')
        f.write('        cp -r /net/para33/data1/morabito/lofar/scripts/fixinfo ${MODEL_DIR}/fixinfo\n')
        f.write('        cd ${MODEL_DIR}/fixinfo\n')
        f.write('        ./fixbeaminfo ${SB_WORK_DIR}/${SBNAME}/${MS} > ${SB_WORK_DIR}/${SBNAME}/SB${SB}.log.fixbeam 2>&1\n')
        f.write('        # return to working directory for subband\n')
        f.write('        cd ${SB_WORK_DIR}/${SBNAME}\n')
        f.write('fi\n')
        f.write('\n')
        f.write('############################# INITIAL FLAGGING ###################################\n')
        f.write('\n')
        f.write('## base flagging parset to use\n')
        f.write('FLAG_PARSET=${PARSET_DIR}/flagging.parset\n\n')
        f.write('## flag if it exists\n')
        f.write(r'''if [ "${FLAG_PARSET}" ]; then''')
        f.write('\n')
        f.write('        ## msout file name, blank to output to self \n')
        f.write(r'''        MSOUT=""''')
        f.write('\n')
        f.write('        ## write a parset with the correct information for the subband\n')
        f.write('        PARSET=${MS}.ndppp.parset\n')
        f.write('        echo msin=${MS} > ${PARSET}\n')
        f.write('        echo msout=${MSOUT} >> ${PARSET}\n')
        f.write(r'''        while read LINE; do echo -e "${LINE}" >> ${PARSET}; done < ${FLAG_PARSET}''')
        f.write('\n')
        f.write('        ## Run NDPPP ##\n')
        f.write('        NDPPP ${PARSET} > SB${SB}.log.init_flagging 2>&1\n')
        f.write('        # remove parset\n')
        f.write('        rm ${PARSET}\n')
        f.write('else\n')
        f.write(r'''        echo "No flagging parset available, doing no flagging."''')
        f.write('\n')
        f.write('fi\n')
        f.write('################################### DEMIXING ######################################\n')
        f.write('\n')
        f.write('## base flagging parset to use\n')
        f.write('DEMIX_PARSET=${PARSET_DIR}/demix.parset\n\n')
        f.write('## demix if parset exists\n')
        f.write(r'''if [ "${DEMIX_PARSET}" ]; then''')
        f.write('\n')
        f.write('        ## skymodel to use\n')
        f.write('        SKY_MODEL=/net/para33/data1/lofar/models/Ateam_LBA.sky\n')
        f.write('        cp -r ${SKY_MODEL} .\n\n')
        f.write('        ## msout file name\n')
        f.write(r'''        POS=`expr "${MS}" : '.*.MS'`''')
        f.write('\n')
        f.write('        BASENAME=${MS:0:$POS-3}\n')
        f.write('        MSOUT=${BASENAME}.dem.MS\n\n')
        f.write('        ## write a parset with the correct information for the subband\n')
        f.write('        PARSET=SB${SB}.ndppp.demix.parset\n')
        f.write('        echo msin=${MS} > ${PARSET}\n')
        f.write('        echo msout=${MSOUT} >> ${PARSET}\n')
        f.write(r'''        while read LINE; do echo -e "${LINE}" >> ${PARSET}; done < $DEMIX_PARSET''')
        f.write('\n')
        f.write('        echo demixer.skymodel=Ateam_LBA.sky >> ${PARSET}\n\n')
        f.write('        ## Run NDPPP ##\n')
        f.write('        NDPPP ${PARSET} > SB${SB}.log.demixing 2>&1\n\n')
        f.write('        # check if the demixing was successful -- if so, delete the un-demixed file\n')
        f.write(r'''        CHECK_DEMIX=`grep "Total NDPPP time" SB${SB}.log.demixing`''')
        f.write('\n')
        f.write('        if [ ${#CHECK_DEMIX} -gt 0 ]; then \n')
        f.write('                rm -r ${MS}\n')
        f.write('                rm ${PARSET}\n')
        f.write('                rm -r Ateam_LBA.sky\n')
        f.write('                rm -r instrument\n')
        f.write('        fi\n\n')
        f.write('        # re-set MS name\n')
        f.write('        MS=${MSOUT}\n')
        f.write('else\n')
        f.write(r'''        echo "Demixing parset does not exist, no demixing done."''')
        f.write('\n')
        f.write('fi\n')
        f.write('\n')
        f.write('################################## AVERAGING #####################################\n')
        f.write('\n')
        f.write('msoverview in=${MS} verbose=T > sbinfo.log\n')
        f.write('finalchan={} ## read from file\n'.format(freqres))
        f.write('finaltime={} ## read from file\n\n'.format(timeres))
        f.write('# check logs/sbinfo.log for current time resolution\n')
        f.write(r'''TMP=`grep "TOPO" sbinfo.log`''')
        f.write('\n')
        f.write(r'''nchan=`echo ${TMP} | cut -d' ' -f 3`''')
        f.write('\n\n')
        f.write(r'''TMP=`grep "Total integration" sbinfo.log`''')
        f.write('\n')
        f.write(r'''inttime=`echo ${TMP} | cut -d' ' -f 8`''')
        f.write('\n')
        f.write(r'''TMP=`grep "ntimes" sbinfo.log`''')
        f.write('\n')
        f.write(r'''TMP1=`echo ${TMP} | cut -d'=' -f 3`''')
        f.write('\n')
        f.write(r'''ntimes=`echo ${TMP1} | cut -d' ' -f 1`''')
        f.write('\n')
        f.write(r'''timeres=`echo "${inttime} / ${ntimes}" | bc`''')
        f.write('\n\n')
        f.write('# calculate freqstep and timestep\n')
        f.write(r'''chanstep=`echo "${nchan} / ${finalchan}" | bc`''')
        f.write('\n')
        f.write(r'''timestep=`echo "${timeres} / ${finaltime}" | bc`''')
        f.write('\n\n')
        f.write('if [ ${chanstep} == 1 ] && [ ${timestep} == 1 ]; then\n')
        f.write(r'''        echo "Frequency and time averaging not needed."''')
        f.write('\n')
        f.write('else\n')
        f.write('        # if zero, then use freqstep and timestep of 1\n')
        f.write('        if [ ${chanstep} == 0 ]; then chanstep=1; fi\n')
        f.write('        if [ ${timestep} == 0 ]; then timestep=1; fi\n\n')
        f.write('        ## msout file name\n')
        f.write(r'''        POS=`expr "${MS}" : '.*.MS'`''')
        f.write('\n')
        f.write('        BASENAME=${MS:0:$POS-3}\n')
        f.write('        MSOUT=${BASENAME}.avg.MS\n\n')
        f.write('        ## write a parset with the correct information for the subband\n')
        f.write('        PARSET=SB${SB}.ndppp.avg.parset\n')
        f.write('        echo msin=${MS} > ${PARSET}\n')
        f.write('        echo msout=${MSOUT} >> ${PARSET}\n')
        f.write('        cat >> ${PARSET} << EOF\n')
        f.write('steps=[avg]\n')
        f.write('avg.type=averager\n')
        f.write('avg.freqstep=${chanstep}\n')
        f.write('avg.timestep=${timestep}\n')
        f.write('EOF\n\n')
        f.write('        ## Run NDPPP ##\n')
        f.write('        NDPPP ${PARSET} > SB${SB}.log.lb.avg 2>&1\n')
        f.write('        # remove parset\n')
        f.write('        rm ${PARSET}\n')
        f.write('        # move demixed subband to storage\n')
        f.write('        mv ${MS} ${STORAGE_DIR}/${MS}\n')
        f.write('        # re-set MS name\n')
        f.write('        MS=${MSOUT}\n\n')
        f.write('fi\n\n')
        f.write('################################## CALIBRATION #####################################\n')
        f.write('\n')
        f.write('# set the parset and the model\n')
        f.write('PARSET=calibrate.parset\n')
        f.write('cat >> ${PARSET} << EOF\n')
        f.write('Strategy.ChunkSize=0\n\n')                                                                                                                              
        f.write('Strategy.InputColumn=DATA\n')
        f.write('Strategy.Steps=[solve,correct]\n')
        f.write('Strategy.Steps=[solve]\n\n')
        f.write('Step.solve.Model.Beam.Enable=T\n')
        f.write('Step.solve.Model.Gain.Enable=T\n')
        f.write('Step.solve.Model.Sources=[]\n')
        f.write('Step.solve.Operation=SOLVE\n')
        f.write('Step.solve.Solve.CellChunkSize=300\n')
        f.write('Step.solve.Solve.CellSize.Freq=0\n')
        f.write('Step.solve.Solve.CellSize.Time=5\n')
        f.write('Step.solve.Solve.Options.BalancedEqs=F\n')
        f.write('Step.solve.Solve.Options.ColFactor=1e-9\n')
        f.write('Step.solve.Solve.Options.EpsDerivative=1e-9\n')
        f.write('Step.solve.Solve.Options.EpsValue=1e-9\n')
        f.write('Step.solve.Solve.Options.LMFactor=1.0\n')
        f.write('Step.solve.Solve.Options.MaxIter=100\n')
        f.write('Step.solve.Solve.Options.PropagateSolutions=T\n')
        f.write('Step.solve.Solve.Options.UseSVD=T\n')
        f.write('Step.solve.Solve.Parms=["Gain:0:0:*","Gain:1:1:*"]\n')
        f.write('\n')
        f.write('Step.correct.Model.Beam.Enable=T\n')
        f.write('Step.correct.Model.Gain.Enable=T\n')
        f.write('Step.correct.Model.Sources=[]\n')
        f.write('Step.correct.Operation=CORRECT\n')
        f.write('Step.correct.Output.Column=CORRECTED_DATA\n')
        f.write('EOF\n\n')
        f.write('MODEL={}\n'.format(skymodel))
        f.write('# run bbs to calibrate\n')
        f.write('calibrate-stand-alone -f ${MS} ${PARSET} ${MODEL} > SB${SB}.log.run_bbs_calibrator 2>&1\n')
        f.write('# run msoverview when this is finished\n')
        f.write('msoverview in=${MS} > calfinished.log\n')
	f.write('# remove parset\n')
	f.write('rm ${PARSET}\n')
        f.write('# get the frequency of the subband\n')
        f.write(r'''TMP=`grep "TOPO" calfinished.log`''')
        f.write('\n')
        f.write(r'''SBFREQ=`echo ${TMP} | cut -d' ' -f 8`''')
        f.write('\n')
        f.write('echo ${SBFREQ} SB${SB} >> ${WORK_DIR}/cal_sb_freqs\n\n')
        f.write('# plot the solutions\n')
	f.write('python /home/wwilliams/para/scripts/plot_solutions_all_stations.py ${MS}/instrument cal_solutions\n\n')
        f.write('################# done ##########################\n')
    f.close()

##----------------------- PARAMETERS ----------------------- 


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-t','--target',default=False,dest='targetname',help='Name of target for the observation',required=True)
    parser.add_argument('-e','--email',default='lmorabit@gmail.com',dest='myemail',help='email address for notifications to be sent to',required=True)
    parser.add_argument('-r','--root-dir',default=False,dest='rootdir',help='Name of root directory of observation',required=True)
    parser.add_argument('-u','--username-lta',default=False,dest='ltaun',help='Your LTA username, to be written in the download script',required=True)
    parser.add_argument('-p','--password-lta',default=False,dest='ltapw',help='Your LTA password, to be written in the download script',required=True)
    parser.add_argument('-L','--LBA',action='store_true',default=False,dest='lbaflag',help='set to True if this is an LBA observation') 
    args = parser.parse_args()
    pipeline(args)
