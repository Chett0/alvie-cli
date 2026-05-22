# alvie-cli

## Requirements

Ensure you have the following installed on your system:
- Docker

## Execution

Build and run docker container

```bash
docker pull matteobusi/alvie
docker build -t alvie-cli .
docker run -it alvie-cli
```

<!-- Create a file named .env in the root directory 

```env
ALVIE_CODE_PATH=path/to/alvie/codebase
``` -->

Activate python virtual environment

```bash
source venv/bin/activate
```

Run 

```bash
python alvie-cli
```