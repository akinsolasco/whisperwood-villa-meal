# Enhanced Living Whisperwood Smart Label Support Site

This package contains the static support/manual website for Enhanced Living
Whisperwood Smart Label.

The site is plain HTML, CSS, JavaScript, and image assets. It does not need
Node.js, Python, a database, or a build step to run.

## Package Contents

- `index.html` - main support site page.
- `styles.css` - visual styling.
- `app.js` - search/help interactions.
- `assets/` - logo and favicon.
- `deployment/` - optional server examples for IT.

## Recommended Live Setup

Recommended web root:

```text
/var/www/whisperwood-support-site
```

Recommended domain pattern:

```text
support.your-domain.com
```

Replace `support.your-domain.com` in the example config files with the final
facility domain or subdomain.

## GitHub Connected Update Flow

The cleanest flow is:

1. IT installs Git on the server.
2. IT clones the repository on the server.
3. The web server points to `docs/support_portal` inside the cloned repository.
4. When you edit the manual and push to GitHub, IT can run the update script, or
   install the included timer to pull changes automatically.

Repository:

```text
https://github.com/akinsolasco/whisperwood-villa-meal.git
```

If the repository is private, IT must use one of these:

- a GitHub deploy key with read access, or
- a GitHub personal access token with read access, or
- a GitHub account already authorized to the repository.

## One-Time Linux Server Setup

Example path:

```bash
sudo mkdir -p /opt/whisperwood-support-site
sudo chown -R "$USER":"$USER" /opt/whisperwood-support-site
git clone https://github.com/akinsolasco/whisperwood-villa-meal.git /opt/whisperwood-support-site/repo
sudo cp /opt/whisperwood-support-site/repo/docs/support_portal/deployment/update_support_site.sh /opt/whisperwood-support-site/update_support_site.sh
sudo chmod +x /opt/whisperwood-support-site/update_support_site.sh
sudo ln -sfn /opt/whisperwood-support-site/repo/docs/support_portal /var/www/whisperwood-support-site
```

Then configure one web server:

- Nginx: use `deployment/nginx-whisperwood-support-site.conf`
- Caddy: use `deployment/Caddyfile`
- Apache: use `deployment/apache-whisperwood-support-site.conf`

## Updating After Future Changes

Manual update:

```bash
sudo /opt/whisperwood-support-site/update_support_site.sh
```

Automatic update:

Install the included systemd service and timer:

```bash
sudo cp deployment/whisperwood-support-site-update.service /etc/systemd/system/
sudo cp deployment/whisperwood-support-site-update.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now whisperwood-support-site-update.timer
```

The timer checks GitHub every five minutes.

## SSL / HTTPS

Use HTTPS for the live manual.

Recommended options:

- Caddy: automatic HTTPS after DNS points to the server.
- Nginx or Apache: use Certbot/Let's Encrypt after DNS points to the server.
- Internal-only network: IT may use a trusted internal certificate.

DNS must point the chosen domain or subdomain to the server before public SSL
can be issued.

## Quick Test

After hosting, open:

```text
https://support.your-domain.com/
```

The page should load the Enhanced Living Whisperwood logo, search box, role
guides, recovery guide, download section, and hardware troubleshooting section.

## Notes for IT

- This is a static site. Do not expose database credentials here.
- Keep this site separate from the Raspberry Pi Control Service.
- If the repository is private, do not put GitHub tokens into public files.
- If using Nginx or Apache, reload the service after config changes.
- If using the automatic updater, check logs with:

```bash
journalctl -u whisperwood-support-site-update.service -n 100 --no-pager
```
