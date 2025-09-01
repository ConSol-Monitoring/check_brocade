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
import json
import re
import os
from typing import Optional, Dict, Any
from checkbrocade import CheckBrocadeConnnectException

requests.packages.urllib3.disable_warnings()


class broadcomAPI:
    def __init__(self, logger, base_url: str, username: str, password: str, sessionfile: Optional[str] = None):
        self.logger = logger
        self.base_url = base_url
        self.username = username
        self.password = password
        self.sessionfile = sessionfile
        self.apiversion: Optional[str] = None

        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            "Accept": "application/yang-data+json",
            "Content-Type": "application/yang-data+json",
        })

        token = self.read_session_id()
        if token:
            self.logger.info(f"Using existing token from {self.sessionfile}")
            self.session.headers["Authorization"] = token
            if not self.verify_token():
                self.logger.warning("Stored token is invalid. Logging in with username/password.")
                self.login_with_password()
        else:
            self.logger.info("No existing token found. Logging in with username/password.")
            self.login_with_password()

        self.logger.debug(f"Session initialized with headers: {self.session.headers}")
        atexit.register(self.cleanup)

    # ---------------------------
    # Session Handling
    # ---------------------------
    def write_session_id(self, token: str):
        if self.sessionfile:
            try:
                with open(self.sessionfile, "w") as f:
                    self.logger.debug(f"Saving session to {self.sessionfile}")
                    f.write(token)
            except Exception as e:
                self.logger.error(f"Failed to write session file: {e}")

    def read_session_id(self) -> Optional[str]:
        if not self.sessionfile:
            return None
        try:
            self.logger.debug(f"Reading session from {self.sessionfile}")
            return open(self.sessionfile).read().strip()
        except FileNotFoundError:
            return None
        except Exception:
            self.logger.exception("Error restoring session")
            return None

    # ---------------------------
    # Token Verification & Login
    # ---------------------------
    def verify_token(self) -> bool:
        status_url = f"{self.base_url}/rest/running/brocade-chassis/chassis"
        self.logger.info("Verifying token")
        try:
            response = self.session.get(status_url, timeout=(5, 5))
            self.logger.debug(f"Verify URL {status_url} response with {response.status_code}")
            self.apiversion = response.headers.get("Content-Type")

            if response.status_code == 200:
                return True
            elif response.status_code in (401, 403):
                self.logger.warning("Stored token invalid or expired. Re-login required.")
                self.login_with_password()
                response = self.session.get(status_url, timeout=(5, 5))
                self.logger.debug(f"Verify after re-login response: {response.status_code}")
                return response.status_code == 200
            else:
                self.logger.warning(f"Unexpected status code {response.status_code} in verify_token()")
        except requests.RequestException as e:
            self.logger.error(f"Error verifying token: {e}")
        return False

    def login_with_password(self):
        self.logger.info(f"Login with user/password to {self.base_url}")
        login_url = f"{self.base_url}/rest/login"
        try:
            response = self.session.post(login_url, auth=(self.username, self.password), timeout=(5, 5))
            response.raise_for_status()
        except requests.RequestException as e:
            self.logger.error(f"Login request failed: {e}")
            raise

        token = response.headers.get("Authorization")
        self.apiversion = response.headers.get("Content-Type")

        if token:
            self.logger.info("Password login successful")
            if self.sessionfile:
                self.write_session_id(token)
            self.session.headers["Authorization"] = token
            self.logger.debug(
                f"For manual logout use:\ncurl -kv -X POST -H 'Authorization: {token}' "
                f"-H 'Accept: application/yang-data+json' '{self.base_url}/rest/logout'"
            )
        else:
            self.logger.error(f"Login failure {response.status_code}")

    # ---------------------------
    # Logout & Cleanup
    # ---------------------------
    def logout(self):
        self.logger.info("Logging out...")
        logout_url = f"{self.base_url}/rest/logout"
        try:
            response = self.session.post(logout_url)
            if response.status_code == 204:
                self.logger.info("Logout successful")
                if self.sessionfile and os.path.exists(self.sessionfile):
                    os.remove(self.sessionfile)
            else:
                self.logger.warning(f"Logout failed with status: {response.status_code}")
        except requests.RequestException as e:
            self.logger.error(f"Logout request failed: {e}")
        finally:
            self.session.close()

    def cleanup(self):
        if self.session:
            self.logger.info("Closing session")
            self.session.close()

    # ---------------------------
    # Requests with Automatic Retry
    # ---------------------------
    def make_request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None,
                     params: Optional[Dict[str, Any]] = None):
        url = f"{self.base_url}/{endpoint}"
        self.logger.info(f"Making {method} request to {url}")

        for attempt in range(2):  # max 2 attempts
            try:
                response = self.session.request(method, url, json=data, params=params)

                if response.status_code == 400:
                    self.logger.error(f"Bad request (400) to {url}. Aborting.")
                    response.raise_for_status()

                if response.status_code in (401, 403):
                    self.logger.warning("Unauthorized (401/403). Verifying token and re-login if needed...")
                    if not self.verify_token():
                        self.logger.error("Re-login failed during request retry.")
                        self.logout()
                        response.raise_for_status()
                    continue  # retry after re-login

                response.raise_for_status()
                r_dict = response.json()
                self.logger.debug(f"{json.dumps(r_dict, indent=4, sort_keys=True)}")
                return r_dict.get("Response")

            except requests.RequestException as e:
                self.logger.error(f"Request to {url} failed: {e}")
                if attempt == 1:
                    self.logout()
                    raise
            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error: {e}")
                raise

    # ---------------------------
    # Version Mapping
    # ---------------------------
    def version(self, fabric: bool = False) -> str:
        FabricOS = {
            "1.30.0": "8.2.1b",
            "1.40.0": "9.0.1",
            "1.50.0": "9.1.0b",
            "1.60.0": "9.1.1",
            "2.0.0": "9.2.1",
            "2.0.1": "9.2.1b",
        }
        match = re.search(r"^.*version=(.*)$", str(self.apiversion))
        if match:
            version = match.group(1)
            return FabricOS.get(version, version) if fabric else version
        return "unknown"

