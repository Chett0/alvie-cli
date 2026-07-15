BASE_IMAGE := matteobusi/alvie
PROJECT_NAME = alvie

SERVICE := app # CLI
VIEWER_SERVICE := viewer # viewer

COMPOSE_CMD := docker compose -p $(PROJECT_NAME)

VENV_ACTIVATE := /home/alvie/venv/bin/activate

.PHONY: all pull build rebuild run cli viewer up stop stop-cli stop-viewer down restart restart-cli restart-viewer exec

all: run

pull:
	docker pull $(BASE_IMAGE)

build:
	$(COMPOSE_CMD) build

rebuild:
	$(COMPOSE_CMD) build --no-cache

# start viewer in background and run alvie-cli in foreground
run:
	$(COMPOSE_CMD) up --build -d $(VIEWER_SERVICE)
	$(COMPOSE_CMD) run --rm -it $(SERVICE)

cli:
	$(COMPOSE_CMD) run --build --rm -it $(SERVICE)

viewer:
	$(COMPOSE_CMD) up --build -d $(VIEWER_SERVICE)

up:
	$(COMPOSE_CMD) up --build -d

stop:
	$(COMPOSE_CMD) stop

stop-cli:
	$(COMPOSE_CMD) stop $(SERVICE)

stop-viewer:
	$(COMPOSE_CMD) stop $(VIEWER_SERVICE)

down:
	$(COMPOSE_CMD) down

restart:
	$(COMPOSE_CMD) restart

restart-cli:
	$(COMPOSE_CMD) restart $(SERVICE)

restart-viewer:
	$(COMPOSE_CMD) restart $(VIEWER_SERVICE)

exec:
	$(COMPOSE_CMD) exec -it $(SERVICE) /bin/bash --rcfile $(VENV_ACTIVATE)
