import re

matchFlags = re.M

def match(type, search, string, flags=matchFlags):
	if type == 'split':
		return bool(re.search('{1}{2}{1}'.format(r'\b', search), string, flags=flags))
	elif type in ('advanced', 'regexp'):
		return bool(re.search(search, string, flags=flags))
	elif type == 'partial':
		return search in string
	else:
		return search == string

def replace(match_type, search, string, replace_type, replacement, flags=matchFlags):
	if not match(match_type, search, string):
		return string
	if replace_type == 'total':
		return replacement
	if match_type == 'split':
		split_search = '{1}{2}{1}'.format(r'\b', search)
		return re.sub(split_search, replacement, string, flags=flags)
	elif match_type in ('advanced', 'regexp'):
		return re.sub(search, replacement, string, flags=flags)
	elif match_type == 'partial':
		return string.replace(search, replacement)
	else:
		return replacement
