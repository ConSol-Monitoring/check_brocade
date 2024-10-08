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
import re

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
        self.headers['Authorization'], self.apiversion = self.login()
        self.logger.debug(f"#---> init header : {self.headers}")
        self.session = requests.Session()
        self.session.verify = self.verify
        self.session.headers.update(self.headers)
        self.logger.debug(f"full session object {self.session}")
    
    def login(self):
        """
        There is no respones body when requesting login URL
        """
        self.logger.info(f"try login to {self.base_url}")
        login_url = f"{self.base_url}/rest/login" 
        response = requests.post(login_url, headers=self.headers, auth=(self.username, self.password),verify=self.verify, timeout=(5,5))
        if not response.ok:
            self.logger.error(f"requests response not ok")
        response.raise_for_status()
        CustomBasic = response.headers.get("Authorization")
        ApiVersion = response.headers.get("Content-Type")
        if response.status_code == 200:
            self.logger.info(f"Login successfull {response.status_code}")
            atexit.register(broadcomAPI.logout, self)
            self.logger.debug(f'for manual logout please use curl \n curl -kv -X POST -H "Authorization: Custom_Basic {CustomBasic}" -H "Accept: application/yang-data+json" "{self.base_url}/rest/logout"')
            return CustomBasic, ApiVersion
        else:
            self.logger.error(f"Login failure {response.status_code}") 
        
    def logout(self):
        self.logger.info("logout")
        logout_url = f"{self.base_url}/rest/logout"
        response = self.session.post(logout_url )
        self.logger.debug(f"{response.status_code}")
        self.logger.debug(f"{response.headers}")
        response.raise_for_status()
        if response.status_code == 204:
            self.logger.info("logout successfully")
                
        self.session.close()
        
    def make_request(self, method, endpoint, data=None, params=None):
        url = f"{self.base_url}/{endpoint}"
        self.logger.info(f"make {method} request to {url}")
        response = self.session.request(method, url, json=data, params=params)
        response.raise_for_status()
        r_dict = response.json()
        self.logger.debug(f"{json.dumps(r_dict, indent=4, sort_keys=True)}") 
        #self.logger.debug(f"{r_dict}")
        return r_dict['Response']

    def version(self,fabric=False):
        """
        https://techdocs.broadcom.com/us/en/fibre-channel-networking/fabric-os/fabric-os-rest-api/9-2-x/v26395730/v25026650.html
        The resource API version for Fabric OS 9.2.1 is 2.0.0
        The resource API version for Fabric OS 9.1.1 is 1.60.0 (major.minor.patch)
        The resource API version for Fabric OS 9.1.0b is 1.50.0. 
        The resource API version for Fabric OS 9.0.1 is 1.40.0. 
        The resource API version for Fabric OS 9.0.0a is 1.40.0. 
        The resource API version for Fabric OS 8.2.1b is 1.30.0.
        """
        FabricOS = {
            "1.30.0": "8.2.1b",
            "1.40.0": "9.0.1",
            "1.50.0": "9.1.0b",
            "1.60.0": "9.1.1",
            "2.0.0": "9.2.1"
        }
        match = re.search(r'^.*version=(.*)$', self.apiversion)
        if match:
            if fabric:
                version = FabricOS[match.group(1)]
            else:
                version = match.group(1)
        else:
            version = "unknown"
        return version