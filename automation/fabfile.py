from awsplatform import *
from chef import *
from fabric.api import task
from chefsupermarket import *
from shutil import rmtree

log = logging.getLogger()
log.setLevel(logging.DEBUG)  # create console handler and set level to info
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
handler.setFormatter(logFormatter)
log.addHandler(handler)

# create error file handler and set level to error
#handler = logging.FileHandler(os.path.join(output_dir, "error.log"), "w", encoding=None, delay="true")
#handler.setLevel(logging.ERROR)
#formatter = logging.Formatter("%(levelname)s - %(message)s")
#handler.setFormatter(formatter)
#logger.addHandler(handler)

@task
def kube_start(platform_id=None):
    """
    Create an AWS platform and install kubernetes
    :param platform_id:
    :return:
    """
    if not platform_id:
        print "Please provide an ID string for the platform"
        return

    # Download the cookbooks
    cookbooks_path = "cookbooks"
    supermarket = ChefSupermarket()
    supermarket.download("kubernetes", "latest", cookbooks_path)
    supermarket.download("docker", "1.0.12", cookbooks_path)
    supermarket.download("build-essential", "2.2.3", cookbooks_path)
    supermarket.download("selinux", "0.9.0", cookbooks_path)
    supermarket.download("compat_resource", "latest", cookbooks_path)

    # tar the cookbooks
    chef_solo_tar = "chef-solo.tar.gz"
    with tarfile.open(chef_solo_tar, "w:gz") as tar:
        tar.add(cookbooks_path)

    # Remove the cookbooks
    rmtree(cookbooks_path)

    # upload the tar to a S3 bucket
    bucket = Bucket(platform_id)
    chef_solo_url = bucket.upload(chef_solo_tar)

    # delete the tar file
    os.remove(chef_solo_tar)

    # Start AWS
    kube_platform = AWSPlatform(platform_id=platform_id)
    kube_platform.create_vpc()
    kube_platform.create_internet_gateway()
    kube_platform.create_subnet()
    kube_platform.create_security_group()
    kube_platform.launch_instances()

    # Install Chef on the first instance
    host = kube_platform.get_status()[0]["ip"]
    chef_config =  {
              "cookbook_path": "/var/chef/cookbooks",
              "solo": True,
              "umask": "0022"
    }
    chef = RemoteChefClient(host=host, cookbook_url=chef_solo_url, chef_config_data=chef_config )
    chef.install()
    chef.run("kubernetes::master")

    # Delete the S3 bucket
    bucket.delete()

    # print the result
    print kube_status(platform_id)


@task
def kube_status(platform_id=None):
    """
    Print the current status of the platform
    :param platform_id:
    :return:
    """
    if not platform_id:
        print "Please provide an ID string for the platform"
        return

    kube_platform = AWSPlatform(platform_id=platform_id)
    kube_platform.populate()
    status = kube_platform.get_status()
    if len(status) < 1:
        print "You have no instances running"
    else:
        print status



@task
def kube_terminate(platform_id=None):
    """
    destroy a playform
    :param platform_id:
    :return:
    """
    if not platform_id:
        print "Please provide an ID string for the platform"
        return

    kube_platform = AWSPlatform(platform_id=platform_id)
    kube_platform.populate()
    kube_platform.destroy()
