#!/usr/bin/env python3
"""
run_attacklab.py - Unified launcher for Attack Lab system

This script starts all Attack Lab services in a single process using asyncio.
"""

import sys
import os
import signal
import asyncio
import argparse
import socket
from aiohttp import web

import attacklab

# Import server classes
import importlib.util

def load_module(name, path):
    """Dynamically load a module"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class AttackLabSystem:
    """Main Attack Lab system manager"""
    
    def __init__(self, quiet=False):
        if quiet:
            attacklab.QUIET = True
        
        self.request_runner = None
        self.result_runner = None
        self.update_task = None
        self.running = False
    
    async def start_request_server(self):
        """Start the request server"""
        attacklab.log_msg("Starting request server...")
        
        # Import the request server module
        requestd = load_module('requestd', 'attacklab-requestd.py')
        
        # Create the app
        app = await requestd.create_app()
        
        self.request_runner = web.AppRunner(app)
        await self.request_runner.setup()
        
        site = web.TCPSite(self.request_runner, '0.0.0.0', attacklab.REQUESTD_PORT)
        await site.start()
        
        attacklab.log_msg(f"Request server running on port {attacklab.REQUESTD_PORT}")
    
    async def start_result_server(self):
        """Start the result server"""
        attacklab.log_msg("Starting result server...")
        
        # Import the result server module
        resultd = load_module('resultd', 'attacklab-resultd.py')
        
        # Create the app
        app = await resultd.create_app()
        
        self.result_runner = web.AppRunner(app)
        await self.result_runner.setup()
        
        site = web.TCPSite(self.result_runner, '0.0.0.0', attacklab.RESULTD_PORT)
        await site.start()
        
        attacklab.log_msg(f"Result server running on port {attacklab.RESULTD_PORT}")
    
    async def scoreboard_update_loop(self):
        """Periodically update the scoreboard"""
        while self.running:
            try:
                proc = await asyncio.create_subprocess_shell(
                    f"./{attacklab.UPDATE}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()
                
                if proc.returncode != 0:
                    attacklab.log_msg(f"Error: Update script ({attacklab.UPDATE}) failed")
            
            except Exception as e:
                attacklab.log_msg(f"Error in scoreboard update: {e}")
            
            await asyncio.sleep(attacklab.UPDATE_PERIOD)
    
    async def start(self):
        """Start all services"""
        self.running = True
        
        server_dname = socket.gethostname()
        attacklab.log_msg(f"Attack Lab system started on {server_dname}")
        
        # Start servers
        await self.start_request_server()
        await self.start_result_server()
        
        # Start scoreboard updates if validate script exists
        if os.path.exists(f"./{attacklab.UPDATE}") and os.access(f"./{attacklab.UPDATE}", os.X_OK):
            self.update_task = asyncio.create_task(self.scoreboard_update_loop())
            attacklab.log_msg("Scoreboard updates enabled")
        else:
            attacklab.log_msg(f"Warning: Update script ({attacklab.UPDATE}) not found. Scoreboard updates disabled.")
        
        attacklab.log_msg("All services started successfully")
    
    async def stop(self):
        """Stop all services"""
        self.running = False
        attacklab.log_msg("Shutting down Attack Lab system...")
        
        if self.update_task:
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass
        
        if self.request_runner:
            await self.request_runner.cleanup()
        if self.result_runner:
            await self.result_runner.cleanup()
        
        attacklab.log_msg("Attack Lab system stopped")

async def main_async(quiet=False):
    """Async main function"""
    system = AttackLabSystem(quiet=quiet)
    loop = asyncio.get_event_loop()
    
    def signal_handler(signame):
        attacklab.log_msg(f"Received {signame}. Shutting down...")
        asyncio.create_task(system.stop())
        loop.stop()
    
    # Setup signal handlers
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        try:
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(signal.Signals(s).name))
        except (NotImplementedError, AttributeError):
            # Windows doesn't support add_signal_handler
            pass
    
    try:
        await system.start()
        
        # Keep running
        while system.running:
            await asyncio.sleep(1)
    
    except KeyboardInterrupt:
        await system.stop()
    except Exception as e:
        attacklab.log_msg(f"Fatal error: {e}")
        await system.stop()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Attack Lab System')
    parser.add_argument('-q', '--quiet', action='store_true', 
                       help='Quiet mode - log to file instead of console')
    args = parser.parse_args()
    
    try:
        asyncio.run(main_async(quiet=args.quiet))
    except KeyboardInterrupt:
        print("\nShutdown complete")

if __name__ == "__main__":
    main()
```

---

## FILE 7: requirements.txt
```
aiohttp>=3.8.0
