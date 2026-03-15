# Deployment Guide for Render

This guide explains how to deploy the Trading Bot backend to Render.

## Prerequisites

- A Render account (free or paid)
- Git repository (GitHub, GitLab, or Bitbucket)
- Your code pushed to the repository

---

## Step 1: Prepare Your Repository

### Update `.gitignore`

Ensure the following are in your `.gitignore`:

```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
.venv/
venv/

# IDE
.vscode/
.idea/

# Environment variables
.env
.env.local

# Large files (optional - you may want to include some models)
*.keras
*.h5
artifacts/models/*.keras

# Outputs
outputs/
*.log
```

### Include Model Files (Optional)

If you want to deploy with pre-trained models, you have two options:

**Option A: Commit models to Git** (for small models)
```bash
git add backend/tradingBot/artifacts/models/*.keras
git commit -m "Add pre-trained models"
git push
```

**Option B: Download models on startup** (recommended for large models)
Create a `download_models.sh` script:

```bash
#!/bin/bash
# Download models from cloud storage
# Example using AWS S3:
aws s3 cp s3://your-bucket/models/ tradingBot/artifacts/models/ --recursive

# Or using Google Drive, Dropbox, etc.
```

---

## Step 2: Create a Web Service on Render

### 2.1 Navigate to Render Dashboard

1. Go to [https://render.com](https://render.com)
2. Sign in to your account
3. Click **"New +"** → **"Web Service"**

### 2.2 Connect Your Repository

1. Choose your Git provider (GitHub, GitLab, or Bitbucket)
2. Select your repository
3. Render will auto-detect it's a Python project

### 2.3 Configure the Service

| Setting | Value |
|---------|-------|
| **Name** | `trading-bot-backend` (or your choice) |
| **Region** | Choose closest to your users |
| **Branch** | `main` (or your deployment branch) |
| **Root Directory** | `backend` |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 2` |

### 2.4 Choose Instance Type

| Plan | Use Case | Cost |
|------|----------|------|
| **Free** | Testing, development | $0/month |
| **Starter** | Small production workloads | $7/month |
| **Standard** | Production with better performance | $25+/month |

**Note:** Free instances spin down after 15 minutes of inactivity. The first request after spin-down will take 30-60 seconds to respond.

---

## Step 3: Configure Environment Variables

In the Render dashboard, go to **Environment** tab and add:

| Variable | Value | Description |
|----------|-------|-------------|
| `PORT` | `8000` | Render sets this automatically |
| `PYTHON_VERSION` | `3.11.0` | Python version |

Optional variables for production:

| Variable | Value | Description |
|----------|-------|-------------|
| `LOG_LEVEL` | `info` | Logging level |
| `ALLOWED_ORIGINS` | `https://your-frontend.com` | CORS origins |

---

## Step 4: Configure Health Check

Render will automatically use the `HEALTHCHECK` from your Dockerfile.

**Health Check Endpoint:** `/api/health`

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-03-15T12:00:00.000Z"
}
```

---

## Step 5: Deploy

1. Click **"Create Web Service"**
2. Render will start building your application
3. Monitor the build logs in the dashboard
4. Once deployed, you'll see your service URL: `https://trading-bot-backend.onrender.com`

---

## Step 6: Test the Deployment

### Test Health Endpoint

```bash
curl https://your-app.onrender.com/api/health
```

### Test Models Endpoint

```bash
curl https://your-app.onrender.com/api/models
```

### Test Prediction

```bash
curl -X POST https://your-app.onrender.com/api/predict \
  -H "Content-Type: application/json" \
  -d '{"symbol": "AAPL"}'
```

---

## Step 7: Deploy the Frontend

### Option A: Deploy to Vercel

1. Go to [https://vercel.com](https://vercel.com)
2. Import your GitHub repository
3. Set **Root Directory** to `frontend`
4. Add environment variable:
   - `REACT_APP_API_URL=https://your-app.onrender.com`
5. Deploy

### Option B: Deploy to Netlify

1. Go to [https://netlify.com](https://netlify.com)
2. Connect your GitHub repository
3. Set **Base directory** to `frontend`
4. Set **Build command** to `npm run build`
5. Set **Publish directory** to `frontend/build`
6. Add environment variable:
   - `REACT_APP_API_URL=https://your-app.onrender.com`
7. Deploy

### Option C: Deploy to Render (Static Site)

1. In Render dashboard, create **New +** → **Static Site**
2. Connect your repository
3. Set **Root Directory** to `frontend`
4. Set **Build Command** to `npm install && npm run build`
5. Set **Publish Directory** to `build`
6. Add environment variable:
   - `REACT_APP_API_URL=https://your-app.onrender.com`

---

## Troubleshooting

### Build Fails

**Error: Module not found**
```
ModuleNotFoundError: No module named 'tradingBot'
```

**Solution:** Ensure the Root Directory is set to `backend` and the `tradingBot` folder is inside it.

**Error: TensorFlow installation fails**
```
ERROR: Failed building wheel for tensorflow
```

**Solution:** The Dockerfile includes necessary system dependencies. Make sure you're using the provided Dockerfile.

### Runtime Errors

**Error: Model not found**
```
Model not found for symbol: AAPL
```

**Solution:** 
1. Check if models are in the repository
2. Or download models on startup using a build script
3. Or upload models via Render's dashboard (Files tab)

**Error: CORS issues from frontend**
```
Access to fetch at '...' from origin '...' has been blocked by CORS policy
```

**Solution:** Update `allow_origins` in `backend/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://your-frontend.vercel.app",  # Add your frontend URL
    ],
    # ...
)
```

### Performance Issues

**Slow first request (Free tier)**
- Free instances spin down after 15 minutes of inactivity
- Upgrade to Starter plan ($7/month) for always-on instances

**Slow model predictions**
- Models are loaded on-demand (first prediction is slower)
- Consider pre-loading models at startup
- Upgrade to a larger instance type

---

## Monitoring

### Render Dashboard

Monitor your service in the Render dashboard:
- **Metrics**: CPU, Memory, Request count
- **Logs**: Real-time application logs
- **Deployments**: Deployment history and status

### Health Check Monitoring

Render automatically monitors the health check endpoint. If health checks fail consecutively, Render will restart your service.

### Logging

The application logs to stdout/stderr automatically. View logs in:
- Render Dashboard → **Logs** tab
- Or use Render CLI: `render logs -s your-service-id`

---

## Cost Optimization

### Free Tier Tips

1. **Use Free PostgreSQL** (if you add a database)
2. **Optimize model loading** - cache models in memory
3. **Use CDN** for static frontend assets
4. **Monitor usage** - stay within free tier limits

### Paid Tier Recommendations

1. **Starter Plan** ($7/month) - Always-on backend
2. **Add Redis** for caching ($7/month)
3. **Use Render's PostgreSQL** for data persistence ($7/month)

---

## CI/CD with Render

Render automatically deploys when you push to your configured branch.

### Auto-Deploy Settings

1. Go to **Settings** → **Auto-Deploy**
2. Enable/disable auto-deploy
3. Configure branch to deploy from

### Manual Deploy

```bash
# Push to trigger deployment
git push origin main

# Render will automatically build and deploy
```

---

## Security Best Practices

### 1. Use Environment Variables for Secrets

```python
import os

SECRET_KEY = os.getenv("SECRET_KEY")
API_KEY = os.getenv("API_KEY")
```

### 2. Enable HTTPS

Render provides free SSL certificates automatically.

### 3. Add API Authentication (Production)

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401, detail="Invalid API key")
```

### 4. Rate Limiting

Install slowapi for rate limiting:

```bash
pip install slowapi
```

```python
from slowapi import SlowApi, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = SlowApi(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.get("/api/predict")
@limiter.limit("10/minute")
async def predict(request: Request):
    # ...
```

---

## Backup and Recovery

### Backup Models

1. Store models in cloud storage (S3, Google Cloud Storage)
2. Use Render's persistent disk (paid feature)
3. Version control your model files (if small enough)

### Database Backup

If you add a PostgreSQL database:
1. Enable automatic backups in Render dashboard
2. Use `pg_dump` for manual backups
3. Store backups in external storage

---

## Support

- **Render Docs**: [https://render.com/docs](https://render.com/docs)
- **Render Community**: [https://community.render.com](https://community.render.com)
- **Render Status**: [https://status.render.com](https://status.render.com)

---

## Checklist

- [ ] Code pushed to Git repository
- [ ] `backend/requirements.txt` is up to date
- [ ] `backend/Dockerfile` is configured
- [ ] Models are available (committed or downloadable)
- [ ] Environment variables configured
- [ ] CORS settings updated for production
- [ ] Frontend deployed and connected to backend
- [ ] Health check passing
- [ ] Monitoring enabled
- [ ] Backup strategy in place

---

**Congratulations!** Your Trading Bot is now deployed to Render! 🚀
