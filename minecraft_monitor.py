import logging
from mcstatus import JavaServer
import time

logger = logging.getLogger(__name__)


class MinecraftMonitor:
    """Monitors Minecraft server for player activity."""
    
    def __init__(self, server_ip, port=25565):
        self.server_ip = server_ip
        self.port = port
        self.server = None
    
    def _get_server(self):
        """Get or create server connection."""
        if self.server is None:
            self.server = JavaServer.lookup(f"{self.server_ip}:{self.port}")
        return self.server
    
    def is_server_online(self):
        """Check if the Minecraft server is online and responding."""
        try:
            server = self._get_server()
            status = server.status()
            logger.debug(f"Server online check successful: {status.players.online} players")
            return True
        except Exception as e:
            logger.debug(f"Server not responding: {e}")
            return False
    
    def get_player_count(self):
        """Get the current number of players on the server."""
        try:
            server = self._get_server()
            status = server.status()
            player_count = status.players.online
            logger.info(f"Current players: {player_count}")
            return player_count
        except Exception as e:
            logger.warning(f"Failed to get player count: {e}")
            return None
    
    def wait_for_server_ready(self, timeout=180):
        """Wait for the Minecraft server to be ready after droplet starts."""
        logger.info("Waiting for Minecraft server to be ready...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.is_server_online():
                logger.info("Minecraft server is ready!")
                return True
            time.sleep(5)
        
        logger.warning("Timeout waiting for Minecraft server to be ready")
        return False
