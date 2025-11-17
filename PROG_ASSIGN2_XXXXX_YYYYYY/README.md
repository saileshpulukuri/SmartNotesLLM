# CS5200 Programming Assignment 2 – Personal Notes Assistant

This repository implements the multi-user notes management system required for the assignment. It combines a Flask backend (with SQLite by default) and a Streamlit frontend powered by an open-source LLM via Ollama. Natural-language commands are translated into CRUD operations on the `users` and `notes` tables described in the specification.

## Project Layout

- `backend/`: Flask application, database models, and LLM agent.
- `frontend/`: Streamlit interface for registration, login, and natural-language control.
- `scripts/`: helper utilities (database initialization).
- `docs/`: additional documentation (runbook, architecture notes).
- `requirements.txt`: Python dependencies for backend and frontend.

## Features

- Multi-user registration and authentication backed by JWT tokens.
- CRUD API for `users` and `notes` using SQLAlchemy models matching the assignment schema.
- Natural-language endpoint that calls an open-source LLM (via Ollama) to infer the desired action.
- Streamlit web UI to manage accounts and send natural-language queries.
- Keyword-based fallback parser when no LLM runtime is available (keeps manual testing possible).

## Prerequisites

1. Python 3.10 or newer.
2. [Ollama](https://ollama.com/) installed locally with at least one model pulled (the defaults assume `llama3`).
3. Optional: virtual environment tooling such as `venv` or `conda`.

## Quick Start

1. **Create and activate a virtual environment (recommended)**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Pull an open-source model for Ollama** (only necessary once):
   ```bash
   ollama pull llama3
   ```
4. **Initialize the database**:
   ```bash
   python scripts/init_db.py
   ```
5. **Run the backend** (defaults to `http://127.0.0.1:5000`):
   ```bash
   python -m backend.server
   ```
6. **Run the Streamlit frontend** (opens on `http://localhost:8501`):
   ```bash
   streamlit run frontend/streamlit_app.py
   ```

## Environment Configuration

Override defaults by exporting variables before running the apps:

- `FLASK_DEBUG=1` – enables auto-reload.
- `DATABASE_URL=sqlite:////absolute/path/to/notes.db` – change database location/back-end.
- `JWT_SECRET_KEY`, `FLASK_SECRET_KEY` – replace with secure random values for production.
- `OLLAMA_BASE_URL` – point to remote Ollama host if using a different machine.
- `OLLAMA_MODEL` – set to the model name you pulled (`llama3`, `mistral`, etc.).
- `BACKEND_URL` – set in Streamlit when backend runs on a different host/port (defaults to `http://127.0.0.1:5000`; avoid `http://localhost:5000` if macOS AirPlay Receiver is using that port).

Create a `.env` file (see `.env.example`) or export variables in the shell.

## Usage Workflow

1. Register a new user or log in with existing credentials.
2. After authentication, write natural-language instructions such as:
   - “Create a new note about the project demo saying the slides are due Friday.”
   - “What did I note about the budget review?”
   - “Update note 2 and change the message to include the Zoom link.”
   - “Delete the reminder about groceries.”
3. The backend interprets the intent, executes the corresponding CRUD operation, and returns results. Streamlit shows the agent’s summary, JSON response, and refreshed notes list.

## Testing Without an LLM

If Ollama is not running, the backend falls back to a deterministic keyword parser. The behavior is limited but allows manual verification of the REST endpoints. For full credit, demonstrate the app with Ollama enabled and document which model you used.

## Submission Checklist

- Update the folder name to `PROG_ASSIGN2_<CRN>_<700ID>`.
- Include this README and any supplementary docs (e.g., `docs/RUNBOOK.md`).
- Provide screenshots or recordings if requested by the instructor.
- Zip the folder and upload per course instructions.

## Troubleshooting

- **Ollama connection errors**: ensure the Ollama service is running (`ollama serve`) and that the `OLLAMA_BASE_URL` environment variable points to it.
- **JWT errors**: delete the `.venv` or `.pyc` files if configuration changes aren’t applied; ensure secrets are consistent.
- **Database locked**: close other applications accessing `notes.db`; consider switching to PostgreSQL or MySQL by updating `DATABASE_URL`.

## License

This project is delivered for academic coursework. Adapt and extend as needed for your assignment submission.

