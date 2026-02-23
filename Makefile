# PhotoCleaner Makefile
# Quick commands for common development tasks

.PHONY: help install test lint format clean build run docker

# Default target
help:
	@echo "PhotoCleaner v0.8.3 - Development Commands"
	@echo "=========================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install all dependencies"
	@echo "  make install-dev   Install dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test          Run all tests"
	@echo "  make test-cov      Run tests with coverage"
	@echo "  make test-fast     Run tests (skip slow ones)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint          Run linter (ruff)"
	@echo "  make format        Format code (black)"
	@echo "  make typecheck     Run type checker (mypy)"
	@echo "  make check-all     Run all quality checks"
	@echo ""
	@echo "Running:"
	@echo "  make run           Start GUI"
	@echo "  make run-debug     Start GUI in debug mode"
	@echo ""
	@echo "Building:"
	@echo "  make build         Build executable"
	@echo "  make docker        Build Docker image"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean         Remove build artifacts"
	@echo "  make clean-all     Remove all generated files"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-cov black ruff mypy

test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=src --cov-report=html --cov-report=term

test-fast:
	pytest tests/ -v -m "not slow"

lint:
	ruff check src/

format:
	black src/ tests/

typecheck:
	mypy src/ --ignore-missing-imports

check-all: lint typecheck test

run:
	python run_ui.py

run-debug:
	PHOTOCLEANER_MODE=DEBUG python run_ui.py

build:
	pyinstaller PhotoCleaner.spec --clean --noconfirm

docker:
	docker build -t photocleaner:0.5.5 .

clean:
	rm -rf build/ dist/ *.egg-info
	rm -rf .pytest_cache .coverage htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

clean-all: clean
	rm -rf .venv/
	rm -f *.db *.license
