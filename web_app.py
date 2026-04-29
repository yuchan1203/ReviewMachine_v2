"""
Legacy Streamlit app wrapper.

This file previously implemented a Streamlit-based UI. The project has
been migrated to a FastAPI backend with a static frontend served at
`/app/`. Keep this file as a shim that explains the migration.
"""

def main():
    print("This repository no longer runs via Streamlit.\n")
    print("Run the FastAPI server: `python -m uvicorn main:app --reload --port 8000`\n")
    print("Then open http://127.0.0.1:8000/app/")


if __name__ == "__main__":
    main()