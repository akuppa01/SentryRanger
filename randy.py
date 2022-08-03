import os
import requests
import json
from pathlib import Path
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

"""
Deletes all the policies in TempFiles from Ranger DB
"""


host = "150.136.204.120:6182"

url =  "https://{}/service/public/v2/api/policy".format(host)

username = "admin"
password = "OracleTeamUSA!123"

headers = {
    'Content-Type': 'application/json',
}

print("check 1")

try:
    files = Path('TempFiles/').glob('*')
    for file in files:
        arr = str(file).split('/')
        policyName = arr[1].replace('.json','')

        params = {
            'servicename': 'kkrkdonotd_hive',
            'policyname': policyName
        }
        output = requests.delete(url, params=params, headers=headers, verify=False, auth=(username, password))
        
        if output.status_code == 204:
            print(policyName + " successfully deleted from Ranger")

except Exception as error:
    print("error")


