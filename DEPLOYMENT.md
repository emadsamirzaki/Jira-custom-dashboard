# Deployment Guide - Jira Dashboard

## Overview
This guide covers deploying the Jira Dashboard to production. The app is containerized and can be deployed to various platforms.

## ⚠️ Security First

**BEFORE DEPLOYMENT:**
1. ✅ Never commit `.env` or `config.yaml` to version control (they're in `.gitignore`)
2. ✅ Regenerate your Jira API token before deployment
3. ✅ Use environment variables for all sensitive data (recommended)
4. ✅ Set `LOG_LEVEL=WARNING` in production

## Prerequisites

- Docker & Docker Compose (for containerized deployment)
- OR Python 3.9+ (for manual deployment)
- Internet connection (connects to Jira Cloud)

## Deployment Options

### Option 1: Docker Deployment (Recommended) 🐳

#### Quick Start
```bash
# 1. Clone the repository
git clone https://github.com/emadsamirzaki/Jira-custom-dashboard.git
cd "Jira-custom-dashboard"

# 2. Create .env file with your credentials
cp .env.example .env
# Edit .env with your Jira details

# 3. Start the application
docker-compose up -d

# 4. Access the dashboard
# Open your browser to: http://your-host:8501
```

#### .env Configuration
```env
JIRA_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@example.com
JIRA_TOKEN=your-api-token-here
JIRA_PROJECT_KEY=ESP
JIRA_BOARD_ID=81
LOG_LEVEL=WARNING
```

#### Docker Commands
```bash
# View logs
docker-compose logs -f jira-dashboard

# Stop the application
docker-compose down

# Rebuild the image
docker-compose build --no-cache

# Update the image
docker-compose pull
docker-compose up -d
```

### Option 2: Manual Python Deployment

#### Installation
```bash
# 1. Clone the repository
git clone https://github.com/emadsamirzaki/Jira-custom-dashboard.git
cd "Jira-custom-dashboard"

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Create .env file
cp .env.example .env
# Edit .env with your Jira details
```

#### Running the Application
```bash
# Development
streamlit run app.py

# Production (with specific settings)
streamlit run app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --logger.level=warning \
  --client.showErrorDetails false
```

### Option 3: Streamlit Cloud Deployment 🌐

**Easiest option - Zero DevOps Setup**

1. Push your code to GitHub (make sure `.env` and `config.yaml` are in `.gitignore`)
2. Go to https://streamlit.io/cloud
3. Click "New app" → Connect your GitHub repository
4. Select the repo and `app.py` as the main file
5. In "Advanced settings" → Add your environment variables:
   - `JIRA_URL`
   - `JIRA_EMAIL`
   - `JIRA_TOKEN`
   - `JIRA_PROJECT_KEY`
   - `JIRA_BOARD_ID`
   - `LOG_LEVEL=WARNING`

### Option 4: VPS Deployment (DigitalOcean, AWS, etc.)

#### Using Systemd Service
```bash
# 1. Copy files to VPS
scp -r . user@your-vps:/home/user/jira-dashboard

# 2. SSH into VPS and set up
ssh user@your-vps
cd /home/user/jira-dashboard

# 3. Create virtual environment and install
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 4. Create .env file
nano .env
# Add your credentials

# 5. Create systemd service file
sudo nano /etc/systemd/system/jira-dashboard.service
```

**Service file content:**
```ini
[Unit]
Description=Jira Dashboard Streamlit App
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/user/jira-dashboard
Environment="PATH=/home/user/jira-dashboard/venv/bin"
ExecStart=/home/user/jira-dashboard/venv/bin/streamlit run app.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --logger.level=warning
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 6. Start the service
sudo systemctl enable jira-dashboard
sudo systemctl start jira-dashboard
sudo systemctl status jira-dashboard

# View logs
sudo journalctl -f -u jira-dashboard
```

#### With Nginx Reverse Proxy
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        
        # Streamlit specific settings
        proxy_buffering off;
        proxy_request_buffering off;
        client_max_body_size 10M;
    }

    location /_stcore/stream {
        proxy_pass http://localhost:8501/_stcore/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

## Performance Optimization

### For High-Traffic Deployments

1. **Increase cache TTL** in environment:
   ```env
   CACHE_TTL=600  # 10 minutes instead of 5
   ```

2. **Run multiple replicas** with load balancer (Docker/Kubernetes)

3. **Reduce Jira API calls**:
   - Adjust cache decorators in code
   - Use maxResults wisely in JQL queries

4. **Monitor performance**:
   ```bash
   # Check memory usage
   docker stats jira-dashboard
   
   # Check logs for errors
   docker logs -f jira-dashboard
   ```

## Maintenance

### Regular Tasks
- Monitor disk space and logs
- Check Jira API rate limits
- Review application logs for errors
- Keep dependencies updated

### Updates
```bash
# Pull latest code
git pull origin master

# Update dependencies
pip install --upgrade -r requirements.txt

# Rebuild Docker image
docker-compose build --no-cache
docker-compose up -d
```

### Troubleshooting

**Connection Issues:**
- Verify Jira URL is accessible
- Check API token is valid (regenerate if needed)
- Ensure firewall allows outbound HTTPS

**Performance Issues:**
- Check Jira API rate limits
- Review logs for slow queries
- Increase container resources

**Memory Issues:**
```bash
# Docker - increase memory limit
docker-compose down
# Edit docker-compose.yml - increase memory limit
docker-compose up -d
```

## Security Checklist

- ✅ Never commit `.env` or `config.yaml`
- ✅ Use strong, unique Jira API tokens
- ✅ Regenerate tokens before/after sharing access
- ✅ Use HTTPS in production
- ✅ Set `LOG_LEVEL=WARNING` to avoid logging sensitive data
- ✅ Run containers as non-root user
- ✅ Use environment variables for all secrets
- ✅ Implement rate limiting if exposed publicly
- ✅ Monitor logs for suspicious activity
- ✅ Keep dependencies updated

## Support

For issues or questions:
1. Check the logs: `docker logs jira-dashboard` or app terminal
2. Verify `.env` configuration
3. Test Jira connectivity manually
4. Review README.md for additional configuration

---

**Last Updated:** February 2026
