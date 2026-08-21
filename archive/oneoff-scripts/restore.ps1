# SceneIQ Emergency Restore
git fetch origin
git checkout main
git reset --hard origin/stable-backup
git push origin main --force
cd frontend
npm run build
cd ..
git add -f frontend/dist
git commit -m "restore: rollback to stable"
git push origin main
