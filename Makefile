PROJECT_NAME = vdr-extract
COMPOSE = docker compose
API_SERVICE = vdr-extract-api
WORKER_SERVICE = vdr-extract-worker

# ======================================================
# 🧱 Basic Lifecycle Commands
# ======================================================

.PHONY: build up down restart rebuild logs ps exec-api exec-worker clean help

build:
	@echo "🔨 Building all Docker images..."
	$(COMPOSE) build --no-cache

up:
	@echo "🚀 Starting $(PROJECT_NAME) stack..."
	$(COMPOSE) up
	@echo "✅ Services are running! Try: http://localhost:8080/docs"

up-bg:
	@echo "🚀 Starting $(PROJECT_NAME) stack..."
	$(COMPOSE) up -d
	@echo "✅ Services are running! Try: http://localhost:8080/docs"

down:
	@echo "🛑 Stopping and removing all containers..."
	$(COMPOSE) down

restart:
	@echo "♻️ Restarting stack..."
	$(COMPOSE) down
	$(COMPOSE) up -d

rebuild:
	@echo "🔁 Rebuilding containers..."
	$(COMPOSE) down
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

logs:
	@echo "📜 Tail logs for $(PROJECT_NAME)..."
	$(COMPOSE) logs -f --tail=100

log-api:
	@echo "📜 Tail logs for API service..."
	$(COMPOSE) logs -f --tail=100 $(API_SERVICE)

ps:
	@echo "📋 Container status:"
	$(COMPOSE) ps

remove-orphans:
	@echo "🧹 Removing orphaned containers..."
	rm -rf ./_data/minio
	$(COMPOSE) down -v --remove-orphans

# ======================================================
# 🧩 Development Helpers
# ======================================================

exec-api:
	@echo "🐍 Entering API container shell..."
	$(COMPOSE) exec $(API_SERVICE) /bin/bash || $(COMPOSE) exec $(API_SERVICE) /bin/sh

exec-worker:
	@echo "⚙️ Entering Worker container shell..."
	$(COMPOSE) exec $(WORKER_SERVICE) /bin/bash || $(COMPOSE) exec $(WORKER_SERVICE) /bin/sh

clean:
	@echo "🧹 Removing all containers, volumes, and images..."
	$(COMPOSE) down -v --rmi all
	docker system prune -af
	@echo "✅ Clean complete."

# ======================================================
# 🧠 Quality / Check Commands
# ======================================================

lint:
	@echo "🧽 Running code lint checks (ruff + black if available)..."
	@$(COMPOSE) exec $(API_SERVICE) bash -c 'if command -v ruff >/dev/null 2>&1; then ruff check .; fi'
	@$(COMPOSE) exec $(API_SERVICE) bash -c 'if command -v black >/dev/null 2>&1; then black --check .; fi'

# ======================================================
# 🧰 Utility & Shortcuts
# ======================================================

test-health:
	@echo "🩺 Testing health endpoint..."
	curl -s http://localhost:8080/health-check | jq .

list-buckets:
	@echo "🪣 Listing MinIO buckets..."
	$(COMPOSE) exec $(API_SERVICE) python -c "from api.services.storage_service import get_minio_client; c=get_minio_client(); print([b.name for b in c.list_buckets()])"

open-docs:
	@echo "🌐 Opening FastAPI docs..."
	open http://localhost:8080/docs || xdg-open http://localhost:8080/docs || true

# ======================================================
# 📖 Help
# ======================================================

help:
	@echo ""
	@echo "📘 $(PROJECT_NAME) Makefile Commands"
	@echo "---------------------------------------"
	@echo " build           → Build all Docker images"
	@echo " up              → Start all services in background"
	@echo " down            → Stop and remove all containers"
	@echo " restart         → Restart the full stack"
	@echo " rebuild         → Rebuild everything from scratch"
	@echo " logs            → Tail logs from all services"
	@echo " ps              → Show running containers"
	@echo " exec-api        → Open shell inside API container"
	@echo " exec-worker     → Open shell inside Worker container"
	@echo " clean           → Remove containers, volumes, and images"
	@echo " lint            → Run code linting (ruff/black if available)"
	@echo " test-health     → Call /health-check endpoint"
	@echo " list-buckets    → Print MinIO buckets via Python shell"
	@echo " open-docs       → Open FastAPI Swagger UI in browser"
	@echo " help            → Show this help menu"
	@echo "---------------------------------------"