# 🚀 Quick Deploy to Railway.app

## Step 1: Prepare Repository

```bash
# Initialize git (if not already)
git init

# Add all files
git add .

# Commit
git commit -m "Ready for deployment"

# Create GitHub repo and push
git remote add origin https://github.com/YOUR_USERNAME/pickmychild.git
git branch -M main
git push -u origin main
```

## Step 2: Deploy on Railway

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Choose **"Deploy from GitHub repo"**
4. Select your `pickmychild` repository
5. Railway will automatically:
   - Detect it's a Python project
   - Install dependencies from `requirements.txt`
   - Run `python main.py`

## Step 3: Configure Environment Variables

In Railway dashboard → Variables tab, add:

```bash
TELEGRAM_BOT_TOKEN=8392371227:AAFxW-WQJidQnk2R2SlitVoNBpVSBP8EkFU
FACE_DETECTION_CONFIDENCE=0.4
FACE_MATCH_THRESHOLD=0.45
PHOTO_ACCUMULATION_TIMEOUT=5.0
ENABLE_EVENTS_FEATURE=false
LOG_LEVEL=INFO
```

## Step 4: That's it! 🎉

Your bot is now running 24/7!

- View logs in Railway dashboard
- Monitor uptime
- Auto-deploys on every git push

## 📊 Railway Free Tier Limits

- ✅ 500 hours/month (~20 days)
- ✅ 1GB RAM
- ✅ 1GB Storage
- ✅ Always-on (doesn't sleep)

**Tip:** For full 24/7 coverage, create a second Railway account and alternate between them! 😉

## 🔧 Useful Commands

```bash
# View logs
railway logs

# Open dashboard
railway open

# SSH into container
railway shell
```

## 🆘 Need Help?

- Railway Docs: https://docs.railway.app
- Project README: See `DEPLOYMENT.md` for detailed guide
