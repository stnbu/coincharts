# -*- mode: python; coding: utf-8 -*-
"""A small amount of justified magic: with this module,

>>> import logger
>>> logger.debug('yay!')
"""

import logging

_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)

for level in 'debug', 'info', 'warning', 'error', 'exception', 'critical', 'addHandler':
    globals()[level] = getattr(_logger, level)

