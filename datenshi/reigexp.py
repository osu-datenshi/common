import re

def match(type, search, string):
	if type == 'split':
		return bool(re.search('{1}{2}{1}'.format(r'\b', search), string))
	elif type in ('advanced', 'regexp'):
		return bool(re.search(search, string))
	elif type == 'partial':
		return search in string
	else:
		return search == string
