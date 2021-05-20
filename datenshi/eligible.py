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
	if not mtMode:
		return True
	return mtMode and userUtils.isInPrivilegeGroup(userID, "Developer")

def scoreV2(userID):
	if not features.RANKING_SCOREV2:
		return False
	return userUtils.isInPrivilegeGroup(userID, "Chat Moderators")

def tryLogin(userID):
	mtFlag = glob.db.fetch('select value_int from bancho_settings where name = "dev_maintenance"')
	if mtFlag is not None and mtFlag['value_int']:
		return userUtils.isInPrivilegeGroup(userID, "Developer")
	return True

def tryLoadBeatmap(userID):
	mtFlag = glob.db.fetch('select value_int from bancho_settings where name = "beatmap_addition"')
	if mtFlag is None:
		return True
	if mtFlag['value_int'] == 2:
		return False
	elif mtFlag['value_int'] == 1:
		if userID == 0:
			return False
		return userUtils.isInPrivilegeGroup(userID, "Developer")
	return True

def tryAddStat(userID):
	mtFlag = glob.db.fetch('select value_int from bancho_settings where name = "beatmap_addition"')
	if mtFlag is not None and mtFlag['value_int']:
		return False
	return True
