# MAX Mini App setup

Build the client with `cd frontend; npm install; npm run build`, then run `uvicorn api:app --host 0.0.0.0 --port 8000`.

For browser development use `ENV=development`; the client sends only the development header and the server accepts it only in that mode. In MAX set `ENV=production`, a strong `APP_SESSION_SECRET`, HTTPS `MINI_APP_URL`, and register that HTTPS URL in the bot's advanced Mini App settings. MAX Bridge is loaded from `https://st.max.ru/js/max-web-app.js`; production requests exchange `window.WebApp.initData` for a signed one-hour application session.

The host must be HTTPS. Set the bot button label to «Играть» in MAX Partner settings. `startapp` payloads are retained by MAX in `initData`; challenge links must use only the documented ASCII payload alphabet and 512-character limit.
