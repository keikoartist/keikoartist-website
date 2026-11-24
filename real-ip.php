<?php
// The visitor's real IP for rate limits and spam checks. Behind Cloudflare every request comes from a Cloudflare
// server, so the visitor's IP is in the CF-Connecting-IP header; that header is trusted ONLY when the request really
// comes from Cloudflare's published IP ranges (cloudflare.com/ips), so it cannot be faked. Without Cloudflare nothing changes.
if (realpath((string)($_SERVER['SCRIPT_FILENAME'] ?? '')) === __FILE__) { http_response_code(404); exit; }

function ka_ip_in(string $ip, string $cidr): bool {
  [$net, $bits] = explode('/', $cidr); $a = @inet_pton($ip); $b = @inet_pton($net);
  if ($a === false || $b === false || strlen($a) !== strlen($b)) return false;
  $bits = (int)$bits; $bytes = intdiv($bits, 8); $rest = $bits % 8;
  if (substr($a, 0, $bytes) !== substr($b, 0, $bytes)) return false;
  if ($rest === 0) return true;
  $mask = chr((0xFF << (8 - $rest)) & 0xFF);
  return (($a[$bytes] & $mask) === ($b[$bytes] & $mask));
}

function ka_real_ip(): string {
  $remote = (string)($_SERVER['REMOTE_ADDR'] ?? '0');
  $cf = trim((string)($_SERVER['HTTP_CF_CONNECTING_IP'] ?? ''));
  if ($cf === '' || !filter_var($cf, FILTER_VALIDATE_IP)) return $remote;
  static $ranges = ['173.245.48.0/20', '103.21.244.0/22', '103.22.200.0/22', '103.31.4.0/22', '141.101.64.0/18', '108.162.192.0/18',
    '190.93.240.0/20', '188.114.96.0/20', '197.234.240.0/22', '198.41.128.0/17', '162.158.0.0/15', '104.16.0.0/13', '104.24.0.0/14',
    '172.64.0.0/13', '131.0.72.0/22', '2400:cb00::/32', '2606:4700::/32', '2803:f800::/32', '2405:b500::/32', '2405:8100::/32',
    '2a06:98c0::/29', '2c0f:f248::/32'];
  foreach ($ranges as $r) if (ka_ip_in($remote, $r)) return $cf;
  return $remote;
}
