# Putting Delhi Air online (free, ~10 minutes)

Streamlit Community Cloud hosts the site for free and gives you a link that works on any phone or computer, 24/7.

## 1. Put the code on GitHub (no command line needed)
1. Sign in or sign up at <https://github.com>.
2. Click **+** (top right) → **New repository**. Name it `delhi-air`, leave it **Public**, and click **Create repository**.
3. On the new repo page, click **uploading an existing file**.
4. Open your `Documents/Delhi-AQI-Dashboard` folder in Finder and drag in **everything except** `.venv` and `my_exposure.json`:
   `app.py`, `aqi.py`, `browser_js.py`, `causes.py`, `data.py`, `details.py`, `expand.py`, `health_log.py`, `i18n.py`,
   `locations.py`, `planner.py`, `sky.py`, `ui.py`, `requirements.txt`, `README.md`, and the **`.streamlit` folder** (only `config.toml`).
   - Press **⌘ ⇧ .** in Finder to show hidden folders like `.streamlit`.
   - **Don't upload `.streamlit/secrets.toml`.** It holds your private token.
5. Click **Commit changes**.

## 2. Deploy on Streamlit Cloud
1. Go to <https://share.streamlit.io> and **Continue with GitHub**.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Pick your `delhi-air` repo, branch `main`, main file `app.py`.
4. Optional: under **Advanced settings** → **Secrets**, paste your WAQI token for live station data:
   ```toml
   WAQI_TOKEN = "your-token-here"
   ```
5. Click **Deploy**. After a minute or two you get a link like `https://delhi-air.streamlit.app`. Share it with anyone.

## Notes
- The site fetches fresh data every time someone opens it, and keeps refreshing while it's open.
- **My exposure** saves its log on the server. Online, everyone using the link shares one log and it can reset when
  the app restarts, so the log is best used on your own computer with `./run.sh`.
- To update the site later, upload the changed files to the repo again. Streamlit Cloud redeploys automatically.
