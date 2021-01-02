import time
import requests
import json

try:
    from pymysql.err import ProgrammingError
except ImportError:
    from MySQLdb._exceptions import ProgrammingError

import objects.beatmap
from common import generalUtils
# from common.constants import gameModes, mods
from common.constants import privileges
from common.log import logUtils as log
# from common.ripple import passwordUtils, scoreUtils
from objects import glob

tier = ('unranked', 'pending', 'qualified', 'loved', 'ranked')

def __daten_import_call__(variableList):
    def editSet(mapsetID, status, rankUserID):
        """
        I know this is significantly slower, and I do understand why I do it.
        """
        mapIDs = [r['beatmap_id'] for r glob.db.fetchAll('SELECT beatmap_id FROM beatmaps WHERE beatmapset_id = %s', (mapsetID,))]
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
        elif 'loved' == status:
            freezeStatus = 2
            rankTypeID   = 5
        elif 'unranked' == status:
            # tbh, this also can lock out for a map being unable to have a leaderboard too.
            freezeStatus = 0
            rankTypeID   = 0
        elif 'reset' == status:
            freezeStatus = 0
            rankTypeID   = 2
        else:
            return None
    	glob.db.execute("UPDATE beatmaps SET ranked = {}, ranked_status_freezed = {}, rankedby = {} WHERE beatmap_id in ({})".format(\
          rankTypeID, freezeStatus, userID,          \
          ','.join(str(mapID) for mapID in mapList)) \
        )
    
    variableList['editSet'] = editSet
    variableList['editMap'] = editMap
    pass

__daten_import_call__(globals())
del __daten_import_call__

def announceMap(idTuple, status, banchoCallback=None, discordCallback=None):
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
        beatmapData = glob.db.fetch("SELECT beatmapset_id, song_name, ranked FROM beatmaps WHERE beatmapset_id = {} LIMIT 1".format(mapsetID))
    else:
        beatmapData = glob.db.fetch("SELECT beatmapset_id, song_name, ranked FROM beatmaps WHERE beatmap_id = {} LIMIT 1".format(mapID))
    
    supportBancho  = 'BOT_NAME' in dir(glob) and callable(banchoCallback)
    supportDiscord = 'discord' in glob.conf.config and 'ranked-map' in glob.conf.config['discord'] and callable(discordCallback)
    if isSet:
        banchoMsg  = "[https://osu.ppy.sh/s/{} {}] has been {}!".format(mapsetID,beatmapData['song_name'],status)
        discordMsg = "{} has been {}".format(beatmapData["song_name"], status)
    else:
        banchoMsg  = "[https://osu.ppy.sh/b/{} {}] has been partially-{}!".format(mapID,beatmapData['song_name'],status)
		discordMsg = "{} has been {}".format(beatmapData["song_name"], status)
    if supportBancho:
        banchoCallback(banchoMsg)
    if supportDiscord:
        discordCallback(discordMsg, idTuple)
