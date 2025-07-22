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
import re
from monplugin import Check,Status
from ..tools import cli
from ..tools.helper import severity,item_filter,compare_versions
from ..tools.connect import broadcomAPI

__cmd__ = "interface-health"
description = f"{__cmd__} interface-health"
"""
"""
logger = None
args = None

def run():
    global logger
    global args
    parser = cli.Parser()
    parser.set_epilog("Check for Interface Health")
    parser.set_description(description)
    parser.add_optional_arguments(cli.Argument.EXCLUDE,
                                  cli.Argument.INCLUDE)
    
    parser.add_optional_arguments({
        'name_or_flags': ['--ignore-disabled'],
        'options': {
            'action': 'store_true',
            'help': 'ignore interfaces in disabled state',
        }},
        {
        'name_or_flags': ['--port-type'],
        'options': {
            'action': 'store',
            'default': ['e-port'],
            'nargs': '+',
            'help': "list of port-type to check, default is e-port. Can also be 'all'",
        }},
        {
        'name_or_flags': ['--show-all'],
        'options': {
            'action': 'store_true',
            'help': 'show all interfaces',
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

    check = Check()
    try:
        plugin(check)
    except Exception as e:
        logger.error(f"{e}")
        check.exit(Status.UNKNOWN, f"{e}")

def plugin(check):
    base_url = f"https://{args.host}:{args.port}"
    api = broadcomAPI(logger, base_url, args.username, args.password, args.sessionfile)
    virtual_fabrics = {}
    c = api.make_request("GET", "rest/running/brocade-chassis/chassis")
    chassis = c['chassis']
    
    # check if it's a director
    if re.search(r'^x\d', chassis['product-name'].lower()) and 'dcx' in chassis['vendor-part-number'].lower():
        logger.info(f"chassis is a brocade director with name: {chassis['product-name']} / part-number: {chassis['vendor-part-number']}")
        isDirector = True
    else: 
        isDirector = False
       
    # check vf enabled and in use
    if 'vf-enabled' in chassis and chassis['vf-enabled']:
        logger.info(f"VF Found checking for IDs")
        s = api.make_request("GET","rest/running/brocade-fibrechannel-logical-switch/fibrechannel-logical-switch")
        # which vfs have ports
        for vf in s['fibrechannel-logical-switch']:
            if len(vf['port-index-members']) != 0:
                logger.info(f"get fibrechannels for virtual fabric {vf['fabric-id']}")
                f = api.make_request("GET",f"rest/running/brocade-interface/fibrechannel?vf-id={vf['fabric-id']}")
                virtual_fabrics[str(vf['fabric-id'])] = f['fibrechannel']
            else:
                logger.debug(f"Fabric-ID {vf['fabric-id']} has no ports")
    else:
        logger.info(f"NO VF go ahead")
        f = api.make_request("GET","rest/running/brocade-interface/fibrechannel")
        virtual_fabrics['novf']= f['fibrechannel']

    ## first try of director didn't respond with trunk info 
    ##t = api.make_request("GET","rest/running/brocade-fibrechannel-trunk/trunk-area/")
    
    """
    operational-status(-string)
    0 : Undefined
    2 : Online
    3 : Offline
    5 : Faulty
    6 : Testing
    """
    porttype = {
        0 : "unknown",
        7 : "e-port",
        10: "g-port",
        11: "u-port",
        15: "f-port",
        16: "l-port",
        17: "fcoe-port",
        19: "ex-port",
        20: "d-port",
        21: "sim-port",
        22: "af-port",
        23: "ae-port",
        25: "ve-port",
        26: "ethernet-flex-port",
        29: "flex-port",
        30: "n-port",
        31: "mirror-port",
        32: "icl-port",
        33: "fc-lag-port",
        32768: "lb-port,"
    }
    operstate = {
        0: "Undefined",
        2: "Online",
        3: "Offline",
        5: "Faulty",
        6: "Testing",
    }
    """
    seems to be implemented in FabricOS > 9.0.0
    operstate = {
        0: "null,",
        1: "offline,",
        2: "online,",
        3: "online warning,",
        4: "disabled,",
        5: "degraded,",
        6: "initializing,",
        7: "delete pending,",
        8: "ha online,",
        9: "ha offline,",
        10: "ha ready,",
        11: "empty,",
        12: "in progress,",
        13: "misconfig,",
        14: "failover,",
        15: "down pending,",
        16: "circuit disabled/fenced/testing,",
        17: "internal error,",
        18: "ipsec error,",
        19: "network error,",
        20: "authentication error,",
        21: "timeout,",
        22: "tcp-timeout,",
        23: "remote close timeout,",
        24: "remote close,",
        25: "rejected,",
        26: "no port,",
        27: "no route,",
        28: "dp offline,",
        29: "hcl inprogress,",
        30: "internal error,",
        31: "configuration incomplete,",
        32: "circuit fenced,",
        33: "child delete complete,",
        34: "delete failure,",
        35: "spill over,",
        36: "running,",
        37: "testing,",
        38: "aborted,",
        39: "passed,",
        40: "failed",
    } 
    """
    supported_version = compare_versions("9.1.0", api.version(True))
    port_count = 0
    for vf,fibrechannel in virtual_fabrics.items(): 
        if 'novf' in vf: 
            VF = ""
        else:
            VF = f"VF {vf:3} "
            
        port_count += len(fibrechannel)    
        
        for intf in fibrechannel:
            if supported_version:
                ifType = intf['port-type-string'] 
                oper_state = intf['operational-status-string']
            else:
                ifType = porttype[intf['port-type']]
                oper_state = operstate[intf['operational-status']]
              
            # as directors have just icl ports  
            if isDirector:
                if 'icl-port' in ifType and 'e-port' in intf['port-scn']:
                    ifType = "icl-port (trunk master)"
                elif 'icl-port' in ifType and 't-port' in intf['port-scn']:
                    ifType = "icl-port (trunk slave)"
                args.port_type.append('icl')
                
                
            admin_state = "enabled" 
            logline = f"{VF}{ifType} {intf['name']} ({intf['user-friendly-name']}) {admin_state} {intf['is-enabled-state']} / {oper_state} {intf['operational-status']}"
            # Show all interfaces
            if args.show_all:
                print(logline) 
                continue
            
            # just e-ports are interesting
            if 'all' in args.port_type:
                pass
            if not any(re.search(rf'^{re.escape(port)}', ifType, re.IGNORECASE) for port in args.port_type):
                logger.info(f"skip {logline} port not int white list")
                port_count -= 1
                continue
            
            # Filter out include / exclude and disabled ports 
            if (args.exclude or args.include) and item_filter(args,f"{ifType} {intf['name']} {intf['user-friendly-name']}"): 
                logger.info(f"skip {logline} include / exlude match")
                port_count -= 1
                continue
           
            # port not enabled but ignored 
            if args.ignore_disabled and not intf['is-enabled-state']:
                logger.info(f"ignore {logline} it's disabled")
                port_count -= 1
                continue
           
            if not intf['is-enabled-state']: admin_state = "disabled"
            
            logger.info(f"check {logline}")
            if supported_version:
                text = f"{VF}{ifType} {intf['name']:5} {intf['user-friendly-name']:23} {admin_state}/{oper_state} {intf['port-health']}"
            else:
                text = f"{VF}{ifType} {intf['name']:5} {intf['user-friendly-name']:23} {admin_state}/{oper_state}"

            # Check for status
            if not intf['is-enabled-state']:
                check.add_message(Status.WARNING, text)
            # critical if healthy, faulty or offline
            # port-health seems to be just an informal field
            #if supported_version and "healthy" not in intf['port-health']:
            #    check.add_message(Status.CRITICAL, f"{VF}{ifType} {intf['name']:5} {intf['user-friendly-name']:23} {intf['port-health']}")
            if intf['operational-status'] == 5 or intf['operational-status'] == 3:
                check.add_message(Status.CRITICAL, text)   
            # warning if undefined or testing
            elif intf['operational-status'] == 0 or intf['operational-status'] == 6:
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
