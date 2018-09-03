# -*- mode: python; coding: utf-8 -*-
"""re-export `modules.*` and make models (and ORM) usable outside of web framework.

So, if you have django "app" `foo` installed as a package, from anywhere you should be able to

>>> record = foo.db.SomeTable(**kwargs)
>>> record.save()

et cetera.
"""

import django
from .settings import *
from django.conf import settings

settings.configure(DATABASES=DATABASES)
django.setup()

from .models import *
