# Production deployment — VPS provisioning runbook

**One-time provisioning: from nothing to a running server.** Everything recurring afterwards — redeploying, logs, backups and restores, major Postgres upgrades — is [operations.md](../operations.md).

Takes the production host from zero to a phone-accessible HTTPS URL with CI-gated auto-deploys. Architecture and rationale: [infra-0001](../decisions/infra-0001-deployment.md).

The repo side is already in place: `docker-compose.prod.yml` (Caddy + prod images + scheduler, Postgres unpublished), `Caddyfile`, `backend/crontab`, and `.github/workflows/cd.yml`. What remains is host- and account-level, in order:

## 1. Provision the host

- Hetzner **CX23** (~€7/mo) or **CPX22** if the CX line is out of stock — **2 vCPU / 4 GB / ≥40 GB, x86-64, EU**, Ubuntu 26.04 LTS, with your SSH public key set at creation. 4 GB is the floor because the deploy builds the prod images on the host. Spec rationale and fallback providers: [infra-0001](../decisions/infra-0001-deployment.md). (arm64 hosts — Oracle Always-Free, Hetzner CAX, Scaleway ARM — need an arm64 supercronic binary in `backend/Dockerfile` first.)
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
  printf '[DEFAULT]\nbackend = systemd\n' > /etc/fail2ban/jail.local && systemctl restart fail2ban
  ```

  **`backend = systemd` is not optional here.** The default jail reads `/var/log/auth.log`, which this image does not produce, so without it fail2ban runs happily and bans nobody — a protection that reports success while doing nothing. Confirm with `fail2ban-client status sshd` that the jail has seen failures. Port 80 stays open despite everything being HTTPS: Caddy needs it for the ACME challenge and the redirect.

- Install Docker Engine + Compose from the official apt repo (<https://docs.docker.com/engine/install/ubuntu/>), then `usermod -aG docker deploy`. Note `docker` group membership is root-equivalent; it grants `deploy` nothing new because it already has `sudo`, which is exactly why no other user joins it.

- Generate a **dedicated** `ed25519` deploy key for CI — not your personal key — and authorize it for `deploy`. It carries no passphrase, because CI cannot type one, and no `command=`/`from=` restriction in `authorized_keys`: CD runs arbitrary compose commands and GitHub's runner IPs are dynamic. Containment is that it is a separate key, revocable by deleting one line.

## 2. DNS

Point an A record for **`s-charge.app`** at the VPS IP (AAAA too if IPv6 is enabled). Caddy needs the name resolving to the host before it can obtain the Let's Encrypt certificate.

DNS is on Cloudflare. Set the record to **DNS only — grey cloud, not the orange proxied one.** Proxied, Cloudflare terminates TLS at its edge: Caddy never completes the ACME challenge and visitors get Cloudflare's certificate instead of the origin's.

`.app` is HSTS-preloaded, so there is no HTTP fallback at any point — the name works over HTTPS or not at all. Why this domain and registrar, and what was rejected: [infra-0001](../decisions/infra-0001-deployment.md).

## 3. Clone + configure

```bash
sudo mkdir -p /opt/s-charge && sudo chown deploy:deploy /opt/s-charge
git clone git@github.com:Aaleexsnchz/S-Charge.git /opt/s-charge
cd /opt/s-charge
```

**Clone over SSH, not HTTPS.** The repository is private and CD fetches unattended, so there is
nobody to answer a credential prompt — over HTTPS `git fetch` dies with *"could not read Username
for 'https://github.com'"* and the deploy fails at its first step. The host needs its own key
registered as a **deploy key** on the repository (Settings → Deploy keys, read-only is enough);
generate it on the server with `ssh-keygen -t ed25519` and add the public half there. This is a
different key from the CI `DEPLOY_SSH_KEY`, which authenticates GitHub Actions *to the server*,
not the server to GitHub.

The CD workflow assumes `/opt/s-charge`; if you choose another path, update `cd.yml`.

Create the server-side `.env` — one file at the root, never committed. Start from [.env.example](../../.env.example) and set prod values:

- fresh `SECRET_KEY` (`openssl rand -hex 32`) and a strong `POSTGRES_PASSWORD` (mirrored in `DATABASE_URL`) — **rotate, don't reuse, the dev values**
- `ENVIRONMENT=production`, `SESSION_COOKIE_SECURE=true`
- `CORS_ALLOW_ORIGINS=` (empty — same-origin behind Caddy)
- `APP_BASE_URL=https://s-charge.app` and `GOOGLE_REDIRECT_URI=https://s-charge.app/api/auth/google/callback`
- `SITE_ADDRESS=s-charge.app` — Caddy's public address, and the only variable Compose reads by interpolation rather than handing to a container
- `REVE_API_KEY`, `RESEND_API_KEY` / `MAIL_FROM` (see step 6)

**No value may contain `$`.** Compose truncates at the first one and only warns, so the container silently receives half a password while anything reading the file directly sees all of it. `openssl rand -hex 32` is safe; a password manager's "special characters" toggle is not.

`ENVIRONMENT=production` arms a check in [config.py](../../backend/app/config.py): the backend refuses to start if `SECRET_KEY`, `DATABASE_URL` or `APP_BASE_URL` is missing or still holds its development default, if Google is configured without a redirect URI, or if `SESSION_COOKIE_SECURE` is false. A container that restarts in a loop right after this step is that check talking — read `logs backend`.

## 4. Bootstrap the database from a seed dump

The REVE catalogue took ~12 days to seed under the 5 req/hr cap — **never re-seed in prod; restore the latest seed dump** (it excludes `users`/`oauth_account` rows and carries the ETL cursors, so the refresh watermark survives intact and users register fresh).

**The server's `POSTGRES_USER` / `POSTGRES_DB` must match the database the dump was taken from** (`ev_charging_app` / `ev_charging`) — the placeholders in `.env.example` are `app_user` / `app_db`, and restoring into names that disagree with the archive is the fastest way to lose a 12-day seed to a confusing error.

The dump exists in two places — `backups/` on the development laptop and the B2 bucket. Push it from the laptop unless `rclone` is already configured on the host:

```bash
scp backups/<latest seed>.dump deploy@<host>:/opt/s-charge/   # from the laptop
```

Then, on the host, from `/opt/s-charge`:

```bash
docker compose -f docker-compose.prod.yml up -d db
docker compose -f docker-compose.prod.yml exec -T db pg_restore \
  -U ev_charging_app -d ev_charging --clean --if-exists --no-owner < <latest seed>.dump
```

Verify before moving on: the row counts should match the source (`select count(*) from charging_points` ≈ 13.7k).

## 5. First deploy

```bash
export APP_VERSION="$(git describe --tags --always)"
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head
```

`APP_VERSION` is a **build argument**, not runtime configuration: it is baked into both images, so a deploy that forgets to export it reports `dev` and only a rebuild fixes it. CD exports it for you; only a by-hand deploy needs the line above. Before the first tag exists, `git describe --tags --always` yields a short commit sha, and that is what `/api/health` will report.

**`up -d` starts the scheduler along with everything else.** The ETLs run from the first deploy: the PVPC fetch keeps `/api/prices/today` populated, and the REVE refresh keeps tariffs current. The service sat behind a Compose profile until Phase 6, which is why older notes describe an extra `--profile scheduler` step — that profile is gone.

Verify: `https://s-charge.app` loads the app on a phone, the PWA installs, and `https://s-charge.app/api/health` returns ok **with the version you just deployed**.

The laptop crontab still owns the refresh and backup jobs at this point. Handing them over is a separate step — the scheduler profile has to come on first, and the weekly backup needs `rclone` and its B2 config on the VPS.

## 6. External services for the prod origin

- **Google OAuth** (Cloud Console → the existing client): add `https://s-charge.app` as authorised JavaScript origin and `https://s-charge.app/api/auth/google/callback` as redirect URI.
- **Resend**: verify a sending domain (or keep sandbox during private testing) and set `MAIL_FROM` accordingly — without it, verification emails only reach the account owner's inbox.

## 7. CI/CD + branch protection

Repository secrets (Settings → Secrets and variables → Actions): `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_SSH_KEY` (a dedicated key authorized on the VPS, not your personal one), `DEPLOY_KNOWN_HOSTS` (`ssh-keyscan <host>`). CD runs on a **tag push**, and on demand via *Run workflow* — which deploys `main` for a look at unreleased work on a real device ([infra-0003](../decisions/infra-0003-deploy-on-tag.md)). Merging does not deploy.

Protect `main` with a ruleset: **require a pull request**, require the CI checks to pass, and block force-pushes and deletion. `main` is what production runs, so every change goes through a PR ([AGENTS.md](../../AGENTS.md) → Git workflow).

Then **test the loop end to end** — merge a trivial PR, confirm nothing deploys, then push a tag and watch the version at `/api/health` change to it. That round trip is the only proof the pipeline works; do it before trusting it.

## Rolling back

A deploy is a git checkout plus a rebuild, so going back is the same operation aimed at an older commit:

```bash
cd /opt/s-charge
git fetch --tags
git checkout v0.1.0                       # or the previous good commit
export APP_VERSION="$(git describe --tags --always)"
docker compose -f docker-compose.prod.yml up -d --build
```

Leave the branch detached until the fix is merged; the next CD run does `git pull --ff-only`, which fails loudly on a detached HEAD rather than deploying over your rollback silently.

**Code rolls back; the schema does not.** `alembic upgrade` has already run, and older code against a newer schema is only safe when the migration was additive. If it was not, restore the dump CD takes immediately before migrating — `backups/pre-migrate-*.dump` on the server, most recent last, restored with the `pg_restore` line in [operations.md](../operations.md). This is why that dump exists.

### The migration window

`cd.yml` brings the new containers up and *then* migrates, so for the few seconds between them the new code serves against the old schema. Closing it properly means migrating before the new containers take traffic, which needs a release/rollout split this deployment does not have. At single-user demo traffic the exposure is negligible, and the pre-migration dump improves recovery rather than the window itself — but it is a known trade-off, not an oversight.

## 8. Security gate

Before sharing the URL, run through the pre-deploy gate in [infra-0001](../decisions/infra-0001-deployment.md) (`/security-review`): HSTS present, only 22/80/443 open, `docker compose -f docker-compose.prod.yml ps` shows no published `5432`, secrets rotated, cookie `Secure`, CORS empty, backups restorable.
