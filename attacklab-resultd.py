#!/usr/bin/env python3
"""
attacklab-resultd.py - The CS:APP Attack Lab result server

The result server is a simple, special-purpose HTTP server that
collects real-time results from targets that the students are solving.

Copyright (c) 2016, R. Bryant and D. O'Hallaron.
Converted to Python 3 using aiohttp
"""

import time
import socket
import argparse
from aiohttp import web

import attacklab

class AttackLabResultServer:
    """Attack Lab Result Server using aiohttp"""
    
    def __init__(self):
        self.app = web.Application()
        self.app.middlewares.append(self.log_middleware)
        self.setup_routes()
    
    @web.middleware
    async def log_middleware(self, request, handler):
        """Log all requests"""
        attacklab.log_msg(f"Result server received: {request.method} {request.path_qs}")
        try:
            response = await handler(request)
            attacklab.log_msg(f"Response status: {response.status}")
            return response
        except web.HTTPException as ex:
            attacklab.log_msg(f"HTTP Exception: {ex.status} {ex.reason}")
            raise
    
    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/', self.handle_result)
        self.app.router.add_get('/submit', self.handle_result)
    
    async def handle_result(self, request):
        """Handle result submissions from targets"""
        # Get client info
        client_dname = request.remote
        try:
            client_dname = socket.gethostbyaddr(client_dname)[0].lower()
        except:
            client_dname = "unknown"
        
        # Get request line for logging
        request_hdr = f"{request.method} {request.path_qs} {request.version}"
        
        # Check header length
        if len(request_hdr) > attacklab.MAXHDRLEN or len(request_hdr) == 0:
            return web.Response(status=400)
        
        # Parse parameters
        params = request.query
        userid = params.get('user', '')
        course = params.get('course', '')
        result = params.get('result', '')
        
        attacklab.log_msg(f"received: {request_hdr}")
        attacklab.log_msg(f"userid={userid} course={course} result={result}")
        
        # Append to log file
        try:
            with open(attacklab.LOGFILE, 'a') as logfile:
                date = time.strftime("%a %b %d %H:%M:%S %Y")
                logfile.write(f"{client_dname}|{date}|{userid}|{course}|{result}\n")
        except Exception as e:
            attacklab.log_die(f"Error: Unable to open {attacklab.LOGFILE} for appending: {e}")
        
        # Send response
        return web.Response(
            text='OK',
            headers={
                'Connection': 'close',
                'MIME-Version': '1.0',
                'Content-Type': 'text/plain'
            }
        )

async def create_app():
    """Create and configure the aiohttp application"""
    server = AttackLabResultServer()
    return server.app

def main():
    """Main routine"""
    parser = argparse.ArgumentParser(description='Attack Lab result server')
    parser.add_argument('-q', action='store_true',
                       help=f'Quiet. Send error and status msgs to {attacklab.STATUSLOG} instead of tty.')
    args = parser.parse_args()
    
    if args.q:
        attacklab.QUIET = True
    
    server_dname = socket.gethostname()
    server_port = attacklab.RESULTD_PORT
    
    attacklab.log_msg(f"Results server started on {server_dname}:{server_port}")
    
    # Start the server
    web.run_app(
        create_app(),
        host='0.0.0.0',
        port=server_port,
        print=None  # Suppress aiohttp startup messages
    )

if __name__ == "__main__":
    main()
