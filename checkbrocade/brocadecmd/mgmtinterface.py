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
from ..tools.helper import severity, convert_keys
from ..tools.connect import broadcomAPI

__cmd__ = "mgmt-interface-health"
description = f"{__cmd__} mgmt-interface-health"
"""
"""
logger = None
args = None

def run():
    global logger
    global args
    parser = cli.Parser()
    parser.set_epilog("Check for Management Interface Health")
    parser.set_description(description)
    parser.add_optional_arguments(cli.Argument.EXCLUDE,
                                  cli.Argument.INCLUDE)

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
    response = api.make_request("GET", "rest/running/brocade-chassis/management-ethernet-interface")
    ifaces = convert_keys(response)

    ##
    ## Single int switch
    ## Always OK
    ##
    if len(ifaces.management_ethernet_interface) == 1:
        logger.info(f"seems to be a single switch")
        ifc = ifaces.management_ethernet_interface[0]
        logger.debug(f"interface -> {ifc}")
        check.exit(Status.OK, f"{ifc.cp_name} interface {ifc.interface_name} {ifc.speed}/{ifc.duplex}-duplex")
        # finish here
    else:
        logger.info(f"seems to be a DCX")

    ##
    ## Multi interface switch
    ##
    cp = {}
    for int in ifaces.management_ethernet_interface:
        if int.cp_name not in cp:
            cp[int.cp_name] = []
        cp[int.cp_name].append(int)

    for c in cp:
        try:
            bond = [x for x in cp[c] if "bond" in x.interface_name][0]
        except:
            logger.debug(f"no bond found for {c}: {cp[c]}")
            check.add_message(Status.WARNING, f"no bond interface found for {c}")
            continue

        active = [x for x in cp[c] if bond.active_interface in x.interface_name][0]
        standby = [x for x in cp[c] if bond.standby_interfaces.interface[0] in x.interface_name][0]

        out = f"{c} {bond.interface_name} {bond.speed}/{bond.duplex}-duplex; ACTIVE {active.interface_name} STANDBY {standby.interface_name}"

        # check bond
        if not bond.connection_established_status or "running" not in bond.ethernet_status_flags.flag:
            check.add_message(Status.CRITICAL, out)
        # check active interface
        elif not active.connection_established_status or "running" not in active.ethernet_status_flags.flag:
            check.add_message(Status.CRITICAL, out)
        else:
            check.add_message(Status.OK, out)

    (code, message) = check.check_messages(separator="\n")
    if code == Status.OK:
        check.exit(code=code,message=f"all interfaces are running\n{message}")
    else:
        check.exit(code=code,message=message)