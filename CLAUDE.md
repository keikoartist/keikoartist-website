# keikoartist.com — notes for Claude Code

Commission website of KeikoArts (Keiko, VTuber artist and Live2D studio). Live at https://keikoartist.com.
The owner writes in Indonesian and wants short, direct answers in Indonesian. Do the work, then say in a few lines what changed.

## Rules that always apply

- Refine and polish, never redesign. Light theme only. Keep the pink brand colour (#f2628f). Filled buttons use the darker `--btn-pink` (#c93a6a) so white text stays readable (owner chose this, Nov 2026).
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
| `stats-api.php` | Anonymous visit counter (no cookies, IP never stored): page views, sources (`?ref=` / `utm_source` / referrer), order form opened, orders sent, spins. Daily files in `keikoarts-data/stats/`; yesterday's summary is posted to Discord once a day. The admin Settings panel shows the last 7 days and the Christmas spins (`stats` action in `order-api.php`). |
| `spin-api.php` | Christmas spin wheel draw (see Open items). |
| `admin/index.html` | Admin inbox at /admin/: Chats, Orders (board view like VGen, plus list view), Settings (Discord webhook, Gmail App Password). |
| `tools/build_pages.py` | Generates the service pages (`custom-vtuber-model/`, `live2d-rigging/`, `custom-pngtuber-model/`, `custom-twitch-emotes/`, `vtuber-portfolio/`, `vtuber-pricing/`), the guide pages for search (`vtuber-model-cost/`, `how-to-commission-a-vtuber-model/`, `live2d-vs-pngtuber/`; text built from the prices and terms in `index.html`), `404.html` and `sitemap.xml` from the data in `index.html`. Run `python3 tools/build_pages.py` after changing prices, services or the gallery. |
| `assets/site.css` | Shared styles for the service pages. |
| `images/` | Artwork (WebP). `images/t/` = small versions for grids (520 px wide) and `images/s/` = 360 px versions for phones, both made from the originals. |
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
- `indexnow.yml` — sends every sitemap URL to Bing and other IndexNow search engines (runs when `sitemap.xml` changes; key file `4578f2324956634018c29c1d4d2a4d28.txt` in the root, public by design). Google is not part of IndexNow: the owner submits the sitemap in Search Console.

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
- Commission status badge in the hero: `SLOTS` in `index.html` (open/closed, `start` = "I can start right away", shown next to "Our Services" and in the order form). The badge is a link that opens the order form. The hero badge shows Keiko's emote (images/contact-emote.webp, waves now and then) + "Commissions OPEN" with a live green dot, next to the spin wheel button (no Christmas deadline, owner Nov 2026).
- First-visit loading screen (`#kaLoader` right after `<body>` in `index.html`, chibi `images/loader-chibi.webp`): once per browser session, hides on page load or after 2.5 s, never with `?dryrun=1` or in automated browsers.
- `VTUBERS` (section "Original VTuber Characters"): Keiko's own original characters, not clients. No names; never present them as client VTubers.
- The owner's VGen account (vgen.co/keikoarts) is suspended; reviews there cannot be read publicly. The owner will not appeal: do not suggest it.
- Owner time zone: WIB (GMT+7).
- Goal (Nov 2026): $2000 from the site with new clients only (no past clients reachable). Promote links with `?ref=` (e.g. keikoartist.com/?ref=reddit) so the daily stats show which channel works.
- Christmas edition (`SEASON` in `index.html`, ends 7 Jan 2027): snow, candy-cane line (Santa hat on the logo removed, owner Nov 2026) and a Christmas spin wheel (one spin per visitor, button in the hero; opens by itself once for a new visitor after 20 s and some scrolling, or after 35 s, never with `?dryrun=1` or in automated browsers; `/?spin=1` opens it). Service pages get the candy-cane line and a "Spin the Christmas wheel" link (date taken from `SEASON.until` by `build_pages.py`). Prizes (`GIFTS`, set by the owner): free emotes, free Christmas badges, free source files, free skeb, free sketch, 10% off. The server (`spin-api.php`, same prize order as `GIFTS`) draws the prize and code (XMAS-xxxxx), posts every spin to Discord and logs it in `spins.csv`; winners claim on Discord and Keiko applies it by hand. Nothing changes in PayPal or the order prices.
- Track record (owner, Nov 2026): 200+ commissions completed (shown next to the reviews score, in the "Hi, I'm Keiko" line and in the signature line of the generated pages).
- Reviews: one VGen review (PNGTuber, Mar 2025, "the art keiko made was soo beautiful!...") is waiting for the reviewer's name.
- Hero (Nov 2026): on desktop the artwork fills the hero edge to edge behind the text (soft white fade on the left for readability; hero height follows the 16:9 art, capped at the screen). Witch effects: on the first visit (with the loader, once per session, never in tests) a purple smoke puff clears to reveal the page; purple smoke (`.smk`) and a glowing magic orb (`.orb`) in `.hero-fx`; soft smoke also behind the final CTA. CSS only, off with reduced motion.
- Featured Works (Nov 2026): on screens 760px+ the grid becomes a spellbook (`#bookWrap`, built by JS from the `.works.fw` items, which are moved into the pages so the lightbox and rigging video keep working): cover → one work per page → "Your character next?" page → back cover. Pages turn in 3D (arrows, click a page, keyboard), while the book is on screen it turns its own pages every 3.5 s and starts again from page 1; it pauses on hover and stops for good once the visitor turns a page. Pages can also be dragged like paper (corner lifts on hover, shadow while turning). Beside the closed book (1100px+): chibi Keiko with "Turn the page", magic orb, candle, sparkles, purple smoke; they fade out while the book is open on screens under 1750px. Phones keep the grid. Section titles: small pink snowflake, no underline bar.
- Book shelf (Nov 2026, screens 760px+): three books in the Featured Works section, chosen with tabs: Portfolio (works, turns its own pages until the visitor uses a book), How to Order (6 steps, same facts as TOS/FAQ), TOS & FAQ (built from the #faq answers and #tos terms on the page, so edit those). On these screens #process, #faq and #tos are hidden and links to them (#process, #faq, #tos, #privacy) open the matching book page. Phones keep the normal sections. Six other works sit beside the book (.bk-mini) on 1100px+. The "Custom VTuber models" section was removed; its facts are now FAQ answers.
