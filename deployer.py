import subprocess

class Deployer(object):
    def __init__(self, production_url, target_dir):
        self.production_url = production_url
        self.target_dir = target_dir

    def deploy(self, archive):
        command = 'cat {archive} | ssh {production} "cd {directory}; tar xvjf -"'.format(
            archive=archive,
            production=self.production_url,
            directory=self.target_dir
        )
        print command
        result = subprocess.call(command, shell=True)
