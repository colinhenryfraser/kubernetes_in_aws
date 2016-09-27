import requests
import tarfile
import os


class ChefSupermarket():
    def __init__(self, supermarket_url="https://supermarket.chef.io"):
        """
        Object to interact with a Chef supermarket
        :param supermarket_url: the URL of the chef supermarket
        :return:
        """
        self.supermarket_url = supermarket_url

    def download(self, cookbook_name, version='latest', save_path="."):
        """
        Download and unpack a cookbook from the supermarket
        :param cookbook_name: the name for the cookbook to download
        :param save_path: The path of where to save the file
        :return:
        """
        download_url = "{}/cookbooks/{}/download".format(self.supermarket_url, cookbook_name)
        downloaded_tar_file = "{}.tgz".format(cookbook_name)

        #
        # Download the compressed cookobook
        r = requests.get(download_url, stream=True)
        with open(downloaded_tar_file, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()

        #
        # Create the save_path if it doesn't exist
        if not os.path.isdir(save_path):
            os.mkdir(save_path)

        #
        # un-pack and store in the requested location
        tar = tarfile.open(downloaded_tar_file)
        tar.extractall(save_path)
        tar.close()

        #
        # Delete the downloaded file
        os.remove(downloaded_tar_file)

        return "{}/{}".format(save_path, cookbook_name)
