# Quick Start: Docker Verification

## TL;DR

```bash
# Run this single command to verify everything works:
./test-e2e.sh
```

## What It Tests

✅ Health check endpoint
✅ Score API functionality
✅ Data persistence
✅ Container restarts
✅ Volume mounting
✅ Environment variables

## Expected Duration

⏱️ 2-3 minutes

## If Tests Pass

Your Docker deployment is production-ready! Deploy with:

```bash
docker-compose up -d
```

## If Tests Fail

Check `DOCKER-VERIFICATION.md` for troubleshooting steps.

## Documentation

- **test-e2e.sh**: Automated verification script
- **DOCKER-VERIFICATION.md**: Complete manual guide
- **VERIFICATION-STATUS.md**: Detailed status report

---

**Ready to verify?** Run: `./test-e2e.sh`
