#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from pprint import pprint as pp
import logging
from http.client import HTTPConnection  # py3

requests.packages.urllib3.disable_warnings()

log = logging.getLogger('urllib3')
log.setLevel(logging.DEBUG)

# logging from urllib3 to console
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
log.addHandler(ch)

# print statements from `http.client.HTTPConnection` to console/stdout
HTTPConnection.debuglevel = 1


class broadcomAPI():
    def __init__(self, base_url, username, password):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.headers = ({
            'Accept': 'application/yang-data+json',
            'Content-Type': 'application/yang-data+json',
        })
        self.verify = False
        
    def __enter__(self):
        self.login()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        self.logout() 
        
    def login(self):
        login_url = f"{self.base_url}/rest/login" 
        # 
        try:
            response = requests.post(login_url, headers=self.headers, auth=(self.username, self.password),verify=self.verify)
            #response.raise_for_status()
            pp(response.status_code)
            if response.status_code == '200':
                pp("###########")
                self.headers['Authorization'] = response.headers.get("Authorization")
                print("Anmeldung erfolgreich")
                self.session = requests.Session()
                self.session.headers.update(self.headers)
                
        except requests.exceptions.HTTPError as errh:
            print(f"HTTP Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            print(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            print(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            print(f"Error: {err}")
        return self
            
    def logout(self):
        pp("LOGOUT HEADER-------")
        pp(self.session.headers)
        logout_url = f"{self.base_url}/rest/logout"
        try:
            response = self.session.post(logout_url, verify=self.verify)
            pp(response.status_code)
            pp(response.headers)
            response.raise_for_status()
            print("Abmeldung erfolgreich")
        except Exception as e:
            pp(f"#----> {e}")
        self.session.close()
        #except requests.exceptions.HTTPError as errh:
        #    print(f"HTTP Error: {errh}")
        #except requests.exceptions.ConnectionError as errc:
        #    print(f"Error Connecting: {errc}")
        #except requests.exceptions.Timeout as errt:
        #    print(f"Timeout Error: {errt}")
        #except requests.exceptions.RequestException as err:
        #    print(f"Error: {err}")
        
    def Headers(self):
        header = {
            'Accept': 'application/yang-data+json',
            'Content-Type': 'application/yang-data+json',
        }
        return header
        
    def apiGet(self,url):
        r = self.session.get(url, headers=self.Headers())
        r.rais_for_status()
        return (r.status_code, r.json())
    


    def make_request(self, method, endpoint, data=None, params=None):
        pp("MAKE REQUEST ----------")
        pp(self.session.headers)
        url = f"{self.base_url}/{endpoint}"

        try:
            response = self.session.request(method, url, json=data, params=params, verify=self.verify)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as errh:
            print(f"HTTP Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            print(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            print(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            print(f"Error: {err}")
            
# Beispiel-Nutzung der Klasse
base_url = "https://localhost:8899"
username = 'ads\\nagios-monitor'
password = 'YA4HCi_Paieob2!'

with broadcomAPI(base_url, username, password) as api_client:
    # Beispiel für eine GET-Anfrage
    response_data = api_client.make_request("GET", "rest/running/brocade-chassis/chassis")
    print(response_data)
#response_data = api_client.make_request("POST", "rest/logout")
#print(response_data)

