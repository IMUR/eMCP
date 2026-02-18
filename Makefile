.PHONY: help up down restart logs register status ps clean dev docs

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	@[ -f .env ] || cp .env.example .env
	@mkdir -p demo-data
	@[ -f demo-data/readme.txt ] || echo "eMCP demo filesystem" > demo-data/readme.txt
	docker compose up -d
	@printf "  Waiting for gateway..."
	@until docker exec emcp-server curl -sf http://localhost:8080/api/v0/tools > /dev/null 2>&1; do sleep 2; printf "."; done
	@echo " ready"
	@$(MAKE) --no-print-directory register
	@echo ""
	@docker compose ps --format "table {{.Name}}\t{{.Status}}"
	@echo ""
	@echo "  Web UI:   http://localhost:$${EMCP_MANAGER_PORT:-3701}"
	@echo "  Gateway:  http://localhost:$${EMCP_GATEWAY_PORT:-3700}"

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
	@curl -sf http://localhost:$${EMCP_GATEWAY_PORT:-3700}/api/v0/tools 2>/dev/null | jq 'length' 2>/dev/null || echo "gateway not ready"

ps: ## List running containers
	docker compose ps

register: ## Re-register all configs with MCPJungle
	@command -v jq >/dev/null 2>&1 || { echo "Error: jq is required. Install: apt-get install jq / brew install jq"; exit 1; }
	@echo "Registering server configs..."
	@for f in configs/*.json; do \
		name=$$(jq -r '.name' $$f); \
		echo "  $$name"; \
		docker exec emcp-server /mcpjungle deregister $$name 2>/dev/null || true; \
		docker exec emcp-server /mcpjungle register -c /configs/$$(basename $$f); \
	done
	@echo "Done."

dev: ## Start with locally built images (for development)
	@[ -f .env ] || cp .env.example .env
	@mkdir -p demo-data
	@[ -f demo-data/readme.txt ] || echo "eMCP demo filesystem" > demo-data/readme.txt
	docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d --build
	@printf "  Waiting for gateway..."
	@until docker exec emcp-server curl -sf http://localhost:8080/api/v0/tools > /dev/null 2>&1; do sleep 2; printf "."; done
	@echo " ready"
	@$(MAKE) --no-print-directory register
	@echo ""
	@docker compose ps --format "table {{.Name}}\t{{.Status}}"
	@echo ""
	@echo "  Web UI:   http://localhost:$${EMCP_MANAGER_PORT:-3701}"
	@echo "  Gateway:  http://localhost:$${EMCP_GATEWAY_PORT:-3700}"

clean: ## Remove all containers, volumes, and runtime data
	docker compose down -v --remove-orphans
	rm -rf data/ demo-data/

docs: ## Serve documentation locally
	@command -v mkdocs >/dev/null 2>&1 || { echo "Install mkdocs: pip install mkdocs-material"; exit 1; }
	mkdocs serve
