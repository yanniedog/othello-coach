"""API server CLI"""

import argparse
import sys
import asyncio
import signal
from pathlib import Path
import tomli
import logging
from ..logging_setup import setup_logging
from ..api.server import APIServer


def load_config(config_path: str = None) -> dict:
    """Load configuration from file"""
    if config_path is None:
        config_path = Path.home() / '.othello_coach' / 'config.toml'
    
    try:
        with open(config_path, 'rb') as f:
            config = tomli.load(f)
        return config
    except FileNotFoundError:
        logging.getLogger(__name__).error("Config file not found: %s", config_path)
        logging.getLogger(__name__).error("Run 'othello-coach' first to create default configuration")
        sys.exit(1)
    except Exception as e:
        logging.getLogger(__name__).exception("Error loading config: %s", e)
        sys.exit(1)


async def main():
    """Main entry point for othello-api"""
    setup_logging(overwrite=False)
    parser = argparse.ArgumentParser(
        description="Start Othello Coach local API server"
    )
    
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Host to bind to (default: 127.0.0.1, loopback only)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=0,
        help='Port to bind to (default: 0 for random available port)'
    )
    
    parser.add_argument(
        '--config',
        help='Configuration file path'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (shows /docs endpoint)'
    )
    
    parser.add_argument(
        '--generate-token',
        action='store_true',
        help='Generate new API token and exit'
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Check if API is enabled
    if not config.get('feature_flags', {}).get('api', False):
        logging.getLogger(__name__).error("API is disabled in configuration")
        logging.getLogger(__name__).error("Set feature_flags.api = true in config.toml to enable")
        sys.exit(1)
    
    # Override host if not loopback
    if args.host not in ('127.0.0.1', 'localhost', '::1'):
        logging.getLogger(__name__).warning("API server only supports loopback addresses for security; forcing host to 127.0.0.1")
        args.host = '127.0.0.1'
    
    # Use configured port if not specified
    port = args.port or config.get('api', {}).get('port', 0)
    
    # Set debug mode
    config['debug'] = args.debug
    
    # Generate token if requested
    if args.generate_token:
        import secrets
        new_token = secrets.token_urlsafe(32)
        logging.getLogger(__name__).info("Generated new API token: %s", new_token)
        logging.getLogger(__name__).info("Add this to your config.toml:")
        logging.getLogger(__name__).info("[api]\ntoken = \"%s\"", new_token)
        return
    
    try:
        # Create and start server
        server = APIServer(config)
        
        logging.getLogger(__name__).info("Othello Coach API Server v1.1.0")
        logging.getLogger(__name__).info("Configuration: %s", args.config or 'default')
        logging.getLogger(__name__).info("Features enabled:")
        for feature, enabled in config.get('feature_flags', {}).items():
            status = "enabled" if enabled else "disabled"
            logging.getLogger(__name__).info("  %s: %s", feature, status)
        logging.getLogger(__name__).info("")
        
        # Handle shutdown gracefully
        shutdown_event = asyncio.Event()
        
        def signal_handler():
            logging.getLogger(__name__).info("Received shutdown signal...")
            shutdown_event.set()
        
        # Register signal handlers
        if sys.platform != 'win32':
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(sig, signal_handler)
        
        # Start server
        server_task = asyncio.create_task(
            server.start(host=args.host, port=port)
        )
        
        # Wait for shutdown signal or server completion
        done, pending = await asyncio.wait(
            [server_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logging.getLogger(__name__).info("API server stopped")
        
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Shutdown requested by user")
    except Exception as e:
        logging.getLogger(__name__).exception("Error starting API server: %s", e)
        sys.exit(1)


def main_sync():
    """Synchronous wrapper for async main"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main_sync()
