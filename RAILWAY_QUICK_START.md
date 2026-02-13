# Quick Railway Setup Guide

## 🚀 Two Ways to Deploy

### Method 1: Using Railway Dashboard (No CLI Needed) ⭐ EASIEST

This method doesn't require installing anything!

#### Step 1: Push Code to GitHub

```bash
# If not already a git repo
cd "d:\campus connection\sqlspark-lab-main\backend"
git init
git add .
git commit -m "Prepare for Railway deployment"

# Create a new repo on GitHub, then:
git remote add origin https://github.com/your-username/your-repo-name.git
git push -u origin main
```

#### Step 2: Deploy from Railway Dashboard

1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"**
3. Select **"Deploy from GitHub repo"**
4. Authorize Railway to access your GitHub
5. Select your repository
6. Railway will automatically detect Django and deploy!

#### Step 3: Add PostgreSQL

1. In your Railway project dashboard
2. Click **"New"** → **"Database"** → **"Add PostgreSQL"**
3. Done! DATABASE_URL is automatically connected

#### Step 4: Add Environment Variables

Click on your service → **"Variables"** tab → Add:

```
SECRET_KEY=django-insecure-GENERATE-A-NEW-ONE-HERE
DEBUG=False
DJANGO_SETTINGS_MODULE=camera_demo_backend.settings
ALLOWED_HOSTS=.railway.app
CORS_ALLOWED_ORIGINS=https://your-frontend.vercel.app
CSRF_TRUSTED_ORIGINS=https://your-frontend.vercel.app
```

**Generate SECRET_KEY:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

#### Step 5: Redeploy

Railway will automatically redeploy with the new environment variables.

#### Step 6: Create Superuser

In Railway dashboard:
1. Click on your service
2. Go to **"Settings"** → **"Deploy Logs"**
3. Click **"Open Shell"**
4. Run: `python manage.py createsuperuser`

✅ **Done!** Your backend is live at `https://your-app.railway.app`

---

### Method 2: Using Railway CLI

If you want to use the CLI, here's how to install it:

#### Windows Installation Options:

**Option A: PowerShell Script (Recommended)**
```powershell
# Run in PowerShell as Administrator
iwr https://railway.app/install.ps1 -useb | iex
```

**Option B: NPM (if npm is working)**
```bash
npm install -g @railway/cli
```

**Option C: Download Executable**
1. Go to https://github.com/railwayapp/cli/releases
2. Download `railway_windows_amd64.exe`
3. Rename to `railway.exe`
4. Move to a folder in your PATH (e.g., `C:\Windows\System32`)

#### After Installation:

```bash
# Login
railway login

# Link to project (if already created via dashboard)
railway link

# Or create new project
railway init

# Deploy
railway up

# Run commands
railway run python manage.py createsuperuser
```

---

## 🎯 Recommended Approach

**Use Method 1 (Dashboard)** - It's simpler and doesn't require CLI installation!

---

## 📝 Next Steps After Deployment

1. **Get your backend URL** from Railway dashboard
2. **Test admin panel**: `https://your-app.railway.app/admin`
3. **Update frontend** to use the Railway backend URL
4. **Test API endpoints** from your frontend

---

## ⚡ Quick Commands Reference

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(50))"

# Check if Railway CLI is installed
railway --version

# View logs (if using CLI)
railway logs

# Open project in browser (if using CLI)
railway open
```

---

## Need Help?

Check the detailed walkthrough in `railway_walkthrough.md` for more information!
