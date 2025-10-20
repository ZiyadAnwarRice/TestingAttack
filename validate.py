#!/usr/bin/env python3
"""
validate.py - Called periodically by the attacklab-reportd.py daemon.

Scans the submissions in log.txt. Validates the most recent submission
for each phase submitted by each user. Updates the scoreboard, creates
reports for each student in the reports/ directory, and generates the
scores.csv file with the score for each student.

Usage: ./validate.py
"""

import sys
import os
import re
import subprocess
import datetime
from collections import defaultdict

import attacklab

# Autoflush output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(line_buffering=True)

# Constants
MAX_LEVEL = 3
MAX_PHASE = 5
MAX_CTARGET_PHASE = 3
MIN_RTARGET_LEVEL = 2
MAX_STRLEN = 1024
WEIGHT = [0, 10, 25, 25, 35, 5]  # indexed starting at 1

# Late penalty configuration
DEADLINE = datetime.datetime(2025, 10, 31, 23, 55, 0)  # October 31st, 11:55 PM
PENALTY_PER_DAY = 10  # 10 points per day late
MAX_LATE_DAYS = 3     # After 3 days, score is 0

# Parameters
SILENT_MAKE = "-s"

def read_logfile(logfile):
    """
    Read the logfile and create a dict entry for each user that consists
    of an array of their most recent submissions for each phase.
    """
    users = defaultdict(lambda: [None] * (MAX_PHASE + 1))
    
    try:
        with open(logfile, 'r') as f:
            linenum = 0
            for line in f:
                linenum += 1
                line = line.strip()
                
                # Skip blank lines
                if not line:
                    continue
                
                # Parse the input line
                match = re.match(r'(.*)\|(.*)\|(.*)\|(.*)\|(\d+):(.*):(.*):(.*):([\d]+):(.*)', line)
                if not match:
                    attacklab.log_msg(f"Warning: Invalid line {linenum} in {logfile}.")
                    continue
                
                hostname, time, userid, course, targetid, status, authkey, program, level, exploit = match.groups()
                level = int(level)
                targetid = int(targetid)
                
                # Check the input
                if not all([userid, course, targetid, status, authkey, program, level, exploit]):
                    attacklab.log_msg(f"Warning: Invalid line {linenum} in {logfile}.")
                    continue
                
                if status == "FAIL":
                    continue
                
                if program not in ["ctarget", "rtarget"]:
                    attacklab.log_msg(f"Warning: Bad program name ({program}) in line {linenum}. Ignored.")
                    continue
                
                if level < 1 or level > MAX_LEVEL:
                    attacklab.log_msg(f"Warning: Bad level ({level} > {MAX_LEVEL}) in line {linenum}. Ignored.")
                    continue
                
                if len(exploit) > MAX_STRLEN:
                    attacklab.log_msg(f"Warning: Input string too long in line {linenum}. Ignored.")
                    continue
                
                if program == "ctarget" and level > MAX_CTARGET_PHASE:
                    attacklab.log_msg(f"Warning: [{userid}:{linenum}] ctarget invoked with invalid level ({level}). Ignored.")
                    continue
                
                if program == "rtarget" and level < MIN_RTARGET_LEVEL:
                    attacklab.log_msg(f"Warning: [{userid}:{linenum}] rtarget invoked with invalid level ({level}). Ignored.")
                    continue
                
                # Compute phase offset
                if program == "ctarget":
                    phase = level
                else:
                    phase = MAX_CTARGET_PHASE - 1 + level
                
                # Add submission
                users[userid][phase] = {
                    'time': time,
                    'user': userid,
                    'targetid': targetid,
                    'authkey': authkey,
                    'program': program,
                    'level': level,
                    'exploit': exploit,
                    'valid': 0
                }
    
    except FileNotFoundError:
        attacklab.log_die(f"Couldn't open logfile {logfile}")
    
    return users

def main():
    """Main program"""
    logfile = attacklab.LOGFILE
    scorefile = attacklab.SCOREFILE
    webpage = attacklab.SCOREBOARDPAGE
    srcdir = "src"
    builddir = "build"
    
    # Read submissions
    users = read_logfile(logfile)
    
    # Create reports directory
    if not os.path.exists("reports"):
        os.makedirs("reports")
    elif not os.path.isdir("reports"):
        os.system("rm reports")
        os.makedirs("reports")
    
    # Open scores file
    try:
        scorefile_handle = open(scorefile, 'w')
    except:
        attacklab.log_die(f"Could not open {scorefile} for writing")
    
    # Save original working directory
    owd = os.getcwd()
    
    # Update log path for when we change directories
    attacklab.STATUSLOG = os.path.join(owd, attacklab.STATUSLOG)
    
    # Prepare the src directory
    try:
        os.chdir(srcdir)
        subprocess.run(f"make {SILENT_MAKE} clean && make {SILENT_MAKE}", shell=True, check=True)
        os.chdir(builddir)
    except Exception as e:
        attacklab.log_die(f"Couldn't prepare {srcdir}: {e}")
    
    # Store rankings and row data
    rankings = {}
    row_data = {}
    
    # Validate each user's submissions
    for username in users:
        reportfile = os.path.join(owd, "reports", username)
        
        try:
            with open(reportfile, 'w') as report:
                # Print summary
                report.write(f"Evaluating the most recent submissions for user {username}:\n")
                for i in range(1, MAX_PHASE + 1):
                    report.write(f"Phase {i}: ")
                    if users[username][i]:
                        sub = users[username][i]
                        report.write(f"{sub['time']}:{sub['targetid']}:{sub['program']}:"
                                   f"{sub['level']}:{sub['exploit']}\n")
                    else:
                        report.write("No submission.\n")
                report.write("\n")
                
                # Validate each submission
                valid = [False] * (MAX_PHASE + 1)
                
                for i in range(1, MAX_PHASE + 1):
                    if users[username][i]:
                        sub = users[username][i]
                        targetid = sub['targetid']
                        exploit = sub['exploit']
                        program = sub['program']
                        authkey = sub['authkey']
                        level = sub['level']
                        
                        # Create exploit file
                        exploitfile = f"{program}.l{level}"
                        with open(exploitfile, 'w') as f:
                            f.write(f"{exploit}\n")
                        
                        # Run the checker
                        report.write(f"Validating exploit for phase {i}.\n")
                        
                        target_path = f"../../targets/target{targetid}"
                        checker = f"{program}-check"
                        
                        cmd = (f"cat {exploitfile} | ./hex2raw | "
                              f"{target_path}/{checker} -a {authkey} -l {level}")
                        
                        try:
                            result = subprocess.run(cmd, shell=True, 
                                                  capture_output=True, text=True,
                                                  timeout=10)
                            output = result.stdout + result.stderr
                            report.write(output)
                            
                            if result.returncode == 0:
                                valid[i] = True
                                report.write(f"SUCCESS: Phase {i} exploit is valid ({WEIGHT[i]})\n")
                            else:
                                valid[i] = False
                                report.write(f"FAILURE: Phase {i} exploit is invalid. (0)\n")
                        except subprocess.TimeoutExpired:
                            valid[i] = False
                            report.write(f"FAILURE: Phase {i} exploit timed out. (0)\n")
                        except Exception as e:
                            valid[i] = False
                            report.write(f"FAILURE: Phase {i} error: {e}. (0)\n")
                        
                        report.write("\n")
                
                # Compute score
                maxscore = sum(WEIGHT[1:])
                raw_score = sum(WEIGHT[i] for i in range(1, MAX_PHASE + 1) if valid[i])
                
                # Get most recent submission time
                maxtime = 0
                maxdate = ""
                for i in range(1, MAX_PHASE + 1):
                    if users[username][i]:
                        date = users[username][i]['time']
                        tmp = attacklab.date2time(date)
                        if tmp > maxtime:
                            maxtime = tmp
                            maxdate = date
                
                # Apply late penalty
                if maxtime > 0:
                    submission_date = datetime.datetime.fromtimestamp(maxtime)
                    if submission_date > DEADLINE:
                        # Calculate days late (ceiling division)
                        days_late = (submission_date - DEADLINE).days + 1
                        
                        if days_late >= MAX_LATE_DAYS:
                            # 3+ days late = 0 score
                            score = 0
                            report.write(f"\nRaw Score: {raw_score}/{maxscore}\n")
                            report.write(f"Days Late: {days_late}\n")
                            report.write(f"Penalty: Assignment is {days_late} days late (>= {MAX_LATE_DAYS} days)\n")
                            report.write(f"Final Score: 0/{maxscore} (TOO LATE)\n")
                        else:
                            # Deduct 10 points per day, minimum score is 0
                            penalty = days_late * PENALTY_PER_DAY
                            score = max(0, raw_score - penalty)
                            report.write(f"\nRaw Score: {raw_score}/{maxscore}\n")
                            report.write(f"Days Late: {days_late}\n")
                            report.write(f"Penalty: -{penalty} points ({PENALTY_PER_DAY} points per day)\n")
                            report.write(f"Final Score: {score}/{maxscore}\n")
                    else:
                        # On time
                        score = raw_score
                        report.write(f"\nScore: {score}/{maxscore} (on time)\n")
                else:
                    score = raw_score
                    report.write(f"\nScore: {score}/{maxscore}\n")
                
                scorefile_handle.write(f"{username},{score}\n")
                
                # Store ranking data
                rankings[username] = (score, maxtime)
                
                # Store row data
                targetid = users[username][MAX_PHASE]['targetid'] if users[username][MAX_PHASE] else 0
                row_data[username] = {
                    'maxdate': maxdate,
                    'targetid': targetid,
                    'valid': valid
                }
        
        except Exception as e:
            attacklab.log_msg(f"Error processing user {username}: {e}")
            continue
    
    scorefile_handle.close()
    
    # Generate HTML scoreboard
    os.chdir(owd)
    
    try:
        with open(webpage, 'w') as web:
            # Write header
            web.write("""
<html>
<head>
<title>Attack Lab Scoreboard</title>
</head>
<body bgcolor=ffffff>

<table width=650><tr><td>
<h2>Attack Lab Scoreboard</h2>
<p>
Here is the latest information that we have received from your targets.
</td></tr></table>
""")
            
            import time
            web.write(f"Last updated: {time.strftime('%a %b %d %H:%M:%S %Y')} ")
            web.write(f"(updated every {attacklab.UPDATE_PERIOD} secs)<br>\n")
            web.write(f"<b>Deadline: October 31, 2025 at 11:55 PM</b><br>\n")
            web.write(f"<b>Late Penalty: -10 points per day, 0 points after 3 days</b><br>\n")
            
            web.write(f"""
<p>
<table border=0 cellspacing=1 cellpadding=1>
<tr bgcolor={attacklab.DARK_GREY} align=center>
<th align=center width=40> <b>#</b></th>
<th align=center width=60> <b>Target</b></th>
<th align=center width=200> <b>Date</b></th>
<th align=center width=70> <b>Score</b></th>
<th align=center width=70> <b>Phase 1</b></th>
<th align=center width=70> <b>Phase 2</b></th>
<th align=center width=70> <b>Phase 3</b></th>
<th align=center width=70> <b>Phase 4</b></th>
<th align=center width=70> <b>Phase 5</b></th>
</tr>
""")
            
            # Sort users by score (desc), then time (asc)
            sorted_users = sorted(rankings.items(), 
                                key=lambda x: (-x[1][0], x[1][1], x[0]))
            
            num_students = 0
            for username, (score, _) in sorted_users:
                num_students += 1
                targetid = row_data[username]['targetid']
                date = row_data[username]['maxdate']
                valid = row_data[username]['valid']
                
                web.write(f'<tr bgcolor={attacklab.LIGHT_GREY} align=center>\n')
                web.write(f'<td align=right>{num_students}</td>\n')
                web.write(f'<td align=right>{targetid}</td>')
                web.write(f'<td align=center>{date}</td>')
                web.write(f'<td align=right>{score}</td>')
                
                for i in range(1, MAX_PHASE + 1):
                    web.write('<td align=right>')
                    if users[username][i]:
                        if valid[i]:
                            web.write(f'{WEIGHT[i]}')
                        else:
                            web.write('<font color=red><b>invalid</b></font>')
                    else:
                        web.write('0')
                    web.write('</td>')
                
                web.write('</tr>\n')
            
            web.write('</table></body></html>\n')
    
    except Exception as e:
        attacklab.log_die(f"Error writing scoreboard: {e}")

if __name__ == "__main__":
    main()