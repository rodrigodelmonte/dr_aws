from time import strftime, sleep
import boto.ec2
import datetime

date = strftime("-%Y-%m-%d")

AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''

ec2 = boto.ec2()

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
        inst_name = inst['Name'] + date
        ami = conn_east.create_image(inst['instance_id'],
                                     inst_name, no_reboot)
        ami_list.append([ami, inst_name])
        sleep(5)
    return ami_list


def check_ami(ami):
    '''This function returns the state of an ami after available.'''

    state = conn_east.get_image(ami)
    while state.state == 'pending':
        state = conn_east.get_image(ami)
        sleep(5)
    return state.state

# Creates instances list.
reservations = conn_east.get_all_instances()
instance_list = []
for res in reservations:
    for inst in res.instances:
        instance_list.append({'instance_id': inst.id, 'Name': inst.tags['Name']})

builded_ami = create_ami(instance_list)

for ami in builded_ami:
    ami_id = ami[0]
    ami_name = ami[1]
    ami_status = check_ami(ami_id) #Wait ami be available.
    if ami_status == 'available':
        conn_west.copy_image('us-east-1',
                             ami_id, name=ami_name,
                             description=ami_name)

# Clean old AMI, first test carefully.
sleep(900)
today = datetime.datetime.today()
DD = datetime.timedelta(days=7)
earlier = today - DD
earlier_str = earlier.strftime("%Y%m%d")

my_amys = conn_west.get_all_images(owners='self')

for ami in my_amys:
    if ami.name[-8:] < earlier_str:
        ami.deregister()
