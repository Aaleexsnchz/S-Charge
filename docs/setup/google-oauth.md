# Google OAuth setup

The backend supports Google sign-in side by side with email/password; both flows land on the same HttpOnly session cookie. To enable it locally, create an OAuth 2.0 Client in Google Cloud Console and paste the credentials into the root `.env`.

1. Open [APIs & Services → OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent). Set **User type: External** (Internal restricts sign-in to a Google Workspace org and rejects personal Gmail with `403 org_internal`). Fill in App name, support email, and developer contact. While the app is in **Testing**, add every Google account you'll use as a **Test user**, otherwise consent is denied.
2. Enable the **People API** for the same project: <https://console.cloud.google.com/apis/library/people.googleapis.com>. The Python `httpx-oauth` Google client fetches the user profile from `people.googleapis.com`, not the legacy `/oauth2/v3/userinfo` endpoint, so without this the OAuth callback fails with `GetProfileError → GetIdEmailError` after Google has already issued the access token.
3. Go to **APIs & Services → Credentials** and click **Create credentials → OAuth client ID**. Application type: **Web application**.
4. Fill in:
   - **Authorised JavaScript origins:** `http://localhost:5173`
   - **Authorised redirect URIs:** `http://localhost:5173/api/auth/google/callback`
5. Copy the generated **Client ID** and **Client Secret** into the root `.env`:

   ```env
   GOOGLE_CLIENT_ID=<paste>
   GOOGLE_CLIENT_SECRET=<paste>
   GOOGLE_REDIRECT_URI=http://localhost:5173/api/auth/google/callback
   ```

6. Restart the backend so it reads the new env vars — stop `just api` and start it again. On the **production** stack the backend is a container, and there it must be `docker compose -f docker-compose.prod.yml up -d --force-recreate backend`: Compose snapshots env vars at container creation, so a plain restart keeps the old empty values and Google rejects the authorize request with `Missing required parameter: client_id`.

"Iniciar sesión con Google" on `/login` will now bounce through Google and return you to the app authenticated. The redirect URI points at the Vite dev server (`:5173`), not the backend directly (`:8000`); Vite proxies `/api/*` to the backend so the session cookie lands on the same origin as the SPA. The production deploy ([Phase 5](../plan/phases/phase-5.md)) swaps these localhost URLs for the production domain.

**Browser note for testing.** Run the OAuth flow from a regular browser tab. Google's "secure browsers" policy returns `403 disallowed_useragent` when the user-agent looks like an embedded webview — including Edge/Chrome DevTools' device-emulation toolbar (e.g. iPhone 12 Pro), in-IDE preview panels, and mobile in-app browsers. Toggle device emulation off for the consent step, then re-enable it for layout testing once you're authenticated.
