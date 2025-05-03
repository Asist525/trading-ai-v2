#!/usr/bin/env bash
set -Eeuo pipefail          # ① 스크립트 오류 시 즉시 중단

IMG_DJ=mydjango:latest
IMG_CO=kis-collector:latest
KIND_CONTEXT=${KIND_CONTEXT:-kind}   # ② 여러 kind 클러스터 쓸 때 대비

echo "🛠️  Docker 이미지 빌드 (no-cache)…"
docker build --no-cache -t "${IMG_DJ}" -f Dockerfile.django .
docker build --no-cache -t "${IMG_CO}" -f Dockerfile.collector .

echo "📦 kind 클러스터에 이미지 로딩…"
kind load docker-image "${IMG_DJ}" --name "${KIND_CONTEXT}"
kind load docker-image "${IMG_CO}" --name "${KIND_CONTEXT}"

echo "⚙️  ConfigMap / Secret 적용…"
kubectl apply -f kis-config.yaml
kubectl apply -f kis-secret.yaml

echo "🗄️  Postgres & Django & Collector 배포/업데이트…"
kubectl apply -f postgres.yaml
kubectl apply -f django.yaml
kubectl apply -f collector-deploy.yaml

echo "🧹 기존 collector Pod 삭제(rolling)…"
kubectl delete pod -l app=kis-collector --ignore-not-found=true

echo "⏳ collector 새 Pod Ready 대기…"
kubectl rollout status deploy/kis-collector --timeout=120s

echo "🔎 실시간 수집기 로그 팔로우"
kubectl logs deploy/kis-collector -f
