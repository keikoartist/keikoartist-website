<?php
/*
 * KeikoArts live chat API (visitor widget + admin inbox).
 * Storage: SQLite file OUTSIDE the public folder (falls back to a protected folder).
 * Config (server only, not in GitHub) — keikoarts-config.php:
 *   <?php return [
 *     'discord_webhook'     => 'https://discord.com/api/webhooks/...',   // optional: ping on new chats
 *     'chat_admin_password' => 'your-strong-password',                   // required for /admin/
 *   ];
 */
declare(strict_types=1);
header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');
header('Referrer-Policy: same-origin');

const SMTP_HOST = 'ssl://smtp.gmail.com:465';
const KA_CHAT = 1;
require_once __DIR__ . '/chat-bot.php';   // automatic answer from prices.json
const MAX_MSG = 2000;
const MAX_NAME = 60;

function out(int $code, array $data = []): void { http_response_code($code); echo json_encode($data + ['ok' => $code === 200], JSON_UNESCAPED_UNICODE); exit; }
function fail(int $code, string $msg): void { out($code, ['error' => $msg]); }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') fail(405, 'POST only');
$host = preg_replace('/:\d+$/', '', strtolower($_SERVER['HTTP_HOST'] ?? ''));
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin && strtolower((string)parse_url($origin, PHP_URL_HOST)) !== $host) fail(403, 'bad origin');

$cfgFile = __DIR__ . '/keikoarts-config.php';
ob_start(); $cfg = is_file($cfgFile) ? (include $cfgFile) : []; ob_end_clean();   // ignore stray spaces or newlines printed by the server config file
if (!is_array($cfg)) $cfg = [];

/* ---------- storage ---------- */
function data_dir(): string {
  $outside = dirname(__DIR__, 2) . '/keikoarts-data';          // e.g. /home/user/keikoarts-data
  if ((is_dir($outside) || @mkdir($outside, 0700, true)) && is_writable($outside)) return $outside;
  $inside = __DIR__ . '/chat-data';                              // fallback, locked by .htaccess
  if (!is_dir($inside)) @mkdir($inside, 0700, true);
  if (!is_file("$inside/.htaccess")) @file_put_contents("$inside/.htaccess", "Require all denied\nDeny from all\n");
  if (!is_file("$inside/index.html")) @file_put_contents("$inside/index.html", '');
  return $inside;
}
function db(): PDO {
  static $pdo = null; if ($pdo) return $pdo;
  $pdo = new PDO('sqlite:' . data_dir() . '/chat.sqlite', null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC]);
  $pdo->exec('PRAGMA journal_mode=WAL; PRAGMA busy_timeout=4000; PRAGMA foreign_keys=ON;');
  $pdo->exec('CREATE TABLE IF NOT EXISTS conversations(
      id TEXT PRIMARY KEY, token_hash TEXT NOT NULL, name TEXT, email TEXT, page TEXT,
      status TEXT NOT NULL DEFAULT \'open\', created INTEGER, updated INTEGER,
      unread_admin INTEGER NOT NULL DEFAULT 0, unread_visitor INTEGER NOT NULL DEFAULT 0, last_ping INTEGER NOT NULL DEFAULT 0)');
  $pdo->exec('CREATE TABLE IF NOT EXISTS messages(
      id INTEGER PRIMARY KEY AUTOINCREMENT, conv_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
      sender TEXT NOT NULL, agent TEXT, body TEXT NOT NULL, created INTEGER NOT NULL)');
  $pdo->exec('CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conv_id, id)');
  $pdo->exec('CREATE TABLE IF NOT EXISTS hits(k TEXT, t INTEGER)');
  $cols = array_column($pdo->query('PRAGMA table_info(conversations)')->fetchAll(), 'name');
  if (!in_array('discord', $cols, true)) $pdo->exec('ALTER TABLE conversations ADD COLUMN discord TEXT');
  if (!in_array('notify', $cols, true)) $pdo->exec('ALTER TABLE conversations ADD COLUMN notify INTEGER NOT NULL DEFAULT 1');
  if (!in_array('remind_at', $cols, true)) $pdo->exec('ALTER TABLE conversations ADD COLUMN remind_at INTEGER NOT NULL DEFAULT 0');
  if (!in_array('remind_n', $cols, true)) $pdo->exec('ALTER TABLE conversations ADD COLUMN remind_n INTEGER NOT NULL DEFAULT 0');
  return $pdo;
}

/* ---------- helpers ---------- */
function clean(string $v, int $max): string {
  $v = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $v) ?? '';
  $v = trim($v);
  return mb_substr($v, 0, $max);
}
function client_ip(): string { return $_SERVER['REMOTE_ADDR'] ?? '0'; }
function rate_limit(string $key, int $max, int $window): void {
  $db = db(); $now = time();
  $db->prepare('DELETE FROM hits WHERE t < ?')->execute([$now - 3600]);
  $k = hash('sha256', $key);
  $st = $db->prepare('SELECT COUNT(*) FROM hits WHERE k = ? AND t > ?'); $st->execute([$k, $now - $window]);
  if ((int)$st->fetchColumn() >= $max) fail(429, 'Too many messages, please wait a moment.');
  $db->prepare('INSERT INTO hits(k,t) VALUES(?,?)')->execute([$k, $now]);
}
function visitor_conv(array $in): array {
  $id = (string)($in['id'] ?? ''); $tok = (string)($in['token'] ?? '');
  if (!preg_match('/^[a-f0-9]{24}$/', $id) || strlen($tok) < 32) fail(401, 'bad session');
  $st = db()->prepare('SELECT * FROM conversations WHERE id = ?'); $st->execute([$id]); $c = $st->fetch();
  if (!$c || !hash_equals($c['token_hash'], hash('sha256', $tok))) fail(401, 'bad session');
  return $c;
}
function msgs(string $conv, int $since): array {
  $st = db()->prepare('SELECT id, sender, agent, body, created FROM messages WHERE conv_id = ? AND id > ? ORDER BY id LIMIT 300');
  $st->execute([$conv, $since]);
  return array_map(function ($m) { $m['id'] = (int)$m['id']; $m['created'] = (int)$m['created']; return $m; }, $st->fetchAll());
}
/* ---- email to a visitor when Keiko replies (sent from the studio Gmail saved in admin -> Settings) ---- */
function chat_mail(string $to, string $subject, string $text, string $html): bool {
  $s = ka_settings(); $u = (string)($s['gmail_user'] ?? ''); $p = (string)($s['gmail_pass'] ?? '');
  if ($u === '' || $p === '' || !filter_var($to, FILTER_VALIDATE_EMAIL)) return false;
  $say = function ($fp, ?string $c, array $ok) { if ($c !== null) fwrite($fp, $c . "\r\n"); $r = ''; while (($l = fgets($fp, 600)) !== false) { $r .= $l; if (strlen($l) < 4 || $l[3] === ' ') break; } if (!in_array((int)substr($r, 0, 3), $ok, true)) throw new RuntimeException(trim(substr($r, 0, 120))); };
  try {
    $e = 0; $m = ''; $fp = @stream_socket_client(SMTP_HOST, $e, $m, 8); if (!$fp) return false; stream_set_timeout($fp, 15);
    $say($fp, null, [220]); $say($fp, 'EHLO keikoartist.com', [250]); $say($fp, 'AUTH LOGIN', [334]); $say($fp, base64_encode($u), [334]); $say($fp, base64_encode($p), [235]);
    $say($fp, "MAIL FROM:<$u>", [250]); $say($fp, "RCPT TO:<$to>", [250, 251]); $say($fp, 'DATA', [354]);
    $bd = 'alt_' . bin2hex(random_bytes(8));
    $raw = "From: KeikoArts <$u>\r\nTo: <$to>\r\nReply-To: <$u>\r\nSubject: =?UTF-8?B?" . base64_encode($subject) . "?=\r\nDate: " . date('r') . "\r\nMessage-ID: <" . bin2hex(random_bytes(12)) . "@keikoartist.com>\r\nMIME-Version: 1.0\r\nContent-Type: multipart/alternative; boundary=\"$bd\"\r\n\r\n"
         . "--$bd\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($text))
         . "--$bd\r\nContent-Type: text/html; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n" . chunk_split(base64_encode($html)) . "--$bd--\r\n";
    fwrite($fp, preg_replace('/^\./m', '..', $raw) . "\r\n.\r\n"); $say($fp, null, [250]);
    @fwrite($fp, "QUIT\r\n"); @fclose($fp); return true;
  } catch (Throwable $ex) { if (!empty($fp)) @fclose($fp); return false; }
}
function clean_discord(string $v): string {   // a Discord username: letters, numbers, _ and . (old style name#1234 allowed)
  $v = trim(ltrim(trim($v), '@'));
  return preg_match('/^[a-zA-Z0-9_.]{2,32}(#\d{4})?$/', $v) ? $v : '';
}
function bot_answer(string $convId, string $text, bool $first, string $email, string $name): void {   // stored as sender 'bot'; emailed only for the first message
  try { $ans = bot_reply($text, $first); } catch (\Throwable $e) { return; }
  if ($ans === '') return;
  $db = db(); $now = time();
  $db->prepare('INSERT INTO messages(conv_id, sender, agent, body, created) VALUES(?,?,?,?,?)')->execute([$convId, 'bot', 'Automatic reply', $ans, $now]);
  if ($first && $email !== '') {
    $nm = preg_match('/^Visitor [0-9A-F]{4}$/', $name) ? 'there' : $name; $link = 'https://keikoartist.com/#chat';
    @chat_mail($email, 'KeikoArts got your message',
      "Hi $nm,\n\nThanks for writing to KeikoArts! Here is an automatic answer while Keiko is away:\n\n$ans\n\nKeiko will reply personally, usually within 6 hours (WIB). Just reply to this email, or continue the chat on the website (same device): $link\n\nKeikoArts",
      '<div style="font-family:Arial,sans-serif;color:#7a2846;font-size:14px;line-height:1.55"><p>Hi ' . htmlspecialchars($nm) . ',</p><p>Thanks for writing to KeikoArts! Here is an automatic answer while Keiko is away:</p>'
      . '<blockquote style="margin:12px 0;padding:10px 14px;background:#fff0f5;border-left:3px solid #f2628f;border-radius:6px">' . nl2br(htmlspecialchars($ans)) . '</blockquote>'
      . '<p>Keiko will reply personally, usually within 6 hours (WIB). Just reply to this email, or <a href="' . $link . '">continue the chat on the website</a>.</p><p>KeikoArts</p></div>');
  }
}
/* Reminders: while a chat stays unread, Discord gets a reminder every 30 minutes (up to 12 times = 6 hours).
   Runs on chat traffic and from the scheduled GitHub workflow (chat-reminders.yml) calling ?remind=1. */
function send_reminders(array $cfg): int {
  $hook = (string)($cfg['discord_webhook'] ?? '');
  if (!preg_match('#^https://(?:ptb\.|canary\.)?(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$#', $hook)) { $st = ka_settings(); $hook = (string)($st['discord_webhook'] ?? ''); }
  $hasHook = preg_match('#^https://(?:ptb\.|canary\.)?(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$#', $hook) && function_exists('curl_init');
  $ks = ka_settings(); $ownerMail = (string)($ks['gmail_user'] ?? '');   // Keiko's own Gmail (the one set in admin → Settings) also gets the reminder
  if (!$hasHook && $ownerMail === '') return 0;
  $db = db(); $now = time(); $sent = 0;
  $st = $db->prepare("SELECT c.*, (SELECT body FROM messages m WHERE m.conv_id = c.id AND m.sender = 'visitor' ORDER BY m.id DESC LIMIT 1) AS last_msg,
                             (SELECT MIN(created) FROM messages m WHERE m.conv_id = c.id AND m.sender = 'visitor' AND m.id > COALESCE((SELECT MAX(id) FROM messages a WHERE a.conv_id = c.id AND a.sender = 'admin'), 0)) AS waiting_since
                      FROM conversations c WHERE c.unread_admin > 0 AND c.status = 'open' AND c.remind_n < 12 AND c.remind_at < ? LIMIT 10");
  $st->execute([$now - 1800]);
  foreach ($st->fetchAll() as $c) {
    $since = (int)($c['waiting_since'] ?: $c['updated']); if ($now - $since < 1800) continue;   // first reminder after 30 minutes
    $db->prepare('UPDATE conversations SET remind_at = ?, remind_n = remind_n + 1 WHERE id = ?')->execute([$now, $c['id']]);
    $mins = intdiv($now - $since, 60); $wait = $mins >= 60 ? intdiv($mins, 60) . ' h ' . ($mins % 60) . ' min' : "$mins min";
    $safe = fn($x) => str_replace(['@everyone', '@here'], ["@\u{200B}everyone", "@\u{200B}here"], (string)$x);
    $payload = ['username' => 'KeikoArts Chat', 'allowed_mentions' => ['parse' => []], 'embeds' => [[
      'title' => '⏰ Still unread: ' . $safe($c['name'] ?: 'Visitor') . " (waiting $wait)",
      'description' => $safe(mb_substr((string)$c['last_msg'], 0, 400)),
      'color' => 0xC93A6A,
      'fields' => array_values(array_filter([$c['email'] ? ['name' => 'Email', 'value' => $safe($c['email']), 'inline' => true] : null, !empty($c['discord']) ? ['name' => 'Discord', 'value' => $safe($c['discord']), 'inline' => true] : null])),
      'footer' => ['text' => 'Reminder ' . ((int)$c['remind_n'] + 1) . '/12 · reply at keikoartist.com/admin'],
    ]]];
    if ($hasHook) { $ch = curl_init($hook);
      curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($payload), CURLOPT_HTTPHEADER => ['Content-Type: application/json'], CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 4]);
      curl_exec($ch); curl_close($ch); }
    if ($ownerMail !== '') {
      $who = (string)($c['name'] ?: 'Visitor'); $msg = mb_substr((string)$c['last_msg'], 0, 600);
      @chat_mail($ownerMail, "⏰ Unread chat: $who (waiting $wait)",
        "$who is still waiting for your reply on keikoartist.com ($wait).\n\nLast message:\n$msg\n\n" . ($c['email'] ? "Email: {$c['email']}\n" : '') . (!empty($c['discord']) ? "Discord: {$c['discord']}\n" : '') . "\nReply here: https://keikoartist.com/admin/\n\nReminder " . ((int)$c['remind_n'] + 1) . '/12',
        '<div style="font-family:Arial,sans-serif;color:#7a2846;font-size:14px;line-height:1.55"><p><b>' . htmlspecialchars($who) . '</b> is still waiting for your reply on keikoartist.com (' . $wait . ').</p>'
        . '<blockquote style="margin:12px 0;padding:10px 14px;background:#fff0f5;border-left:3px solid #f2628f;border-radius:6px">' . nl2br(htmlspecialchars($msg)) . '</blockquote>'
        . '<p>' . ($c['email'] ? 'Email: ' . htmlspecialchars((string)$c['email']) . '<br>' : '') . (!empty($c['discord']) ? 'Discord: ' . htmlspecialchars((string)$c['discord']) : '') . '</p>'
        . '<p><a href="https://keikoartist.com/admin/" style="color:#c93a6a;font-weight:bold">Reply in the admin inbox</a></p><p style="color:#999;font-size:12px">Reminder ' . ((int)$c['remind_n'] + 1) . '/12</p></div>');
    }
    $sent++;
  }
  return $sent;
}
function discord_ping(array $cfg, array $c, string $text, bool $isNew): void {
  $hook = (string)($cfg['discord_webhook'] ?? '');
  if (!preg_match('#^https://(?:ptb\.|canary\.)?(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$#', $hook)) { $st = json_decode((string)@file_get_contents(data_dir() . '/settings.json'), true); $hook = is_array($st) ? (string)($st['discord_webhook'] ?? '') : ''; }
  if (!preg_match('#^https://(?:ptb\.|canary\.)?(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$#', $hook) || !function_exists('curl_init')) return;
  $now = time();
  if (!$isNew && $now - (int)$c['last_ping'] < 120) return;                 // don't spam: max 1 ping / 2 min per chat
  db()->prepare('UPDATE conversations SET last_ping = ? WHERE id = ?')->execute([$now, $c['id']]);
  $safe = fn($s) => str_replace(['@everyone', '@here'], ["@\u{200B}everyone", "@\u{200B}here"], $s);
  $payload = ['username' => 'KeikoArts Chat', 'allowed_mentions' => ['parse' => []], 'embeds' => [[
    'title' => ($isNew ? '💬 New chat from ' : '💬 New message from ') . $safe($c['name'] ?: 'Visitor'),
    'description' => $safe(mb_substr($text, 0, 500)),
    'color' => 0xF2628F,
    'fields' => array_values(array_filter([$c['email'] ? ['name' => 'Email', 'value' => $safe($c['email']), 'inline' => true] : null, !empty($c['discord']) ? ['name' => 'Discord', 'value' => $safe($c['discord']), 'inline' => true] : null])),
    'footer' => ['text' => 'Reply at keikoartist.com/admin'],
  ]]];
  $ch = curl_init($hook);
  curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($payload), CURLOPT_HTTPHEADER => ['Content-Type: application/json'], CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 4]);
  curl_exec($ch); curl_close($ch);
}

/* ---------- admin auth (stateless signed token, no PHP sessions needed) ---------- */
function ka_settings(): array { $j = json_decode((string)@file_get_contents(data_dir() . '/settings.json'), true); return is_array($j) ? $j : []; }
function ka_save_settings(array $s): bool { $f = data_dir() . '/settings.json'; $ok = @file_put_contents($f, json_encode($s, JSON_UNESCAPED_SLASHES), LOCK_EX) !== false; @chmod($f, 0600); return $ok; }
/* the admin secret: a password set with "Forgot password?" (stored hashed in settings.json) wins over the one in keikoarts-config.php */
function admin_pw(array $cfg): string { $h = (string)(ka_settings()['admin_pw_hash'] ?? ''); return $h !== '' ? $h : trim((string)($cfg['chat_admin_password'] ?? '')); }
function admin_pw_ok(array $cfg, string $try): bool {
  $h = (string)(ka_settings()['admin_pw_hash'] ?? '');
  if ($h !== '') return password_verify($try, $h);
  $pw = trim((string)($cfg['chat_admin_password'] ?? ''));
  return $pw !== '' && hash_equals(hash('sha256', $pw), hash('sha256', $try));
}
function ka_hook(array $cfg): string {
  $re = '#^https://(?:ptb\.|canary\.)?(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$#';
  $h = (string)($cfg['discord_webhook'] ?? ''); if (!preg_match($re, $h)) $h = (string)(ka_settings()['discord_webhook'] ?? '');
  return preg_match($re, $h) ? $h : '';
}
function ka_post_json(string $url, array $payload, array $headers = []): int {
  if (!function_exists('curl_init')) return 0;
  $ch = curl_init($url);
  curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES), CURLOPT_HTTPHEADER => array_merge(['Content-Type: application/json', 'Accept: application/json'], $headers), CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 12, CURLOPT_CONNECTTIMEOUT => 6]);
  curl_exec($ch); $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch); return $code;
}
function admin_key(array $cfg): string { return hash_hmac('sha256', 'keikoarts-admin-v1', admin_pw($cfg)); }
function make_token(array $cfg): string { $exp = time() + 60 * 60 * 24 * 14; return $exp . '.' . hash_hmac('sha256', (string)$exp, admin_key($cfg)); }
function require_admin(array $cfg): void {
  if (strlen(admin_pw($cfg)) < 8) fail(401, 'login required');
  global $in;
  $t = (string)($_SERVER['HTTP_X_AUTH'] ?? ($in['_auth'] ?? ''));
  if (!preg_match('/^(\d{10})\.([a-f0-9]{64})$/', $t, $m)) fail(401, 'login required');
  if ((int)$m[1] < time() || !hash_equals(hash_hmac('sha256', $m[1], admin_key($cfg)), $m[2])) fail(401, 'login required');
}

/* ---------- router ---------- */
if (isset($_GET['remind'])) { try { $n = send_reminders($cfg); } catch (\Throwable $e) { $n = 0; } out(200, ['ok' => true, 'sent' => $n]); }   // scheduled reminder check (no data returned)
$raw = file_get_contents('php://input', false, null, 0, 20000) ?: '';
$in = json_decode($raw, true);
if (!is_array($in)) fail(400, 'bad json');
$action = (string)($in['action'] ?? '');
if (in_array($action, ['start', 'send', 'poll'], true) && mt_rand(1, 10) === 1) { try { send_reminders($cfg); } catch (\Throwable $e) {} }   // also check now and then on chat traffic

try {
switch ($action) {

  /* ===== visitor ===== */
  case 'start': {
    if (!empty($in['_honey'])) out(200, ['id' => str_repeat('0', 24), 'token' => str_repeat('0', 40)]);
    rate_limit('start:' . client_ip(), 15, 3600);
    $name = clean((string)($in['name'] ?? ''), MAX_NAME);
    $email = clean((string)($in['email'] ?? ''), 120);
    $text = clean((string)($in['message'] ?? ''), MAX_MSG);
    if ($text === '') fail(400, 'Please type a message.');
    if ($name === '') $name = 'Visitor ' . strtoupper(substr(bin2hex(random_bytes(2)), 0, 4));
    if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) fail(400, 'Please check your email address.');
    $dc = clean_discord((string)($in['discord'] ?? ''));
    if ($email === '' || $dc === '') fail(400, 'Please add your email and your Discord username so I can reply even after you leave.');   // also blocks old cached pages without the contact fields
    $id = bin2hex(random_bytes(12)); $tok = bin2hex(random_bytes(24)); $now = time();
    $db = db(); $db->beginTransaction();
    $db->prepare('INSERT INTO conversations(id, token_hash, name, email, discord, page, created, updated, unread_admin) VALUES(?,?,?,?,?,?,?,?,1)')
       ->execute([$id, hash('sha256', $tok), $name, $email, $dc, clean((string)($in['page'] ?? ''), 200), $now, $now]);
    $db->prepare('INSERT INTO messages(conv_id, sender, body, created) VALUES(?,?,?,?)')->execute([$id, 'visitor', $text, $now]);
    $db->commit();
    $st = $db->prepare('SELECT * FROM conversations WHERE id = ?'); $st->execute([$id]);
    discord_ping($cfg, $st->fetch(), $text, true);
    bot_answer($id, $text, true, $email, $name);
    out(200, ['id' => $id, 'token' => $tok, 'messages' => msgs($id, 0)]);
  }
  case 'send': {
    $c = visitor_conv($in);
    rate_limit('send:' . client_ip(), 20, 60);
    $text = clean((string)($in['message'] ?? ''), MAX_MSG);
    if ($text === '') fail(400, 'empty');
    $now = time(); $db = db();
    $db->prepare('INSERT INTO messages(conv_id, sender, body, created) VALUES(?,?,?,?)')->execute([$c['id'], 'visitor', $text, $now]);
    $db->prepare('UPDATE conversations SET updated = ?, unread_admin = unread_admin + 1, status = \'open\' WHERE id = ?')->execute([$now, $c['id']]);
    discord_ping($cfg, $c, $text, false);
    $st = $db->prepare("SELECT COUNT(*) FROM messages WHERE conv_id = ? AND sender = 'admin'"); $st->execute([$c['id']]);
    if ((int)$st->fetchColumn() === 0) bot_answer($c['id'], $text, false, '', '');   // until Keiko has replied herself, price questions get an automatic answer
    out(200, ['messages' => msgs($c['id'], (int)($in['since'] ?? 0))]);
  }
  case 'contact': {   // visitor leaves (or changes) an email / Discord username so Keiko can reach them outside the website
    $c = visitor_conv($in);
    rate_limit('contact:' . client_ip(), 10, 3600);
    $email = clean((string)($in['email'] ?? ''), 120); $rawDc = trim((string)($in['discord'] ?? ''));
    if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) fail(400, 'Please check your email address.');
    $dc = clean_discord($rawDc); if ($rawDc !== '' && $dc === '') fail(400, 'Please check your Discord username.');
    if ($email === '' && $dc === '') fail(400, 'Please enter your email or Discord username.');
    $now = time(); $db = db();
    $db->prepare('UPDATE conversations SET email = ?, discord = ?, updated = ?, unread_admin = unread_admin + 1 WHERE id = ?')->execute([$email ?: (string)$c['email'], $dc ?: (string)($c['discord'] ?? ''), $now, $c['id']]);
    $db->prepare('INSERT INTO messages(conv_id, sender, body, created) VALUES(?,?,?,?)')->execute([$c['id'], 'visitor', '📇 Contact: ' . implode(' · ', array_filter([$email ? "email $email" : '', $dc ? "Discord $dc" : ''])), $now]);
    $st = $db->prepare('SELECT * FROM conversations WHERE id = ?'); $st->execute([$c['id']]); $c2 = $st->fetch(); $c2['last_ping'] = 0;
    discord_ping($cfg, $c2, '📇 Left contact details: ' . implode(' · ', array_filter([$email, $dc ? "Discord $dc" : ''])), false);
    out(200, ['email' => $c2['email'], 'discord' => $c2['discord'], 'messages' => msgs($c['id'], (int)($in['since'] ?? 0))]);
  }
  case 'poll': {
    $c = visitor_conv($in);
    if (!empty($in['open'])) db()->prepare('UPDATE conversations SET unread_visitor = 0 WHERE id = ?')->execute([$c['id']]);
    out(200, ['messages' => msgs($c['id'], (int)($in['since'] ?? 0)), 'unread' => empty($in['open']) ? (int)$c['unread_visitor'] : 0, 'status' => $c['status'], 'has_contact' => ($c['email'] ?? '') !== '' || ($c['discord'] ?? '') !== '']);
  }

  /* ===== admin ===== */
  case 'login': {
    $pw = admin_pw($cfg);
    if (strlen($pw) < 8) fail(503, 'Admin password not set. Add chat_admin_password (8+ characters) to keikoarts-config.php.');
    $k = 'login:' . client_ip(); $db = db(); $now = time();
    $st = $db->prepare('SELECT COUNT(*) FROM hits WHERE k = ? AND t > ?'); $st->execute([hash('sha256', $k), $now - 600]);
    if ((int)$st->fetchColumn() >= 10) fail(429, 'Too many wrong attempts. Please wait 10 minutes and try again.');
    usleep(300000);
    if (!admin_pw_ok($cfg, trim((string)($in['password'] ?? '')))) {
      $db->prepare('INSERT INTO hits(k,t) VALUES(?,?)')->execute([hash('sha256', $k), $now]);
      fail(401, 'Wrong password.');
    }
    out(200, ['token' => make_token($cfg)]);
  }
  case 'reset_request': {   // "Forgot password?": a one-time link (30 min) goes to Keiko's Discord and email
    rate_limit('reset:' . client_ip(), 3, 3600); rate_limit('reset:all', 8, 3600);
    $tok = bin2hex(random_bytes(24));
    $s = ka_settings(); $s['reset_hash'] = hash('sha256', $tok); $s['reset_exp'] = time() + 1800;
    if (!ka_save_settings($s)) fail(500, 'Could not create a reset link right now. Please try again later.');
    $link = 'https://keikoartist.com/admin/#reset=' . $tok;
    $sent = [];
    $hook = ka_hook($cfg);
    if ($hook && ka_post_json($hook, ['username' => 'KeikoArts Admin', 'allowed_mentions' => ['parse' => []], 'embeds' => [[
        'title' => '🔑 Admin password reset', 'color' => 0xF2628F,
        'description' => "Someone asked to reset the admin password on keikoartist.com.\n\n**[Tap here to set a new password]($link)**\n\nThe link works once, for 30 minutes. If this was not you, just ignore this message.",
      ]]]) < 300) $sent[] = 'discord';
    $mc = ka_post_json('https://formsubmit.co/ajax/keikoarts22@gmail.com', ['_subject' => 'KeikoArts admin: reset your password', '_template' => 'box', '_captcha' => 'false',
      'Message' => "Someone asked to reset the admin password on keikoartist.com. Open this link to set a new password (works once, for 30 minutes):", 'Reset link' => $link,
      'Not you?' => 'Just ignore this email. Your password stays the same.'], ['Origin: https://keikoartist.com', 'Referer: https://keikoartist.com/admin/']);
    if ($mc >= 200 && $mc < 300) $sent[] = 'email';
    if (!$sent) fail(502, 'The reset link could not be sent. Please try again in a few minutes.');
    out(200, ['sent' => $sent]);
  }
  case 'reset_set': {
    rate_limit('resetset:' . client_ip(), 10, 3600);
    $tok = (string)($in['token'] ?? ''); $new = (string)($in['password'] ?? '');
    $s = ka_settings();
    if (!preg_match('/^[a-f0-9]{48}$/', $tok) || empty($s['reset_hash']) || (int)($s['reset_exp'] ?? 0) < time() || !hash_equals((string)$s['reset_hash'], hash('sha256', $tok)))
      fail(400, 'This reset link has expired or was already used. Please tap "Forgot password?" again.');
    if (mb_strlen(trim($new)) < 8 || mb_strlen($new) > 200) fail(400, 'Please use at least 8 characters.');
    $s['admin_pw_hash'] = password_hash(trim($new), PASSWORD_DEFAULT); unset($s['reset_hash'], $s['reset_exp']); $s['admin_pw_changed'] = time();
    if (!ka_save_settings($s)) fail(500, 'Could not save the new password. Please try again.');
    $hook = ka_hook($cfg);
    if ($hook) ka_post_json($hook, ['username' => 'KeikoArts Admin', 'allowed_mentions' => ['parse' => []], 'embeds' => [['title' => '✅ Admin password changed', 'color' => 0x1D9A55, 'description' => 'The admin password for keikoartist.com/admin was just changed. Other devices need to log in again.']]]);
    out(200, ['token' => make_token($cfg)]);
  }
  case 'me': { require_admin($cfg); out(200); }
  case 'logout': { out(200); }
  case 'list': {
    require_admin($cfg);
    $status = ($in['status'] ?? 'open') === 'closed' ? 'closed' : 'open';
    $st = db()->prepare('SELECT c.id, c.name, c.email, c.page, c.status, c.created, c.updated, c.unread_admin,
        (SELECT body FROM messages m WHERE m.conv_id = c.id ORDER BY m.id DESC LIMIT 1) AS last,
        (SELECT sender FROM messages m WHERE m.conv_id = c.id ORDER BY m.id DESC LIMIT 1) AS last_sender
      FROM conversations c WHERE c.status = ? ORDER BY c.updated DESC LIMIT 200');
    $st->execute([$status]);
    $tot = (int)db()->query('SELECT COALESCE(SUM(unread_admin),0) FROM conversations WHERE status = \'open\'')->fetchColumn();
    $rows = array_map(function ($r) { $r['unread_admin'] = (int)$r['unread_admin']; $r['created'] = (int)$r['created']; $r['updated'] = (int)$r['updated']; return $r; }, $st->fetchAll());
    out(200, ['conversations' => $rows, 'unread_total' => $tot]);
  }
  case 'thread': {
    require_admin($cfg);
    $id = (string)($in['id'] ?? ''); if (!preg_match('/^[a-f0-9]{24}$/', $id)) fail(400, 'bad id');
    db()->prepare('UPDATE conversations SET unread_admin = 0, remind_n = 0 WHERE id = ?')->execute([$id]);
    $st = db()->prepare('SELECT id, name, email, discord, page, status, created FROM conversations WHERE id = ?'); $st->execute([$id]);
    $c = $st->fetch(); if (!$c) fail(404, 'not found');
    $ks = ka_settings();
    out(200, ['conversation' => $c, 'messages' => msgs($id, (int)($in['since'] ?? 0)), 'mail_ready' => !empty($ks['gmail_user']) && !empty($ks['gmail_pass'])]);
  }
  case 'reply': {
    require_admin($cfg);
    $id = (string)($in['id'] ?? ''); if (!preg_match('/^[a-f0-9]{24}$/', $id)) fail(400, 'bad id');
    $text = clean((string)($in['message'] ?? ''), MAX_MSG); if ($text === '') fail(400, 'empty');
    $agent = clean((string)($in['agent'] ?? ''), 30) ?: 'Keiko';
    $now = time(); $db = db();
    $db->prepare('INSERT INTO messages(conv_id, sender, agent, body, created) VALUES(?,?,?,?,?)')->execute([$id, 'admin', $agent, $text, $now]);
    $db->prepare('UPDATE conversations SET updated = ?, unread_visitor = unread_visitor + 1, unread_admin = 0, remind_n = 0 WHERE id = ?')->execute([$now, $id]);
    $emailed = false;
    $st = $db->prepare('SELECT name, email FROM conversations WHERE id = ?'); $st->execute([$id]); $cv = $st->fetch();
    if ($cv && ($cv['email'] ?? '') !== '' && empty($in['no_email'])) {
      $nm = (string)($cv['name'] ?: 'there'); if (preg_match('/^Visitor [0-9A-F]{4}$/', $nm)) $nm = 'there';
      $link = 'https://keikoartist.com/#chat';
      $emailed = chat_mail((string)$cv['email'], "$agent from KeikoArts replied to your message",
        "Hi $nm,\n\n$agent replied to your chat on keikoartist.com:\n\n$text\n\nJust reply to this email, or continue the chat on the website (same device): $link\n\nKeikoArts",
        '<div style="font-family:Arial,sans-serif;color:#7a2846;font-size:14px;line-height:1.55"><p>Hi ' . htmlspecialchars($nm) . ',</p><p>' . htmlspecialchars($agent) . ' replied to your chat on keikoartist.com:</p>'
        . '<blockquote style="margin:12px 0;padding:10px 14px;background:#fff0f5;border-left:3px solid #f2628f;border-radius:6px">' . nl2br(htmlspecialchars($text)) . '</blockquote>'
        . '<p>Just reply to this email, or <a href="' . $link . '">continue the chat on the website</a>.</p><p>KeikoArts</p></div>');
    }
    out(200, ['messages' => msgs($id, (int)($in['since'] ?? 0)), 'emailed' => $emailed]);
  }
  case 'close': case 'reopen': {
    require_admin($cfg);
    $id = (string)($in['id'] ?? ''); if (!preg_match('/^[a-f0-9]{24}$/', $id)) fail(400, 'bad id');
    db()->prepare('UPDATE conversations SET status = ?, unread_admin = 0, remind_n = 0 WHERE id = ?')->execute([$action === 'close' ? 'closed' : 'open', $id]);
    out(200);
  }
  case 'delete': {
    require_admin($cfg);
    $id = (string)($in['id'] ?? ''); if (!preg_match('/^[a-f0-9]{24}$/', $id)) fail(400, 'bad id');
    db()->prepare('DELETE FROM conversations WHERE id = ?')->execute([$id]);
    out(200);
  }
  case 'delete_many': {   // admin: delete several chats at once (ticked in the list)
    require_admin($cfg);
    $ids = array_values(array_unique(array_filter((array)($in['ids'] ?? []), function ($x) { return is_string($x) && preg_match('/^[a-f0-9]{24}$/', $x); })));
    if (!$ids || count($ids) > 200) fail(400, 'Nothing selected');
    $db = db(); $db->beginTransaction(); $del = $db->prepare('DELETE FROM conversations WHERE id = ?'); $n = 0;
    foreach ($ids as $x) { $del->execute([$x]); $n += $del->rowCount(); }
    $db->commit();
    out(200, ['deleted' => $n]);
  }
  default: fail(400, 'unknown action');
}
} catch (Throwable $e) {
  error_log('chat-api: ' . $e->getMessage());
  fail(500, 'Server error, please try again.');
}
