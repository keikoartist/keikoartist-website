"""Builds the SEO service pages of keikoartist.com from the data in index.html.

Run from the repo root:  python3 tools/build_pages.py
Prices, packages, add-ons, timelines and deliverables are read from the SERVICES / DETAILS / GALLERY
objects in index.html, so the pages always match the order form. Re-run after changing prices.
Writes: custom-vtuber-model/, live2d-rigging/, custom-pngtuber-model/, vtuber-portfolio/, vtuber-pricing/,
404.html and sitemap.xml.
"""
import json, os, re, subprocess, html, datetime, hashlib
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://keikoartist.com/'
SRC = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()

def js_object(name):
    start = SRC.index(f'const {name} =')
    end = SRC.index('\n};', start) + 3
    out = subprocess.run(['node', '-e', SRC[start:end] + f'\nprocess.stdout.write(JSON.stringify({name}))'], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)

SERVICES, DETAILS, GALLERY = js_object('SERVICES'), js_object('DETAILS'), js_object('GALLERY')
CSS_V = hashlib.md5(open(os.path.join(ROOT, 'assets/site.css'), 'rb').read()).hexdigest()[:8]
TODAY = datetime.date.today().isoformat()
e = lambda s: html.escape(str(s), quote=True)

def money(n):
    n = float(n)
    return f'${n:,.0f}' if n == int(n) else f'${n:,.2f}'

# descriptive alt text for every portfolio image (what is actually in the picture)
ALT = {
    'custom-vtuber-model-kitsune-gown': 'Full-body VTuber model art of a fox-eared girl in a pink and black layered gown with gold armor details',
    'custom-vtuber-model-witch': 'Full-body VTuber model art of a pink-haired witch in a purple outfit holding a pink flame',
    'custom-vtuber-model-maid': 'Full-body VTuber model art of a pink-haired maid with cat ears holding playing cards',
    'custom-vtuber-model-rocker': 'Full-body VTuber model art of a silver-haired rocker girl in a black jacket with a guitar case',
    'custom-vtuber-model-dragon': 'Full-body VTuber model art of a dragon girl with horns in a pink and black frilled dress',
    'vtuber-debut-package-keikomi': 'VTuber debut package sheet with full-body model, rigging, logo, eye banner, expressions and PSD files',
    'vtuber-stream-overlay-keikomi': 'Stream overlay set with Starting Soon, Be Right Back and Ending Soon screens in purple and pink',
    'vtuber-stream-background-room': 'Night-time streamer bedroom background with gaming chair, desk and window',
    'chibi-vtuber-model-witch': 'Full-body chibi VTuber art of a pink-haired witch in a black and pink outfit',
    'custom-twitch-emotes-witch': 'Two Twitch emotes of a pink-haired witch: blushing and surprised',
    'animated-twitch-emotes-witch': 'Set of 8 animated Twitch emotes of a pink-haired witch: surprised, tongue out, smug, nervous, crying, giggling with phone, blowing a kiss and holding money',
    'custom-twitch-emote-witch': 'Twitch emote of a pink-haired witch sticking out her tongue',
    'vtuber-twitch-banner-eyes-blue': 'Eye banner of glowing blue eyes framed by purple hair',
    'animated-vtuber-banner-eyes-silver': 'Animated eye banner of silver-haired character with glasses',
    'vtuber-twitch-banner-mouth': 'Mouth banner of a smiling character with fangs and purple nails',
    'vtuber-twitch-banner-eyes-fire': 'Eye banner of orange eyes surrounded by flames',
    'vtuber-twitch-banner-eyes-sakura': 'Eye banner of pink eyes with round glasses and cherry blossoms',
    'vtuber-pet-mascot-anglercat': 'VTuber pet: fluffy blue cat sitting on a glowing anglerfish',
    'vtuber-pet-mascot-cat': 'VTuber pet: green leaf cat with flower collar',
    'vtuber-pet-mascot-tiger': 'VTuber pet: orange tiger cub with a red crest',
    'vtuber-pet-mascot-snow-leopard': 'VTuber pet: lavender snow leopard with purple flame tail',
    'vtuber-pet-mascot-peach': 'VTuber pet: peach creature with leaf hat and green eyes',
    'vtuber-pet-mascot-bear': 'VTuber pet: brown teddy bear with a top hat and green sash',
    'vtuber-logo-mosswing': 'Custom VTuber logo "Mosswing" in mossy green lettering with leaves',
    'custom-pngtuber-model-cat-mask': 'PNGTuber model of a girl wearing a black cat helmet with glowing eyes',
    'custom-pngtuber-model-violet': 'PNGTuber model of a purple-haired woman in a corset dress sitting on a suitcase',
    'custom-vtuber-pfp-wolf': 'Profile picture of a silver-haired wolf girl in a red off-shoulder dress',
    'custom-vtuber-pfp-glasses': 'Profile picture of a long-haired man with glasses',
    'custom-vtuber-pfp-leaf': 'Profile picture of a green-haired character with leaf collar and antlers',
    'custom-illustration-calico-cat': 'Illustration of a fluffy calico cat sitting in a flower meadow',
    'custom-illustration-tabby-kitten': 'Illustration of a tabby kitten with mushrooms in a meadow',
    'custom-illustration-couple-selfie': 'Couple illustration of two students taking a selfie on a phone',
    'custom-illustration-cottage-garden': 'Illustration of a woman reading with a cat in a cottage garden',
    'live2d-rigging-showcase-poster': 'Live2D rigging showcase of a white-haired VTuber model',
}
# short caption under each artwork (what it is, from the picture itself; no claims about rigging or clients)
CAPTION = {
    'custom-vtuber-model-kitsune-gown': 'Kitsune in a layered gown · full‑body model art',
    'custom-vtuber-model-witch': 'Pink-haired witch · full‑body model art',
    'custom-vtuber-model-maid': 'Cat-eared maid · full‑body model art',
    'custom-vtuber-model-rocker': 'Silver-haired rocker · full‑body model art',
    'custom-vtuber-model-dragon': 'Dragon girl in a frilled dress · full‑body model art',
    'vtuber-debut-package-keikomi': 'Debut package: model, logo, banner, expressions',
    'vtuber-stream-overlay-keikomi': 'Starting Soon, BRB and Ending screens',
    'vtuber-stream-background-room': 'Night-time streamer room background',
    'chibi-vtuber-model-witch': 'Chibi witch · full‑body chibi art',
    'custom-twitch-emotes-witch': 'Blush and surprised emotes',
    'animated-twitch-emotes-witch': 'Set of 8 animated emotes',
    'custom-twitch-emote-witch': 'Tongue-out emote',
    'vtuber-twitch-banner-eyes-blue': 'Glowing blue eye banner',
    'animated-vtuber-banner-eyes-silver': 'Animated eye banner',
    'vtuber-twitch-banner-mouth': 'Fanged smile mouth banner',
    'vtuber-twitch-banner-eyes-fire': 'Fire eye banner',
    'vtuber-twitch-banner-eyes-sakura': 'Sakura eye banner',
    'vtuber-pet-mascot-anglercat': 'Fluffy cat on an anglerfish',
    'vtuber-pet-mascot-cat': 'Leaf cat with a flower collar',
    'vtuber-pet-mascot-tiger': 'Tiger cub with a red crest',
    'vtuber-pet-mascot-snow-leopard': 'Snow leopard with a flame tail',
    'vtuber-pet-mascot-peach': 'Peach creature with a leaf hat',
    'vtuber-pet-mascot-bear': 'Teddy bear in a top hat',
    'vtuber-logo-mosswing': 'Mosswing logo in mossy lettering',
    'custom-pngtuber-model-cat-mask': 'Cat-helmet girl · PNGTuber',
    'custom-pngtuber-model-violet': 'Violet on a suitcase · PNGTuber',
    'custom-vtuber-pfp-wolf': 'Wolf girl · profile picture',
    'custom-vtuber-pfp-glasses': 'Man with glasses · profile picture',
    'custom-vtuber-pfp-leaf': 'Leaf-collar character · profile picture',
    'custom-illustration-calico-cat': 'Calico cat in a meadow',
    'custom-illustration-tabby-kitten': 'Tabby kitten with mushrooms',
    'custom-illustration-couple-selfie': 'Couple selfie illustration',
    'custom-illustration-cottage-garden': 'Reading in a cottage garden',
}
def img_size(name):
    with Image.open(os.path.join(ROOT, 'images', name + '.webp')) as im:
        return im.size
def img(name, cls='', eager=False, sizes='(max-width:560px) 46vw, 260px', thumb=False):
    w, h = img_size(name)
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    ss = ''
    tp = os.path.join(ROOT, 'images', 't', name + '.webp')
    if thumb and os.path.exists(tp):   # small version for grids; the full image opens on click
        with Image.open(tp) as ti: tw = ti.size[0]
        sp = os.path.join(ROOT, 'images', 's', name + '.webp')
        small = f'/images/s/{name}.webp 360w, ' if os.path.exists(sp) else ''
        if tw < w: ss = f' srcset="{small}/images/t/{name}.webp {tw}w, /images/{name}.webp {w}w" sizes="{sizes}"'
    return f'<img src="/images/{name}.webp"{ss} alt="{e(ALT.get(name, name))}" width="{w}" height="{h}" {load} decoding="async"{(" class=" + chr(34) + cls + chr(34)) if cls else ""}>'
def fig(name, caption, wide=False):
    return f'<figure{" class=\"wide\"" if wide else ""}><a href="/images/{name}.webp">{img(name, thumb=True, sizes="(max-width:560px) 94vw, 540px" if wide else "(max-width:560px) 46vw, 260px")}</a><figcaption>{e(caption)}</figcaption></figure>'
RIG_VIDEO = ('<figure class="wide"><video src="/images/live2d-rigging-showcase.mp4" poster="/images/live2d-rigging-showcase-poster.webp" controls muted loop playsinline preload="none" '
             'width="1280" height="720" aria-label="Live2D rigging showcase: head turns, blinking and hair physics"></video><figcaption>Live2D rigging showcase</figcaption></figure>')

SHOWCASES = [('hoodie', 'Long-haired boy in a hoodie · Live2D model', 'Live2D model of a long-haired boy in a grey hoodie: head turns, blinking, expressions and toggles'),
             ('red-dress', 'Wolf girl in red · Live2D model', 'Live2D model of a silver-haired wolf girl in a red dress: blinking, expressions and toggles')]
VIDEOS = [  # for VideoObject structured data and the video sitemap (Google video results)
    ('live2d-rigging-showcase', 'Live2D rigging showcase', 'Live2D rigging by KeikoArts: head turns, blinking and hair physics on a white-haired VTuber model.', 'PT11S', '2026-11-21'),
    ('live2d-model-showcase-hoodie', 'Live2D VTuber model: long-haired boy in a hoodie', 'Moving Live2D VTuber model by KeikoArts: head turns, blinking, expressions and toggles, ready for VTube Studio.', 'PT58S', '2026-11-24'),
    ('live2d-model-showcase-red-dress', 'Live2D VTuber model: wolf girl in a red dress', 'Moving Live2D VTuber model by KeikoArts: blinking, expressions and toggles, ready for VTube Studio.', 'PT70S', '2026-11-24'),
    ('live2d-rigging-wip-process', 'Live2D rigging work in progress: tail and hair physics', 'Behind the scenes of a KeikoArts Live2D rig: setting up tail, hair and dress physics in Live2D Cubism for a nine-tailed fox VTuber.', 'PT42S', '2026-11-24')]
def video_ld():
    return [{"@context": "https://schema.org", "@type": "VideoObject", "name": n, "description": d, "thumbnailUrl": f"{SITE}images/{k}-poster.webp",
             "contentUrl": f"{SITE}images/{k}.mp4", "uploadDate": f"{dt}T08:00:00+07:00", "duration": dur, "creator": {"@type": "Organization", "name": "KeikoArts", "url": SITE}}
            for k, n, d, dur, dt in VIDEOS]
WIP_VIDEO = ('<figure class="wide"><video src="/images/live2d-rigging-wip-process.mp4" poster="/images/live2d-rigging-wip-process-poster.webp" controls muted loop playsinline preload="none" width="960" height="540" aria-label="Live2D rigging work in progress: tail and hair physics in Live2D Cubism"></video><figcaption>Work in progress: tail, hair and dress physics in Live2D Cubism</figcaption></figure>')
SHOW_VIDEOS = ''.join(f'<figure class="wide"><video src="/images/live2d-model-showcase-{k}.mp4" poster="/images/live2d-model-showcase-{k}-poster.webp" controls muted loop playsinline preload="none" width="960" height="540" aria-label="{e(al)}"></video><figcaption>{e(cap)}</figcaption></figure>' for k, cap, al in SHOWCASES)

def svc_table(name, show_includes=True):
    s = SERVICES[name]
    if s.get('table'):
        cols = s['table']['cols']
        head = ''.join(f'<th class="num">{e(c)}</th>' for c in cols)
        rows = ''.join(f'<tr><td>{e(r)}</td>' + ''.join(f'<td class="num">{money(s["packages"][i][1])}</td>' for i in ix) + '</tr>' for r, ix in s['table']['rows'])
        return f'<div class="tblwrap"><table class="tbl"><thead><tr><th>Option</th>{head}</tr></thead><tbody>{rows}</tbody></table></div>'
    rows = ''.join(f'<tr><td>{e(p[0])}<small>{e(p[2])}</small></td><td class="num">{money(p[1])}{"<small>per emote</small>" if s.get("qty") else ""}</td></tr>' for p in s['packages'])
    return f'<div class="tblwrap"><table class="tbl"><thead><tr><th>Package</th><th class="num">Price (USD)</th></tr></thead><tbody>{rows}</tbody></table></div>'
def addons_line(name):
    ad = SERVICES[name]['addons']
    if not ad: return ''
    parts = [f'{e(a[0])} <b>{"+" + money(a[1]) if a[1] else "included"}</b>' for a in ad]
    return '<p class="addons">Add-ons: ' + ' · '.join(parts) + '</p>'

# ---------------------------------------------------------------- layout
NAV = [('/', 'Home'), ('/custom-vtuber-model/', 'VTuber Models'), ('/live2d-rigging/', 'Live2D Rigging'),
       ('/custom-pngtuber-model/', 'PNGTuber'), ('/vtuber-pricing/', 'Pricing'), ('/vtuber-portfolio/', 'Portfolio')]

# line icons for the menu (same style as the homepage header)
_mi = lambda d: '<svg class="mi" viewBox="0 0 24 24" width="17" height="17" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">' + d + '</svg>'
NAV_ICON = {
    '/': _mi('<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v9.5h13V10"/><path d="M10 19.5v-5h4v5"/>'),
    '/custom-vtuber-model/': _mi('<circle cx="12" cy="9" r="4.5"/><path d="M4.5 20c1.2-3.6 4-5.5 7.5-5.5s6.3 1.9 7.5 5.5"/><path d="M8 5.5 6.5 2.8M16 5.5l1.5-2.7"/>'),
    '/live2d-rigging/': _mi('<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>'),
    '/custom-pngtuber-model/': _mi('<rect x="4" y="4" width="16" height="16" rx="4"/><circle cx="9.5" cy="10.5" r="1"/><circle cx="14.5" cy="10.5" r="1"/><path d="M9.5 14.5c1.4 1.2 3.6 1.2 5 0"/>'),
    '/vtuber-pricing/': _mi('<path d="M3.5 12.5 12 4h7.5V11.5L11 20z"/><circle cx="16" cy="8" r="1.4"/>'),
    '/vtuber-portfolio/': _mi('<rect x="3.5" y="4.5" width="17" height="15" rx="2.5"/><circle cx="9" cy="10" r="1.8"/><path d="m4 18 5-5 4 4 3-3 4 4"/>'),
}
FOOT = [('/custom-vtuber-model/', 'Custom VTuber Model'), ('/live2d-rigging/', 'Live2D Rigging'), ('/custom-pngtuber-model/', 'Custom PNGTuber Model'), ('/custom-twitch-emotes/', 'Custom Twitch Emotes'),
        ('/vtuber-pricing/', 'VTuber Pricing'), ('/vtuber-portfolio/', 'VTuber Portfolio'), ('/vtuber-model-cost/', 'VTuber Model Cost'), ('/how-to-commission-a-vtuber-model/', 'How to Commission'), ('/live2d-vs-pngtuber/', 'Live2D vs PNGTuber'), ('/#faq', 'FAQ'), ('/#tos', 'Terms of Service'), ('/#privacy', 'Privacy')]

def page(path, title, desc, h1, crumb, body, faq, og_image, order='', extra_ld=None, eyebrow='KeikoArts · VTuber art & Live2D studio'):
    # studio signature line under the intro, in Keiko's own words (same as the homepage)
    body = re.sub(r'(<p class="lead">.*?</p>)', r'\1\n      <p class="style-line">✦ Cute meets gothic, made from scratch with updates at every stage · 200+ commissions completed</p>', body, count=1, flags=re.S)
    url = SITE + path.strip('/') + '/'
    nav = ''.join(f'<a href="{u}"{" aria-current=" + chr(34) + "page" + chr(34) if u == "/" + path + "/" else ""}>{NAV_ICON.get(u, "")}<span>{t}</span></a>' for u, t in NAV)
    order_url = '/?order=' + order.replace(' ', '%20') if order else '/?order'
    faq_html = ''.join(f'<details><summary>{e(q)}</summary><p>{a}</p></details>' for q, a in faq)
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE},
              {"@type": "ListItem", "position": 2, "name": crumb, "item": url}]},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
              {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r'<[^>]+>', '', a)}} for q, a in faq]}]
    if extra_ld: ld.extend(extra_ld if isinstance(extra_ld, list) else [extra_ld])
    lds = ''.join(f'<script type="application/ld+json">{json.dumps(x, ensure_ascii=False, separators=(",", ":"))}</script>\n' for x in ld)
    w, h = img_size(og_image)
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<script>if(location.protocol==='http:'&&/(^|\\.)keikoartist\\.com$/i.test(location.hostname))location.replace('https://'+location.host+location.pathname+location.search+location.hash);</script>
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="index, follow, max-image-preview:large">
<meta name="format-detection" content="telephone=no">
<meta name="theme-color" content="#ffffff">
<meta property="og:type" content="website">
<meta property="og:site_name" content="KeikoArtist">
<meta property="og:locale" content="en_US">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}images/{og_image}.webp">
<meta property="og:image:width" content="{w}">
<meta property="og:image:height" content="{h}">
<meta property="og:image:alt" content="{e(ALT.get(og_image, ''))}">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/images/keikoarts-logo.webp">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preload" as="style" href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Poppins:wght@400;500;600&display=swap" onload="this.onload=null;this.rel='stylesheet'">
<noscript><link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Poppins:wght@400;500;600&display=swap" rel="stylesheet"></noscript>
<link rel="stylesheet" href="/assets/site.css?v={CSS_V}">
{lds}</head>
<body>
<header>
  <div class="wrap nav">
    <a href="/" class="logo"><img src="/images/keikoarts-logo.webp" alt="KeikoArts logo" width="40" height="40"><span><b>KeikoArts</b><small>Illustration &amp; Live2D Studio</small></span></a>
    <nav class="menu" id="menu" aria-label="Main">{nav}</nav>
    <a href="{order_url}" rel="nofollow" class="btn btn-pink nav-cta arrow">Start a Project</a>
    <button class="burger" type="button" aria-label="Menu" aria-controls="menu" aria-expanded="false">☰</button>
  </div>
</header>
<main>
  <div class="wrap"><nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span>›</span>{e(crumb)}</nav></div>
{body}
  <section class="sec" id="faq"><div class="wrap">
    <h2>Frequently asked questions</h2>
    <div class="faq">{faq_html}</div>
  </div></section>
</main>
<footer>
  <div class="wrap">
    <div class="foot">
      <a href="/" class="logo"><img src="/images/keikoarts-logo.webp" alt="" width="40" height="40"><span><b>KeikoArts</b><small>Illustration &amp; Live2D Studio</small></span></a>
      <span class="foot-socs"><a href="https://discord.gg/FbgWxMPjf" target="_blank" rel="noopener"><b>Join Keiko's Discord</b></a> · <a href="https://x.com/IamKeikoArt" target="_blank" rel="noopener me">X</a> · <a href="https://www.instagram.com/iamkeikoarts/" target="_blank" rel="noopener me">Instagram</a> · <a href="https://ko-fi.com/keikoarts" target="_blank" rel="noopener me">Ko-fi</a></span>
    </div>
    <nav class="foot-links" aria-label="Services">{"".join(f'<a href="{u}">{t}</a>' for u, t in FOOT)}</nav>
    <div class="copy">© {datetime.date.today().year} KeikoArts · keikoartist.com</div>
  </div>
</footer>
<script>
(function(){{if(new Date()>=new Date('2027-01-07T00:00:00+07:00'))return;document.body.classList.add('xmas');var e=document.querySelector('.phero .eyebrow');if(e){{var a=document.createElement('a');a.href='/?spin=1';a.className='xmas-pill';a.innerHTML='<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" style="vertical-align:-3px"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6 5.6 18.4" stroke="currentColor" stroke-width="1.2" opacity=".6"/><circle cx="12" cy="12" r="2.2" fill="currentColor"/></svg> Spin the Christmas wheel';e.insertAdjacentElement('afterend',a);}}}})();
(function(){{try{{var q=new URLSearchParams(location.search),r=document.referrer?new URL(document.referrer).hostname:'';var s=q.get('ref')||q.get('utm_source')||(r&&r!==location.hostname?r:'');navigator.sendBeacon('/stats-api.php',new Blob([JSON.stringify({{e:'view',p:location.pathname,s:s}})],{{type:'application/json'}}));}}catch(_){{}}}})();
(function(){{var b=document.querySelector('.burger'),m=document.getElementById('menu');
b.addEventListener('click',function(){{var o=m.classList.toggle('open');b.setAttribute('aria-expanded',o)}});
var v=document.querySelector('video');if(v&&'IntersectionObserver'in window){{new IntersectionObserver(function(es){{es.forEach(function(x){{if(!x.isIntersecting&&!v.paused)v.pause()}})}}).observe(v)}}}})();
</script>
</body>
</html>
'''

def related(exclude):
    items = [('/custom-vtuber-model/', 'Custom VTuber Model', 'Original Live2D model, bust to full body'),
             ('/live2d-rigging/', 'Live2D Rigging', 'Rig your art for VTube Studio'),
             ('/custom-pngtuber-model/', 'Custom PNGTuber Model', 'Idle + talking avatar, from $60'),
             ('/custom-twitch-emotes/', 'Custom Twitch Emotes', 'Static and animated, from $5 each'),
             ('/vtuber-pricing/', 'VTuber Pricing', 'Every service and add-on'),
             ('/vtuber-portfolio/', 'VTuber Portfolio', 'Models, pets, emotes and more')]
    cards = ''.join(f'<a href="{u}"><b>{t}</b><span>{d}</span></a>' for u, t, d in items if u != exclude)
    return f'''  <section class="sec"><div class="wrap">
    <h2>Related services</h2>
    <div class="related">{cards}</div>
  </div></section>'''

def cta(title, text, order, label):
    return f'''  <div class="wrap"><div class="cta"><div><h2>{title}</h2><p>{text}</p></div>
    <a class="btn btn-pink arrow" rel="nofollow" href="{"/?order=" + order.replace(" ", "%20") if order else "/?order"}">{label}</a></div></div>'''

def service_ld(name, url, desc, low):
    return {"@context": "https://schema.org", "@type": "Service", "name": name, "url": url, "description": desc,
            "serviceType": name, "areaServed": "Worldwide",
            "provider": {"@type": "ProfessionalService", "name": "KeikoArts", "url": SITE},
            "offers": {"@type": "Offer", "price": str(low), "priceCurrency": "USD", "url": url}}

V, P = SERVICES['VTuber'], SERVICES['PNGTuber']
vp = {p[0]: p[1] for p in V['packages']}
vadd = {a[0]: a[1] for a in V['addons']}
PAY = 'Pay with a one-click PayPal link (card or PayPal balance) in USD: in full, 50/50 (half upfront, half before final files), or in 3 installments for orders above $150. 13% tax is added on every invoice.'

# ---------------------------------------------------------------- 1. custom VTuber model
def custom_vtuber():
    vtubers = [x for x in GALLERY['VTuber']]
    body = f'''  <section class="wrap phero">
    <div>
      <p class="eyebrow">VTuber model commission</p>
      <h1 class="serif">Custom VTuber Model Commission</h1>
      <p class="lead">{e(DETAILS["VTuber"]["about"])} I draw your character from scratch, split the art into layers ready for Live2D and, if you choose, rig it and set it up for VTube Studio so you can go live.</p>
      <div class="btns"><a class="btn btn-pink arrow" rel="nofollow" href="/?order=VTuber">Start your VTuber model</a><a class="btn btn-ghost" href="/vtuber-pricing/">See all prices</a></div>
      <div class="facts"><span>Art from <b>{money(vp["Bust · Art only"])}</b></span><span>Art + rig from <b>{money(vp["Bust · Art + Rig"])}</b></span><span>About <b>{e(V["eta"])}</b></span></div>
    </div>
    <figure>{img(vtubers[0], eager=True)}</figure>
  </section>

  <section class="sec"><div class="wrap">
    <h2>Choose your model size</h2>
    <p>The size decides how much of your character is drawn and rigged. Bigger models have more parts to draw and move, so they take longer and cost more.</p>
    <div class="grid">
      <div class="box"><h3>Bust</h3><p>Your character up to the chest. The classic "just chatting" framing, and the easiest way to start.</p><p class="price">from {money(vp["Bust · Art only"])}</p></div>
      <div class="box"><h3>Half body</h3><p>Up to the waist, so arms, hands and more of the outfit are on screen.</p><p class="price">from {money(vp["Half body · Art only"])}</p></div>
      <div class="box"><h3>Full body</h3><p>Your whole character from head to toe, for layouts and content that show the full design.</p><p class="price">from {money(vp["Full body · Art only"])}</p></div>
    </div>
  </section>

  <section class="sec"><div class="wrap">
    <h2>Art only, art + rig, or rig only</h2>
    <p>You can order just the Live2D character art, the art together with rigging, or only the rigging for art you already have.</p>
    {svc_table("VTuber")}
    <div class="grid" style="margin-top:14px">
      <div class="box"><h3>Art only</h3><p>Your character art split into layers and ready to rig (PSD). Good if you already work with a rigger.</p></div>
      <div class="box"><h3>Art + Rig</h3><p>The complete package: art, Live2D rigging and a VTube Studio file, ready to stream.</p></div>
      <div class="box"><h3>Rig only</h3><p>Send me your layered PSD and I rig it. More on the <a href="/live2d-rigging/">Live2D rigging page</a>.</p></div>
    </div>
    <p class="note">{e(DETAILS["VTuber"]["notes"])} The final price is confirmed on your invoice before you pay.</p>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Expressions, tracking and extras</h2>
    <div class="grid two">
      <div class="box"><h3>What the rig includes</h3><ul><li>Head turns and blinking</li><li>Lip-sync</li><li>Hair and clothing physics</li><li>A VTube Studio file, ready to stream</li></ul><p style="margin-top:8px">VTube Studio tracks your face with a webcam or an iPhone.</p></div>
      <div class="box"><h3>Add-ons</h3><ul>{"".join(f"<li>{e(a[0])}: <b>+{money(a[1])}</b></li>" for a in V["addons"])}</ul><p style="margin-top:8px">VBridger is an extra setup for more expressive mouth tracking.</p></div>
    </div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Expression toggle ideas</h2>
    <p>Toggles are extra faces or effects you switch on with a hotkey while streaming (+{money(vadd["Extra expression / toggle"])} each). Popular picks:</p>
    <ol class="toggle-ideas"><li><b>01</b>Blush</li><li><b>02</b>Teary eyes</li><li><b>03</b>Crying</li><li><b>04</b>Heart eyes</li><li><b>05</b>Starry eyes</li><li><b>06</b>Angry mark</li><li><b>07</b>Dark face</li><li><b>08</b>Dizzy eyes</li><li><b>09</b>Shocked (O_O)</li><li><b>10</b>&gt;_&lt;</li><li><b>11</b>Sweat drop</li><li><b>12</b>Sleepy (zzz)</li></ol>
    <p class="note">Smiling, blinking and closed eyes already come from face tracking, so there's no need to pick them as toggles. Send your own references too; the final look is drawn to match your character.</p>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Custom character design</h2>
    <p>You don't need a finished character sheet. Send a description, a few references or an existing design, and I work out the outfit, colors and details with you. Small changes are unlimited during the sketch stage, so the design can settle before coloring starts.</p>
    <div class="gallery">{"".join(fig(x, CAPTION.get(x, "VTuber model art")) for x in vtubers)}</div>
    <p class="note">More work in the <a href="/vtuber-portfolio/">VTuber portfolio</a>.</p>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>How ordering works</h2>
    <ol class="steps">
      <li><b>Send the order form</b><span>Pick the size and option, describe your character and attach references.</span></li>
      <li><b>Get your invoice</b><span>I review your request and email you an invoice (PDF), usually within 6 hours (WIB, GMT+7). {e(PAY)}</span></li>
      <li><b>Sketch to rig</b><span>Sketch, lineart, coloring and rigging, with progress updates at every stage.</span></li>
      <li><b>Go live</b><span>You receive your files and VTube Studio model. Estimated time: {e(V["eta"])}; rush delivery (+25%) is available.</span></li>
    </ol>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Usage rights</h2>
    <p>Personal use, streaming, monetized videos and social media are included. Merch and other commercial rights are an add-on (+{money(vadd["Commercial / merch rights"])}). The artist keeps the copyright; reselling, NFTs and AI training are not allowed. Read the full <a href="/#tos" style="color:var(--pink-text);font-weight:600">Terms of Service</a>.</p>
    <p>Preparing a debut? <a href="/vtuber-pricing/#vtuber-packages" style="color:var(--pink-text);font-weight:600">VTuber packages</a> start at {money(SERVICES["VTuber Packages"]["from"])} and bundle the model with emotes, a background, an overlay and more.</p>
  </div></section>
{guides_block("")}
{related("/custom-vtuber-model/")}
{cta("Got a VTuber in mind?", "Send me your idea and I'll email your invoice. You only pay after you've checked it.", "VTuber", "Start your VTuber model")}'''
    faq = [
        ('How much does a custom VTuber model cost?', f'Art only costs {money(vp["Bust · Art only"])} (bust), {money(vp["Half body · Art only"])} (half body) or {money(vp["Full body · Art only"])} (full body). Art + rig costs {money(vp["Bust · Art + Rig"])}, {money(vp["Half body · Art + Rig"])} or {money(vp["Full body · Art + Rig"])}. Complex designs with wings or many accessories may cost a bit more; the final price is on your invoice. See <a href="/vtuber-pricing/">all prices</a>.'),
        ('How long does a VTuber model take?', f'About {e(V["eta"])}, depending on the complexity of the design and the queue. Rush delivery (+25%) is available in the order form.'),
        ('Does the model work with VTube Studio?', 'Yes. Art + Rig and Rig only orders include a VTube Studio file, ready to stream with webcam or iPhone face tracking. Art only orders get a layered PSD that is ready to rig.'),
        ('Can I use my model on monetized streams?', f'Yes. Streaming, monetized videos and social media are included. Merch and other commercial rights are an add-on (+{money(vadd["Commercial / merch rights"])}).'),
        ('I already have VTuber art. Can you just rig it?', f'Yes, rig only starts at {money(vp["Bust · Rig only"])}. Send your layered PSD with the order form. See <a href="/live2d-rigging/">Live2D rigging</a>.'),
        ('How do I pay?', 'After you send the order form, I email you an invoice as a PDF. ' + e(PAY)),
    ]
    desc = f'Commission a custom Live2D VTuber model: original character art, bust to full body, rigged for VTube Studio. Art from {money(vp["Bust · Art only"])}, art + rig from {money(vp["Bust · Art + Rig"])}.'
    return page('custom-vtuber-model', 'Custom VTuber Model Commission | KeikoArtist', desc, 'Custom VTuber Model Commission', 'Custom VTuber Model',
                body, faq, vtubers[0], 'VTuber', service_ld('Custom VTuber model commission', SITE + 'custom-vtuber-model/', desc, V['from']))

# ---------------------------------------------------------------- 2. Live2D rigging
def rigging():
    body = f'''  <section class="wrap phero">
    <div>
      <p class="eyebrow">Live2D rigging commission</p>
      <h1 class="serif">Live2D Rigging for VTuber Models</h1>
      <p class="lead">Turn layered character art into a moving VTuber model. Rigging covers head turns, blinking, lip-sync and hair &amp; clothing physics, and you get a VTube Studio file that's ready to stream.</p>
      <div class="btns"><a class="btn btn-pink arrow" rel="nofollow" href="/?order=VTuber">Order rigging</a><a class="btn btn-ghost" href="/custom-vtuber-model/">Need the art too?</a></div>
      <div class="facts"><span>Rig only from <b>{money(vp["Bust · Rig only"])}</b></span><span>Art + rig from <b>{money(vp["Bust · Art + Rig"])}</b></span><span>VTube Studio <b>ready</b></span></div>
    </div>
    <figure class="cover"><video src="/images/live2d-rigging-showcase.mp4" poster="/images/live2d-rigging-showcase-poster.webp" controls muted loop playsinline preload="none" width="1280" height="720" aria-label="Live2D rigging showcase: head turns, blinking and hair physics"></video></figure>
  </section>

  <section class="sec"><div class="wrap">
    <h2>What the rigging includes</h2>
    <div class="grid four">
      <div class="box"><h3>Head turns</h3><p>Your model follows your head left, right, up and down.</p></div>
      <div class="box"><h3>Blinking</h3><p>Eye blinks that follow your own eyes.</p></div>
      <div class="box"><h3>Lip-sync</h3><p>The mouth moves when you talk.</p></div>
      <div class="box"><h3>Physics</h3><p>Hair and clothing that sway naturally as you move.</p></div>
    </div>
    <p class="note">Every rig is delivered with a VTube Studio file. VTube Studio can track your face with a webcam or an iPhone. Rigging on Team Keiko is done by Tomy, our rigger.</p>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Rigging prices</h2>
    <p>Prices depend on how much of the character is rigged. Rig only is for art you already have; art + rig includes the character art.</p>
    {svc_table("VTuber")}
    <p class="addons">Add-ons: extra expression / toggle <b>+{money(vadd["Extra expression / toggle"])}</b> · hand toggle <b>+{money(vadd["Hand toggle"])}</b> each · VBridger <b>+{money(vadd["VBridger"])}</b> · extra outfit <b>+{money(vadd["Extra outfit"])}</b> · extra hairstyle <b>+{money(vadd["Extra hairstyle"])}</b></p>
    <p class="note">Rigging a pet companion? <a href="/vtuber-pricing/#vtuber-pet">VTuber pet art + rig</a> is {money(SERVICES["VTuber Pet"]["packages"][1][1])}.</p>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>What to send for rig only</h2>
    <div class="grid two">
      <div class="box"><h3>A layered PSD</h3><p>Rigging needs your character art as a PSD with the parts on separate layers (for example eyes, mouth, hair and clothing pieces). Attach it in the order form, or paste a link to it.</p></div>
      <div class="box"><h3>Your wishes</h3><p>Tell me which expressions or toggles you want, and anything special about how the model should move. I review everything before your invoice is sent.</p></div>
    </div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>How it works</h2>
    <ol class="steps">
      <li><b>Send the order form</b><span>Choose VTuber, pick "Rig only" (or "Art + Rig") and attach your files.</span></li>
      <li><b>Get your invoice</b><span>I check your request and email you an invoice (PDF). {e(PAY)}</span></li>
      <li><b>Rigging</b><span>Your model is rigged with progress updates along the way.</span></li>
      <li><b>Delivery</b><span>You receive the Live2D model and VTube Studio file. VTuber models take about {e(V["eta"])}.</span></li>
    </ol>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Rigged models</h2>
    <div class="gallery">{RIG_VIDEO}{SHOW_VIDEOS}{WIP_VIDEO}{"".join(fig(x, "VTuber model art") for x in GALLERY["VTuber"][:3])}</div>
    <p class="note">More in the <a href="/vtuber-portfolio/">portfolio</a>.</p>
  </div></section>
{related("/live2d-rigging/")}
{cta("Bring your art to life", "Send your PSD and get your invoice by email.", "VTuber", "Order Live2D rigging")}'''
    faq = [
        ('How much does Live2D rigging cost?', f'Rig only costs {money(vp["Bust · Rig only"])} for a bust, {money(vp["Half body · Rig only"])} for half body and {money(vp["Full body · Rig only"])} for full body. Extra expressions or toggles are +{money(vadd["Extra expression / toggle"])} each and VBridger is +{money(vadd["VBridger"])}.'),
        ('What do I need to send?', 'A layered PSD of your character, with the parts on separate layers so they can move. Attach it in the order form or paste a link.'),
        ('Can you rig art that someone else drew?', 'Yes. Rig only is made for art you already have; just send the layered PSD.'),
        ('Which apps does the model work with?', 'Every rig comes with a VTube Studio file. VTube Studio supports webcam and iPhone face tracking.'),
        ('What is VBridger?', f'VBridger is an extra setup for more expressive mouth tracking. You can add it to your order for +{money(vadd["VBridger"])}.'),
        ('How long does rigging take?', f'VTuber models take about {e(V["eta"])}, depending on the model and the queue. I confirm the timeline when I review your files.'),
    ]
    desc = f'Live2D rigging for your VTuber art: head turns, blinking, lip-sync and hair & clothing physics, delivered with a VTube Studio file. Rig only from {money(vp["Bust · Rig only"])}.'
    return page('live2d-rigging', 'Live2D Rigging Commission for VTuber Models | KeikoArtist', desc, 'Live2D Rigging for VTuber Models', 'Live2D Rigging',
                body, faq, 'live2d-rigging-showcase-poster', 'VTuber', [service_ld('Live2D rigging', SITE + 'live2d-rigging/', desc, vp["Bust · Rig only"])] + video_ld())

# ---------------------------------------------------------------- 3. PNGTuber
def pngtuber():
    pk = {p[0]: p for p in P['packages']}
    imgs = GALLERY['PNGTuber']
    body = f'''  <section class="wrap phero">
    <div>
      <p class="eyebrow">PNGTuber commission</p>
      <h1 class="serif">Custom PNGTuber Model</h1>
      <p class="lead">{e(DETAILS["PNGTuber"]["about"])} Your character switches between idle and talking images while you speak, and blinks on its own. No rigging needed, so it's quicker and more affordable than a Live2D model.</p>
      <div class="btns"><a class="btn btn-pink arrow" rel="nofollow" href="/?order=PNGTuber">Start your PNGTuber</a><a class="btn btn-ghost" href="/custom-vtuber-model/">Compare with Live2D</a></div>
      <div class="facts"><span>From <b>{money(P["from"])}</b></span><span>About <b>{e(P["eta"])}</b></span></div>
    </div>
    <figure>{img(imgs[0], eager=True)}</figure>
  </section>

  <section class="sec"><div class="wrap">
    <h2>Packages</h2>
    {svc_table("PNGTuber")}
    {addons_line("PNGTuber")}
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>What you get</h2>
    <div class="grid">{"".join(f'<div class="box"><p>{e(x)}</p></div>' for x in DETAILS["PNGTuber"]["includes"])}</div>
    <p class="note">{e(DETAILS["PNGTuber"]["notes"])}</p>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>PNGTuber or Live2D VTuber?</h2>
    <div class="grid two">
      <div class="box"><h3>PNGTuber</h3><p>Image-based avatar: idle and talking states with blinking. From {money(P["from"])}, about {e(P["eta"])}. Ideal to start streaming quickly.</p></div>
      <div class="box"><h3>Live2D VTuber model</h3><p>Fully rigged model that follows your head, eyes and mouth, with hair and clothing physics. From {money(vp["Bust · Art + Rig"])} with rigging, about {e(V["eta"])}. <a href="/custom-vtuber-model/">Custom VTuber models</a></p></div>
    </div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>PNGTuber examples</h2>
    <div class="gallery">{"".join(fig(x, CAPTION.get(x, "PNGTuber model")) for x in imgs)}</div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>How ordering works</h2>
    <ol class="steps">
      <li><b>Send the order form</b><span>Choose bust-up or thigh-up / full body and describe your character.</span></li>
      <li><b>Get your invoice</b><span>I email you an invoice (PDF). {e(PAY)}</span></li>
      <li><b>Drawing</b><span>Sketch, lineart and coloring, with updates along the way.</span></li>
      <li><b>Start streaming</b><span>You receive transparent PNGs for each state, ready for your PNGTuber app.</span></li>
    </ol>
  </div></section>
{related("/custom-pngtuber-model/")}
{cta("Start streaming with your own PNGTuber", "Send your idea and get your invoice by email.", "PNGTuber", "Start your PNGTuber")}'''
    faq = [
        ('How much does a custom PNGTuber cost?', f'{e(pk["Bust-up"][0])} is {money(pk["Bust-up"][1])} and {e(pk["Thigh-up / full body"][0])} is {money(pk["Thigh-up / full body"][1])}. Extra expressions are +{money(P["addons"][0][1])} each; props and accessories are included.'),
        ('Which apps can I use it with?', 'You get transparent PNGs that are ready for PNGTuber Plus or Veadotube.'),
        ('How long does it take?', f'About {e(P["eta"])}.'),
        ('What is the difference between a PNGTuber and a VTuber model?', 'A PNGTuber swaps between images (idle, talking, blinking). A Live2D VTuber model is rigged, so it follows your head, eyes and mouth smoothly. See <a href="/custom-vtuber-model/">custom VTuber models</a>.'),
        ('Can I use it on monetized streams?', 'Yes. Personal use, streaming, monetized content and social media are allowed. Merch / commercial rights are a $30 add-on.'),
    ]
    desc = f'A custom PNGTuber avatar with idle and talking states and blinking, delivered as transparent PNGs ready for PNGTuber Plus or Veadotube. From {money(P["from"])}.'
    return page('custom-pngtuber-model', 'Custom PNGTuber Model Commission | KeikoArtist', desc, 'Custom PNGTuber Model', 'Custom PNGTuber Model',
                body, faq, imgs[0], 'PNGTuber', service_ld('Custom PNGTuber model', SITE + 'custom-pngtuber-model/', desc, P['from']))

# ---------------------------------------------------------------- 3b. custom Twitch emotes
def emotes():
    E = SERVICES['Emotes']; D = DETAILS['Emotes']
    pk = {p[0]: p[1] for p in E['packages']}; ad = {a[0]: a[1] for a in E['addons']}
    imgs = GALLERY['Emotes']
    # still image on top (fast, works as a link preview); the animated set stays in the gallery below (lazy, small version)
    hero = next((x for x in imgs if 'animated' not in x), imgs[0])
    body = f"""  <section class="wrap phero">
    <div>
      <p class="eyebrow">Emote commission</p>
      <h1 class="serif">Custom Twitch Emotes</h1>
      <p class="lead">{e(D["about"])} Hand-drawn static or animated emotes of your own character or VTuber, delivered in Twitch and Discord sizes.</p>
      <div class="btns"><a class="btn btn-pink arrow" rel="nofollow" href="/?order=Emotes">Order your emotes</a><a class="btn btn-ghost" href="/vtuber-pricing/">See all prices</a></div>
      <div class="facts"><span>Static <b>{money(pk["Static emote"])}</b> each</span><span>Animated <b>{money(pk["Animated emote"])}</b> each</span><span>About <b>{e(E["eta"])}</b></span></div>
    </div>
    <figure>{img(hero, eager=True)}</figure>
  </section>

  <section class="sec"><div class="wrap">
    <h2>Emote prices</h2>
    {svc_table("Emotes")}
    {addons_line("Emotes")}
    <p class="note">{e(D["notes"])} Order as many as you like in one form; the total updates as you change the quantity.</p>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>What you get</h2>
    <div class="grid">{"".join(f'<div class="box"><p>{e(x)}</p></div>' for x in D["includes"])}</div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Static or animated?</h2>
    <div class="grid two">
      <div class="box"><h3>Static emotes</h3><p>One clear expression per emote, as a transparent PNG. {money(pk["Static emote"])} per emote. Good for a first set: love, cry, hype, laugh.</p></div>
      <div class="box"><h3>Animated emotes</h3><p>A short looping animation as a GIF, for reactions that need movement. {money(pk["Animated emote"])} per emote.</p></div>
    </div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Emote examples</h2>
    <div class="gallery">{"".join(fig(x, CAPTION.get(x, "Twitch emotes"), wide="animated" in x) for x in imgs)}</div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>How ordering works</h2>
    <ol class="steps">
      <li><b>Send the order form</b><span>Choose static or animated, set how many, and list the expressions you want (for example love, cry, hype, sleepy). Attach a reference of your character.</span></li>
      <li><b>Get your invoice</b><span>I email you an invoice (PDF). {e(PAY)}</span></li>
      <li><b>Drawing</b><span>Sketch first, then lineart and coloring, with updates along the way.</span></li>
      <li><b>Upload and use</b><span>You receive transparent PNG or GIF files in 112, 56 and 28 px, ready to upload to Twitch or Discord.</span></li>
    </ol>
  </div></section>
{related("/custom-twitch-emotes/")}
{cta("Give your chat its own emotes", "Send your list of expressions and get your invoice by email.", "Emotes", "Order your emotes")}"""
    faq = [
        ('How much do custom Twitch emotes cost?', f'Static emotes are {money(pk["Static emote"])} each and animated emotes are {money(pk["Animated emote"])} each. A sub badge set (3 badges) is +{money(ad["Sub badge set (3)"])}. 13% tax is added on the invoice.'),
        ('What sizes and files do I get?', 'Transparent PNG files for static emotes and GIF files for animated emotes, in 112, 56 and 28 px. Twitch-ready resizing is included.'),
        ('How long do emotes take?', f'About {e(E["eta"])}, depending on how many you order and the queue. Rush delivery (+25%) is available in the order form.'),
        ('Can you draw emotes of my VTuber or original character?', 'Yes. Attach a reference of your character in the order form and list the expressions you want.'),
        ('Can I use the emotes on Discord too?', 'Yes. The files are sized for Twitch and Discord.'),
        ('Can I use them on monetized streams?', 'Yes. Personal use, streaming, monetized content and social media are allowed. Merch / commercial rights are a $30 add-on.'),
    ]
    desc = f'Custom Twitch emotes of your character or VTuber: static {money(pk["Static emote"])} and animated {money(pk["Animated emote"])} per emote, in Twitch and Discord sizes. Sub badges available.'
    return page('custom-twitch-emotes', 'Custom Twitch Emotes Commission | KeikoArtist', desc, 'Custom Twitch Emotes', 'Custom Twitch Emotes',
                body, faq, hero, 'Emotes', service_ld('Custom Twitch emotes', SITE + 'custom-twitch-emotes/', desc, E['from']))

# ---------------------------------------------------------------- 4. portfolio
def portfolio():
    cats = [('vtuber-models', 'VTuber models', 'VTuber', '/custom-vtuber-model/', 'Custom VTuber model', 'VTuber model'),
            ('vtuber-packages', 'VTuber debut packages', 'VTuber Packages', '/vtuber-pricing/#vtuber-packages', 'VTuber packages', 'Debut package'),
            ('pngtuber', 'PNGTuber models', 'PNGTuber', '/custom-pngtuber-model/', 'Custom PNGTuber model', 'PNGTuber'),
            ('chibi', 'Chibi VTuber', 'Chibi VTuber', '/vtuber-pricing/#chibi-vtuber', 'Chibi VTuber prices', 'Chibi model art'),
            ('pets', 'VTuber pets', 'VTuber Pet', '/vtuber-pricing/#vtuber-pet', 'VTuber pet prices', 'VTuber pet'),
            ('emotes', 'Emotes', 'Emotes', '/vtuber-pricing/#emotes', 'Emote prices', 'Emotes'),
            ('banners', 'Eye and mouth banners', 'Banner', '/vtuber-pricing/#banner', 'Banner prices', 'Banner'),
            ('logos', 'VTuber logos', 'VTuber Logo', '/vtuber-pricing/#vtuber-logo', 'Logo prices', 'VTuber logo'),
            ('pfp', 'Profile pictures', 'Custom PFP', '/vtuber-pricing/#custom-pfp', 'PFP prices', 'Profile picture'),
            ('overlays', 'Stream overlays and backgrounds', None, '/vtuber-pricing/#stream-overlay', 'Overlay prices', 'Stream asset'),
            ('illustrations', 'Illustrations', 'Custom Inquiry', '/?order=Custom%20Inquiry', 'Request a custom piece', 'Illustration')]
    seen = set(); cards = []; counts = []
    order_key = {'overlays': 'Stream Overlay', 'illustrations': 'Custom Inquiry'}
    short = {'vtuber-models': 'VTuber model', 'vtuber-packages': 'Debut package', 'pngtuber': 'PNGTuber', 'chibi': 'Chibi VTuber', 'pets': 'VTuber pet',
             'emotes': 'Emotes', 'banners': 'Banner', 'logos': 'VTuber logo', 'pfp': 'Profile picture', 'overlays': 'Stream asset', 'illustrations': 'Illustration'}
    for cid, title, key, link, linktext, cap in cats:
        names = ['vtuber-stream-overlay-keikomi', 'vtuber-stream-background-room'] if key is None else [n for n in GALLERY.get(key, []) if n != 'vtuber-stream-background-room' or key == 'Background']
        if key == 'VTuber Packages': names = ['vtuber-debut-package-keikomi']
        names = [n for n in names if n not in seen and os.path.exists(os.path.join(ROOT, 'images', n + '.webp'))]
        if not names and cid != 'vtuber-models': continue
        seen.update(names)
        okey = order_key.get(cid, key)
        go = '/?order=' + okey.replace(' ', '%20')
        n_here = len(names)
        if cid == 'vtuber-models':
            n_here += 1
            for k, cap, al in SHOWCASES:
                n_here += 1
                cards.append(f'<article class="wcard wide" data-cat="vtuber-models"><div class="wimg"><video src="/images/live2d-model-showcase-{k}.mp4" poster="/images/live2d-model-showcase-{k}-poster.webp" controls muted loop playsinline preload="none" width="960" height="540" aria-label="{e(al)}"></video></div>'
                             f'<div class="wbody"><div class="wtags"><span class="wtag">Live2D model</span><span class="wtag soft">Moving model</span></div><h3>{e(cap.split(" · ")[0])}</h3><a class="wgo" rel="nofollow" href="/?order=VTuber">Order similar →</a></div></article>')
            cards.append('<article class="wcard wide" data-cat="vtuber-models"><div class="wimg"><video src="/images/live2d-rigging-showcase.mp4" poster="/images/live2d-rigging-showcase-poster.webp" controls muted loop playsinline preload="none" width="1280" height="720" aria-label="Live2D rigging showcase: head turns, blinking and hair physics"></video></div>'
                         '<div class="wbody"><div class="wtags"><span class="wtag">Live2D rigging</span><span class="wtag soft">Showcase</span></div><h3>Live2D rigging showcase</h3><a class="wgo" href="/live2d-rigging/">About rigging →</a></div></article>')
        for n in names:
            w, h = img_size(n)
            wide = w > 1.4 * h
            capt = CAPTION.get(n, cap)
            parts = capt.split(' · ')
            sub = f'<span class="wtag soft">{e(parts[1])}</span>' if len(parts) > 1 else ''
            sizes = "(max-width:560px) 94vw, 560px" if wide else "(max-width:560px) 94vw, (max-width:900px) 46vw, 380px"
            cards.append(f'<article class="wcard{" wide" if wide else ""}" data-cat="{cid}"><a class="wimg" href="/images/{n}.webp">{img(n, thumb=True, sizes=sizes)}</a>'
                         f'<div class="wbody"><div class="wtags"><span class="wtag">{e(short[cid])}</span>{sub}</div><h3>{e(parts[0])}</h3><a class="wgo" rel="nofollow" href="{go}">Order similar →</a></div></article>')
        counts.append((cid, title, n_here))
    total = sum(c for _, _, c in counts)
    chips = f'<button type="button" class="wf on" data-f="all" aria-pressed="true">All <b>{total}</b></button>' + ''.join(
        f'<button type="button" class="wf" data-f="{cid}" aria-pressed="false">{e(title)} <b>{c}</b></button>' for cid, title, c in counts)
    filter_js = ("(function(){var g=document.getElementById('wgrid'),cs=[].slice.call(g.children),bs=[].slice.call(document.querySelectorAll('.wf')),out=document.getElementById('wcount');"
                 "function set(f){var n=0;cs.forEach(function(c){var on=f==='all'||c.getAttribute('data-cat')===f;c.hidden=!on;if(on)n++;});"
                 "bs.forEach(function(b){var on=b.getAttribute('data-f')===f;b.classList.toggle('on',on);b.setAttribute('aria-pressed',on);});out.textContent='Showing '+n+(n===1?' work':' works');}"
                 "bs.forEach(function(b){b.addEventListener('click',function(){var f=b.getAttribute('data-f');set(f);history.replaceState(null,'',f==='all'?location.pathname:'#'+f);});});"
                 "var h=location.hash.slice(1);if(h&&bs.some(function(b){return b.getAttribute('data-f')===h;})){set(h);setTimeout(function(){document.getElementById('works').scrollIntoView();var o=document.querySelector('.wf.on'),w=o&&o.parentNode;if(w)w.scrollLeft=o.offsetLeft-(w.clientWidth-o.offsetWidth)/2;},50);}})();")
    hero_img = img(GALLERY["VTuber"][0], eager=True)
    body = ('  <section class="wrap phero">\n    <div>\n      <p class="eyebrow">Portfolio</p>\n'
            '      <h1 class="serif">VTuber &amp; Live2D Art Portfolio</h1>\n'
            '      <p class="lead">VTuber models, Live2D rigging, PNGTubers, pets, emotes, banners, logos and illustrations made by Team Keiko. Every piece was drawn from scratch. Tap an image to see it full size.</p>\n'
            '      <div class="btns"><a class="btn btn-pink arrow" rel="nofollow" href="/?order">Start a project</a><a class="btn btn-ghost" href="/vtuber-pricing/">See prices</a></div>\n'
            f'    </div>\n    <figure>{hero_img}</figure>\n  </section>\n\n'
            '  <section class="sec" id="works"><div class="wrap">\n    <h2>All works</h2>\n'
            f'    <div class="wfilters" role="toolbar" aria-label="Filter works">{chips}</div>\n'
            f'    <p class="wcount" id="wcount" aria-live="polite">Showing {total} works</p>\n'
            f'    <div class="wgrid" id="wgrid">{"".join(cards)}</div>\n  </div></section>\n'
            f'  <script>{filter_js}</script>\n'
            + related("/vtuber-portfolio/") + '\n'
            + cta("Want something like this?", "Tell me your idea and get your invoice by email.", "", "Start a project"))
    faq = [
        ('Who made these artworks?', 'Team Keiko: Keiko (artist), Zhopio (illustrator) and Tomy (rigger). Every piece here is original work, drawn from scratch.'),
        ('Can I order something in a similar style?', 'Yes. Mention the piece you like in the order form, and attach it as a reference if you want.'),
        ('Will my commission be shown in the portfolio?', 'Finished work may be shared on the portfolio and socials, unless you ask for a private or delayed reveal.'),
        ('How do I order?', 'Click "Start a project", choose a service, describe your idea and send the form. I email you your invoice (PDF) with a one-click PayPal link.'),
    ]
    desc = 'VTuber models, Live2D rigging, PNGTubers, chibi models, pets, emotes, banners, logos and illustrations made by KeikoArts for streamers.'
    gallery_ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "VTuber & Live2D Art Portfolio", "url": SITE + 'vtuber-portfolio/',
                  "about": {"@type": "ProfessionalService", "name": "KeikoArts", "url": SITE}}
    return page('vtuber-portfolio', 'VTuber Model & Live2D Art Portfolio | KeikoArtist', desc, 'VTuber & Live2D Art Portfolio', 'VTuber Portfolio',
                body, faq, GALLERY['VTuber'][0], '', gallery_ld)

# ---------------------------------------------------------------- 5. pricing
def pricing():
    slug = lambda n: re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')
    pages = {'VTuber': '/custom-vtuber-model/', 'PNGTuber': '/custom-pngtuber-model/', 'Emotes': '/custom-twitch-emotes/'}
    order = ['VTuber', 'VTuber Packages', 'PNGTuber', 'Chibi VTuber', 'VTuber Pet', 'Emotes', 'Custom PFP', 'Banner', 'VTuber Logo', 'Stream Overlay', 'Background']
    opt_help = {'Art only': 'Layered PSD, ready to rig', 'Art + Rig': 'Moving Live2D model + VTube Studio file', 'Rig only': 'You send your PSD, I rig it'}

    def thumb(n):
        g = GALLERY.get(n) or []
        if not g: return ''
        f = g[0]
        src = f'/images/s/{f}.webp' if os.path.exists(os.path.join(ROOT, 'images', 's', f + '.webp')) else f'/images/t/{f}.webp'
        return f'<img class="pr-thumb" src="{src}" alt="{e(ALT.get(f, n))}" width="96" height="96" loading="lazy" decoding="async">'

    def addon_chips(n):
        ad = SERVICES[n]['addons']
        if not ad: return ''
        return '<div class="pr-adds"><span class="pr-adds-l">Add-ons</span>' + ''.join(
            f'<span class="pr-add">{e(a[0])} <b>{"+" + money(a[1]) if a[1] else "included"}</b></span>' for a in ad) + '</div>'

    blocks = []
    for n in order:
        s = SERVICES[n]
        about = DETAILS.get(n, {}).get('about', '')
        more = f'<a class="pr-more" href="{pages[n]}">Details →</a>' if n in pages else ''
        go = '/?order=' + n.replace(' ', '%20')
        if s.get('table'):
            cols = s['table']['cols']
            sizes = {'Bust': 'Up to the chest', 'Half': 'Up to the waist', 'Full': 'Head to toe'}
            cards = ''
            for ci, col in enumerate(cols):
                lines = ''.join(f'<li><span>{e(r)}<small>{e(opt_help.get(r, ""))}</small></span><b>{money(s["packages"][ix[ci]][1])}</b></li>' for r, ix in s['table']['rows'])
                label = 'Half body' if col == 'Half' else 'Full body' if col == 'Full' else col
                cards += f'<div class="pr-card"><h4>{e(label)}</h4><p class="pr-sub">{e(sizes.get(col, ""))}</p><ul class="pr-lines">{lines}</ul><a class="btn btn-pink pr-btn" rel="nofollow" href="{go}">Order {e(label.lower())}</a></div>'
        else:
            per = ' <small>per emote</small>' if s.get('qty') else ''
            cards = ''.join(f'<div class="pr-card"><h4>{e(p[0])}</h4><p class="pr-price">{money(p[1])}{per}</p><p class="pr-sub">{e(p[2])}</p><a class="btn btn-ghost pr-btn" rel="nofollow" href="{go}">Order</a></div>' for p in s['packages'])
        blocks.append(f'''    <div class="pr-svc" id="{slug(n)}">
      <div class="pr-head">{thumb(n)}<div><h3>{e(n)}</h3><p>{e(about)}</p><p class="pr-meta">From <b>{money(s["from"])}</b> + 13% tax · about {e(s["eta"])} {more}</p></div></div>
      <div class="pr-cards">{cards}</div>
      {addon_chips(n)}
    </div>''')
    jump = ''.join(f'<a class="wf" href="#{slug(n)}">{e(n)} <b>{money(SERVICES[n]["from"])}</b></a>' for n in order)
    steps = ''.join(f'<li><b>{i}</b><span><strong>{t}</strong>{d}</span></li>' for i, (t, d) in enumerate([
        ('Pick a service', 'Model, PNGTuber, emotes, banner and more.'),
        ('Choose size and option', 'The card shows the price for each choice.'),
        ('Add extras if you like', 'Expressions, outfits, commercial rights and so on.'),
        ('Pay your way', '13% tax is added. Pay in full, 50/50 or in 3 parts (orders above $150).')], 1))
    body = f'''  <section class="wrap phero" style="grid-template-columns:1fr">
    <div>
      <p class="eyebrow">Prices in USD</p>
      <h1 class="serif">VTuber Commission Prices</h1>
      <p class="lead">Every service and its price on one page. These are the same prices as in the order form, and your final total is shown before you send it.</p>
      <ol class="pr-steps">{steps}</ol>
    </div>
  </section>

  <section class="sec" id="prices"><div class="wrap">
    <h2>Price list</h2>
    <nav class="wfilters pr-jump" aria-label="Jump to a service">{jump}</nav>
{chr(10).join(blocks)}
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Payment and rules</h2>
    <div class="grid">
      <div class="box"><h3>How you pay</h3><p>After you send the order form, I email you an invoice (PDF). {e(PAY)}</p></div>
      <div class="box"><h3>Custom requests</h3><p>Have an idea that isn't listed? With a <a rel="nofollow" href="/?order=Custom%20Inquiry">custom inquiry</a> you name your price; 13% tax is added on the invoice and it's paid upfront.</p></div>
      <div class="box"><h3>Rush and complex designs</h3><p>Rush delivery is +25%. Very complex designs (for example wings or many accessories) may cost a bit more; the final price is always on your invoice before you pay.</p></div>
      <div class="box"><h3>Revisions</h3><p>Unlimited small revisions during the sketch. Up to 2 minor revisions after coloring; major changes after approval may have extra fees.</p></div>
      <div class="box"><h3>Refunds</h3><p>Full refund before work starts. After the sketch, refunds are based on completed work. No refund after final files are delivered.</p></div>
      <div class="box"><h3>Usage rights</h3><p>Personal use, streaming, monetized content and socials are included. Merch / commercial rights are a $30 add-on for any service.</p></div>
    </div>
  </div></section>
{related("/vtuber-pricing/")}
{cta("Found what you need?", "Send the order form and I'll email your invoice.", "", "Start a project")}'''
    faq = [
        ('How much does a custom VTuber model cost?', f'Art only starts at {money(vp["Bust · Art only"])} (bust); art + rig at {money(vp["Bust · Art + Rig"])}. A full-body model with rigging is {money(vp["Full body · Art + Rig"])}. See <a href="/custom-vtuber-model/">custom VTuber models</a>.'),
        ('Can I pay in installments?', 'Yes: 50/50 (half upfront, half before final files), or 3 installments for orders above $150.'),
        ('Which currency do you use?', 'All prices are in US dollars (USD), before 13% tax, which is added on the invoice. You pay with a one-click PayPal link (card or PayPal balance).'),
        ('Why do some prices say "from"?', 'It is the starting price of the smallest package. The final price depends on the options and add-ons you choose, and is confirmed on your invoice.'),
        ('What does a VTuber debut package include?', '; '.join(f'{e(p[0])} ({money(p[1])}): {e(p[2])}' for p in SERVICES["VTuber Packages"]["packages"]) + '.'),
    ]
    desc = 'Prices for custom VTuber models, Live2D rigging, PNGTubers, emotes, overlays, banners and logos in USD, with add-ons, timelines and payment plans.'
    offers_ld = {"@context": "https://schema.org", "@type": "OfferCatalog", "name": "KeikoArts VTuber commission prices", "url": SITE + 'vtuber-pricing/',
                 "itemListElement": [{"@type": "Offer", "price": str(SERVICES[n]["from"]), "priceCurrency": "USD",
                                      "itemOffered": {"@type": "Service", "name": n, "provider": {"@type": "ProfessionalService", "name": "KeikoArts", "url": SITE}}} for n in order]}
    return page('vtuber-pricing', 'VTuber Commission Prices & Packages | KeikoArtist', desc, 'VTuber Commission Prices', 'VTuber Pricing',
                body, faq, 'vtuber-debut-package-keikomi', '', offers_ld)

# ---------------------------------------------------------------- 404
def not_found():
    out = page('404', 'Page not found | KeikoArtist', 'This page does not exist.', 'Page not found', 'Page not found',
               '''  <section class="wrap phero" style="grid-template-columns:1fr">
    <div><h1 class="serif">Page not found</h1><p class="lead">This page doesn't exist (anymore). Try one of these:</p>
    <div class="btns"><a class="btn btn-pink" href="/">Home</a><a class="btn btn-ghost" href="/custom-vtuber-model/">Custom VTuber models</a><a class="btn btn-ghost" href="/vtuber-pricing/">Prices</a></div></div>
  </section>''', [('How do I order?', 'Go to the <a href="/">homepage</a> and click "Start a Project".')], 'custom-vtuber-model-witch')
    out = out.replace('<meta name="robots" content="index, follow, max-image-preview:large">', '<meta name="robots" content="noindex">')
    out = re.sub(r'<link rel="canonical"[^>]*>\n', '', out)
    out = re.sub(r'<script type="application/ld\+json">.*?</script>\n', '', out)
    return out


# ---------------------------------------------------------------- guides (long-tail search pages)
GUIDES = [('/vtuber-model-cost/', 'How much does a VTuber model cost?', 'Prices by size, extras and packages'),
          ('/how-to-commission-a-vtuber-model/', 'How to commission a VTuber model', 'Step by step, from idea to stream'),
          ('/live2d-vs-pngtuber/', 'Live2D vs PNGTuber', 'Which avatar fits you and your budget'),
          ('/how-to-become-a-vtuber/', 'How to become a VTuber', 'What you need to start, step by step')]

def guides_block(exclude):
    cards = ''.join(f'<a href="{u}"><b>{t}</b><span>{d}</span></a>' for u, t, d in GUIDES if u != exclude)
    return ('  <section class="sec"><div class="wrap">\n    <h2>VTuber commission guides</h2>\n'
            f'    <div class="related">{cards}</div>\n  </div></section>')

def article_ld(path, title, desc, image):
    return {"@context": "https://schema.org", "@type": "Article", "headline": title, "description": desc,
            "url": SITE + path + '/', "inLanguage": "en", "dateModified": TODAY,
            "author": {"@type": "Person", "name": "Keiko", "url": SITE},
            "publisher": {"@type": "Organization", "name": "KeikoArts", "logo": {"@type": "ImageObject", "url": SITE + "images/keikoarts-logo.webp"}},
            "image": SITE + "images/" + image + ".webp"}

def guide_cost():
    pk = SERVICES['VTuber Packages']['packages']; P = SERVICES['PNGTuber']; C = SERVICES['Chibi VTuber']
    row = lambda name: ''.join(f'<td class="num">{money(vp[s + " · " + name])}</td>' for s in ('Bust', 'Half body', 'Full body'))
    detail = e(DETAILS["VTuber"]["notes"]).split(". ", 1)[-1]
    addons = "".join(f"<li>{e(a[0])}: <b>+{money(a[1])}</b></li>" for a in V["addons"])
    pkgs = "".join(f'<div class="box"><h3>{e(n)}</h3><p>{e(d)}</p><p class="price">{money(pr)}</p></div>' for n, pr, d in pk)
    body = f'''  <section class="wrap phero">
    <div>
      <p class="eyebrow">VTuber commission guide</p>
      <h1 class="serif">How Much Does a Custom VTuber Model Cost?</h1>
      <p class="lead">At KeikoArts a custom Live2D VTuber model costs {money(vp["Bust · Art + Rig"])} to {money(vp["Full body · Art + Rig"])} with rigging, or {money(vp["Bust · Art only"])} to {money(vp["Full body · Art only"])} for the art alone. This page shows what changes the price, what the extras cost and how to pay.</p>
      <div class="btns"><a class="btn btn-pink arrow" rel="nofollow" href="/?order=VTuber">Get your exact price</a><a class="btn btn-ghost" href="/vtuber-pricing/">All prices</a></div>
    </div>
    <figure>{img("custom-vtuber-model-dragon", eager=True)}</figure>
  </section>

  <section class="sec"><div class="wrap">
    <h2>VTuber model prices at a glance</h2>
    <div class="tblwrap"><table class="tbl"><thead><tr><th>Option</th><th class="num">Bust</th><th class="num">Half body</th><th class="num">Full body</th></tr></thead><tbody>
      <tr><td>Art only (layered PSD, ready to rig)</td>{row("Art only")}</tr>
      <tr><td>Art + Rig (Live2D model + VTube Studio file)</td>{row("Art + Rig")}</tr>
      <tr><td>Rig only (you send the PSD)</td>{row("Rig only")}</tr>
    </tbody></table></div>
    <p class="note">Prices in USD. 13% tax is added on every invoice. The final price is confirmed on your invoice before you pay.</p>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>What changes the price</h2>
    <div class="grid">
      <div class="box"><h3>Size</h3><p>Bust shows your character to the chest, half body to the waist, full body from head to toe. More of the character means more parts to draw and rig.</p></div>
      <div class="box"><h3>Art, rig or both</h3><p>Art only is the drawing split into layers. Rigging makes it move in VTube Studio. Art + Rig gives you a model that is ready to stream.</p></div>
      <div class="box"><h3>Design details</h3><p>{detail}</p></div>
    </div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Extras and add-ons</h2>
    <div class="grid two">
      <div class="box"><h3>Model add-ons</h3><ul>{addons}</ul></div>
      <div class="box"><h3>Other costs to plan for</h3><ul><li>13% tax on every invoice</li><li>Rush delivery: +25%</li><li>Merch / commercial rights: +{money(vadd["Commercial / merch rights"])} (streaming and monetized videos are already included)</li></ul></div>
    </div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Debut packages</h2>
    <p>If you are preparing a debut, a package bundles the model with the other assets you need, in one matching style.</p>
    <div class="grid">{pkgs}</div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Smaller budget?</h2>
    <div class="grid two">
      <div class="box"><h3>PNGTuber</h3><p>An idle and a talking image with blinking, no rigging. From {money(P["from"])}, about {e(P["eta"])}. Read <a href="/live2d-vs-pngtuber/">Live2D vs PNGTuber</a>.</p></div>
      <div class="box"><h3>Chibi VTuber</h3><p>A cute full-body chibi with 3 expressions, ready to rig. From {money(C["from"])}, about {e(C["eta"])}.</p></div>
    </div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>How payment works</h2>
    <p>{e(PAY)} Nothing is charged until you pay the invoice.</p>
  </div></section>
{guides_block("/vtuber-model-cost/")}
{cta("Want your exact price?", "Send your idea with the order form and get your invoice by email, usually within 6 hours (WIB, GMT+7).", "VTuber", "Get your price")}'''
    faq = [
        ('How much is a cheap VTuber model?', f'The lowest-cost option here is a PNGTuber from {money(P["from"])}. For a Live2D model, a bust with art and rigging starts at {money(vp["Bust · Art + Rig"])}.'),
        ('How much does a full-body Live2D VTuber model cost?', f'{money(vp["Full body · Art only"])} for the art only, or {money(vp["Full body · Art + Rig"])} with rigging and a VTube Studio file, plus 13% tax.'),
        ('Is rigging included in the price?', f'Only in Art + Rig. Art only gives you a layered PSD that is ready to rig. Rig only for your own art starts at {money(vp["Bust · Rig only"])}.'),
        ('Can I pay in parts?', 'Yes: 50/50 (half upfront, half before final files), or 3 installments for orders above $150.'),
        ('Are there hidden costs?', f'No. The order form and your invoice show the total: the package, any add-ons you choose, 13% tax, and optional rush (+25%) or commercial rights (+{money(vadd["Commercial / merch rights"])}).'),
    ]
    desc = f'Custom VTuber model prices: Live2D art + rig from {money(vp["Bust · Art + Rig"])} to {money(vp["Full body · Art + Rig"])}, art only from {money(vp["Bust · Art only"])}. Sizes, add-ons, debut packages and payment options.'
    title = 'How Much Does a Custom VTuber Model Cost?'
    return page('vtuber-model-cost', title + ' | KeikoArtist', desc, title, 'VTuber Model Cost', body, faq,
                'custom-vtuber-model-dragon', 'VTuber', article_ld('vtuber-model-cost', title, desc, 'custom-vtuber-model-dragon'),
                eyebrow='KeikoArts · VTuber commission guides')

def guide_howto():
    body = f'''  <section class="wrap phero">
    <div>
      <p class="eyebrow">VTuber commission guide</p>
      <h1 class="serif">How to Commission a Custom VTuber Model</h1>
      <p class="lead">Commissioning your first VTuber model is easier than it looks. Here is the whole process at KeikoArts, from your first idea to going live in VTube Studio, with what to prepare at each step.</p>
      <div class="btns"><a class="btn btn-pink arrow" rel="nofollow" href="/?order=VTuber">Start your commission</a><a class="btn btn-ghost" href="/vtuber-model-cost/">See the costs</a></div>
    </div>
    <figure>{img("custom-vtuber-model-witch", eager=True)}</figure>
  </section>

  <section class="sec"><div class="wrap">
    <h2>Step by step</h2>
    <ol class="steps">
      <li><b>Decide what you need</b><span>Art only (a layered PSD), Art + Rig (a model ready to stream) or Rig only (for art you already have). Then pick bust, half body or full body.</span></li>
      <li><b>Prepare your character</b><span>A character sheet helps, but it is not required. A description, a few reference pictures and the mood you want are enough to start.</span></li>
      <li><b>Send the order form</b><span>Choose the options and extras, describe your character and attach your references. The total updates as you choose.</span></li>
      <li><b>Get your invoice</b><span>I review your request and email an invoice (PDF), usually within 6 hours (WIB, GMT+7). Your slot is secured once payment is received.</span></li>
      <li><b>Sketch and revisions</b><span>Small revisions are unlimited during the sketch, so the design can settle. Up to 2 minor revisions after coloring.</span></li>
      <li><b>Lineart, coloring and rigging</b><span>Progress updates at every stage. For Art + Rig I set up head turns, blinking, lip-sync and hair and clothing physics.</span></li>
      <li><b>Go live</b><span>You receive your files and a VTube Studio model. Every commission takes 3 weeks at most; rush delivery (+25%) is available.</span></li>
    </ol>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>What to send with your order</h2>
    <div class="grid two">
      <div class="box"><h3>Helpful to include</h3><ul><li>A front view of your character (a sketch, sheet or picrew is fine)</li><li>Colors you want and colors to avoid</li><li>Personality and stream style</li><li>Outfit details and accessories</li></ul></div>
      <div class="box"><h3>Good to know</h3><ul><li>Extra expressions and toggles are +{money(vadd["Extra expression / toggle"])} each</li><li>Extra outfits or hairstyles can be added later</li><li>Questions first? Ask on <a href="https://discord.gg/FbgWxMPjf" target="_blank" rel="noopener">Discord</a></li></ul></div>
    </div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Payment and rights</h2>
    <p>{e(PAY)}</p>
    <p>Streaming, monetized videos and social media use are included. Merch and other commercial rights are +{money(vadd["Commercial / merch rights"])}. Read the full <a href="/#tos">Terms of Service</a>.</p>
  </div></section>
{guides_block("/how-to-commission-a-vtuber-model/")}
{cta("Want to start?", "Send me your idea and I'll email your invoice. You only pay after you've checked it.", "VTuber", "Start your commission")}'''
    faq = [
        ('Do I need a finished character design?', 'No. A description and a few references are enough. The design is worked out together during the sketch stage.'),
        ('How long does a VTuber commission take?', f'VTuber models take about {e(V["eta"])}, and every commission takes 3 weeks at most. Rush delivery (+25%) is available.'),
        ('When do I pay?', 'After you send the order form you get an invoice. You can pay in full, 50/50, or in 3 installments for orders above $150. Your slot is secured once payment is received.'),
        ('Can I ask for changes?', 'Yes. Small revisions are unlimited during the sketch. After coloring, up to 2 minor revisions are included; major changes after approval may have extra fees.'),
        ('What software do I need to stream?', 'VTube Studio. It tracks your face with a webcam or an iPhone. Art + Rig orders include a VTube Studio file, ready to stream.'),
    ]
    desc = 'How to commission a custom VTuber model step by step: what to prepare, how ordering, payment and revisions work, and how long it takes until you go live.'
    title = 'How to Commission a Custom VTuber Model'
    return page('how-to-commission-a-vtuber-model', 'How to Commission a VTuber Model (Step by Step) | KeikoArtist', desc, title, 'How to Commission', body, faq,
                'custom-vtuber-model-witch', 'VTuber', article_ld('how-to-commission-a-vtuber-model', title, desc, 'custom-vtuber-model-witch'),
                eyebrow='KeikoArts · VTuber commission guides')

def guide_compare():
    P = SERVICES['PNGTuber']
    body = f'''  <section class="wrap phero">
    <div>
      <p class="eyebrow">VTuber commission guide</p>
      <h1 class="serif">Live2D vs PNGTuber: Which One Should You Get?</h1>
      <p class="lead">Both let you stream as your own character. A Live2D model follows your face; a PNGTuber switches images when you talk. Here is how they compare in price, time, setup and feel.</p>
      <div class="btns"><a class="btn btn-pink arrow" href="/custom-vtuber-model/">Live2D models</a><a class="btn btn-ghost" href="/custom-pngtuber-model/">PNGTuber models</a></div>
    </div>
    <figure>{img("custom-pngtuber-model-cat-mask", eager=True)}</figure>
  </section>

  <section class="sec"><div class="wrap">
    <h2>Side by side</h2>
    <div class="tblwrap"><table class="tbl"><thead><tr><th></th><th>Live2D VTuber</th><th>PNGTuber</th></tr></thead><tbody>
      <tr><td>Price</td><td>From {money(vp["Bust · Art + Rig"])} with rigging</td><td>From {money(P["from"])}</td></tr>
      <tr><td>Time</td><td>About {e(V["eta"])}</td><td>About {e(P["eta"])}</td></tr>
      <tr><td>Movement</td><td>Head turns, blinking, lip-sync, hair and clothing physics</td><td>Idle and talking images, blinking</td></tr>
      <tr><td>Tracking</td><td>Face tracking with a webcam or iPhone</td><td>Reacts to your voice</td></tr>
      <tr><td>Software</td><td>VTube Studio</td><td>PNGTuber Plus or Veadotube</td></tr>
      <tr><td>Files</td><td>Live2D model + VTube Studio file</td><td>Transparent PNGs</td></tr>
    </tbody></table></div>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Which one fits you?</h2>
    <div class="grid two">
      <div class="box"><h3>Pick a PNGTuber if…</h3><ul><li>You want to start streaming soon on a small budget</li><li>You mostly chat, play games or make videos</li><li>You want something simple to set up</li></ul><p class="price">from {money(P["from"])}</p></div>
      <div class="box"><h3>Pick Live2D if…</h3><ul><li>You want your character to move with you</li><li>Expressions and reactions matter for your content</li><li>You are planning a debut</li></ul><p class="price">from {money(vp["Bust · Art + Rig"])}</p></div>
    </div>
    <p class="note">Many streamers start as a PNGTuber and move to Live2D later. Your PNGTuber design can be the base for a future Live2D model.</p>
  </div></section>
{guides_block("/live2d-vs-pngtuber/")}
{cta("Not sure yet?", "Tell me about your stream on Discord or in the order form, and I'll suggest the best fit.", "", "Start a project")}'''
    faq = [
        ('Is a PNGTuber cheaper than a Live2D VTuber?', f'Yes. A PNGTuber starts at {money(P["from"])}; a Live2D model with rigging starts at {money(vp["Bust · Art + Rig"])}.'),
        ('Can a PNGTuber become a Live2D model later?', 'Yes. The same character design can be redrawn in layers and rigged for Live2D when you are ready.'),
        ('Do I need a webcam?', 'For Live2D, a webcam or an iPhone is used for face tracking in VTube Studio. A PNGTuber only needs your microphone.'),
        ('Which is better for a debut?', 'Most debuts use a Live2D model because it moves with you. A debut package bundles the model with emotes, a background and an overlay.'),
    ]
    desc = f'Live2D VTuber vs PNGTuber compared: price (from {money(vp["Bust · Art + Rig"])} vs from {money(P["from"])}), time, movement, tracking and software, and which one fits your stream.'
    title = 'Live2D vs PNGTuber: Which One Should You Get?'
    return page('live2d-vs-pngtuber', title + ' | KeikoArtist', desc, 'Live2D vs PNGTuber', 'Live2D vs PNGTuber', body, faq,
                'custom-pngtuber-model-cat-mask', 'PNGTuber', article_ld('live2d-vs-pngtuber', title, desc, 'custom-pngtuber-model-cat-mask'),
                eyebrow='KeikoArts · VTuber commission guides')

def guide_start():
    P = SERVICES['PNGTuber']; K = SERVICES['VTuber Packages']['packages']
    body = f"""  <section class="wrap phero">
    <div>
      <p class="eyebrow">VTuber commission guide</p>
      <h1 class="serif">How to Become a VTuber: What You Need to Start</h1>
      <p class="lead">A VTuber streams or makes videos as an animated character instead of on camera. You need four things: a character, a model, tracking software and a way to stream. Here is each step, with real prices.</p>
      <div class="btns"><a class="btn btn-pink arrow" rel="nofollow" href="/?order=VTuber">Start a project</a><a class="btn btn-ghost" href="/vtuber-pricing/">See prices</a></div>
    </div>
    <figure>{img(GALLERY["VTuber"][0], eager=True)}</figure>
  </section>

  <section class="sec"><div class="wrap">
    <h2>The 5 steps</h2>
    <ol class="steps">
      <li><b>Create your character.</b> Name, personality, colors and outfit. A few reference images or a short description is enough; I design the rest with you.</li>
      <li><b>Choose your model type.</b> A <a href="/custom-pngtuber-model/">PNGTuber</a> (from {money(P["from"])}) switches images when you talk. A <a href="/custom-vtuber-model/">Live2D model</a> (art + rig from {money(vp["Bust · Art + Rig"])}) follows your face. <a href="/live2d-vs-pngtuber/">Compare them</a>.</li>
      <li><b>Get the model made.</b> Every commission is done within 3 weeks, with updates at every stage. Live2D models come with a VTube Studio file.</li>
      <li><b>Set up tracking.</b> VTube Studio tracks your face with a webcam or an iPhone. A PNGTuber only needs your microphone (PNGTuber Plus or Veadotube).</li>
      <li><b>Start streaming.</b> Add the model to OBS or Streamlabs and go live on Twitch, YouTube or TikTok. Emotes, a background and an overlay make your channel look complete.</li>
    </ol>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>What it costs</h2>
    <div class="grid">
      <div class="box"><h3>Start small</h3><p>PNGTuber from {money(P["from"])}. Good for starting soon on a small budget.</p></div>
      <div class="box"><h3>Live2D model</h3><p>Art + rig: bust {money(vp["Bust · Art + Rig"])}, half body {money(vp["Half body · Art + Rig"])}, full body {money(vp["Full body · Art + Rig"])}.</p></div>
      <div class="box"><h3>Full debut</h3><p>{"; ".join(f"{e(p[0])} {money(p[1])}" for p in K)}: model, rig and stream assets in one style.</p></div>
    </div>
    <p class="note">Prices in USD; 13% tax is added on the invoice. See <a href="/vtuber-model-cost/">how much a VTuber model costs</a> for every option.</p>
  </div></section>
{guides_block("/how-to-become-a-vtuber/")}
{cta("Ready to make your character?", "Tell me your idea in the order form, or ask first on Discord.", "", "Start a project")}"""
    faq = [
        ('What do I need to become a VTuber?', 'A character design, a model (PNGTuber or Live2D), tracking software such as VTube Studio, and streaming software such as OBS. A webcam or iPhone is used for Live2D face tracking.'),
        ('How much does it cost to become a VTuber?', f'You can start with a PNGTuber from {money(P["from"])}. A Live2D model with rigging starts at {money(vp["Bust · Art + Rig"])} for a bust. 13% tax is added.'),
        ('Do I need to draw my own model?', 'No. Most VTubers commission an artist. Send your idea or references and the artist designs, draws and rigs the model.'),
        ('How long does it take to get a VTuber model?', 'Every commission at KeikoArts is done within 3 weeks, with updates at every stage.'),
        ('Can I use a VTuber model on YouTube and TikTok?', 'Yes. Streaming, monetized videos and social media are included. Merch / commercial rights are a $30 add-on.'),
    ]
    desc = f'How to become a VTuber: create a character, choose a PNGTuber (from {money(P["from"])}) or Live2D model (from {money(vp["Bust · Art + Rig"])}), set up VTube Studio and start streaming.'
    title = 'How to Become a VTuber: What You Need to Start'
    return page('how-to-become-a-vtuber', title + ' | KeikoArtist', desc, 'How to Become a VTuber', 'How to become a VTuber', body, faq,
                GALLERY["VTuber"][0], 'VTuber', article_ld('how-to-become-a-vtuber', title, desc, GALLERY["VTuber"][0]),
                eyebrow='KeikoArts · VTuber commission guides')

PAGES = {'custom-vtuber-model': custom_vtuber, 'live2d-rigging': rigging, 'custom-pngtuber-model': pngtuber, 'custom-twitch-emotes': emotes,
         'vtuber-portfolio': portfolio, 'vtuber-pricing': pricing,
         'vtuber-model-cost': guide_cost, 'how-to-commission-a-vtuber-model': guide_howto, 'live2d-vs-pngtuber': guide_compare, 'how-to-become-a-vtuber': guide_start}
for slug_, fn in PAGES.items():
    os.makedirs(os.path.join(ROOT, slug_), exist_ok=True)
    open(os.path.join(ROOT, slug_, 'index.html'), 'w', encoding='utf-8').write(fn())
open(os.path.join(ROOT, '404.html'), 'w', encoding='utf-8').write(not_found())
urls = [('', '1.0')] + [(s + '/', '0.8') for s in PAGES]
def page_images(u):   # artwork shown on a page, for the image sitemap (Google Images)
    src = open(os.path.join(ROOT, u, 'index.html') if u else os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    names = re.findall(r'images/([a-z0-9-]+)\.webp', src)
    if not u: names += [n for v in GALLERY.values() for n in v]
    out = []
    for n in names:
        if n.startswith(('keikoarts-logo', 'keikoarts-team', 'vtuber-avatar')) or n in out: continue
        if os.path.exists(os.path.join(ROOT, 'images', n + '.webp')): out.append(n)
    return out
def sm_url(u, p):
    ims = ''.join(f'<image:image><image:loc>{SITE}images/{n}.webp</image:loc></image:image>' for n in page_images(u))
    vids = ''.join(f'<video:video><video:thumbnail_loc>{SITE}images/{k}-poster.webp</video:thumbnail_loc><video:title>{e(n)}</video:title><video:description>{e(d)}</video:description><video:content_loc>{SITE}images/{k}.mp4</video:content_loc><video:duration>{int(dur[2:-1])}</video:duration></video:video>' for k, n, d, dur, dt in VIDEOS) if u == 'live2d-rigging/' else ''
    return f'  <url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod><priority>{p}</priority>{ims}{vids}</url>\n'
sm = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
      'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" xmlns:video="http://www.google.com/schemas/sitemap-video/1.1">\n' + ''.join(sm_url(u, p) for u, p in urls) + '</urlset>\n')
open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(sm)
# llms.txt: a plain summary for AI assistants (ChatGPT, Claude, Perplexity...) built from the same data as the site
def _pk(n): return '; '.join(f'{p[0]} {money(p[1])}' + (' each' if SERVICES[n].get('qty') else '') for p in SERVICES[n]['packages'])
llms = f"""# KeikoArts (keikoartist.com)

> KeikoArts is Keiko's VTuber art and Live2D studio: original anime VTuber models drawn from scratch and rigged in Live2D, ready for VTube Studio, plus PNGTubers, emotes, banners, logos and stream assets. Style: cute meets gothic. 200+ commissions completed. Prices in USD; 13% tax is added on every invoice. Every commission is done within 3 weeks.

## How to order
- Order form with live total: {SITE}?order=VTuber (all services: {SITE}#services)
- Payment: PayPal (card or PayPal balance), in full, 50/50, or 3 parts for orders above $150
- Questions before ordering: Discord {'https://discord.gg/FbgWxMPjf'} or the live chat on the website (usually replies within 6 hours, WIB / GMT+7)
- Merch / commercial rights: +$30 for any service. Rush delivery: +25%.

## Prices
- Live2D VTuber model: {_pk('VTuber')}
- VTuber model add-ons: {'; '.join(f"{a[0]} +{money(a[1])}" + (' each' if 'toggle' in a[0].lower() else '') for a in SERVICES['VTuber']['addons'])}
- VTuber debut packages: {_pk('VTuber Packages')}
- PNGTuber: {_pk('PNGTuber')}
- Twitch / Discord emotes: {_pk('Emotes')}
- Chibi VTuber: {_pk('Chibi VTuber')}
- VTuber pet: {_pk('VTuber Pet')}
- Others (from): {', '.join(f"{n} {money(SERVICES[n]['from'])}" for n in ['Custom PFP', 'Banner', 'VTuber Logo', 'Stream Overlay', 'Background'])}

## Pages
- [Custom VTuber model]({SITE}custom-vtuber-model/): what is included, sizes, rigging, timeline
- [Live2D rigging]({SITE}live2d-rigging/): rig only for your own art, VTube Studio file, showcase videos
- [Custom PNGTuber]({SITE}custom-pngtuber-model/)
- [Custom Twitch emotes]({SITE}custom-twitch-emotes/)
- [Portfolio]({SITE}vtuber-portfolio/)
- [All prices]({SITE}vtuber-pricing/)
- [How much does a VTuber model cost?]({SITE}vtuber-model-cost/)
- [How to commission a VTuber model]({SITE}how-to-commission-a-vtuber-model/)
- [Live2D vs PNGTuber]({SITE}live2d-vs-pngtuber/)
- [How to become a VTuber]({SITE}how-to-become-a-vtuber/)
"""
open(os.path.join(ROOT, 'llms.txt'), 'w', encoding='utf-8').write(llms)
# prices for the chat's automatic reply (chat-api.php reads this; same data as the order form)
open(os.path.join(ROOT, 'prices.json'), 'w', encoding='utf-8').write(json.dumps({n: {'from': s['from'], 'eta': s.get('eta', ''), 'qty': bool(s.get('qty')), 'packages': s['packages'], 'addons': s['addons']} for n, s in SERVICES.items()}, ensure_ascii=False, indent=1))
print('built', ', '.join(PAGES), '+ 404.html + sitemap.xml + prices.json + llms.txt')
