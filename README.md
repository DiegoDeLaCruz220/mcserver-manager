# Minecraft Server Manager

Automatically manages your Digital Ocean Minecraft server droplet using a **TCP proxy** that runs 24/7 on Railway. The proxy:
- Detects when players try to connect
- Starts your Digital Ocean droplet automatically
- Forwards all traffic to your actual Minecraft server
- Monitors player activity and shuts down after 15 minutes of inactivity

**Perfect for saving costs** - your expensive Minecraft server only runs when people are actually playing!

## Architecture

```
Player (anywhere)
    ↓
Railway App (always-on proxy on port 25565)
    ↓
Digital Ocean Droplet (143.244.222.76 - starts/stops automatically)
    ↓
Minecraft Server
```

## Features

- **Zero-downtime detection**: Always-on TCP proxy listens for connections
- **Auto-start**: Starts the Digital Ocean droplet when players connect
- **Transparent forwarding**: All Minecraft traffic is proxied seamlessly
- **Auto-shutdown**: Monitors activity and shuts down after 15 minutes of inactivity
- **Cost-effective**: Railway free tier + droplet only runs when needed
- **Minimal lag**: TCP proxy adds only ~10-50ms latency

## Requirements

- Python 3.7+
- Digital Ocean API token
- Digital Ocean droplet with Minecraft server
- Railway account (free tier works)

## Setup

### 1. Prepare Your Digital Ocean Droplet

Make sure your Minecraft server:
1. Starts automatically when the droplet boots
2. Is accessible on port 25565
3. Has a static IP address (143.244.222.76)

### 2. Get Digital Ocean Credentials

**API Token:**
1. Log into Digital Ocean
2. Go to API → Tokens/Keys
3. Generate New Token with Read & Write access
4. Save the token

**Droplet ID:**
1. Go to your Droplets page
2. Click on your Minecraft server droplet
3. The ID is in the URL: `digitalocean.com/droplets/YOUR_DROPLET_ID`

### 3. Deploy to Railway

1. **Create Railway account**: Go to [railway.app](https://railway.app) and sign up

2. **Create new project**:
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Connect this repository

3. **Add environment variables** in Railway dashboard:
   ```
   DO_API_TOKEN=your_digital_ocean_api_token
   DROPLET_ID=your_droplet_id
   MC_SERVER_IP=143.244.222.76
   LISTEN_PORT=25565
   INACTIVITY_TIMEOUT=15
   ```

4. **Expose port 25565**:
   - In Railway project settings
   - Go to "Networking" tab
   - Add a TCP Proxy on port 25565
   - Railway will give you a public address (like `proxy.railway.app:25565`)

5. **Deploy**: Railway will automatically build and deploy

### 4. Update Your Minecraft DNS/IP

Point your Minecraft server domain (or tell players to use):
```
<your-railway-url>:25565
```

For example: `minecraft-proxy.railway.app:25565`

### 5. Test It

1. Make sure your Digital Ocean droplet is **OFF**
2. Try to connect to your Railway proxy address
3. Wait 1-2 minutes for the droplet to start
4. You should connect successfully!

## Local Testing (Optional)

If you want to test locally first:

```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your credentials

# Run locally
python main.py
```

## How It Works

1. **Always-on Proxy**: Railway runs the TCP proxy 24/7 (free tier)
2. **Connection Detection**: When a player connects, proxy detects it
3. **Droplet Startup**: Proxy starts the Digital Ocean droplet via API
4. **Wait for Ready**: Proxy waits for Minecraft server to fully start (~30-60 seconds)
5. **Traffic Forwarding**: All Minecraft traffic is proxied transparently
6. **Activity Monitoring**: Tracks active connections and player count
7. **Auto-shutdown**: After 15 minutes of zero players, droplet shuts down

## Configuration

Environment variables:

- `DO_API_TOKEN` - Your Digital Ocean API token (required)
- `DROPLET_ID` - Your droplet ID (required)
- `MC_SERVER_IP` - Your droplet's IP address (required)
- `LISTEN_PORT` - Port to listen on (default: 25565)
- `INACTIVITY_TIMEOUT` - Minutes before shutdown (default: 15)

## Monitoring

View logs in Railway dashboard:
- Connection attempts
- Droplet start/stop events
- Player counts
- Inactivity countdowns

## Cost Estimation

**Railway**: Free tier (500 hours/month) - more than enough!
**Digital Ocean**: Only charged when droplet is running
- Example: 4 hours/day of play = $5-15/month instead of $40-100/month

## Troubleshooting

**"Connection refused" errors**
- Check Railway deployment is running
- Verify port 25565 is exposed in Railway networking settings
- Ensure environment variables are set correctly

**Droplet doesn't start**
- Verify Digital Ocean API token has write permissions
- Check droplet ID is correct
- Review Railway logs for error messages

**Server takes too long to start**
- Normal! First connection takes 1-2 minutes
- Minecraft server needs time to boot
- Subsequent connections are faster if server is already running

**Lag issues**
- Railway proxy adds minimal latency (usually <50ms)
- Check Railway region matches your player base
- Monitor Railway logs for connection issues

## Advanced: Custom Domain

To use your own domain (e.g., `mc.yourdomain.com`):

1. Get your Railway TCP proxy address
2. Create an **A record** pointing to Railway's IP
3. Create an **SRV record** for Minecraft:
   ```
   _minecraft._tcp.yourdomain.com SRV 0 5 25565 proxy.railway.app
   ```

## License

MIT
