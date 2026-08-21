# SceneIQ Deployment Notes

## Current Status
- ✅ Works perfectly locally
- ⏳ Cloud deployment postponed

## Issues Encountered
- Prisma Python client generation in Render build environment
- Build/runtime environment differences

## Solutions to Try Later
1. Use Docker container for consistent environment
2. Try Railway.app or Fly.io (better Python support)
3. Pre-generate Prisma client and commit it
4. Use different ORM (SQLAlchemy) instead of Prisma

## Local Development
```bash
# Start local server
python -m uvicorn src.main:app --reload

# Run tests
pytest tests/ -v

# Generate coverage
pytest --cov=src --cov-report=html
```

## For Now
Focus on local development and testing.
Deployment can be tackled later with fresh perspective.