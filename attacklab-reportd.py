#!/usr/bin/env python3
"""
attacklab-reportd.py - Attack Lab reporting daemon

Copyright (c) 2016, R. Bryant and D. O'Hallaron
Converted to Python 3

Repeatedly calls the validate.py program to validate the most recent
exploits for each student, and generate the scoreboard web page and
the scores.csv file.
"""

import os
import asyncio
import argparse

import attacklab

async def scoreboard_update_loop():
    """Periodically update the scoreboard"""
    while True:
        try:
            # Run the validation script
            proc = await asyncio.create_subprocess_shell(
                f"./{attacklab.UPDATE}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                attacklab.log_msg(f"Error: Update script ({attacklab.UPDATE}) failed")
        
        except Exception as e:
            attacklab.log_msg(f"Error in scoreboard update: {e}")
        
        # Wait before next update
        await asyncio.sleep(attacklab.UPDATE_PERIOD)

async def main_async(quiet=False):
    """Async main routine"""
    if quiet:
        attacklab.QUIET = True
    
    # Check that the update script exists
    if not os.path.exists(attacklab.UPDATE) or not os.access(attacklab.UPDATE, os.X_OK):
        attacklab.log_die(f"ERROR: Update script ({attacklab.UPDATE}) either missing or not executable")
    
    attacklab.log_msg("Report daemon started")
    
    # Run the update loop
    await scoreboard_update_loop()

def main():
    """Main routine"""
    parser = argparse.ArgumentParser(description='Attack Lab reporting daemon')
    parser.add_argument('-q', action='store_true', 
                       help=f'Quiet. Send error and status msgs to {attacklab.STATUSLOG} instead of tty.')
    args = parser.parse_args()
    
    try:
        asyncio.run(main_async(quiet=args.q))
    except KeyboardInterrupt:
        attacklab.log_msg("Report daemon stopped")

if __name__ == "__main__":
    main()
