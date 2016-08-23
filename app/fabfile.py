from fabric.api import *
import boto3


@task
def aws_start():
    image_id_ubuntu = "ami-2d39803a"
    image_id_rhel = "ami-2051294a"
    image_id_aws = "ami-6869aa05"

    try:
        ec2 = boto3.resource('ec2')
        print ec2.create_instances(ImageId=image_id_ubuntu,
                                   MinCount=1,
                                   MaxCount=1,
                                   InstanceType='t2.micro',
                                   KeyName='ServerKey',
                                   SecurityGroupIds=['sg-c16eb5bb'],
                                   SubnetId='subnet-1c435544',
                                   )
    except:
        print "Unable to connect to AWS"


@task
def aws_status():
    ec2 = boto3.resource('ec2')
    for instance in ec2.instances.filter():
        print "Instance {} is in State {}. IP: {}".format(instance.id, instance.state['Name'],
                                                          instance.public_ip_address)


@task
def aws_terminate(id='ALL'):
    ec2 = boto3.resource('ec2')

    instance_ids = []

    if id == 'ALL':
        for instance in ec2.instances.filter():
            instance_ids.append(instance.id)
    else:
        instance_ids.append(id)

    ec2.instances.filter(InstanceIds=instance_ids).terminate()


if __name__ == '__main__':
    aws_status()
    aws_terminate('ALL')
    aws_status()
