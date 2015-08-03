import os
import subprocess
from app import celery
from archiver import Archiver
from compiler import Compiler
from deployer import Deployer
import settings as SETTINGS

@celery.task
def deploy(slug, testing_url, production_url, theme_url, production_server, production_dir):
    build_dir = os.path.join(SETTINGS.BUILD_DIR, slug)
    archive_dir = os.path.join(SETTINGS.ARCHIVE_DIR, slug)

    compiler = Compiler(build_dir, testing_url, production_url, theme_url)
    compiler.compile()

    archiver = Archiver(slug, build_dir, archive_dir)
    archive = archiver.archive()

    deployer = Deployer(production_server, SETTINGS.SSH_KEY, archive_dir, production_dir)
    deployer.deploy(archive)

    return True

@celery.task
def restore(slug, archive, production_server, production_dir):
    archive_dir = os.path.join(SETTINGS.ARCHIVE_DIR, slug)

    deployer = Deployer(production_server, SETTINGS.SSH_KEY, archive_dir, production_dir)
    deployer.deploy(archive)

@celery.task
def rsync(slug, production_server, production_dir):
    source_dir = os.path.join('/var/www/html/', slug, 'wp-content/uploads')
    upload_dir = os.path.join(production_dir, 'wp-content/uploads')

    command = 'cd {source_dir}; rsync -rt ./* -r \'ssh -i {ssh_key}\' {production}:{upload_dir}'.format(
        source_dir=source_dir,
        ssh_key=SETTINGS.SSH_KEY,
        production=production_server,
        upload_dir=upload_dir
    )

    result = subprocess.check_call(command, shell=True)
