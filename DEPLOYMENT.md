# Deployment Configuration Files

This directory contains all the necessary files for deploying your Django backend to various free hosting platforms.

## Files Created

- **Procfile** - Process file for Railway/Render deployment
- **runtime.txt** - Specifies Python version (3.11.0)
- **railway.json** - Railway-specific configuration
- **render.yaml** - Render.com configuration with PostgreSQL
- **deploy_helper.py** - Helper script to generate SECRET_KEY and show deployment steps

## Quick Start

### Option 1: Railway (Recommended for ML workloads)

```bash
# Run the helper script to get your SECRET_KEY
python deploy_helper.py

# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up

# Add PostgreSQL in Railway dashboard
# Set environment variables (shown in deploy_helper.py output)
# Create superuser: railway run python manage.py createsuperuser
```

### Option 2: Render.com

```bash
# Sign up at render.com
# Connect your GitHub repository
# Render will auto-detect the render.yaml configuration
# Add PostgreSQL database
# Set environment variables in dashboard
```

### Option 3: Fly.io

```bash
# Install Fly CLI
iwr https://fly.io/install.ps1 -useb | iex

# Login and launch
fly auth login
fly launch

# Create PostgreSQL
fly postgres create
fly postgres attach <postgres-app-name>

# Deploy
fly deploy
```

## Environment Variables Required

All platforms need these environment variables:

- `SECRET_KEY` - Generate with deploy_helper.py
- `DEBUG` - Set to `False` for production
- `DATABASE_URL` - Auto-set by PostgreSQL service
- `ALLOWED_HOSTS` - Your deployment domain (e.g., `.railway.app`)
- `CORS_ALLOWED_ORIGINS` - Your frontend URL
- `CSRF_TRUSTED_ORIGINS` - Your frontend URL

## Platform Comparison

| Platform | RAM | Free Tier | Best For |
|----------|-----|-----------|----------|
| Railway | 2GB | $5/month credit | ML workloads ⭐ |
| Render | 512MB | 750 hours/month | Simple apps |
| Fly.io | 3GB | 160GB bandwidth | Containerized apps |

## Need Help?

See the comprehensive deployment guide in the artifacts for detailed instructions.
