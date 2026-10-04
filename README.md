# Fake Job Detector

## Deploy the API to Render

1. Create a Render Blueprint from this repository and use the included `render.yaml`, or create a Python web service with **Root Directory** set to `backend`.
2. Set the required `MONGO_URL` environment variable to your MongoDB connection string. Ensure your MongoDB network access rules allow connections from Render.
3. Set `CORS_ORIGINS` to the exact Vercel frontend origin, such as `https://your-project.vercel.app`. For multiple origins, separate them with commas; do not include URL paths or a trailing slash.
4. Deploy and confirm `https://<your-render-service>.onrender.com/api/health` returns a healthy response.

The Render service installs `backend/requirements.txt` and starts with Uvicorn on Render's assigned port. Model artifacts are loaded from the tracked `ml/models` directory in the repository.

## Deploy the frontend to Vercel

1. Import this repository into Vercel and set **Root Directory** to `frontend`.
2. Set the `VITE_API_URL` environment variable to the Render service origin, for example `https://your-render-service.onrender.com` (do not append `/api/v1`).
3. Build with `npm run build` and use `dist` as the output directory. Vercel detects Vite automatically; `frontend/vercel.json` keeps client-side routes on the app entry point.
4. After the Vercel deployment is created, add its origin to the Render service's `CORS_ORIGINS` environment variable and redeploy the API.

For local development, the frontend defaults to `http://127.0.0.1:8000` and the backend allows the Vite localhost origins. Copy `backend/.env.example` to `backend/.env` and set `MONGO_URL` if you need MongoDB-backed job storage.
