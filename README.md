# bashupload

A single-port file upload/download service. The server runs on **Python 3
standard library only** (no `apt`/`pip` install required), and the client is
just a one-liner using the standard `curl` shipped with every Linux box (no
need to edit `bashrc` or `source` any script).

## Why this exists

Designed for **minimal terminal-only environments** — boxes where you have
a shell and `curl`, but:

- **no GUI** (so a web upload page is useless — the user can't see it),
- **no `apt`/`pip`/install rights** (so you can't pull in `scp` servers,
  `rsync` daemons, MinIO, syncthing, or any third-party uploader).

The tool is built only one assumption that are almost always true on
a fresh Linux system:

- `curl` is already installed → the client needs no install, no shell
  functions, no aliases, no script `source`-ing.

That's why the client is one line of plain `curl` and the server is a
single `.py` file. If those constraints don't apply to you (you have a
browser, you can install packages, you have admin rights), a normal web
file server is probably a better fit.

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

## Network setup

### Local network (LAN)

No setup needed. Run the server, then point clients at the host's LAN
IP — they just need to be on the same network (same Wi-Fi, same office
LAN, etc.).

```bash
# on the server:
python server.py

# from any machine in the same network:
curl -T file.log http://192.168.x.y:16261/
```

Find the server's LAN IP with `ip a` / `ifconfig` / `ipconfig`.

### External network (internet)

The server host must have a **stable, externally-reachable address**.
Two common ways:

- **Port forwarding on your router.** Open the chosen port (e.g. 16261)
  in the router's admin panel and forward it to the server machine's
  LAN IP. Works with consumer ISPs that hand out a routable IPv4. Since
  consumer IPs are usually dynamic, pair this with a DDNS service (e.g.
  DuckDNS) so you don't have to re-share the IP whenever it changes.
- **Run on a host with a static public IP.** A cloud VM (AWS / GCP /
  any cheap VPS) or an office server on a fixed-line connection
  already has a permanent public address — no router config needed.
  Just make sure the cloud firewall / security group allows inbound
  TCP on your port.

Either way, **read the security notes below before exposing the service
to the open internet** — there is no built-in authentication.

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

- A file with the same name already exists
  → `Duplicate filename: "<name>" already exists on the server`
- A file with the same content (hash) already exists, even under a
  different name
  → `Duplicate content: identical file already exists as "<existing>"`

The response body always names the existing file that caused the conflict.

## Allowed file types

- **No extension** — files without an extension (e.g. `Dockerfile`,
  `Makefile`, raw dumps) are allowed
- **Text / config / source**: `.log .txt .md .json .csv .tsv .yaml .yml
  .ini .conf .cfg .toml .sh .py .js .ts .html .xml`
- **Images**: `.jpg .jpeg .png .gif .webp .bmp .svg .ico`
- **Audio**: `.mp3 .wav .flac .ogg .m4a .aac .opus`
- **Video**: `.mp4 .mov .avi .mkv .webm .m4v`

Edit `ALLOWED_EXTS` in `server.py` to change this list. Maximum upload
size: 1 GB (`MAX_SIZE`).

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
