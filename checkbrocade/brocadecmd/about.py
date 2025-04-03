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
from ..tools.helper import severity, compare_versions, convert_keys
from ..tools.connect import broadcomAPI
from pprint import pprint as pp

__cmd__ = "about"
description = f"{__cmd__} need just connection settings and show up the brocade version"
"""
"""
logger = None
args = None

def run():
    global logger
    global args
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

    check = Check()
    try:
        plugin(check)
    except Exception as e:
        logger.error(f"{e}")
        check.exit(Status.UNKNOWN, f"{e}")

def plugin(check):
    base_url = f"https://{args.host}:{args.port}"
    api = broadcomAPI(logger, base_url, args.username, args.password, args.sessionfile)
    response = api.make_request("GET", "rest/running/brocade-chassis/chassis")
    chass = convert_keys(response)
    chassis = chass.chassis
    if compare_versions("9.2.0", api.version(True)):
        response = api.make_request("GET", "rest/running/brocade-chassis/version")
        ns = convert_keys(response)
        version = ns.version.fabric_os
    else:
        logger.info("FOS < 9.2.0 use version from API response")
        version = api.version(True)

    check.add_message(Status.OK, f"{chassis.manufacturer} {chassis.product_name} FOS {version} S/N {chassis.vendor_serial_number}")
    (code, message) = check.check_messages(separator="\n")
    check.exit(code=code,message=message)

if __name__ == "__main__":
    run()