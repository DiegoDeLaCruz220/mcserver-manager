import os
import sys
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

from digitalocean_manager import DigitalOceanManager
from minecraft_monitor import MinecraftMonitor
from port_listener import TCPProxy

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcserver-manager.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class MCServerManager:
    """Main service that manages the Minecraft server droplet."""
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        self.do_api_token = os.getenv('DO_API_TOKEN')
        self.droplet_id = os.getenv('DROPLET_ID')
        self.mc_server_ip = os.getenv('MC_SERVER_IP')
        # Railway assigns PORT, but we also support LISTEN_PORT for flexibility
        self.listen_port = int(os.getenv('PORT', os.getenv('LISTEN_PORT', 25565)))
        self.inactivity_timeout = int(os.getenv('INACTIVITY_TIMEOUT', 15))
        
        # Validate required config
        if not all([self.do_api_token, self.droplet_id, self.mc_server_ip]):
            logger.error("Missing required environment variables. Check your .env file.")
            sys.exit(1)
        
        # Initialize managers
        self.do_manager = DigitalOceanManager(self.do_api_token, self.droplet_id)
        self.mc_monitor = MinecraftMonitor(self.mc_server_ip, self.listen_port)
        self.tcp_proxy = TCPProxy(
            listen_port=self.listen_port,
            target_host=self.mc_server_ip,
            target_port=self.listen_port,
            on_connection_callback=self.on_connection_attempt,
            get_server_ready_callback=self.ensure_server_ready
        )
        
        # State tracking
        self.last_activity_time = None
        self.startup_in_progress = False
        self.running = True
        self.server_ready = False
    
    def on_connection_attempt(self, address):
        """Called when someone tries to connect to the proxy."""
        logger.info(f"New connection from {address[0]}:{address[1]}")
        
        # Update activity time
        self.last_activity_time = datetime.now()
        
        # Check if droplet is running, start if not
        if not self.do_manager.is_running():
            logger.info("Droplet is offline. Starting droplet...")
            self.server_ready = False
            self.start_server()
        elif not self.server_ready:
            logger.info("Droplet is starting up...")
        else:
            logger.info("Server is ready, connection will be proxied")
    
    def ensure_server_ready(self):
        """Ensure the Minecraft server is ready before proxying. Returns True when ready."""
        if self.server_ready:
            return True
        
        # Wait for droplet to be running
        max_wait = 300  # 5 minutes
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            if self.do_manager.is_running():
                break
            logger.info("Waiting for droplet to start...")
            time.sleep(5)
        
        if not self.do_manager.is_running():
            logger.error("Droplet did not start in time")
            return False
        
        # Wait for Minecraft server to be ready
        logger.info("Droplet is running, waiting for Minecraft server...")
        if self.mc_monitor.wait_for_server_ready():
            self.server_ready = True
            self.last_activity_time = datetime.now()
            logger.info("Minecraft server is ready!")
            return True
        else:
            logger.error("Minecraft server did not become ready")
            return False
    
    def start_server(self):
        """Start the Minecraft server droplet."""
        if self.startup_in_progress:
            logger.info("Startup already in progress, skipping")
            return
        
        self.startup_in_progress = True
        self.server_ready = False
        try:
            success = self.do_manager.start_droplet()
            if success:
                logger.info("Droplet started successfully")
            else:
                logger.error("Failed to start droplet")
        finally:
            self.startup_in_progress = False
    
    def check_inactivity(self):
        """Check if the server has been inactive and should be shut down."""
        if not self.do_manager.is_running():
            logger.debug("Droplet is not running, skipping inactivity check")
            self.server_ready = False
            return
        
        # Check active proxy connections first (more reliable than player count)
        active_connections = self.tcp_proxy.get_active_connections()
        
        if active_connections > 0:
            # Active connections, update activity time
            self.last_activity_time = datetime.now()
            logger.debug(f"{active_connections} active connections, activity time updated")
            return
        
        # No active proxy connections, double-check with server query
        if not self.mc_monitor.is_server_online():
            logger.debug("Minecraft server not responding")
            # Server might be starting or having issues, don't shutdown yet
            return
        
        player_count = self.mc_monitor.get_player_count()
        
        if player_count is None:
            logger.warning("Could not get player count")
            return
        
        if player_count > 0:
            # Players are active, update last activity time
            self.last_activity_time = datetime.now()
            logger.debug(f"{player_count} players online, activity time updated")
        else:
            # No players online
            if self.last_activity_time is None:
                # First time seeing zero players, start the timer
                self.last_activity_time = datetime.now()
                logger.info("No players online, starting inactivity timer")
            else:
                # Check if timeout has elapsed
                inactive_duration = datetime.now() - self.last_activity_time
                timeout_duration = timedelta(minutes=self.inactivity_timeout)
                
                if inactive_duration >= timeout_duration:
                    logger.info(f"Server inactive for {self.inactivity_timeout} minutes. Shutting down...")
                    self.do_manager.stop_droplet()
                    self.last_activity_time = None
                    self.server_ready = False
                else:
                    remaining = timeout_duration - inactive_duration
                    logger.info(f"No players online. Shutdown in {remaining.seconds // 60} minutes")
    
    def run(self):
        """Main service loop."""
        logger.info("=== MC Server Manager Started ===")
        logger.info(f"Proxying connections to: {self.mc_server_ip}:{self.listen_port}")
        logger.info(f"Listening on port: {self.listen_port}")
        logger.info(f"Inactivity timeout: {self.inactivity_timeout} minutes")
        
        # Start the TCP proxy
        self.tcp_proxy.start()
        
        try:
            # Check initial state
            if self.do_manager.is_running():
                logger.info("Droplet is currently running")
                self.last_activity_time = datetime.now()
                self.server_ready = True
            else:
                logger.info("Droplet is currently off")
            
            # Main monitoring loop
            while self.running:
                self.check_inactivity()
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Clean shutdown of the service."""
        logger.info("Shutting down MC Server Manager...")
        self.running = False
        self.tcp_proxy.stop()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    manager = MCServerManager()
    manager.run()
