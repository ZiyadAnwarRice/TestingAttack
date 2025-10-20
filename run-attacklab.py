#!/usr/bin/env python3
"""
run_attacklab.py - Attack Lab unified launcher
"""

import sys
import os
import signal
import asyncio
import socket
from aiohttp import web
import importlib.util

import attacklab
attacklab.QUIET = False

def load_module(name, path):
    """Dynamically load a module"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class AttackLabSystem:
    """Main Attack Lab system manager"""
    
    def __init__(self):
        self.request_runner = None
        self.result_runner = None
        self.update_task = None
        self.running = False
        self.shutdown_event = asyncio.Event()
    
    async def start_request_server(self):
        """Start the request server"""
        try:
            requestd = load_module('requestd', 'attacklab-requestd.py')
            app = await requestd.create_app()
            
            self.request_runner = web.AppRunner(app)
            await self.request_runner.setup()
            
            site = web.TCPSite(self.request_runner, '0.0.0.0', attacklab.REQUESTD_PORT)
            await site.start()
        except Exception as e:
            print(f"Failed to start request server: {e}")
            raise
    
    async def start_result_server(self):
        """Start the result server"""
        try:
            resultd = load_module('resultd', 'attacklab-resultd.py')
            app = await resultd.create_app()
            
            self.result_runner = web.AppRunner(app)
            await self.result_runner.setup()
            
            site = web.TCPSite(self.result_runner, '0.0.0.0', attacklab.RESULTD_PORT)
            await site.start()
        except Exception as e:
            print(f"Failed to start result server: {e}")
            raise
    
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
                    print(f"Scoreboard update failed")
            
            except Exception as e:
                print(f"Error updating scoreboard: {e}")
            
            await asyncio.sleep(attacklab.UPDATE_PERIOD)
    
    async def start(self):
        """Start all services"""
        self.running = True
        
        try:
            await self.start_request_server()
            await self.start_result_server()
            
            if os.path.exists(f"./{attacklab.UPDATE}") and os.access(f"./{attacklab.UPDATE}", os.X_OK):
                self.update_task = asyncio.create_task(self.scoreboard_update_loop())
            
            print("=" * 60)
            print("Attack Lab Server Running")
            print(f"Request server:  http://{attacklab.SERVER_NAME}:{attacklab.REQUESTD_PORT}/")
            print(f"Scoreboard:      http://{attacklab.SERVER_NAME}:{attacklab.REQUESTD_PORT}/scoreboard")
            print("=" * 60)
        except Exception as e:
            print(f"Failed to start: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop all services"""
        if not self.running:
            return
            
        self.running = False
        print("\nShutting down...")
        
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
        
        print("Shutdown complete")
        self.shutdown_event.set()

async def main_async():
    """Async main function"""
    system = AttackLabSystem()
    
    def signal_handler(signum):
        asyncio.create_task(system.stop())
    
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
        except:
            pass
    
    try:
        await system.start()
        await system.shutdown_event.wait()
    except KeyboardInterrupt:
        await system.stop()
    except Exception as e:
        print(f"Fatal error: {e}")
        await system.stop()
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"Failed: {e}")
        sys.exit(1)