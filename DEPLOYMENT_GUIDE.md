# Deployment Guide: Vercel + Render

## Prerequisites

- GitHub account
- Vercel account (free)
- Render account (free)
- Firebase project with service account key
- Gemini API key

---

## Part 1: Deploy Backend to Render

### Step 1: Prepare Repository

1. Make sure all code is committed to Git
2. Push to GitHub:
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

### Step 2: Create Render Web Service

1. Go to [https://render.com](https://render.com)
2. Sign up/Login with GitHub
3. Click **"New +"** → **"Web Service"**
4. Connect your GitHub repository
5. Configure:
   - **Name**: `simats-aqua-backend`
   - **Region**: Singapore (or closest to you)
   - **Branch**: `main`
   - **Root Directory**: (leave empty)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free

### Step 3: Add Environment Variables

In the "Environment" section, add these variables:

1. **API_SECRET_KEY**

   - Click "Add Environment Variable"
   - Key: `API_SECRET_KEY`
   - Value: Generate a secure key (e.g., use `openssl rand -hex 32`)

2. **GEMINI_API_KEY**

   - Key: `GEMINI_API_KEY`
   - Value: Your Google Gemini API key

3. **FIREBASE_KEY_JSON**
   - Key: `FIREBASE_KEY_JSON`
   - Value: Copy entire contents of `firebase-key.json` (paste as one line or use Render's secret file)

### Step 4: Deploy

1. Click **"Create Web Service"**
2. Wait 5-10 minutes for deployment
3. Once deployed, copy your backend URL (e.g., `https://simats-aqua-backend.onrender.com`)
4. Test it: Visit `https://your-backend-url.onrender.com/api/health`

**Note**: Free tier sleeps after 15 minutes of inactivity. First request may take 30-60 seconds.

---

## Part 2: Deploy Frontend to Vercel

### Step 1: Prepare Frontend Configuration

1. Create `.env.production` file in `frontend-react/`:

   ```bash
   cd frontend-react
   ```

2. Add your backend URL:

   ```
   VITE_API_BASE_URL=https://your-backend-url.onrender.com
   VITE_GEMINI_API_KEY=your_gemini_api_key
   ```

3. Commit changes:
   ```bash
   git add .
   git commit -m "Add production environment"
   git push
   ```

### Step 2: Update Frontend API Calls

If your frontend makes API calls, ensure they use `import.meta.env.VITE_API_BASE_URL`:

Example:

```javascript
const API_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
```

### Step 3: Deploy to Vercel

1. Go to [https://vercel.com](https://vercel.com)
2. Sign up/Login with GitHub
3. Click **"Add New..."** → **"Project"**
4. Import your GitHub repository
5. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend-react`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### Step 4: Add Environment Variables (Vercel)

1. Go to **Settings** → **Environment Variables**
2. Add:
   - **VITE_API_BASE_URL**: `https://your-backend-url.onrender.com`
   - **VITE_GEMINI_API_KEY**: Your Gemini API key
3. Make sure to select all environments (Production, Preview, Development)

### Step 5: Deploy

1. Click **"Deploy"**
2. Wait 2-3 minutes
3. Your frontend URL will be: `https://your-project.vercel.app`
4. Test the application!

---

## Part 3: Update CORS for Production

### Update Backend CORS Settings

Since your backend currently allows all origins (`allow_origins=["*"]`), it should work immediately.

For better security (optional):

1. Edit `backend/main.py`:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=[
           "https://your-project.vercel.app",
           "http://localhost:5173",  # for local dev
       ],
       allow_credentials=False,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
2. Push changes - Render will auto-deploy

---

## Part 4: Custom Domain (Optional)

### For Vercel (Frontend):

1. Go to Project Settings → Domains
2. Add your custom domain
3. Update DNS records as shown

### For Render (Backend):

1. Go to Settings → Custom Domain
2. Add `api.yourdomain.com`
3. Update DNS records

---

## Troubleshooting

### Backend Issues:

- **500 Error**: Check Render logs for Python errors
- **Module Not Found**: Ensure `requirements.txt` is correct
- **Firebase Error**: Verify `FIREBASE_KEY_JSON` env variable

### Frontend Issues:

- **API Connection Failed**: Check `VITE_API_BASE_URL` in Vercel settings
- **Build Failed**: Run `npm run build` locally first
- **Blank Page**: Check browser console for errors

### Commands to Test Locally:

```bash
# Backend
cd backend
python -m uvicorn main:app --reload

# Frontend
cd frontend-react
npm run build
npm run preview
```

---

## Monitoring & Updates

### Render:

- Auto-deploys on git push
- Check logs in Render dashboard
- Free tier: 750 hours/month

### Vercel:

- Auto-deploys on git push
- Check deployments in Vercel dashboard
- Free tier: Unlimited bandwidth for personal projects

---

## Security Checklist

- ✓ Environment variables set (not in code)
- ✓ `firebase-key.json` in `.gitignore`
- ✓ `.env` files in `.gitignore`
- ✓ API keys using platform secrets
- ✓ CORS configured for production domain
