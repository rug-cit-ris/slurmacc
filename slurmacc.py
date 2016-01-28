#!/usr/bin/env python


import ldap
import csv
import sys
import subprocess
import optparse
import datetime
import operator
from datetime import date

# Parameters
energy = 0

# Global values
totalCPU = 0
totalEnergy = 0

def getargs():
	
	today=date.today()
	
	usage = "usage: %prog [options]"
	parser = optparse.OptionParser(usage=usage)
	
	parser.add_option("-b","--debug", dest="debug", default=False, action="store_true",
					  help="Shows progress of program, ")
	
	parser.add_option("-n","--cputime", dest="cputime", default=False, action="store_true",
					  help="Report on used cpu time (hours), "+ 
						   "the default is to report on used wallclock time (hours).")
	
	parser.add_option("-m","--energy", dest="energy", default=False, action="store_true",
					  help="Report on used energy (joules)")
	
	parser.add_option("-j","--jobs", dest="jobs", default=False, action="store_true",
					  help="Report on number of jobs run, "+
						   "the default is to report on used wallclock time (hours).")
	parser.add_option("-s","--startdate",dest="startdate", default=str(datetime.date(today.year-1,today.month,today.day)),
					  help="Only include accounting records from this date on, " +
						   "format yyyy-m-d."
					 ) 
	parser.add_option("-e","--enddate",dest="enddate", default=str(today),
					  help="Only include accounting records for up to, " +
						   "and not including this date , format yyyy-m-d."
					 )

	parser.add_option("-u","--user", dest="user", default=False, action="store_true",
					  help="Present accounting information for all users by their name. " 
					 )
	parser.add_option("-d","--uid", dest="uid", default=False, action="store_true",
					  help="Display user information based on uid, instead of full name " 
					  )
						   
	parser.add_option("-r","--research", dest="research", default=False, action="store_true", 
					  help="Present accounting information for this " +
						   "comma separated list of research institutes. " + 
						   "Specifying all will result in information " +
						   "aggregated per research institute for all research institutes"
						   "Specifying list will result in a list of known groups."
					 )
	parser.add_option("-f","--faculty", dest="faculty", default=False, action="store_true", 
					  help="Present accounting information for this " +
						   "comma separated list of faculties. Specifying all" +
						   "will result in information aggregated per faculty for all faculties"
						   "Specifying list will result in a list of known groups."
					 )

	parser.add_option("-o","--sort", dest="sort", default=False, action="store_true",
				  help="Sort table on user, group, faculty or research " + 
					   "institute, instead of on used time."
					 )
	
	parser.add_option("-x","--csv", dest="csv", default=False, action="store_true",
					  help="Show results in comma separated value format"
					 )
					 
	parser.add_option("-p", "--password", dest="password", default="",
					  help="Supply db password as argument on command-line"
					 )
	parser.add_option("-t","--time",dest="time", default='m',
					 help="Output time unit, default is in minutes."
					 )	
	(options, args) = parser.parse_args()
	if options.cputime and options.energy:
		parser.error("Options -n and -m are mutually exclusive.")
	if options.uid and options.person:
		parser.error("Options -u and -d are mutually exclusive.")
	
	try:    
		startdate = options.startdate.split('-')
		enddate = options.enddate.split('-')
		options.startdate=datetime.date(int(startdate[0]),int(startdate[1]),int(startdate[2]))
		options.enddate=datetime.date(int(enddate[0]),int(enddate[1]),int(enddate[2]))
	except:
		parser.error("Wrong date specified for -s or -e, use the format YYYY-MM-DD")
	if len(args) !=0:
		parser.error("Unrecognised arguments supplied")
	if startdate > enddate:
		parser.error("Start date must be before the end date.")
	return options

def openPersonDB():
	DB = []
	try:
		with open('PersonDB.csv', 'rb') as f:
			csvfile = csv.reader(f, delimiter=';', quoting=csv.QUOTE_NONE)
			DB = [row for row in csvfile]
	except IOError:
		print "File PersonDB.csv does not exist. It is now created."	
	return DB

def clusterLDAP(pw):
	l = ldap.initialize("ldap://172.23.47.249")
	try:
		l.protocol_version = ldap.VERSION3
		l.set_option(ldap.OPT_REFERRALS, 0)	
		bind = l.simple_bind_s("cn=clusteradminperegrine ,o=asds", pw)
		base = "ou=Peregrine, o=asds"
		criteria = "objectClass=Person"
		attributes = ['uid', 'ou', 'fullName']
		result = l.search_s(base, ldap.SCOPE_SUBTREE, criteria, attributes)
		results = [entry for dn, entry in result if isinstance(entry, dict)]
		return results
	except:
		print "Invalid password"
		sys.exit()
	finally:
		l.unbind()
		
def updateDB(ldap):
	DB = openPersonDB()
	appendPerson = []
	removePerson = []
	for dict in ldap:
		found = False
		for person in DB:
			# If database is not empty check if uids match with ldap.
			if person[0] == '' and person[1] == '' and person[2] == '':
				DB.remove(person)
				break
			if dict['uid'][0] == person[0]:
				# Checks new full names. What if someone changes his/ her name?
				if 'fullName' in dict and (person[2] == '' or person[2] == 'noFullName'):
					print person[0] + " previously had no full name in LDAP, but now has a full name: " + dict['fullName'][0]
					person[2] = dict['fullName'][0]
					continue
				# Also check if ou fields match with ldap (someone could have a new ou field).
				if 'ou' in dict:
					# Check if ou field still is actual, else removes the entry and puts it in the changed list.
					for row1 in DB:
						if (row1[0] == dict['uid'][0] and row1[1] not in dict['ou']) and not (row1[1] == '' or row1[1] == 'unknown ou,UKN'):
							print row1[1]
							
							removePerson.append(row1)
					# Checks for every field if it is in the DB.
					appendFields = []
					for i in range(0,len(dict['ou'])):
						for row2 in DB:
							# True if the uid and the field are the same.
							if row2[0] == dict['uid'][0] and dict['ou'][i] == row2[1]:
								break
						# If there is no uid with this field then add this field.
						else:
							appendFields.append(dict['ou'][i])
					if appendFields != []:
						
						if 'ou' in dict and (person[1] == '' or person[1] == 'unknown ou,UKN'):
							print person[0] + " has a new ou field in LDAP, but now has a known field: "
							removePerson.append(person)
							continue
						for i in range(0, len(appendFields)):
							appendPerson = ['','','']
							appendPerson[0] = dict['uid'][0]
							appendPerson[1] = str(appendFields[i])
							appendPerson[2] = str(dict['fullName'][0])
							print person[0] + " has a new field: " + appendFields[i]
							DB.append(appendPerson)
						appendFields = []
				break
			else:
				# Happens when the database is empty, all persons from ldap get added.
				pass
			# Used to break through a second for loop.
			if found == True:
				break
		else:
			# If the person in LDAP was not in the DB.
			appendPerson = ['','','']
			appendPerson[0] = str(dict['uid'][0])
			if 'ou' in dict:
				for i in range(0,len(dict['ou'])):
					appendPerson = ['','','']
					appendPerson[0] = str(dict['uid'][0])
					appendPerson[1] = str(dict['ou'][i])
					if 'fullName' in dict:
						appendPerson[2] = str(dict['fullName'][0])
					if 'fullName' not in dict:
						appendPerson[2] = ''
					DB.append(appendPerson)
					print appendPerson[0] + " with field " + appendPerson[1] + ' added to DB by LDAP.'
			if 'ou' not in dict:
				appendPerson[1] = ''
				if 'fullName' in dict:
					appendPerson[2] = dict['fullName'][0]
				if 'fullName' not in dict:
					appendPerson[2] = ''
				DB.append(appendPerson)
				print appendPerson[0] + " with field " + appendPerson[1] + ' added to DB by LDAP.'
	# Create new file.
	with open('PersonDB.csv', 'w+') as f:
		f.write('')
	# Only remove persons from DB if necessary.
	if removePerson != []:
		for row in removePerson:
			if row[1] != '':
				print str(row[0]) + " with field: " + str(row[1]) + " is removed and put in changedDB.csv"
			DB.remove(row)
		date = datetime.date.today()
		with open('removedDB.csv', 'ab') as f:
			for row in removePerson:
				if not (row[1] == '' or row[1] == 'unknown ou,UKN'):
					f.write(str(row[0])+';'+str(row[1])+';'+str(row[2])+';'+str(date) +'\n')
	# Rewrite the new DB file with all people and their updated fields to PersonDB.csv.
	with open('PersonDB.csv', 'ab') as f:
		for row in DB:
			f.write(str(row[0])+';'+str(row[1])+';'+str(row[2])+'\n')

def CPUTime(s, e, timeunit):
	# s = startdate, e = enddate.
	sreport = subprocess.Popen(["sreport", "cluster", "AccountUtilizationByUser","-t"+timeunit,  "start="+s, "end="+e, "format=Login,Used,Energy", "-n", "-p"], stdout=subprocess.PIPE)
	(output, err) = sreport.communicate()
	cpu = output.split()
	sReport = []
	for i in cpu:
		sReport.append(i.split('|'))
	return sReport

def updateDBwithSReport(newDB):
	with open('PersonDB.csv', 'w+') as f:
		f.write('')
	for row in newDB:
		with open('PersonDB.csv', 'ab') as f:
			f.write(str(row[0])+";"+str(row[1])+";"+str(row[2])+"\n")
	
def addCPUTimeToDB(sReport):
	DB = openPersonDB()
	global totalCPU
	totalCPU = int(sReport[0][1])
	newPersonList = []
	for srPerson in sReport:
		if srPerson[0] == "":
				continue
		pCount = 0 # Used for dealing with people that occur more than once in the DB.
		for row in DB:
			# If the person in sreport is also in the DB.
			if srPerson[0] == row[0]:
				count = 0
				for doubles in DB:
					if srPerson[0] == doubles[0]:
						count = count +1
				# CPUtime		
				try:
					row[3] = float(row[3]) + (float(srPerson[1])/count)
				except IndexError:
					row.append(float(srPerson[1])/count)
				# Energy
				try:
					row[4] = float(row[4]) + (float(srPerson[2])/count)
				except IndexError:
					row.append(float(srPerson[2])/count)
				if count > 1:
					pCount = pCount + 1
					if pCount == count:
						break
				else:
					break
		else:
			newPerson = [srPerson[0],'unknown ou,UKN', 'noFullName', srPerson[1], srPerson[2]]
			DB.append(newPerson)
			print row[0] + " with field " + row[1] + " added to DB by sReport."
	updateDBwithSReport(DB)
	return DB

def reportPersonData(data,options):
	delim = ';'
	if options.csv:
		delim = ','
	for row in data:
		try:
			if row[3]:
				pass
		except IndexError:
			row.append(int(0))
		try:
			if row[4]:
				pass
		except IndexError:
			row.append(int(0))
	if options.sort:
		if options.user:
			sorted_data = sorted(data, key=operator.itemgetter(2))
			for row in sorted_data:
				print row[2] + delim + row[0] + delim + str(row[3]) + delim + str(row[4])
		else: #if options.uid
			sorted_data = sorted(data, key=operator.itemgetter(0))
			for row in sorted_data:
				print row[0] + delim + row[2] + delim + str(row[3]) + delim + str(row[4])
	else:
		if options.energy:
			sorted_data = sorted(data, key=operator.itemgetter(4), reverse=True)
			for row in sorted_data:
				if row[4] != 0:
					print row[0] + delim + row[1] + row[2] + delim + str(row[4])
		else: #if options.cputime:
			sorted_data = sorted(data, key=operator.itemgetter(3), reverse=True)
			for row in sorted_data:
				if row[3] != 0:
					print row[0] + delim + row[1] + delim + row[2] + delim + str(row[3])
	
def calcOuHistogramData(data, i):
	ouHistogramCPUTime = dict()
	for row in data:
		if row[1] in ouHistogramCPUTime: 
			try:
				ouHistogramCPUTime[row[1]] = ouHistogramCPUTime[row[1]] + float(row[3+i])
			except IndexError:
				pass
		else:
			try:
				ouHistogramCPUTime[row[1]] = float(row[3+i])
			except IndexError:
				pass
	return ouHistogramCPUTime

def reportDepartmentData(ouHistogramData, options):
	delim = ";"
	if options.csv == True:
		delim = ","
	if options.sort == True:
		sorted_ouHistogramData = sorted(ouHistogramData.items(), key=operator.itemgetter(0))
	else:
		sorted_ouHistogramData = sorted(ouHistogramData.items(), key=operator.itemgetter(1), reverse=True)
	for row in sorted_ouHistogramData:
		if row[1] != 0:
			print row[0] + delim + str(row[1])
	
def calcFacultyData(ouHistogramData):
	facultyData = dict()
	# Finds faculty names and takes the faculty code from it:
	# e.g. Biomedical Engineering,UCM gets put in UCM.
	for row in ouHistogramData:
			for i in range(len(row)):
				# Stops searching for faculty codes after 4 characters.
				if i > 4:
					continue
				if row[len(row)-1-i] == ',':
					facultyCode = row[len(row)-i:]
					if facultyCode in facultyData:
						facultyData[facultyCode] = facultyData[facultyCode]  + ouHistogramData[row]
					else: 
						facultyData[facultyCode] = ouHistogramData[row]
	return facultyData
	
def reportFacultyData(facultyData, options, cpu):
	delim = ";"
	# If the time unit is not seconds, minutes or hours yet:
	if options.time == 'm' or options.time == 'minute':
		options.time = 'minutes'
	if options.time == 's' or options.time == 'second':
		options.time = 'seconds'
	if options.time == 'h' or options.time == 'hours':
		options.time = 'hours'
	if options.csv == True:
		delim = ","
	# Used for calculating missing data.
	totalFacultyData = 0
	if options.sort == True:
		sorted_facultyData = sorted(facultyData.items(), key=operator.itemgetter(0))
	else:
		sorted_facultyData = sorted(facultyData.items(), key=operator.itemgetter(1), reverse=True)
	# The actual report.
	for row in sorted_facultyData:
		totalFacultyData = totalFacultyData + row[1]
		if row[1] != 0:
			print row[0]+ delim + str(row[1])
	# Report unclassified seconds, minutes or hours.
	if cpu == True:
		unknownCPU = totalCPU - totalFacultyData
		if unknownCPU > 5 or unknownCPU < -5: # Prevents from being printed when rounded of.
			print str(unknownCPU) + " CPU "+ options.time.lower() + " are unclassified" 

def main():
	options = getargs()
	if options.debug:
		print "Connecting with LDAP."
	ldapDict = clusterLDAP(options.password)
	if ldapDict == []:
		print "LDAP failed, please provide a password with option -p and the password."
		return
		
	if options.debug:
		print "Retrieving data from sReport."
	cpu = CPUTime(str(options.startdate), str(options.enddate), str(options.time))
	try:
		assert cpu
	except AssertionError:
		print "Failed to import data from sReport."
	
	if options.debug:
		print "Updating DB with LDAP."
	updateDB(ldapDict)
	
	# Gives CPU time per user and adds new users.
	if options.debug:
		print "Updating DB with sReport."
	data= addCPUTimeToDB(cpu)
	
	
	
	# Print all cluster users names or uids and their cputime or energy used.
	if options.user or options.uid:
		reportPersonData(data, options)
	
	# CPU/energy for each department (e.g. "Kunstmatige Intelligentie,FWN").
	if options.research or options.faculty: 
		if options.debug and (options.research or options.faculty):
			print "Calculating histograms."
		if options.cputime:
			ouHistogramCPUTime = calcOuHistogramData(data, False)
		if options.energy:
			ouHistogramEnergy = calcOuHistogramData(data, True)
	
	# Print each department and their CPU time or energy:
	if options.research: 
		if options.debug and (options.research or options.faculty):
			print "Reporting data for departments."
		if options.cputime:
			reportDepartmentData(ouHistogramCPUTime, options)
		if options.energy:
			reportDepartmentData(ouHistogramEnergy, options)
	
	# CPU time or energy for each faculty code (e.g. FWN).
	if options.faculty:
		if options.debug and (options.research or options.faculty):
			print "Reporting data for faculties."
		if options.cputime:
			facultyCPUTime = calcFacultyData(ouHistogramCPUTime)
			reportFacultyData(facultyCPUTime, options, True)
		if options.energy:
			facultyEnergy = calcFacultyData(ouHistogramEnergy)
			reportFacultyData(facultyEnergy, options, False)
	
if __name__ == "__main__":
	main()