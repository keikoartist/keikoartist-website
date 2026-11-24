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

The host blocks `mail()`. Emails go through the owner's Gmail (SMTP with an App Password saved in admin → Settings, stored in `settings.json` on the server). FormSubmit is only the backup if Gmail sending fails.

## Secrets (server only, never in git)

- `public_html/keikoartist.com/keikoarts-config.php`: admin password (fallback) and Discord webhook.
- `keikoarts-data/settings.json`: Discord webhook set from admin, Gmail App Password, admin password set via "Forgot password?" (hashed).
- GitHub repository secrets: FTP login for deploys.

## Testing locally

Run the site with `php -S 127.0.0.1:8830` in a copy of the repo that has a test `keikoarts-config.php` (never the real one) and test with Playwright. For email, point the SMTP host at a local mock server.

## Open items

- Gmail App Password set up by the owner on 23 Nov 2026 (diag: mail_set true, smtp.gmail.com reachable). Emails to clients now go through Gmail.
- Cloudflare: the owner's colleague (Bu Mella) may ask to switch the nameservers. Before that, check that deploys use the hosting's FTP address, not the domain name.
- A possible move of the site to the studio standard (Next.js on Bu Mella's server) is not decided. Do not start it unless asked.
- Commission status badge in the hero: `SLOTS` in `index.html` (open/closed, `start` = "I can start right away", shown next to "Our Services" and in the order form). The badge is a link that opens the order form. The hero badge shows Keiko's emote (images/contact-emote.webp, pops out of the pill, waves now and then) + "Commissions • open" with a live green dot, no arrow, next to the spin wheel button (no Christmas deadline, owner Nov 2026).
- First-visit loading screen (`#kaLoader` right after `<body>` in `index.html`, chibi `images/loader-chibi.webp`): once per browser session, hides as soon as the page is ready (at most 1 s; smoke puff 1.1 s, UX review Nov 2026), never with `?dryrun=1` or in automated browsers.
- `VTUBERS` (section "Original VTuber Characters"): Keiko's own original characters, not clients. No names; never present them as client VTubers.
- The owner's VGen account (vgen.co/keikoarts) is suspended; reviews there cannot be read publicly. The owner will not appeal: do not suggest it.
- Owner time zone: WIB (GMT+7).
- Goal (Nov 2026): $2000 from the site with new clients only (no past clients reachable). Promote links with `?ref=` (e.g. keikoartist.com/?ref=reddit) so the daily stats show which channel works.
- Christmas edition (`SEASON` in `index.html`, ends 7 Jan 2027): snow (Santa hat and candy-cane line removed, Nov 2026) and a Christmas spin wheel (one spin per visitor, button in the hero; no automatic pop-up since the UX review (Nov 2026); the hero button and `/?spin=1` open it). Service pages get the thin pink–lavender header line and a "Spin the Christmas wheel" link (line icon) (date taken from `SEASON.until` by `build_pages.py`). Prizes (`GIFTS`, set by the owner): free emotes, free Christmas badges, free source files, free sketch, 10% off (Skeb is a rare prize: gold "Skeb · rare" slice, the server draws it 5 times in 100 via WEIGHTS in spin-api.php, owner 23 Nov 2026; the others share the rest equally). The server (`spin-api.php`, same prize order as `GIFTS`) draws the prize and code (XMAS-xxxxx), posts every spin to Discord and logs it in `spins.csv`; winners claim on Discord and Keiko applies it by hand. Nothing changes in PayPal or the order prices.
- Track record (owner, Nov 2026): 200+ commissions completed (shown next to the reviews score, in the "Hi, I'm Keiko" line and in the signature line of the generated pages).
- Reviews (24 Nov 2026): 26 real VGen reviews (one is 4 stars, so the score line says 4.96) from the owner's screenshots. The Apr 2026 review and the Mar 2025 PNGTuber review show "Anonymous" (owner, 24 Nov 2026). Avatars are letters; real profile pictures only if the owner sends the image files.
- Hero (Nov 2026): on desktop the artwork fills the hero edge to edge (phones and tablets too since 23 Nov: full-bleed art on top, text below over a white fade) behind the text (soft white fade on the left for readability; hero height follows the 16:9 art, capped at the screen). Witch effects: on the first visit (with the loader, once per session, never in tests) a purple smoke puff clears to reveal the page; purple smoke (`.smk`) and a glowing magic orb (`.orb`) in `.hero-fx`; soft smoke also behind the final CTA. CSS only, off with reduced motion.
- Featured Works (Nov 2026): on screens 760px+ the grid becomes a spellbook (`#bookWrap`, built by JS from the `.works.fw` items, which are moved into the pages so the lightbox and rigging video keep working): cover → one work per page → "Your character next?" page → back cover. Pages turn in 3D (arrows, click a page, keyboard), while the book is on screen it turns its own pages every 3.5 s and starts again from page 1; it pauses on hover and stops for good once the visitor turns a page. Pages can also be dragged like paper (corner lifts on hover, shadow while turning). Beside the closed book (1100px+): chibi Keiko with "Turn the page", magic orb, candle, sparkles, purple smoke; they fade out while the book is open on screens under 1750px. Phones keep the grid. Section titles: small pink snowflake, no underline bar.
- Book shelf (Nov 2026, screens 760px+): three books in the #portfolio section (titled "Open a spellbook" by JS on these screens, "Featured Works" on phones), chosen with tabs: Portfolio (works, turns its own pages until the visitor uses a book), How to Order (6 steps, same facts as TOS/FAQ), TOS & FAQ (built from the #faq answers and #tos terms on the page, so edit those). On these screens #process, #faq and #tos are hidden and links to them (#process, #faq, #tos, #privacy) open the matching book page. Phones keep the normal sections. Six other works sit beside the book (.bk-mini) on 1100px+. The "Custom VTuber models" section was removed; its facts are now FAQ answers.
- UX review (Nov 2026): the Featured Works grid shows on every screen again; the three-book shelf is now a pop-up opened by "✦ Open the spellbook" (desktop/tablet), works inside it are copies of the grid items. #process, #faq and #tos are normal sections again on all screens. The side works (.bk-mini) are hidden. Chips (spin, "I can start right away") share one white-pill style. Services: VTuber, VTuber Packages and PNGTuber are `.card.main` (highlighted), the rest come under "More services".
- Design review (Nov 2026): palette = pink (main), plum #6b3a8f / lavender (support, also the Discord buttons), green only for "open"/"start". Header line is a thin pink–lavender gradient (no candy-cane). Card "Order now" buttons are soft (pink only on hover); the filled pink button is the main action per screen. All cards share --card-r / --card-b / --card-sh. No emoji in buttons or chips (line SVG icons). Emotes don't wiggle; smoke, orb and the spellbook still move. Nothing under 13px on phones except the logo tagline.
- Fonts (Nov 2026): DM Serif Display (headings) + Poppins (text, also prices). Numbers never use the serif: every "DM Serif Display" stack starts with "KDigits" (assets/fonts/poppins-digits.woff2, Poppins SemiBold subset of 0-9 $ % + , . – ×, 1.5 KB), in index.html, assets/site.css and admin/index.html. One handwritten accent: Caveat 700 only for "Hi, I'm Keiko ♡" (Google Fonts `text=` subset, loads async).
- Order form (Nov 2026): VTuber opens with Art + Rig · Bust selected (same prices). No emoji in the form (line SVG icons). The "Back" button returns to the service list (step 1), it does not close the form.
- "Planning your debut?" section (#debut, before Team, Nov 2026): debut planner (date → order-by date = debut − 21 days; under 21 days → rush/ask on Discord; under 11 days → message first), character brief button (opens the VTuber form with brief questions in Details if empty), "Ask first, free" Discord card.
- Live chat (Nov 2026): the first message needs an email OR a Discord username, at least one (owner, 24 Nov 2026; fields #kcFEmail + #kcFDc above the message box, checked in JS and again by chat-api.php start); the old optional "Leave your email" form only shows for old chats without contact. On phones the floating chat bubble stays hidden unless there is an unread reply; visitors open the chat from the menu ("Chat with us").
- Prices (owner, 24 Nov 2026): VBridger +$200 (was $50), new add-on "Hand toggle" +$30 each; Full body Art + Rig stays $400. Add-ons with "toggle" in the name get a quantity box (1–20) in the order form; the invoice line reads "Hand toggle × 5".
- Chat auto-reply (24 Nov 2026): after the first message the visitor sees an "Automatic reply" (only on their device, not stored): reply time, and if the message asks about prices, the VTuber prices and add-ons taken from SERVICES.
- Showcase videos (owner, 24 Nov 2026, from Google Drive): images/live2d-model-showcase-{hoodie,red-dress}.mp4 (full, 960px, ~3–4 MB, on /live2d-rigging/ and /vtuber-portfolio/ via SHOWCASES in build_pages.py) and *-loop.mp4 (10 s, ~0.7 MB, in Featured Works). All preload="none"; desktop plays them when on screen, phones show the poster with controls.
- Chat automatic answer (24 Nov 2026): `chat-bot.php` (included by chat-api.php, 404 on its own) builds an answer from `prices.json` (written by build_pages.py from SERVICES, so it always matches the order form): a full estimate for VTuber questions (size, Art only / Art + Rig / Rig only, VBridger, hand toggles, extra expressions, outfits, hairstyles, commercial rights, + 13% tax) or the price list of other services named in the message. Stored as sender `bot` ("Automatic reply"), shown in the visitor chat and the admin inbox (lavender, "Auto:"), and the first one is emailed to the visitor. Later price questions get an automatic answer only until Keiko has replied herself. It never invents prices; Keiko confirms the final price.
- Admin (24 Nov 2026): no "Reply as" field; every admin reply is sent as Keiko.
- VTuber Packages (owner, 24 Nov 2026): same prices and contents, named by model size: "Starter · Bust up" $250, "Debut · Half body" $380, "Full Debut · Full body" $520.
- WIP rigging video (owner, 24 Nov 2026): images/live2d-rigging-wip-process.mp4 (Live2D Cubism physics, nine-tailed fox) on /live2d-rigging/ and in the VideoObject list (VIDEOS in build_pages.py).
- AI assistants (24 Nov 2026): build_pages.py writes `llms.txt` (summary, prices and page links from SERVICES) so ChatGPT / Claude / Perplexity can read the studio's facts; robots.txt allows all crawlers.
- Guide page /how-to-become-a-vtuber/ (24 Nov 2026, guide_start in build_pages.py). Homepage JSON-LD ProfessionalService has knowsAbout, founder (Keiko) and slogan. Search Console: the owner already has keikoartist.com verified (seen 24 Nov 2026).
- Chat reminders (24 Nov 2026): while a chat is unread, Discord AND Keiko's own Gmail (gmail_user from admin Settings) get "⏰ Still unread" every 30 minutes (first after 30 min, max 12 = 6 h; resets when Keiko opens, replies or closes the chat). `send_reminders()` in chat-api.php runs from `chat-api.php?remind=1` (GitHub Actions `chat-reminders.yml`, every 15 min) and now and then on chat traffic. Replies from the admin inbox are emailed to the visitor (email is required in the chat).
- Cart (owner, 24 Nov 2026, like Etsy): in the order form, "Add to cart" (next to Send Order, not for Custom Inquiry) saves the service with its options, add-ons and details text on the visitor's device (`ka_cart` in localStorage, up to 6 services, 30 days). A cart icon is always in the header (count badge when it has items; empty cart says so). The cart view (step 3) lists the items, subtotal, 13% tax and total; Checkout opens the normal form with all items as ONE order: Service = "VTuber + Emotes", every item is an invoice line, one PayPal link (server recomputes the tax; up to 60 lines). "Send Order" on a service still orders only that service. In the cart each item has Edit (pencil: reopens the service with its choices and details; the button reads "Update cart" and Send Order is hidden while editing) and Remove (✕), plus "Clear cart" (tap twice). The old "You have an unfinished order" pop-up was removed (owner found it annoying); the draft still comes back when the service is opened again.
- Etsy/VGen-style trust (24 Nov 2026): order tracking page `order-api.php?a=track&id=…&k=<view_key>` (timeline: received → payment → Sketch/Lineart/Coloring/Rigging/Final files (`STAGES`) → Delivered, plus Keiko's note); link in the client email, on the thank-you screen ("Track your order") and in admin (order detail → "Progress (client sees this)": stage, short note, "Email the client", "Mark order Done"; `stage` action, columns stage/stage_note/stage_at). Checkout: "ready by <date>" (today + 21 days, rush + 11), optional "Coupon or prize code" field (recorded with the order only, Keiko applies it by hand; no automatic price change), a checklist under the price (revisions from the TOS: unlimited at sketch + 2 minor after coloring; PayPal checkout; full refund before work starts; tracking link), and an approximate price in the visitor's currency (fx-api.php: the server fetches ECB rates from frankfurter, open.er-api.com as backup, cached 12 h in keikoarts-data/fx.json; "approx., you pay in USD"). Cart: "Save for later" / "Move to cart" (`ka_saved`). Reviews: 8 shown on 768px+, "Show all N reviews" button; phones keep the carousel with a "2 / 26" counter. No "PayPal Buyer Protection" claim: it does not cover art commissions (intangible).
- Chat automatic answer also covers "are you open?" (from `SLOTS`, written to prices.json as `_status`), turnaround (3 weeks at most), how to order/pay and revisions; the first answer and the chat header say "faster on Discord".
- Slots per service (owner, 24 Nov 2026: "VTuber 5 slots, the others varied"): `SLOTS.per` in index.html (VTuber 5, VTuber Packages 3, PNGTuber 4, Chibi VTuber 4, VTuber Pet 4, Emotes 10, Custom PFP 6, Banner 6, VTuber Logo 6, Stream Overlay 4, Background 4; the non-VTuber numbers were chosen by Claude for the owner to adjust). Shown as a green "5 slots left" line on the service cards, in the service list and in the order form header; 0 shows "Fully booked". Manual: edit the numbers and run build_pages.py (prices.json `_status.slots` feeds the chat answer "VTuber model slots left: 5").
