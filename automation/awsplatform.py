import boto3
from time import sleep
import logging

class Bucket:
    def __init__(self, platform_id):
        """
        object to interact with an S3 bucket
        :param platform_id: ID used to lable the bucket
        :return:
        """
        self.log = logging.getLogger()
        
        self.platform_id = "colinhenryfraser_{}".format(platform_id)
        self.objects = []

        try:
            self.resource = boto3.resource('s3')
            self.client = boto3.client('s3')
        except Exception, e:
            self.log.debug("Unable to create the S3 resource and client")
            self.log.debug(str(e))
            self.resource = None

        try:
            self.bucket = self.resource.create_bucket(ACL='public-read', Bucket=self.platform_id)
            self.log.debug("Created bucket {}".format(self.bucket.name))
        except Exception, e:
            print "Unable to create the S3 bucket"
            self.log.debug(str(e))
            self.resource = None

    def upload(self, src_file):
        """
        Upload an object to the bucket
        :param src_file: The object to upload
        :return:
        """
        dst_file = src_file.split('/')[-1]

        try:
            self.bucket.upload_file(src_file, dst_file)
            self.objects.append({"Key": dst_file})
            return self.client.generate_presigned_url('get_object',
                                                      Params = {'Bucket': self.platform_id, 'Key': dst_file},
                                                      ExpiresIn = 600)
        except Exception, e:
            self.log.debug("Unable to upload {} to {} in bucket {}".format(src_file, dst_file, self.bucket.name))
            self.log.debug(str(e))

    def delete(self):
        """
        delete the bucket
        :return:
        """
        try:
            self.log.debug("Deleting objects '{}' from '{}'".format(self.objects, self.bucket.name))
            self.bucket.delete_objects(Delete={"Objects": self.objects})
            self.bucket.delete()
            self.log.info("Deleted bucket {}".format(self.bucket.name))
        except Exception, e:
            self.log.debug("Unable to delete bucket")
            self.log.debug(str(e))


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
        self.log = logging.getLogger()

        self.platform_id = platform_id

        # Lists to hold the ids of resources that have been created
        self.security_group = None
        self.instances = list()
        self.vpc = None
        self.subnet = None
        self.internet_gateway = None

        # E2C Stuff
        self.availability_zone = avaliabilty_zone
        self.image_id = image_id
        self.instance_type = instance_type
        self.key_name = key_name
        self.network_cidr = network_cidr

        # The EC2 resource and client
        try:
            self.resource = boto3.resource('ec2')
            self.client = boto3.client('ec2')
        except Exception, e:
            self.log.debug("Unable to create the resource EC2")
            self.log.debug(str(e))
            self.resource = None

    def create_vpc(self):
        """
        Create an AWS virtual private cloud
        :return: True of False depending on success
        """
        try:
            self.vpc = self.resource.create_vpc(CidrBlock=self.network_cidr)
            while self.vpc.state != "available":
                self.log.debug("The VPC is {0}".format(self.vpc.state))
                sleep(1)
                self.vpc.reload()
            self.vpc.create_tags(Tags=[{"Key": "Name", "Value": "{}_vpc_{}".format(self.platform_id, self.vpc.vpc_id)}])
            self.log.debug("VPC Created: '{0}'".format(self.vpc.vpc_id))
        except Exception, e:
            self.log.debug("Unable to create the resource VPC")
            self.log.debug(str(e))
            return False

        # wait for the vpc to become available
        while self.vpc.state != "available":
            self.log.debug("The VPC is {0}".format(self.subnet.state))
            sleep(2)
            self.vpc.reload()

    def create_internet_gateway(self):
        """
        Create a gateway for use with the VCN
        :return: True of False depending on success
        """
        # Ensure that there is already a vpc
        if self.vpc is None or self.vpc.state != "available":
            self.log.debug("Unable to create a gateway as no VPC has been created")
            return False

        try:
            self.internet_gateway = self.resource.create_internet_gateway()
            self.log.debug("Gateway Created: '{0}'".format(self.internet_gateway.internet_gateway_id))
        except Exception, e:
            self.log.debug("Unable to create a Internet gateway")
            self.log.debug(str(e))
            return False

        # attach the gateway to the VPC
        try:
            self.vpc.attach_internet_gateway(InternetGatewayId=self.internet_gateway.internet_gateway_id)
            self.log.debug("Attached Internet gateway '{0}' to VPC '{1}"
                     .format(self.internet_gateway.internet_gateway_id, self.vpc.vpc_id))
        except Exception, e:
            self.log.debug("Unable to attach Internet gateway '{0}' to VPC '{1}"
                     .format(self.internet_gateway.internet_gateway_id, self.vpc.vpc_id))
            self.log.debug(str(e))
            return False

        # Update the route table
        try:
            for route_table in self.vpc.route_tables.all():
                route_table.create_route(DestinationCidrBlock="0.0.0.0/0",
                                         GatewayId=self.internet_gateway.internet_gateway_id)
                self.log.debug("Added route to route table '{0}'".format(route_table.route_table_id))
        except Exception, e:
            self.log.debug("Unable to update route table")
            self.log.debug(str(e))
            return False

    def create_subnet(self):
        """
        Create a subnet in the VPC
        :return: True of False depending on success
        """
        # Ensure that there is already a vpc
        if self.vpc is None or self.vpc.state != "available":
            self.log.debug("Unable to create a subnet as no VPC has been created")
            return False

        try:
            # create
            self.subnet = self.resource.create_subnet(AvailabilityZone=self.availability_zone,
                                                      CidrBlock=self.network_cidr,
                                                      VpcId=self.vpc.vpc_id)
            # Wait till ready
            while self.subnet.state != "available":
                self.log.debug("The subnet is {0}".format(self.subnet.state))
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
            self.log.debug("Subnet '{0}' created in VPC '{1}'".format(self.subnet.subnet_id, self.vpc.vpc_id))
            return True
        except Exception, e:
            self.log.debug("Unable to create a subnet in VPC '{0}'".format(self.vpc.vpc_id))
            self.log.debug(str(e))
            return False

    def create_security_group(self):
        """
        Create an AWS security group and add the firewall rules
        :return:
        """
        try:
            self.security_group = self.resource.create_security_group(
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
            self.log.debug("Security Group '{0}' created"
                     .format(self.security_group.group_id))
            return True

        except Exception, e:
            self.log.debug("Upable to create the security group")
            self.log.debug(str(e))
            return False

    def launch_instances(self, max_count=1, min_count=1):
        """
        Launch an instance using the values defined in this object
        :param max_count: maximum number of these instances to launch
        :param min_count: miniumum number of these instances to launch
        :return:
        """
        instances = self.resource.create_instances(ImageId=self.image_id,
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
                self.log.debug("{} is in state {}".format(instance.instance_id, instance.state['Name']))
                if instance.state['Name'] == 'running':
                    booted_instances['instance.instance_id'] = instance.state["Name"]
            sleep(2)

        # Tag and append to the instances list
        for instance in instances:
            instance.create_tags(
                    Tags=[
                        {
                            'Key': 'Name',
                            'Value': '{0}_instance_{1}'.format(self.platform_id, instance.instance_id)
                        }
                    ]
            )
            self.instances.append(instance)

        for instance in instances:
            instance.reload()
            self.log.debug("Instance '{0}' created with IP '{1}'".format(instance.instance_id,
                                                                         instance.public_ip_address))

    def populate(self):
        """
        Populate the object from resources currently in AWS by using the platform_id
        :return:
        """
        # populate instances
        instances = self.resource.instances.filter(
                Filters=[
                    {
                        'Name': 'tag-value',
                        'Values': [
                            '{0}_instance_*'.format(self.platform_id),
                        ]
                    },
                ]
        )
        for instance in instances:
            self.instances.append(instance)
            self.log.info("instance '{0}' has been added".format(instance.instance_id))
            break

        # populate VPC
        vpcs = self.resource.vpcs.filter(
                Filters=[
                    {
                        'Name': 'tag-value',
                        'Values': [
                            '{0}_vpc_*'.format(self.platform_id),
                        ]
                    },
                ],
        )
        for vpc in vpcs:
            self.log.debug("Adding VPC '{0}'".format(vpc.vpc_id))
            self.vpc = vpc
            self.vpc.reload()
            break

        # populate subnets from the VPC
        try:
            for subnet in self.vpc.subnets.all():
                self.log.debug("Populating subnet {}".format(subnet.subnet_id))
                self.subnet = subnet
                break
        except Exception, e:
            self.log.debug("Unable to populate subnets")
            self.log.debug(str(e))

        # populate security groups from the VPC
        try:
            for security_group in self.vpc.security_groups.all():
                self.log.debug("Populating Security Group {}".format(security_group.group_id))
                self.security_group = security_group
                break
        except Exception, e:
            self.log.debug("Unable to populate security groups")
            self.log.debug(str(e))

        # populate the internet gateway
        try:
            for internet_gateway in self.vpc.internet_gateways.all():
                self.log.debug("Populating Internet Gateway {}".format(internet_gateway.internet_gateway_id))
                self.internet_gateway = internet_gateway
                break
        except Exception, e:
            self.log.debug("Unable to populate internet gateway")
            self.log.debug(str(e))

    def destroy(self):
        """
        Delete everything to do with this object in AWS
        :return: True on success & False on failure
        """
        # Terminate instances
        try:
            for instance in self.instances:
                instance.terminate()
                self.log.debug("The instance '{0}' is being deleted".format(instance.instance_id))
        except Exception, e:
            self.log.debug("Unable to delete some or all of the instances in '{0}'".format(self.platform_id))
            self.log.debug(str(e))

        # wait for the instances to stop
        stopped_instances = {}
        while not len(stopped_instances) == len(self.instances):
            for instance in self.instances:
                instance.reload()
                self.log.debug("Instance '{0}' is in state '{1}'".format(instance.instance_id, instance.state['Name']))
                if instance.state['Name'] == 'terminated':
                    stopped_instances['instance.instance_id'] = instance.state["Name"]
            sleep(5)

        # Delete security group
        try:
            self.security_group.delete()
            self.log.debug("The Security group '{0}' has been deleted".format(self.security_group.group_id))
        except Exception, e:
            self.log.debug("Unable to delete the Security Group")
            self.log.debug(str(e))

        # Delete the subnet
        try:
            self.subnet.delete()
            self.log.debug("The Subnet '{0}' has been deleted".format(self.subnet.subnet_id))
        except Exception, e:
            self.log.debug("Unable to delete the Subnet")
            self.log.debug(str(e))

        # delete all routes tables and route associations
        try:
            for route_table in self.vpc.route_tables.all():
                try:
                    for association in route_table.associations.all():
                        association.delete()
                        self.log.debug("Removed route table association {0}".format(association.route_table_association_id))
                except Exception, e:
                    self.log.debug("Unable to delete the route")
                    self.log.debug(str(e))
                route_table.delete()
                self.log.debug("The Route table {} has been delete".format(route_table.route_table_id))
        except Exception, e:
            self.log.debug("Unable to delete the Route Table")
            self.log.debug(str(e))

        # Delete the internet gateway
        try:
            self.vpc.detach_internet_gateway(InternetGatewayId=self.internet_gateway.internet_gateway_id)
            self.internet_gateway.delete()
            self.log.debug("The Internet Gateway '{0}' has been deleted".format(self.internet_gateway.internet_gateway_id))
        except Exception, e:
            self.log.debug("Unable to delete the Internet Gateway")
            self.log.debug(str(e))

        # Delete the VPC
        try:
            self.vpc.delete()
            self.log.debug("The VPV '{0}'has been deleted".format(self.vpc.vpc_id))
        except Exception, e:
            self.log.debug("Unable to delete the VPC")
            self.log.debug(str(e))

    def get_status(self):
        status_data = []
        for instance in self.instances:
            instance_data = {"id": instance.instance_id, "ip": instance.public_ip_address, "status": instance.state}
            status_data.append(instance_data)

        return status_data


if __name__ == '__main__':
    platform = AWSPlatform(platform_id="testing")
    # platform.populate()
    platform.create_vpc()
    platform.create_internet_gateway()
    platform.create_subnet()
    platform.create_security_group()
    platform.launch_instances()
    platform.destroy()
