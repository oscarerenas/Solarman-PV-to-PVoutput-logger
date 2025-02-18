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

# Developed 2016 by Christopher McAvaney <christopher.mcavaney@gmail.com>
# Intended for own use, but could be used by anybody who has a SolarmanPV Portal API key.
# Released to the public in 2016.

import requests
import datetime
from util import DEBUG
import sys
import socket
import six
# put in place for python2 vs python3 compatibility
if six.PY2:
	from urlparse import urlparse
elif six.PY3:
	from urllib.parse import urlparse
import subprocess

solarman_pv_api_base = 'https://openapi.solarmanpv.com/v1'

class SolarmanPVAPI:
	# NOTE: You will need to know the plant_id for the "plant" that you want to retrieve data
	def __init__(self, client_id, client_secret, plant_id):
		self.__client_id = client_id
		self.__client_secret = client_secret
		self.__plant_id = plant_id
		self.__access_token = ""
		self.__auth_headers = {}
		self.__authorised = False
		self.__requests_verify = True
		# default timeout of 7 seconds
		self.__requests_timeout = 7
		self.debug = True

		self.connected = self.__connect()

	def setDebug(self, debug):
		self.debug = debug

	def __str__(self):
		return self.__class__.__name__ + ' TO BE COMPLETED'

	def __requests_get(self, url, verify=None, timeout=None, headers=None, params=None):
		if verify is None:
			verify = self.__requests_verify
		if timeout is None:
			timeout = self.__requests_timeout
		url_components = urlparse(url)

		try:
			if headers is not None and params is not None:
				response = requests.get(url, verify=verify, timeout=timeout, headers=headers, params=params)
			elif headers is not None and params is None:
				response = requests.get(url, verify=verify, timeout=timeout, headers=headers)
			elif headers is None and params is not None:
				response = requests.get(url, verify=verify, timeout=timeout, params=params)
			elif headers is None and params is None:
				response = requests.get(url, verify=verify, timeout=timeout)
		except requests.exceptions.SSLError as e:
			if self.debug:
				DEBUG('SSLError - trying again without verify turned on')
			try:
				# This could possibly be an issue with the SSL certificate of the API service being expired 
				# or something, probably harmless, so try without verifying the certificate
				if headers is not None and params is not None:
					response = requests.get(url, verify=False, timeout=timeout, headers=headers, params=params)
				elif headers is not None and params is None:
					response = requests.get(url, verify=False, timeout=timeout, headers=headers)
				elif headers is None and params is not None:
					response = requests.get(url, verify=False, timeout=timeout, params=params)
				elif headers is None and params is None:
					response = requests.get(url, verify=False, timeout=timeout)
				else:
					print('here - but why')
					print('headers == %s params == %s' % (str(headers), str(params)))
			except:
				print('%s: SSLError (no verify attempt): %s' % (self.__class__.__name__, e))
				print('url == %s' % (url))
				subprocess.call("echo | openssl s_client -showcerts -servername %s -connect %s:443 2>/dev/null | openssl x509 -inform pem -noout -text" % (url_components.netloc, url_components.netloc), shell=True)
				# catastrophic failure
				sys.exit(2)
		except socket.gaierror as e:
			print('%s: gaierror - %s\n' % (self.__class__.__name__, e))
			print('attempt to connect to %s\n' % (url_components['netloc']))
			sys.exit(2)
			return False
		except requests.exceptions.ConnectionError as e:
			print('%s: connection failed - %s\n' % (self.__class__.__name__, e))
			sys.exit(2)
			return False
		except requests.exceptions.Timeout as e:
			print('%s: request timed out - %s\n' % (self.__class__.__name__, e))
			# Maybe at this point, we could sleep for 5 seconds and then try again? - to be implemented
			sys.exit(2)
			return False
		except requests.exceptions.RequestException as e:
			print('%s: request failed - %s\n' % (self.__class__.__name__, e))
			sys.exit(2)
			return False
		except:
			print('%s: request failed - %s\n' % (self.__class__.__name__, sys.exc_info()[0]))
			return False

		return response

	def __connect(self):
		# Connect to the API and get the authorisation token required for subsequent requests
		url = solarman_pv_api_base + '/oauth2/accessToken?client_id=%s&client_secret=%s&grant_type=client_credentials' % (self.__client_id, self.__client_secret)
		response = self.__requests_get(url, timeout=15)
		"""
		try:
			response = requests.get(url, verify=self.__requests_verify, timeout=7)
		except socket.gaierror as e:
			print('%s: gaierror - %s\n' % (self.__class__.__name__, e))
			print('attempt to connect to %s\n' % (solarman_pv_api_base))
			return False
		except requests.exceptions.ConnectionError as e:
			print('%s: connection failed - %s\n' % (self.__class__.__name__, e))
			return False
		except requests.exceptions.RequestException as e:
			print('%s: request failed - %s\n' % (self.__class__.__name__, e))
			return False
		"""

		# Grab the uid (which is just the client_id returned) and access_token and put them in a 
		# variable for subsequent API calls
		try:
			uid = response.json()['data']['uid']
		except ValueError as e:
			print('%s: __connect(): ValueError == %s\n' % (self.__class__.__name__, e))
			print('response == %s\n' % response)
			return False
		except:
			print("%s: __connect(): Unexpected error: %s" % (self.__class__.__name__, sys.exc_info()[0]))
			return False

		token = response.json()['data']['access_token']
		self.__auth_headers = {'uid':uid, 'token':token}

		self.__authorised = True
		return True

	# Allows sorting and deals with the case of no time value (shouldn't happen, but could do)
	def __extractTimePowerData(self, json):
		# Need to convert datetime to unixtime - even though value is UTC and this will change to localtime, 
		# not an issue as it is only for a relative comparison
		unix_ts = datetime.datetime.strptime(json['time'], "%Y-%m-%dT%H:%M:%SZ").strftime("%s")
		try:
			return int(unix_ts)
		except KeyError:
			return 0

	# Allows sorting and deals with the case of no time value (shouldn't happen, but could do)
	def __extractTimeInverterData(self, json):
		# Need to convert datetime to unixtime - even though value is UTC and this will change to localtime, 
		# not an issue as it is only for a relative comparison
		unix_ts = datetime.datetime.strptime(json['time'], "%Y-%m-%dT%H:%M:%S+10:00").strftime("%s")
		try:
			return int(unix_ts)
		except KeyError:
			return 0

	# Returns power data as a JSON object
	def getPower(self, date_to_retrieve=None, most_recent_value=None):
		if date_to_retrieve is None:
			date_to_retrieve = datetime.date.today().strftime('%Y-%m-%d')

		if self.debug:
			DEBUG('getPower()')
			DEBUG('today == ' + date_to_retrieve)
			DEBUG('Getting plant power (for a day)')

		# Get the power data for a specified date or today
		url = solarman_pv_api_base + '/plant/power'
		params = {'plant_id':self.__plant_id, 'date':date_to_retrieve, 'timezone_id':'Australia/Canberra'}
		response = self.__requests_get(url, self.__requests_verify, 40, self.__auth_headers, params)
		"""
		try:
			response = requests.get(url, verify=self.__requests_verify, timeout=7, headers=self.__auth_headers, params=params)
		except requests.exceptions.ConnectionError as e:
			print('%s: connection failed - %s' % (self.__class__.__name__, e))
			return None
		"""
			
		response.encoding = 'utf-8'

		if self.debug:
			print('response == ' + str(response))
			print('response.url == ' + response.url)
			print('response.encoding == ' + response.encoding)
			print('response.text == ' + response.text)
			#print response.json()

		# validate response
		if 'data' not in response.json() and 'powers' not in response.json():
			# should return None, maybe an exception
			print('%s:getPower(): data or powers not in response: %s' % (self.__class__.__name__, response.text.encode('ascii', 'replace')))
			return None

		if most_recent_value is True:
			# Sort the json() (just to be sure), take the last value
			power_data = response.json()['data']['powers']
			most_recent_power_data = None
			if isinstance(power_data, list): 
				power_data.sort(key=self.__extractTimePowerData, reverse=True)
				# temporary exception handler to nut out but first thing in the morning
				try:
					most_recent_power_data = power_data[0]
				except IndexError:
					# Some error in response from the API, i.e. an empty list
					most_recent_power_data = None
				except:
					# Effectively an unhandled error - retaining this debug whilst in beta testing mode
					print('%s: Exception: getPower(): An error with power_data %s' % (self.__class__.__name__, sys.exc_info()[0]))
					print(str(power_data))
					print(power_data)
			else:
				# temporary debug - whilst in beta testing mode
				print('is this an empty response case? debugs below will help diagnose')
				print('power_data == ' + str(power_data))
				print('most_recent_power_data == ' + str(most_recent_power_data))
				print('response.json() == ' + str(response.json()))
			return most_recent_power_data
		else:
			return response.json()

	# Returns inverter data as a JSON object
	def getInverterData(self, date_to_retrieve=None, device_id=None, most_recent_value=None):
		if date_to_retrieve is None:
			date_to_retrieve = datetime.date.today().strftime('%Y-%m-%d')

		if device_id.isdigit() is not True:
			print('device id is not a number')
			return None

		if self.debug:
			DEBUG('getInverterData()')
			DEBUG('today == ' + date_to_retrieve)
			DEBUG('Getting inverter data (for a day)')

		# Get the power data for a specified date or today
		url = solarman_pv_api_base + '/device/inverter/data'
		params = {'device_id':device_id, 'start_date':date_to_retrieve, 'end_date':date_to_retrieve, 'timezone_id':'Australia/Canberra', 'perpage': '500'}
		response = self.__requests_get(url, self.__requests_verify, 40, self.__auth_headers, params)
		"""
		try:
			response = requests.get(url, verify=self.__requests_verify, timeout=7, headers=self.__auth_headers, params=params)
		except requests.exceptions.ConnectionError as e:
			print('%s: connection failed - %s' % (self.__class__.__name__, e))
			return None
		except requests.exceptions.ReadTimeout as e:
			print('%s: connection timed out - %s' % (self.__class__.__name__, e))
			return None
		"""
			
		response.encoding = 'utf-8'

		if self.debug:
			print('response == ' + str(response))
			print('response.url == ' + response.url)
			print('response.encoding == ' + response.encoding)
			print('response.text == ' + response.text)
			#print(response.json())

		# validate response
		try:
			if 'data' not in response.json() and 'datas' not in response.json():
				# should return None, maybe an exception
				print('%s: data or powers not in response: %s' % (self.__class__.__name__, response.text.encode('utf-8').strip()))
				return None
		except:
			print('exception on response - it should be json but is:')
			print(str(response.text))
			return None

		if most_recent_value is True:
			# Sort the json() (just to be sure), take the last value
			inverter_data = response.json()['data']['datas']
			most_recent_inverter_data = None
			if isinstance(inverter_data, list): 
				inverter_data.sort(key=self.__extractTimeInverterData, reverse=True)
				# temporary exception handler to nut out but first thing in the morning
				try:
					most_recent_inverter_data = inverter_data[0]
				except IndexError:
					# Some error in response from the API, i.e. an empty list
					most_recent_inverter_data = None
				except:
					# Effectively an unhandled error - retaining this debug whilst in beta testing mode
					print('%s: Exception: getInverterData(): An error with inverter_data %s' % (self.__class__.__name__, sys.exc_info()[0]))
					print(str(inverter_data))
					print(inverter_data)
			else:
				# temporary debug - whilst in beta testing mode
				print('is this an empty response case? debugs below will help diagnose')
				print('inverter_data == ' + str(inverter_data))
				print('most_recent_power_data == ' + str(most_recent_power_data))
				print('response.json() == ' + str(response.json()))
			return most_recent_inverter_data
		else:
			return response.json()

# END OF FILE
