# Email provider setup

The backend sends verification and password-reset emails through [Resend](https://resend.com). Without an API key, registration still succeeds but the helper logs `email_send_failed` instead of delivering — fine for UI sanity-checking, not enough to exercise the verify or reset success paths. Decision rationale: [auth-0003](../decisions/auth-0003-preregistration-shell-mitigation.md).

1. Create an account at <https://resend.com> and copy a key from **API Keys**. Free tier is 100 emails/day, sufficient for the thesis demo.
2. Add the credentials to `backend/.env`:

   ```env
   RESEND_API_KEY=<paste>
   MAIL_FROM=onboarding@resend.dev
   APP_BASE_URL=http://localhost:5173
   ```

3. Restart the backend so it reads the new env vars — stop `just api` and start it again. On the production stack use `up -d --force-recreate backend`, not `restart` (see the [Google OAuth guide](google-oauth.md) for why).

**Sandbox sender.** `onboarding@resend.dev` works without DNS setup but, in test mode, Resend only delivers to the email address that owns the Resend account. Register through the UI with that same email to receive the verification link.

**Production setup.** Once the production domain exists, verify it in Resend's **Domains** dashboard, add the SPF/DKIM/DMARC records they provide to your DNS, and switch `MAIL_FROM` to a sender on that domain. Inbox placement (especially Gmail) depends on those records — without DKIM, transactional mail tends to land in spam.
