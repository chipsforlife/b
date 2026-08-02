# Mini Art Inspiration Board

A one-page Flask web app for saving music and visual art inspiration. Add an item, choose a category, mark favorites, and delete items — all data is stored in Firebase Firestore so it survives a page refresh.

## Features

- Add a new inspiration item with a title and category (Music or Visual Art)
- View all saved items on the board
- Mark/unmark an item as a favorite (favorites are highlighted and sorted to the top)
- Delete an item
- Data is persisted in Firebase Firestore, so items remain after refreshing the page

## Tech Stack

- Python + Flask
- HTML / CSS (Jinja2 templates)
- Firebase Firestore (via `firebase-admin`)

## Setup & Run Instructions

1. **Clone the repository**

   ```bash
   git clone https://github.com/chipsforlife/a.git
   cd a
   ```

2. **Create a virtual environment and install dependencies**

   ```bash
   python -m venv venv
   venv\Scripts\activate   # on Windows
   pip install -r requirements.txt
   ```

3. **Set up Firebase**

   - Go to the [Firebase Console](https://console.firebase.google.com/) and create a project.
   - Enable **Firestore Database**.
   - Go to *Project Settings → Service Accounts* and generate a new private key. This downloads a JSON file — **do not commit this file to GitHub**.
   - Save the JSON file somewhere on your machine (outside the repo, or it's already git-ignored if placed in the project folder).

4. **Configure environment variables**

   - Copy `.env.example` to `.env`:

     ```bash
     copy .env.example .env
     ```

   - Edit `.env` and set `GOOGLE_APPLICATION_CREDENTIALS` to the full path of your downloaded service account JSON file.

5. **Run the app**

   ```bash
   python app.py
   ```

   Open `http://127.0.0.1:5000` in your browser.

## Project Structure

```
app.py
templates/
    index.html
static/
    style.css
requirements.txt
.gitignore
.env.example
README.md
```

## Screenshot

![Mini Art Inspiration Board screenshot](screenshot.png)
