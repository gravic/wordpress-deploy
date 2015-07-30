import os
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
