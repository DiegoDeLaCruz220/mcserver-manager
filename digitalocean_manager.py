import digitalocean
import time
import logging

logger = logging.getLogger(__name__)


class DigitalOceanManager:
    """Manages Digital Ocean droplet operations."""
    
    def __init__(self, api_token, droplet_id):
        self.api_token = api_token
        self.droplet_id = int(droplet_id)
        self.manager = digitalocean.Manager(token=api_token)
        self.droplet = None
        self._load_droplet()
    
    def _load_droplet(self):
        """Load the droplet object."""
        try:
            self.droplet = self.manager.get_droplet(self.droplet_id)
            logger.info(f"Loaded droplet: {self.droplet.name} (ID: {self.droplet_id})")
        except Exception as e:
            logger.error(f"Failed to load droplet {self.droplet_id}: {e}")
            raise
    
    def is_running(self):
        """Check if the droplet is currently running."""
        self.droplet.load()
        status = self.droplet.status
        logger.debug(f"Droplet status: {status}")
        return status == 'active'
    
    def start_droplet(self):
        """Start the droplet if it's not running."""
        self.droplet.load()
        
        if self.droplet.status == 'active':
            logger.info("Droplet is already running")
            return True
        
        logger.info(f"Starting droplet {self.droplet.name}...")
        try:
            self.droplet.power_on()
            
            # Wait for the droplet to start (timeout after 5 minutes)
            timeout = 300
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                self.droplet.load()
                if self.droplet.status == 'active':
                    logger.info("Droplet started successfully")
                    # Give the Minecraft server some time to start
                    time.sleep(30)
                    return True
                time.sleep(5)
            
            logger.error("Timeout waiting for droplet to start")
            return False
            
        except Exception as e:
            logger.error(f"Failed to start droplet: {e}")
            return False
    
    def stop_droplet(self):
        """Stop the droplet if it's running."""
        self.droplet.load()
        
        if self.droplet.status == 'off':
            logger.info("Droplet is already stopped")
            return True
        
        logger.info(f"Stopping droplet {self.droplet.name}...")
        try:
            self.droplet.shutdown()
            logger.info("Shutdown command sent successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to stop droplet: {e}")
            return False
