#!/usr/bin/env python3

import optparse
import io
import subprocess
import pandas
import datetime
from datetime import date

def getargs():

    today=date.today()

    usage = "usage: %prog [options]"
    parser = optparse.OptionParser(usage=usage)

    parser.add_option("-d","--debug", dest="debug", default=False, action="store_true",
                      help="Shows progress of program, ")

    parser.add_option("-c","--cputime", dest="cputime", default=False, action="store_true",
                      help="Report on used cpu time (hours), "+
                     "the default is to report on used wallclock time (hours).")

    parser.add_option("-m","--energy", dest="energy", default=False, action="store_true",
                      help="Report on used energy (joules)")

    parser.add_option("-j","--jobs", dest="jobs", default=False, action="store_true",
                      help="Report on number of jobs run, "+
                      "the default is to report on used wallclock time (hours).")

    parser.add_option("-s","--startdate",dest="startdate", 
                      default=str(datetime.date(today.year-1,today.month,today.day)),
                      help="Only include accounting records from this date on, " +
                      "format yyyy-m-d.")

    parser.add_option("-e","--enddate",dest="enddate", default=str(today),
                      help="Only include accounting records for up to, " +
                      "and not including this date , format yyyy-m-d.")

    parser.add_option("-u","--user", dest="user", default=False, action="store_true",
                      help="Present accounting information for all users by their name. ")

    parser.add_option("-i","--uid", dest="uid", default=False, action="store_true",
                      help="Display user information based on uid, instead of full name ")

    parser.add_option("-r","--research", dest="researchgroup", default=False, action="store_true",
                      help="Present accounting information for this " +
                      "comma separated list of research groups. " +
                      "Specifying all will result in information " +
                      "aggregated per research institute for all research groups"
                      "Specifying list will result in a list of known groups.")

    parser.add_option("-f","--faculty", dest="faculty", default=False, action="store_true",
                      help="Present accounting information for this " +
                      "comma separated list of faculties. Specifying all" +
                      "will result in information aggregated per faculty for all faculties"
                      "Specifying list will result in a list of known groups.")

    parser.add_option("-o","--sort", dest="sort", default=False, action="store_true",
                      help="Sort table on user, group, faculty or research " +
                      "institute, instead of on used time.")

    parser.add_option("-x","--csv", dest="csv", default=False, action="store_true",
                      help="Show results in comma separated value format")

    parser.add_option("-t","--time",dest="time", default='m',
                      help="Output time unit, default is in minutes.")

    parser.add_option("-n","--filename", dest="userdata", default="PersonDB.csv",
                      help="Filename for csv file with user data.")

    (options, args) = parser.parse_args()
    if options.cputime and options.energy:
        parser.error("Options -n and -m are mutually exclusive.")
    if options.uid and options.person:
        parser.error("Options -u and -d are mutually exclusive.")
    try:
         startdate = pandas.Timestamp(options.startdate)
         enddate = pandas.Timestamp(options.enddate)
#        startdate = options.startdate.split('-')
#        enddate = options.enddate.split('-')
#        options.startdate=datetime.date(int(startdate[0]),int(startdate[1]),int(startdate[2]))
#        options.enddate=datetime.date(int(enddate[0]),int(enddate[1]),int(enddate[2]))
    except:
        parser.error("Wrong date specified for -s or -e, use the format YYYY-MM-DD")
    if len(args) !=0:
        parser.error("Unrecognised arguments supplied")
    if startdate > enddate:
        parser.error("Start date must be before the end date.")
    return options

def CPUTime(s, e, timeunit):
    # s = startdate, e = enddate.
    encoding = 'ascii'    # specify the encoding of the CSV data
    try:
        sreport = subprocess.Popen(["sreport", "cluster", 
                                   "AccountUtilizationByUser","-t"+timeunit,  
                                   "start="+s, "end="+e, 
                                   "format=Login,Account,Used,Energy","-P"], 
                                   stdout=subprocess.PIPE)
    
        csvData = io.StringIO(sreport.stdout.read().decode())
        usage = pandas.read_csv(csvData, delimiter='|', skiprows=4)
    except:
        print("Error reading data from sreport.")
        print("Command used:")
        print("    sreport cluster AccountUtilizationByUser -t %s start=%s " % (timeunit, e) + 
              "end=%s format=Login,Account,Used,Energy -P" % e)
    usage = usage[pandas.notnull(usage.Login)]
    return usage

def getUserDB(filename, startdate, enddate):
    try:
        userData = pandas.read_csv(filename, parse_dates = [5,6])
    except:
        print("Error reading user data from %s", filename)
    # Remove potential duplicate entries outside our time window
    # 1. Remove all user entries that started later than our time window
    userData = userData[userData.StartDate < enddate]
    # 2. Remove all user entries that finished before our time window
    userData = userData[(userData.EndDate > startdate) | (pandas.isnull(userData.EndDate))]

    # Use the last occurence for each user as the one to account for.
    # This is not completely valid, but separating the usage without going to 
    # a resolution of single day is impossible.
    # 1. Sort on startdate
    userData = userData.sort_values(by='StartDate')
    # 2. Remove duplicates and keep last
    userData = userData.drop_duplicates(subset = ['Username'])
    
    # Remove unnamed first column
    userData = userData.drop(columns=['Unnamed: 0'])
    
    # Rename column Username to Login
    userData.rename({'Username' : 'Login'}, axis =1, inplace=True)
   
    return userData

def getUsageTable(usage, users):
    usageTable = usage.set_index('Login').join(users.set_index('Login'))
    return usageTable

  
def main():
    options = getargs()

    if options.debug:
        print("Retrieving data from sReport.")
    usage = CPUTime(str(options.startdate), str(options.enddate), str(options.time))

    if options.debug:
        print("Reading user data from %s" % options.userdata)
    users = getUserDB(options.userdata, options.startdate, options.enddate)
       
    if options.debug:
       print("Combining sreport data with user data")
    usageTable = getUsageTable(usage, users)

    if options.researchgroup:
       usageTable = usageTable.groupby(['Department','Account']).sum()

    if options.faculty:
       usageTable = usageTable.groupby(['Faculty','Account']).sum()


    usageTable.to_csv("usage.csv")

if __name__ == "__main__":
    main()
