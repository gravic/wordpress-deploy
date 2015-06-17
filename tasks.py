from app import celery

@celery.task
def compile():
    print 'Compiling'
