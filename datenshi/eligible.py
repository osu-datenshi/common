import time
import requests
import json

try:
    from pymysql.err import ProgrammingError
except ImportError:
    from MySQLdb._exceptions import ProgrammingError

from common import generalUtils
from common.constants import gameModes, mods
from common.constants import privileges
from common.constants import features
from common.datenshi import modeSwitches
from common.log import logUtils as log
from common.ripple import userUtils
from objects import glob
from discord_webhook import DiscordWebhook, DiscordEmbed

# Dev note: this is meant to be a toggle done for features.
def submitScore(userID):
	mtFlag = glob.db.fetch('select value_int from system_settings where name = "game_maintenance"')
	mtMode = mtFlag is not None and mtFlag['value_int']
    return mtMode and userUtils.isInPrivilegeGroup(userID, "Developer")

def scoreV2(userID):
    if not features.RANKING_SCOREV2:
        return False
    return userUtils.isInPrivilegeGroup(userID, "Chat Moderators")
