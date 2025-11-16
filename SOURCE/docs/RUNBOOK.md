# Runbook – CS5200 Notes Assistant

This runbook explains how to set up, run, and demonstrate the assignment deliverable.

## 1. Setup

1. Install Python 3.10+.
2. (Recommended) create a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install project dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install and start [Ollama](https://ollama.com/download). Pull at least one open-source model:
   ```bash
   ollama pull llama3
   ollama serve  # runs the local API on port 11434
   ```
5. Initialize the database:
   ```bash
   python scripts/init_db.py
   ```

## 2. Launch Services

- **Backend API**:
  ```bash
  python -m backend.server
  ```
  The service listens on `http://127.0.0.1:5000` by default and exposes routes under `/api`.

- **Streamlit Frontend** (in a new terminal):
  ```bash
  streamlit run frontend/streamlit_app.py
  ```
  The interface opens in the default browser at `http://localhost:8501`.

## 3. Demonstration Script

1. Visit the Streamlit page.
2. Register a new user in the sidebar. Upon success, you will be logged in automatically.
3. Issue a natural-language command, for example:
   - “Create a note about the team sync saying we meet at 3 PM.”
   - “What did I note about the team sync?”
   - “Update note 1 to add that it is on Zoom.”
   - “Delete the note about groceries.”
4. Observe:
   - The agent summary displayed for each query.
   - The JSON payload showing the CRUD result.
   - The updated list of notes at the bottom of the page.

## 4. Configuration Reference

Set environment variables before running either process to customize behavior:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_DEBUG` | Enables Flask debug mode | `0` |
| `DATABASE_URL` | Database connection string | `sqlite:///backend/notes.db` |
| `JWT_SECRET_KEY` | Secret for JWT signing | random placeholder |
| `OLLAMA_BASE_URL` | URL of Ollama API | `http://localhost:11434` |
| `OLLAMA_MODEL` | Model name to query | `llama3` |
| `BACKEND_URL` | Base URL for Streamlit to call | `http://127.0.0.1:5000` |
| `API_PREFIX` | API prefix path | `/api` |

Create a `.env` file (optional) and export variables via your shell if needed.

## 5. Troubleshooting

- **Backend cannot reach Ollama**: ensure `ollama serve` is running and the model is downloaded. Verify connectivity with `curl http://127.0.0.1:11434/api/tags`.
- **403 Forbidden on registration**: macOS AirPlay Receiver sometimes binds to `localhost:5000`. Use the default `http://127.0.0.1:5000` endpoint or disable AirPlay Receiver.
- **JWT expired**: log in again or increase `ACCESS_TOKEN_EXPIRES_MINUTES`.
- **Database locked**: stop other processes using the SQLite file or switch to PostgreSQL/MySQL by changing `DATABASE_URL`.
- **CORS errors**: the backend enables CORS by default; double-check `BACKEND_URL` and `API_PREFIX` values.

## 6. Submission Notes

- Rename the enclosing folder to `PROG_ASSIGN2_<CRN>_<700ID>` before zipping.
- Include screenshots, this runbook, and any additional evidence requested by the instructor.
- Document the exact Ollama model and version used during your demo.

