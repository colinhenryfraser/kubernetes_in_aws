from fabric.api import env, run
from fabric.contrib.files import append
from time import sleep
import os


def _retry(f, retry_limit=10, delay=10):
    """
    Decorator that will re-try the decorated function in the event of an exception
    :param retry_limit: Number of retries
    :param delay: delay in seconds between attempts
    :return:
    """

    def decorator_retry(*args, **kwargs):
        attempts = 1
        while attempts <= retry_limit:
            try:
                return f(*args, **kwargs)
            except:
                print "Function {0}() failed so retrying - attempt {1} of {2}" \
                    .format(f.__name__, attempts, retry_limit)
            attempts += 1
            sleep(delay)

    return decorator_retry


class RemoteChefClient:
    def __init__(self, host, user='ec2-user', password=None, ssh_key='~/.ssh/aws.pem', databag=None, cookbook_url=None,
                 chef_config_data={}):
        """
        Run chef on a remote host via Fabric commands
        :param host: String - the host to run commands on
        :param user: String - ssh user name
        :param password: String - password (in None, it will use the ssh key)
        :param ssh_key: String - location of the ssh key
        :param databag: Dict - the databag to use
        :param cookbook_url: String - URL containing the cookbooks for chef-solo
        :return:
        """

        # Assign host access values from params
        self.host = host
        self.user = user
        self.password = password
        self.ssh_key = ssh_key

        # Chef cookbooks and databags
        self.databag = databag
        self.cookbook_url = cookbook_url

        # Chef stuff
        self.chef_config_data = chef_config_data
        self.chef_config_file = "/etc/chef/client.rb"
        self.chef_files_path = "/var/chef"
        self.data_bag_path = "{}/data_bags".format(self.chef_files_path)

        # Fabric settings
        env.host_string = self.host
        env.key_filename = self.ssh_key
        env.user = self.user
        env.password = self.password
        env.keepalive = 30

    @_retry
    def install(self):
        """
        Install Chef client on the host
        :return: True or False - depending upon success
        """
        # Install chef
        run("sudo yum -y install https://packages.chef.io/stable/el/7/chef-12.13.37-1.el7.x86_64.rpm")

        # Add config Config
        self._config()

    @_retry
    def run(self, cookbook):
        """
        Run cookbooks on the remote host
        :param cookbook_url: String - URL for the chef-solo cookbook tar ball
        :param cookbook: String - The name of the cookbook to run. This should be in the tar ball
        :return:
        """
        run("sudo chef-solo -c '{}' -o '{}' -r '{}'".format(self.chef_config_file,
                                                      cookbook,
                                                      self.cookbook_url))

    def _config(self):
        """
        Perform the required configuration for chef
        :return:
        """

        # Add a new config file (delete any old one)
        run("sudo mkdir -p {0}".format(os.path.dirname(self.chef_config_file)))
        run("sudo rm -f {0}".format(self.chef_config_file))
        chef_config_str = ""
        for key,val in self.chef_config_data.iteritems():
            chef_config_str += "{0}\t'{1}'\n".format(key, val)
        append(filename=self.chef_config_file, text=chef_config_str, use_sudo=True)