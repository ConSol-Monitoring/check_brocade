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


import logging
from monplugin import Check,Status
from ..tools import cli
from ..tools.helper import severity,item_filter
from ..tools.connect import broadcomAPI
from pprint import pprint as pp

__cmd__ = "interface-health"
description = f"{__cmd__} interface-health"
"""
"""
def run():
    parser = cli.Parser()
    parser.set_epilog("Check for Interface Health")
    parser.set_description(description)
    parser.add_optional_arguments(cli.Argument.EXCLUDE,
                                  cli.Argument.INCLUDE)
    parser.add_optional_arguments({
        'name_or_flags': ['--ignore-disabled'],
        'options': {
            'action': 'store',
            'help': 'ignore interfaces in disabled state',
        }},
        {
        'name_or_flags': ['--port-type'],
        'options': {
            'action': 'store',
            'default': 'e-port',
            'nargs': '+',
        'help': "list of port-type to check, default is e-port",
        }
    })
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

    logger.debug(f"#-> START") 
    api = broadcomAPI(logger, base_url, args.username, args.password)
    f = api.make_request("GET","rest/running/brocade-interface/fibrechannel")
    """
    operational-status(-string)
    0 : Undefined
    2 : Online
    3 : Offline
    5 : Faulty
    6 : Testing
    """
    port_count = len(f['fibrechannel'])
    admin_state = "enabled" 
    
    for int in f['fibrechannel']:
        # just e-ports are interesting
        if int['port-type-string'] not in args.port_type:
        #if int['port-type'] != 7:
            port_count -= 1
            continue
        
        logline = f"{int['port-type-string']} {int['name']} ({int['user-friendly-name']}) {int['operational-status-string']} {int['operational-status']}"
       
        # Filter out include / exclude and disabled ports 
        if (args.exclude or args.include) and item_filter(args,f"{int['port-type-string']} {int['name']} {int['user-friendly-name']}"): 
            logger.info(f"skip {logline} include / exlude match")
            port_count -= 1
            continue
       
        # port not enabled but ignored 
        if args.ignore_disabled and not int['is-enabled-state']:
            logger.info(f"ignore {logline} it's disabled")
            port_count -= 1
            continue
       
        if not int['is-enabled-state']: admin_state = "disabled"
        
        text = f"{int['port-type-string']} {int['name']:5} {int['user-friendly-name']:20} {admin_state}/{int['operational-status-string']}"
       
        # Check for status    
        if not int['is-enabled-state']:
            check.add_message(Status.WARNING, text)
        # critical if healthy, faulty or offline
        if "healthy" not in int['port-health'] or int['operational-status'] == 5 or int['operational-status'] == 3:
            check.add_message(Status.CRITICAL, text)   
        # warning if undefined or testing
        elif int['operational-status'] == 0 or int['operational-status'] == 6:
            check.add_message(Status.WARNING, text)
        else:
            check.add_message(Status.OK, text) 
    
    (code, message) = check.check_messages(separator="\n")
    if code == Status.OK and port_count == 1:
        check.exit(code=code,message=message)
    elif code == Status.OK:
        check.exit(code=code,message=f"checked {port_count} ports\n{message}")
    else: 
        check.exit(code=code,message=message)

if __name__ == "__main__":
    run()