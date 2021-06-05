from common.constants import mods
from objects import glob

def isRankable(m):
	"""
	Checks if `m` contains unranked mods

	:param m: mods enum
	:return: True if there are no unranked mods in `m`, else False
	"""
	# I am a wizard.... feel free to make sense of this and do a better job (merge req are welcome)
	if "_unranked-mods" not in glob.conf.extra:
		glob.conf.extra["_unranked-mods"] = sum([getattr(mods, key) for key, value in
												glob.conf.extra["common"]["rankable-mods"].items() if not value
												]) # Store the unranked mods mask into glob

	# I know bitmasks... so get that old trash out of here ktnxbye
	return m & ~glob.conf.extra["_unranked-mods"] == m and m & 8320 != 8320

def readableGameMode(gameMode):
	"""
	Convert numeric gameMode to a readable format. Can be used for db too.

	:param gameMode:
	:return:
	"""
	# TODO: Same as common.constants.gameModes.getGameModeForDB, remove one
	if gameMode == 0:
		return "std"
	elif gameMode == 1:
		return "taiko"
	elif gameMode == 2:
		return "ctb"
	else:
		return "mania"
