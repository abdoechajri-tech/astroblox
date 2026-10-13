# AstroBlox

Blox Fruits trading site: username + password accounts, trade posts (fruits, perm fruits, gamepasses),
trade offers, global chat, per-trade chat and private messages. Python (Flask) + SQLite.

## 1. Run it on your Windows PC (PowerShell)

```powershell
cd astroblox
python -m venv venv
venv\Scripts\Activate.ps1        # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000, create an account and test it. Stop with Ctrl+C.

## 2. Put it online for free with Cloudflare Tunnel

Cloudflare Pages and Workers cannot run Flask, but Cloudflare Tunnel (free) gives your PC a public
https link without opening any router ports. The site only works while your PC and the tunnel are running.

### Quick link (no Cloudflare account needed)

1. Install cloudflared (PowerShell): `winget install --id Cloudflare.cloudflared`
   Close and reopen PowerShell afterwards.
2. Terminal 1, start the site with Cloudflare mode on:
   ```powershell
   cd astroblox
   venv\Scripts\Activate.ps1
   $env:ASTROBLOX_HTTPS="1"
   $env:ASTROBLOX_BEHIND_CLOUDFLARE="1"
   python app.py
   ```
3. Terminal 2, start the tunnel:
   ```powershell
   cloudflared tunnel --url http://localhost:5000
   ```
4. Copy the `https://something.trycloudflare.com` address it prints and share it. Anyone can open it.
   The address changes every time you restart the tunnel.

### Permanent address (needs a free Cloudflare account and your own domain)

1. Add your domain to Cloudflare (a domain costs money, Cloudflare's plan for it is free).
2. `cloudflared tunnel login`
3. `cloudflared tunnel create astroblox`
4. `cloudflared tunnel route dns astroblox play.yourdomain.com`
5. `cloudflared tunnel run --url http://localhost:5000 astroblox`
6. Keep both windows open. To keep it running without windows, look up "cloudflared Windows service".

## 3. Other free hosts that can run Flask (no PC left on)

PythonAnywhere has a free plan that can run a small Flask app with a disk for the SQLite file. Upload
this folder, create a Flask web app pointing at `app.py` (variable `app`), and set
`ASTROBLOX_HTTPS=1`. Check their current free-plan limits first.

## Good to know

- **Forgot password:** there is no email reset. Run `python reset_password.py USERNAME NEWPASSWORD`.
- **Backups:** copy `astroblox.db` (the whole database) regularly. Never share `secret.key`.
- **No staff tools yet.** To remove a user or a bad trade, edit `astroblox.db` with "DB Browser for SQLite".
- Passwords are stored hashed. Messages are only visible to the people in them, but you (the host)
  can read the database, so tell users not to send passwords.
- Trading Blox Fruits for money or Robux breaks Roblox's rules. This site is item-for-item only.
