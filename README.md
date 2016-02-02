# slurmacc
Tools to add extra information from LDAP to the user info in SLURM sreport overviews.

# About

test
The slurmacc file is used to create a data base of a persons UID, the field he/she works in and his/her full name, using Lightweight Directory Access Protocol (LDAP), and then reports the amount of time spend by the user. 
slurmacc.py also adds missing users from LDAP that are in sReport to the database. All fields that are unknown can be filled in manually, but will get updated if the fields are known in LDAP and are different.
The data from sreport that yields the amount of wallclock time spend on the cores of the Peregrine cluster is paired with the UID and then distributed over their fields.
For example if someone has an UID of p123456 and is in the departments Artificial Intelligence,XYZ and Biomedical Engineering,WXY and sReport has a value of 100 hours consumed on the cluster,
then the fields Artificial Intelligence,XYZ and Biomedical Engineering,WXY both get accounted for 50 hours.
If this is done for every user, all time spend for every department is added up such that it is clear which department has used the cluster for a certain time.
At last it is also possible to request the amount of time used by the faculty codes. This means that the time of Artificial Intelligence,XYZ and Computing Science,XYZ are added to the faculty code XYZ.
This file prioritises the data from LDAP, but if information is missing, then it will use the fields that are added manually or at last name them to unknown. If a person gets removed from LDAP, the person is put in another file with the date of removement. 
Hence, this file is an up-to-date datebase of all users in LDAP and is able to report the time spend on a cluster for the user, department, or faculty code.

# How to use

The following command returns the amount of time spend(default: -n) for the user (-u), the department (-r) and the faculty code (-f) in hours (by -t h) on the cluster.
slurmacc.py can be run by the command: 'slurmacc.py -p "password" -t h -u -r -f -n'.
Note that slurmacc.py requires a password for LDAP and thus the password is put after "-p".

For only updating the database the optionalities -u -r -n -f can be left out.
Changes are reported in the output.
