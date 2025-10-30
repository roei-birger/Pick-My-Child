# Railway Deployment - Low Memory Configuration

## Problem
Railway's free tier has 1GB RAM limit. The original `buffalo_l` model uses too much memory and causes OOM (Out Of Memory) crashes.

## Solution
Optimized for low memory usage:

### 1. Model Changes
- **buffalo_l → buffalo_sc** (Small & Compact model)
  - `buffalo_l`: ~600MB memory
  - `buffalo_sc`: ~200MB memory
  - Still provides good accuracy for face recognition

### 2. Detection Settings
- Reduced detection size: 640x640 → 320x320
- CPU-only mode (no GPU context overhead)

### 3. Docker Optimizations
- Purge pip cache after installation
- Clean apt cache
- Memory-efficient environment variables

### 4. Environment Variables in Railway

Add these in Railway **Settings → Variables**:

```env
TELEGRAM_BOT_TOKEN=your_token_here
FACE_DETECTION_CONFIDENCE=0.4
FACE_MATCH_THRESHOLD=0.45
PHOTO_ACCUMULATION_TIMEOUT=5.0
ENABLE_EVENTS_FEATURE=false
PYTHONUNBUFFERED=1
MALLOC_TRIM_THRESHOLD_=100000
MALLOC_MMAP_THRESHOLD_=100000
LOG_LEVEL=INFO
```

## Expected Memory Usage

With these optimizations:
- **Startup**: ~300-400MB
- **During face detection**: ~500-700MB
- **Idle**: ~250-350MB

This should fit comfortably within Railway's 1GB limit.

## Trade-offs

✅ **Pros:**
- Fits in Railway free tier
- Still accurate for most faces
- Faster detection (smaller model)

⚠️ **Cons:**
- Slightly lower accuracy on difficult faces
- May miss very small faces
- Smaller detection area (320x320)

## Monitoring

Check Railway logs for:
- Memory usage warnings
- OOM crashes
- Slow response times

If still having OOM issues, consider:
1. Upgrade to Railway Pro ($5/month) for 2GB RAM
2. Use Render.com (512MB-1GB depending on plan)
3. Optimize further (lazy loading, process per request)

## Testing

After deployment, test with:
1. Single photo filtering
2. Batch processing (10+ photos)
3. Adding new people with multiple photos
4. Multiple concurrent users

Monitor Railway metrics during testing.
