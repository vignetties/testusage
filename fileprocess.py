
import os

#"x" - Create - will create a file, returns an error if the file exist

#open("/tmp/noargmyfile.txt", "x")

prof = [ "primary" ]

for i in prof:
    print("fileis :"+ i)
    filename = "/tmp/maintenance-svc." + i
    print ("flagis"+ filename)
    #open(filename, "x")
filename = ''.join(prof)
print (filename)
