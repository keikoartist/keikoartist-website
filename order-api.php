<?php
/*
 * KeikoArts orders API.
 *  - POST ?a=submit (multipart form from the website): saves the order + reference files OUTSIDE the
 *    public folder, emails Keiko, sends the client a confirmation/invoice email, pings Discord, and
 *    returns the order ID + PayPal link so the page can show the invoice right away.
 *  - JSON POST {action:...} with the admin token (same login as the chat inbox): list/view/update orders.
 * Optional config in keikoarts-config.php (server only): 'discord_webhook', 'chat_admin_password'.
 */
declare(strict_types=1);
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');
header('Referrer-Policy: same-origin');
date_default_timezone_set('Asia/Jakarta');
ini_set('serialize_precision', '-1');

const OWNER_EMAIL    = 'keikoarts22@gmail.com';        // where new orders are emailed
const PAYPAL_EMAIL   = 'theresa.oktavia10@gmail.com';  // PayPal account that receives payments
const MAIL_FROM      = 'orders@keikoartist.com';
const TAX_RATE       = 0.13;                           // custom orders: tax added on the invoice
const MAX_FILES      = 5;
const MAX_FILE_BYTES = 12 * 1024 * 1024;
const MAIL_ATTACH_MAX = 15 * 1024 * 1024;              // bigger uploads stay in the admin inbox only
const DISCORD_USER   = 'https://discord.com/users/1053527069528707072';
const STATUSES       = ['new', 'paid', 'in_progress', 'done', 'cancelled'];

function jout(int $code, array $data = []): void {
  header('Content-Type: application/json; charset=utf-8'); http_response_code($code);
  echo json_encode($data + ['ok' => $code === 200], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); exit;
}
$HTML_MODE = !empty($_GET['html']);   // plain form post (browser without working JavaScript): answer with a page, not JSON
function page(string $title, string $body): void {
  header('Content-Type: text/html; charset=utf-8');
  echo '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>' . htmlspecialchars($title) . ' · KeikoArts</title>'
     . '<style>body{margin:0;font-family:Arial,sans-serif;background:#fff4f8;color:#7a2846}main{max-width:560px;margin:24px auto;background:#fff;border:1px solid #fbd3e0;border-radius:18px;padding:24px}h1{color:#f2628f;font-size:24px;margin:0 0 8px}table{width:100%;border-collapse:collapse;font-size:15px;margin:14px 0}td{padding:6px 0;border-bottom:1px solid #fde9f0}td:last-child{text-align:right}.tot td{font-weight:bold;border:0;padding-top:10px}.pp{display:block;text-align:center;background:#ffc439;color:#003087;font-weight:bold;padding:14px;border-radius:999px;text-decoration:none;margin:16px 0 8px}.muted{color:#a8607a;font-size:13px}a.back{color:#f2628f}</style></head><body><main>'
     . $body . '<p class="muted">Questions? <a class="back" href="https://discord.com/users/1053527069528707072">Message me on Discord</a> · <a class="back" href="/">Back to keikoartist.com</a></p></main></body></html>';
  exit;
}
function fail(int $code, string $msg): void {
  global $HTML_MODE;
  if ($HTML_MODE) { http_response_code($code); page('Order not sent', '<h1>Sorry, your order was not sent</h1><p>' . htmlspecialchars($msg) . '</p><p><a class="back" href="javascript:history.back()">← Go back and try again</a></p>'); }
  jout($code, ['error' => $msg]);
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') fail(405, 'POST only');
$hostHdr = strtolower($_SERVER['HTTP_HOST'] ?? '');
$host = preg_replace('/:\d+$/', '', $hostHdr);
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin && strtolower((string)parse_url($origin, PHP_URL_HOST)) !== $host) fail(403, 'bad origin');

$cfgFile = __DIR__ . '/keikoarts-config.php';
$cfg = is_file($cfgFile) ? (include $cfgFile) : [];
if (!is_array($cfg)) $cfg = [];
$SITE = preg_match('/^(localhost|127\.0\.0\.1)$/', $host) ? "http://$hostHdr/" : 'https://keikoartist.com/';

/* ---------- storage ---------- */
function data_dir(): string {
  $outside = dirname(__DIR__, 2) . '/keikoarts-data';
  if ((is_dir($outside) || @mkdir($outside, 0700, true)) && is_writable($outside)) return $outside;
  $inside = __DIR__ . '/chat-data';
  if (!is_dir($inside)) @mkdir($inside, 0700, true);
  if (!is_file("$inside/.htaccess")) @file_put_contents("$inside/.htaccess", "Require all denied\nDeny from all\n");
  if (!is_file("$inside/index.html")) @file_put_contents("$inside/index.html", '');
  return $inside;
}
function db(): PDO {
  static $pdo = null; if ($pdo) return $pdo;
  $pdo = new PDO('sqlite:' . data_dir() . '/orders.sqlite', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
  $pdo->exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=4000;');
  $pdo->exec('CREATE TABLE IF NOT EXISTS orders(
      id TEXT PRIMARY KEY, kind TEXT, status TEXT NOT NULL DEFAULT \'new\', name TEXT, email TEXT, discord TEXT,
      service TEXT, package TEXT, plan TEXT, price REAL, tax REAL, total REAL, due REAL,
      fields TEXT, files TEXT, mailed INTEGER DEFAULT 0, created INTEGER, updated INTEGER)');
  $pdo->exec('CREATE INDEX IF NOT EXISTS idx_orders_created ON orders(created)');
  $pdo->exec('CREATE TABLE IF NOT EXISTS hits(k TEXT, t INTEGER)');
  return $pdo;
}

/* ---------- helpers ---------- */
function clean(string $v, int $max): string {
  $v = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $v) ?? '';
  return mb_substr(trim($v), 0, $max);
}
function client_ip(): string { return $_SERVER['REMOTE_ADDR'] ?? '0'; }
function rate_limit(string $key, int $max, int $window): void {
  $db = db(); $now = time();
  $db->prepare('DELETE FROM hits WHERE t < ?')->execute([$now - 86400]);
  $k = hash('sha256', $key);
  $st = $db->prepare('SELECT COUNT(*) FROM hits WHERE k = ? AND t > ?'); $st->execute([$k, $now - $window]);
  if ((int)$st->fetchColumn() >= $max) fail(429, 'Too many orders from your connection. Please wait a little or message me on Discord.');
  $db->prepare('INSERT INTO hits(k,t) VALUES(?,?)')->execute([$k, $now]);
}
function money2(float $n): string { return '$' . number_format($n, 2); }
function h(string $s): string { return htmlspecialchars($s, ENT_QUOTES, 'UTF-8'); }
function no_links(string $s): string { return trim(preg_replace('~(https?://|www\.)\S*|\S+\.(com|net|org|io|me|ly|xyz|ru|cn)\b\S*~i', '', $s) ?? ''); }
function mime_of(string $ext): string {
  return ['jpg' => 'image/jpeg', 'jpeg' => 'image/jpeg', 'png' => 'image/png', 'webp' => 'image/webp', 'gif' => 'image/gif',
          'pdf' => 'application/pdf', 'psd' => 'image/vnd.adobe.photoshop', 'clip' => 'application/octet-stream', 'heic' => 'image/heic'][$ext] ?? 'application/octet-stream';
}
function paypal_link(float $amount, string $id, string $label, string $site): string {
  if ($amount <= 0 || !filter_var(PAYPAL_EMAIL, FILTER_VALIDATE_EMAIL)) return '';
  return 'https://www.paypal.com/cgi-bin/webscr?' . http_build_query([
    'cmd' => '_xclick', 'business' => PAYPAL_EMAIL, 'item_name' => mb_substr("KeikoArts commission – $label [$id]", 0, 127),
    'item_number' => $id, 'amount' => number_format($amount, 2, '.', ''), 'currency_code' => 'USD', 'no_shipping' => '1', 'rm' => '1',
    'return' => $site . '?paid=1&rid=' . rawurlencode($id), 'cancel_return' => $site]);
}
function send_mail(string $to, string $subject, string $html, string $text, string $replyTo = '', array $attach = []): bool {
  if (!function_exists('mail')) return false;
  $b1 = 'mix_' . bin2hex(random_bytes(8)); $b2 = 'alt_' . bin2hex(random_bytes(8));
  $headers = ['From: KeikoArts <' . MAIL_FROM . '>', 'MIME-Version: 1.0', 'X-Mailer: KeikoArts'];
  if ($replyTo !== '' && filter_var($replyTo, FILTER_VALIDATE_EMAIL)) $headers[] = 'Reply-To: ' . $replyTo;
  $alt = "--$b2\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($text))
       . "--$b2\r\nContent-Type: text/html; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($html)) . "--$b2--\r\n";
  if ($attach) {
    $headers[] = "Content-Type: multipart/mixed; boundary=\"$b1\"";
    $body = "--$b1\r\nContent-Type: multipart/alternative; boundary=\"$b2\"\r\n\r\n" . $alt;
    foreach ($attach as $a) {
      $data = @file_get_contents($a['path']); if ($data === false) continue;
      $body .= "--$b1\r\nContent-Type: {$a['type']}; name=\"{$a['name']}\"\r\nContent-Transfer-Encoding: base64\r\nContent-Disposition: attachment; filename=\"{$a['name']}\"\r\n\r\n" . chunk_split(base64_encode($data));
    }
    $body .= "--$b1--\r\n";
  } else { $headers[] = "Content-Type: multipart/alternative; boundary=\"$b2\""; $body = $alt; }
  $subj = '=?UTF-8?B?' . base64_encode($subject) . '?=';
  $hdr = implode("\r\n", $headers);
  $ok = @mail($to, $subj, $body, $hdr, '-f' . MAIL_FROM);
  if (!$ok) $ok = @mail($to, $subj, $body, $hdr);
  return (bool)$ok;
}
function discord_ping(array $cfg, array $o, array $fields): void {
  $hook = $cfg['discord_webhook'] ?? '';
  if (!preg_match('#^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$#', $hook) || !function_exists('curl_init')) return;
  $safe = fn($s) => str_replace(['@everyone', '@here'], ["@\u{200B}everyone", "@\u{200B}here"], (string)$s);
  $f = fn($n, $v, $in = true) => ['name' => $n, 'value' => $safe($v !== '' && $v !== null ? mb_substr((string)$v, 0, 1000) : '-'), 'inline' => $in];
  $payload = ['username' => 'KeikoArts Orders', 'allowed_mentions' => ['parse' => []], 'embeds' => [[
    'title' => ($o['kind'] === 'custom' ? '🧾 New custom order ' : '🎀 New request ') . $o['id'],
    'description' => $safe(mb_substr($fields['Details'] ?? '-', 0, 1500)),
    'color' => 0xF2628F,
    'fields' => [
      $f('Service', trim(($o['service'] ?? '') . ' — ' . ($o['package'] ?? ''), ' —')),
      $f('Total', money2((float)$o['total']) . ($o['kind'] === 'custom' ? ' (incl. 13% tax)' : '')),
      $f('Due now', money2((float)$o['due']) . ' · ' . $o['plan']),
      $f('Client', $o['name']), $f('Discord', $o['discord']), $f('Email', $o['email']),
      $f('Files', (string)count(json_decode($o['files'], true) ?: [])),
    ],
    'footer' => ['text' => 'See keikoartist.com/admin → Orders'],
  ]]];
  $ch = curl_init($hook);
  curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($payload), CURLOPT_HTTPHEADER => ['Content-Type: application/json'], CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 4]);
  curl_exec($ch); curl_close($ch);
}

/* ---------- admin auth (same login/token as the chat inbox) ---------- */
function admin_pw(array $cfg): string { return trim((string)($cfg['chat_admin_password'] ?? '')); }
function admin_key(array $cfg): string { return hash_hmac('sha256', 'keikoarts-admin-v1', admin_pw($cfg)); }
function require_admin(array $cfg, array $in): void {
  if (strlen(admin_pw($cfg)) < 8) fail(401, 'login required');
  $t = (string)($_SERVER['HTTP_X_AUTH'] ?? ($in['_auth'] ?? ''));
  if (!preg_match('/^(\d{10})\.([a-f0-9]{64})$/', $t, $m)) fail(401, 'login required');
  if ((int)$m[1] < time() || !hash_equals(hash_hmac('sha256', $m[1], admin_key($cfg)), $m[2])) fail(401, 'login required');
}
function order_row(string $id): array {
  if (!preg_match('/^(INV|REQ)-\d{4}-\d{4}$/', $id)) fail(400, 'bad id');
  $st = db()->prepare('SELECT * FROM orders WHERE id = ?'); $st->execute([$id]); $o = $st->fetch();
  if (!$o) fail(404, 'not found');
  return $o;
}

try {
/* =================== public: health check (upload limits) =================== */
if (($_GET['a'] ?? '') === 'ping') {
  jout(200, ['upload_max' => ini_get('upload_max_filesize'), 'post_max' => ini_get('post_max_size'), 'max_file_uploads' => (int)ini_get('max_file_uploads'),
             'mail' => function_exists('mail'), 'mail_in_disabled_list' => stripos((string)ini_get('disable_functions'), 'mail') !== false,
             'php' => PHP_MAJOR_VERSION . '.' . PHP_MINOR_VERSION, 'sqlite' => in_array('sqlite', PDO::getAvailableDrivers(), true), 'data_writable' => is_writable(data_dir())]);
}

/* =================== one-off: remove Claude's automated test orders (exact test signatures only) =================== */
if (($_GET['a'] ?? '') === 'cleanup_tests') {
  $db = db(); $ids = [];
  foreach ($db->query('SELECT id, name, email, discord, fields FROM orders')->fetchAll() as $r) {
    $f = json_decode((string)$r['fields'], true) ?: [];
    $browserTest = $r['name'] === 'Test' && $r['email'] === 'test@example.com' && $r['discord'] === 'tester' && ($f['Details'] ?? '') === 'Automated test';
    $apiTest = $r['name'] === 'TEST by Claude - please delete' && strpos((string)($f['Details'] ?? ''), 'Automatic test of the new order system') === 0;
    if ($browserTest || $apiTest) $ids[] = $r['id'];
  }
  foreach ($ids as $id) {
    $dir = data_dir() . '/order-files/' . $id;
    if (is_dir($dir)) { foreach (glob("$dir/*") ?: [] as $f) @unlink($f); @rmdir($dir); }
    $db->prepare('DELETE FROM orders WHERE id = ?')->execute([$id]);
  }
  $left = (int)$db->query('SELECT COUNT(*) FROM orders')->fetchColumn();
  jout(200, ['deleted' => $ids, 'orders_left' => $left]);
}

/* =================== public: new order =================== */
if (($_GET['a'] ?? '') === 'submit') {
  if (!$_POST) fail(413, 'Your reference files are too big to upload. Please attach smaller images, or paste links instead.');
  if (!empty($_POST['_honey'])) jout(200, ['id' => 'REQ-0000-0000', 'pay_url' => '']);
  $dry = !empty($_POST['_dryrun']);                               // test mode: validates everything, saves/sends nothing
  rate_limit(($dry ? 'dry:' : 'order:') . client_ip(), $dry ? 40 : 20, 3600);

  $skip = ['svc', 'pkg', 'add', 'mxType', 'mxSize', 'Request ID', 'Estimated total (USD)', 'Amount due now (USD)'];
  $fields = [];
  foreach ($_POST as $k => $v) {
    if (!is_string($v) || !is_string($k) || $k === '' || $k[0] === '_') continue;
    $label = clean(str_replace('_', ' ', $k), 60);              // PHP turns spaces in field names into "_"
    if ($label === 'email') $label = 'Email';
    if (in_array($label, $skip, true) || count($fields) >= 30) continue;
    $fields[$label] = clean($v, $label === 'Details' ? 4000 : 400);
  }
  $name = $fields['Name'] ?? ''; $service = $fields['Service'] ?? ''; $email = $fields['Email'] ?? '';
  if ($name === '' || $service === '' || ($fields['Details'] ?? '') === '') fail(400, 'Please fill in your name and describe your request.');
  if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) fail(400, 'Please check your email address.');

  $kind = $service === 'Custom Inquiry' ? 'custom' : 'request';
  $plan = $fields['Payment plan'] ?? 'Full payment';
  if ($kind === 'custom') {
    $price = round((float)str_replace(',', '.', (string)($_POST['_price'] ?? 0)), 2);
    if ($price < 5 || $price > 10000) fail(400, 'Please enter your price ($5 – $10,000).');
    $tax = round($price * TAX_RATE, 2); $total = round($price + $tax, 2); $due = $total; $plan = 'Full payment';
  } else {
    $price = 0.0; $tax = 0.0;
    $tRaw = $_POST['_total'] ?? preg_replace('/[^0-9.]/', '', (string)($_POST['Estimated_total_(USD)'] ?? '0'));
    $total = round(min(100000, max(0, (float)$tRaw)), 2);
    $k = strpos($plan, '50/50') !== false ? 0.5 : (preg_match('/3x|3×/iu', $plan) ? 1 / 3 : 1);
    $due = $total > 0 ? ceil(round($total * $k * 100, 6)) / 100 : 0.0;
  }

  $db = db();
  $prefix = $kind === 'custom' ? 'INV-' : 'REQ-';
  do { $id = $prefix . date('md') . '-' . random_int(1000, 9999); $st = $db->prepare('SELECT 1 FROM orders WHERE id = ?'); $st->execute([$id]); } while ($st->fetchColumn());

  // reference files
  $files = []; $report = []; $skippedNames = []; $dir = data_dir() . '/order-files/' . $id;
  $allowed = ['jpg', 'jpeg', 'png', 'webp', 'gif', 'pdf', 'psd', 'clip', 'heic'];
  foreach ($_FILES as $f) {
    if (!is_array($f) || !isset($f['error']) || is_array($f['error']) || $f['error'] === UPLOAD_ERR_NO_FILE) continue;
    $nm = clean((string)($f['name'] ?? 'file'), 80); $err = (int)$f['error']; $ext = strtolower(pathinfo($nm, PATHINFO_EXTENSION));
    $why = '';
    if (count($files) >= MAX_FILES) $why = 'too many files';
    elseif ($err === UPLOAD_ERR_INI_SIZE || $err === UPLOAD_ERR_FORM_SIZE || (int)$f['size'] > MAX_FILE_BYTES) $why = 'too big';
    elseif ($err !== UPLOAD_ERR_OK) $why = 'upload error ' . $err;
    elseif (!in_array($ext, $allowed, true)) $why = 'file type not allowed';
    if ($why === '') {
      $base = substr(preg_replace('/[^A-Za-z0-9\-]+/', '_', pathinfo($nm, PATHINFO_FILENAME)) ?: 'file', 0, 40);
      $safe = (count($files) + 1) . '-' . (trim($base, '_') ?: 'file') . '.' . $ext;
      if ($dry) $files[] = ['name' => $safe, 'size' => (int)$f['size'], 'type' => mime_of($ext)];
      else {
        if (!is_dir($dir)) @mkdir($dir, 0700, true);
        if (@move_uploaded_file($f['tmp_name'], "$dir/$safe")) $files[] = ['name' => $safe, 'size' => (int)$f['size'], 'type' => mime_of($ext)];
        else $why = 'could not save';
      }
    }
    if ($why !== '') $skippedNames[] = $nm;
    $report[] = ['name' => $nm, 'size' => (int)($f['size'] ?? 0), 'ok' => $why === '', 'why' => $why];
  }
  $skipped = count($skippedNames);
  if ($dry) {
    $label = $kind === 'custom' ? 'Custom commission, ' . ($fields['Usage'] ?? 'Personal') . ' use, incl. 13% tax' : trim($service . ' (' . ($fields['Package'] ?? '') . ')');
    jout(200, ['id' => $id, 'kind' => $kind, 'price' => $price, 'tax' => $tax, 'total' => $total, 'due' => $due, 'plan' => $plan,
               'pay_url' => paypal_link($due, $id, $label, $SITE), 'date' => date('M j, Y'), 'emailed' => false, 'notified' => false,
               'files' => count($files), 'skipped_files' => $skipped, 'skipped_names' => $skippedNames, 'dry_run' => true, 'file_report' => $report]);
  }

  $o = ['id' => $id, 'kind' => $kind, 'name' => $name, 'email' => $email, 'discord' => $fields['Discord'] ?? '',
        'service' => $service, 'package' => $fields['Package'] ?? '', 'plan' => $plan, 'price' => $price, 'tax' => $tax,
        'total' => $total, 'due' => $due, 'fields' => json_encode($fields, JSON_UNESCAPED_UNICODE), 'files' => json_encode($files)];
  $now = time();
  $db->prepare('INSERT INTO orders(id,kind,status,name,email,discord,service,package,plan,price,tax,total,due,fields,files,created,updated)
                VALUES(?,?,\'new\',?,?,?,?,?,?,?,?,?,?,?,?,?,?)')
     ->execute([$id, $kind, $name, $email, $o['discord'], $service, $o['package'], $plan, $price, $tax, $total, $due, $o['fields'], $o['files'], $now, $now]);

  $label = $kind === 'custom' ? 'Custom commission, ' . ($fields['Usage'] ?? 'Personal') . ' use, incl. 13% tax' : trim($service . ' (' . ($o['package']) . ')');
  $payUrl = paypal_link($due, $id, $label, $SITE);
  $dateStr = date('M j, Y');

  // ---- email to Keiko ----
  $rows = '';
  $sum = $kind === 'custom'
    ? ['Client price' => money2($price), 'Tax (13%)' => money2($tax), 'Total (paid upfront)' => money2($total)]
    : ['Estimated total' => money2($total), 'Due now' => money2($due) . " ($plan)"];
  foreach ($sum + $fields as $k => $v) $rows .= '<tr><th align="left" valign="top" style="padding:6px 12px 6px 0;color:#a8607a;font-weight:500;white-space:nowrap">' . h((string)$k) . '</th><td style="padding:6px 0;white-space:pre-wrap">' . h((string)$v) . '</td></tr>';
  $fileNote = $files ? count($files) . ' reference file(s)' : 'No files';
  $attach = []; $bytes = 0;
  foreach ($files as $f) { $bytes += $f['size']; if ($bytes <= MAIL_ATTACH_MAX) $attach[] = ['path' => "$dir/{$f['name']}", 'name' => $f['name'], 'type' => $f['type']]; }
  if (count($attach) < count($files)) $fileNote .= ' (open the admin inbox to see all files)';
  $titleTxt = $kind === 'custom' ? "New custom order — " . money2($total) . " incl. tax [$id]" : "New request: $service (" . $o['package'] . ") — " . money2($total) . " [$id]";
  $html = '<div style="font-family:Arial,sans-serif;color:#7a2846;font-size:14px"><h2 style="color:#f2628f;margin:0 0 6px">' . h($titleTxt) . '</h2>'
        . '<p style="margin:0 0 14px;color:#a8607a">' . h($dateStr) . ' · ' . h($fileNote) . ' · <a href="' . h($SITE) . 'admin/">Open admin → Orders</a></p>'
        . '<table cellspacing="0" style="border-collapse:collapse;font-size:14px">' . $rows . '</table>'
        . ($payUrl ? '<p style="margin-top:14px;color:#a8607a">The client was shown a PayPal button for ' . h(money2($due)) . '. Check PayPal for a payment with ID ' . h($id) . '.</p>' : '') . '</div>';
  $text = $titleTxt . "\n\n";
  foreach ($sum + $fields as $k => $v) $text .= "$k: $v\n";
  $text .= "\n$fileNote\nAdmin: {$SITE}admin/\n";
  $mailed = send_mail(OWNER_EMAIL, $titleTxt, $html, $text, $email, $attach);
  if ($attach && !$mailed) $mailed = send_mail(OWNER_EMAIL, $titleTxt, $html, $text . "\n(Files were too big for email — see the admin inbox.)", $email);

  // ---- confirmation / invoice email to the client ----
  $clientMailed = false;
  if ($email !== '') {
    $cn = h(no_links($name) ?: 'there');
    if ($kind === 'custom') {
      $subj = "Your KeikoArts invoice $id";
      $body = "<p>Hi $cn, thank you for your custom order at KeikoArts! ♡</p>"
            . '<table cellspacing="0" style="border-collapse:collapse;font-size:14px;min-width:280px">'
            . '<tr><td colspan="2" style="padding:0 0 8px;color:#a8607a">Invoice <b style="color:#f2628f">' . h($id) . '</b> · ' . h($dateStr) . '</td></tr>'
            . '<tr><td style="padding:4px 16px 4px 0">Custom commission (' . h($fields['Usage'] ?? 'Personal') . ' use)</td><td align="right">' . money2($price) . '</td></tr>'
            . '<tr><td style="padding:4px 16px 4px 0">Tax (13%)</td><td align="right">' . money2($tax) . '</td></tr>'
            . '<tr><td style="padding:8px 16px 4px 0;border-top:1px solid #fbd3e0"><b>Total due (USD)</b></td><td align="right" style="border-top:1px solid #fbd3e0;padding-top:8px"><b>' . money2($total) . '</b></td></tr></table>';
      $txt = "Hi " . (no_links($name) ?: 'there') . ", thank you for your custom order at KeikoArts!\n\nINVOICE $id · $dateStr\nCustom commission: " . money2($price) . "\nTax (13%): " . money2($tax) . "\nTOTAL DUE: " . money2($total) . " USD\n\n";
    } else {
      $subj = "Your KeikoArts request $id";
      $body = "<p>Hi $cn, thank you for your commission request at KeikoArts! ♡</p><p>Request ID: <b style=\"color:#f2628f\">" . h($id) . '</b><br>Service: ' . h($service . ' (' . $o['package'] . ')') . '<br>Estimated total: ' . money2($total) . '<br>Payment plan: ' . h($plan) . '</p>';
      $txt = "Hi " . (no_links($name) ?: 'there') . ", thank you for your commission request at KeikoArts!\n\nRequest ID: $id\nService: $service ({$o['package']})\nEstimated total: " . money2($total) . "\nPayment plan: $plan\n\n";
    }
    if ($payUrl) {
      $body .= '<p><a href="' . h($payUrl) . '" style="display:inline-block;background:#ffc439;color:#003087;padding:12px 22px;border-radius:999px;font-weight:bold;text-decoration:none">Pay ' . money2($due) . ' with PayPal</a></p><p style="color:#a8607a;font-size:13px">Full refund if I can\'t take your ' . ($kind === 'custom' ? 'commission' : 'request') . '.</p>';
      $txt .= "Pay " . money2($due) . " with PayPal:\n$payUrl\n(Full refund if I can't take your " . ($kind === 'custom' ? 'commission' : 'request') . ".)\n\n";
    }
    $body .= '<p>Questions? Message me on <a href="' . DISCORD_USER . '">Discord</a> with your ' . ($kind === 'custom' ? 'invoice number' : 'Request ID') . '. I reply within 6 hours.</p><p>— Keiko, KeikoArts</p>';
    $txt .= "Questions? Message me on Discord with your " . ($kind === 'custom' ? 'invoice number' : 'Request ID') . ":\n" . DISCORD_USER . "\n\n— Keiko, KeikoArts";
    $clientMailed = send_mail($email, $subj, '<div style="font-family:Arial,sans-serif;color:#7a2846;font-size:14px">' . $body . '</div>', $txt, OWNER_EMAIL);
  }
  $db->prepare('UPDATE orders SET mailed = ? WHERE id = ?')->execute([$mailed ? 1 : 0, $id]);
  discord_ping($cfg, $o, $fields);

  if ($HTML_MODE) {
    $rowsH = $kind === 'custom'
      ? '<tr><td>Custom commission (' . h($fields['Usage'] ?? 'Personal') . ' use)</td><td>' . money2($price) . '</td></tr><tr><td>Tax (13%)</td><td>' . money2($tax) . '</td></tr><tr class="tot"><td>Total due (USD)</td><td>' . money2($total) . '</td></tr>'
      : '<tr><td>' . h($service . ' (' . $o['package'] . ')') . '</td><td>' . money2($total) . '</td></tr><tr class="tot"><td>Due now (' . h($plan) . ')</td><td>' . money2($due) . '</td></tr>';
    page($kind === 'custom' ? 'Your invoice' : 'Request sent',
      '<h1>' . ($kind === 'custom' ? 'Your invoice ♡' : 'Request sent! ♡') . '</h1><p class="muted">' . ($kind === 'custom' ? 'Invoice no.' : 'Request ID') . ' <b>' . h($id) . '</b> · ' . h($dateStr) . '</p><p>Billed to <b>' . h($name) . '</b></p>'
      . '<table>' . $rowsH . '</table>'
      . ($payUrl && $due > 0 ? '<a class="pp" href="' . h($payUrl) . '">Pay ' . money2($due) . ' with PayPal</a><p class="muted">Secure checkout on PayPal. Full refund if I can\'t take your ' . ($kind === 'custom' ? 'commission' : 'request') . '.</p>' : ''));
  }
  jout(200, ['id' => $id, 'kind' => $kind, 'price' => $price, 'tax' => $tax, 'total' => $total, 'due' => $due, 'plan' => $plan,
             'pay_url' => $payUrl, 'date' => $dateStr, 'emailed' => $clientMailed, 'notified' => $mailed, 'files' => count($files), 'skipped_files' => $skipped, 'skipped_names' => $skippedNames]);
}

/* =================== admin =================== */
$raw = file_get_contents('php://input', false, null, 0, 20000) ?: '';
$in = json_decode($raw, true);
if (!is_array($in)) fail(400, 'bad json');
require_admin($cfg, $in);
$action = (string)($in['action'] ?? '');

switch ($action) {
  case 'count': {
    jout(200, ['new' => (int)db()->query("SELECT COUNT(*) FROM orders WHERE status = 'new'")->fetchColumn()]);
  }
  case 'list': {
    $s = (string)($in['status'] ?? 'new');
    $sql = 'SELECT id, kind, status, name, email, discord, service, package, plan, total, due, files, created FROM orders';
    if ($s === 'open') { $st = db()->prepare("$sql WHERE status IN ('new','paid','in_progress') ORDER BY created DESC LIMIT 300"); $st->execute(); }
    elseif (in_array($s, STATUSES, true)) { $st = db()->prepare("$sql WHERE status = ? ORDER BY created DESC LIMIT 300"); $st->execute([$s]); }
    else { $st = db()->prepare("$sql ORDER BY created DESC LIMIT 300"); $st->execute(); }
    $rows = array_map(function ($r) { $r['total'] = (float)$r['total']; $r['due'] = (float)$r['due']; $r['created'] = (int)$r['created']; $r['files'] = count(json_decode((string)$r['files'], true) ?: []); return $r; }, $st->fetchAll());
    $new = (int)db()->query("SELECT COUNT(*) FROM orders WHERE status = 'new'")->fetchColumn();
    jout(200, ['orders' => $rows, 'new' => $new]);
  }
  case 'get': {
    $o = order_row((string)($in['id'] ?? ''));
    foreach (['price', 'tax', 'total', 'due'] as $k) $o[$k] = (float)$o[$k];
    $o['created'] = (int)$o['created']; $o['updated'] = (int)$o['updated']; $o['mailed'] = (int)$o['mailed'];
    $o['fields'] = json_decode((string)$o['fields'], true) ?: []; $o['files'] = json_decode((string)$o['files'], true) ?: [];
    $o['pay_url'] = paypal_link((float)$o['due'], $o['id'], $o['kind'] === 'custom' ? 'Custom commission, incl. 13% tax' : $o['service'] . ' (' . $o['package'] . ')', $SITE);
    jout(200, ['order' => $o]);
  }
  case 'status': {
    $o = order_row((string)($in['id'] ?? ''));
    $s = (string)($in['status'] ?? ''); if (!in_array($s, STATUSES, true)) fail(400, 'bad status');
    db()->prepare('UPDATE orders SET status = ?, updated = ? WHERE id = ?')->execute([$s, time(), $o['id']]);
    jout(200);
  }
  case 'file': {
    $o = order_row((string)($in['id'] ?? ''));
    $name = (string)($in['name'] ?? '');
    foreach (json_decode((string)$o['files'], true) ?: [] as $f) {
      if ($f['name'] === $name) {
        $p = data_dir() . '/order-files/' . $o['id'] . '/' . basename($f['name']);
        if (!is_file($p)) break;
        header('Content-Type: ' . $f['type']); header('Content-Length: ' . filesize($p));
        header('Content-Disposition: inline; filename="' . $f['name'] . '"');
        readfile($p); exit;
      }
    }
    fail(404, 'file not found');
  }
  case 'delete': {
    $o = order_row((string)($in['id'] ?? ''));
    $dir = data_dir() . '/order-files/' . $o['id'];
    if (is_dir($dir)) { foreach (glob("$dir/*") ?: [] as $f) @unlink($f); @rmdir($dir); }
    db()->prepare('DELETE FROM orders WHERE id = ?')->execute([$o['id']]);
    jout(200);
  }
  default: fail(400, 'unknown action');
}
} catch (Throwable $e) {
  error_log('order-api: ' . $e->getMessage());
  fail(500, 'Server error, please try again.');
}
