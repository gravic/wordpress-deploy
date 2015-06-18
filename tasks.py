import os
from app import celery
from compiler import Compiler
from archiver import Archiver

@celery.task
def deploy(slug, testing_url, production_url):
    build_dir = os.path.join('./dist/build/', slug)
    archive_dir = os.path.join('./dist/archive/', slug)

    compiler = Compiler(build_dir, testing_url, production_url)

    compiler.compile()

    archiver = Archiver(slug, build_dir, archive_dir)

    archiver.archive()

    return True
