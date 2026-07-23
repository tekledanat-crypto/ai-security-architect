.PHONY: up down validate-frameworks test lint dev-backend dev-frontend dev-mcp

up:              ## Run the full stack (complete after Chunk 5)
	docker compose up --build

down:
	docker compose down

validate-frameworks:  ## Validate framework JSON against schema (CI gate)
	python frameworks/validate.py

test:            ## Run all test suites (populated per chunk)
	cd mcp-server && pytest -q || true
	cd backend && pytest -q || true

lint:
	ruff check backend mcp-server frameworks || true

dev-mcp:         ## Chunk 3
	cd mcp-server && uvicorn app.http:app --port 8100 --reload

dev-backend:     ## Chunk 4
	cd backend && uvicorn app.main:app --port 8000 --reload

dev-frontend:    ## Chunk 5
	cd frontend && npm run dev

evals: ## Run scoring-engine evaluations (golden architectures)
	python3 tests/evals/run_evals.py

evals-json: ## Machine-readable eval results
	python3 tests/evals/run_evals.py --json

validate-iac: ## Static pre-flight checks on the Bicep templates
	python3 scripts/validate_bicep.py

verify-governance: ## Check governance docs cite real files and tests
	python3 scripts/verify_governance_claims.py

verify: ## Run every check: corpus, engine, backend, evals, IaC, governance
	python3 frameworks/validate.py
	cd mcp-server && python3 -m pytest -q
	cd backend && python3 -m pytest -q
	cd tests/evals && python3 -m pytest -q
	python3 scripts/validate_bicep.py
	python3 scripts/verify_governance_claims.py
