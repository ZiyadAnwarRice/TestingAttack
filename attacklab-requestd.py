
"""
attacklab-requestd.py - The CS:APP Attack Lab Request Daemon

Copyright (c) 2016, R. Bryant and D. O'Hallaron

The request daemon is a simple special-purpose HTTP server that
allows students to use their Web browser to request custom made
targets and to view the realtime scoreboard.
"""

import os
import re
import argparse
import asyncio
from aiohttp import web

import attacklab

# Error messages
BAD_USERMAIL_MSG = "Invalid email address."
USERMAIL_TAINT_MSG = "The email address contains an illegal character."
BAD_USERNAME_MSG = "You forgot to enter a user name."
USERNAME_TAINT_MSG = "The user name contains an illegal character."

def buildform(hostname, port, labid, usermail, username, errmsg=""):
    """Build an HTML form as a string"""
    form = f"""<html><title>CS:APP Attack Lab Target Request</title>
<body bgcolor=white>
<h2>CS:APP Attack Lab Target Request</h2>
<p>Fill in the form and then click the Submit button once to download your unique target.</p>
<p>It takes a few seconds to build your target, so please be patient.</p>
<p>Hit the Reset button to get a clean form.</p>
<p>Legal characters are spaces, letters, numbers, underscores ('_'),<br>
hyphens ('-'), at signs ('@'), and dots ('.').</p>
<form action=http://{hostname}:{port} method=get>
<table>
<tr>
<td><b>User name</b><br><font size=-1><i>{attacklab.USERNAME_HINT}&nbsp;</i></font></td>
<td><input type=text size={attacklab.MAX_TEXTBOX} maxlength={attacklab.MAX_TEXTBOX} name=username value="{username}"></td>
</tr>
<tr>
<td><b>Email address</b></td>
<td><input type=text size={attacklab.MAX_TEXTBOX} maxlength={attacklab.MAX_TEXTBOX} name=usermail value="{usermail}"></td>
</tr>
<tr><td>&nbsp;</td></tr>
<tr>
<td><input type=submit name=submit value="Submit"></td>
<td><input type=submit name=reset value="Reset"></td>
</tr>
</table></form>
"""
    if errmsg:
        form += f"<p><font color=red><b>{errmsg}</b></font><p>\n"
    form += "</body></html>\n"
    return form

class AttackLabRequestServer:
    """Attack Lab Request Server using aiohttp"""
    
    def __init__(self):
        self.app = web.Application()
        self.setup_routes()
    
    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/', self.handle_request)
        self.app.router.add_get('/scoreboard', self.handle_scoreboard)
    
    async def handle_scoreboard(self, request):
        """Handle scoreboard requests"""
        content = "No scoreboard yet..."
        if os.path.exists(attacklab.SCOREBOARDPAGE):
            with open(attacklab.SCOREBOARDPAGE, 'r') as f:
                content = f.read()
        
        return web.Response(text=content, content_type='text/html')
    
    async def handle_request(self, request):
        """Handle form and target requests"""
        # Get client info
        client_dname = request.remote
        
        # Get query parameters
        params = request.query
        username = params.get('username', '').strip()
        usermail = params.get('usermail', '').strip()
        
        # If no form arguments or reset request, send clean form
        if (not usermail and not username) or 'reset' in params:
            form = buildform(attacklab.SERVER_NAME, attacklab.REQUESTD_PORT, 
                           "", "", "", "")
            return web.Response(text=form, content_type='text/html')
        
        # Validate inputs - check for illegal characters
        # Legal: spaces, letters, numbers, hyphens, underscores, @, dots
        legal_pattern = r'^[\s\-@\w.]+$'
        
        # Validate email
        if usermail:
            if not re.match(legal_pattern, usermail):
                attacklab.log_msg(f"Invalid target request from {client_dname}: "
                                f"Illegal character in email address ({usermail})")
                form = buildform(attacklab.SERVER_NAME, attacklab.REQUESTD_PORT,
                               "", usermail, username, USERMAIL_TAINT_MSG)
                return web.Response(text=form, content_type='text/html')
        
        # Validate username
        if username:
            if not re.match(legal_pattern, username):
                attacklab.log_msg(f"Invalid target request from {client_dname}: "
                                f"Illegal character in user name ({username})")
                form = buildform(attacklab.SERVER_NAME, attacklab.REQUESTD_PORT,
                               "", usermail, username, USERNAME_TAINT_MSG)
                return web.Response(text=form, content_type='text/html')
        
        # Check username is not empty
        if not username or username == "":
            attacklab.log_msg(f"Invalid target request from {client_dname}: Missing user name")
            form = buildform(attacklab.SERVER_NAME, attacklab.REQUESTD_PORT,
                           "", usermail, username, BAD_USERNAME_MSG)
            return web.Response(text=form, content_type='text/html')
        
        # Check email is valid
        if not usermail or usermail == "" or '@' not in usermail:
            attacklab.log_msg(f"Invalid target request from {client_dname}: "
                            f"Invalid email address ({usermail})")
            form = buildform(attacklab.SERVER_NAME, attacklab.REQUESTD_PORT,
                           "", usermail, username, BAD_USERMAIL_MSG)
            return web.Response(text=form, content_type='text/html')
        
        # Everything is valid - build and deliver target
        attacklab.log_msg(f"Received target request from {client_dname}:{username}:{usermail}")
        
        # Get list of existing targets
        targets = []
        if os.path.exists(attacklab.TARGETDIR):
            for item in os.listdir(attacklab.TARGETDIR):
                if item.startswith('target'):
                    try:
                        num = int(item.replace('target', ''))
                        targets.append(num)
                    except ValueError:
                        pass
        
        # Find next target number
        targetnum = max(targets) + 1 if targets else 1
        
        # Build the target
        owd = os.getcwd()
        attacklab.log_msg(f"Start building target target{targetnum} for {username}")
        
        build_cmd = (f"cd {attacklab.TARGETSRC} && "
                    f"./{attacklab.BUILDTARGET} -u {username} -t {targetnum} "
                    f">> {owd}/{attacklab.STATUSLOG} 2>&1")
        
        proc = await asyncio.create_subprocess_shell(
            build_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        
        if proc.returncode != 0:
            attacklab.log_msg(f"ERROR: Couldn't make target{targetnum}")
            return web.Response(text="Error building target", status=500)
        
        attacklab.log_msg(f"Finished building target target{targetnum} for {username}")
        
        # Send the tar file
        tarfilename = f"target{targetnum}.tar"
        tarpath = os.path.join(attacklab.TARGETDIR, tarfilename)
        
        if not os.path.exists(tarpath):
            return web.Response(text=f"Target file not found: {tarfilename}", status=500)
        
        with open(tarpath, 'rb') as f:
            tar_data = f.read()
        
        attacklab.log_msg(f"Sent target {targetnum} to {client_dname}:{username}:{usermail}")
        
        return web.Response(
            body=tar_data,
            headers={
                'Connection': 'close',
                'MIME-Version': '1.0',
                'Content-Type': 'application/x-tar',
                'Content-Disposition': f'file; filename="{tarfilename}"'
            }
        )

async def create_app():
    """Create and configure the aiohttp application"""
    server = AttackLabRequestServer()
    return server.app

def main():
    """Main routine"""
    parser = argparse.ArgumentParser(description='Attack Lab request server')
    parser.add_argument('-q', action='store_true',
                       help=f'Quiet. Send error and status msgs to {attacklab.STATUSLOG} instead of tty.')
    args = parser.parse_args()
    
    if args.q:
        attacklab.QUIET = True
    
    attacklab.log_msg(f"Request server started on {attacklab.SERVER_NAME}:{attacklab.REQUESTD_PORT}")
    
    # Check that required files exist
    buildtarget_path = os.path.join(attacklab.TARGETSRC, attacklab.BUILDTARGET)
    if not os.path.exists(buildtarget_path) or not os.access(buildtarget_path, os.X_OK):
        attacklab.log_die(f"Error: Couldn't find an executable {buildtarget_path} script.")
    
    # Create target directory if needed
    if not os.path.exists(attacklab.TARGETDIR):
        os.makedirs(attacklab.TARGETDIR)
    
    # Start the server
    web.run_app(
        create_app(),
        host='0.0.0.0',
        port=attacklab.REQUESTD_PORT,
        print=None  # Suppress aiohttp startup messages
    )

if __name__ == "__main__":
    main()
