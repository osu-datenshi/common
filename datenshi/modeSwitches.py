import time, requests, json

from collections import namedtuple

from common import generalUtils
from common.constants import gameModes, mods, personalBestScores, privileges, features
from common.log import logUtils as log
from common.ripple import passwordUtils, scoreUtils
from objects import glob

def __wrapper__():
    h = {}
    tbl_mode   = namedtuple('tbl_mode', 'std relax alt')
    h['stats'] = tbl_mode('users_stats', 'rx_stats', 'alternative_stats')
    h['score'] = tbl_mode('scores', 'scores_relax', 'scores_alternative')
    h['beatmap_pc'] = tbl_mode('users_beatmap_playcount', 'rx_beatmap_playcount', 'users_beatmap_playcount')
    h['leaderboard'] = tbl_mode('leaderboard', 'leaderboard_relax', 'leaderboard_alt')
    
    for k,v in h.items():
        globals()[k] = v
    del globals()['__wrapper__']
__wrapper__()

del namedtuple
