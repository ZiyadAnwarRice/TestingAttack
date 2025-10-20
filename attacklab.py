#!/usr/bin/env python3
"""
Attacklab.py - CS:APP Attack Lab Configuration File

Copyright (c) 2016, R. Bryant and D. O'Hallaron.
Converted to Python 3
"""

import time
import sys
from datetime import datetime

######
# Section 1: Required Configuration Variables (INSTRUCTOR)
######

SERVER_NAME = "jade.clear9.rice.edu"
USERNAME_HINT = "Enter your Rice NetID"
UPDATE_PERIOD = 20

REQUESTD_PORT = 18193
RESULTD_PORT = 18194

USERNAMES = [
    "alc", "mb156", "go15", "nr34", "tx10", "yn23", "bsl5", "comp222",
    "aa150", "aa255", "aa258", "aa270", "aaa38", "aac20", "ab223", "ab235",
    "abs15", "ac188", "acl18", "acs22", "acy3", "ad163", "ad166", "adg10",
    "ag188", "agn6", "agt8", "ah108", "ahc12", "ahv5", "aj106", "ajd18",
    "akr6", "alf15", "am307", "am315", "ams37", "amw21", "ap163", "apb7",
    "ara10", "art11", "ask20", "at105", "atb6", "bl77", "br52", "bs82",
    "bw35", "bw52", "caa12", "cah20", "cb112", "cf57", "ck62", "ckp2",
    "cn32", "csp8", "cw161", "cz68", "daj11", "db71", "dem14", "dhk3",
    "dk66", "dq7", "dr56", "drm15", "dvs1", "eak5", "ed56", "eec6",
    "eer7", "eg56", "eid2", "emm20", "es100", "etb5", "ew66", "ew67",
    "gec7", "gh20", "gjn1", "gl34", "ha30", "hd58", "hg60", "hk63",
    "hs102", "hw81", "ia22", "icw3", "is38", "ja110", "jal30", "jc165",
    "jc270", "jh215", "jj85", "jl363", "jl370", "jl561", "jmj11", "jn62",
    "js323", "jsp12", "jt81", "jt83", "jwl10", "kda5", "kkp5", "kn33",
    "kn36", "ldn1", "lim6", "ll103", "ll110", "ll151", "ls151", "ma185",
    "mas52", "mdo5", "mff1", "mg181", "mg188", "mhl10", "mkm10", "mlw10",
    "mt123", "mv57", "mz70", "nam12", "ngc5", "njz1", "nl58", "nl61",
    "nr58", "nt30", "ntq1", "nwc1", "og16", "os25", "pm58", "pml5",
    "pp31", "ps155", "pzz1", "qd8", "qz51", "ra80", "ral18", "rb160",
    "rc115", "reg12", "rek6", "rg100", "rr82", "rs150", "rs182", "sd122",
    "sd152", "sl149", "sp180", "spv3", "ss356", "ssv5", "st107", "sv65",
    "sw122", "sx25", "tcb10", "tde2", "th70", "tjl5", "tm100", "tmb15",
    "tmc15", "vjb5", "vl22", "vsg2", "vtn6", "vw11", "vw12", "wam4",
    "war2", "wb20", "wv5", "wzh1", "xs28", "yk72", "yl233", "yr23",
    "yt52", "yx76", "yz186", "yz236", "zas5", "zl116", "zp12"
]

######
# Section 2: Optional Configuration Variables
######

REQUESTD_TIMEOUT = 30

# Script names
REQUESTD = "attacklab-requestd.py"
RESULTD = "attacklab-resultd.py"
REPORTD = "attacklab-reportd.py"
UPDATE = "validate.py"
BUILDTARGET = "buildtarget.pl"

# Log files
LOGFILE = "./log.txt"
STATUSLOG = "./log-status.txt"

# Directories
TARGETDIR = "./targets"
TARGETSRC = "./src/build"

# Scoreboard files
SCOREFILE = "./scores.csv"
SCOREBOARDPAGE = "./attacklab-scoreboard.html"

# Quiet mode
QUIET = True

# Colors
DARK_GREY = '#b8d8ff'
LIGHT_GREY = '#dfefff'

# Form widths
WIDTH_USERID = 100
WIDTH_EMAIL = 225
WIDTH_INTEGER = 50
WIDTH_SHORTDATE = 120
WIDTH_TEXTTABLE = 600
CELLPADDING = 1
CELLSPACING = 1

# Misc constants
MAXHDRLEN = 16384
MAX_TEXTBOX = 32

######
# Helper functions
######

def log_msg(message):
    """Append a message to the status log"""
    date = time.strftime("%a %b %d %H:%M:%S %Y")
    script_name = sys.argv[0].split('/')[-1]
    
    if QUIET:
        try:
            with open(STATUSLOG, 'a') as f:
                f.write(f"{date}:{script_name}:{message}\n")
        except IOError:
            pass
    else:
        print(message)

def log_die(message):
    """Append a message to the status log and exit"""
    log_msg(message)
    sys.exit(1)

def date2time(date_str):
    """
    Convert a date string to seconds since the epoch
    
    Examples:
    Aug 4 11:01:05 2003
    August 4 11:01:05 2003
    """
    months = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
        'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
        'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    
    days = {
        'sun': 0, 'mon': 1, 'tue': 2, 'wed': 3,
        'thu': 4, 'fri': 5, 'sat': 6
    }
    
    try:
        # Normalize and parse
        date_lower = date_str.lower()
        date_lower = ' '.join(date_lower.split())
        
        parts = date_lower.split()
        
        # Check if first part is a day of week
        if parts[0][:3] in days:
            _, mon_str, mday, time_str, year_str = parts
        else:
            mon_str, mday, time_str, year_str = parts
        
        # Parse month
        mon = months.get(mon_str[:3])
        if mon is None:
            log_msg(f"Error: Invalid month field ({mon_str}) in date string {date_str}")
            return -1
        
        # Parse day
        mday = int(mday)
        if mday < 0 or mday > 31:
            log_msg(f"Error: Invalid day of month field in date string {date_str}")
            return -1
        
        # Parse time
        hours, minutes, seconds = map(int, time_str.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59):
            log_msg(f"Error: Invalid time field in date string {date_str}")
            return -1
        
        # Parse year
        year = int(year_str)
        if year < 0:
            log_msg(f"Error: Invalid year field in date string {date_str}")
            return -1
        
        # Create datetime and convert to timestamp
        dt = datetime(year, mon, mday, hours, minutes, seconds)
        return int(dt.timestamp())
        
    except (ValueError, IndexError) as e:
        log_msg(f"Error: Could not parse date string {date_str}: {e}")
        return -1

def short_date(timestamp):
    """Returns an abbreviated string version of an epoch time"""
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%a %b %d %H:%M")
