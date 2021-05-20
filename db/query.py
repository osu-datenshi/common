class QueryBuilder:
	BUILD_LIMIT = 1048576

	def __init__(self, prefix, suffix, join=','):
		self.prefix  = prefix
		self.suffix  = suffix
		self.join    = join
		self.builder = None
		self.finisher = None
		self.reset()

	def reset(self):
		self.query = ''

	def append(self, stmt):
		if self.builder is None:
			if self.query:
				self.query += self.join
			self.query += ' '
			self.query += stmt
		else:
			self.query += self.builder(self, stmt)

	def build(self):
		if self.query:
			query = "{} {} {}".format(self.prefix, self.query, self.suffix)
			if self.finisher is not None:
				query = self.finisher(query)
			return query

	def appendAndBuild(self, stmt):
		self.append(stmt)
		if self.longQuery:
			query = self.build()
			self.reset()
			return query

	@property
	def longQuery(self):
		return len(self.query) > self.BUILD_LIMIT
