SolarmanPV API to PVoutput Logger
=================================
Solarman PV details:
http://www.solarmanpv.com/index_en.html

Solarman PV portal details:
http://www.solarmanpv.com/en-us/solarmanweb.html

Demo account view:
http://www.solarmanpv.com/portal/Terminal/TerminalDefault.aspx

A Python project to take data from the Solarman PV portal API, take the most recent value and log the data to pvoutput.org via their API.
This project could be used by any Solarman PV portal user, all that is needed is the relevant API key which can be obtained from their customer service - customerservice@solarmanpv.com

This project is a fork and modification of the https://github.com/MattCordell/SolarMax_PVoutputLogger project.

Command line usage:

``` bash
usage: ./SolarmanPV-to-PVoutput.py [-h] [-d] [-v] --smpv_client_id
                                   SMPV_CLIENT_ID --smpv_client_secret
                                   SMPV_CLIENT_SECRET --smpv_plant_id
                                   SMPV_PLANT_ID --pvo_key PVO_KEY
                                   --pvo_system_id PVO_SYSTEM_ID

optional arguments:
  -h, --help            show this help message and exit
  -d, --debug           turn on debug output
  -v, --version         show program's version number and exit
  --smpv_client_id SMPV_CLIENT_ID
                        SolarmanPV API client ID
  --smpv_client_secret SMPV_CLIENT_SECRET
                        SolarmanPV API client secret
  --smpv_plant_id SMPV_PLANT_ID
                        ID of the plant (i.e. The solar PV site within
                        SolarmanPV)
  --pvo_key PVO_KEY     PVoutput API key
  --pvo_system_id PVO_SYSTEM_ID
                        PVoutput system ID
```

If you have a Weewx instance, you can include these parameters which will work for the "inverter" version of the script:
``` bash
./SolarmanPV-to-PVoutput-inverter-data.py <AS ABOVE, THEN>
  --weewx_user WEEWX_DB_USER
  --weewx_password WEEWX_DB_PASSWD
  --weewx_host WEEWX_DB_HOST
  --weewx_database WEEWX_DB_NAME
```
