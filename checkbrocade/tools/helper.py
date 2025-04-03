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
from types import SimpleNamespace

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

def compare_versions(required, current):
    def split_version(version):
        return re.findall(r'\d+|\D+', version)
    
    def convert_part(part):
        return int(part) if part.isdigit() else part
    
    required_parts = split_version(required)
    current_parts = split_version(current)
    
    for p1, p2 in zip(required_parts, current_parts):
        p1 = convert_part(p1)
        p2 = convert_part(p2)
        if p1 < p2:
            return True
        elif p1 > p2:
            return False
    
    if len(required_parts) < len(current_parts):
        return True
    elif len(required_parts) > len(current_parts):
        return False
    
    return -1

# Include & Exclude filter
def item_filter(args,item=None) -> None:
    """ Filter for items like disks, sensors, etc.."""
    if args.exclude:
        if re.search(args.exclude,item):
            return(True)
        else:
            return(False)
    elif args.include:
        if re.search(args.include,item):
            return(False)
        else:
            return(True)

# Create a Python NameSpace object from API JSON respone        
def sanitize_key(key):
    """ replace nasty chars by _ """
    key = key.replace("-", "_")
    key = re.sub(r'\W|^(?=\d)', '_', key) 
    return key

def convert_keys(obj):
    """ convert into namespaces"""
    if isinstance(obj, dict):
        return SimpleNamespace(**{sanitize_key(k): convert_keys(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return [convert_keys(i) for i in obj]
    return obj

# Convert time into secons
# 1d / 1 W / 1.5h
def to_seconds(value) -> None:
    if not value:
        return None
    
    match = re.search(r'([\d.]+)\s*([smhdwMy]?)', value.lower())
    if not match:
        return None
    
    time, unit = float(match.group(1)), match.group(2)
    unit_multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400,
        "w": 604800,
        "M": 2592000,  # Monat ≈ 30 Tage
        "y": 31536000  # Jahr ≈ 365 Tage
    }
    
    return time * unit_multipliers.get(unit, 1)    

def seconds_to_human(seconds: int) -> str:
    if seconds < 0:
        return "unknown input"
    
    time_units = [
        ("year", 31536000),
        ("month", 2592000),
        ("week", 604800),
        ("day", 86400),
        ("hour", 3600),
        ("minute", 60),
        ("second", 1)
    ]
    
    result = []
    
    if seconds >= 31536000:  # years
        relevant_units = ["year", "month", "week"]
    elif seconds >= 604800:  # Wochen-Bereich
        relevant_units = ["week", "day", "hour"]
    else:
        relevant_units = ["day", "hour", "minute"]
    
    for unit, unit_seconds in time_units:
        if unit in relevant_units:
            value = seconds // unit_seconds
            if value > 0:
                result.append(f"{value} {unit}{'s' if value > 1 else ''}")
                seconds %= unit_seconds
        if len(result) == 3:
            break
    
    return ", ".join(result) if result else "0 seconds"
