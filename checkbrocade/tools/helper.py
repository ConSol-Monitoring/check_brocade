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

from monplugin import Range
import re

# Security level mapping
def severity(level) -> None:
    if level > 5:
        level = 5
    log_levels = {
        1: 'CRITICAL',
        2: 'ERROR',
        3: 'WARNING',
        4: 'INFO',
        5: 'DEBUG',
    }
    return log_levels[level]

# Compare various version strings
def compareVersion(required,current) -> None:
    required = re.sub("[a-zA-Z]",".",required)
    current = re.sub("[a-zA-Z]",".",current)
    versions1 = [int(v) for v in required.split(".")]
    versions2 = [int(v) for v in current.split(".")]
    for i in range(max(len(versions1),len(versions2))):
       v1 = versions1[i] if i < len(versions1) else 0
       v2 = versions2[i] if i < len(versions2) else 0
       if v1 < v2:
           return 1
       elif v1 > v2:
           return 0
    return -1