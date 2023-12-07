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
from ..tools.helper import severity
from ..tools.connect import broadcomAPI

__cmd__ = "hardware-health"
description = f"{__cmd__} checks for hardware health state of Blade, Fan, Temperature and Power-Supplies"
"""
"""
logger = None
args = None
def run():
    global logger
    global args
    parser = cli.Parser()
    parser.set_epilog("Check for health of Blade, Fan, Temperature and Powersupplies")
    parser.set_description(description)
    parser.add_optional_arguments(cli.Argument.PERFDATA) 
    parser.add_optional_arguments({
        'name_or_flags': ['--type'],
        'options': {
            'action': 'store',
            'nargs': '+',
            'help': 'List of available sensor types (separated by space):\nblade fan power temp',
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
    if not args.type:
        sType = ['blade','fan','power','temp']
    else:
        sType = args.type
        
    logger.debug(f"begin {__cmd__}") 
    api = broadcomAPI(logger, base_url, args.username, args.password)
    
    summary = ""
    
    if 'blade' in sType:
        b = api.make_request("GET", "rest/running/brocade-fru/blade")
        for blade in b['blade']:
            text = f"{blade['blade-type']} on slot {blade['slot-number']} is {blade['blade-state']}"
            if 'enabled' in blade['blade-state']:
                check.add_message(Status.OK, text)
            else:
                check.add_message(Status.CRITICAL, text)
        summary += f"{len(b['blade'])} Blades "
   
    # no usabel respones for wwn query 
    if 'wwn' in sType:
        pass
        w = api.make_request("GET", "rest/running/brocade-fru/wwn")
   
    # also no sensfull data at this time    
    if 'history' in sType:
        pass
        h = api.make_request("GET", "rest/running/brocade-fru/history-log")
        
    if 'fan' in sType:
        f = api.make_request("GET", "rest/running/brocade-fru/fan")
        for fan in f['fan']:
            text = f"Fan unit {fan['unit-number']} is {fan['operational-state']}"
            if 'ok' in fan['operational-state']:
                check.add_message(Status.OK, text)
            else:
                check.add_message(Status.CRITICAL, text)
            if args.perfdata:
                perfData = {'label': f"fan_{fan['unit-number']}_speed", 'value': f"{fan['speed']}", 'uom': "rpm"}
                check.add_perfdata(**perfData)
        summary += f"{len(f['fan'])} Fans "
        
    if 'power' in sType:
        p = api.make_request("GET", "rest/running/brocade-fru/power-supply")
        for power in p['power-supply']:
            text = f"power-supply {power['unit-number']} is {power['operational-state']}"
            if 'ok' in power['operational-state']:
                check.add_message(Status.OK, text)
            else:
                check.add_message(Status.CRITICAL, text)
            if args.perfdata:
                if power['input-voltage'] != -1:
                    perfData = {'label': f"power-supply_{power['unit-number']}_input", 'value': f"{power['input-voltage']}", 'uom': "V"}
                    check.add_perfdata(**perfData)
                if power['temperature-sensor-supported'] and 'temp' in sType:
                    perfDataTemp = {'label': f"temperatur_power-supply_{power['unit-number']}", 'value': f"{power['temperature']}", 'uom': "C"}
                    check.add_perfdata(**perfDataTemp)
        summary += f"{len(p['power-supply'])} power-supplies "
        
    if 'temp' in sType:
        t = api.make_request("GET", "rest/running/brocade-fru/sensor")
        for sensor in t['sensor']:
            if 'ok' not in sensor['state']:
                check.add_message(Status.WARNING, f"Sensor {sensor['category']} {sensor['id']} is {sensor['state']}")
            if 'temperature' in sensor['category']:
                uom = "C"
            else:
                uom = ""
            if args.perfdata:
                perfData = {'label': f"{sensor['category']}_{sensor['id']}", 'value': f"{sensor[sensor['category']]}", 'uom': uom}
                check.add_perfdata(**perfData)
        summary += f"{len(t['sensor'])} Temp-Sensors"
             
    (code, message) = check.check_messages(separator="\n")
    if code == Status.OK:
        check.exit(code=code,message=f"{summary}\n{message}")
    else:
        check.exit(code=code,message=message)

if __name__ == "__main__":
    run()