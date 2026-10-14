# Putting AQIfyMe online (free, ~10 minutes)

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

## Morning AQI digest on Telegram (free)
Every day at 7:00 AM IST, GitHub posts today's AQI image and summary to your Telegram channel. Anyone can join the
channel to get it.

1. **Create the bot:** in Telegram, open **@BotFather**, send `/newbot`, and pick a name (e.g. *AQIfyMe Bot*) and a
   username ending in `bot`. BotFather replies with a **token**. Keep it secret.
2. **Create the channel:** in Telegram, tap **New Channel**, call it *AQIfyMe*, make it **Public**, and give it a link such
   as `t.me/aqifyme_delhi`. Open the channel → **Administrators → Add Admin** → add your bot (it needs *Post messages*).
3. **Add the secrets on GitHub:** open your repo → **Settings → Secrets and variables → Actions → New repository secret**,
   and add:
   - `TELEGRAM_BOT_TOKEN`: the token from BotFather
   - `TELEGRAM_CHAT_ID`: your channel's @username, e.g. `@aqifyme_delhi`
   - `WAQI_TOKEN` (optional): your aqicn.org token, for station-corrected numbers
4. **Test it:** repo → **Actions** → **Morning AQI digest** → **Run workflow**. The post appears in your channel in about a minute.
5. **Optional:** to change which localities are listed, go to **Settings → Secrets and variables → Actions → Variables**
   and add `DIGEST_LOCATIONS`, e.g. `ITO,Anand Vihar,Noida Sector 62,Gurugram Vikas Sadan`.

Share the channel link (`t.me/your_channel`) on the website or with friends. GitHub pauses scheduled jobs if the repo has
no activity for 60 days; pushing any change, or clicking *Run workflow*, wakes it up again.
