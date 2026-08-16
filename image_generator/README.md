# AI Image Generator

A one-page Flask app that generates images from a text prompt using OpenAI's
Images API (`gpt-image-1`). Type a description, pick a size, and the image
renders on the page — no reload.

## Tech Stack

- Python + Flask (backend, calls the OpenAI API so the key never reaches the browser)
- HTML (Jinja2 template)
- CSS (dark theme, responsive image grid)
- Vanilla JS (`fetch` to call `/generate` and inject the returned image)

## Setup & Run

1. **Create a virtual environment and install dependencies**

   ```bash
   python -m venv venv
   venv\Scripts\activate   # on Windows
   pip install -r requirements.txt
   ```

2. **Get an OpenAI API key**

   - Create/copy a key from the [OpenAI API keys page](https://platform.openai.com/api-keys).
   - Image generation is billed per image on your OpenAI account — check
     [pricing](https://openai.com/api/pricing/) before generating a lot of images.

3. **Configure environment variables**

   ```bash
   copy .env.example .env
   ```

   Edit `.env` and set `OPENAI_API_KEY` to your key. `.env` is already
   git-ignored at the repo root, so it won't be committed.

4. **Run the app**

   ```bash
   python app.py
   ```

   Open `http://127.0.0.1:5001` in your browser. (Port 5001, so it can run
   alongside the Mini Art Inspiration Board app on port 5000.)

## How it works

- `POST /generate` receives `{ prompt, size }` as JSON from the browser.
- The Flask route calls `client.images.generate(model="gpt-image-1", ...)`
  server-side, using the API key from your environment — the key is never
  sent to the browser.
- OpenAI returns the image as base64 (`b64_json`); Flask wraps it in a
  `data:image/png;base64,...` URL and sends it back as JSON.
- The frontend JS drops that URL straight into an `<img src="...">`, so the
  image appears without a page reload, and adds a download link.

## Notes / Next steps

- Errors (invalid key, no billing, content-policy rejection) are caught and
  shown in the UI instead of crashing the server.
- Prompts are capped at 1000 characters as a basic guard.
- Ideas to extend: save generated images to disk or Firestore (like the
  other app in this repo), add a history/gallery view, add a "regenerate"
  button, or let users pick a style preset.
