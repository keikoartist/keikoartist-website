<?php
// Christmas spin wheel: the server draws the prize and the claim code, keeps a record and posts it to Discord,
// so Keiko can check every code a visitor claims. Prize order must match GIFTS in index.html.
header('Content-Type: application/json');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

const GIFTS = ['Free emotes', 'Free Christmas badges', 'Free source files', 'Free skeb (surprise-me art)', 'Free sketch', '10% off your next commission'];
const WEIGHTS = [19, 19, 19, 5, 19, 19];   // skeb is rare: 5 in 100 spins (owner, Nov 2026); the others share the rest
const SEASON_END = '2027-01-07';

function out($code, $data) { http_response_code($code); echo json_encode($data); exit; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(405, ['ok' => false, 'msg' => 'POST only']);
if (time() >= strtotime(SEASON_END . ' 00:00:00 Asia/Jakarta')) out(410, ['ok' => false, 'msg' => 'season over']);

$host = preg_replace('/:\d+$/', '', strtolower($_SERVER['HTTP_HOST'] ?? ''));
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin && strtolower((string)parse_url($origin, PHP_URL_HOST)) !== $host) out(403, ['ok' => false, 'msg' => 'bad origin']);

// rate limit: 3 spins / 10 min per IP
require_once __DIR__ . '/real-ip.php';
$ip = ka_real_ip();
$rl = sys_get_temp_dir() . '/ka_spin_' . md5($ip);
$hits = array_filter(json_decode(@file_get_contents($rl) ?: '[]', true) ?: [], fn($t) => $t > time() - 600);
if (count($hits) >= 3) out(429, ['ok' => false, 'msg' => 'too many']);
$hits[] = time(); @file_put_contents($rl, json_encode(array_values($hits)));

$r = random_int(1, array_sum(WEIGHTS)); $g = 0;
foreach (WEIGHTS as $i => $w) { if ($r <= $w) { $g = $i; break; } $r -= $w; }
$alpha = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'; $c = '';
for ($i = 0; $i < 5; $i++) $c .= $alpha[random_int(0, strlen($alpha) - 1)];
$code = 'XMAS-' . $c;
$visitor = substr(hash('sha256', 'keikoarts-spin|' . $ip), 0, 6);   // short visitor tag, not the IP itself

// record on the server (outside the public folder when possible)
$dir = dirname(__DIR__, 2) . '/keikoarts-data';
if (!is_dir($dir)) @mkdir($dir, 0700, true);   // same folder as order-api.php data_dir()
if (!is_dir($dir) || !is_writable($dir)) $dir = __DIR__ . '/chat-data';
if (is_dir($dir) && is_writable($dir)) {
  @file_put_contents($dir . '/spins.csv', gmdate('c') . ",$code," . GIFTS[$g] . ",$visitor\n", FILE_APPEND | LOCK_EX);
}

// Discord (same webhook as orders); a failure never blocks the visitor
$cfgFile = __DIR__ . '/keikoarts-config.php';
ob_start(); $cfg = is_file($cfgFile) ? (include $cfgFile) : []; ob_end_clean();
if (!is_array($cfg)) $cfg = [];
$hook = (string)($cfg['discord_webhook'] ?? '');
if ($hook === '') {
  foreach ([dirname(__DIR__, 2) . '/keikoarts-data/settings.json', __DIR__ . '/chat-data/settings.json'] as $sf) {
    $st = json_decode((string)@file_get_contents($sf), true);
    if (is_array($st) && !empty($st['discord_webhook'])) { $hook = (string)$st['discord_webhook']; break; }
  }
}
if (function_exists('curl_init') && preg_match('#^https://(?:ptb\.|canary\.)?(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$#', $hook)) {
  $payload = ['username' => 'KeikoArts Spin Wheel', 'allowed_mentions' => ['parse' => []],
    'embeds' => [['title' => '🎡 Spin wheel: ' . GIFTS[$g], 'description' => "Code **$code** · visitor `$visitor`",
      'color' => 0xF2628F, 'footer' => ['text' => 'keikoartist.com'], 'timestamp' => gmdate('c')]]];
  $ch = curl_init($hook);
  curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($payload),
    CURLOPT_HTTPHEADER => ['Content-Type: application/json'], CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 5]);
  curl_exec($ch); curl_close($ch);
}

out(200, ['ok' => true, 'g' => $g, 'c' => $code]);
