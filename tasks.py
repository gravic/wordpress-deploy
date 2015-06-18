from app import celery
from compiler import Compiler
from archiver import Archiver

@celery.task
def deploy(slug, testing_url, production_url):
    compiler = Compiler('./test/', testing_url, production_url)

    compiler.compile()

    archiver = Archiver(slug, './test/')

    archiver.archive()

    return True
