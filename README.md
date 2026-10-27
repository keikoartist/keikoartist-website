# keikoartist.com

Website commission KeikoArts (single page, static HTML).

- `index.html` — seluruh website. Harga & layanan: cari `const SERVICES`, contoh karya: `GALLERY`, deskripsi: `DETAILS`, VTuber Children: `VTUBERS`.
- `images/` — semua gambar & video.
- Antrian: Google Sheets (isi `SHEET_CSV` di index.html setelah sheet di-publish ke web).
- Form order → keikoarts22@gmail.com via FormSubmit.

## Deploy
Push ke `main` → GitHub Actions upload via FTP ke Rumahweb (`public_html/keikoartist.com`).
Secrets: FTP_SERVER, FTP_USERNAME, FTP_PASSWORD, FTP_DIR.

## Catatan hosting
- `index.php` WordPress di-rename jadi `index-wp.php`; `.htaccess` diawali `DirectoryIndex index.html index.php index-wp.php` dan `CacheLookup off`.
- Kembali ke WordPress: rename `index-wp.php` → `index.php` dan hapus baris DirectoryIndex.
