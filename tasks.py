from app import celery

@celery.task
def bar(testing_url, production_url):
    print 'Compiling'

    compiler = Compiler('', testing_url, production_url)

    compiler.compile()

    return True
