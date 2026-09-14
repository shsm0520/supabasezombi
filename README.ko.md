# SupabaseZombi

Supabase 데이터베이스를 좀비처럼 계속 살려두는 서비스입니다. 🧟‍♂️

## 특징

- 24시간마다 자동으로 실행
- 매번 랜덤 1~10개 데이터 삽입
- 50개 넘으면 자동 정리 (30개로 유지)
- 여러 Supabase 데이터베이스 지원
- Docker 컨테이너로 실행
- 텔레그램 알림 지원 (선택 사항)

## 빠른 시작

```bash
# 1. 저장소 복제
git clone https://github.com/shsm0520/supabasezombi.git
cd supabasezombi

# 2. 예제에서 config.json 생성
cp config.json.example config.json
# config.json 파일을 열어 Supabase 정보 입력

# 3. (선택) 커스텀 설정 파일 생성
cp docker-compose.override.yml.example docker-compose.override.yml
# docker-compose.override.yml 파일을 수정하여 원하는 설정 입력

# 4. 서비스 시작
docker-compose up -d
```

## 설정

### 1. 저장소 복제

```bash
git clone https://github.com/shsm0520/supabasezombi.git
cd supabasezombi
```

### 2. Supabase 설정

예제 템플릿에서 `config.json` 생성:

```bash
cp config.json.example config.json
```

그리고 `config.json` 파일을 수정하여 데이터베이스 정보 입력:

```json
[
  {
    "name": "Database 1",
    "supabase_url": "https://your-project.supabase.co",
    "supabase_key": "your-anon-key",
    "table_name": "keep-alive"
  },
  {
    "name": "Database 2",
    "supabase_url": "https://another-project.supabase.co",
    "supabase_key_env": "SUPABASE_KEY_2",
    "table_name": "keep-alive"
  }
]
```

> **참고**: `config.json`은 보안을 위해 Git에서 제외됩니다. 항상 `config.json.example`을 템플릿으로 사용하세요.

### 3. (선택) 텔레그램 알림 및 설정 커스터마이징

예제에서 `docker-compose.override.yml` 생성:

```bash
cp docker-compose.override.yml.example docker-compose.override.yml
```

그리고 `docker-compose.override.yml`에서 필요한 설정의 주석을 해제하고 값을 수정:

```yaml
version: "3.8"

services:
  supabasezombi:
    environment:
      # 텔레그램 알림
      - TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
      - TELEGRAM_CHAT_ID=123456789
      # 실행 설정 커스터마이징
      - RUN_INTERVAL_HOURS=24
      - RANDOM_INSERT_MIN=1
      - RANDOM_INSERT_MAX=10
      - MAX_DATA_LIMIT=50
      - TARGET_DATA_COUNT=30
```

> **참고**: `docker-compose.override.yml`은 Git에서 제외되므로 업데이트 시 설정이 보존됩니다.

## 실행 방법

### Docker Compose 사용 (권장)

```bash
# 서비스 시작 (빌드 없이 바로 실행!)
docker-compose up -d

# 로그 확인
docker-compose logs -f supabasezombi

# 서비스 중지
docker-compose down

# 변경 후 재시작
docker-compose restart
```

### Docker 직접 사용 (대안)

```bash
# 먼저 복제
git clone https://github.com/shsm0520/supabasezombi.git
cd supabasezombi

# config.json 수정 후 실행
docker run -d \
  --name supabasezombi \
  --restart unless-stopped \
  -w /app \
  -v $(pwd)/main_standalone.py:/app/main.py:ro \
  -v $(pwd)/config.json:/app/config.json:ro \
  -e TZ=Asia/Seoul \
  python:3.11-slim \
  sh -c "pip install --no-cache-dir supabase requests && python -u main.py"

# 로그 확인
docker logs -f supabasezombi

# 컨테이너 중지
docker stop supabasezombi
docker rm supabasezombi
```

### Python 직접 실행 (로컬 개발)

```bash
# 저장소 복제
git clone https://github.com/shsm0520/supabasezombi.git
cd supabasezombi

# 의존성 설치
pip install supabase requests

# 실행
python main_standalone.py
```

## 로그

컨테이너 로그를 확인하면 실행 상태를 볼 수 있습니다:

```bash
docker logs -f supabasezombi
```

출력 예시:

```
2025-10-30 09:00:00 - INFO - KeepAlive service started. Running every 24 hours

2025-10-30 09:00:00 - INFO - == '2025-10-30 09:00:00' Run start (2 servers)
2025-10-30 09:00:00 - INFO - = Server #1: My Database
2025-10-30 09:00:01 - INFO -   ✓ SUCCESS | #15 data | Inserted: 7 | Deleted: 0
2025-10-30 09:00:01 - INFO - = Server #2: Another Database
2025-10-30 09:00:02 - INFO -   ✓ SUCCESS | #53 data | Inserted: 5 | Deleted: 23
2025-10-30 09:00:02 - INFO - == All run complete (2/2)
2025-10-30 09:00:02 - INFO - == Next run: '2025-10-31 09:00:02'
```

## 환경변수

민감한 정보는 환경변수로 관리할 수 있습니다.

`docker-compose.override.yml`에서 환경변수 추가:

```yaml
version: "3.8"

services:
  supabasezombi:
    environment:
      - SUPABASE_KEY_1=your-key-here
      - SUPABASE_KEY_2=another-key-here
```

그리고 `config.json`에서 참조:

```json
{
  "name": "Database 1",
  "supabase_url": "https://your-project.supabase.co",
  "supabase_key_env": "SUPABASE_KEY_1",
  "table_name": "keep-alive"
}
```

## 문제 해결

### 컨테이너가 계속 재시작됨

- 로그 확인: `docker logs supabasezombi`
- config.json 파일이 올바른지 확인
- Supabase URL과 Key가 유효한지 확인

### 즉시 실행하고 싶음

```bash
docker restart supabasezombi
```

## 텔레그램 알림

매일 실행 결과를 텔레그램으로 받을 수 있습니다:

1. [@BotFather](https://t.me/BotFather)에서 봇 생성
2. [@userinfobot](https://t.me/userinfobot)에서 Chat ID 확인
3. `docker-compose.yml`에서 주석 해제하고 값 입력:
   ```yaml
   environment:
     - TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
     - TELEGRAM_CHAT_ID=123456789
   ```

알림 내용:

- 실행 시간 및 소요 시간
- 성공/실패 서버 개수
- 실패한 서버 이름 (있을 경우)

## 크레딧

[supabase-inactive-fix](https://github.com/travisvn/supabase-inactive-fix) by [travisvn](https://github.com/travisvn)을 기반으로 제작되었습니다.

추가된 기능:

- 랜덤 삽입 개수 (실행당 1-10개)
- 50개 초과 시 자동 정리 기능
- 단일 파일로 간소화
- 빌드 없이 바로 실행 가능한 Docker 배포
- 개선된 로그 형식
- 텔레그램 알림 지원

## 라이센스

MIT License - 자유롭게 사용하세요!

---

**유용하다면 Star ⭐ 눌러주세요!**
