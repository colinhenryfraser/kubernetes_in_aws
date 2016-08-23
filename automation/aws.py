import boto3
from inspect import stack


class AWSPlatform():
    def __int__(self, platform_id,  avaliabilty_zone='us-east-1a', image_id="ami-2051294a",
                instance_type="t2.micro", key_name="ServerKey", network_cidr="10.0.0.0/24"):
        """
        Object to manage aws platform resources
        :param id: Sting containiong an id to use when creating reources
        :param image_id: String containing the image ID to use. The default is RHEL7
        :param instance_type: String containg the type of aws instance. Default is t2.micro
        :param key_name: String containing the ssh key to use for the instance
        :return:
        """

        self.platform_id = platform_id

        # Lists to hold the ids of resources that have been created
        self.security_groups = list()
        self.instances = list()
        self.vpc = None
        self.subnet = None

        # E2C Stuff
        self.avaliabilty_zone = avaliabilty_zone
        self.image_id = image_id
        self.instance_type = instance_type
        self.key_name = key_name
        self.network_cidr = network_cidr

        # The EC2 resource
        try:
            self.ec2 = boto3.resource('ec2')
        except Exception, e:
            self.log("Unable to create the rerource EC2")
            self.log(e)
            self.ec2 = None

    def log(self, message="", type="DEBUG"):
        """
        Log any messages
        :param type: The type of message - DEBUG, WARNING, INFO
        :param message:
        :return:
        """
        function = stack()[1][3]
        print ("{0} {1} {2}".format(type, function, message))

    def create_vpc(self):
        """
        Create an AWS virtual private cloud
        :return: True of False depending on success
        """
        try:
            self.vpc = self.vpcs.append(self.ec2.Vpc(self.platform_id))
            return True
        except Exception, e:
            self.log("Unable to create the rerource EC2")
            self.log(e)
            return False

    def create_subnet(self):
        """
        Create a subent in the VPC
        :return: True of False depending on success
        """
        if self.subnet is None:
            self.log("Unable to create a subnet as no VPC has been created")
            return False

        try:
            self.subnet = self.vpc.create_subnet(AvailabilityZone=self.avaliabilty_zone, CidrBlock=self.network_cidr)
            return True
        except Exception,e:
            self.log("Unable to create a subnet")
            self.log(e)
            return False

    def create_security_group(self):
        """
        Create an AWS security group
        :return:
        """
        pass

    def launch_instances(self, max_count=1, min_count=1):
        """
        Launch an instance using the values defined in this object
        :param max_count: maximum number of these instances to launch
        :param min_count: miniumum number of these instances to launch
        :return:
        """
        self.ec2.create_instances(ImageId=self.image_id,
                                  MinCount=min_count,
                                  MaxCount=max_count,
                                  InstanceType=self.instance_type,
                                  KeyName=self.key_name,
                                  SecurityGroupIds=self.security_groups,
                                  SubnetId=self.subnet_id,
                                  )
