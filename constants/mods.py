"""
Mod constants.
"""

NOMOD       = 0
NOFAIL      = 1
EASY        = 2
TOUCHSCREEN = 4
HIDDEN      = 8
HARDROCK    = 16
SUDDENDEATH = 32
DOUBLETIME  = 64
RELAX       = 128
HALFTIME    = 256
NIGHTCORE   = 512
FLASHLIGHT  = 1024
AUTOPLAY    = 2048
SPUNOUT     = 4096
RELAX2      = 8192
PERFECT     = 16384
KEY4        = 32768
KEY5        = 65536
KEY6        = 131072
KEY7        = 262144
KEY8        = 524288
KEYMOD      = 1015808
FADEIN      = 1048576
RANDOM      = 2097152
LASTMOD     = 4194304
KEY9        = 16777216
KEY10       = 33554432
KEYDOUBLE   = 33554432
KEYCOOP     = 33554432
KEY1        = 67108864
KEY3        = 134217728
KEY2        = 268435456
SCOREV2     = 536870912
MIRROR      = 1073741824

def _wrapper_():
	# remove wrapper from namespace
	del globals()['_wrapper_']
	# a way to avoid from writing it directly.
	stupid_names = 'ZE XR'.split()
	# we have three naming conventions here
	# - normal/sane
	# - community
	# - programming property-wise
	sane_names   = 'NM NF EM TD HD HR SD DT RL HT NC FL AP SO ATP PF 4K 5K 6K 7K 8K SUD RAN CIN 9K DP 1K 3K 2K V2 MIR'.split()
	comm_names   = 'NM NF {} TD HD HR SD DT {} HT NC FL AP SO ATP PF 4K 5K 6K 7K 8K FI RD CIN 9K DP 1K 3K 2K V2 MR'.format(
		*[dumb[::-1] for dumb in stupid_names]
	).split()
	syntax_names = 'NM NF EM TD HD HR SD DT RL HT NC FL AP SO ATP PF K4 K5 K6 K7 K8 SUD RAN CIN 9K DP K1 K3 K2 V2 MIR'.split()
	
	# shorten global temporary
	g = globals()
	mvalues = {}
	# generate namespace values from each naming conventions
	for name_list in [sane_names, comm_names, syntax_names]:
		for i, name in zip(range(len(name_list)),name_list):
			# our assumption here is
			# - mod names never been registered before, so we gotta quick.
			v = 1 << (i - 1) if i > 0 else 0
			if name not in mvalues:
				mvalues[name] = v
			if name not in g:
				g[name] = v
	
	# add exclusive mod flags
	# this part is not for total exclusion, but for addition of mods that can made the mods overlapping instead.
	excl_mods = 'NC DT;PF SD'.split(';')
	excl_mods = [mp.split() for mp in excl_mods]
	
	# obtain mod value from strings
	def selectMods(*mod_str):
		"""
		Obtain mod value from given string.
		All arguments must be a mixture of mod strings.
		"""
		mod_value = 0
		flat_str = set(ms for ml in mod_str for ms in ml.split() if isinstance(ml, str))
		for ms in flat_str:
			# only limit selectMods query to defined mod names
			if not any(ms in a for a in [sane_names, comm_names]):
				continue
			mod_value = mod_value | g[ms]
		return mod_value
	
	# Register KEY MODS
	for k in 'KM KEYMODS KeyMod'.split():
		g[k] = selectMods(*[f"{n}K" for n in range(1,10)],'DP')
	
	# Register FREE MODS
	for k in 'FM FREEMODS FreeMod'.split():
		g[k] = selectMods('NF', 'EM HR', 'HD SUD', 'SD', 'FL', 'RL ATP SP') | KM
	
	# Register SPECIAL MODE marker
	g['SPECIAL_MODES'] = selectMods('RL', 'V2')
	# Register SCORE DOWN marker
	g['SCORE_DOWN'] = selectMods('EM', 'NF', 'HT')
	
	def toModString(value, mode=0, sep=','):
		"""
		Convert given mod value into a mod string.
		"""
		for excl_pair in excl_mods:
			if not all(value & g[mp] for mp in excl_pair):
				continue
			value = value & ~g[excl_pair[1]]
		if not value:
			return 'NM'
		m = []
		a = [sane_names, comm_names]
		mode = 0 if mode not in range(len(a)) else mode
		for mb, mod in zip(range(len(a[mode])-1),a[mode][1:]):
			if mod not in m and value & (1 << mb):
				m.append(mod)
		return sep.join(m)
	
	# register functions to global namespace
	for f in [selectMods, toModString]:
		g[f.__name__] = f

_wrapper_()
