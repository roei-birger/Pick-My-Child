# Git Push Commands - Run these in order

## Step 1: Remove old git
```bash
cd C:/Dev/pickmychild
rm -rf .git
```

## Step 2: Initialize fresh repository
```bash
git init
```

## Step 3: Configure git (replace with your email)
```bash
git config user.name "Roi Birger"
git config user.email "rbirger123@gmail.com"
```

## Step 4: Add GitHub remote
```bash
git remote add origin https://github.com/roei-birger/Pick-My-Child.git
```

## Step 5: Add all files
```bash
git add .
```

## Step 6: Check what will be committed
```bash
git status
```

## Step 7: Create initial commit
```bash
git commit -m "Initial commit - pickmychild bot v1.0

Features:
- Face recognition with InsightFace
- Photo filtering by people
- Model improvement workflow
- Album support (batch processing)
- Filtering mode with UI lock
- Railway/Render deployment ready
"
```

## Step 8: Set main branch
```bash
git branch -M main
```

## Step 9: Force push (replaces everything in GitHub)
```bash
git push -f origin main
```

## ✅ Verify
Go to: https://github.com/roei-birger/Pick-My-Child

---

## 🚨 If you get authentication error:

### Option 1: Use Personal Access Token
1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select "repo" scope
4. Copy the token
5. Use it as password when pushing:
   ```bash
   git push -f origin main
   # Username: roei-birger
   # Password: YOUR_TOKEN_HERE
   ```

### Option 2: Use GitHub CLI
```bash
gh auth login
git push -f origin main
```

### Option 3: Use SSH
```bash
git remote set-url origin git@github.com:roei-birger/Pick-My-Child.git
git push -f origin main
```

---

## 📝 Files that will be uploaded:

- ✅ All Python code (handlers, services, utils)
- ✅ Configuration files (config.py, .env.example)
- ✅ Dependencies (requirements.txt)
- ✅ Deployment files (railway.json, Procfile, render.yaml)
- ✅ Documentation (README.md, DEPLOYMENT.md, etc.)
- ❌ .env (ignored - contains secrets!)
- ❌ venv/ (ignored - too large)
- ❌ *.db (ignored - local database)
- ❌ uploads/ (ignored - user data)

---

## 🎯 After pushing:

### Deploy to Railway:
1. Go to https://railway.app
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose "Pick-My-Child"
5. Add environment variables (from .env)
6. Deploy! 🚀

### Deploy to Render:
1. Go to https://render.com
2. Click "New +"
3. Select "Web Service"
4. Connect "Pick-My-Child" repo
5. Add environment variables
6. Deploy! 🚀
