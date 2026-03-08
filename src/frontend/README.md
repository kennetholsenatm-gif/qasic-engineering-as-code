# QASIC Engineering-as-Code – Front end

Vite + React SPA that talks to the FastAPI backend. Run protocol, routing, pipeline, inverse design; view results and doc links.

## Setup

```bash
npm install
```

## Development

Start the API first (from repo root):

```bash
uvicorn app.main:app --reload --port 8000
```

Then start the front end (proxy will forward `/api` to the backend):

```bash
npm run dev
```

Open http://localhost:5173.

## Build

```bash
npm run build
```

Output is in `dist/`. To serve it from the FastAPI backend, copy `dist` contents to a folder the backend mounts (see app README).

## Env

- `VITE_API_BASE_URL` — API base URL (default: empty, so relative `/api` is used with the dev proxy).
