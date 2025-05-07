echo "[1] Docker Compose 빌드 및 컨테이너 실행"
docker compose up --build -d

echo "[2] 실시간 로그 보기 (Ctrl+C로 종료)"
docker compose logs -f  
