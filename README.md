# vakantie-lijst-app

Gedeelde vakantie-paklijst: items toevoegen/verwijderen, aanvinken als ingepakt, groepen aanmaken
en anderen uitnodigen via een link (Google-login of gewoon een e-mailadres).

## 1. Supabase (database)

1. Maak een gratis project op https://supabase.com.
2. Ga naar de SQL Editor en voer het volledige `schema.sql` uit dat in deze map staat.
3. Ga naar "Connect" (bovenaan het dashboard) -> kies **Session pooler** (niet de directe
   connectie -- die is IPv6-only en werkt niet vanaf Streamlit Community Cloud).
4. Vul de host/port/database/username/password in `.streamlit/secrets.toml` in onder
   `[connections.postgresql]`.

## 2. Lokaal draaien

```bash
python -m venv .venv
.venv\Scripts\activate       # op Windows
pip install -r requirements.txt
streamlit run app.py
```

Zonder `[auth]` in `secrets.toml` werkt de app al volledig via de eenvoudige naam/e-mail-login.

## 3. Google-login toevoegen (optioneel, later)

1. Nieuw project op https://console.cloud.google.com.
2. **APIs & Services -> OAuth consent screen**: type "External", app-naam + support-e-mail
   invullen. Scopes: enkel `openid`, `email`, `profile` laten staan.
3. Zet de consent screen op **"In production"** (niet "Testing") -- anders kunnen enkel
   handmatig toegevoegde test-e-mailadressen inloggen, en moet iedereen die je via een
   uitnodigingslink toevoegt vooraf gekend zijn. Met enkel deze niet-gevoelige scopes vereist
   dit geen Google-verificatieproces.
4. **Credentials -> Create Credentials -> OAuth client ID -> Web application**. Redirect URIs:
   `http://localhost:8501/oauth2callback` (lokaal), en na de eerste deploy ook
   `https://<jouw-app-naam>.streamlit.app/oauth2callback`.
5. Zet het `[auth]`-blok in `.streamlit/secrets.toml` (staat al als voorbeeld in commentaar
   klaar) en vul `client_id`/`client_secret` in. Genereer een `cookie_secret` met:
   `python -c "import secrets; print(secrets.token_hex(32))"`.

## 4. Deployen op Streamlit Community Cloud

1. Zorg dat `.streamlit/secrets.toml` NIET meegecommit wordt (staat in `.gitignore`).
2. Push naar GitHub, maak de app aan op https://share.streamlit.io.
3. Plak de volledige inhoud van je lokale `secrets.toml` in App settings -> Secrets, met
   `redirect_uri` en `app_base_url` aangepast naar de live `https://...streamlit.app` URL.
4. Voeg diezelfde live redirect-URI ook toe in Google Cloud Console (stap 3.4 hierboven).
