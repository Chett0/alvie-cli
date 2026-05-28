BASE_IMAGE := matteobusi/alvie

all: build run

pull:
	docker pull $(BASE_IMAGE)

build:
	docker compose build

rebuild:
	docker compose build --no-cache

run:
	docker compose run --rm app