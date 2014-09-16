from time import strftime, sleep
from boto import ec2
import datetime

# Instances name that should be copied to Oregon AWS region.
disaster_recovery_instances = ['Instance00','Instance01']

date = strftime("-%Y-%m-%d")

AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''

conn_east = ec2.connect_to_region("us-east-1",
                                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)

conn_west = ec2.connect_to_region('us-west-2',
                                  aws_access_key_id=AWS_ACCESS_KEY_ID,
                                  aws_secret_access_key=AWS_SECRET_ACCESS_KEY)


def create_ami(instance_list):
    '''This function creates ami and returns a list.'''

    #Use no_reboot carefully, if True your instance will be reboot
    #at snapshot process, but this method is more safe.
    no_reboot=False
    ami_list = []
    for inst in instance_list:
        try:
            ami = conn_east.create_image(inst['instance_id'],
                                         inst['Name'] + date, no_reboot)
        except Exception as e:
            print str(e)
        ami_list.append([ami, inst['Name'] + date])
        sleep(5)
    sleep(30)
    return ami_list


def check_ami(ami):
    '''This function returns the state of an ami after available.'''

    state = conn_east.get_image(ami)
    while state.state == 'pending':
        state = conn_east.get_image(ami)
        sleep(5)
    return state.state


def delete_old_ami(list_ami):
    '''This function deregister an old ami.'''

    date_N_days_ago = datetime.datetime.now() - datetime.timedelta(days=2)
    date_N_days_ago = date_N_days_ago.strftime("%Y-%m-%d")
    for ami in list_ami:
        if ami.name[-10:] <= date_N_days_ago:
            ami.deregister()


# Starts generate ami.
reservations = conn_east.get_all_instances()
instances = [i for r in reservations for i in r.instances]
instance_list = []
for inst in instances:
	if inst.tags['Name'] in disaster_recovery_instances:
		instance_list.append({'instance_id': inst.id, 'Name': inst.tags['Name']})

# Creates instances ami.
builded_ami = create_ami(instance_list)

# Copy ami to Oregon.
for ami in builded_ami:
    ami_id = ami[0]
    ami_name = ami[1]
    ami_status = check_ami(ami_id) #Wait ami be available.
    if ami_status == 'available':
        conn_west.copy_image('us-east-1',
                             ami_id, name=ami_name,
                             description=ami_name)

# Clean old AMI, first test carefully.
sleep(300)

list_ami = conn_west.get_all_images(owners='self')
delete_old_ami(list_ami)
list_ami = conn_east.get_all_images(owners='self')
delete_old_ami(list_ami)