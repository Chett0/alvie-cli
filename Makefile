BASE_IMAGE := matteobusi/alvie
SERVICE := app
VIEWER_SERVICE := viewer
VENV_ACTIVATE := /home/alvie/venv/bin/activate

.PHONY: all pull build rebuild run compose compose-up compose-exec compose-stop compose-start compose-start-container compose-restart compose-restart-container

all: build run

pull:
	docker pull $(BASE_IMAGE)

build:
	docker compose build

rebuild:
	docker compose build --no-cache

# start viewer in background and run alvie-cli in foreground
run:
	docker compose up -d $(VIEWER_SERVICE)
	docker compose run --rm -it $(SERVICE)

viewer:
	docker compose up -d $(VIEWER_SERVICE)

compose: 
	docker compose up -d
	docker compose exec -it $(SERVICE) /bin/bash --rcfile $(VENV_ACTIVATE)

compose-up:
	docker compose up -d $(SERVICE)

stop:
	docker compose stop $(SERVICE)
	docker compose stop $(VIEWER_SERVICE)


start: compose-start exec

compose-start:
	docker compose start $(SERVICE)


restart: compose-restart exec

compose-restart:
	docker compose restart $(SERVICE)

exec:
	docker compose exec -it $(SERVICE) /bin/bash --rcfile $(VENV_ACTIVATE)
