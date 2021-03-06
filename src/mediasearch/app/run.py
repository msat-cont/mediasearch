#!/usr/bin/env python
#
# Mediasearch
#

MONGODB_SERVER_HOST = 'localhost'
MONGODB_SERVER_PORT = 27017

import os, sys, datetime, json, logging
import atexit
from collections import namedtuple
try:
    from flask import Flask
    from flask import request, Blueprint
except:
    logging.error('Flask framework is not installed')
    os._exit(1)
try:
    from pymongo import MongoClient
except:
    logging.error('MongoDB support is not installed')
    os._exit(1)
from mediasearch.utils.dbs import mongo_dbs
from mediasearch.utils.sync import synchronizer, sync_clean
from mediasearch.plugin.connect import mediasearch_plugin

app = Flask(__name__)

def setup_mediasearch(dbname, lockfile):
    mongo_dbs.set_dbname(dbname)
    DbHolder = namedtuple('DbHolder', 'db')
    mongo_dbs.set_db(DbHolder(db=MongoClient(MONGODB_SERVER_HOST, MONGODB_SERVER_PORT)[mongo_dbs.get_dbname()]))

    synchronizer.prepare(lockfile)
    atexit.register(sync_clean)

    app.register_blueprint(mediasearch_plugin)

@app.errorhandler(404)
def page_not_found(error):
    request_url = request.url
    if not request_url:
        request_url = ''
    try:
        request_url = str(request_url)
    except:
        request_url = request_url.encode('utf8', 'ignore')

    logging.warning('page not found: ' + request_url)

    return (json.dumps({'_message': 'page not found'}), 404, {'Content-Type': 'application/json'})

def run_flask(dbname, host='localhost', port=9020, lockfile='', debug=False):
    setup_mediasearch(dbname, lockfile)
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    run_flask('mediasearch', host='localhost', port=9020, lockfile='', debug=True)

