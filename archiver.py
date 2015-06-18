import tarfile
from datetime import datetime

class Archiver(object):
    def __init__(self, site_slug, input_dir):
        self.site = site_slug
        self.input_dir = input_dir

    def archive(self):
        timestamp = str(datetime.now()).split('.')[0].replace(' ', '_')
        archive_name = '{0}_{1}'.format(self.site, timestamp)
        archive_path = archive_name

        tar = tarfile.open(archive_name, 'w:bz2')
        tar.add(self.input_dir)
        tar.close()
