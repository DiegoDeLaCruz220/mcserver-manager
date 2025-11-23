from flask import Flask, render_template, jsonify
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Shared state with main app
manager_instance = None
log_buffer = []
MAX_LOGS = 100


class LogHandler(logging.Handler):
    """Custom log handler to capture logs for web display."""
    
    def emit(self, record):
        try:
            log_entry = {
                'timestamp': datetime.fromtimestamp(record.created).strftime('%H:%M:%S'),
                'message': self.format(record),
                'type': self.get_log_type(record.levelname)
            }
            log_buffer.append(log_entry)
            if len(log_buffer) > MAX_LOGS:
                log_buffer.pop(0)
        except Exception:
            pass
    
    def get_log_type(self, levelname):
        """Map log level to display type."""
        mapping = {
            'DEBUG': 'info',
            'INFO': 'info',
            'WARNING': 'warning',
            'ERROR': 'error',
            'CRITICAL': 'error'
        }
        return mapping.get(levelname, 'info')


def init_web_server(manager):
    """Initialize the web server with the manager instance."""
    global manager_instance
    manager_instance = manager
    
    # Add our custom log handler to capture logs
    log_handler = LogHandler()
    log_handler.setFormatter(logging.Formatter('%(name)s - %(levelname)s - %(message)s'))
    logging.getLogger().addHandler(log_handler)


@app.route('/')
def index():
    """Serve the main dashboard page."""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """Get current server status."""
    try:
        if not manager_instance:
            return jsonify({
                'status': 'unknown',
                'player_count': None,
                'server_ip': None,
                'crafty_url': None
            })
        
        # Get droplet status
        is_running = manager_instance.do_manager.is_running()
        status = 'active' if is_running else 'off'
        
        # Get player count if server is running
        player_count = None
        if is_running and manager_instance.server_ready:
            player_count = manager_instance.mc_monitor.get_player_count()
        
        # Get CraftyController URL from env or default
        crafty_url = os.getenv('CRAFTY_URL')
        if not crafty_url and is_running:
            crafty_url = f"http://{manager_instance.mc_server_ip}:8443"
        
        return jsonify({
            'status': status,
            'player_count': player_count,
            'server_ip': manager_instance.mc_server_ip,
            'tcp_proxy_port': manager_instance.listen_port,
            'active_connections': manager_instance.tcp_proxy.get_active_connections(),
            'crafty_url': crafty_url if is_running else None
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            'status': 'error',
            'player_count': None,
            'server_ip': None,
            'crafty_url': None
        }), 500


@app.route('/api/logs')
def get_logs():
    """Get recent logs."""
    return jsonify({'logs': log_buffer})


@app.route('/api/start', methods=['POST'])
def start_server():
    """Start the Minecraft server droplet."""
    try:
        if not manager_instance:
            return jsonify({
                'success': False,
                'message': 'Manager not initialized'
            }), 500
        
        if manager_instance.do_manager.is_running():
            return jsonify({
                'success': False,
                'message': 'Server is already running'
            })
        
        logger.info("Manual start requested from web interface")
        manager_instance.start_server()
        
        return jsonify({
            'success': True,
            'message': 'Server start initiated. Please wait 1-2 minutes for Minecraft to boot.'
        })
    except Exception as e:
        logger.error(f"Error starting server: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@app.route('/api/stop', methods=['POST'])
def stop_server():
    """Stop the Minecraft server droplet."""
    try:
        if not manager_instance:
            return jsonify({
                'success': False,
                'message': 'Manager not initialized'
            }), 500
        
        if not manager_instance.do_manager.is_running():
            return jsonify({
                'success': False,
                'message': 'Server is already stopped'
            })
        
        logger.info("Manual stop requested from web interface")
        manager_instance.do_manager.stop_droplet()
        manager_instance.server_ready = False
        manager_instance.last_activity_time = None
        
        return jsonify({
            'success': True,
            'message': 'Server shutdown initiated.'
        })
    except Exception as e:
        logger.error(f"Error stopping server: {e}")
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


def run_web_server(port=8080):
    """Run the Flask web server."""
    logger.info(f"Starting web dashboard on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
