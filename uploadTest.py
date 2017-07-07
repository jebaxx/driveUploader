import os
import time
import logging
import logging.handlers
#import driveLibraryV3
import glob
import re

log_folderId =  "0BwEMWPU5Jp9SN0cyM0N6ZWN1Wk0"		#// log directory
exec_folderId = "0BwEMWPU5Jp9SNExlMFdXdkdEZUE"		#// remote execution log directory
cam_folderId  = "0BwEMWPU5Jp9SZDNEOEdaeWJrQjA"		#// captured image file directory
tn_folderId   = "0BwEMWPU5Jp9SVkp5V3Q5bjhxVkE"		#// captured image thumbnail file directory

#spool_dir = "/var/www/_spool/"
spool_dir = "/tmp/"

# setup root logger
logger = logging.getLogger("")
logger.setLevel(logging.DEBUG)

h1 = logging.StreamHandler()
h1.setLevel(logging.DEBUG)
h1.setFormatter(logging.Formatter('%(asctime)s : %(levelname)s [ %(funcName)s ] %(message)s'))
logger.addHandler(h1)

h2 = logging.handlers.SysLogHandler()
h2.setLevel(logging.DEBUG)
h2.setFormatter(logging.Formatter('%(levelname)s [ %(funcName)s ] %(message)s'))
logger.addHandler(h2)

# setup module logger
logger = logging.getLogger(__name__)

#gd = driveLibraryV3.driveLibrary(logger)

#service = gd.GD_createService()

fileList = {}
waitList = {}

while True:

    print "**********"
    list = glob.glob(spool_dir+"imginf*.txt")

    for f in list:
    
	print f + " found."
	m = re.search('imginf([0-9][0-9-_]+)', f)

	if (m is None):

	    #<<this file is treated as plane text file>>
	    pass

	else:
	    timeStamp = m.group(1)

	    if timeStamp in fileList:
		fileList[timeStamp]['counter'] -= 1
		print "counter = {}".format(fileList[timeStamp]['counter'])

		if fileList[timeStamp]['counter'] == 0:
		    del fileList[timeStamp]

	    else:

		try:
		    inf_v = {}
		    imginf_file = open(f, 'r')

		    for inf_line in imginf_file:
			inf_i = inf_line.split('=')
			inf_v[inf_i[0].strip(' \n')] = inf_i[1].strip(' \n') 

		    imginf_file.close() # <<inf file should be unlinked here>>

		    inf_v['counter'] = 3
		    fileList[timeStamp] = inf_v
		    print "counter = {}".format(fileList[timeStamp]['counter'])

		except IOError:
		    logger.error("imginf file cannot open.")
		    # <<This inf file should be deleted here>>
		    continue


    print "**********"
    list = glob.glob(spool_dir+"*.jpg")

    for f in list:

	print f + " found."
	m = re.search('(ccam|tn|Bcam)_([0-9][0-9-_]+)', f)

	if (m is None):

	    #<<This is a simple jpeg file>>
	    pass

	else:
	    timeStamp = m.group(2)
	    try:
		os.rename(f, spool_dir + "waiting/" + m.group(1) + "_" + timeStamp + ".jpg")
	    except OSError:
		os.mkdir(spool_dir + "waiting")
		os.rename(f, spool_dir + "waiting/" + m.group(1) + "_" + timeStamp + ".jpg")

	    if timeStamp in fileList:
		print "match with imginf file"
		description =  "distance = " + fileList[timeStamp]['distance'] + "\n"
		description += "illuminance = " + fileList[timeStamp]['Lux'] + "\n"
		description += "Exposure data = " + fileList[timeStamp]['ExposureTime']
		description += " - " + fileList[timeStamp]['F'] + " - " + fileList[timeStamp]['ISO']

		if ('obj.distance' in fileList):
		    description += "\nno.dist = " + fileList[timeStamp]['obj.distance']

		print description
		#<<This file is uploaded as an auto captured image>>

		if timeStamp in waitList:
		    del waitList[timeStamp]

	    else:
		if (timeStamp in waitList):
		    waitList[timeStamp] -= 1
		    print "counter = {}".format(waitList[timeStamp])

		    if waitList[timeStamp] == 0:
			#<<This file is uploaded simply as normal jpeg file>>
			print '<<This file is uploaded simply as normal jpeg file>>'
			del waitList[timeStamp]

		else:
		    waitList[timeStamp] = 3
		    print "counter = {}".format(waitList[timeStamp])

    print "* * * * * * * * * * * * * * * * * * * *"
    time.sleep(10)
#    list = glob.glob(spool_dir+"*.csv")
#    for f in list:
#	print f
#    print "**********"

