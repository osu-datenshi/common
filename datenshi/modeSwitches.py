import time, requests, json

from collections import namedtuple

from common import generalUtils
from common.constants import gameModes, mods, personalBestScores, privileges, features
from common.log import logUtils as log
from common.ripple import passwordUtils, scoreUtils
from objects import glob

def __wrapper__():
    g = globals()
    h = {}
    tbl_mode   = namedtuple('tbl_mode', 'std relax alt')
    h['stats'] = tbl_mode('users_stats', 'rx_stats', 'alternative_stats')
    # I wish this is fixed
    h['score'] = tbl_mode('scores', 'scores_relax', 'scores_alternative')
    
    for k,v in h.items():
        g[k] = v
    del g['__wrapper__']
__wrapper__()

del namedtuple
