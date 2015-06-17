from app import celery
from compiler import Compiler

@celery.task
def compile_site(slug, testing_url, production_url):
    compiler = Compiler('./test/', testing_url, production_url)

    compiler.compile()

    return True
