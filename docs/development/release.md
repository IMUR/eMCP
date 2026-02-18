# eMCP Release Preparation

Step-by-step instructions to go from the current state to a proper `v1.0.0` release with pre-built Docker images on GitHub Container Registry (ghcr.io).

Work through each step in order. Each section describes what needs to change, why, and the exact edits to make.

---

## Overview

| Step | What | Why |
|------|------|-----|
| 1 | Fix rough edges | Prevent first-run failures for new users |
| 2 | Clean up Dockerfile.gateway | Remove leftover development comments |
| 3 | Add GitHub Actions CI | Auto-build and publish Docker images on tag |
| 4 | Switch compose to pre-built images | Faster, more reliable first start |
| 5 | Add dev compose override | Preserve local build workflow for contributors |
| 6 | Run TEST_VALIDATION.md on a clean VM | Confirm it actually works |
| 7 | Tag v1.0.0 and publish release | Ship it |

---

## Step 1: Fix Rough Edges

Three issues exist in the current `Makefile` that will cause problems for new users.

### 1a. `demo-data/` is never created automatically

The `filesystem-mcp` container mounts `./demo-data:/demo:ro`. If the directory doesn't exist, Docker Compose either fails or creates it as root-owned, breaking the mount. It's gitignored, so new users won't have it.

**Fix:** Make `up` create it before starting services.

**Edit `Makefile`** — change the `up` target from:

```makefile
up: .env ## Start all services
	docker compose up -d
	@echo ""
	@echo "  Web UI:   http://localhost:5010"
	@echo "  Gateway:  http://localhost:8090"
```

To:

```makefile
up: .env ## Start all services
	@mkdir -p demo-data
	@[ -f demo-data/readme.txt ] || echo "eMCP demo filesystem" > demo-data/readme.txt
	docker compose up -d
	@echo ""
	@echo "  Web UI:   http://localhost:5010"
	@echo "  Gateway:  http://localhost:8090"
```

### 1b. `register` and `status` use `python3` on the host

The `register` target parses JSON config files with `python3`, and `status` counts tools with `python3`. These are host-side operations — `python3` may not be installed (and shouldn't be assumed). `jq` is a more appropriate tool for this, and is already required by `TEST_VALIDATION.md`.

**Fix the `register` target** — replace the `python3` line:

```makefile
# Before:
name=$$(python3 -c "import json; print(json.load(open('$$f'))['name'])"); \

# After:
name=$$(jq -r '.name' $$f); \
```

Also add a guard at the top of the target:

```makefile
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
```

**Fix the `status` target** — replace the `python3` pipe:

```makefile
# Before:
@curl -sf http://localhost:8090/api/v0/tools 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo "gateway not ready"

# After:
@curl -sf http://localhost:8090/api/v0/tools 2>/dev/null | jq 'length' 2>/dev/null || echo "gateway not ready"
```

### 1c. Remove demo-data from `make clean`

`make clean` currently deletes `demo-data/`, which is fine for teardown. But the README also says users create it manually. Confirm the `clean` target behavior is intentional (full reset) — if yes, no change needed, just document it clearly. If you want a softer default, rename to `make reset` for the full wipe and have `make clean` only remove containers and volumes.

**Recommended:** Keep `clean` as a full reset. It's explicit and safe.

---

## Step 2: Clean Up Dockerfile.gateway

`dockerfiles/Dockerfile.gateway` currently contains a block of unresolved comments about user permissions that were left from development. This is unprofessional in a public repo.

**Replace the full contents of `dockerfiles/Dockerfile.gateway` with:**

```dockerfile
FROM mcpjungle/mcpjungle:latest-stdio

USER root

# Install Docker CLI so MCPJungle can exec into sibling containers
RUN apt-get update && \
    apt-get install -y docker.io && \
    rm -rf /var/lib/apt/lists/*
```

That's it. The comments were speculative and don't reflect actual runtime behavior.

---

## Step 3: Add GitHub Actions CI/CD

Create the directory structure and workflow file that will automatically build and push Docker images to ghcr.io whenever a version tag is pushed.

### 3a. Create the workflow directory

```bash
mkdir -p .github/workflows
```

### 3b. Create `.github/workflows/docker-publish.yml`

This workflow:
- Triggers on any `v*` tag push (e.g. `v1.0.0`, `v1.2.3`)
- Also runs a build-only check on every push to `main` (no push to registry)
- Builds two images: `emcp-manager` and `emcp-server` (gateway)
- Pushes both to `ghcr.io/imur/` with the version tag and `latest`
- Uses the built-in `GITHUB_TOKEN` — no additional secrets needed

```yaml
name: Build and Publish Docker Images

on:
  push:
    branches:
      - main
    tags:
      - 'v*'

env:
  REGISTRY: ghcr.io
  OWNER: imur

jobs:
  build-manager:
    name: Build emcp-manager
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        if: startsWith(github.ref, 'refs/tags/')
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.OWNER }}/emcp-manager
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable=${{ startsWith(github.ref, 'refs/tags/') }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ./emcp-manager
          dockerfile: ./emcp-manager/Dockerfile
          push: ${{ startsWith(github.ref, 'refs/tags/') }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}

  build-gateway:
    name: Build emcp-server (gateway)
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Log in to GitHub Container Registry
        if: startsWith(github.ref, 'refs/tags/')
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.OWNER }}/emcp-server
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=raw,value=latest,enable=${{ startsWith(github.ref, 'refs/tags/') }}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          dockerfile: ./dockerfiles/Dockerfile.gateway
          push: ${{ startsWith(github.ref, 'refs/tags/') }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

### 3c. Make packages public on GitHub

After the first push, the published packages will be private by default. To make them publicly pullable (required for `docker compose up -d` to work without auth):

1. Go to `https://github.com/IMUR?tab=packages`
2. Click `emcp-manager` → Package settings → Change visibility → Public
3. Repeat for `emcp-server`

Do this after Step 4's first tag push.

---

## Step 4: Switch docker-compose.yaml to Pre-built Images

Once images are published to ghcr.io, `docker-compose.yaml` should pull them instead of building locally. This makes first-run fast and deterministic.

**Edit `docker-compose.yaml`:**

Change the `emcp-server` service from:

```yaml
  emcp-server:
    build:
      context: .
      dockerfile: dockerfiles/Dockerfile.gateway
    image: emcp:gateway
```

To:

```yaml
  emcp-server:
    image: ghcr.io/imur/emcp-server:latest
```

Change the `emcp-manager` service from:

```yaml
  emcp-manager:
    build:
      context: ./emcp-manager
      dockerfile: Dockerfile
```

To:

```yaml
  emcp-manager:
    image: ghcr.io/imur/emcp-manager:latest
```

**Important:** Do this *after* the first successful CI push (Step 3 + first tag). If you switch before images exist on ghcr.io, `docker compose up` will fail with a pull error.

---

## Step 5: Add a Dev Compose Override

Contributors who want to build images locally (to test changes to `emcp-manager/`) should not have to modify `docker-compose.yaml`. Create a separate override file.

**Create `docker-compose.dev.yaml`:**

```yaml
# Development override — restores local build for emcp-manager and emcp-server
# Usage: docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d

services:
  emcp-server:
    build:
      context: .
      dockerfile: dockerfiles/Dockerfile.gateway
    image: emcp:gateway

  emcp-manager:
    build:
      context: ./emcp-manager
      dockerfile: Dockerfile
    image: emcp:manager
```

**Add a `dev` target to `Makefile`:**

```makefile
dev: .env ## Start with locally built images (for development)
	@mkdir -p demo-data
	@[ -f demo-data/readme.txt ] || echo "eMCP demo filesystem" > demo-data/readme.txt
	docker compose -f docker-compose.yaml -f docker-compose.dev.yaml up -d --build
	@echo ""
	@echo "  Web UI:   http://localhost:5010"
	@echo "  Gateway:  http://localhost:8090"
```

Add `dev` to the `.PHONY` line at the top of the Makefile.

Also update `docker-compose.dev.yaml` to the `.gitignore`? No — this should be committed. It's a developer tool, not a personal config.

---

## Step 6: Run TEST_VALIDATION.md on a Clean VM

**Do not skip this step.** The test doc was written against expected behavior, not verified behavior.

### Recommended VM options

**Option A — Multipass (local, fastest):**
```bash
multipass launch --name emcp-test --memory 2G --disk 10G --cpus 2
multipass shell emcp-test
```

**Option B — DigitalOcean droplet:**
- Ubuntu 22.04 LTS, 2GB RAM ($12/mo, destroy after test)
- SSH in and proceed

**Option C — Any spare Linux machine or WSL2 (Ubuntu)**

### Run the test

Follow `TEST_VALIDATION.md` from Phase 1 through Phase 12. For each phase:

- Run every command exactly as written
- Record actual output next to each **Pass** criterion
- Mark **PASS** or **FAIL** in the results table at the bottom
- If something fails, fix the root cause in the repo before proceeding

### Known likely issues to watch for

1. **`make up` fails on first run** — may be a timing issue with `emcp-server` waiting for `db`. The healthcheck should handle this, but if not, a `sleep` may be needed in `up`.
2. **`make register` finds no configs** — if the filesystem demo server was never registered after `make up`. The fix is to have `make up` auto-register on first start, or document that `make register` must be run after every fresh start.
3. **Web UI shows no tools** — almost always a registration issue. `make register` should resolve it.
4. **`filesystem-mcp` exits** — `npx` may not cache well in `node:22-slim`. Consider using the official `mcp/filesystem` Docker image if it's available, or pinning the npx version.

For each failure: fix it, commit, note the fix in `CHANGELOG.md`, then re-run from that phase.

---

## Step 7: Tag v1.0.0 and Publish the Release

Once TEST_VALIDATION passes cleanly:

### 7a. Update CHANGELOG.md

Edit `CHANGELOG.md` to reflect any fixes made during testing. Add the final release date.

### 7b. Commit all changes

```bash
git add -A
git commit -m "Prepare v1.0.0 release"
git push origin main
```

Wait for the CI build on `main` to pass (build-only, no push).

### 7c. Create and push the tag

```bash
git tag -a v1.0.0 -m "Initial public release

Tool Access Broker for MCP systems. Filters which tools AI agents
can access to reduce token costs and cognitive overhead.

See CHANGELOG.md for details."

git push origin v1.0.0
```

This triggers the CI workflow. Monitor at `https://github.com/IMUR/eMCP/actions`.

### 7d. Make packages public (if not done in Step 3c)

Go to `https://github.com/IMUR?tab=packages` and set both `emcp-manager` and `emcp-server` to **Public**.

### 7e. Create the GitHub Release

Using the GitHub MCP tool or via the GitHub web UI:

**Via web UI:**
1. Go to `https://github.com/IMUR/eMCP/releases/new`
2. Select tag: `v1.0.0`
3. Title: `v1.0.0 — Initial Public Release`
4. Body: paste from CHANGELOG.md, append quick start snippet:

```markdown
## Quick Start

```bash
git clone https://github.com/IMUR/eMCP.git
cd eMCP
cp .env.example .env   # set POSTGRES_USER and POSTGRES_PASSWORD
make up
```

Open http://localhost:5010
```

5. Check **Set as latest release**
6. Publish

### 7f. Verify the published images work

On your test VM (or a fresh shell):

```bash
# Should pull from ghcr.io, not build locally
git clone https://github.com/IMUR/eMCP.git emcp-release-test
cd emcp-release-test
cp .env.example .env
# edit .env
make up
```

**Pass:** No `docker build` output — images are pulled directly. Services start faster than the local build test.

---

## Post-Release: Update Personal Deployment

Your personal deployment at `/mnt/ops/docker/eMCP` builds its own images and has its own configs. It should stay independent. No changes needed there unless you want to adopt the pre-built images (you probably don't — you want full control).

To pull in improvements from the public repo into your personal deployment in the future:

```bash
cd /mnt/ops/docker/eMCP
git remote add public https://github.com/IMUR/eMCP.git
git fetch public
git cherry-pick <commit-hash>   # pick specific improvements
```

---

## Summary Checklist

- [ ] **1a** — `make up` auto-creates `demo-data/`
- [ ] **1b** — `register` and `status` use `jq` instead of `python3`
- [ ] **1c** — Confirm `make clean` behavior is documented
- [ ] **2** — `Dockerfile.gateway` cleaned of leftover comments
- [ ] **3a** — `.github/workflows/` directory created
- [ ] **3b** — `docker-publish.yml` workflow written and pushed
- [ ] **3c** — ghcr.io packages set to public (after first tag)
- [ ] **4** — `docker-compose.yaml` updated to pull from ghcr.io
- [ ] **5** — `docker-compose.dev.yaml` created, `make dev` added
- [ ] **6** — `TEST_VALIDATION.md` run on a clean VM, all phases pass
- [ ] **7a** — `CHANGELOG.md` updated with final release date
- [ ] **7b** — All changes committed and pushed to `main`
- [ ] **7c** — `v1.0.0` tag pushed, CI builds images
- [ ] **7d** — ghcr.io packages confirmed public
- [ ] **7e** — GitHub Release created with release notes
- [ ] **7f** — Fresh clone verified to pull images (not build)
