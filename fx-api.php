<?php
// Exchange rate USD → the visitor's currency, for the "≈ Rp …" line under the order total (approximate; invoices are always USD).
// Fetched by the server (ECB rates from frankfurter, open.er-api.com as backup) and cached for 12 hours in keikoarts-data/fx.json.
header('Content-Type: application/json');
header('X-Content-Type-Options: nosniff');
header('Cache-Control: public, max-age=3600');

$cur = strtoupper((string)($_GET['c'] ?? ''));
$ok = ['IDR','EUR','GBP','JPY','PHP','MYR','SGD','AUD','CAD','BRL','MXN','KRW','INR','THB','NZD','CHF','SEK','NOK','DKK','PLN','CZK','HUF','TRY','ZAR','HKD','CNY'];
if (!in_array($cur, $ok, true)) { http_response_code(400); echo '{"ok":false}'; exit; }

$dir = dirname(__DIR__, 2) . '/keikoarts-data';
if (!is_dir($dir) || !is_writable($dir)) $dir = __DIR__ . '/chat-data';
$file = "$dir/fx.json";
$c = json_decode((string)@file_get_contents($file), true);
if (!is_array($c) || empty($c['rates']) || time() - (int)($c['t'] ?? 0) > 43200) {
  $get = function (string $url) {
    if (!function_exists('curl_init')) return null;
    $ch = curl_init($url);
    curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => 5, CURLOPT_FOLLOWLOCATION => true, CURLOPT_USERAGENT => 'keikoartist.com rates']);
    $r = curl_exec($ch); $code = curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
    $j = $code === 200 ? json_decode((string)$r, true) : null;
    return is_array($j) ? $j : null;
  };
  $rates = null;
  $j = $get('https://api.frankfurter.app/latest?from=USD');
  if ($j && !empty($j['rates'])) $rates = $j['rates'];
  if (!$rates) { $j = $get('https://open.er-api.com/v6/latest/USD'); if ($j && !empty($j['rates'])) $rates = $j['rates']; }
  if ($rates) { $c = ['t' => time(), 'rates' => array_intersect_key($rates, array_flip($ok))]; @file_put_contents($file, json_encode($c)); }
}
$v = (float)($c['rates'][$cur] ?? 0);
if ($v <= 0) { http_response_code(503); echo '{"ok":false}'; exit; }
echo json_encode(['ok' => true, 'cur' => $cur, 'rate' => $v, 't' => (int)$c['t']]);
