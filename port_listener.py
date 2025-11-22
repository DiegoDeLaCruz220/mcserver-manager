import socket
import logging
import threading
import time
import select

logger = logging.getLogger(__name__)


class TCPProxy:
    """TCP proxy that forwards connections to the Minecraft server."""
    
    def __init__(self, listen_port=25565, target_host=None, target_port=25565, 
                 on_connection_callback=None, get_server_ready_callback=None):
        self.listen_port = listen_port
        self.target_host = target_host
        self.target_port = target_port
        self.on_connection_callback = on_connection_callback
        self.get_server_ready_callback = get_server_ready_callback
        self.running = False
        self.server_socket = None
        self.listener_thread = None
        self.active_connections = 0
        self.connection_lock = threading.Lock()
    
    def start(self):
        """Start the proxy server."""
        if self.running:
            logger.warning("Proxy is already running")
            return
        
        self.running = True
        self.listener_thread = threading.Thread(target=self._listen, daemon=True)
        self.listener_thread.start()
        logger.info(f"TCP Proxy started on port {self.listen_port}, forwarding to {self.target_host}:{self.target_port}")
    
    def stop(self):
        """Stop the proxy server."""
        self.running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        logger.info("TCP Proxy stopped")
    
    def get_active_connections(self):
        """Get the current number of active connections."""
        with self.connection_lock:
            return self.active_connections
    
    def _listen(self):
        """Main listening loop."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.listen_port))
            self.server_socket.listen(10)
            self.server_socket.settimeout(1.0)
            
            logger.info(f"Proxy listening on port {self.listen_port}")
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.info(f"Connection from {address[0]}:{address[1]}")
                    
                    # Trigger callback to ensure server is ready
                    if self.on_connection_callback:
                        self.on_connection_callback(address)
                    
                    # Handle this connection in a new thread
                    connection_thread = threading.Thread(
                        target=self._handle_connection,
                        args=(client_socket, address),
                        daemon=True
                    )
                    connection_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        logger.error(f"Error accepting connection: {e}")
        
        except Exception as e:
            logger.error(f"Failed to start proxy: {e}")
        finally:
            if self.server_socket:
                self.server_socket.close()
    
    def _handle_connection(self, client_socket, client_address):
        """Handle a single client connection by proxying to the target server."""
        server_socket = None
        
        with self.connection_lock:
            self.active_connections += 1
            logger.info(f"Active connections: {self.active_connections}")
        
        try:
            # Wait for the Minecraft server to be ready
            if self.get_server_ready_callback:
                logger.info("Waiting for Minecraft server to be ready...")
                if not self.get_server_ready_callback():
                    logger.error("Server did not become ready, closing client connection")
                    client_socket.close()
                    return
            
            # Connect to the actual Minecraft server
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(10.0)
            
            try:
                server_socket.connect((self.target_host, self.target_port))
                logger.info(f"Connected to Minecraft server at {self.target_host}:{self.target_port}")
            except Exception as e:
                logger.error(f"Failed to connect to Minecraft server: {e}")
                client_socket.close()
                return
            
            # Set sockets to non-blocking for select
            client_socket.setblocking(False)
            server_socket.setblocking(False)
            
            # Proxy data between client and server
            self._proxy_data(client_socket, server_socket, client_address)
            
        except Exception as e:
            logger.error(f"Error handling connection from {client_address}: {e}")
        finally:
            if client_socket:
                try:
                    client_socket.close()
                except:
                    pass
            if server_socket:
                try:
                    server_socket.close()
                except:
                    pass
            
            with self.connection_lock:
                self.active_connections -= 1
                logger.info(f"Connection closed. Active connections: {self.active_connections}")
    
    def _proxy_data(self, client_socket, server_socket, client_address):
        """Proxy data bidirectionally between client and server."""
        sockets = [client_socket, server_socket]
        
        try:
            while self.running:
                readable, _, exceptional = select.select(sockets, [], sockets, 1.0)
                
                if exceptional:
                    logger.debug("Socket exception, closing connection")
                    break
                
                for sock in readable:
                    try:
                        data = sock.recv(4096)
                        if not data:
                            # Connection closed
                            return
                        
                        # Forward data to the other socket
                        if sock is client_socket:
                            server_socket.sendall(data)
                        else:
                            client_socket.sendall(data)
                            
                    except socket.error as e:
                        logger.debug(f"Socket error during proxy: {e}")
                        return
                    
        except Exception as e:
            logger.error(f"Error proxying data: {e}")
