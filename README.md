wordpress-deploy
================

This project was designed as an internal tool to build out WordPress sites to flat files for use in production. While it is currently geared towards and configured for WordPress installations, it should work for compiling any dynamically served content to static HTML.

# Setup

1. Install the dependencies: `pip install -r requirements.txt`
2. Clone the example settings file with `cp settings.py.dist settings.py`, and then customize to your liking.
3. Create the database with `python -m db.init`.
4. Start the Celery workers: `./bin/start_workers`.
5. Run the application: `python app.py`
