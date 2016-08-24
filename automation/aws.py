import boto3
from inspect import stack
from time import sleep


class AWSPlatform:
    def __init__(self, platform_id, avaliabilty_zone='us-east-1a', image_id="ami-2051294a",
                 instance_type="t2.micro", key_name="ServerKey", network_cidr="10.0.0.0/24"):
        """
        Object to manage aws platform resources
        :param platform_id: Sting containiong an id to use when creating reources
        :param image_id: String containing the image ID to use. The default is RHEL7
        :param instance_type: String containg the type of aws instance. Default is t2.micro
        :param key_name: String containing the ssh key to use for the instance
        :return:
        """

        self.platform_id = platform_id

        # Lists to hold the ids of resources that have been created
        self.security_group = None
        self.instances = list()
        self.vpc = None
        self.subnet = None

        # E2C Stuff
        self.availability_zone = avaliabilty_zone
        self.image_id = image_id
        self.instance_type = instance_type
        self.key_name = key_name
        self.network_cidr = network_cidr

        # The EC2 resource
        try:
            self.ec2 = boto3.resource('ec2')
            self.client = boto3.client('ec2')
        except Exception, e:
            self.log("Unable to create the rerource EC2")
            self.log(str(e))
            self.ec2 = None

    @staticmethod
    def log(message="", log_type="DEBUG"):
        """
        Log any messages - not sure how I am going to log so just keep it all here for now
        :param log_type: The type of message - DEBUG, WARNING, INFO
        :param message:
        :return:
        """
        function = stack()[1][3]
        print ("{0} {1} {2}".format(log_type, function, message))

    def create_vpc(self):
        """
        Create an AWS virtual private cloud
        :return: True of False depending on success
        """
        try:
            self.vpc = self.ec2.create_vpc(CidrBlock=self.network_cidr)
            while self.vpc.state != "available":
                self.log("The VPC is {0}".format(self.vpc.state))
                sleep(1)
                self.vpc.reload()
            self.vpc.create_tags(Tags=[{"Key": "Name", "Value": "{}_vpc_{}".format(self.platform_id, self.vpc.vpc_id)}])
            return True
        except Exception, e:
            self.log("Unable to create the resource VPC")
            self.log(str(e))
            return False

    def create_subnet(self):
        """
        Create a subnet in the VPC
        :return: True of False depending on success
        """
        # Ensure that there is already a vpc
        if self.vpc is None or self.vpc.state != "available":
            self.log("Unable to create a subnet as no VPC has been created")
            return False

        try:
            # create
            self.subnet = self.ec2.create_subnet(AvailabilityZone=self.availability_zone,
                                                 CidrBlock=self.network_cidr,
                                                 VpcId=self.vpc.vpc_id)
            # Wait till ready
            while self.subnet.state != "available":
                self.log("The subnet is {0}".format(self.subnet.state))
                sleep(1)
                self.subnet.reload()

            # tag
            self.subnet.create_tags(Tags=[
                {
                    "Key": "Name",
                    "Value": "{}_subnet_{}".format(self.platform_id, self.vpc.vpc_id)
                }
            ])

            # Update public IPs
            self.client.modify_subnet_attribute(SubnetId=self.subnet.subnet_id,
                                                MapPublicIpOnLaunch={
                                                    'Value': True
                                                })

            self.subnet.reload()
            self.log("Subnet '{0}' created in VPC '{1}'".format(self.subnet.subnet_id, self.vpc.vpc_id))
            print self.subnet.map_public_ip_on_launch
            #
            return True
        except Exception, e:
            self.log("Unable to create a subnet")
            self.log(str(e))
            return False

    def create_security_group(self):
        """
        Create an AWS security group and add the firewall rules
        :return:
        """
        try:
            self.security_group = self.ec2.create_security_group(
                    GroupName="{0}-security_group".format(self.platform_id),
                    Description="Security for {0}".format(self.platform_id),
                    VpcId=self.vpc.vpc_id)

            # Add the ports
            security_group_rules = [
                {
                    "UserIdGroupPairs": [
                        {
                            "GroupId": self.security_group.group_id,
                        }
                    ],
                    "IpProtocol": 'tcp',
                    "FromPort": 22,
                    "ToPort": 22,
                    "IpRanges": [
                        {
                            "CidrIp": "0.0.0.0/0"
                        }
                    ]
                }
            ]
            self.security_group.authorize_ingress(IpPermissions=security_group_rules)
            return True

        except Exception, e:
            self.log("Upable to create the security group")
            self.log(str(e))
            return False

    def launch_instances(self, max_count=1, min_count=1):
        """
        Launch an instance using the values defined in this object
        :param max_count: maximum number of these instances to launch
        :param min_count: miniumum number of these instances to launch
        :return:
        """
        instances = self.ec2.create_instances(ImageId=self.image_id,
                                              MinCount=min_count,
                                              MaxCount=max_count,
                                              InstanceType=self.instance_type,
                                              KeyName=self.key_name,
                                              SecurityGroupIds=[self.security_group.group_id],
                                              SubnetId=self.subnet.subnet_id,
                                              )

        # Wait for all instances to launch
        booted_instances = {}
        while not len(booted_instances) == len(instances):
            for instance in instances:
                instance.reload()
                self.log("{} is in state {}".format(instance.instance_id, instance.state['Name']))
                if instance.state['Name'] == 'running':
                    booted_instances['instance.instance_id'] = instance.state["Name"]
            sleep(2)

        # Tag and append to the instances list
        for instance in instances:
            self.ec2.Tag(instance.instance_id, "Name", "{0}_instance_{1}"
                         .format(self.platform_id, instance.instance_id))
            self.instances.append(instance.instance_id)

    def destroy(self):
        """
        Delete everything to do with this object in AWS
        :return: True on success & False on failure
        """
        # Terminate instances
        # self.ec2.instances.filter(InstanceIds=self.instances).terminate()

        # Delete the subnet
        self.subnet.delete()

        # Delete the VPC
        self.vpc.delete()


if __name__ == '__main__':
    platform = AWSPlatform(platform_id="testing")
    platform.create_vpc()
    platform.create_subnet()
    platform.create_security_group()
    platform.launch_instances()
    #platform.destroy()
