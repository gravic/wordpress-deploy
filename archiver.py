import os
import tarfile
from datetime import datetime

class Archiver(object):
    def __init__(self, site_slug, input_dir, output_dir):
        self.site = site_slug
        self.input_dir = input_dir
        self.output_dir = os.path.abspath(output_dir)

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def archive(self):
        timestamp = str(datetime.now()).split('.')[0].replace(' ', '_')
        archive_name = '{0}_{1}.tar.bz2'.format(self.site, timestamp)
        archive_path = os.path.join(self.output_dir, archive_name)

        tar = tarfile.open(archive_path, 'w:bz2')
        tar.add(self.input_dir, arcname='')
        tar.close()
