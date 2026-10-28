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

const MAX_MSG = 2000;
const MAX_NAME = 60;

function out(int $code, array $data = []): void { http_response_code($code); echo json_encode($data + ['ok' => $code === 200], JSON_UNESCAPED_UNICODE); exit; }
function fail(int $code, string $msg): void { out($code, ['error' => $msg]); }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') fail(405, 'POST only');
$host = preg_replace('/:\d+$/', '', strtolower($_SERVER['HTTP_HOST'] ?? ''));
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin && strtolower((string)parse_url($origin, PHP_URL_HOST)) !== $host) fail(403, 'bad origin');

$cfgFile = __DIR__ . '/keikoarts-config.php';
$cfg = is_file($cfgFile) ? (include $cfgFile) : [];
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
  $st->execute([$conv, $since]); return $st->fetchAll();
}
function discord_ping(array $cfg, array $c, string $text, bool $isNew): void {
  $hook = $cfg['discord_webhook'] ?? '';
  if (!preg_match('#^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$#', $hook) || !function_exists('curl_init')) return;
  $now = time();
  if (!$isNew && $now - (int)$c['last_ping'] < 120) return;                 // don't spam: max 1 ping / 2 min per chat
  db()->prepare('UPDATE conversations SET last_ping = ? WHERE id = ?')->execute([$now, $c['id']]);
  $safe = fn($s) => str_replace(['@everyone', '@here'], ["@\u{200B}everyone", "@\u{200B}here"], $s);
  $payload = ['username' => 'KeikoArts Chat', 'allowed_mentions' => ['parse' => []], 'embeds' => [[
    'title' => ($isNew ? '💬 New chat from ' : '💬 New message from ') . $safe($c['name'] ?: 'Visitor'),
    'description' => $safe(mb_substr($text, 0, 500)),
    'color' => 0xF2628F,
    'fields' => array_values(array_filter([$c['email'] ? ['name' => 'Email', 'value' => $safe($c['email']), 'inline' => true] : null])),
    'footer' => ['text' => 'Reply at keikoartist.com/admin'],
  ]]];
  $ch = curl_init($hook);
  curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($payload), CURLOPT_HTTPHEADER => ['Content-Type: application/json'], CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 4]);
  curl_exec($ch); curl_close($ch);
}

/* ---------- admin auth (stateless signed token, no PHP sessions needed) ---------- */
function admin_pw(array $cfg): string { return trim((string)($cfg['chat_admin_password'] ?? '')); }
function admin_key(array $cfg): string { return hash_hmac('sha256', 'keikoarts-admin-v1', admin_pw($cfg)); }
function make_token(array $cfg): string { $exp = time() + 60 * 60 * 24 * 14; return $exp . '.' . hash_hmac('sha256', (string)$exp, admin_key($cfg)); }
function require_admin(array $cfg): void {
  if (strlen(admin_pw($cfg)) < 8) fail(401, 'login required');
  $t = (string)($_SERVER['HTTP_X_AUTH'] ?? '');
  if (!preg_match('/^(\d{10})\.([a-f0-9]{64})$/', $t, $m)) fail(401, 'login required');
  if ((int)$m[1] < time() || !hash_equals(hash_hmac('sha256', $m[1], admin_key($cfg)), $m[2])) fail(401, 'login required');
}

/* ---------- router ---------- */
$raw = file_get_contents('php://input', false, null, 0, 20000) ?: '';
$in = json_decode($raw, true);
if (!is_array($in)) fail(400, 'bad json');
$action = (string)($in['action'] ?? '');

try {
switch ($action) {

  /* ===== visitor ===== */
  case 'start': {
    if (!empty($in['_honey'])) out(200, ['id' => str_repeat('0', 24), 'token' => str_repeat('0', 40)]);
    rate_limit('start:' . client_ip(), 5, 3600);
    $name = clean((string)($in['name'] ?? ''), MAX_NAME);
    $email = clean((string)($in['email'] ?? ''), 120);
    $text = clean((string)($in['message'] ?? ''), MAX_MSG);
    if ($text === '') fail(400, 'Please type a message.');
    if ($name === '') $name = 'Visitor ' . strtoupper(substr(bin2hex(random_bytes(2)), 0, 4));
    if ($email !== '' && !filter_var($email, FILTER_VALIDATE_EMAIL)) fail(400, 'Please check your email address.');
    $id = bin2hex(random_bytes(12)); $tok = bin2hex(random_bytes(24)); $now = time();
    $db = db(); $db->beginTransaction();
    $db->prepare('INSERT INTO conversations(id, token_hash, name, email, page, created, updated, unread_admin) VALUES(?,?,?,?,?,?,?,1)')
       ->execute([$id, hash('sha256', $tok), $name, $email, clean((string)($in['page'] ?? ''), 200), $now, $now]);
    $db->prepare('INSERT INTO messages(conv_id, sender, body, created) VALUES(?,?,?,?)')->execute([$id, 'visitor', $text, $now]);
    $db->commit();
    $st = $db->prepare('SELECT * FROM conversations WHERE id = ?'); $st->execute([$id]);
    discord_ping($cfg, $st->fetch(), $text, true);
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
    out(200, ['messages' => msgs($c['id'], (int)($in['since'] ?? 0))]);
  }
  case 'poll': {
    $c = visitor_conv($in);
    if (!empty($in['open'])) db()->prepare('UPDATE conversations SET unread_visitor = 0 WHERE id = ?')->execute([$c['id']]);
    out(200, ['messages' => msgs($c['id'], (int)($in['since'] ?? 0)), 'unread' => empty($in['open']) ? (int)$c['unread_visitor'] : 0, 'status' => $c['status']]);
  }

  /* ===== admin ===== */
  case 'login': {
    $pw = admin_pw($cfg);
    if (strlen($pw) < 8) fail(503, 'Admin password not set. Add chat_admin_password (8+ characters) to keikoarts-config.php.');
    $k = 'login:' . client_ip(); $db = db(); $now = time();
    $st = $db->prepare('SELECT COUNT(*) FROM hits WHERE k = ? AND t > ?'); $st->execute([hash('sha256', $k), $now - 600]);
    if ((int)$st->fetchColumn() >= 10) fail(429, 'Too many wrong attempts. Please wait 10 minutes and try again.');
    usleep(300000);
    if (!hash_equals(hash('sha256', $pw), hash('sha256', trim((string)($in['password'] ?? ''))))) {
      $db->prepare('INSERT INTO hits(k,t) VALUES(?,?)')->execute([hash('sha256', $k), $now]);
      fail(401, 'Wrong password.');
    }
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
    out(200, ['conversations' => $st->fetchAll(), 'unread_total' => $tot]);
  }
  case 'thread': {
    require_admin($cfg);
    $id = (string)($in['id'] ?? ''); if (!preg_match('/^[a-f0-9]{24}$/', $id)) fail(400, 'bad id');
    db()->prepare('UPDATE conversations SET unread_admin = 0 WHERE id = ?')->execute([$id]);
    $st = db()->prepare('SELECT id, name, email, page, status, created FROM conversations WHERE id = ?'); $st->execute([$id]);
    $c = $st->fetch(); if (!$c) fail(404, 'not found');
    out(200, ['conversation' => $c, 'messages' => msgs($id, (int)($in['since'] ?? 0))]);
  }
  case 'reply': {
    require_admin($cfg);
    $id = (string)($in['id'] ?? ''); if (!preg_match('/^[a-f0-9]{24}$/', $id)) fail(400, 'bad id');
    $text = clean((string)($in['message'] ?? ''), MAX_MSG); if ($text === '') fail(400, 'empty');
    $agent = clean((string)($in['agent'] ?? ''), 30) ?: 'Keiko';
    $now = time(); $db = db();
    $db->prepare('INSERT INTO messages(conv_id, sender, agent, body, created) VALUES(?,?,?,?,?)')->execute([$id, 'admin', $agent, $text, $now]);
    $db->prepare('UPDATE conversations SET updated = ?, unread_visitor = unread_visitor + 1, unread_admin = 0 WHERE id = ?')->execute([$now, $id]);
    out(200, ['messages' => msgs($id, (int)($in['since'] ?? 0))]);
  }
  case 'close': case 'reopen': {
    require_admin($cfg);
    $id = (string)($in['id'] ?? ''); if (!preg_match('/^[a-f0-9]{24}$/', $id)) fail(400, 'bad id');
    db()->prepare('UPDATE conversations SET status = ?, unread_admin = 0 WHERE id = ?')->execute([$action === 'close' ? 'closed' : 'open', $id]);
    out(200);
  }
  case 'delete': {
    require_admin($cfg);
    $id = (string)($in['id'] ?? ''); if (!preg_match('/^[a-f0-9]{24}$/', $id)) fail(400, 'bad id');
    db()->prepare('DELETE FROM conversations WHERE id = ?')->execute([$id]);
    out(200);
  }
  default: fail(400, 'unknown action');
}
} catch (Throwable $e) {
  error_log('chat-api: ' . $e->getMessage());
  fail(500, 'Server error, please try again.');
}
