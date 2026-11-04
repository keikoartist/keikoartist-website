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
    'vtuber-kitsune-gown': 'Full-body VTuber model art of a fox-eared girl in a pink and black layered gown with gold armor details',
    'vtuber-witch': 'Full-body VTuber model art of a pink-haired witch in a purple outfit holding a pink flame',
    'vtuber-maid': 'Full-body VTuber model art of a pink-haired maid with cat ears holding playing cards',
    'vtuber-rocker': 'Full-body VTuber model art of a silver-haired rocker girl in a black jacket with a guitar case',
    'vtuber-dragon': 'Full-body VTuber model art of a dragon girl with horns in a pink and black frilled dress',
    'pkg-keikomi': 'VTuber debut package sheet with full-body model, rigging, logo, eye banner, expressions and PSD files',
    'overlay-keikomi': 'Stream overlay set with Starting Soon, Be Right Back and Ending Soon screens in purple and pink',
    'bg-stream-room': 'Night-time streamer bedroom background with gaming chair, desk and window',
    'chibi-witch': 'Full-body chibi VTuber art of a pink-haired witch in a black and pink outfit',
    'emotes-witch': 'Two Twitch emotes of a pink-haired witch: blushing and surprised',
    'emote-witch-1': 'Twitch emote of a pink-haired witch sticking out her tongue',
    'eye-banner-blue': 'Eye banner of glowing blue eyes framed by purple hair',
    'eye-banner-silver-animated': 'Animated eye banner of silver-haired character with glasses',
    'mouth-banner': 'Mouth banner of a smiling character with fangs and purple nails',
    'eye-banner-fire': 'Eye banner of orange eyes surrounded by flames',
    'eye-banner-sakura': 'Eye banner of pink eyes with round glasses and cherry blossoms',
    'mascot-anglercat': 'VTuber pet: fluffy blue cat sitting on a glowing anglerfish',
    'mascot-pet': 'VTuber pet: green leaf cat with flower collar',
    'mascot-tiger': 'VTuber pet: orange tiger cub with a red crest',
    'mascot-snowleopard': 'VTuber pet: lavender snow leopard with purple flame tail',
    'mascot-peach': 'VTuber pet: peach creature with leaf hat and green eyes',
    'mascot-bear': 'VTuber pet: brown teddy bear with a top hat and green sash',
    'logo-mosswing': 'Custom VTuber logo "Mosswing" in mossy green lettering with leaves',
    'pngtuber-catmask': 'PNGTuber model of a girl wearing a black cat helmet with glowing eyes',
    'pngtuber-violet': 'PNGTuber model of a purple-haired woman in a corset dress sitting on a suitcase',
    'pfp-wolf': 'Profile picture of a silver-haired wolf girl in a red off-shoulder dress',
    'pfp-glasses': 'Profile picture of a long-haired man with glasses',
    'pfp-leaf': 'Profile picture of a green-haired character with leaf collar and antlers',
    'illustration-calico': 'Illustration of a fluffy calico cat sitting in a flower meadow',
    'illustration-tabby': 'Illustration of a tabby kitten with mushrooms in a meadow',
    'illustration-couple-selfie': 'Couple illustration of two students taking a selfie on a phone',
    'illustration-cottage': 'Illustration of a woman reading with a cat in a cottage garden',
    'rigging-poster': 'Live2D rigging showcase of a white-haired VTuber model',
}
def img_size(name):
    with Image.open(os.path.join(ROOT, 'images', name + '.webp')) as im:
        return im.size
def img(name, cls='', eager=False, sizes='(max-width:560px) 50vw, 260px'):
    w, h = img_size(name)
    load = 'fetchpriority="high"' if eager else 'loading="lazy"'
    return f'<img src="/images/{name}.webp" alt="{e(ALT.get(name, name))}" width="{w}" height="{h}" {load} decoding="async"{(" class=" + chr(34) + cls + chr(34)) if cls else ""}>'
def fig(name, caption, wide=False):
    return f'<figure{" class=\"wide\"" if wide else ""}><a href="/images/{name}.webp">{img(name)}</a><figcaption>{e(caption)}</figcaption></figure>'
RIG_VIDEO = ('<figure class="wide"><video src="/images/rigging-showcase.mp4" poster="/images/rigging-poster.webp" controls muted loop playsinline preload="none" '
             'width="1280" height="720" aria-label="Live2D rigging showcase: head turns, blinking and hair physics"></video><figcaption>Live2D rigging showcase</figcaption></figure>')

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
FOOT = [('/custom-vtuber-model/', 'Custom VTuber Model'), ('/live2d-rigging/', 'Live2D Rigging'), ('/custom-pngtuber-model/', 'Custom PNGTuber Model'),
        ('/vtuber-pricing/', 'VTuber Pricing'), ('/vtuber-portfolio/', 'VTuber Portfolio'), ('/#faq', 'FAQ'), ('/#tos', 'Terms of Service')]

def page(path, title, desc, h1, crumb, body, faq, og_image, order='', extra_ld=None, eyebrow='KeikoArts · VTuber art & Live2D studio'):
    url = SITE + path.strip('/') + '/'
    nav = ''.join(f'<a href="{u}"{" aria-current=" + chr(34) + "page" + chr(34) if u == "/" + path + "/" else ""}>{t}</a>' for u, t in NAV)
    order_url = '/?order=' + order.replace(' ', '%20') if order else '/?order'
    faq_html = ''.join(f'<details><summary>{e(q)}</summary><p>{a}</p></details>' for q, a in faq)
    ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE},
              {"@type": "ListItem", "position": 2, "name": crumb, "item": url}]},
          {"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
              {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": re.sub(r'<[^>]+>', '', a)}} for q, a in faq]}]
    if extra_ld: ld.append(extra_ld)
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
<link rel="icon" href="/images/pfp.webp">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Poppins:wght@400;500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css?v={CSS_V}">
{lds}</head>
<body>
<header>
  <div class="wrap nav">
    <a href="/" class="logo"><img src="/images/pfp.webp" alt="KeikoArts logo" width="40" height="40"><span><b>KeikoArts</b><small>Illustration &amp; Live2D Studio</small></span></a>
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
      <a href="/" class="logo"><img src="/images/pfp.webp" alt="" width="40" height="40"><span><b>KeikoArts</b><small>Illustration &amp; Live2D Studio</small></span></a>
      <span><a href="https://discord.gg/FbgWxMPjf" target="_blank" rel="noopener"><b>Join Keiko's Discord</b></a></span>
    </div>
    <nav class="foot-links" aria-label="Services">{"".join(f'<a href="{u}">{t}</a>' for u, t in FOOT)}</nav>
    <div class="copy">© {datetime.date.today().year} KeikoArts · keikoartist.com</div>
  </div>
</footer>
<script>
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
PAY = 'Pay via Ko-fi in USD: in full, 50/50 (half upfront, half before final files), or in 3 installments for orders above $150.'

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
    <h2>Custom character design</h2>
    <p>You don't need a finished character sheet. Send a description, a few references or an existing design, and I work out the outfit, colors and details with you. Small changes are unlimited during the sketch stage, so the design can settle before coloring starts.</p>
    <div class="gallery">{"".join(fig(x, "VTuber model art") for x in vtubers)}</div>
    <p class="note">More work in the <a href="/vtuber-portfolio/">VTuber portfolio</a>.</p>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>How ordering works</h2>
    <ol class="steps">
      <li><b>Send the order form</b><span>Pick the size and option, describe your character and attach references.</span></li>
      <li><b>Get your invoice</b><span>I review your request and email you an invoice (PDF), usually within 6 hours. {e(PAY)}</span></li>
      <li><b>Sketch to rig</b><span>Sketch, lineart, coloring and rigging, with progress updates at every stage.</span></li>
      <li><b>Go live</b><span>You receive your files and VTube Studio model. Estimated time: {e(V["eta"])}; rush delivery (+25%) is available.</span></li>
    </ol>
  </div></section>

  <section class="sec"><div class="wrap">
    <h2>Usage rights</h2>
    <p>Personal use, streaming, monetized videos and social media are included. Merch and other commercial rights are an add-on (+{money(vadd["Commercial / merch rights"])}). The artist keeps the copyright; reselling, NFTs and AI training are not allowed. Read the full <a href="/#tos" style="color:var(--pink);font-weight:600">Terms of Service</a>.</p>
    <p>Preparing a debut? <a href="/vtuber-pricing/#vtuber-packages" style="color:var(--pink);font-weight:600">VTuber packages</a> start at {money(SERVICES["VTuber Packages"]["from"])} and bundle the model with emotes, a background, an overlay and more.</p>
  </div></section>
{related("/custom-vtuber-model/")}
{cta("Ready to design your VTuber?", "Send your idea and get your invoice by email. Nothing is charged until you pay it.", "VTuber", "Start your VTuber model")}'''
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
    <figure class="cover"><video src="/images/rigging-showcase.mp4" poster="/images/rigging-poster.webp" controls muted loop playsinline preload="none" width="1280" height="720" aria-label="Live2D rigging showcase: head turns, blinking and hair physics"></video></figure>
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
    <p class="addons">Add-ons: extra expression / toggle <b>+{money(vadd["Extra expression / toggle"])}</b> · VBridger <b>+{money(vadd["VBridger"])}</b> · extra outfit <b>+{money(vadd["Extra outfit"])}</b> · extra hairstyle <b>+{money(vadd["Extra hairstyle"])}</b></p>
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
    <div class="gallery">{RIG_VIDEO}{"".join(fig(x, "VTuber model art") for x in GALLERY["VTuber"][:3])}</div>
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
                body, faq, 'rigging-poster', 'VTuber', service_ld('Live2D rigging', SITE + 'live2d-rigging/', desc, vp["Bust · Rig only"]))

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
    <div class="gallery">{"".join(fig(x, "PNGTuber model") for x in imgs)}</div>
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
    seen = set(); secs = []
    toc = []
    for cid, title, key, link, linktext, cap in cats:
        names = ['overlay-keikomi', 'bg-stream-room'] if key is None else [n for n in GALLERY.get(key, []) if n != 'bg-stream-room' or key == 'Background']
        if key == 'VTuber Packages': names = ['pkg-keikomi']
        names = [n for n in names if n not in seen and os.path.exists(os.path.join(ROOT, 'images', n + '.webp'))]
        if not names and cid != 'vtuber-models': continue
        seen.update(names)
        wide = lambda n: Image.open(os.path.join(ROOT, 'images', n + '.webp')).size[0] > 1.4 * Image.open(os.path.join(ROOT, 'images', n + '.webp')).size[1]
        figs = (RIG_VIDEO if cid == 'vtuber-models' else '') + ''.join(fig(n, cap, wide(n)) for n in names)
        toc.append(f'<a href="#{cid}">{title}</a>')
        secs.append(f'''  <section class="sec" id="{cid}"><div class="wrap">
    <h2>{title}</h2>
    <div class="gallery">{figs}</div>
    <p class="note"><a href="{link}">{linktext} →</a></p>
  </div></section>''')
    body = f'''  <section class="wrap phero">
    <div>
      <p class="eyebrow">Portfolio</p>
      <h1 class="serif">VTuber &amp; Live2D Art Portfolio</h1>
      <p class="lead">VTuber models, Live2D rigging, PNGTubers, pets, emotes, banners, logos and illustrations made by Team Keiko. Every piece was drawn from scratch. Tap an image to see it full size.</p>
      <div class="btns"><a class="btn btn-pink arrow" rel="nofollow" href="/?order">Start a project</a><a class="btn btn-ghost" href="/vtuber-pricing/">See prices</a></div>
      <div class="facts">{"".join(f"<span>{t}</span>" for t in toc[:6])}</div>
    </div>
    <figure>{img(GALLERY["VTuber"][0], eager=True)}</figure>
  </section>
{chr(10).join(secs)}
{related("/vtuber-portfolio/")}
{cta("Want something like this?", "Tell me your idea and get your invoice by email.", "", "Start a project")}'''
    faq = [
        ('Who made these artworks?', 'Team Keiko: Keiko (artist), Zhopio (illustrator) and Tomy (rigger). Every piece here is original work, drawn from scratch.'),
        ('Can I order something in a similar style?', 'Yes. Mention the piece you like in the order form, and attach it as a reference if you want.'),
        ('Will my commission be shown in the portfolio?', 'Finished work may be shared on the portfolio and socials, unless you ask for a private or delayed reveal.'),
        ('How do I order?', 'Click "Start a project", choose a service, describe your idea and send the form. I email you your invoice (PDF), and you pay via Ko-fi.'),
    ]
    desc = 'VTuber models, Live2D rigging, PNGTubers, chibi models, pets, emotes, banners, logos and illustrations made by KeikoArts for streamers.'
    gallery_ld = {"@context": "https://schema.org", "@type": "CollectionPage", "name": "VTuber & Live2D Art Portfolio", "url": SITE + 'vtuber-portfolio/',
                  "about": {"@type": "ProfessionalService", "name": "KeikoArts", "url": SITE}}
    return page('vtuber-portfolio', 'VTuber Model & Live2D Art Portfolio | KeikoArtist', desc, 'VTuber & Live2D Art Portfolio', 'VTuber Portfolio',
                body, faq, GALLERY['VTuber'][0], '', gallery_ld)

# ---------------------------------------------------------------- 5. pricing
def pricing():
    slug = lambda n: re.sub(r'[^a-z0-9]+', '-', n.lower()).strip('-')
    pages = {'VTuber': '/custom-vtuber-model/', 'PNGTuber': '/custom-pngtuber-model/'}
    order = ['VTuber', 'VTuber Packages', 'PNGTuber', 'Chibi VTuber', 'VTuber Pet', 'Emotes', 'Custom PFP', 'Banner', 'VTuber Logo', 'Stream Overlay', 'Background']
    blocks = []
    for n in order:
        s = SERVICES[n]
        more = f' · <a href="{pages[n]}">Details</a>' if n in pages else ''
        blocks.append(f'''    <div class="svc" id="{slug(n)}">
      <h3>{e(n)}</h3>
      <p class="meta">From {money(s["from"])}{" per emote" if s.get("qty") else ""} · about {e(s["eta"])} · <a rel="nofollow" href="/?order={n.replace(" ", "%20")}">Order</a>{more}</p>
      {svc_table(n)}
      {addons_line(n)}
    </div>''')
    body = f'''  <section class="wrap phero" style="grid-template-columns:1fr">
    <div>
      <p class="eyebrow">Prices in USD</p>
      <h1 class="serif">VTuber Commission Prices</h1>
      <p class="lead">Current prices for every service: custom VTuber models, Live2D rigging, PNGTubers, emotes, banners, logos and stream assets. These are the same prices you see in the order form.</p>
      <div class="facts">{"".join(f'<span><a href="#{slug(n)}">{e(n)}</a> from <b>{money(SERVICES[n]["from"])}</b></span>' for n in order)}</div>
    </div>
  </section>

  <section class="sec"><div class="wrap">
    <h2>Price list</h2>
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
{cta("Found what you need?", "Send the order form and get your invoice by email.", "", "Start a project")}'''
    faq = [
        ('How much does a custom VTuber model cost?', f'Art only starts at {money(vp["Bust · Art only"])} (bust); art + rig at {money(vp["Bust · Art + Rig"])}. A full-body model with rigging is {money(vp["Full body · Art + Rig"])}. See <a href="/custom-vtuber-model/">custom VTuber models</a>.'),
        ('Can I pay in installments?', 'Yes: 50/50 (half upfront, half before final files), or 3 installments for orders above $150.'),
        ('Which currency do you use?', 'All prices are in US dollars (USD). You pay via Ko-fi.'),
        ('Why do some prices say "from"?', 'It is the starting price of the smallest package. The final price depends on the options and add-ons you choose, and is confirmed on your invoice.'),
        ('What does a VTuber debut package include?', '; '.join(f'{e(p[0])} ({money(p[1])}): {e(p[2])}' for p in SERVICES["VTuber Packages"]["packages"]) + '.'),
    ]
    desc = 'Prices for custom VTuber models, Live2D rigging, PNGTubers, emotes, overlays, banners and logos in USD, with add-ons, timelines and payment plans.'
    offers_ld = {"@context": "https://schema.org", "@type": "OfferCatalog", "name": "KeikoArts VTuber commission prices", "url": SITE + 'vtuber-pricing/',
                 "itemListElement": [{"@type": "Offer", "price": str(SERVICES[n]["from"]), "priceCurrency": "USD",
                                      "itemOffered": {"@type": "Service", "name": n, "provider": {"@type": "ProfessionalService", "name": "KeikoArts", "url": SITE}}} for n in order]}
    return page('vtuber-pricing', 'VTuber Commission Prices & Packages | KeikoArtist', desc, 'VTuber Commission Prices', 'VTuber Pricing',
                body, faq, 'pkg-keikomi', '', offers_ld)

# ---------------------------------------------------------------- 404
def not_found():
    out = page('404', 'Page not found | KeikoArtist', 'This page does not exist.', 'Page not found', 'Page not found',
               '''  <section class="wrap phero" style="grid-template-columns:1fr">
    <div><h1 class="serif">Page not found</h1><p class="lead">This page doesn't exist (anymore). Try one of these:</p>
    <div class="btns"><a class="btn btn-pink" href="/">Home</a><a class="btn btn-ghost" href="/custom-vtuber-model/">Custom VTuber models</a><a class="btn btn-ghost" href="/vtuber-pricing/">Prices</a></div></div>
  </section>''', [('How do I order?', 'Go to the <a href="/">homepage</a> and click "Start a Project".')], 'vtuber-witch')
    out = out.replace('<meta name="robots" content="index, follow, max-image-preview:large">', '<meta name="robots" content="noindex">')
    out = re.sub(r'<link rel="canonical"[^>]*>\n', '', out)
    out = re.sub(r'<script type="application/ld\+json">.*?</script>\n', '', out)
    return out

PAGES = {'custom-vtuber-model': custom_vtuber, 'live2d-rigging': rigging, 'custom-pngtuber-model': pngtuber,
         'vtuber-portfolio': portfolio, 'vtuber-pricing': pricing}
for slug_, fn in PAGES.items():
    os.makedirs(os.path.join(ROOT, slug_), exist_ok=True)
    open(os.path.join(ROOT, slug_, 'index.html'), 'w', encoding='utf-8').write(fn())
open(os.path.join(ROOT, '404.html'), 'w', encoding='utf-8').write(not_found())
urls = [('', '1.0')] + [(s + '/', '0.8') for s in PAGES]
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(
    f'  <url><loc>{SITE}{u}</loc><lastmod>{TODAY}</lastmod><priority>{p}</priority></url>\n' for u, p in urls) + '</urlset>\n'
open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8').write(sm)
print('built', ', '.join(PAGES), '+ 404.html + sitemap.xml')
