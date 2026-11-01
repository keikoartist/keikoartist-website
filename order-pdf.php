<?php
/*
 * Builds the order PDF (order brief + invoice + how to pay) that is posted to Keiko's Discord.
 * Included by order-api.php only.
 */
if (!defined('KA_API')) { http_response_code(404); exit; }
if (!defined('FPDF_FONTPATH')) define('FPDF_FONTPATH', __DIR__ . '/lib/fpdf/font/');
require_once __DIR__ . '/lib/fpdf/fpdf.php';

const KA_KOFI = 'https://ko-fi.com/keikoarts';
const KA_DOT  = "\xB7";   // middle dot in the PDF font encoding

/* UTF-8 -> the PDF font encoding (Windows-1252). Emoji are dropped, other unsupported letters become "?". */
function ka_pdf_txt($s, &$lost = null): string {
  $s = (string)$s;
  if (preg_match('/^[\x09\x0A\x0D\x20-\x7E]*$/', $s)) return $s;
  $s = preg_replace('/[\x{1F000}-\x{1FAFF}\x{2600}-\x{27BF}\x{2B00}-\x{2BFF}\x{FE00}-\x{FE0F}\x{200B}-\x{200D}\x{2060}\x{E0000}-\x{E007F}]/u', '', $s) ?? '';
  $s = strtr($s, ["\u{00A0}" => ' ', "\u{2009}" => ' ', "\u{202F}" => ' ', "\u{2011}" => '-', "\u{2012}" => '-', "\u{2212}" => '-', "\u{2192}" => '->', "\u{2190}" => '<-', "\u{2605}" => '*', "\u{2606}" => '*']);
  $out = '';
  foreach (preg_split('//u', $s, -1, PREG_SPLIT_NO_EMPTY) ?: [] as $ch) {
    $c = @iconv('UTF-8', 'windows-1252', $ch);
    if ($c === false || $c === '') {
      $c = @iconv('UTF-8', 'windows-1252//TRANSLIT', $ch);
      if ($c === false || $c === '' || strpos($c, '?') !== false) { $c = '?'; $lost = true; }
    }
    $out .= $c;
  }
  return $out;
}
function ka_money($n): string { $n = round((float)$n, 2); return ($n < 0 ? '-' : '') . '$' . number_format(abs($n), 2); }

class KAPDF extends FPDF {
  public $docId = '';
  function SetPad($mm) { $this->cMargin = $mm; }
  function Footer() {
    $this->SetY(-13);
    $this->SetFont('Helvetica', '', 8);
    $this->SetTextColor(168, 96, 122);
    $this->Cell(0, 5, 'KeikoArts  ' . KA_DOT . '  keikoartist.com  ' . KA_DOT . '  ' . $this->docId . '  ' . KA_DOT . '  page ' . $this->PageNo() . ' of {nb}', 0, 0, 'C');
  }
}

/* $o = a row of the orders table. $newTotal: optional final price agreed with the client (adds an adjustment line). */
function ka_order_pdf(array $o, $newTotal = null): string {
  $f      = json_decode((string)($o['fields'] ?? ''), true) ?: [];
  $files  = json_decode((string)($o['files'] ?? ''), true) ?: [];
  $custom = ($o['kind'] ?? '') === 'custom';
  $id     = (string)($o['id'] ?? '');
  $total  = round((float)($o['total'] ?? 0), 2);
  $plan   = $custom ? 'Full payment' : ((string)($o['plan'] ?? '') ?: 'Full payment');
  $lines  = json_decode((string)($o['lines'] ?? ''), true);
  if (!is_array($lines) || !$lines) {
    $lines = $custom
      ? [['Custom commission (' . ($f['Usage'] ?? 'Personal') . ' use)', (float)($o['price'] ?? 0)], ['Tax (13%)', (float)($o['tax'] ?? 0)]]
      : [[trim(($o['service'] ?? '') . ' - ' . ($o['package'] ?? ''), ' -'), $total]];
  }
  if ($newTotal !== null && abs((float)$newTotal - $total) >= 0.005) {
    $lines[] = ['Adjustment (final price agreed together)', round((float)$newTotal - $total, 2)];
    $total = round((float)$newTotal, 2);
  }
  $k   = $custom ? 1 : (strpos($plan, '50/50') !== false ? 0.5 : (preg_match('/3x|3×/iu', $plan) ? 1 / 3 : 1));
  $due = $total > 0 ? ceil(round($total * $k * 100, 6)) / 100 : 0.0;
  $planLbl = $k == 0.5 ? '50% deposit' : ($k < 0.5 ? '1st of 3 installments' : 'full payment');
  $created = (int)($o['created'] ?? 0) ?: time();
  $lost = false;
  $T = function ($s) use (&$lost) { return ka_pdf_txt($s, $lost); };

  $pdf = new KAPDF('P', 'mm', 'A4');
  $pdf->docId = $T($id);
  $pdf->SetMargins(16, 14, 16);
  $pdf->SetAutoPageBreak(true, 18);
  $pdf->AliasNbPages();
  $pdf->SetTitle('KeikoArts invoice ' . $id, true);
  $pdf->SetAuthor('KeikoArts', true);
  $pdf->SetCreator('keikoartist.com', true);
  $pdf->AddPage();
  $pink = [242, 98, 143]; $ink = [122, 40, 70]; $muted = [168, 96, 122]; $line = [251, 211, 224];
  $color = function ($c) use ($pdf) { $pdf->SetTextColor($c[0], $c[1], $c[2]); };

  // ---- header ----
  $pdf->SetFillColor(255, 240, 246); $pdf->Rect(0, 0, 210, 34, 'F');
  $pdf->SetFillColor($pink[0], $pink[1], $pink[2]); $pdf->Rect(0, 34, 210, 1.2, 'F');
  $pdf->SetXY(16, 8); $pdf->SetFont('Helvetica', 'B', 24); $color($pink); $pdf->Cell(100, 11, 'KeikoArts');
  $pdf->SetXY(16, 19.5); $pdf->SetFont('Helvetica', '', 9.5); $color($muted); $pdf->Cell(100, 5, 'Illustration & Live2D Studio');
  $pdf->SetXY(16, 24.5); $pdf->Cell(100, 5, 'keikoartist.com  ' . KA_DOT . '  keikoarts22@gmail.com');
  $pdf->SetXY(104, 8); $pdf->SetFont('Helvetica', 'B', 20); $color($ink); $pdf->Cell(90, 11, 'INVOICE', 0, 0, 'R');
  $pdf->SetXY(104, 19.5); $pdf->SetFont('Helvetica', '', 9.5); $color($muted); $pdf->Cell(90, 5, 'No. ' . $T($id), 0, 0, 'R');
  $pdf->SetXY(104, 24.5); $pdf->Cell(90, 5, 'Date: ' . date('M j, Y', $created), 0, 0, 'R');

  // ---- billed to + amount due ----
  $y = 42;
  $pdf->SetXY(16, $y); $pdf->SetFont('Helvetica', 'B', 8); $color($muted); $pdf->Cell(90, 4, 'BILLED TO');
  $pdf->SetXY(16, $y + 5); $pdf->SetFont('Helvetica', 'B', 12.5); $color($ink); $pdf->MultiCell(96, 6, $T(($o['name'] ?? '') ?: 'Client'), 0, 'L');
  $pdf->SetFont('Helvetica', '', 9.5); $color($muted);
  if (($o['discord'] ?? '') !== '') { $pdf->SetX(16); $pdf->Cell(96, 5, 'Discord: ' . $T($o['discord']), 0, 1); }
  if (($o['email'] ?? '') !== '')   { $pdf->SetX(16); $pdf->Cell(96, 5, 'Email: ' . $T($o['email']), 0, 1); }
  $leftEnd = $pdf->GetY();
  $pdf->SetFillColor(255, 244, 248); $pdf->SetDrawColor($line[0], $line[1], $line[2]); $pdf->SetLineWidth(0.4);
  $pdf->Rect(120, $y - 2, 74, 26, 'DF');
  $pdf->SetXY(124, $y + 1); $pdf->SetFont('Helvetica', 'B', 8); $color($muted); $pdf->Cell(66, 4, $due < $total ? 'AMOUNT DUE NOW' : 'TOTAL DUE');
  $pdf->SetXY(124, $y + 6); $pdf->SetFont('Helvetica', 'B', 20); $color($pink); $pdf->Cell(66, 10, ka_money($due) . ' USD');
  $pdf->SetXY(124, $y + 16.5); $pdf->SetFont('Helvetica', '', 8.5); $color($muted); $pdf->Cell(66, 4, 'Pay via Ko-fi  ' . KA_DOT . '  ' . $planLbl);
  $pdf->SetY(max($leftEnd, $y + 24) + 1);

  $section = function ($n, $title, $need = 30) use ($pdf, $color, $pink, $ink, $line) {
    if ($pdf->GetY() + $need > 279) $pdf->AddPage();
    $pdf->Ln(2.5);
    $pdf->SetX(16); $pdf->SetFont('Helvetica', 'B', 12); $color($pink); $pdf->Cell(7, 6.5, $n);
    $color($ink); $pdf->Cell(0, 6.5, $title, 0, 1);
    $pdf->SetDrawColor($line[0], $line[1], $line[2]); $pdf->SetLineWidth(0.4);
    $pdf->Line(16, $pdf->GetY() + 0.6, 194, $pdf->GetY() + 0.6); $pdf->Ln(2.4);
  };
  $kv = function ($k, $v) use ($pdf, $color, $muted, $ink, $T) {
    $v = trim($T($v)); if ($v === '' || $v === '-') return;
    if ($pdf->GetY() + 7 > 279) $pdf->AddPage();
    $y = $pdf->GetY();
    $pdf->SetXY(16, $y); $pdf->SetFont('Helvetica', '', 9.5); $color($muted); $pdf->Cell(42, 5.4, $k);
    $pdf->SetXY(58, $y); $pdf->SetFont('Helvetica', 'B', 9.5); $color($ink); $pdf->MultiCell(136, 5.4, $v, 0, 'L');
  };

  // ---- 1. brief ----
  $section('1', 'Order brief (scope of work)');
  $kv('Service', ($o['service'] ?? '') ?: 'Custom Inquiry');
  if (!$custom) $kv('Package', $o['package'] ?? '');
  if (!$custom && (int)($f['Quantity'] ?? 1) > 1) $kv('Quantity', $f['Quantity']);
  if (!$custom) $kv('Add-ons', $f['Add-ons'] ?? '');
  if ($custom) $kv('Usage', ($f['Usage'] ?? 'Personal') . ' use');
  $dl = (string)($f['Deadline'] ?? '');
  if (preg_match('/^\d{4}-\d{2}-\d{2}$/', $dl)) { $ts = strtotime($dl); if ($ts) $dl = date('M j, Y', $ts); }
  $kv('Deadline', $dl !== '' ? $dl : 'No deadline');
  $kv('Payment plan', $plan);
  $shown = ['Name', 'Discord', 'Email', 'Details', 'Service', 'Package', 'Quantity', 'Add-ons', 'Usage', 'Deadline', 'Payment plan', 'Reference links', 'budget', 'Budget'];
  foreach ($f as $key => $val) if (!in_array($key, $shown, true) && is_string($val)) $kv((string)$key, $val);
  if (!empty($f['Reference links'])) $kv('Reference links', preg_replace('/\s+/', ' ', (string)$f['Reference links']));
  if ($files) {
    $names = array_map(function ($x) { return preg_replace('/^\d+-/', '', (string)($x['name'] ?? '')); }, $files);
    $kv('Reference files', count($files) . ' file(s): ' . implode(', ', $names));
  }
  $details = trim((string)($f['Details'] ?? ''));
  if ($details !== '') {
    $pdf->Ln(2);
    if ($pdf->GetY() + 18 > 277) $pdf->AddPage();
    $pdf->SetX(16); $pdf->SetFont('Helvetica', 'B', 8); $color($muted); $pdf->Cell(0, 5, 'DETAILS', 0, 1);
    $pdf->SetFillColor(255, 249, 251); $pdf->SetDrawColor($line[0], $line[1], $line[2]); $pdf->SetLineWidth(0.3);
    $pdf->SetFont('Helvetica', '', 10); $pdf->SetTextColor(70, 32, 50);
    $pdf->SetX(16); $pdf->Cell(178, 2.2, '', 'LTR', 1, 'L', true);
    $pdf->SetPad(3); $pdf->SetX(16); $pdf->MultiCell(178, 5.4, $T($details), 'LR', 'L', true); $pdf->SetPad(1);
    $pdf->SetX(16); $pdf->Cell(178, 2.2, '', 'LBR', 1, 'L', true);
  }

  // ---- 2. invoice ----
  $section('2', 'Invoice', 34);
  $pdf->SetFillColor(255, 240, 246); $pdf->SetFont('Helvetica', 'B', 8.5); $color($muted);
  $pdf->SetX(16); $pdf->Cell(140, 7, '  DESCRIPTION', 0, 0, 'L', true); $pdf->Cell(38, 7, 'AMOUNT  ', 0, 1, 'R', true);
  foreach ($lines as $l) {
    if (!is_array($l) || count($l) < 2) continue;
    if ($pdf->GetY() + 8 > 277) $pdf->AddPage();
    $y = $pdf->GetY();
    $pdf->SetXY(16, $y + 0.7); $pdf->SetFont('Helvetica', '', 10); $color($ink); $pdf->MultiCell(138, 6, ' ' . $T($l[0]), 0, 'L');
    $y2 = max($pdf->GetY(), $y + 6.7) + 0.7;
    $pdf->SetXY(156, $y + 0.7); $pdf->Cell(38, 6, (float)$l[1] == 0.0 ? 'Free' : ka_money($l[1]), 0, 0, 'R');
    $pdf->SetDrawColor(253, 233, 240); $pdf->Line(16, $y2, 194, $y2); $pdf->SetY($y2);
  }
  $tot = function ($label, $amount, $big = false) use ($pdf, $color, $pink, $ink, $muted) {
    $pdf->SetX(16);
    $pdf->SetFont('Helvetica', 'B', $big ? 12 : 10); $color($big ? $ink : $muted); $pdf->Cell(140, $big ? 9 : 7, $label, 0, 0, 'R');
    $color($big ? $pink : $ink); $pdf->Cell(38, $big ? 9 : 7, $amount, 0, 1, 'R');
  };
  $pdf->Ln(1);
  $tot('Total (USD)', ka_money($total), true);
  if ($due < $total) {
    $tot('Due now ' . KA_DOT . ' ' . $planLbl, ka_money($due));
    $tot($k < 0.5 ? 'Remaining (2 more installments)' : 'Remaining (before final files)', ka_money($total - $due));
  }

  // ---- 3. how to pay ----
  $section('3', 'How to pay', 70);   // keeps the payment box, terms and thank-you on one page
  $y = $pdf->GetY();
  $pdf->SetFillColor(255, 244, 248); $pdf->SetDrawColor($pink[0], $pink[1], $pink[2]); $pdf->SetLineWidth(0.5);
  $pdf->Rect(16, $y, 178, 30, 'DF');
  $pdf->SetXY(21, $y + 3); $pdf->SetFont('Helvetica', 'B', 11); $color($ink); $pdf->Cell(0, 6, 'Pay via Ko-fi', 0, 1);
  $pdf->SetFont('Helvetica', '', 10);
  $pdf->SetX(21); $color($ink); $pdf->Cell(5, 6, '1.'); $pdf->Cell($pdf->GetStringWidth('Open') + 2.6, 6, 'Open'); $pdf->SetFont('Helvetica', 'BU', 10); $color($pink);
  $pdf->Cell(40, 6, 'ko-fi.com/keikoarts', 0, 1, 'L', false, KA_KOFI);
  $pdf->SetFont('Helvetica', '', 10); $color($ink);
  $pdf->SetX(21); $pdf->Cell(5, 6, '2.'); $pdf->Cell(0, 6, 'Send ' . ka_money($due) . ' USD' . ($due < $total ? ' (' . $planLbl . ')' : ''), 0, 1);
  $pdf->SetX(21); $pdf->Cell(5, 6, '3.'); $pdf->Cell(0, 6, 'Write your invoice number ' . $T($id) . ' in the Ko-fi message', 0, 1);
  $pdf->SetY($y + 32);
  $pdf->SetX(16); $pdf->SetFont('Helvetica', '', 8.8); $color($muted);
  $pdf->MultiCell(178, 4.6, "Your slot is secured once the payment is received. Full refund if I can't take your commission. "
    . 'By paying you agree to the Terms of Service at keikoartist.com/#tos.', 0, 'L');
  if ($lost) { $pdf->Ln(1); $pdf->SetX(16); $pdf->SetFont('Helvetica', 'I', 8); $pdf->MultiCell(178, 4.2, 'Some characters (for example non-Latin text) cannot be shown in this PDF and appear as "?".', 0, 'L'); }
  $pdf->Ln(3);
  $pdf->SetX(16); $pdf->SetFont('Helvetica', 'B', 11); $color($pink); $pdf->Cell(178, 6, 'Thank you for choosing KeikoArts!', 0, 1, 'C');

  return $pdf->Output('S');
}
