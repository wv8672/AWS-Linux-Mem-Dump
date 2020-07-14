import boto3
import botocore
import paramiko
from termcolor import colored 
import time


#A Python Boto3 script which:
#-----------------------------------------

#Lists EC2 Instances and associated Volumes..
#Accepts Instance selection for Memory Dump
#-------
#Builds a Forensic Volume 
#Attaches Forensic Volume to selected Instance 
#SSH into selected Instance
#Runs script that:  
# ==> Mounts Forensic Volume to selected Instance 
# ==> Uses LiME to Dump Memory of Instance on to attached Forensic Volume
# ==> Unmounts Forensic Volume of the selected Instance
#-------
#Detaches the Forensic Volume from selected Instance 
#-------
#Builds a SIFT Workstation Instance
#Attaches the Forensic Volume to the SIFT Workstation
#-------
#SSH into SIFT Workstation Instance and mounts the Volume


##############################################################################################################################

#Import AWS creds from config.properties

def getVarFromFile(filename):
    import imp
    f = open(filename)
    global data
    data = imp.load_source('data', '', f)
    f.close()

getVarFromFile('config.properties')

##############################################################################################################################

#Set Boto3 Resource and Client variables

vpc_client = boto3.client('ec2')
vpc_resource = boto3.resource('ec2')

##############################################################################################################################

#List EC2 Instances and associated Volumes..

print(" \nPRINTING EC2 INSTANCE STATS" )
print('-------------------------------------------------- \n')

for instance in vpc_resource.instances.all():

    for instance_name in instance.tags:
        if instance_name['Key'] == 'Name':
            print_value = instance_name['Value']
            print colored("Instance: %s" %print_value, 'green')
    print(
         "Id: {0}\nPublic IP: {1}\nPrivate IP: {2}\nSubnet: {3}\nAMI: {4}\n".format(
         instance.id, instance.public_ip_address, instance.private_ip_address, instance.subnet_id, instance.image.id
         )
     )

    for vol_data in instance.block_device_mappings:
        volume = vol_data.get('Ebs')
        print(
            "Mounted Vol: {0}\nVol Id: {1}\nVol Status: {2}\n".format(
            vol_data['DeviceName'], volume.get('VolumeId'), volume.get('Status')
            )
        )
print('################################################\n')

###########################################################################################################################

#Accept Instance selection for Memory Dump

print("[ ENTER INSTANCE IP & ID TO DUMP MEMORY ]\n")
ip_address = raw_input("ENTER INSTANCE IP\n")
instance_id = raw_input("\nENTER INSTANCE ID\n")

##########################################################################################################################

#Build Forensic Volume 

print('\n===> BUILDING FORENSIC VOLUME..\n')
forensic_volume = vpc_resource.create_volume(
        AvailabilityZone=data.availibilityZone_value,
)
time.sleep(15)
print('===> FORENSIC VOLUME BUILD COMPLETE\n')
for_vol_id = forensic_volume.id
print(for_vol_id)

###########################################################################################################################

#Attach Forensic Volume to selected Instance

print('\n===> ATTACHING FORENSICS VOLUME TO SELECTED INSTANCE.. \n')
vol_attach_instance = vpc_client.attach_volume(
    Device = data.ForVolDevice_value,
    InstanceId = instance_id,
    VolumeId = for_vol_id  
)
time.sleep(10)
print('FORENSIC VOLUME SUCCESSFULLY ATTACHED\n')
print(instance_id, for_vol_id)

##########################################################################################################################

#SSH into selected Instance
#Run remote script to:  
# ==> Mount Forensic Volume to selected Instance 
# ==> Use LiME to Dump Memory of Instance on to attached Forensic Volume
# ==> Unmount Forensic Volume of the selected Instance

print('===> MOUNTING VOLUME TO SIFT WORKSTATION..\n')
instance_conn = paramiko.SSHClient()
instance_conn.load_system_host_keys()
instance_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
instance_conn.connect(workstation_ip, port=data.ConnPort_value, username=data.ConnUsername_value, key_filename=data.ConnKeyFilename_value)
command = data.MemDumpScript_value
(stdin, stdout, stderr) = instance_conn.exec_command(command)
for std_out in stdout.readlines()
    print std_out
    instance_conn.close()

print('\n===> MEMORY DUMP TO FORENSIC VOLUME COMPLETE')

############################################################################################################################

#Detach Forensic Volume from selected Instance

print('\n===> DETACHING FORENSICS VOLUME FROM SELECTED INSTANCE.. \n')
vol_detach_instance = vpc_client.detach_volume(
    VolumeId = for_vol_id  
)
time.sleep(10)
print('===> FORENSIC VOLUME SUCCESSFULLY DETACHED\n')
print(for_vol_id)

##########################################################################################################################

#Build a SIFT Workstation Instance

print('\n===> BUILDING SIFT WORKSTATION INSTANCE..\n')
workstation_instance = vpc_resource.create_instances(
    ImageId = data.ImageId_value,
    SubnetId = data.SubnetId_value,
    MinCount = data.MinCount_value,
    MaxCount = data.MaxCount_value,
    KeyName = data.KeyName_value,
    InstanceType = data.InstanceType_value
)

for instance in workstation_instance:
    instance.wait_until_running()
    instance.reload()
    print('===> SIFT WORKSTATION BUILD COMPLETE\n')
    workstation_id = instance.id
    workstation_ip = instance.public_ip_address
    print(workstation_id)

###########################################################################################################################

#Attach Forensic Volume to SIFT Workstation

print('===> ATTACHING FORENSIC VOLUME TO SIFT WORKSTATION..\n')
vol_attach_workstation = vpc_client.attach_volume(
    Device = data.ForVolDevice_value,
    InstanceId = workstation_id,
    VolumeId = for_vol_id
    )
time.sleep(10)
print('FORENSIC VOLUME SUCCESSFULLY ATTACHED\n')

###########################################################################################################################

#SSH into SIFT Workstation and mount Volume

# Mount Forensic(compromised) Volume 
# -> mkdir /mnt/forensic_data
# -> mount /dev/xvdf1 /mnt/forensic_data

print('===> MOUNTING VOLUME TO SIFT WORKSTATION..\n')
workstation_conn = paramiko.SSHClient()
workstation_conn.load_system_host_keys()
workstation_conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
workstation_conn.connect(workstation_ip, port=data.ConnPort_value, username=data.ConnUsername_value, key_filename=data.ConnKeyFilename_value)
command = data.MountVolume_value
(stdin, stdout, stderr) = workstation_conn.exec_command(command)
for std_out in stdout.readlines()
    print std_out
    workstation_conn.close()

print('\n===> FORENSIC VOLUME MOUNTED TO SIFT WORKSTATION')
print('\n===> READY FOR ANALYSIS::')