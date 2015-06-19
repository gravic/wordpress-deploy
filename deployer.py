import os
import subprocess

class Deployer(object):
    def __init__(self, production_url, ssh_key, source_dir, target_dir):
        self.production_url = production_url
        self.ssh_key = ssh_key
        self.source_dir = source_dir
        self.target_dir = target_dir

    def deploy(self, archive):
        command = 'cat {archive_path} | ssh -i ~/.ssh/{ssh_key} {production} "cd {directory}; tar xvjf -"'.format(
            archive_path=os.path.abspath(os.path.join(self.source_dir, archive)),
            ssh_key=self.ssh_key,
            production=self.production_url,
            directory=self.target_dir
        )
        print command
        result = subprocess.call(command, shell=True)
