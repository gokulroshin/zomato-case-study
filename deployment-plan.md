# Zomato Case Study: Deployment Plan

This document outlines the steps to deploy the application with the backend hosted on **Railway** and the frontend on **Vercel**.

## 1. Preparation

### 1.1 Decoupling Frontend & Backend
Currently, `frontend/api.js` points to `http://127.0.0.1:8000/api/v1` and the backend serves the frontend statically via `app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")`.
- Update `frontend/api.js` to point to the Railway backend URL dynamically.
- (Optional) Remove the `app.mount` line in `app/main.py` since Vercel will handle the frontend.

### 1.2 Update CORS Settings
In `app/main.py`, CORS is configured to `allow_origins=["*"]`. For production security, this should be updated to only allow the Vercel frontend domain once it is generated.

## 2. Backend Deployment (Railway)

1. **Create an account** on [Railway](https://railway.app/).
2. **New Project**: Click "New Project" -> "Deploy from GitHub repo".
3. **Select Repository**: Choose the Zomato case study repository.
4. **Environment Variables**: Go to the "Variables" tab in your Railway service and add:
   - `GROQ_API_KEY`: Your Groq API key (required for LLM features).
5. **Start Command**: Railway uses Nixpacks to automatically detect Python and `requirements.txt`. Under Settings -> Deploy -> Custom Start Command, enter:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
6. **Generate Domain**: Go to "Settings" -> "Environment" -> "Domains" and click "Generate Domain". Copy this URL (e.g., `https://your-app.up.railway.app`).

## 3. Frontend Deployment (Vercel)

1. **Update API Base URL**: In `frontend/api.js`, update `API_BASE_URL` to use the Railway domain generated in the previous step:
   ```javascript
   // Change this:
   // const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

   // To this:
   const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
       ? 'http://127.0.0.1:8000/api/v1' 
       : 'https://<your-railway-app-url>/api/v1'; // Replace with actual Railway URL
   ```
   *Commit and push this change to your repository before deploying the frontend.*
2. **Create an account** on [Vercel](https://vercel.com/).
3. **Add New Project**: Click "Add New..." -> "Project".
4. **Import Repository**: Import your GitHub repository.
5. **Configure Build Settings**:
   - **Framework Preset**: Other
   - **Root Directory**: `frontend` (Important: Since your HTML/JS files are in the `frontend` folder).
   - **Build Command**: Leave empty (as it's static HTML/JS).
   - **Install Command**: Leave empty.
   - **Output Directory**: Leave empty or set to `.`
6. **Deploy**: Click "Deploy". Vercel will generate a live domain for your frontend.

## 4. Post-Deployment Checklist

- [ ] Update Railway's CORS settings in `app/main.py` with the Vercel domain.
- [ ] Test the Vercel application to ensure it communicates correctly with the Railway backend.
- [ ] Verify that recommendations are successfully generated in the live environment.
