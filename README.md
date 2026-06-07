# AI Karaoke Performance Assistant

Minimal full-stack scaffold for a karaoke workflow:

- `backend/`: FastAPI services and API endpoints
- `frontend/`: React + Vite performance-mode UI

## Backend

Install dependencies:

```bash
pip install -r backend/requirements.txt
```

Run the API:

```bash
uvicorn backend.app.main:app --reload
```

API endpoints:

- `GET /health`
- `POST /api/extract-audio`
- `POST /api/analyze-audio`
- `POST /api/song-structure`
- `POST /api/key-recommendation`
- `POST /api/section-timestamps`

## Frontend

Install dependencies:

```bash
cd frontend
npm install
```

Run the UI:

```bash
npm run dev
```

Optional environment variable:

```bash
VITE_API_BASE_URL=http://localhost:8000
```
