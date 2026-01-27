FROM python:3.11-slim

WORKDIR /app

# 의존성 설치
RUN pip install --no-cache-dir --quiet --no-warn-script-location --disable-pip-version-check \
    supabase requests

# 파일 복사
COPY main_standalone.py main.py

# 환경 변수 설정
ENV TZ=Asia/Seoul
ENV PYTHONUNBUFFERED=1

# 메인 스크립트 실행
CMD ["python", "-u", "main.py"]
