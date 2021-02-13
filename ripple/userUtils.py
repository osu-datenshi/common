import time
import requests
import json

try:
    from pymysql.err import ProgrammingError
except ImportError:
    from MySQLdb._exceptions import ProgrammingError

from common import generalUtils
from common.constants import gameModes, mods
from common.constants import personalBestScores
from common.constants import privileges
from common.constants import features
from common.datenshi import modeSwitches
from common.log import logUtils as log
from common.ripple import passwordUtils, scoreUtils
from objects import glob
from discord_webhook import DiscordWebhook, DiscordEmbed

STUPIDEST_ABBREVIATION_LIST = ['rx']

def _genWarnConfusion(f):
    def g(*args,**kwargs):
        log.warning(f"{f.__name__} is called.")
        f(*args,**kwargs)
    return g

def logUserLog(log, fileMd5, userID, gameMode, scoreid):
	"""
	Add some log by user!
	:param log: Log Message
	:param fileMd5: MD5File ID of map
	:param userID: I thinks this easy to know it
	:param gameMode: GameMode
	:param scoreid: ScoreID or Play ID
	"""
	glob.db.execute(f"INSERT INTO users_logs (user, log, time, game_mode, beatmap_md5, scoreid) VALUES ({userID}, '{log}', {int(time.time())}, {gameMode}, '{fileMd5}', {scoreid})")
	return True

def getBeatmapTime(beatmapID):
    p = 0
    r = requests.get("https://s.troke.id/api/b/{}".format(beatmapID)).text
    if r != "null\n":
        p = json.loads(r)['TotalLength']

    return p

if "userSettings":
    # User Settings System
    # This allows the user and the dev to configure the game settings even more further without force adding columns like dumb
    # - Rei_Fan49
    def getUserSetting(userID, key):
        query = glob.db.fetch('select int_value as i, str_value as s from user_settings where user_id = {} and name = "{}"'.format(userID, key))
        result = None
        if query is None:
            pass
        elif query['s'] is not None:
            result = query['s']
        elif query['i'] is not None:
            result = query['i']
        return result

    def setUserSetting(userID, key, value):
        query = glob.db.fetch('select int_value as i, str_value as s from user_settings where user_id = {} and name = %s'.format(userID), [key])
        input = [None, None]
        if isinstance(value,int):
            input[0] = value
        else:
            input[1] = str(value)
        if query is None:
            glob.db.execute('insert into user_settings (user_id, name, int_value, str_value) values (%s, %s, %s, %s)', [userID, key, *input])
        else:
            glob.db.execute('update user_settings set int_value = %s, str_value = %s where user_id = {} and name = %s'.format(userID), [*input, key])

    def resetUserSetting(userID, key):
        glob.db.execute('delete from user_settings where user_id = {} and name = %s'.format(userID), [key])

    def getOrderedUserSetting(userID, key, prefix_order):
        orders = list(prefix_order) + ['global']
        result = None
        while result is None and orders:
            prefix, orders = orders[0], orders[1:]
            result = getUserSetting(userID, f"{prefix}:{key}")
        return result

if "board":
    def PPBoard(userID, relax):
        result = getOrderedUserSetting(userID, 'board', [('relax' if relax else 'standard')])
        if result is not None:
            return result == 1
        result = glob.db.fetch(
            "SELECT ppboard FROM {table}_stats WHERE id = {userid}".format(table=STUPIDEST_ABBREVIATION_LIST[0] if relax else 'users', userid=userID))
        return result['ppboard']

    def BoardMode(userID, relax):
        result = getOrderedUserSetting(userID, 'board', [('relax' if relax else 'standard')])
        if result is not None:
            return result
        return 0

    def setScoreBoard(userID, relax):
        setUserSetting(userID, "{}:board".format(('relax' if relax else 'standard')), 0)
        glob.db.execute(
            "UPDATE {table}_stats SET ppboard = 0 WHERE id = {userid}".format(table=STUPIDEST_ABBREVIATION_LIST[0] if relax else 'users', userid=userID))

    def setPPBoard(userID, relax):
        setUserSetting(userID, "{}:board".format(('relax' if relax else 'standard')), 1)
        glob.db.execute("UPDATE {table}_stats SET ppboard = 1 WHERE id = {userid}".format(table=STUPIDEST_ABBREVIATION_LIST[0] if relax else 'users', userid=userID))

    def InvisibleBoard(userID):
        """
        Board visiblity
        Not everyone wants to see leaderboard for a reason.
        This feature allows you to hide specific scope of the leaderboard.
        - Rei_Fan49
        """
        result = getOrderedUserSetting(userID, 'board_visibility', [])
        if result is not None:
            return result
        return 0

    def setInvisibleBoard(userID, relax, b):
        setUserSetting(userID, "{}:board_visibility".format('global'), b)
        # setUserSetting(userID, "{}:board_visibility".format(('relax' if relax else 'standard')), b)
        # setUserSetting(userID, "{}:board".format(('relax' if relax else 'standard')), 2)

if "personal settings":
    def ScoreOverrideType(userID, relax):
        """
        Score Override Type
        This allows the user to specify what kind of score override they should use.
        Personally PP override is dumb for me, so I had to create this feature.
        - Rei_Fan49
        """
        result = getOrderedUserSetting(userID, 'personal_best_overtake', [('relax' if relax else 'standard')])
        if result is not None:
            return result
        return glob.conf.extra["lets"]["submit"]["score-overwrite"]

    def setScoreOverrideType(userID, relax, t):
        k = "{}:personal_best_overtake".format(('relax' if relax else 'standard'))
        if t not in personalBestScores.VALID_SCORE_TYPES:
            resetUserSetting(userID, k)
        else:
            setUserSetting(userID, k, t)

    def PPAbuseFlag(userID, relax):
        """
        TODO: Another separate rank, but im too lazy to customize the redis.
        If this ever implemented, just calculate those qualified maps into pp_abuse_flag
        Idk if you should do this kind of Calculation
        -> Check beatmap_md5, is it on qualified or not, if yes go to this route or else normal route
        - Rei_Fan49
        """
        result = getOrderedUserSetting(userID, 'pp_abuser_rank', [('relax' if relax else 'standard')])
        if result is not None:
            return bool(result)
        return False

    def setPPAbuseFlag(userID, key, b):
        setUserSetting(userID, "{}:pp_abuser_rank".format(key), b)

    def PPScoreInformation(userID, relax):
        """
        PP Score Information
        Allows you to subscribe to Yohane to receive amount of PPs obtained in a map, for every clears.
        - Rei_Fan49
        """
        result = getOrderedUserSetting(userID, 'pp_gain_information', [('relax' if False else 'standard')])
        if result is not None:
            return bool(result)
        return False

    def setPPScoreInformation(userID, relax, t):
        # k = "{}:pp_gain_information".format(('relax' if False else 'standard'))
        k = "global:pp_gain_information"
        setUserSetting(userID, k, t)

def noPPLimit(userID, relax):
    result = glob.db.fetch(
        "SELECT unrestricted_pp FROM {table}_stats WHERE id = {userid}".format(table=STUPIDEST_ABBREVIATION_LIST[0] if relax else 'users',
                                                                            userid=userID))
    return result['unrestricted_pp']

def whitelistUserPPLimit(userID, relax, value=1):
    glob.db.execute("UPDATE {table}_stats SET unrestricted_pp = %s WHERE id = {userid}".format(table=STUPIDEST_ABBREVIATION_LIST[0] if relax else 'users',
                                                                                           userid=userID),[value])
def _genIncTime(n,i):
    t = modeSwitches.stats[i]
    def inc(userID,gameMode=0,length=0):
        modeForDB = gameModes.getGameModeForDB(gameMode)
        result = glob.db.fetch("SELECT playtime_{gm} as playtime FROM {t} WHERE id = %s".format(t=t,gm=modeForDB),
                               [userID])
        if result is not None:
            glob.db.execute("UPDATE {t} SET playtime_{gm} = %s WHERE id = %s".format(t=t,gm=modeForDB),
                            [(int(result['playtime']) + int(length)), userID])
        else:
            print("Something went wrong...")
    globals()[n] = inc
_genIncTime('incrementPlaytime',0)
_genIncTime('incrementPlaytimeRelax',1)
if features.RANKING_SCOREV2:
    _genIncTime('incrementPlaytimeAlt',2)

def _genObtainStat(n,i,mm):
    t = modeSwitches.stats[i]
    def stat(userID, gameMode):
        """
        Get all user stats relative to `gameMode`

        :param userID:
        :param gameMode: game mode number
        :return: dictionary with result
        """
        modeForDB = gameModes.getGameModeForDB(gameMode)
        
        if gameMode in mm:
            return mm[gameMode](userID,gameMode)
        
        # Get stats
        stats = glob.db.fetch("""SELECT
                            ranked_score_{gm} AS rankedScore,
                            avg_accuracy_{gm} AS accuracy,
                            playcount_{gm} AS playcount,
                            total_score_{gm} AS totalScore,
                            pp_{gm} AS pp
                            FROM {t} WHERE id = %s LIMIT 1""".format(t=t,gm=modeForDB), [userID])

        # Get game rank
        stats["gameRank"] = getGameRank(userID, gameMode)
        # Return stats + game rank
        return stats
    globals()[n] = stat
_genObtainStat('getUserStats',0,dict())
_genObtainStat('getUserStatsRelax',1,dict([(3,getUserStats)]))
if features.RANKING_SCOREV2:
    _genObtainStat('getUserStats',2,dict())

def _genMaxCombo(n,i):
    t = modeSwitches.score[i]
    def maxcombo(userID, gameMode):
        """
        Get all user stats relative to `gameMode`
     
        :param userID:
        :param gameMode: game mode number
        :return: dictionary with result
        """
        # Get stats
        if features.MASTER_SCORE_TABLE:
            maxcombo = glob.db.fetch(
                "SELECT max_combo FROM scores_master WHERE userid = %s AND play_mode = %s AND special_mode = {} ORDER BY max_combo DESC LIMIT 1".format(i),
                [userID, gameMode])
        else:
            maxcombo = glob.db.fetch(
                "SELECT max_combo FROM {} WHERE userid = %s AND play_mode = %s ORDER BY max_combo DESC LIMIT 1".format(t),
                [userID, gameMode])

        # Return stats + game rank
        return maxcombo["max_combo"]
    globals()[n] = maxcombo
_genMaxCombo('getMaxCombo', 0)
_genMaxCombo('getMaxComboRelax', 1)
if features.RANKING_SCOREV2:
    _genMaxCombo('getMaxComboAlt', 2)

def getIDSafe(_safeUsername):
    """
    Get user ID from a safe username
    :param _safeUsername: safe username
    :return: None if the user doesn't exist, else user id
    """
    result = glob.db.fetch("SELECT id FROM users WHERE username_safe = %s LIMIT 1", [_safeUsername])
    if result is not None:
        return result["id"]
    return None

def getAll():
    """
    Get all users
    :return: None if the user doesn't exist, else tuple of userID
    """
    result = glob.db.fetchAll("SELECT id FROM users WHERE 1")
    return result

def getID(username):
    """
    Get username's user ID from userID redis cache (if cache hit)
    or from db (and cache it for other requests) if cache miss

    :param username: user
    :return: user id or 0 if user doesn't exist
    """
    # Get userID from redis
    usernameSafe = safeUsername(username)
    userID = glob.redis.get("ripple:userid_cache:{}".format(usernameSafe))

    if userID is None:
        # If it's not in redis, get it from mysql
        userID = getIDSafe(usernameSafe)

        # If it's invalid, return 0
        if userID is None:
            return 0

        # Otherwise, save it in redis and return it
        glob.redis.set("ripple:userid_cache:{}".format(usernameSafe), userID, 3600)  # expires in 1 hour
        return userID

    # Return userid from redis
    return int(userID)

def getUsername(userID):
    """
    Get userID's username

    :param userID: user id
    :return: username or None
    """
    result = glob.db.fetch("SELECT username FROM users WHERE id = %s LIMIT 1", [userID])
    if result is None:
        return None
    return result["username"]

def getSafeUsername(userID):
    """
    Get userID's safe username

    :param userID: user id
    :return: username or None
    """
    result = glob.db.fetch("SELECT username_safe FROM users WHERE id = %s LIMIT 1", [userID])
    if result is None:
        return None
    return result["username_safe"]

def exists(userID):
    """
    Check if given userID exists

    :param userID: user id to check
    :return: True if the user exists, else False
    """
    return True if glob.db.fetch("SELECT id FROM users WHERE id = %s LIMIT 1", [userID]) is not None else False

def checkLogin(userID, password, ip=""):
    """
    Check userID's login with specified password

    :param userID: user id
    :param password: md5 password
    :param ip: request IP (used to check active bancho sessions). Optional.
    :return: True if user id and password combination is valid, else False
    """
    # Check cached bancho session
    banchoSession = False
    if ip != "":
        banchoSession = checkBanchoSession(userID, ip)

    # Return True if there's a bancho session for this user from that ip
    if banchoSession:
        return True

    # Otherwise, check password
    # Get password data
    passwordData = glob.db.fetch("SELECT password_md5, salt, password_version FROM users WHERE id = %s LIMIT 1",
                                 [userID])

    # Make sure the query returned something
    if passwordData is None:
        return False

    # Return valid/invalid based on the password version.
    if passwordData["password_version"] == 2:
        return passwordUtils.checkNewPassword(password, passwordData["password_md5"])
    if passwordData["password_version"] == 1:
        ok = passwordUtils.checkOldPassword(password, passwordData["salt"], passwordData["password_md5"])
        if not ok:
            return False
        newpass = passwordUtils.genBcrypt(password)
        glob.db.execute("UPDATE users SET password_md5=%s, salt='', password_version='2' WHERE id = %s LIMIT 1",
                        [newpass, userID])

def getRequiredScoreForLevel(level):
    """
    Return score required to reach a level

    :param level: level to reach
    :return: required score
    """
    if level <= 100:
        if level >= 2:
            return 5000 / 3 * (4 * (level ** 3) - 3 * (level ** 2) - level) + 1.25 * (1.8 ** (level - 60))
        elif level <= 0 or level == 1:
            return 1  # Should be 0, but we get division by 0 below so set to 1
    elif level >= 101:
        return 26931190829 + 100000000000 * (level - 100)

def getLevel(totalScore):
    """
    Return level from totalScore

    :param totalScore: total score
    :return: level
    """
    level = 1
    while True:
        # if the level is > 8000, it's probably an endless loop. terminate it.
        if level > 8000:
            return level

        # Calculate required score
        reqScore = getRequiredScoreForLevel(level)

        # Check if this is our level
        if totalScore <= reqScore:
            # Our level, return it and break
            return level - 1
        else:
            # Not our level, calculate score for next level
            level += 1

def _genUpdateLevel(n,i):
    def lv(userID, gameMode=0, totalScore=0):
        """
        Update level in DB for userID relative to gameMode

        :param userID: user id
        :param gameMode: game mode number
        :param totalScore: new total score
        :return:
        """
        # Make sure the user exists
        # if not exists(userID):
        #	return

        # Get total score from db if not passed
        mode = scoreUtils.readableGameMode(gameMode)
        if totalScore == 0:
            totalScore = glob.db.fetch(
                "SELECT total_score_{m} as total_score FROM {t} WHERE id = %s LIMIT 1".format(t=modeSwitches.stats[i],m=mode), [userID])
            if totalScore:
                totalScore = totalScore["total_score"]

        # Calculate level from totalScore
        level = getLevel(totalScore)

        # Save new level
        glob.db.execute("UPDATE {t} SET level_{m} = %s WHERE id = %s LIMIT 1".format(t=modeSwitches.stats[i], m=mode), [level, userID])
    globals()[n] = lv
_genUpdateLevel('updateLevel', 0)
_genUpdateLevel('updateLevelRelax', 1)
if features.RANKING_SCOREV2:
    _genUpdateLevel('updateLevelAlt', 2)

def _genCalcAcc(n,i):
    t = modeSwitches.score[i]
    def acc(userID, gameMode):
        """
        Calculate accuracy value for userID relative to gameMode

        :param userID: user id
        :param gameMode: game mode number
        :return: new accuracy
        """
        # Get best accuracy scores
        if features.MASTER_SCORE_TABLE:
            bestAccScores = glob.db.fetchAll(
                f"SELECT accuracy FROM scores_master WHERE userid = %s AND play_mode = %s AND special_mode = {i} AND completed = 3 AND beatmap_md5 in (select beatmap_md5 from beatmaps where ranked in (2,3)) ORDER BY pp DESC LIMIT 500",
                [userID, gameMode])
        else:
            bestAccScores = glob.db.fetchAll(
                f"SELECT accuracy FROM {t} WHERE userid = %s AND play_mode = %s AND completed = 3 AND beatmap_md5 in (select beatmap_md5 from beatmaps where ranked in (2,3)) ORDER BY pp DESC LIMIT 500",
                (userID, gameMode)
            )

        v = 0
        if bestAccScores is not None:
            # Calculate weighted accuracy
            totalAcc = 0
            divideTotal = 0
            k = 0
            for i in bestAccScores:
                add = int((0.95 ** k) * 100)
                totalAcc += i["accuracy"] * add
                divideTotal += add
                k += 1
            # echo "$add - $totalacc - $divideTotal\n"
            if divideTotal != 0:
                v = totalAcc / divideTotal
            else:
                v = 0
        return v
    globals()[n] = acc
_genCalcAcc('calculateAccuracy',0)
_genCalcAcc('calculateAccuracyRelax',1)
if features.RANKING_SCOREV2:
    _genCalcAcc('calculateAccuracyAlt',2)

def _genCalcPP(n,i):
    t = modeSwitches.score[i]
    def pp(userID, gameMode):
        """
        Calculate userID's total PP for gameMode

        :param userID: user id
        :param gameMode: game mode number
        :return: total PP
        """
        if features.MASTER_SCORE_TABLE:
            return sum(round(round(row["pp"]) * 0.95 ** i) for i, row in enumerate(glob.db.fetchAll(
                "SELECT pp FROM scores_master LEFT JOIN(beatmaps) USING(beatmap_md5) "
                f"WHERE userid = %s AND play_mode = %s AND completed = 3 AND ranked >= 2 AND pp > 0 AND special_mode = {i} "
                "ORDER BY pp DESC LIMIT 500",
                (userID, gameMode)
            )))
        else:
            return sum(round(round(row["pp"]) * 0.95 ** i) for i, row in enumerate(glob.db.fetchAll(
                f"SELECT pp FROM {t} LEFT JOIN(beatmaps) USING(beatmap_md5) "
                "WHERE userid = %s AND play_mode = %s AND completed = 3 AND ranked >= 2 AND pp > 0 "
                "ORDER BY pp DESC LIMIT 500",
                (userID, gameMode)
            )))
    globals()[n] = pp
_genCalcPP('calculatePP',0)
_genCalcPP('calculatePPRelax',1)
if features.RANKING_SCOREV2:
    _genCalcPP('calculatePPAlt',2)

def _genUpdateAcc(n,f,i):
    def acc(userID, gameMode):
        """
        Update accuracy value for userID relative to gameMode in DB

        :param userID: user id
        :param gameMode: gameMode number
        :return:
        """
        newAcc = f(userID, gameMode)
        mode = scoreUtils.readableGameMode(gameMode)
        glob.db.execute("UPDATE {t} SET avg_accuracy_{m} = %s WHERE id = %s LIMIT 1".format(t=modeSwitches.stats[i], m=mode),
                        [newAcc, userID])
    globals()[n] = acc
_genUpdateAcc('updateAccuracy',calculateAccuracy,0)
_genUpdateAcc('updateAccuracyRelax',calculateAccuracyRelax,1)
if features.RANKING_SCOREV2:
    _genUpdateAcc('updateAccuracyAlt',calculateAccuracyAlt,2)

def _genUpdatePP(n,f,i):
    def pp(userID, gameMode, iDontKnowRippleFlag=False):
        """
        Update userID's pp with new value

        :param userID: user id
        :param gameMode: game mode number
        """
        glob.db.execute(
            "UPDATE {} SET pp_{}=%s WHERE id = %s LIMIT 1".format(modeSwitches.stats[i], scoreUtils.readableGameMode(gameMode)),
            (
                f(userID, gameMode),
                userID
            )
        )
        if loggingEnabled:
            log.info("Executed query {} with result {}".format(query, result))
    globals()[n] = pp
_genUpdatePP('updatePP',calculatePP,0)
_genUpdatePP('updatePPRelax',calculatePPRelax,1)
if features.RANKING_SCOREV2:
    _genUpdatePP('updateAccuracyAlt',calculatePPAlt,2)

def _genUpdateStat(n,i,lf):
    t_stat  = modeSwitches.stats[i]
    t_score = modeSwitches.score[i]
    def stat(userID, s):
        """
        Update stats (playcount, total score, ranked score, level bla bla)
        with data relative to a score object

        :param userID:
        :param score_: score object
        :param beatmap_: beatmap object. Optional. If not passed, it'll be determined by score_.
        """
        # Make sure the user exists
        if not exists(userID):
            log.warning("User {} doesn't exist.".format(userID))
            return

        # Get gamemode for db
        mode = scoreUtils.readableGameMode(s.gameMode)
        def recalcFlag():
            timeThisPlay = int(time.time())
            if features.MASTER_SCORE_TABLE:
                timeLastPlay = glob.db.fetch('select `time` from scores_master where userid = %s and play_mode = %s and id < %s and time < %s and special_mode = %s',
                    [userID, s.gameMode, s.scoreID, timeThisPlay, i])
            else:
                timeLastPlay = glob.db.fetch('select `time` from {} where userid = %s and play_mode = %s and id < %s and time < %s'.format(t_score),
                    [userID, s.gameMode, s.scoreID, timeThisPlay])
            if timeLastPlay is None:
                return False
            return timeLastPlay['time'] < features.RANKED_SCORE_RECALC and timeThisPlay >= features.RANKED_SCORE_RECALC
        needRecalc = recalcFlag()
        
        if needRecalc:
            glob.db.execute('UPDATE {3} set ranked_score_{2} = (SELECT SUM(score) FROM scores WHERE userid = {0} AND play_mode = {1} AND completed = 3 AND beatmap_md5 in (select beatmap_md5 from beatmaps where ranked in (2,3))) WHERE id = {0}'.format(userID, s.gameMode, mode, t_stat))

        # Update total score, playcount and play time
        if s.playTime is not None:
            realPlayTime = s.playTime
        else:
            realPlayTime = s.fullPlayTime

        glob.db.execute(
            "UPDATE {t} SET total_score_{m}=total_score_{m}+%s, playcount_{m}=playcount_{m}+1, "
            "playtime_{m} = playtime_{m} + %s "
            "WHERE id = %s LIMIT 1".format(m=mode, t=t_stat),
            (s.score, realPlayTime, userID)
        )

        # Calculate new level and update it
        lf[0](userID, s.gameMode)

        # Update level, accuracy and ranked score only if we have passed the song
        if s.passed:
            # Update ranked score
            if not needRecalc:
                glob.db.execute(
                    "UPDATE {t} SET ranked_score_{m}=ranked_score_{m}+%s WHERE id = %s LIMIT 1".format(t=t_stat,m=mode),
                    (s.rankedScoreIncrease, userID)
                )

            # Update accuracy
            lf[1](userID, s.gameMode)

            # Update pp
            lf[2](userID, s.gameMode)
        pass
    globals()[n] = stat
_genUpdateStat('updateStats',0,(updateLevel, updateAccuracy, updatePP))
_genUpdateStat('updateStatsRelax',1,(updateLevelRelax, updateAccuracyRelax, updatePPRelax))
if features.RANKING_SCOREV2:
    _genUpdateStat('updateStatsAlt',2,(updateLevelAlt, updateAccuracyAlt, updatePPAlt))

def _genRefreshStat(n,f):
    def stat(userID, gameMode):
        """
        Update stats (playcount, total score, ranked score, level bla bla)
        with data relative to a score object

        :param userID:
        :param score_: score object
        :param beatmap_: beatmap object. Optional. If not passed, it'll be determined by score_.
        """
        # Make sure the user exists
        if not exists(userID):
            log.warning("User {} doesn't exist.".format(userID))
            return

        # Update pp
        f(userID, gameMode, True)
    globals()[n] = stat
_genRefreshStat('refreshStats', updatePP)
_genRefreshStat('refreshStatsRelax', updatePPRelax)
if features.RANKING_SCOREV2:
    _genRefreshStat('refreshStatsAlt', updatePPAlt)

def _genIncrementPC(n,i):
    t = modeSwitches.beatmap_pc[i]
    def pc(userID, gameMode, beatmapID):
        glob.db.execute(
            f"INSERT INTO {t} (user_id, beatmap_id, game_mode, playcount) "
            "VALUES (%s, %s, %s, 1) ON DUPLICATE KEY UPDATE playcount = playcount + 1",
            (userID, beatmapID, gameMode)
        )
    globals()[n] = pc
_genIncrementPC('incrementUserBeatmapPlaycount',0)
_genIncrementPC('incrementUserBeatmapPlaycountRelax',1)
if features.RANKING_SCOREV2:
    _genIncrementPC('incrementUserBeatmapPlaycountAlt',2)

def updateLatestActivity(userID):
    """
    Update userID's latest activity to current UNIX time

    :param userID: user id
    :return:
    """
    glob.db.execute("UPDATE users SET latest_activity = %s WHERE id = %s LIMIT 1", [int(time.time()), userID])

def _genObtainRankedPt(n,i):
    t = modeSwitches.stats[i]
    def score(userID, gameMode):
        """
        Get userID's ranked score relative to gameMode

        :param userID: user id
        :param gameMode: game mode number
        :return: ranked score
        """
        mode = scoreUtils.readableGameMode(gameMode)
        result = glob.db.fetch("SELECT ranked_score_{} FROM {} WHERE id = %s LIMIT 1".format(mode,t), [userID])
        if result is not None:
            return result["ranked_score_{}".format(mode)]
        else:
            return 0
    globals()[n] = score
_genObtainRankedPt('getRankedScore',0)
_genObtainRankedPt('getRankedScoreRelax',1)
if features.RANKING_SCOREV2:
    _genObtainRankedPt('getRankedScoreAlt',2)

# FIXME: what should I do in here?
@_genWarnConfusion
def getPP(userID, gameMode):
    """
    Get userID's PP relative to gameMode

    :param userID: user id
    :param gameMode: game mode number
    :return: pp
    """

    mode = scoreUtils.readableGameMode(gameMode)
    result = glob.db.fetch("SELECT pp_{} FROM {} WHERE id = %s LIMIT 1".format(mode, modeSwitches.stats[0]), [userID])
    if result is not None:
        return result["pp_{}".format(mode)]
    else:
        return 0

def _genIncrementReplays(n,i):
    def watch(userID, gameMode):
        """
        Increment userID's replays watched by others relative to gameMode

        :param userID: user id
        :param gameMode: game mode number
        :return:
        """
        mode = scoreUtils.readableGameMode(gameMode)
        glob.db.execute(
            "UPDATE users_stats SET replays_watched_{mode}=replays_watched_{mode}+1 WHERE id = %s LIMIT 1".format(
                mode=mode), [userID])
    globals()[n] = watch
_genIncrementReplays('incrementReplaysWatched',0)
_genIncrementReplays('incrementReplaysWatchedRelax',1)
if features.RANKING_SCOREV2:
    _genIncrementReplays('incrementReplaysWatchedAlt',2)

# FIXME: what should I do in here?
@_genWarnConfusion
def getTotalScore(userID, gameMode):
    """
    Get `userID`'s total score relative to `gameMode`

    :param userID: user id
    :param gameMode: game mode number
    :return: total score
    """
    modeForDB = gameModes.getGameModeForDB(gameMode)
    return glob.db.fetch("SELECT total_score_" + modeForDB + " FROM users_stats WHERE id = %s LIMIT 1", [userID])[
        "total_score_" + modeForDB]

# FIXME: what should I do in here?
@_genWarnConfusion
def getAccuracy(userID, gameMode):
    """
    Get `userID`'s average accuracy relative to `gameMode`

    :param userID: user id
    :param gameMode: game mode number
    :return: accuracy
    """
    modeForDB = gameModes.getGameModeForDB(gameMode)
    return glob.db.fetch("SELECT avg_accuracy_" + modeForDB + " FROM users_stats WHERE id = %s LIMIT 1", [userID])[
        "avg_accuracy_" + modeForDB]

def _genGameRank(n,i):
    t = modeSwitches.leaderboard[i]
    def rank(userID, gameMode):
        """
        Get `userID`'s **in-game rank** (eg: #1337) relative to gameMode

        :param userID: user id
        :param gameMode: game mode number
        :return: game rank
        """
        position = glob.redis.zrevrank("ripple:{}:{}".format(t,gameModes.getGameModeForDB(gameMode)), userID)
        if position is None:
            return 0
        else:
            return int(position) + 1
    globals()[n] = rank
_genGameRank('getGameRank',0)
_genGameRank('getGameRankRelax',1)
if features.RANKING_SCOREV2:
    _genGameRank('getGameRankAlt',2)

def _genPlaycount(n,i):
    t = modeSwitches.stats[i]
    def pc(userID, gameMode):
        """
        Get `userID`'s playcount relative to `gameMode`

        :param userID: user id
        :param gameMode: game mode number
        :return: playcount
        """
        modeForDB = gameModes.getGameModeForDB(gameMode)
        return glob.db.fetch(f"SELECT playcount_{modeForDB} FROM {t} WHERE id = %s LIMIT 1", [userID])[
            "playcount_" + modeForDB]
    globals()[n] = pc
_genPlaycount('getPlaycount',0)
_genPlaycount('getPlaycountRelax',1)
if features.RANKING_SCOREV2:
    _genPlaycount('getPlaycountAlt',2)

def _genUpdateHits(n,i):
    t = modeSwitches.stats[i]
    def hits(userID=0, gameMode=gameModes.STD, newHits=0, score=None):
        if score is None and userID == 0:
            raise ValueError("Either score or userID must be provided")
        if score is not None:
            newHits = score.c50 + score.c100 + score.c300
            gameMode = score.gameMode
            userID = score.playerUserID
        glob.db.execute(
            "UPDATE {t} SET total_hits_{gm} = total_hits_{gm} + %s WHERE id = %s LIMIT 1".format(
                t=t,
                gm=gameModes.getGameModeForDB(gameMode)
            ),
            (newHits, userID)
        )
    globals()[n] = hits
_genUpdateHits('updateTotalHits',0)
_genUpdateHits('updateTotalHitsRelax',1)
if features.RANKING_SCOREV2:
    _genUpdateHits('updateTotalHitsAlt',2)

if "account marker":
    def getAqn(userID):
        """
        Check if AQN folder was detected for userID

        :param userID: user
        :return: True if hax, False if legit
        """
        result = glob.db.fetch("SELECT aqn FROM users WHERE id = %s LIMIT 1", [userID])
        if result is not None:
            return True if int(result["aqn"]) == 1 else False
        else:
            return False

    def setAqn(userID, value=1):
        """
        Set AQN folder status for userID

        :param userID: user
        :param value: new aqn value, default = 1
        :return:
        """
        glob.db.fetch("UPDATE users SET aqn = %s WHERE id = %s LIMIT 1", [value, userID])

    def IPLog(userID, ip):
        """
        Log user IP

        :param userID: user id
        :param ip: IP address
        :return:
        """
        glob.db.execute("""INSERT INTO ip_user (userid, ip, occurencies) VALUES (%s, %s, '1')
                            ON DUPLICATE KEY UPDATE occurencies = occurencies + 1""", [userID, ip])

    def checkBanchoSession(userID, ip=""):
        """
        Return True if there is a bancho session for `userID` from `ip`
        If `ip` is an empty string, check if there's a bancho session for that user, from any IP.

        :param userID: user id
        :param ip: ip address. Optional. Default: empty string
        :return: True if there's an active bancho session, else False
        """
        if ip != "":
            return glob.redis.sismember("peppy:sessions:{}".format(userID), ip)
        else:
            return glob.redis.exists("peppy:sessions:{}".format(userID))

    def is2FAEnabled(userID):
        """
        Returns True if 2FA/Google auth 2FA is enable for `userID`

        :userID: user ID
        :return: True if 2fa is enabled, else False
        """
        return glob.db.fetch("SELECT 2fa_totp.userid FROM 2fa_totp WHERE userid = %(userid)s AND enabled = 1 LIMIT 1", {
            "userid": userID
        }) is not None

    def check2FA(userID, ip):
        """
        Returns True if this IP is untrusted.
        Returns always False if 2fa is not enabled on `userID`

        :param userID: user id
        :param ip: IP address
        :return: True if untrusted, False if trusted or 2fa is disabled.
        """
        if not is2FAEnabled(userID):
            return False

        result = glob.db.fetch("SELECT id FROM ip_user WHERE userid = %s AND ip = %s", [userID, ip])
        return True if result is None else False

    def isAllowed(userID):
        """
        Check if userID is not banned or restricted

        :param userID: user id
        :return: True if not banned or restricted, otherwise false.
        """
        result = glob.db.fetch("SELECT privileges FROM users WHERE id = %s LIMIT 1", [userID])
        if result is not None:
            return (result["privileges"] & privileges.USER_NORMAL) and (result["privileges"] & privileges.USER_PUBLIC)
        else:
            return False

    def isRestricted(userID):
        """
        Check if userID is restricted

        :param userID: user id
        :return: True if not restricted, otherwise false.
        """
        result = glob.db.fetch("SELECT privileges FROM users WHERE id = %s LIMIT 1", [userID])
        if result is not None:
            return (result["privileges"] & privileges.USER_NORMAL) and not (result["privileges"] & privileges.USER_PUBLIC)
        else:
            return False

    def isBanned(userID):
        """
        Check if userID is banned

        :param userID: user id
        :return: True if not banned, otherwise false.
        """
        result = glob.db.fetch("SELECT privileges FROM users WHERE id = %s LIMIT 1", [userID])
        if result is not None:
            return not (result["privileges"] & 3 > 0)
        else:
            return True

    def isLocked(userID):
        """
        Check if userID is locked

        :param userID: user id
        :return: True if not locked, otherwise false.
        """
        result = glob.db.fetch("SELECT privileges FROM users WHERE id = %s LIMIT 1", [userID])
        if result is not None:
            return ( \
                (result["privileges"] & privileges.USER_PUBLIC) and \
                (not (result["privileges"] & privileges.USER_NORMAL)) \
            )
        else:
            return True

    def ban(userID):
        """
        Ban userID

        :param userID: user id
        :return:
        """
        # Set user as banned in db
        banDateTime = int(time.time())
        glob.db.execute("UPDATE users SET privileges = privileges & %s, ban_datetime = %s WHERE id = %s LIMIT 1",
                        [~(privileges.USER_NORMAL | privileges.USER_PUBLIC), banDateTime, userID])

        # Notify bancho about the ban
        glob.redis.publish("peppy:ban", userID)

        # Remove the user from global and country leaderboards
        removeFromLeaderboard(userID)

    def unban(userID):
        """
        Unban userID

        :param userID: user id
        :return:
        """
        glob.db.execute("UPDATE users SET privileges = privileges | %s, ban_datetime = 0 WHERE id = %s LIMIT 1",
                        [(privileges.USER_NORMAL | privileges.USER_PUBLIC), userID])
        glob.redis.publish("peppy:ban", userID)

    def restrict(userID):
        """
        Restrict userID

        :param userID: user id
        :return:
        """
        if not isRestricted(userID):
            # Set user as restricted in db
            banDateTime = int(time.time())
            glob.db.execute("UPDATE users SET privileges = privileges & %s, ban_datetime = %s WHERE id = %s LIMIT 1",
                            [~privileges.USER_PUBLIC, banDateTime, userID])

            # Notify bancho about this ban
            glob.redis.publish("peppy:ban", userID)

            # Remove the user from global and country leaderboards
            removeFromLeaderboard(userID)

    def unrestrict(userID):
        """
        Unrestrict userID.
        Same as unban().

        :param userID: user id
        :return:
        """
        unban(userID)

    def appendNotes(userID, notes, addNl=True, trackDate=True):
        """
        Append `notes` to `userID`'s "notes for CM"

        :param userID: user id
        :param notes: text to append
        :param addNl: if True, prepend \n to notes. Default: True.
        :param trackDate: if True, prepend date and hour to the note. Default: True.
        :return:
        """
        if trackDate:
            notes = "[{}] {}".format(generalUtils.getTimestamp(), notes)
        if addNl:
            notes = "\n{}".format(notes)
        glob.db.execute("UPDATE users SET notes=CONCAT(COALESCE(notes, ''),%s) WHERE id = %s LIMIT 1", [notes, userID])

    def getSilenceEnd(userID):
        """
        Get userID's **ABSOLUTE** silence end UNIX time
        Remember to subtract time.time() if you want to get the actual silence time

        :param userID: user id
        :return: UNIX time
        """
        return glob.db.fetch("SELECT silence_end FROM users WHERE id = %s LIMIT 1", [userID])["silence_end"]

    def silence(userID, seconds, silenceReason, author=1):
        """
        Silence someone

        :param userID: user id
        :param seconds: silence length in seconds
        :param silenceReason: silence reason shown on website
        :param author: userID of who silenced the user. Default: 999
        :return:
        """
        # db qurey
        silenceEndTime = int(time.time()) + seconds
        glob.db.execute("UPDATE users SET silence_end = %s, silence_reason = %s WHERE id = %s LIMIT 1",
                        [silenceEndTime, silenceReason, userID])

        # Log
        targetUsername = getUsername(userID)
        # TODO: exists check im drunk rn i need to sleep (stampa piede ubriaco confirmed)
        if seconds > 0:
            log.rap(author,
                    "has silenced {} for {} seconds for the following reason: \"{}\"".format(targetUsername, seconds,
                                                                                             silenceReason), True)
        else:
            log.rap(author, "has removed {}'s silence".format(targetUsername), True)

if "fiend list":
    def getFriendList(userID):
        """
        Get `userID`'s friendlist

        :param userID: user id
        :return: list with friends userIDs. [0] if no friends.
        """
        # Get friends from db
        friends = glob.db.fetchAll("SELECT user2 FROM users_relationships WHERE user1 = %s", [userID])

        if friends is None or len(friends) == 0:
            # We have no friends, return 0 list
            return [0]
        else:
            # Get only friends
            friends = [i["user2"] for i in friends]

            # Return friend IDs
            return friends

    def addFriend(userID, friendID):
        """
        Add `friendID` to `userID`'s friend list

        :param userID: user id
        :param friendID: new friend
        :return:
        """
        # Make sure we aren't adding us to our friends
        if userID == friendID:
            return

        # check user isn't already a friend of ours
        if glob.db.fetch("SELECT id FROM users_relationships WHERE user1 = %s AND user2 = %s LIMIT 1",
                         [userID, friendID]) is not None:
            return

        # Set new value
        glob.db.execute("INSERT INTO users_relationships (user1, user2) VALUES (%s, %s)", [userID, friendID])

    def removeFriend(userID, friendID):
        """
        Remove `friendID` from `userID`'s friend list

        :param userID: user id
        :param friendID: old friend
        :return:
        """
        # Delete user relationship. We don't need to check if the relationship was there, because who gives a shit,
        # if they were not friends and they don't want to be anymore, be it. ¯\_(ツ)_/¯
        # TODO: LIMIT 1
        glob.db.execute("DELETE FROM users_relationships WHERE user1 = %s AND user2 = %s", [userID, friendID])

if "country data":
    def getCountry(userID):
        """
        Get `userID`'s country **(two letters)**.

        :param userID: user id
        :return: country code (two letters)
        """
        return glob.db.fetch("SELECT country FROM users_stats WHERE id = %s LIMIT 1", [userID])["country"]

    def setCountry(userID, country):
        """
        Set userID's country

        :param userID: user id
        :param country: country letters
        :return:
        """
        glob.db.execute("UPDATE users_stats SET country = %s WHERE id = %s LIMIT 1", [country, userID])

    def logIP(userID, ip):
        """
        User IP log
        USED FOR MULTIACCOUNT DETECTION

        :param userID: user id
        :param ip: IP address
        :return:
        """
        glob.db.execute("""INSERT INTO ip_user (userid, ip, occurencies) VALUES (%s, %s, 1)
                            ON DUPLICATE KEY UPDATE occurencies = occurencies + 1""", [userID, ip])

    def saveBanchoSession(userID, ip):
        """
        Save userid and ip of this token in redis
        Used to cache logins on LETS requests

        :param userID: user ID
        :param ip: IP address
        :return:
        """
        glob.redis.sadd("peppy:sessions:{}".format(userID), ip)

    def deleteBanchoSessions(userID, ip):
        """
        Delete this bancho session from redis

        :param userID: user id
        :param ip: IP address
        :return:
        """
        glob.redis.srem("peppy:sessions:{}".format(userID), ip)

if "privileges":
    def getPrivileges(userID):
        """
        Return `userID`'s privileges

        :param userID: user id
        :return: privileges number
        """
        result = glob.db.fetch("SELECT privileges FROM users WHERE id = %s LIMIT 1", [userID])
        if result is not None:
            return result["privileges"]
        else:
            return 0

    def setPrivileges(userID, priv):
        """
        Set userID's privileges in db

        :param userID: user id
        :param priv: privileges number
        :return:
        """
        glob.db.execute("UPDATE users SET privileges = %s WHERE id = %s LIMIT 1", [priv, userID])

    def getGroupPrivileges(groupName):
        """
        Returns the privileges number of a group, by its name

        :param groupName: name of the group
        :return: privilege integer or `None` if the group doesn't exist
        """
        groupPrivileges = glob.db.fetch("SELECT privileges FROM privileges_groups WHERE name = %s LIMIT 1", [groupName])
        if groupPrivileges is None:
            return None
        return groupPrivileges["privileges"]

    def isInPrivilegeGroup(userID, groupName):
        """
        Check if `userID` is in a privilege group.
        Donor privilege is ignored while checking for groups.

        :param userID: user id
        :param groupName: privilege group name
        :return: True if `userID` is in `groupName`, else False
        """
        groupPrivileges = getGroupPrivileges(groupName)
        if groupPrivileges is None:
            return False
        try:
            userToken = glob.tokens.getTokenFromUserID(userID)
        except AttributeError:
            # LETS compatibility
            userToken = None

        if userToken is not None:
            userPrivileges = userToken.privileges
        else:
            userPrivileges = getPrivileges(userID)
        
        normUser, normGroup = [(priv & ~privileges.USER_DONOR) for priv in [userPrivileges, groupPrivileges]]
        return normUser & normGroup == normGroup

    def isInAnyPrivilegeGroup(userID, groups):
        """
        Checks if a user is in at least one of the specified groups

        :param userID: id of the user
        :param groups: groups list or tuple
        :return: `True` if `userID` is in at least one of the specified groups, otherwise `False`
        """
        userPrivileges = getPrivileges(userID)
        return any(
            userPrivileges & x == x
            for x in (
                getGroupPrivileges(y) for y in groups
            ) if x is not None
        )

if "hw approval":
    def logHardware(userID, hashes, activation=False):
        """
        Hardware log
        USED FOR MULTIACCOUNT DETECTION


        :param userID: user id
        :param hashes:	Peppy's botnet (client data) structure (new line = "|", already split)
                        [0] osu! version
                        [1] plain mac addressed, separated by "."
                        [2] mac addresses hash set
                        [3] unique ID
                        [4] disk ID
        :param activation: if True, set this hash as used for activation. Default: False.
        :return: True if hw is not banned, otherwise false
        """
        # Make sure the strings are not empty
        for i in hashes[2:5]:
            if i == "":
                log.warning("Invalid hash set ({}) for user {} in HWID check".format(hashes, userID), "bunk")
                return False

        # Run some HWID checks on that user if he is not restricted
        if not isRestricted(userID):
            # Get username
            username = getUsername(userID)

            # Get the list of banned or restricted users that have logged in from this or similar HWID hash set
            if hashes[2] == "b4ec3c4334a0249dae95c284ec5983df":
                # Running under wine, check by unique id
                log.debug("Logging Linux/Mac hardware")
                banned = glob.db.fetchAll("""SELECT users.id as userid, hw_user.occurencies, users.username FROM hw_user
                    LEFT JOIN users ON users.id = hw_user.userid
                    WHERE hw_user.userid != %(userid)s
                    AND hw_user.unique_id = %(uid)s
                    AND (users.privileges & 3 != 3)""", {
                    "userid": userID,
                    "uid": hashes[3],
                })
            else:
                # Running under windows, do all checks
                log.debug("Logging Windows hardware")
                banned = glob.db.fetchAll("""SELECT users.id as userid, hw_user.occurencies, users.username FROM hw_user
                    LEFT JOIN users ON users.id = hw_user.userid
                    WHERE hw_user.userid != %(userid)s
                    AND hw_user.mac = %(mac)s
                    AND hw_user.unique_id = %(uid)s
                    AND hw_user.disk_id = %(diskid)s
                    AND (users.privileges & 3 != 3)""", {
                    "userid": userID,
                    "mac": hashes[2],
                    "uid": hashes[3],
                    "diskid": hashes[4],
                })

            for i in banned:
                # Get the total numbers of logins
                total = glob.db.fetch("SELECT COUNT(*) AS count FROM hw_user WHERE userid = %s LIMIT 1", [userID])
                # and make sure it is valid
                if total is None:
                    continue
                total = total["count"]

                # Calculate 10% of total
                perc = (total * 10) / 100

                if i["occurencies"] >= perc:
                    # If the banned user has logged in more than 10% of the times from this user, restrict this user
                    restrict(userID)
                    appendNotes(userID,
                                "Logged in from HWID ({hwid}) used more than 10% from user {banned} ({bannedUserID}), who is banned/restricted.".format(
                                    hwid=hashes[2:5],
                                    banned=i["username"],
                                    bannedUserID=i["userid"]
                                ))
                    log.warning(
                        "**{user}** ({userID}) has been restricted because he has logged in from HWID _({hwid})_ used more than 10% from banned/restricted user **{banned}** ({bannedUserID}), **possible multiaccount**.".format(
                            user=username,
                            userID=userID,
                            hwid=hashes[2:5],
                            banned=i["username"],
                            bannedUserID=i["userid"]
                        ), "cm")

        # Update hash set occurencies
        glob.db.execute("""
                    INSERT INTO hw_user (id, userid, mac, unique_id, disk_id, occurencies) VALUES (NULL, %s, %s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE occurencies = occurencies + 1
                    """, [userID, hashes[2], hashes[3], hashes[4]])

        # Optionally, set this hash as 'used for activation'
        if activation:
            glob.db.execute(
                "UPDATE hw_user SET activated = 1 WHERE userid = %s AND mac = %s AND unique_id = %s AND disk_id = %s",
                [userID, hashes[2], hashes[3], hashes[4]])

        # Access granted, abbiamo impiegato 3 giorni
        # We grant access even in case of login from banned HWID
        # because we call restrict() above so there's no need to deny the access.
        return True

    def resetPendingFlag(userID, success=True):
        """
        Remove pending flag from an user.

        :param userID: user id
        :param success: if True, set USER_PUBLIC and USER_NORMAL flags too
        """
        glob.db.execute("UPDATE users SET privileges = privileges & %s WHERE id = %s LIMIT 1",
                        [~privileges.USER_PENDING_VERIFICATION, userID])
        if success:
            glob.db.execute("UPDATE users SET privileges = privileges | %s WHERE id = %s LIMIT 1",
                            [(privileges.USER_PUBLIC | privileges.USER_NORMAL), userID])

    def verifyUser(userID, hashes):
    	"""
    	Activate `userID`'s account.

    	:param userID: user id
    	:param hashes: 	Peppy's botnet (client data) structure (new line = "|", already split)
    					[0] osu! version
    					[1] plain mac addressed, separated by "."
    					[2] mac addresses hash set
    					[3] unique ID
    					[4] disk ID
    	:return: True if verified successfully, else False (multiaccount)
    	"""
    	if isInPrivilegeGroup(userID, 'Community Manager'):
    		return True
        
    	# Check for valid hash set
    	for i in hashes[2:5]:
    		if i == "":
    			log.warning("Invalid hash set ({}) for user {} while verifying the account".format(str(hashes), userID), "bunk")
    			return False

    	# Get username
    	username = getUsername(userID)

    	# Make sure there are no other accounts activated with this exact mac/unique id/hwid
    	if hashes[2] == "b4ec3c4334a0249dae95c284ec5983df" or hashes[4] == "ffae06fb022871fe9beb58b005c5e21d":
    		# Running under wine, check only by uniqueid
    		log.info("{user} ({userID}) ha triggerato Sannino:\n**Full data:** {hashes}\n**Usual wine mac address hash:** b4ec3c4334a0249dae95c284ec5983df\n**Usual wine disk id:** ffae06fb022871fe9beb58b005c5e21d".format(user=username, userID=userID, hashes=hashes), "bunker")
    		log.debug("Veryfing with Linux/Mac hardware")
    		match = glob.db.fetchAll("SELECT userid FROM hw_user WHERE unique_id = %(uid)s AND userid != %(userid)s AND activated = 1 LIMIT 1", {
    			"uid": hashes[3],
    			"userid": userID
    		})
    		return True
    	else:
    		# Running under windows, full check
    		log.debug("Veryfing with Windows hardware")
    		match = glob.db.fetchAll("SELECT userid FROM hw_user WHERE mac = %(mac)s AND unique_id = %(uid)s AND disk_id = %(diskid)s AND userid != %(userid)s AND activated = 1 LIMIT 1", {
    			"mac": hashes[2],
    			"uid": hashes[3],
    			"diskid": hashes[4],
    			"userid": userID
    		})

    	if match:
    		# This is a multiaccount, restrict other account and ban this account

    		# Get original userID and username (lowest ID)
    		originalUserID = match[0]["userid"]
    		originalUsername = getUsername(originalUserID)
    		# Stealth time, only dev knows it tho.
    		if isInPrivilegeGroup(originalUserID, 'Community Manager'):
    			log.info(f"{originalUsername} logged with another account called {username}.")
    			# appendNotes(originalUserID, "Has created multiaccount {} ({})".format(username, userID))
    			return True

    		# Ban this user and append notes
    		ban(userID)	# this removes the USER_PENDING_VERIFICATION flag too
    		appendNotes(userID, "{}'s multiaccount ({}), found HWID match while verifying account ({})".format(originalUsername, originalUserID, hashes[2:5]))
    		appendNotes(originalUserID, "Has created multiaccount {} ({})".format(username, userID))

    		# Restrict the original
    		restrict(originalUserID)
    		# send to discord
    		if 'DiscordWebhook' in globals():
    			pass
    			webhook = DiscordWebhook(url=glob.conf.config["discord"]["autobanned"])
    			embed = DiscordEmbed(title="NEW REPORTS!", description="{} has been banned because multiaccount (old id {} {})".format(username, originalUsername, originalUserID), color=16711680)
    			webhook.add_embed(embed)
    			webhook.execute()
    		# Disallow login
    		return False
    	else:
    		# No matches found, set USER_PUBLIC and USER_NORMAL flags and reset USER_PENDING_VERIFICATION flag
    		resetPendingFlag(userID)
    		#log.info("User **{}** ({}) has verified his account with hash set _{}_".format(username, userID, hashes[2:5]), "cm")
    	return True

    def hasVerifiedHardware(userID):
        """
        Checks if `userID` has activated his account through HWID

        :param userID: user id
        :return: True if hwid activation data is in db, otherwise False
        """
        data = glob.db.fetch("SELECT id FROM hw_user WHERE userid = %s AND activated = 1 LIMIT 1", [userID])
        if data is not None:
            return True
        return False

def getDonorExpire(userID):
    """
    Return `userID`'s donor expiration UNIX timestamp

    :param userID: user id
    :return: donor expiration UNIX timestamp
    """
    data = glob.db.fetch("SELECT donor_expire FROM users WHERE id = %s LIMIT 1", [userID])
    if data is not None:
        return data["donor_expire"]
    return 0

class invalidUsernameError(Exception):
    pass

class usernameAlreadyInUseError(Exception):
    pass

def safeUsername(username):
    """
    Return `username`'s safe username
    (all lowercase and underscores instead of spaces)

    :param username: unsafe username
    :return: safe username
    """
    return username.lower().strip().replace(" ", "_")

def changeUsername(userID=0, oldUsername="", newUsername=""):
    """
    Change `userID`'s username to `newUsername` in database

    :param userID: user id. Required only if `oldUsername` is not passed.
    :param oldUsername: username. Required only if `userID` is not passed.
    :param newUsername: new username. Can't contain spaces and underscores at the same time.
    :raise: invalidUsernameError(), usernameAlreadyInUseError()
    :return:
    """
    # Make sure new username doesn't have mixed spaces and underscores
    if " " in newUsername and "_" in newUsername:
        raise invalidUsernameError()

    # Get safe username
    newUsernameSafe = safeUsername(newUsername)

    # Make sure this username is not already in use
    if getIDSafe(newUsernameSafe) is not None:
        raise usernameAlreadyInUseError()

    # Get userID or oldUsername
    if userID == 0:
        userID = getID(oldUsername)
    else:
        oldUsername = getUsername(userID)

    # Change username
    glob.db.execute("UPDATE users SET username = %s, username_safe = %s WHERE id = %s LIMIT 1",
                    [newUsername, newUsernameSafe, userID])
    glob.db.execute("UPDATE users_stats SET username = %s WHERE id = %s LIMIT 1", [newUsername, userID])

    # Empty redis username cache
    # TODO: Le pipe woo woo
    glob.redis.delete("ripple:userid_cache:{}".format(safeUsername(oldUsername)))
    glob.redis.delete("ripple:change_username_pending:{}".format(userID))

def removeFromLeaderboard(userID):
    """
    Removes userID from global and country leaderboards.

    :param userID:
    :return:
    """
    # Remove the user from global and country leaderboards, for every mode
    country = getCountry(userID).lower()
    for mode in ["std", "taiko", "ctb", "mania"]:
        glob.redis.zrem("ripple:leaderboard:{}".format(mode), str(userID))
        glob.redis.zrem("ripple:leaderboard_relax:{}".format(mode), str(userID))
        if country is not None and len(country) > 0 and country != "xx":
            glob.redis.zrem("ripple:leaderboard:{}:{}".format(mode, country), str(userID))
            glob.redis.zrem("ripple:leaderboard_relax:{}:{}".format(mode, country), str(userID))

def deprecateTelegram2Fa(userID):
    """
    Checks whether the user has enabled telegram 2fa on his account.
    If so, disables 2fa and returns True.
    If not, return False.

    :param userID: id of the user
    :return: True if 2fa has been disabled from the account otherwise False
    """
    try:
        telegram2Fa = glob.db.fetch("SELECT id FROM 2fa_telegram WHERE userid = %s LIMIT 1", (userID,))
    except ProgrammingError:
        # The table doesnt exist
        return False

    if telegram2Fa is not None:
        glob.db.execute("DELETE FROM 2fa_telegram WHERE userid = %s LIMIT 1", (userID,))
        return True
    return False

def unlockAchievement(userID, achievementID):
    glob.db.execute("INSERT INTO users_achievements (user_id, achievement_id, `time`) VALUES"
                    "(%s, %s, %s)", [userID, achievementID, int(time.time())])

def getAchievementsVersion(userID):
    result = glob.db.fetch("SELECT achievements_version FROM users WHERE id = %s LIMIT 1", [userID])
    if result is None:
        return None
    return result["achievements_version"]

def updateAchievementsVersion(userID):
    glob.db.execute("UPDATE users SET achievements_version = %s WHERE id = %s LIMIT 1", [
        glob.ACHIEVEMENTS_VERSION, userID
    ])

def getClan(userID):
    """
    Get userID's clan

    :param userID: user id
    :return: username or None
    """
    clanInfo = glob.db.fetch(
        "SELECT clans.tag, clans.id, user_clans.clan, user_clans.user FROM user_clans LEFT JOIN clans ON clans.id = user_clans.clan WHERE user_clans.user = %s LIMIT 1",
        [userID])
    username = getUsername(userID)

    if clanInfo is None:
        return username
    return "[" + clanInfo["tag"] + "] " + username

def getUserCountryClan(userID):
    """
    this is just simply shitty name.
    """
    clanInfo = glob.db.fetch(
        "SELECT clans.tag, clans.id, user_clans.clan, user_clans.user FROM user_clans LEFT JOIN clans ON clans.id = user_clans.clan WHERE user_clans.user = %s LIMIT 1",
        [userID])
    username = getUsername(userID)

    if clanInfo is None:
        return "C00000000"
    return "C{:08d}".format(clanInfo['id'])

def obtainPPLimit(userID, gameMode, relax=False, modded=False):
	support_new_limiter = 'pp-limiter' in glob.conf.extra['lets']['submit']
	mode_name = 'std taiko ctb mania'.split()[gameMode]
	if support_new_limiter:
		var_limit   = glob.conf.extra['lets']['submit']['pp-limiter'].get(mode_name + '-tolerant',False)
		var_fullmod = glob.conf.extra['lets']['submit']['pp-limiter'].get(mode_name + '-tolerant-mod',False)
		max_total   = glob.conf.extra['lets']['submit']['pp-limiter'].get(mode_name + '-tootall-ceil',5555)
	else:
		var_limit   = glob.conf.extra['lets']['submit'].get('tolerant-pp-limit',False)
		var_fullmod = glob.conf.extra['lets']['submit'].get('tolerant-fullmod',False)
		max_total   = 5555
	# Check eligiblity of Variable Limiter
	# - it'll go as is, if it's not FULLMOD
	# - if it's FULLMOD, should check if VARIABLE_FULLMOD is on or not.
	can_limit = (modded and var_fullmod) or var_limit
	if relax:
		current_stats = getUserStatsRx(userID, gameMode)
	else:
		current_stats = getUserStats(userID, gameMode)
	# Given a current player statistics
	# Calculate maximum obtainable PP by player. This will allow proper progression of respective player.
	def calculate_limit(limiter, stat):
		# Define a simple scoring with easing to control acceleration towards maximum value.
		def determine_score(value, low, high, ease):
			if value < low:
				return 0
			elif value > high:
				return 1
			return ((value - low) / (high - low)) ** ease
		
		pp_limits = (limiter[0], limiter[1])
		if limiter[1] <= limiter[0]:
			return limiter[0]
		# format (low, hi, ease%)
		play_count_limits = tuple(limiter[2])
		total_pp_limits   = tuple(limiter[3])
		# scoring
		weight_pc, weight_pp = (limiter[4], limiter[5])
		score_pc, score_pp = determine_score(stat['playcount'], *play_count_limits), determine_score(stat['pp'], *total_pp_limits)
		total_score = score_pc * weight_pc + score_pp * weight_pp
		log.debug("PP Limit Score: {}/{}".format(int(total_score), weight_pc + weight_pp))
		return pp_limits[0] + int((pp_limits[1] - pp_limits[0]) * (total_score / (weight_pc + weight_pp)))
	pass
	if support_new_limiter:
		cfg = glob.conf.extra["lets"]["submit"]["pp-limiter"]
	else:
		cfg = glob.conf.extra["lets"]["submit"]
	if can_limit:
		if support_new_limiter:
			if relax:
				limiter = cfg[mode_name + "-relax-fm"]
			else:
				limiter = cfg[mode_name + "-vanilla-fm"]
			if modded and f"{mode_name}-modded-fm" in cfg:
				limiter = cfg.get(mode_name + "-modded-fm",limiter)
		else:
			if relax:
				limiter = cfg["max-relax-pp-formula"]
			else:
				limiter = cfg["max-vanilla-pp-formula"]
			if modded and "max-fullmod-pp-formula" in cfg:
				limiter = cfg.get("max-fullmod-pp-formula",limiter)
		score = calculate_limit(limiter, current_stats)
	else:
		if support_new_limiter:
			basic_pp   = cfg[mode_name + "-vanilla-max"]
			relax_pp   = cfg["pp-limiter"][mode_name + "-relax-max"]
			fullmod_pp = cfg[mode_name + "-modded-max"]
		else:
			basic_pp   = cfg["max-vanilla-pp"]
			relax_pp   = cfg["max-std-pp"]
			fullmod_pp = cfg.get("max-fullmod-pp", 1000)
		if modded:
			score = fullmod_pp
		else:
			score = 999999 if gameMode > 0 else (relax_pp if relax else basic_pp)
	return (score, var_limit, can_limit, max_total)

# Delete all generators
def _wipe():
    to_d = []
    for k,v in globals().items():
        if callable(v) and k.startswith('_gen'):
            to_d.append(k)
    for k in to_d:
        del globals()[k]
_wipe()
del _wipe

if 'relax' not in features.DEPRECATE_SHITTY_ABBREVIATION:
    incrementPlaytimeRX = incrementPlaytimeRelax
    getUserStatsRx = getUserStatsRelax
    getMaxComboRX = getMaxComboRelax
    updateLevelRX = updateLevelRelax
    calculateAccuracyRX = calculateAccuracyRelax
    updateStatsRx = updateStatsRelax
    refreshStatsRx = refreshStatsRelax
    incrementUserBeatmapPlaycountRX = incrementUserBeatmapPlaycountRelax
    incrementReplaysWatchedRX = incrementReplaysWatchedRelax
    getGameRankRx = getGameRankRelax
    getPlaycountRX = getPlaycountRelax
    updateTotalHitsRX = updateTotalHitsRelax
    print("[!] PLEASE NORMALIZE THE RELAX ABBREVIATION IN THIS FILE.")
