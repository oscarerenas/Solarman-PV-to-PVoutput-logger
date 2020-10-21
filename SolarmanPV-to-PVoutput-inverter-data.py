#!/usr/bin/python
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

# Based on Matt Cordell's SolarMax_PVoutLiveLog.py code
# Developed 2016 by Christopher McAvaney <christopher.mcavaney@gmail.com>


import sys
import argparse
import datetime
from util import DEBUG, utc_to_local
# class for talking to the Solarman PV API
from SolarmanPVAPI.solarmanpv_api import SolarmanPVAPI
# API for talking to the PVoutput inverter
from PVoutput.pvoutput import PVoutput_Connection
# class for getting Weewx info
from Weewx.weewx import WeewxInfo
import requests
import socket


if sys.version_info < (2, 7):
	raise "must user Python 2.7 or greater"

# pvoutput specifics
# time to delay between API calls
apiDelay = 5
appVersion = 0.3

# parameters (with defaults)
debug = False
smpv_client_id = smpv_client_secret = smpv_plant_id = None
pvo_key = pvo_system_id = None
weewx_user = weewx_password = weewx_host = weewx_database = None

parser = argparse.ArgumentParser(prog=sys.argv[0])
parser.add_argument("-d", "--debug", help="turn on debug output", action="store_true")
parser.add_argument("-v", "--version", action="version", version="%(prog)s " + str(appVersion))
parser.add_argument("--smpv_client_id", help="SolarmanPV API client ID", required=True)
parser.add_argument("--smpv_client_secret", help="SolarmanPV API client secret", required=True)
parser.add_argument("--smpv_plant_id", help="ID of the plant (i.e. The solar PV site within SolarmanPV)", required=True)
parser.add_argument("--smpv_device_id", help="ID of the device (i.e. The solar PV inverter within the site within SolarmanPV)", required=True)
parser.add_argument("--pvo_key", help="PVoutput API key", required=True)
parser.add_argument("--pvo_system_id", help="PVoutput system ID", required=True)
parser.add_argument("--power_data", help="Use the getPower() i.e. SolarmanPVAPI plant/power method.  Default is getInverterData()", required=False, action="store_true")
parser.add_argument("--weewx_user", help="Weewx MySQL username", required=True)
parser.add_argument("--weewx_password", help="Weewx MySQL password", required=True)
parser.add_argument("--weewx_host", help="Weewx MySQL host", required=True)
parser.add_argument("--weewx_database", help="Weewx MySQL database", required=True)
args = parser.parse_args()

if args.debug:
	print("debug turned on")
	debug = True

client_id = args.smpv_client_id
client_secret = args.smpv_client_secret
plant_id = args.smpv_plant_id
device_id = args.smpv_device_id
pvo_key = args.pvo_key
pvo_system_id = args.pvo_system_id
weewx_user = args.weewx_user
weewx_password = args.weewx_password
weewx_host = args.weewx_host
weewx_database = args.weewx_database

if args.power_data:
	data_method = 'power'
else:
	data_method = 'inverter'

# Create the SolarmanAPI object
smpv = SolarmanPVAPI(client_id, client_secret, plant_id)
smpv.setDebug(debug)
if smpv.connected is not True:
	print('An issue with connection to the SolarmanPV API')
	sys.exit(1)

# get temperature data from Weewx
# create an instance for a Weewx class and call the get "current outside temp" method
try:
	weather_info = WeewxInfo(weewx_user, weewx_password, weewx_host, weewx_database)
	current_outside_temp = weather_info.getCurrentOutsideTemp()
except:
	current_outside_temp = None
DEBUG('current outside temp == ' + str(current_outside_temp))

# testing getInverterData() instead (see below after this if statement)
if data_method == 'power':
	power_details = smpv.getPower(datetime.date.today().strftime("%Y-%m-%d"), True)
	if power_details is not None:
		power = power_details['power']
		# need to convert date and time value from UTC to local time before uploading to pvoutput.org
		power_datetime_local = utc_to_local(datetime.datetime.strptime(power_details['time'], "%Y-%m-%dT%H:%M:%SZ"))
		power_date = power_datetime_local.strftime("%Y%m%d")
		power_time = power_datetime_local.strftime("%H:%M")

		DEBUG('power == ' + str(power) + ' and power_date == ' + power_date)

		try:
			# Create connection to pvoutput.org
			pvout = PVoutput_Connection(pvo_key, pvo_system_id)
			# update pvoutput - but only if there is a value power value (i.e. > 0)

			# add_output() is for end of day output - therfore the peak power, peak time, etc
#			pvout.add_output(power_date, generated=power)

			if power > 0:
				DEBUG('adding inverter data to PVOutput')
				pvout.add_status(power_date, power_time, power_exp=power, temp=current_outside_temp)
			else:
				DEBUG('no need to update - power %dW' % power)
		except:
			print('An error with PVoutput ', sys.exc_info()[0])
			raise
	else:
		# Changed this to a DEBUG, so that it won't output when in a CRON job
		DEBUG('Invalid power data from SolarmanPV API - no further action')

elif data_method == 'inverter':
	date_to_retrieve = datetime.date.today().strftime("%Y-%m-%d")
	inverter_details = smpv.getInverterData(date_to_retrieve, device_id, True)
	if inverter_details is not None:
		DEBUG('inverter_details == ' + str(inverter_details))
		DEBUG('power == %sW' % (inverter_details['power']))
		DEBUG('input current 1 == %sA and 2 == %sA' % (inverter_details['iPv1'], inverter_details['iPv2']))
		DEBUG('input voltage 1 == %sV and 2 == %sV' % (inverter_details['vPv1'], inverter_details['vPv2']))
		DEBUG('output current 1 == %sA' % (inverter_details['iac1']))
		DEBUG('output voltage 1 == %sV' % (inverter_details['vac1']))
		DEBUG('frequency == %sHz' % (inverter_details['fac']))
		DEBUG('time == %s' % (inverter_details['time']))
		inverter_datetime_local = datetime.datetime.strptime(inverter_details['time'], "%Y-%m-%dT%H:%M:%S+10:00")
		inverter_date = inverter_datetime_local.strftime("%Y%m%d")
		inverter_time = inverter_datetime_local.strftime("%H:%M")
		DEBUG('inverter power == ' + str(inverter_details['power']) + ' and inverter_date == ' + inverter_date + ' inverter_time == ' + inverter_time)

		#	power = power_details['power']
		#	# need to convert date and time value from UTC to local time before uploading to pvoutput.org
		#	power_datetime_local = utc_to_local(datetime.datetime.strptime(power_details['time'], "%Y-%m-%dT%H:%M:%SZ"))
		#	power_date = power_datetime_local.strftime("%Y%m%d")
		#	power_time = power_datetime_local.strftime("%H:%M")

		#	DEBUG('power == ' + str(power) + ' and power_date == ' + power_date)

		try:
			# Create connection to pvoutput.org
			pvout = PVoutput_Connection(pvo_key, pvo_system_id)
			# update pvoutput - but only if there is a value power value (i.e. > 0)

			# add_output() is for end of day output - therfore the peak power, pear time, etc
#			pvout.add_output(power_date, generated=power)

			if inverter_details['power'] > 0:
				DEBUG('adding inverter data to PVOutput')
				pvout.add_status(inverter_date, inverter_time, power_exp=inverter_details['power'], vdc=inverter_details['vac1'], temp=current_outside_temp)
			else:
				DEBUG('no need to update - power %dW' % inverter_details['power'])
		except requests.exceptions.Timeout as e:
			print('PVoutput_Connection: request failed on a timeout - %s' % (e))
		except socket.error as e:
			print('PVoutput_Connection: request/socket failed on a timeout - %s' % (e))
		except:
			print('An error with PVoutput ', sys.exc_info()[0])
			raise
	else:
		# Changed this to a DEBUG, so that it won't output when in a CRON job
		DEBUG('Invalid inverter data from SolarmanPV API - no further action')

# temporary exit, looking to include voltage and current data - but need to find out why the current day data doesn't come back through the API
sys.exit(5)

# cycle through the known inverters
count = 0
for sm in smlist:
    for (no, ivdata) in sm.inverters().iteritems():
        try:
            # Pass the parameters you wish to get from the inverter and log. Power, Voltage and Temp are all that's required for PVoutput.
            (inverter, current) = sm.query(no, ['PAC', 'UL1', 'TKK'])

            # create connection to pvoutput.org
            pvoutz = PVoutput_Connection(pvo_key, pvo_systemid)

            #use system date/Time for logging. Close enough
            powerdate = time.strftime("%Y%m%d")
            powerTime = time.strftime("%H:%M")
            # parse the results of sm.query above
            PowerGeneration = str(current['PAC'])
            Temperature = str(current['TKK'])
            Voltage = str(current['UL1'])

            print("Date: " + str(powerdate) + " Time: " + str(
                powerTime) + " W: " + PowerGeneration + " temp: " + Temperature + " volt: " + Voltage)

            # update pvoutput
            if (PowerGeneration):  # make sure that we have actual values...
                pvoutz.add_status(powerdate, powerTime, power_exp=PowerGeneration, temp=Temperature, vdc=Voltage)
                print("Sucessful Log ")
                #Ensure API limits adhered to
                time.sleep(apiDelay)
            else:
                print("aint no data bitch.. make the sun come up")

            count += 1
        except:
            print('Communication Error, WR %i' % no)
            continue
#(status, errors) = sm.status(count)

#if errors:
#    print('WR %i: %s (%s)' % (no, status, errors))
#    try:
#        print("details: ", int(PAC), int(TEMP), int(VOLTAGE))
#    except:
#        pass

if count < len(allinverters):
    print('Not all inverters queried (%i < %i)' % (count, len(allinverters)))

print("Data Succesfully query and posted.")
time.sleep(1)

