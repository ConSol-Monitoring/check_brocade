#!/usr/bin/env python3

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


from dataclasses import fields
import logging
from monplugin import Check,Status
#from netapp_ontap.resources import Software
#from netapp_ontap.error import NetAppRestError
from ..tools import cli
from ..tools.helper import severity
from ..tools.connect import broadcomAPI
from pprint import pprint as pp

__cmd__ = "about"
description = f"{__cmd__} need just connection settings and show up the brocade version"
"""
{'Response':
    {'chassis': 
        {'chassis-user-friendly-name': 'BrocadeG620', 
        'license-id': '10:00:88:94:71:ce:bb:7a', 
        'chassis-wwn': '10:00:88:94:71:ce:bb:b9', 
        'serial-number': 'EWY1929Q06S', 
        'entitlement-serial-number': 'EWY1929Q06S', 
        'manufacturer': 'Brocade Communications Systems LLC', 
        'part-number': '40-1001274-01',
        'vf-enabled': False,
        'vf-supported': True, 
        'fcr-enabled': False, 
        'fcr-supported': True, 
        'max-blades-supported': 1,
        'vendor-revision-number': '', 
        'vendor-part-number': 'BROCAD0000G62', 
        'vendor-serial-number': 'CZC929NKVM', 
        'product-name': 'g620', 
        'chassis-enabled': True, 
        'shell-timeout': 60,
        'session-timeout': 0,
        'message-of-the-day': '',
        'date': '11/27/2023-16:45:46', 
        'usb-device-enabled': False, 
        'usb-available-space': 0,
        'tcp-timeout-level': 5}}}
"""
def run():
    parser = cli.Parser()
    parser.set_epilog("Connect to brocade API and check Software version")
    parser.set_description(description)
    args = parser.get_args()

    # Setup module logging 
    logger = logging.getLogger(__name__)
    logger.disabled=True
    if args.verbose:
        for log_name, log_obj in logging.Logger.manager.loggerDict.items():
            log_obj.disabled = False
            logging.getLogger(log_name).setLevel(severity(args.verbose))

    base_url = f"https://{args.host}:{args.port}"
    
    check = Check()

    pp(args)   
    logger.debug(f"#-> START") 
    api = broadcomAPI(logger, base_url, args.username, args.password)
    response_data = api.make_request("GET", "rest/running/brocade-chassis/chassis")
    print(response_data) 
    
    (code, message) = check.check_messages(separator="\n")
    check.exit(code=code,message=message)

if __name__ == "__main__":
    run()