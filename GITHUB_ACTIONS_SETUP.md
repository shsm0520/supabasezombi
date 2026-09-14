# GitHub Actions 배포 가이드

## 개요

- **GitHub Actions**: Docker 이미지를 빌드하고 레지스트리(GHCR)에 push
- **서버**: 빌드된 이미지를 pull 받아서 `.env` + `config.json`과 함께 실행

## 1. GitHub Actions 설정 (이미지 빌드 & Push)

### 설정 불필요

GitHub Actions는 자동으로 GHCR(GitHub Container Registry)에 이미지를 push합니다.
별도의 Secrets 설정이 필요 없습니다. (`GITHUB_TOKEN`은 자동 제공)

### 이미지 빌드 트리거

- **Push 시**: main, master, develop 브랜치
- **Tag 시**: `v1.0.0` 형식의 태그
- **수동**: Actions 탭 > "Run workflow"

### 빌드된 이미지 위치

- GHCR: `ghcr.io/shsm0520/supabasezombi:latest`

## 2. 서버 배포 (이미지 Pull & 실행)

### 서버에서 설정

```bash
# 1. 필요한 파일 다운로드
git clone https://github.com/shsm0520/supabasezombi.git
cd supabasezombi

# 2. .env 파일 생성 (선택 사항)
cp .env.example .env
# .env 편집하여 설정값 입력

# 3. config.json 생성 (필수)
cp config.json.example config.json
# config.json 편집하여 Supabase 정보 입력

# 4. 이미지 Pull & 실행
docker-compose pull
docker-compose up -d

# 5. 로그 확인
docker-compose logs -f
```

### .env 파일 예시

```env
# 실행 간격 (시간 단위)
RUN_INTERVAL_HOURS=24

# 랜덤 삽입 개수 범위
RANDOM_INSERT_MIN=1
RANDOM_INSERT_MAX=10

# 데이터 정리 설정
MAX_DATA_LIMIT=50
TARGET_DATA_COUNT=30

# Telegram 알림 (선택)
TELEGRAM_BOT_TOKEN=5123456789:ABCDefGHIjklmnoPQRstuvwxyzABCDefGHI
TELEGRAM_CHAT_ID=987654321
```

### config.json 예시

```json
[
  {
    "name": "Database 1",
    "supabase_url": "https://xxxxxxxxxxxx.supabase.co",
    "supabase_key": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "table_name": "keep-alive"
  }
]
```

## 3. 로컬에서 빌드하여 테스트

GitHub 이미지를 사용하지 않고 로컬에서 빌드:

```bash
# docker-compose.yml 수정
# 1. image: ghcr.io/... 줄을 주석처리
# 2. build: . 섹션 주석 해제

# 빌드 & 실행
docker-compose up --build -d
```

## 4. 배포 흐름

```
1. 코드 수정 & Push
   ↓
2. GitHub Actions 자동 실행
   ↓
3. Docker 이미지 빌드 (requirements.txt 의존성 포함)
   ↓
4. GHCR에 Push
   ↓
5. 서버에서 docker-compose pull
   ↓
6. docker-compose up -d
```

## 5. 트러블슈팅

### GitHub Actions 로그 확인

1. GitHub 저장소 > Actions 탭
2. 실행된 workflow 클릭
3. 각 step의 로그 확인

### 일반적인 오류

#### 이미지를 찾을 수 없음

- GHCR 이미지가 private인 경우 로그인 필요:
  ```bash
  echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
  ```

#### 권한 오류

- GitHub 저장소 > Settings > Actions > General
- "Workflow permissions"를 "Read and write permissions"로 설정

#### 서버에서 이미지 Pull 실패

```bash
# 이미지 경로 확인
docker-compose config

# 수동으로 Pull 시도
docker pull ghcr.io/shsm0520/supabasezombi:latest
```

## 6. 보안 고려사항

- `.env`와 `config.json`은 Git에 커밋되지 않음 (`.gitignore`에 포함)
- 서버에만 실제 설정 파일 저장
- Supabase 키는 절대 코드에 하드코딩하지 말것

## 7. 업데이트 및 롤백 방법

### 새 버전 업데이트

```bash
# 최신 이미지 Pull & 재실행
docker-compose pull
docker-compose up -d
```

### 특정 버전 지정 및 롤백

`docker-compose.yml`에서 이미지 태그를 변경한 후 `docker-compose up -d`를 실행합니다:

```yaml
# docker-compose.yml
services:
  supabasezombi:
    image: ghcr.io/shsm0520/supabasezombi:v1.0.0 # 또는 이전 commit SHA / 특정 태그
```

```bash
docker-compose up -d
```
