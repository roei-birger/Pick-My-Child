#!/bin/bash
# Script to initialize Git repository and push to GitHub

echo "🚀 Starting Git initialization..."

# 1. Remove existing git if any
echo "📁 Step 1: Removing old git repository..."
rm -rf .git

# 2. Initialize fresh git
echo "📁 Step 2: Initializing new git repository..."
git init

# 3. Configure git user (if needed)
echo "👤 Step 3: Configuring git user..."
git config user.name "Roei Birger"
git config user.email "roei.birger@example.com"  # Replace with your email

# 4. Add remote
echo "🔗 Step 4: Adding GitHub remote..."
git remote add origin https://github.com/roei-birger/Pick-My-Child.git

# 5. Add all files
echo "📝 Step 5: Adding all files..."
git add .

# 6. Commit
echo "💾 Step 6: Creating initial commit..."
git commit -m "Initial commit - pickmychild bot v1.0

Features:
- Face recognition with InsightFace
- Photo filtering by people
- Model improvement workflow
- Album support (batch processing)
- Filtering mode with UI lock
- Railway/Render deployment ready
"

# 7. Set main branch
echo "🌿 Step 7: Setting main branch..."
git branch -M main

# 8. Force push (since we're replacing everything)
echo "⬆️  Step 8: Pushing to GitHub..."
git push -f origin main

echo "✅ Done! Check your repository at:"
echo "   https://github.com/roei-birger/Pick-My-Child"
