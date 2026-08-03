# Kubernetes manifests

Plain manifests (no Helm/Kustomize dependency) for running the Social Media AI OS
stack on any cluster. Apply in order — the numeric prefixes encode the dependency
order:

```bash
# 1. Build and push images (replace with your registry)
docker build -t your-registry/social-os-api:latest apps/api
docker build -t your-registry/social-os-web:latest \
  --build-arg NEXT_PUBLIC_API_URL=https://api.example.com apps/web
docker push your-registry/social-os-api:latest
docker push your-registry/social-os-web:latest

# 2. Point the manifests at your images
#    (replace `social-os/api:latest` / `social-os/web:latest` in 20-api.yaml,
#    21-worker.yaml, 22-web.yaml with your-registry/... above)

# 3. Create the real secrets file (never commit it)
cp infra/k8s/02-secrets.example.yaml infra/k8s/02-secrets.yaml
# edit infra/k8s/02-secrets.yaml with real values

# 4. Apply everything
kubectl apply -f infra/k8s/00-namespace.yaml
kubectl apply -f infra/k8s/01-configmap.yaml
kubectl apply -f infra/k8s/02-secrets.yaml
kubectl apply -f infra/k8s/10-postgres.yaml
kubectl apply -f infra/k8s/11-redis.yaml
kubectl apply -f infra/k8s/20-api.yaml
kubectl apply -f infra/k8s/21-worker.yaml
kubectl apply -f infra/k8s/22-web.yaml
kubectl apply -f infra/k8s/30-ingress.yaml   # requires an ingress controller
```

Or apply the whole directory at once (kubectl applies alphabetically, which
matches the dependency order thanks to the numeric prefixes):

```bash
kubectl apply -f infra/k8s/ --exclude=02-secrets.example.yaml
```

## What's here

- `10-postgres.yaml` — single-instance Postgres with a PVC. For production, prefer
  a managed Postgres (RDS, Cloud SQL) and just point `DATABASE_URL` at it instead.
- `11-redis.yaml` — single-instance Redis for Celery broker/backend. Same caveat —
  swap for a managed Redis in production.
- `20-api.yaml` — FastAPI Deployment (2 replicas + HPA on CPU), a migration
  `initContainer` that runs `alembic upgrade head` before the app starts, and a
  readiness/liveness probe on `/health`.
- `21-worker.yaml` — Celery worker Deployment (scales horizontally) and Celery
  beat Deployment (**must stay at 1 replica** — running beat twice double-fires
  scheduled tasks).
- `22-web.yaml` — Next.js Deployment + Service.
- `30-ingress.yaml` — nginx Ingress routing `app.example.com` → web,
  `api.example.com` → api. Swap in your own domains and TLS annotations.

This is intentionally minimal and dependency-free so it's easy to read end to
end. For a large multi-environment rollout, layer Kustomize or Helm on top
rather than hand-editing these files per environment.
