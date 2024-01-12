#
# Extract data from cgi-day call to myenergi server
# Chris Horne 04/12/2022
#

import requests
import json
import datetime
from requests.auth import HTTPDigestAuth
import numpy as np
import getpass 
from calendar import monthrange

def extract_values(obj, key):
	"""Pull all values of specified key from nested JSON."""
	arr = []
	def extract(obj, arr, key):        
		"""Recursively search for values of key in JSON tree."""
		if isinstance(obj, dict):
			v1 = 0 
			for k, v in obj.items():
				if isinstance(v, (dict, list)):
					extract(v, arr, key)
				elif k == key:
					v1 = v	
			arr.append(v1)
		elif isinstance(obj, list):
			for item in obj:
				extract(item, arr, key)
		return arr

	results = extract(obj, arr, key)
	return results


server="s18"

# Ask user for details of their hub, zappi etc
username = input("Username/Hub Serial Number: ")
password = getpass.getpass("Password: ")
ID=input("Device (include Z or E + serial number: ")
year=input("Year: ")
first_month=input("First Month: ")
last_month=input("Last Month: ")

for month in range(int(first_month),int(last_month)+1):
	N_days=monthrange(int(year),int(month))
	days=str(N_days[1])
	print(str(year) + "/" + str(month).zfill(2))
	print("Days to process: " + days)


	filename="Energy_Data_"+ID+"_"+year+"-"+str(month).zfill(2)+".csv"
	print("Saving to: " + filename)

	fo = open(filename,"w")
	fo.write("Date,Import (kWh),Export (kWh), Generation (kWh), Zappi Energy (kWh), Self Consumption (kWh), Total Property Usage (kWh), Green Percentage\n")

	for this_day in range(int(days)):
		day=this_day+1
		url = 'https://' + server + '.myenergi.net/cgi-jday-' + ID + '-' + str(year) + '-' + str(month) + '-' + str(day)

		print(url)
		headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
		r = requests.get(url, auth=HTTPDigestAuth(username,password), headers=headers, timeout=20)

		daily_import=0;
		daily_export=0;
		daily_generation=0;
		daily_EV=0;

		if r.status_code == 200:
			if ID[0] == 'Z':
				print ('*** Success - Zappi ***')
				data=json.loads(r.content)
				y_import = np.array(extract_values(r.json(),'imp'))/(60*1000)
				y_gep = np.array(extract_values(r.json(),'gep'))/(60*1000)
				y_exp = np.array(extract_values(r.json(),'exp'))/(60*1000)
				y_z1 = np.array(extract_values(r.json(),'h1d'))/(60*1000)
				y_z2 = np.array(extract_values(r.json(),'h2d'))/(60*1000)
				y_z3 = np.array(extract_values(r.json(),'h3d'))/(60*1000)
				y_z1b = np.array(extract_values(r.json(),'h1b'))/(60*1000)
				y_z2b = np.array(extract_values(r.json(),'h2b'))/(60*1000)
				y_z3b = np.array(extract_values(r.json(),'h3b'))/(60*1000)
				y_zappi = y_z1 + y_z2 + y_z3 + y_z1b + y_z2b + y_z3b
					
				daily_generation=sum(y_gep)/60
				daily_import=sum(y_import)/60
				daily_export=sum(y_exp)/60
				daily_EV=sum(y_zappi)/60
				
				daily_self_consumption = daily_generation-daily_export
				daily_property_usage=daily_import+daily_self_consumption
				daily_green_percentage = (daily_self_consumption / daily_property_usage)*100
					
				print(f'{day}/{month}/{year},{daily_import:.2f},{daily_export:.2f},{daily_generation:.2f},{daily_EV:.2f},{daily_self_consumption:.2f},{daily_property_usage:.2f},{daily_green_percentage:.1f},{len(y_zappi)-1}')
				fo.write(f'{day}/{month}/{year},{daily_import:.2f},{daily_export:.2f},{daily_generation:.2f},{daily_EV:.2f},{daily_self_consumption:.2f},{daily_property_usage:.2f},{daily_green_percentage:.1f},{len(y_zappi)-1}\n')
				
							
			else:
				print ('*** Success - Eddi ***')
				data=json.loads(r.content)
				y_import = np.array(extract_values(r.json(),'imp'))/(60*1000)
				y_gep = np.array(extract_values(r.json(),'gep'))/(60*1000)
				y_exp = np.array(extract_values(r.json(),'exp'))/(60*1000)
				y_h1b=np.array(extract_values(r.json(),'h1b'))/(60*1000)
				y_h1d=np.array(extract_values(r.json(),'h1d'))/(60*1000)
				y_h2b=np.array(extract_values(r.json(),'h2b'))/(60*1000)
				y_h2d=np.array(extract_values(r.json(),'h2d'))/(60*1000)
				y_eddi=y_h1b+y_h1d+y_h2b+y_h2d
				
				daily_generation=sum(y_gep)/60
				daily_import=sum(y_import)/60
				daily_export=sum(y_exp)/60
				daily_Eddi=sum(y_eddi)/60
				
				daily_self_consumption = daily_generation-daily_export
				daily_property_usage=daily_import+daily_self_consumption
				daily_green_percentage = (daily_self_consumption / daily_property_usage)*100
				
				print(f'{day}/{month}/{year},{daily_import:.2f},{daily_export:.2f},{daily_generation:.2f},{daily_Eddi:.2f},{len(y_eddi)},{daily_self_consumption:.2f},{daily_property_usage:.2f},{daily_green_percentage:.1f},{len(y_eddi)-1}')
				fo.write(f'{day}/{month}/{year},{daily_import:.2f},{daily_export:.2f},{daily_generation:.2f},{daily_Eddi:.2f},{daily_self_consumption:.2f},{daily_property_usage:.2f},{daily_green_percentage:.1f},{len(y_eddi)}\n')
				
		else:
			print ("Failed to read ticket, errors are displayed below,")
			response = json.loads(r.content)
			print(response["errors"])

			print("x-request-id : " + r.headers['x-request-id'])
			print("Status Code : " + r.status_code)
			
	fo.close()
			
#fo.close()