<?php
// Sends each new commission request to Keiko's Discord channel (via webhook).
// The webhook URL lives in keikoarts-config.php on the server (NOT in GitHub):
//   <?php return ['discord_webhook' => 'https://discord.com/api/webhooks/...'];
header('Content-Type: application/json');
header('X-Content-Type-Options: nosniff');

function out($code, $msg) { http_response_code($code); echo json_encode(['ok' => $code === 200, 'msg' => $msg]); exit; }

if ($_SERVER['REQUEST_METHOD'] !== 'POST') out(405, 'POST only');

$host = preg_replace('/:\d+$/', '', strtolower($_SERVER['HTTP_HOST'] ?? ''));
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin && strtolower((string)parse_url($origin, PHP_URL_HOST)) !== $host) out(403, 'bad origin');

$cfgFile = __DIR__ . '/keikoarts-config.php';
if (!is_file($cfgFile)) out(200, 'not configured');
$cfg = include $cfgFile;
$hook = $cfg['discord_webhook'] ?? '';
if (!preg_match('#^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$#', $hook)) out(200, 'webhook not set');

// simple rate limit: 5 requests / 10 min per IP
$ip = $_SERVER['REMOTE_ADDR'] ?? '0';
$rl = sys_get_temp_dir() . '/ka_rl_' . md5($ip);
$hits = array_filter(json_decode(@file_get_contents($rl) ?: '[]', true) ?: [], fn($t) => $t > time() - 600);
if (count($hits) >= 5) out(429, 'too many');
$hits[] = time(); @file_put_contents($rl, json_encode(array_values($hits)));

$raw = file_get_contents('php://input', false, null, 0, 20000);
$d = json_decode($raw, true);
if (!is_array($d)) out(400, 'bad json');
if (!empty($d['_honey'])) out(200, 'ok');

function clean($v, $max = 300) {
  $v = is_string($v) ? $v : '';
  $v = trim(preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F]/u', '', $v));
  $v = str_replace(['@everyone', '@here'], ["@\u{200B}everyone", "@\u{200B}here"], $v);
  return mb_substr($v, 0, $max);
}
$f = [];
foreach (['id','due','service','package','addons','total','plan','name','email','discord','deadline','refs','details'] as $k) $f[$k] = clean($d[$k] ?? '', $k === 'details' ? 1000 : 300);
if (!$f['name'] || !$f['service']) out(400, 'missing');

$field = fn($n, $v, $in = true) => ['name' => $n, 'value' => $v !== '' ? $v : '-', 'inline' => $in];
$payload = [
  'username' => 'KeikoArts Orders',
  'allowed_mentions' => ['parse' => []],
  'embeds' => [[
    'title' => "🎀 New request {$f['id']}",
    'description' => $f['details'] ?: '-',
    'color' => 0xF2628F,
    'fields' => [
      $field('Service', $f['service'] . ($f['package'] ? " — {$f['package']}" : '')),
      $field('Estimated total', $f['total']),
      $field('Payment plan', $f['plan']),
      $field('Due now', $f['due']),
      $field('Client', $f['name']),
      $field('Discord', $f['discord']),
      $field('Email', $f['email']),
      $field('Add-ons', $f['addons'], false),
      $field('Deadline', $f['deadline']),
      $field('References', $f['refs'], false),
    ],
    'footer' => ['text' => 'keikoartist.com'],
    'timestamp' => gmdate('c'),
  ]],
];

$ch = curl_init($hook);
curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($payload),
  CURLOPT_HTTPHEADER => ['Content-Type: application/json'], CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 8]);
curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
out($code >= 200 && $code < 300 ? 200 : 502, 'sent ' . $code);
