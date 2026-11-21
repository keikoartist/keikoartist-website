# keikoartist.com — notes for Claude Code

Commission website of KeikoArts (Keiko, VTuber artist and Live2D studio). Live at https://keikoartist.com.
The owner writes in Indonesian and wants short, direct answers in Indonesian. Do the work, then say in a few lines what changed.

## Rules that always apply

- Refine and polish, never redesign. Light theme only. Keep the pink brand colour (#f2628f).
- Never invent reviews, prices, testimonials or client names. Reviews come only from real VGen screenshots or text the owner sends.
- This repo is **public**: never commit passwords, webhook URLs, App Passwords or other secrets. Secrets live only on the server (see "Secrets").
- Never ask the owner to paste a password, webhook URL or App Password into the chat. They type those into the admin Settings themselves.
- Do not show a WhatsApp number anywhere. Public contact = the Discord server (https://discord.gg/FbgWxMPjf). The email address is only for clients who ordered.
- Only touch `public_html/keikoartist.com` on the hosting. Other sites on the same account are not ours.
- Do not change payment behaviour (PayPal, tax, prices) without the owner confirming it first.

## Stack

- Static `index.html` (inline CSS and JS) plus PHP 7.4 endpoints on Rumahweb shared hosting (LiteSpeed). PHP `mail()` is disabled by the host.
- Data: SQLite files in `keikoarts-data/` **outside** the public folder (`orders.sqlite`, `chat.sqlite`, `settings.json`).
- No build step for the homepage. Service pages are generated (see below).

## Files

| Path | What it is |
| --- | --- |
| `index.html` | Homepage: hero, featured works, services and order form, reviews, process, FAQ, TOS, chat widget. Prices and options are in the `SERVICES`, `DETAILS` and `GALLERY` objects inside it. |
| `order-api.php` | Orders: submit, PDF invoice link (`?a=pdf`), PayPal pay link (`?a=pay`), PayPal IPN (marks orders Paid), admin actions, Discord webhook, Gmail sending. |
| `order-pdf.php` + `lib/fpdf/` | Invoice and brief PDF (FPDF, Helvetica). |
| `chat-api.php` | Website live chat: visitors, admin replies, contact details, reply emails, admin login and "Forgot password?". |
| `notify-discord.php` | Helper for Discord notifications. |
| `admin/index.html` | Admin inbox at /admin/: Chats, Orders (board view like VGen, plus list view), Settings (Discord webhook, Gmail App Password). |
| `tools/build_pages.py` | Generates the service pages (`custom-vtuber-model/`, `live2d-rigging/`, `custom-pngtuber-model/`, `custom-twitch-emotes/`, `vtuber-portfolio/`, `vtuber-pricing/`), `404.html` and `sitemap.xml` from the data in `index.html`. Run `python3 tools/build_pages.py` after changing prices, services or the gallery. |
| `assets/site.css` | Shared styles for the service pages. |
| `images/` | Artwork (WebP). `images/t/` = small versions for grids (520 px wide), made from the originals. |
| `tools/ftp_deploy.py` | Deploy script (uploads changed files only). |
| `tools/seo_audit.py`, `tools/htaccess_*` | SEO check and the managed `.htaccess` block. |

## Deploy

- Every push to `main` deploys automatically: GitHub Actions `deploy-ftp.yml` runs `tools/ftp_deploy.py`, which uploads only changed tracked files (state in `.deploy-state.json` on the server) and retries up to 3 times.
- Not uploaded: `.github/`, `docs/`, `tools/`, `README.md`, `CLAUDE.md`.
- Files that exist only on the server are never touched: `keikoarts-config.php` (admin password, Discord webhook), `.htaccess`, `chat-data/`, old WordPress files.

## Checks (GitHub Actions, run with `gh workflow run <file>`)

- `live-browser-test.yml` — order flow on the live site in 5 browsers (test mode, saves nothing). Also runs daily and opens an issue labelled `site-check` if it fails.
- `verify-live.yml` — live page and API checks.
- `seo-audit.yml` — titles, descriptions, links, sitemap.
- `diag-admin.yml` — server ping (Discord set, Gmail set, database OK). Never prints secrets.
- `lighthouse.yml`, `lighthouse-ab.yml` — speed tests.

## Order and payment flow

1. Client sends the order form (email required). The server saves the order, makes a PDF and posts it to Discord.
2. Right after sending, the client sees a **Pay with PayPal** button with the amount filled in (all services, Custom Inquiry too). The same link is in the PDF and the confirmation email.
3. PayPal IPN marks the order **Paid** only when the full amount arrives in USD; Discord gets "Payment received" (or "Payment too low").
4. 13% tax is added on every invoice. Commercial / merch rights are +$30 for every service (Custom Inquiry: when Usage = Commercial). Every commission takes 3 weeks at most.
5. Admin can resend the invoice with "Send invoice to client".

PayPal receiver email: `PAYPAL_EMAIL` in `order-api.php` (confirmed correct by the owner).

## Email

The host blocks `mail()`. Emails go through the owner's Gmail (SMTP with an App Password saved in admin → Settings, stored in `settings.json` on the server). Until that is set up, a FormSubmit backup is used, which often lands in spam.

## Secrets (server only, never in git)

- `public_html/keikoartist.com/keikoarts-config.php`: admin password (fallback) and Discord webhook.
- `keikoarts-data/settings.json`: Discord webhook set from admin, Gmail App Password, admin password set via "Forgot password?" (hashed).
- GitHub repository secrets: FTP login for deploys.

## Testing locally

Run the site with `php -S 127.0.0.1:8830` in a copy of the repo that has a test `keikoarts-config.php` (never the real one) and test with Playwright. For email, point the SMTP host at a local mock server.

## Open items

- Gmail App Password not set up yet (admin → Settings → Emails to clients).
- Cloudflare: the owner's colleague (Bu Mella) may ask to switch the nameservers. Before that, check that deploys use the hosting's FTP address, not the domain name.
- A possible move of the site to the studio standard (Next.js on Bu Mella's server) is not decided. Do not start it unless asked.
- Commission status badge in the hero: `SLOTS` in `index.html` (open/closed).
- `VTUBERS` (section "Original VTuber Characters"): Keiko's own original characters, not clients. No names; never present them as client VTubers.
- The owner's VGen account (vgen.co/keikoarts) is suspended; reviews there cannot be read publicly. The owner will not appeal: do not suggest it.
- Owner time zone: WIB (GMT+7).
- Reviews: one VGen review (PNGTuber, Mar 2025, "the art keiko made was soo beautiful!...") is waiting for the reviewer's name.
