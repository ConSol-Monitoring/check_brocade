#    Copyright (C) 2023  ConSol Consulting & Solutions Software GmbH
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.

import requests
import atexit
import logging,sys,traceback
from checkbrocade import CheckBrocadeConnnectException
import json
from pprint import pprint as pp

#from http.client import HTTPConnection  # py3

requests.packages.urllib3.disable_warnings()

#print statements from `http.client.HTTPConnection` to console/stdout
#HTTPConnection.debuglevel = 1

class broadcomAPI():
    def __init__(self, logger, base_url, username, password):
        self.logger = logger
        self.base_url = base_url
        self.username = username
        self.password = password
        self.headers = ({
            'Accept': 'application/yang-data+json',
            'Content-Type': 'application/yang-data+json',
        })
        self.verify = False
        self.headers['Authorization'] = self.login()
        logger.debug(f"#---> init header : {self.headers}")
        self.session = requests.Session()
        self.session.verify = self.verify
        self.session.headers.update(self.headers)
        logger.debug(f"session header {self.session.headers}")
    
    def login(self):
        """
        There is no respones body when requesting login URL
        """
        self.logger.info(f"try login to {self.base_url}")
        login_url = f"{self.base_url}/rest/login" 
        try:
            response = requests.post(login_url, headers=self.headers, auth=(self.username, self.password),verify=self.verify)
            CustomBasic = response.headers.get("Authorization")
            if response.status_code == 200:
                self.logger.info(f"Login successfull {response.status_code}")
                #self.logger.debug(f"Response header: {response.headers}")
                atexit.register(broadcomAPI.logout, self)
                self.logger.debug(f'curl -v -X POST -H "Authorization: Custom_Basic {CustomBasic}" -H "Accept: application/yang-data+json" "{self.base_url}/rest/logout"')
                return CustomBasic
            elif response.status_code == 403:
                self.logger.error(f"{response.reason}")
                raise CheckBrocadeConnnectException
            # gschmarre hier müssen noch die anderen 400er rein
            #else:
            #    self.logger.error(f"received {response.status_code}")
            #    raise CheckBrocadeConnnectException
        except requests.exceptions.HTTPError as errh:
            self.logger.error(f"HTTP Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            self.logger.error(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            self.logger.error(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            self.logger.error(f"Error: {err}")
            
    def logout(self):
        self.logger.info("logout")
        logout_url = f"{self.base_url}/rest/logout"
        try:
            response = self.session.post(logout_url )
            self.logger.debug(f"{response.status_code}")
            self.logger.debug(f"{response.headers}")
            response.raise_for_status()
            if response.status_code == 204:
                self.logger.info("logout successfully")
                
            self.session.close()
        except requests.exceptions.HTTPError as errh:
            self.logger.error(f"HTTP Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            self.logger.error(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            self.logger.error(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            self.logger.error(f"Error: {err}")
        
    def make_request(self, method, endpoint, data=None, params=None):
        url = f"{self.base_url}/{endpoint}"
        self.logger.info(f"make {method} request to {url}")
        try:
            response = self.session.request(method, url, json=data, params=params)
            response.raise_for_status()
            r_dict = response.json()
            self.logger.debug(f"{json.dumps(r_dict, indent=4, sort_keys=True)}") 
            #self.logger.debug(f"{r_dict}")
            return r_dict['Response']
        except requests.exceptions.HTTPError as errh:
            print(f"HTTP Error: {errh}")
        except requests.exceptions.ConnectionError as errc:
            print(f"Error Connecting: {errc}")
        except requests.exceptions.Timeout as errt:
            print(f"Timeout Error: {errt}")
        except requests.exceptions.RequestException as err:
            print(f"Error: {err}")