import os
from app import celery
from archiver import Archiver
from compiler import Compiler
from deployer import Deployer
import settings as SETTINGS

@celery.task
def deploy(slug, testing_url, production_url):
    build_dir = os.path.join('./dist/build/', slug)
    archive_dir = os.path.join('./dist/archive/', slug)

    compiler = Compiler(build_dir, testing_url, production_url)
    compiler.compile()

    archiver = Archiver(slug, build_dir, archive_dir)
    archive = archiver.archive()

    deployer = Deployer(SETTINGS.PRODUCTION_SERVER, SETTINGS.SSH_KEY, SETTINGS.PRODUCTION_DIR)
    deployer.deploy(archive)

    return True

@celery.task
def restore(slug, archive):
    archive_dir = os.path.join('./dist/archive/', slug)

    deployer = Deployer(SETTINGS.PRODUCTION_SERVER, SETTINGS.SSH_KEY, archive_dir, SETTINGS.PRODUCTION_DIR)
    deployer.deploy(archive)
