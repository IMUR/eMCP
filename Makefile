.PHONY: help up down restart logs register status ps clean dev docs

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: .env ## Start all services
	@mkdir -p demo-data
	@[ -f demo-data/readme.txt ] || echo "eMCP demo filesystem" > demo-data/readme.txt
	docker compose up -d
	@echo ""
	@echo "  Web UI:   http://localhost:5010"
	@echo "  Gateway:  http://localhost:8090"

down: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

logs: ## Tail gateway logs
	docker compose logs -f emcp-server

status: ## Show service health and tool count
	@docker compose ps --format "table {{.Name}}\t{{.Status}}"
	@echo ""
	@printf "  Tools registered: "
	@curl -sf http://localhost:8090/api/v0/tools 2>/dev/null | jq 'length' 2>/dev/null || echo "gateway not ready"

ps: ## List running containers
	docker compose ps

register: ## Re-register all configs with MCPJungle
	@command -v jq >/dev/null 2>&1 || { echo "Error: jq is required. Install: apt-get install jq / brew install jq"; exit 1; }
	@echo "Re-registering all server configs..."
	@for f in configs/*.json; do \
		name=$$(jq -r '.name' $$f); \
		echo "  $$name"; \
		docker exec emcp-server /mcpjungle deregister $$name 2>/dev/null || true; \
		docker exec emcp-server /mcpjungle register -c /configs/$$(basename $$f); \
	done
	@echo "Done."
	@docker exec emcp-server /mcpjungle list servers

.env:
	@echo "No .env file found. Run:"
	@echo "  cp .env.example .env"
	@echo "  # Edit .env with your POSTGRES_USER and POSTGRES_PASSWORD"
	@exit 1

dev: .env ## Start with locally built images (for development)
	@mkdir -p demo-data
	@[ -f demo-data/readme.txt ] || echo "eMCP demo filesystem" > demo-data/readme.txt
	docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d --build
	@echo ""
	@echo "  Web UI:   http://localhost:5010"
	@echo "  Gateway:  http://localhost:8090"

clean: ## Remove all containers, volumes, and runtime data
	docker compose down -v
	rm -rf data/ demo-data/

docs: ## Serve documentation locally
	@command -v mkdocs >/dev/null 2>&1 || { echo "Install mkdocs: pip install mkdocs-material"; exit 1; }
	mkdocs serve
