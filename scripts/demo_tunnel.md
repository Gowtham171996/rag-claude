# 5-Minute Public Demo — Free with ngrok

Your stack is already running locally. ngrok tunnels it to a public HTTPS URL
in one command — no AWS account, no billing, no teardown needed.

## Step 1 — Install ngrok (one-time)
Download from https://ngrok.com/download (Windows installer or zip)
Or with winget:
    winget install ngrok

## Step 2 — Sign up for free account
https://ngrok.com  →  sign up  →  copy your authtoken

## Step 3 — Authenticate (one-time)
    ngrok config add-authtoken YOUR_AUTHTOKEN

## Step 4 — Start the tunnel (while docker compose is running)
    ngrok http 8000

ngrok prints something like:
    Forwarding  https://abc123.ngrok-free.app -> http://localhost:8000

## Step 5 — Share these URLs for the demo
    https://abc123.ngrok-free.app/docs          ← Swagger UI (interactive)
    https://abc123.ngrok-free.app/api/v1/health ← Health check

## Demo curl commands (share with the audience)
    curl -X POST https://abc123.ngrok-free.app/api/v1/ingest-documents \
      -H "X-API-Key: my-secret-key-123" \
      -F "file=@gowtham-resume-LLM.pdf"

    curl -X POST https://abc123.ngrok-free.app/api/v1/query \
      -H "X-API-Key: my-secret-key-123" \
      -H "Content-Type: application/json" \
      -d '{"question": "What are Gowtham key skills?", "collection_name": "default"}'

## Cost: €0
## Setup time: 2 minutes
## Works for: unlimited 5-minute demos
