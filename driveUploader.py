#
#	driveUploader.py
#
#	Monitor the spool directory and upload incoming files to the google drive
#	This module will stay resident to monitor the spool direcotry every 10 seconds.

import os
import time
import glob
import re

###############################################################
# Initialize logger

import logging
import logging.handlers

# setup root logger
logger = logging.getLogger("")
logger.setLevel(logging.DEBUG)

h1 = logging.StreamHandler()
h1.setLevel(logging.DEBUG)
h1.setFormatter(logging.Formatter('%(asctime)s : %(levelname)s [ %(funcName)s ] %(message)s'))
logger.addHandler(h1)

h2 = logging.handlers.SysLogHandler()
h2.setLevel(logging.INFO)
h2.setFormatter(logging.Formatter('%(levelname)s [ %(funcName)s ] %(message)s'))
logger.addHandler(h2)

# setup module logger
logger = logging.getLogger(__name__)

###############################################################
# Initialize driveLibrary

import sys
sys.path.append('/home/pi/projects/driveLibrary')
import driveLibraryV3

# create google drive service instance
gd = driveLibraryV3.driveLibrary(logger)
service = gd.GD_createService()

###############################################################
# CONSTANT VALUES

log_folderId =  "0BwEMWPU5Jp9SN0cyM0N6ZWN1Wk0"		#// log directory
exec_folderId = "0BwEMWPU5Jp9SNExlMFdXdkdEZUE"		#// remote execution log directory
cam_folderId  = "0BwEMWPU5Jp9SZDNEOEdaeWJrQjA"		#// captured image file directory
tn_folderId   = "0BwEMWPU5Jp9SVkp5V3Q5bjhxVkE"		#// captured image thumbnail file directory

spool_dir = "/var/www/_spool/"
waiting_dir = spool_dir + "waiting/"

###############################################################
# MAIN LOOP

meta_data_queue = {}	# imginf*.txt queue
file_queue = {}		# auto captured jpeg file queue

while True:

  try:

    ###############################################################
    # Watch spool directory
    logger.debug("### Check SPOOL ###")	#####
    list = glob.glob(spool_dir+"*")

    for f in list:

	if os.path.isdir(f) or os.path.islink(f) :
	    continue

	base_f = os.path.basename(f)

	##### the case of image inf file
	m = re.search('imginf([0-9][0-9-_]+)\.txt', base_f)
	if m is not None:
	    # the file contents is retrieved and copied to the queue entry and inf-file itself is deleted
	    timeStamp = m.group(1)

	    try:
		inf_v = {}
		imginf_file = open(f, 'r')

		for inf_line in imginf_file:
		    inf_i = inf_line.split('=')
		    inf_v[inf_i[0].strip(' \n')] = inf_i[1].strip(' \n') 

		imginf_file.close()
	        try:
		    os.rename(f, waiting_dir+base_f)
	        except OSError:
		    os.mkdir(waiting_dir)
		    os.rename(f, waiting_dir+base_f)

		inf_v['@counter'] = 4
		meta_data_queue[timeStamp] = inf_v

	    except IOError:
		# Since this file can not read, delete and ignore it.
		logger.error("imginf file cannot open.")
		os.unlink(f)
		continue

	    logger.debug(base_f + " :queued")	#####
            continue
            
	##### the case of auto captured image file
	m = re.search('(ccam|tn|Bcam)_([0-9][0-9-_]+)\.jpg', base_f)

	if m is not None:
	    # The file is an candidate of an auto captured image file
	    # Anyway, It is moved to waiting directroy.

	    try:
		os.rename(f, waiting_dir+base_f)
	    except OSError:
		os.mkdir(waiting_dir)
		os.rename(f, waiting_dir+base_f)

	    file_queue[base_f] = 4

	    logger.debug(base_f + " :queued")	#####
            continue

	##### Exception case of the _spool usage - - - sens_log2.csv file isn't a target of upload
	if base_f == "sens_log2.csv":
            logger.debug("sens_log2.csv should be ignored.")
	    continue

	##### the case of remote execution command LOG files
	m = re.search('cmd_.*\.log', base_f)

	if m is not None:
	    gd.GD_uploadNewFile(service, base_f, exec_folderId, "", "text/plain", f)
	    os.unlink(f)

	    logger.info(base_f + " :uploaded(remote execution log)")	#####
            continue

	### the case of other files
	extention = os.path.splitext(f)

	if extention == '.jpg':
	    mimeType = 'image/jpeg'
	elif extention == '.html':
	    mimeType = 'text/html'
	else:
	    mimeType = 'text/plain'

	gd.GD_uploadFile(service, base_f, log_folderId, "", mimeType, f)
	os.unlink(f)

	logger.info(base_f + " :uploaded(ordinary)")	#####

    ###############################################################
    # Check a correspondence of auto captured image and it's meta-data
    logger.debug("### CHECK QUEUE CORRESPONDENCE###")	#####

    for base_f in file_queue.copy():    # Since Queue contents may be deleted duaring a italation, use a copy of the queue for loop.

	m = re.search('(ccam|tn|Bcam)_([0-9][0-9-_]+)\.jpg', base_f)
	timeStamp = m.group(2)

	if timeStamp in meta_data_queue:

	    # A meta-data of this image file is aleady queued.
	    inf_v = meta_data_queue[timeStamp]
	    description =  "distance = " + inf_v['distance'] + "\n"
	    description += "illuminance = " + inf_v['Lux'] + "\n"
	    description += "Exposure data = " + inf_v['ExposureTime']
	    description += " - " + inf_v['F'] + " - " + inf_v['ISO']

	    if ('obj.distance' in meta_data_queue):
		description += "\no.dist = " + inf_v['obj.distance']
		description += " o.agrg = " + inf_v['obj.average']
		description += " o.ratio = " + inf_v['obj.ratio']

            ## !!! TO BE CONSIDERD !!!
            ## If There is a inconsistency between a waiting directory and a file_queue,
            ##  the error occurs here.
            ## Inconsistent situation is generated when user delete files in the waithing directory from a shell.

	    if m.group(1) == 'tn' or m.group(1) == 'tnb' :
		gd.GD_uploadNewFile(service, base_f, tn_folderId, description, "image/jpeg", waiting_dir + base_f)
		os.unlink(waiting_dir + base_f)
		del file_queue[base_f]
	    else:
		gd.GD_uploadNewFile(service, base_f, cam_folderId, description, "image/jpeg", waiting_dir + base_f)
		os.unlink(waiting_dir + base_f)
		del file_queue[base_f]

	    logger.info(base_f + " :uploaded(auto captured)")	#####

	else:

	    # A meta-data of the file is not queued yet.
	    file_queue[base_f] -= 1

	    if file_queue[base_f] == 0:

		# TIMEOUT
		# This jpeg file is uploaded as an ordinary jpeg file.

                ## !!! TO BE CONSIDERD !!!
                ## If There is a inconsistency between a waiting directory and a file_queue,
                ##  the error occurs here.
                ## Inconsistent situation is generated when user delete files in the waithing directory from a shell.

		gd.GD_uploadNewFile(service, base_f, log_folderId, "", "image/jpeg", waiting_dir + base_f)
		os.unlink(waiting_dir + base_f)
		del file_queue[base_f]
		logger.info(base_f + " :uploaded(ordinary file)")	#####

	    else:
		logger.debug(base_f + " : stay in the file_queue")	#####


    ###############################################################
    # Timeout check of the meta-data queue entry
    logger.debug("check meta_data queue")	#####

    for timeStamp in meta_data_queue.copy():    # Since Queue contents may be deleted duaring a italation, use a copy of the queue for loop. itaration.

	meta_data_queue[timeStamp]['@counter'] -= 1

	if meta_data_queue[timeStamp]['@counter'] == 0:

	    # TIMEOUT
	    # file and queue entry is deleted
	    del meta_data_queue[timeStamp]
	    os.unlink(waiting_dir + 'imginf' + timeStamp + '.txt')
	    logger.debug(timeStamp + " : dequeued from the meta_data_queue");

	else:
	    logger.debug(timeStamp + " : stay in the meta_data_queue");

  except: HttpError:
    import traceback
    logger.error(traceback.print_exc())
    time.sleep(20)

  time.sleep(20)

###############################################################
