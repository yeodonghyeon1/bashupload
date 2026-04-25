#!/usr/bin/env python3
"""bashupload - stdlib-only file upload/download server.

Run: python3 server.py [port]
Default port: 16261

Uses only Python3 standard library (no pip/apt installs needed).
"""
import os
import re
import sys
import json
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 16261
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')
HASH_INDEX = os.path.join(UPLOAD_DIR, '.hashes.json')

ALLOWED_EXTS = {
    '',  # extensionless files (e.g. Dockerfile, Makefile, raw dumps)
    # text / config / source
    '.log', '.txt', '.md', '.json', '.csv', '.tsv',
    '.yaml', '.yml', '.ini', '.conf', '.cfg', '.toml',
    '.sh', '.py', '.js', '.ts', '.html', '.xml',
    # images
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg', '.ico',
    # audio
    '.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.opus',
    # video
    '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v',
}
MAX_SIZE = 200 * 1024 * 1024  # 200MB
SAFE_NAME_RE = re.compile(r'^[A-Za-z0-9._\-]+$')

os.makedirs(UPLOAD_DIR, exist_ok=True)


def load_hashes():
    if not os.path.exists(HASH_INDEX):
        return {}
    try:
        with open(HASH_INDEX, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def save_hashes(h):
    tmp = HASH_INDEX + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(h, f, indent=2, ensure_ascii=False)
    os.replace(tmp, HASH_INDEX)


def reconcile_hashes():
    """Rebuild hash index from actual files if missing/stale."""
    hashes = load_hashes()
    actual_files = {
        f for f in os.listdir(UPLOAD_DIR)
        if not f.startswith('.') and os.path.isfile(os.path.join(UPLOAD_DIR, f))
    }
    indexed = set(hashes.values())
    missing = actual_files - indexed
    if missing:
        for name in missing:
            fp = os.path.join(UPLOAD_DIR, name)
            h = hashlib.sha256()
            with open(fp, 'rb') as f:
                for chunk in iter(lambda: f.read(64 * 1024), b''):
                    h.update(chunk)
            hashes[h.hexdigest()] = name
    stale = [d for d, n in hashes.items() if n not in actual_files]
    for d in stale:
        hashes.pop(d, None)
    if missing or stale:
        save_hashes(hashes)
    return hashes


def safe_name(name):
    if not name or not SAFE_NAME_RE.match(name):
        return None
    if name.startswith('.') or name.startswith('-'):
        return None
    return name


class Handler(BaseHTTPRequestHandler):
    server_version = 'bashupload/1.0'

    def log_message(self, fmt, *args):
        sys.stderr.write(f"[{self.log_date_time_string()}] {self.address_string()} - {fmt % args}\n")

    def _send(self, code, body, ctype='text/plain; charset=utf-8'):
        body_b = body.encode('utf-8') if isinstance(body, str) else body
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(body_b)))
        self.send_header('Connection', 'close')
        self.end_headers()
        try:
            self.wfile.write(body_b)
        except BrokenPipeError:
            pass

    # ------- GET: list or download -------
    def do_GET(self):
        path = unquote(self.path.lstrip('/'))

        if path in ('', 'list', 'index', 'index.html'):
            files = sorted(
                f for f in os.listdir(UPLOAD_DIR)
                if not f.startswith('.') and os.path.isfile(os.path.join(UPLOAD_DIR, f))
            )
            if not files:
                self._send(200, '(empty)\n')
                return
            lines = []
            for f in files:
                size = os.path.getsize(os.path.join(UPLOAD_DIR, f))
                lines.append(f'{size:>12}  {f}')
            self._send(200, '\n'.join(lines) + '\n')
            return

        if path in ('health', 'ping'):
            self._send(200, 'ok\n')
            return

        if path in ('help', 'usage'):
            host = self.headers.get('Host', f'HOST:{PORT}')
            self._send(200, (
                f'bashupload - pure curl usage\n\n'
                f'  upload:   curl -T FILE http://{host}/\n'
                f'  download: curl -O http://{host}/FILE\n'
                f'  list:     curl http://{host}/\n'
                f'  help:     curl http://{host}/help\n\n'
                f'same file (by name or content) is rejected with HTTP 409.\n'
                f'allowed extensions: {sorted(ALLOWED_EXTS)}\n'
            ))
            return

        name = safe_name(path)
        if not name:
            self._send(400, 'Invalid filename\n')
            return
        fp = os.path.join(UPLOAD_DIR, name)
        if not os.path.isfile(fp):
            self._send(404, f'Not found: {name}\n')
            return

        size = os.path.getsize(fp)
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Length', str(size))
        self.send_header('Content-Disposition', f'attachment; filename="{name}"')
        self.send_header('Connection', 'close')
        self.end_headers()
        try:
            with open(fp, 'rb') as f:
                while True:
                    chunk = f.read(64 * 1024)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except BrokenPipeError:
            pass

    # ------- PUT: upload -------
    def do_PUT(self):
        path = unquote(self.path.lstrip('/'))
        name = safe_name(path)
        if not name:
            self._send(400, 'Invalid filename (use: curl -T file URL/)\n')
            return
        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_EXTS:
            self._send(
                400,
                f'Extension "{ext}" not allowed.\nAllowed: {sorted(ALLOWED_EXTS)}\n',
            )
            return

        cl = self.headers.get('Content-Length')
        if cl is None:
            self._send(411, 'Content-Length required (chunked uploads not supported)\n')
            return
        try:
            length = int(cl)
        except ValueError:
            self._send(400, 'Invalid Content-Length\n')
            return
        if length < 0:
            self._send(400, 'Invalid Content-Length\n')
            return
        if length > MAX_SIZE:
            self._send(413, f'File too large (max {MAX_SIZE} bytes)\n')
            return

        final = os.path.join(UPLOAD_DIR, name)
        if os.path.exists(final):
            self._send(409, f'Duplicate filename: "{name}" already exists on the server\n')
            # drain request body so curl sees the response cleanly
            self._drain(length)
            return

        tmp = os.path.join(UPLOAD_DIR, f'.tmp.{os.getpid()}.{name}')
        h = hashlib.sha256()
        remaining = length
        try:
            with open(tmp, 'wb') as f:
                while remaining > 0:
                    chunk = self.rfile.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    h.update(chunk)
                    remaining -= len(chunk)
            if remaining != 0:
                raise IOError('short read')

            digest = h.hexdigest()
            hashes = reconcile_hashes()
            # Skip content-dedup for empty files - every 0-byte file hashes the same.
            if length > 0 and digest in hashes:
                existing = hashes[digest]
                os.remove(tmp)
                self._send(409, f'Duplicate content: identical file already exists as "{existing}"\n')
                return

            os.rename(tmp, final)
            if length > 0:
                hashes[digest] = name
                save_hashes(hashes)
            self._send(201, f'Uploaded: {name} ({length} bytes, sha256:{digest[:16]}...)\n')
        except Exception as e:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            self._send(500, f'Upload failed: {e}\n')

    def do_POST(self):
        # Convenience alias. curl -T uses PUT by default; POST kept for custom clients.
        self.do_PUT()

    def do_DELETE(self):
        self._send(405, 'Delete not allowed\n')

    def _drain(self, length):
        remaining = length
        while remaining > 0:
            chunk = self.rfile.read(min(64 * 1024, remaining))
            if not chunk:
                break
            remaining -= len(chunk)


def main():
    reconcile_hashes()
    server = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f'bashupload listening on 0.0.0.0:{PORT}')
    print(f'storage: {UPLOAD_DIR}')
    print(f'allowed extensions: {sorted(ALLOWED_EXTS)}')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nshutting down')
        server.shutdown()


if __name__ == '__main__':
    main()
