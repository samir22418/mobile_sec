.PHONY: up down build logs test reset db-upgrade

up:
	docker-compose up -d

down:
	docker-compose down

build:
	docker-compose build

logs:
	docker-compose logs -f

test:
	pytest

db-upgrade:
	alembic upgrade head

reset:
	docker-compose down -v
	rm -rf ../backend-data/raw-payloads/*
	docker-compose up -d
