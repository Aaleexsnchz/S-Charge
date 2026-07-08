# Production deployment — VPS provisioning runbook

One-time setup of the production host, from zero to a phone-accessible HTTPS URL with CI-gated auto-deploys. Architecture and rationale: [infra-0001](../decisions/infra-0001-deployment.md). Day-2 operations (logs, rebuilds, backups): [DOCKER.md](../DOCKER.md).

The repo side is already in place: `docker-compose.prod.yml` (Caddy + prod images + scheduler, Postgres unpublished), `Caddyfile`, `backend/crontab`, and `.github/workflows/cd.yml`. What remains is host- and account-level, in order:

## 1. Provision the host

- Hetzner **CX22** (2 vCPU / 4 GB, EU), Ubuntu 24.04 LTS, with your SSH public key set at creation. (Fallback: Oracle Always-Free ARM — needs an arm64 supercronic binary in `backend/Dockerfile` first.)
- Create a non-root user and disable root/password SSH:

  ```bash
  adduser deploy && usermod -aG sudo deploy
  rsync --archive --chown=deploy:deploy ~/.ssh /home/deploy
  # in /etc/ssh/sshd_config: PermitRootLogin no, PasswordAuthentication no
  systemctl restart ssh
  ```

- Firewall + brute-force protection:

  ```bash
  ufw allow OpenSSH && ufw allow 80/tcp && ufw allow 443/tcp && ufw allow 443/udp && ufw enable
  apt install -y fail2ban unattended-upgrades
  ```

- Install Docker Engine + Compose from the official apt repo (<https://docs.docker.com/engine/install/ubuntu/>), then `usermod -aG docker deploy`.

## 2. DNS

Point an A record (domain, or a free DuckDNS subdomain) at the VPS IP. Caddy needs the name resolving to the host before it can obtain the Let's Encrypt certificate.

## 3. Clone + configure

```bash
sudo mkdir -p /opt/tfm && sudo chown deploy:deploy /opt/tfm
git clone https://github.com/Aaleexsnchz/EV-Charging-Management-App.git /opt/tfm
cd /opt/tfm
```

The CD workflow assumes `/opt/tfm`; if you choose another path, update `cd.yml`.

Create the two server-side env files (never committed):

- **`.env`** (root): `SITE_ADDRESS=<your domain>` — see [.env.example](../../.env.example).
- **`backend/.env`**: start from [backend/.env.example](../../backend/.env.example) and set prod values:
  - fresh `SECRET_KEY` (`openssl rand -hex 32`) and a strong `POSTGRES_PASSWORD` (mirrored in `DATABASE_URL`) — **rotate, don't reuse, the dev values**
  - `ENVIRONMENT=production`, `APP_DEBUG=false`, `SESSION_COOKIE_SECURE=true`
  - `CORS_ALLOW_ORIGINS=` (empty — same-origin behind Caddy)
  - `APP_BASE_URL=https://<domain>` and `GOOGLE_REDIRECT_URI=https://<domain>/api/auth/google/callback`
  - `REVE_API_KEY`, `RESEND_API_KEY` / `MAIL_FROM` (see step 6)

## 4. Bootstrap the database from a seed dump

The REVE catalogue took ~12 days to seed under the 5 req/hr cap — **never re-seed in prod; restore the latest seed dump** (it excludes `users`/`oauth_account` rows and carries the ETL cursors, so the refresh watermark survives intact and users register fresh).

```bash
docker compose -f docker-compose.prod.yml up -d db
rclone copy b2:tfm-db-backups/<latest seed>.dump .   # or scp it from the laptop
docker compose -f docker-compose.prod.yml exec -T db pg_restore \
  -U app_user -d app_db --clean --if-exists --no-owner < <latest seed>.dump
```

## 5. First deploy

```bash
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

Verify: `https://<domain>` loads the app on a phone, PWA installs, `https://<domain>/api/health` returns ok, `docker compose -f docker-compose.prod.yml logs scheduler` shows supercronic loading the two jobs. Then **remove the refresh/PVPC entries from the laptop crontab** (the scheduler container owns them now) and move the weekly `backup_db_cron.sh` line to the server crontab (requires `rclone` + the B2 config on the VPS; adjust its hardcoded paths).

## 6. External services for the prod origin

- **Google OAuth** (Cloud Console → the existing client): add `https://<domain>` as authorised JavaScript origin and `https://<domain>/api/auth/google/callback` as redirect URI.
- **Resend**: verify a sending domain (or keep sandbox during private testing) and set `MAIL_FROM` accordingly — without it, verification emails only reach the account owner's inbox.

## 7. CI/CD + branch protection

Repository secrets (Settings → Secrets and variables → Actions): `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` (a dedicated key authorized on the VPS, not your personal one), `DEPLOY_KNOWN_HOSTS` (`ssh-keyscan <host>`). CD runs on every **green** CI run on `main` (and manually via *Run workflow*).

Protect `main`: require a PR and the CI checks before merge.

## 8. Security gate

Before sharing the URL, run through the pre-deploy gate in [infra-0001](../decisions/infra-0001-deployment.md) (`/security-review`): HSTS present, only 22/80/443 open, `docker compose -f docker-compose.prod.yml ps` shows no published `5432`, secrets rotated, cookie `Secure`, CORS empty, backups restorable.
