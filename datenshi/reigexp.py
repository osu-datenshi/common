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

def replace(type, search, string, replacement, flags=matchFlags):
	if not match(type, search, string):
		return string
	if type == 'split':
		split_search = '{1}{2}{1}'.format(r'\b', search)
		return re.sub(split_search, replacement, string, flags=flags)
	elif type in ('advanced', 'regexp'):
		return re.sub(search, replacement, string, flags=flags)
	elif type == 'partial':
		return string.replace(search, replacement)
	else:
		return replacement
