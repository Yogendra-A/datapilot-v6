# DataPilot

## Frontend

Run npm install and npm run dev for the frontend. The default UI uses safe local mock data.

To exercise the live API boundary, copy .env.example to .env.local, set VITE_USE_MOCK_DATA=false, and run npm run mock:backend in another terminal. Set VITE_API_BASE_URL to the reachable FastAPI or tunnel URL for the real backend.

Query requests allow up to 120 seconds. Status, schema, history, and evaluation requests time out after 15 seconds.
