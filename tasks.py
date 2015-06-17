from app import celery
from compiler import Compiler

@celery.task
def bar(testing_url, production_url):
    print 'Compiling'

    compiler = Compiler('./test/', testing_url, production_url)

    compiler.compile()

    return True
