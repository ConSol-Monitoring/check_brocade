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
from checkbrocade import CheckBrocadeConnnectException
import json
import re
import os
from urllib.parse import urlparse
from pprint import pprint as pp

#from http.client import HTTPConnection  # py3

requests.packages.urllib3.disable_warnings()

#print statements from `http.client.HTTPConnection` to console/stdout
#HTTPConnection.debuglevel = 1

class broadcomAPI():
    def __init__(self, logger, base_url, username, password, sessionfile=None):
        self.logger = logger
        self.base_url = base_url
        self.username = username
        self.password = password
        self.sessionfile = sessionfile
        
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'Accept': 'application/yang-data+json',
            'Content-Type': 'application/yang-data+json',
        })
        # check for sessionid 
        token = self.read_session_id()
        if token:
            self.logger.info(f"using existing token from {self.sessionfile}")
            self.session.headers['Authorization'] = token
            if not self.verify_token():
                self.logger.warning("Stored token is invalid. Logging in with username/password.")
                self.login_password()
        else: 
            self.logger.info("No existing token found. Logging in with username/password.")
            self.login_password()
            
        self.logger.debug(f"Session initialized with headers: {self.session.headers}")
        # close session at exit
        atexit.register(self.cleanup)   
   
    def write_session_id(self, token):
        with open(self.sessionfile, "w") as s:
            self.logger.debug(f'saving session to {self.sessionfile}')
            s.write(token)

    def read_session_id(self):
        if not self.sessionfile:
            return None
        try:
            self.logger.debug(f'read session from {self.sessionfile}')
            return open(self.sessionfile).read()
        except FileNotFoundError:
            return None
        except:
            self.logger.exception("Error restoring session")
            return None
    
    def verify_token(self):
        # verify saved token. As there is no proper status endpoint use .../login
        status_url = f"{self.base_url}/rest/running/brocade-chassis/chassis"
        self.logger.info("verify token")
        try:
            response = self.session.get(status_url, timeout=(5, 5))
            self.logger.debug(f"verify url {status_url} response with {response.status_code}")
            self.apiversion = response.headers.get("Content-Type")
            if response.status_code == 200:
                return True
            elif response.status_code == 403 or response.status_code == 401:
                return False
            self.logger.warning(f"Unexpected status code {response.status_code} in verify_token()")
        except requests.RequestException as e:
            self.logger.error(f"Error verifying token: {e}")
        return False

        
    def login_password(self):
        # There is no respones body when requesting login URL
        self.logger.info(f"Login with user and pw to {self.base_url}")
        login_url = f"{self.base_url}/rest/login" 
        response = self.session.post(login_url, auth=(self.username, self.password), timeout=(5,5))
        
        if not response.ok:
            self.logger.error(f"requests response not ok")
            response.raise_for_status()
            
        token = response.headers.get("Authorization")
        self.apiversion = response.headers.get("Content-Type")
       
        if token:
            self.logger.info("Password login successful") 
            if self.sessionfile:
                self.write_session_id(token)
            self.session.headers['Authorization'] = token
            self.logger.debug(f'for manual logout please use curl \ncurl -kv -X POST -H "Authorization: {token}" -H "Accept: application/yang-data+json" "{self.base_url}/rest/logout"')
        else:
            self.logger.error(f"Login failure {response.status_code}") 
        
    def logout(self):
        # logout delete token and session on remote device
        self.logger.info("Logging out...")
        logout_url = f"{self.base_url}/rest/logout"
        response = self.session.post(logout_url )
        try:
            response = self.session.post(logout_url)
            if response.status_code == 204:
                self.logger.info("logout successfully")
                os.remove(self.sessionfile)
            else:
                self.logger.warning(f"Logout failed with status: {response.status_code}")
        except requests.RequestException as e:
            self.logger.error(f"Logout requests failed: {e}")
            
        self.session.close()
        
    def make_request(self, method, endpoint, data=None, params=None):
        url = f"{self.base_url}/{endpoint}"
        self.logger.info(f"Make {method} request to {url}")
        try:
            response = self.session.request(method, url, json=data, params=params)
            response.raise_for_status()
            r_dict = response.json()
            self.logger.debug(f"{json.dumps(r_dict, indent=4, sort_keys=True)}") 
            return r_dict['Response']
        except requests.RequestException as e:
            self.logger.error(f"Request to {url} failed: {e}")
            self.logout()
            raise

    def cleanup(self):
        # close session
        if self.session:
            self.logger.info("Closing session")
            self.session.close()

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
            "2.0.0": "9.2.1",
            "2.0.1": "9.2.1b",
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