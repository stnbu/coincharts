# -*- mode: python; coding: utf-8 -*-
"""re-export `models.*` and make models (and ORM) usable outside of web framework.

>>> import db
>>> record = db.SomeTable(**kwargs)
>>> record.save()

et cetera.
"""

import os
import importlib
import django

from coincharts import logger

# There is a bit of hackery here. Read comments starting with 'HACK'

try:
    # HACK -- we require that DJANGO_SETTINGS_MODULE be set to the the name
    # of the site's settings' module, e.g. `mysite.settings`
    django_settings_module_name = os.environ['DJANGO_SETTINGS_MODULE']
except KeyError:
    raise ImportError("""
The "DJANGO_SETTINGS_MODULE" environment must be set to the name of your site's setting's module. For example:

    export DJANGO_SETTINGS_MODULE="mysite.settings"
""")

# HACK -- this is magic for "from mysite.settings import *"
globals().update(importlib.import_module(
    django_settings_module_name).__dict__)

from django.conf import settings
from django.db import connections
import atexit

# HACK -- note that the rhs "DATABASES" here comes from mysite.settings, above
settings.configure(DATABASES=DATABASES)
django.setup()

from coincharts.models import *

def cleanup():
    logger.info('closing all django database connections for this process')
    connections.close_all()

atexit.register(cleanup)
