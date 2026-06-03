# PDF Tools — Internal Streamlit App

Two tools for your team:
- **Split PDF** — split a mail-merge PDF into individually named files using an Excel recipient list
- **Merge PDFs** — merge PDFs from multiple folders (letters, plans, notices, etc.) matched by filename

---

## Running locally

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
streamlit run app.py
```

Then open http://localhost:8501 in your browser.

---

## Deploying internally (Microsoft 365 / Azure)

### Option A — Azure App Service (recommended for teams)

1. Push this folder to a private Azure DevOps or GitHub repo
2. Create an **Azure App Service** (Linux, Python 3.11)
3. Set the startup command:
   ```
   python -m streamlit run app.py --server.port 8000 --server.address 0.0.0.0
   ```
4. Add **Azure AD authentication** in the App Service "Authentication" blade
   — this restricts access to your organisation's Microsoft accounts only

### Option B — Run on a shared Windows machine

If you have an always-on PC or server on your network:
```bash
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```
Colleagues access it at `http://<machine-ip>:8501`

### Option C — Streamlit Community Cloud (easiest, but public)

Push to a public GitHub repo and connect at https://share.streamlit.io
Not recommended if documents contain sensitive recipient data.

---

## Notes

- Output is always a ZIP file — no files are written to the server's disk
- The split tool upgraded from `PyPDF2` to `pypdf` (the maintained successor)
- The merge tool supports any number of groups, matched by filename stem
