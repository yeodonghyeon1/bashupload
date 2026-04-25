# bashupload

단일 포트 파일 업로드/다운로드 서비스. **apt 설치 없이** Python3 기본
라이브러리만으로 서버가 돌아가고, 클라이언트는 리눅스 기본 `curl` 한 줄이면
충분합니다 (bashrc 수정·스크립트 source 불필요).

## Files

- `server.py` — HTTP 서버 (stdlib only)
- `start.sh` — 실행기 (`./start.sh [port]`, 기본 16261)
- `uploads/` — 저장소 (자동 생성, `.hashes.json` 내용 해시 인덱스)

## Run the server

제일 간단한 방법 — OS 상관없이 Python 직접 실행:

```bash
python server.py            # 포트 16261
python server.py 18080      # 다른 포트
```

런처 스크립트도 있음:

```bash
# Linux / macOS
./start.sh              # 포트 16261
./start.sh 18080

# Windows (cmd / PowerShell)
start.bat               # 포트 16261
start.bat 18080
```

PowerShell에서 `./start.sh` 치지 말기 — Windows는 `.sh`를 실행 못 해서 "뭘로
열까요" 창이 뜹니다. Windows에선 `start.bat` 또는 `python server.py`.

백그라운드로 돌리려면 systemd / nohup / tmux / Windows 서비스 등 사용.

## Client usage (순수 curl)

파일 하나만 인자로 넘기는 형태:
IP: 112.160.106.139
```bash
# 업로드 — URL 끝에 / 를 붙이면 curl이 파일명을 자동으로 경로에 붙여줍니다
curl -T app.log http://HOST:16261/

# 다운로드
curl -O http://HOST:16261/app.log

# 목록
curl http://HOST:16261/

# 사용법 확인
curl http://HOST:16261/help
```

자주 쓴다면 `.bashrc`에 한 줄 alias면 충분 (선택):

```bash
alias bashup='curl -T'   # 사용: bashup app.log http://HOST:16261/
```

## Duplicate handling

업로드된 모든 파일은 SHA-256 해시로 체크됩니다. 아래 두 경우 HTTP 409로 거부:

- 같은 이름의 파일이 이미 서버에 있음, **또는**
- 이름은 달라도 내용(해시)이 동일한 파일이 이미 있음

응답 본문에 어떤 이유인지, 기존 파일 이름이 무엇인지 표시됩니다.

## Allowed file types

`.log .txt .md .json .csv .tsv .yaml .yml .ini .conf .cfg .toml .sh .py .js .ts .html .xml`

`server.py`의 `ALLOWED_EXTS`에서 수정. 최대 업로드 크기: 200 MB (`MAX_SIZE`).

## Security notes

- 파일명은 `[A-Za-z0-9._-]+` 만 허용, `.` 또는 `-` 시작 금지 — 경로 탈출, 히든
  파일 우회 차단.
- 확장자 화이트리스트로 실행 바이너리 업로드 차단 (`.sh`/`.py`는 편의상 포함,
  서버에 스크립트를 올리기 싫으면 목록에서 제거).
- 인증 없음. 인터넷 노출 시 VPN / 방화벽 / 리버스 프록시로 접근 제한 권장.
- `DELETE`는 비활성화. 삭제는 호스트에서 `uploads/` 직접 조작.
