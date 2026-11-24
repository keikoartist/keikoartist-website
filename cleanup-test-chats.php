<?php
// One-time cleanup (24 Nov 2026): removes ONLY the two test chats Claude created by mistake while checking the live site
// (email exactly a@example.com, started on 24 Nov 2026 between 14:00 and 15:00 WIB). Touches nothing else.
header('Content-Type: application/json');
header('Cache-Control: no-store');
$dir = dirname(__DIR__, 2) . '/keikoarts-data';
if (!is_dir($dir)) $dir = __DIR__ . '/chat-data';
$f = "$dir/chat.sqlite";
if (!is_file($f)) { echo '{"deleted":0}'; exit; }
$db = new PDO('sqlite:' . $f, null, null, [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]);
$db->exec('PRAGMA foreign_keys=ON; PRAGMA busy_timeout=4000;');
$from = strtotime('2026-11-24 14:00:00 +0700'); $to = strtotime('2026-11-24 15:00:00 +0700');
$st = $db->prepare("SELECT id FROM conversations WHERE email = 'a@example.com' AND created BETWEEN ? AND ?");
$st->execute([$from, $to]); $ids = $st->fetchAll(PDO::FETCH_COLUMN);
foreach ($ids as $id) {
  $db->prepare('DELETE FROM messages WHERE conv_id = ?')->execute([$id]);
  $db->prepare('DELETE FROM conversations WHERE id = ?')->execute([$id]);
}
echo json_encode(['deleted' => count($ids)]);
