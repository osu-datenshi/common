import time
import requests
import json

try:
	from pymysql.err import ProgrammingError
except ImportError:
	from MySQLdb._exceptions import ProgrammingError

from common import generalUtils
# from common.constants import gameModes, mods
from common.constants import privileges
from common.log import logUtils as log
from common.ripple import userUtils
# from common.ripple import passwordUtils, scoreUtils
from objects import glob

try:
	from discord_webhook import DiscordWebhook, DiscordEmbed
except ImportError:
	pass

tier = ('unranked', 'pending', 'qualified', 'loved', 'ranked')
tierIcons = {-1: '😦', 0: '💔', 2: '⏫', 3: '☑️', 4: '✅', 5: '❤️'}

def __daten_import_call__(variableList):
	def editSet(mapsetID, status, rankUserID):
		"""
		I know this is significantly slower, and I do understand why I do it.
		"""
		mapIDs = [r['beatmap_id'] for r in glob.db.fetchAll('SELECT beatmap_id FROM beatmaps WHERE beatmapset_id = %s', (mapsetID,))]
		if not mapIDs:
			return None
		if isinstance(status, dict):
			# assign status by map ID
			reverseMap = {}
			for mapID, mapStatus in status.items():
				if mapStatus not in reverseMap:
					reverseMap[mapStatus] = []
				reverseMap[mapStatus].append(mapID)
			for mapStatus, mapIDs in reverseMap.items():
				editMap(mapIDs, mapStatus, rankUserID)
			pass
		elif isinstance(status, str):
			# batch set by set ID
			directEditMap(mapIDs, status, rankUserID)
		else:
			return None
		pass

	def editMap(mapID, status, rankUserID):
		directEditMap([mapID], status, rankUserID)

	def directEditMap(mapList, status, rankUserID):
		"""
		PLEASE CONSIDER THIS AS INTERNAL FUNCTION
		"""
		if 'ranked' == status:
			freezeStatus = 1
			rankTypeID   = 2
		elif 'approved' == status:
			freezeStatus = 1
			rankTypeID   = 3
		elif 'loved' == status:
			freezeStatus = 1
			rankTypeID   = 5
		elif 'qualified' == status:
			freezeStatus = 1
			rankTypeID   = 4
		elif 'unranked' == status:
			# tbh, this also can lock out for a map being unable to have a leaderboard too.
			freezeStatus = 1
			rankTypeID   = 0
		elif 'removed' == status:
			# cYsmix - Tear Rain by jonathanlfj judged by Charles445 voted for 40points
			# This is something unacceptable by the community itself. Please stop.
			# Go to local doctor, and ask what's wrong with you for what you did
			# in 7 years ago. Please consult yourself about how wrong are you.
			freezeStatus = 1
			rankTypeID   = -1
		elif 'reset' == status:
			# reset doesn't mean to rank it anyway.
			freezeStatus = 0
			rankTypeID   = 0
		else:
			return None
		glob.db.execute("UPDATE beatmaps SET ranked = {}, ranked_status_freezed = {}, rankedby = {} WHERE beatmap_id in ({})".format(
			rankTypeID, freezeStatus, rankUserID,
			','.join(['%s'] * len(mapList))),
			[*(mapList if mapList else [0])]
		)
	
	variableList['editSet'] = editSet
	variableList['editMap'] = editMap
	pass

__daten_import_call__(globals())
del __daten_import_call__

def announceMap(idTuple, status, ranker=None, banchoCallback=None, autorankFlag=False):
	"""
	Announce the map both in discord (if applicable) and #announce
	"""
	if idTuple[0] == 'b':
		mapID    = idTuple[1]
		mapsetID = None
	elif idTuple[0] == 's':
		mapID    = None
		mapsetID = idTuple[1]
	
	if mapID is None:
		beatmapData = glob.db.fetch("SELECT beatmapset_id, artist, title, ranked, rankedby FROM beatmaps WHERE beatmapset_id = {} LIMIT 1".format(mapsetID))
	else:
		beatmapData = glob.db.fetch("SELECT beatmapset_id, beatmap_id, artist, title, difficulty_name, ranked, rankedby FROM beatmaps WHERE beatmap_id = {} LIMIT 1".format(mapID))
	
	announceMapRaw(beatmapData, status, ranker=ranker, autoFlag=autorankFlag, banchoCallback=banchoCallback)

def announceMapRaw(mapData, status, ranker=None, autoFlag=False, banchoCallback=None):
	supportBancho  = callable(banchoCallback) # 'BOT_NAME' in dir(glob) is not a must
	supportDiscord = 'DiscordWebhook' in globals() and 'discord' in glob.conf.config and 'ranked-map' in glob.conf.config['discord']
	rankerSet = ranker
	if autoFlag:
		status = f"auto-{status}"
		# apparently there's a case autorank happens to non-cached map.
		ranker = mapData.get('rankedby','Auto Ranker')
	userID = None
	if 'rankedby' in mapData:
		if mapData['rankedby'].isdigit():
			ranker = userUtils.getUsername(mapData['rankedby'])
			userID = mapData['rankedby']
		else:
			userID = 1
	pass
	if rankerSet:
		ranker = rankerSet
			
	if 'difficulty_name' in mapData:
		banchoMsg  = "[https://osu.ppy.sh/b/{} {} - {} [{}]] has been {}!".format(mapData['beatmap_id'],mapData['artist'],mapData['title'],mapData['difficulty_name'],status)
		discordMsg = "{} - {} [{}] has been {}".format(mapData['artist'],mapData['title'],mapData['difficulty_name'], status)
	else:
		banchoMsg  = "[https://osu.ppy.sh/s/{} {} - {}] has been {}!".format(mapData['beatmapset_id'],mapData['artist'],mapData['title'],status)
		discordMsg = "{} - {} has been {}".format(mapData['artist'],mapData['title'], status)
	if supportBancho:
		banchoCallback(banchoMsg)
	if supportDiscord:
		modeIcons = [
			'<:modeosu:800724455579713536>',
			'<:modetaiko:800724456070447196>',
			'<:modefruits:800724454980190228>',
			'<:modemania:800724455126335538>'
		]
		webhook = DiscordWebhook(url=glob.conf.config["discord"]["ranked-map"])
		embed = DiscordEmbed()
		# I KNOW THIS IS REDUNDANT BUT I HAD TO DO IT
		bmSData = dict((bmData['beatmap_id'], bmData) for bmData in glob.db.fetchAll('select beatmap_id, artist, title, difficulty_name, mode, ranked from beatmaps where beatmapset_id = %s', (mapData['beatmapset_id'],)))
		if 'difficulty_name' in mapData:
			bmData = bmSData[mapData['beatmap_id']]
			embed.set_title("{3}{4} {0} - {1} [{2}]".format(
				bmData['artist'], bmData['title'], bmData['difficulty_name'],
				modeIcons[bmData['mode']], tierIcons[bmData['ranked']],
			))
			embed.set_url('https://osu.datenshi.pw/b/{}'.format(mapData['beatmap_id']))
			embed.set_description('Map is {1}\n[Download Link](https://osu.datenshi.pw/d/{0})'.format(mapData["beatmapset_id"], status))
			embed.set_color(0xff0000)
		else:
			def safeReplace(text):
				outText = text
				for c in '`':
					outText = outText.replace(c, '')
				for c in '[]()*_~|<:>':
					outText = outText.replace(c, f"\\{c}")
				return outText
			
			modeData = [
				[
					"{1} [{0}]({2})".format(
						safeReplace(bmData['difficulty_name']),
						tierIcons[bmData['ranked']],
						"https://osu.datenshi.pw/b/{}".format(bmData['beatmap_id'])
					) for bmData in bmSData.values() if bmData['mode'] == mode
				] for mode in range(4)
			]
			fbmData = list(bmSData.values())[0]
			sameIcon = len(set([m['ranked'] for m in bmSData.values()])) <= 1
			sameMode = len([m for m in modeData if m]) <= 1
			embed.set_title("{2}{3} {0} - {1}".format(
				mapData['artist'], mapData['title'],
				modeIcons[fbmData['mode']] if sameMode else '',
				tierIcons[fbmData['ranked']] if sameIcon else '',
			))
			for mode in range(4):
				if not modeData[mode]:
					continue
				embed.add_embed_field(
					name='Difficulties' if sameMode else "{} {}".format(
						modeIcons[mode],
						['Standard', 'Taiko', 'Catch The Beat', 'osu!mania'][mode]
					),
					value="\n".join(modeData[mode]),
					inline=False
				)
			embed.set_url('https://osu.datenshi.pw/s/{}'.format(mapData['beatmapset_id']))
			embed.set_description('[Download Link](https://osu.datenshi.pw/d/{0})'.format(mapData["beatmapset_id"]))
			embed.set_color(0xff8000)
		embed.set_thumbnail(url='https://b.ppy.sh/thumb/{}.jpg'.format(str(mapData["beatmapset_id"])))
		userID = None
		if userID:
			embed.set_author(name='{}'.format(ranker), url='https://osu.datenshi.pw/u/{}'.format(str(userID)), icon_url='https://a.datenshi.pw/{}'.format(str(userID)))
		else:
			embed.set_author(name='{}'.format(ranker), url=None, icon_url=None)
		embed.set_footer(text='This map was {} from in-game'.format(status))
		webhook.add_embed(embed)
		webhook.execute()
	
