<?php
// Simple visit counter for keikoartist.com: no cookies, no third parties, the IP is never stored.
// The browser sends a small beacon (page view, order form opened, order sent, spin).
// Once a day the first request posts yesterday's summary to Keiko's Discord (same webhook as orders).
header('Content-Type: application/json');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

function done($code = 204) { http_response_code($code); exit; }
if ($_SERVER['REQUEST_METHOD'] !== 'POST') done(405);

$host = preg_replace('/:\d+$/', '', strtolower($_SERVER['HTTP_HOST'] ?? ''));
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin && strtolower((string)parse_url($origin, PHP_URL_HOST)) !== $host) done(403);

$ua = (string)($_SERVER['HTTP_USER_AGENT'] ?? '');
if ($ua === '' || preg_match('/bot|crawl|spider|slurp|preview|lighthouse|headless|playwright|curl|wget|python|monitor/i', $ua)) done();

$ip = $_SERVER['REMOTE_ADDR'] ?? '0';
$rl = sys_get_temp_dir() . '/ka_stat_' . md5($ip);
$hits = array_filter(json_decode(@file_get_contents($rl) ?: '[]', true) ?: [], fn($t) => $t > time() - 600);
if (count($hits) >= 120) done(429);
$hits[] = time(); @file_put_contents($rl, json_encode(array_values($hits)));

$in = json_decode((string)file_get_contents('php://input', false, null, 0, 2000), true);
if (!is_array($in)) done(400);
$ev = (string)($in['e'] ?? '');
if (!in_array($ev, ['view', 'order_open', 'order_sent', 'spin'], true)) done(400);
$page = substr(preg_replace('#[^a-z0-9/_-]#', '', strtolower((string)($in['p'] ?? '/'))), 0, 60) ?: '/';
$src = strtolower(trim((string)($in['s'] ?? '')));
$src = substr(preg_replace('/^www\./', '', preg_replace('/[^a-z0-9.\-]/', '', $src)), 0, 40) ?: 'direct';
foreach (['t.co' => 'x.com', 'twitter.com' => 'x.com', 'm.facebook.com' => 'facebook.com', 'l.instagram.com' => 'instagram.com', 'out.reddit.com' => 'reddit.com', 'old.reddit.com' => 'reddit.com'] as $a => $b) if ($src === $a) $src = $b;
if (preg_match('/(^|\.)google\./', $src)) $src = 'google';

$tz = new DateTimeZone('Asia/Jakarta');
$today = (new DateTime('now', $tz))->format('Y-m-d');
$dir = dirname(__DIR__, 2) . '/keikoarts-data';
if (!is_dir($dir) || !is_writable($dir)) $dir = __DIR__ . '/chat-data';
if (!is_dir($dir) || !is_writable($dir)) done();
$sd = $dir . '/stats'; if (!is_dir($sd)) @mkdir($sd, 0700);
if (!is_dir($sd)) done();

// one visitor = same IP + browser on the same day (hashed with a daily salt, never stored raw)
$vid = substr(hash('sha256', $today . '|keikoarts|' . $ip . '|' . $ua), 0, 12);

$f = "$sd/$today.json";
$fp = @fopen($f, 'c+'); if (!$fp) done();
flock($fp, LOCK_EX);
$d = json_decode(stream_get_contents($fp) ?: '', true);
if (!is_array($d)) $d = ['views' => 0, 'visitors' => [], 'order_open' => 0, 'order_sent' => 0, 'spin' => 0, 'sources' => [], 'pages' => []];
if ($ev === 'view') {
  $d['views']++;
  if (!isset($d['visitors'][$vid])) { $d['visitors'][$vid] = 1; $d['sources'][$src] = ($d['sources'][$src] ?? 0) + 1; }
  $d['pages'][$page] = ($d['pages'][$page] ?? 0) + 1;
} else {
  $d[$ev] = ($d[$ev] ?? 0) + 1;
}
ftruncate($fp, 0); rewind($fp); fwrite($fp, json_encode($d)); fflush($fp); flock($fp, LOCK_UN); fclose($fp);

// daily summary of yesterday, posted once
$yday = (new DateTime('yesterday', $tz))->format('Y-m-d');
$mark = "$sd/summary-sent.txt";
if (trim((string)@file_get_contents($mark)) !== $yday && is_file("$sd/$yday.json")) {
  @file_put_contents($mark, $yday);
  $y = json_decode((string)@file_get_contents("$sd/$yday.json"), true) ?: [];
  $y += ['visitors' => [], 'sources' => [], 'pages' => []];
  arsort($y['sources']); arsort($y['pages']);
  $top = fn($a) => implode(' · ', array_map(fn($k, $v) => "$k $v", array_keys(array_slice($a, 0, 5, true)), array_slice($a, 0, 5, true))) ?: '-';
  $cfgFile = __DIR__ . '/keikoarts-config.php';
  ob_start(); $cfg = is_file($cfgFile) ? (include $cfgFile) : []; ob_end_clean();
  $hook = is_array($cfg) ? (string)($cfg['discord_webhook'] ?? '') : '';
  if ($hook === '') foreach ([dirname(__DIR__, 2) . '/keikoarts-data/settings.json', __DIR__ . '/chat-data/settings.json'] as $sf) {
    $st = json_decode((string)@file_get_contents($sf), true);
    if (is_array($st) && !empty($st['discord_webhook'])) { $hook = (string)$st['discord_webhook']; break; }
  }
  if (function_exists('curl_init') && preg_match('#^https://(?:ptb\.|canary\.)?(?:discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$#', $hook)) {
    $day = (new DateTime($yday, $tz))->format('j M');
    $payload = ['username' => 'KeikoArts Stats', 'allowed_mentions' => ['parse' => []], 'embeds' => [[
      'title' => "📊 Website yesterday ($day)", 'color' => 0xF2628F,
      'description' => '**' . count($y['visitors'] ?? []) . '** visitors · ' . (int)($y['views'] ?? 0) . ' page views'
        . "\nOrder form opened **" . (int)($y['order_open'] ?? 0) . '** · orders sent **' . (int)($y['order_sent'] ?? 0) . '** · spins ' . (int)($y['spin'] ?? 0)
        . "\n\n**Where visitors came from:** " . $top($y['sources'] ?? [])
        . "\n**Top pages:** " . $top($y['pages'] ?? []),
      'footer' => ['text' => 'keikoartist.com · no cookies'], 'timestamp' => gmdate('c')]]];
    $ch = curl_init($hook);
    curl_setopt_array($ch, [CURLOPT_POST => true, CURLOPT_POSTFIELDS => json_encode($payload),
      CURLOPT_HTTPHEADER => ['Content-Type: application/json'], CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 5]);
    curl_exec($ch); curl_close($ch);
  }
}
done();
