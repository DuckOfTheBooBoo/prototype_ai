# Deployment Guide

This guide explains how to deploy the Fraud Detection application as a monolithic web app to Railway.

## Prerequisites

1. HuggingFace account and uploaded model artifacts
2. Railway account
3. Node.js and pnpm/npm installed locally (for building frontend)

## Step 1: Upload Models to HuggingFace

```bash
# Login to HuggingFace
huggingface-cli login

# Upload artifacts
python upload_artifacts.py --repo-id "your-username/fraud-detection-model"
```

## Step 2: Build Frontend Locally

```bash
cd frontend
pnpm install
pnpm build
cd ..
```

This creates `frontend/dist` with the built frontend files.

## Step 3: Deploy to Railway

### Option A: Via Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Deploy
railway up
```

### Option B: Via Railway Dashboard

1. Go to https://railway.app
2. Create a new project
3. Connect your GitHub repository
4. Railway will auto-detect Python and use:
   - **Build command**: Automatic (installs from requirements.txt)
   - **Start command**: `gunicorn --chdir . --bind 0.0.0.0:$PORT app:app --worker-class eventlet --workers 2`

### Set Environment Variables

In Railway dashboard, add these variables:

```
HF_REPO_ID=your-username/fraud-detection-model
SECRET_KEY=your-secure-secret-key-here
WEBSOCKET_PATH=/socket.io
```

Optional variables:
```
FLASK_DEBUG=false
WEBSOCKET_URL=https://your-app.railway.app
```

## Step 4: Verify Deployment

Once deployed, visit your Railway URL:

- `https://your-app.railway.app/` - Should serve the frontend
- `https://your-app.railway.app/health` - Should return `{"status": "ok"}`
- `https://your-app.railway.app/config` - Should return WebSocket configuration
- `https://your-app.railway.app/api` - Should return API information

## How It Works

### Monolithic Architecture

The application serves both the API and frontend from a single Flask process:

1. **Frontend**: Built Vue.js app is served from `frontend/dist`
2. **API**: Flask routes handle `/predict`, `/health`, `/config`
3. **WebSocket**: Socket.IO handles real-time prediction streaming
4. **Models**: Loaded from HuggingFace at startup (or from local `artifacts/`)

### Route Priority

```
/api              -> API information
/predict          -> Prediction endpoint
/health           -> Health check
/config           -> WebSocket configuration
/<any-path>       -> Frontend static files or index.html (SPA)
```

### Model Loading

Models are loaded lazily on first prediction request:

1. If `HF_REPO_ID` is set: Download from HuggingFace Hub
2. Otherwise: Load from local `artifacts/` folder

## Troubleshooting

### Frontend not showing

**Symptom**: Root `/` returns JSON instead of HTML

**Solution**: Make sure frontend is built before deploying:
```bash
cd frontend && pnpm build
```

The `frontend/dist` folder must exist and contain `index.html`.

### Models not loading

**Symptom**: Predictions fail with model loading errors

**Solutions**:
1. Check `HF_REPO_ID` environment variable is set correctly
2. Verify HuggingFace repository is public or you have authentication
3. Check Railway logs for model download errors

### WebSocket connection fails

**Symptom**: Frontend can't connect to WebSocket

**Solutions**:
1. Check CORS settings in `app.py` (currently allows all origins)
2. Verify `WEBSOCKET_PATH` matches frontend configuration
3. Check Railway logs for WebSocket errors

## Local Development

To run locally:

```bash
# Build frontend
cd frontend && pnpm build && cd ..

# Set environment variables
export HF_REPO_ID="your-username/fraud-detection-model"
export SECRET_KEY="dev-secret-key"

# Run
python app.py
```

Visit http://localhost:5000

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│           Railway Deployment            │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────────────────────┐   │
│  │     Flask App (app.py)          │   │
│  │  ┌──────────────────────────┐   │   │
│  │  │  Frontend (Vue.js SPA)   │   │   │
│  │  │  from frontend/dist/     │   │   │
│  │  └──────────────────────────┘   │   │
│  │  ┌──────────────────────────┐   │   │
│  │  │  API Routes              │   │   │
│  │  │  - /predict              │   │   │
│  │  │  - /health               │   │   │
│  │  │  - /config               │   │   │
│  │  └──────────────────────────┘   │   │
│  │  ┌──────────────────────────┐   │   │
│  │  │  WebSocket (Socket.IO)   │   │   │
│  │  │  - Real-time streaming   │   │   │
│  │  └──────────────────────────┘   │   │
│  └─────────────────────────────────┘   │
│                │                        │
│                ↓                        │
│  ┌─────────────────────────────────┐   │
│  │  HuggingFace Hub                │   │
│  │  Model Artifacts                │   │
│  └─────────────────────────────────┘   │
│                                         │
└─────────────────────────────────────────┘
```
