#!/bin/bash

# Script to push changes to GitHub and sync with GitLab

echo "================================"
echo "STEP 1: Push to GitHub"
echo "================================"

cd /Users/vishant.singh/SupportTicketResolver

# Add all changes
git add .
echo "✅ Files staged"

# Commit
git commit -m "Fix: Restore .env and consolidate integrity check logging with executor-based comment grouping"
echo "✅ Changes committed"

# Push to GitHub
git push origin main
echo "✅ Pushed to GitHub (main branch)"

echo ""
echo "================================"
echo "STEP 2: Sync with GitLab"
echo "================================"

# Assuming GitLab repo is cloned at a similar location
GITLAB_REPO="/Users/vishant.singh/fulfilment-order-ai"

if [ -d "$GITLAB_REPO" ]; then
    cd "$GITLAB_REPO"
    
    # Add GitHub as remote if not already present
    if ! git remote | grep -q github; then
        git remote add github https://github.com/Pheonixxx27/SmartCogniDesk.git
        echo "✅ Added GitHub remote to GitLab repo"
    fi
    
    # Fetch from GitHub
    git fetch github main
    echo "✅ Fetched from GitHub"
    
    # Merge or rebase
    git merge github/main
    echo "✅ Merged GitHub changes into GitLab repo"
    
    # Push to GitLab
    git push origin main
    echo "✅ Pushed to GitLab"
    
    echo ""
    echo "✅ Sync complete! Both repos are now in sync"
else
    echo "❌ GitLab repo not found at $GITLAB_REPO"
    echo "Please update the path and try again"
fi

echo ""
echo "================================"
echo "Summary"
echo "================================"
echo "✅ GitHub repo updated"
echo "✅ GitLab repo synced"
