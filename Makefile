.PHONY: backend frontend ingest train test docker

backend:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

ingest:
	python -m rag.ingest

train:
	python training/train_classifier.py

test:
	python -m pytest tests
	python -m py_compile $$(find backend agents rag jira training tests -name '*.py')

docker:
	docker compose up --build
