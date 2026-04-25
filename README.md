# bashupload

A single-port file upload/download service. The server runs on **Python 3
standard library only** (no `apt`/`pip` install required), and the client is
just a one-liner using the standard `curl` shipped with every Linux box (no
need to edit `bashrc` or `source` any script).

## Files

- `server.py` — HTTP server (stdlib only)
- `start.sh` — launcher (`./start.sh [port]`, default 16261)
- `uploads/` — storage (auto-created, with `.hashes.json` content-hash index)

## Run the server

The simplest way — works on any OS, run Python directly:

```bash
python server.py            # port 16261
python server.py 18080      # custom port
```

Or use the launcher scripts:

```bash
# Linux / macOS
./start.sh              # port 16261
./start.sh 18080

# Windows (cmd / PowerShell)
start.bat               # port 16261
start.bat 18080
```

Don't run `./start.sh` in PowerShell — Windows can't execute `.sh` and will
pop up an "Open with..." dialog. On Windows, use `start.bat` or
`python server.py`.

To run in the background, use `systemd` / `nohup` / `tmux` / a Windows
service, etc.

## Client usage (plain curl)

Pass a single file as the argument:

```bash
# Upload — append "/" to the URL so curl auto-appends the filename to the path
curl -T app.log http://HOST:16261/

# Download
curl -O http://HOST:16261/app.log

# List files
curl http://HOST:16261/

# Show usage
curl http://HOST:16261/help
```

If you use it often, a one-line alias in `.bashrc` is enough (optional):

```bash
alias bashup='curl -T'   # usage: bashup app.log http://HOST:16261/
```

## Duplicate handling

Every uploaded file is hashed with SHA-256. The server returns HTTP 409 in
either of these cases:

- A file with the same name already exists, **or**
- A file with the same content (hash) already exists, even under a
  different name

The response body explains which condition triggered the rejection and
which existing file it conflicts with.

## Allowed file types

`.log .txt .md .json .csv .tsv .yaml .yml .ini .conf .cfg .toml .sh .py .js .ts .html .xml`

Edit `ALLOWED_EXTS` in `server.py` to change this list. Maximum upload
size: 200 MB (`MAX_SIZE`).

## Security notes

- Filenames are restricted to `[A-Za-z0-9._-]+` and may not start with `.`
  or `-` — this blocks path traversal and hidden-file tricks.
- The extension whitelist blocks executable binaries from being uploaded
  (`.sh`/`.py` are included for convenience; remove them from the list if
  you don't want scripts on the server).
- No authentication. If you expose the service to the internet, restrict
  access via VPN, firewall, or a reverse proxy.
- `DELETE` is disabled. To delete files, manipulate `uploads/` directly on
  the host.
