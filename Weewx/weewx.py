#!/usr/bin/env python
# -* coding: utf-8 *-

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Developed 2017 by Christopher McAvaney <christopher.mcavaney@gmail.com>
# Intended for own use, but could be used by anybody who is using Weewx with MySQL database.

import MySQLdb
from MySQLdb.constants import ER

class WeewxInfo:
	db_cnx = None

	def __init__(self, weewx_user, weewx_password, weewx_host, weewx_database):
		# connect to database
		try:
			self.db_cnx = MySQLdb.connect(user=weewx_user, passwd=weewx_password, host=weewx_host, db=weewx_database)
		except MySQLdb.Error as err:
			if err.args[0] == ER.ACCESS_DENIED_ERROR:
				print("%s: Something is wrong with your user name or password" % (self.__class__.__name__))
			elif err.args[0] == ER.BAD_DB_ERROR:
				print("%s: Database does not exist" % (self.__class__.__name__))
			else:
				print("%s: %s" % (self.__class__.__name__, err))
				raise

	def getCurrentOutsideTemp(self):
		db_cursor = self.db_cnx.cursor()

		query = """
			-- o = observations
			-- within the last 15 minutes
			select
				from_unixtime(o.dateTime) day_for_timestamp,
				round((o.outTemp - 32) * 5/9, 1) last_outTemp
			from
				archive o
			where
				o.dateTime >= (unix_timestamp(now()) - (15 * 60))
			order by
				o.dateTime desc
			limit 0,1
		"""

		db_cursor.execute(query)
		data = db_cursor.fetchone()
		rows = db_cursor.rowcount
		db_cursor.close()

		temp = None
		if rows != 0:
			temp = data[1]
		
		return temp

	def __exit__(self, exc_type, exc_value, traceback):
		self.db_cnx.close()

# END OF FILE
