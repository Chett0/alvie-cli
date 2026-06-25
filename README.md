# alvie-cli

## Requirements

Ensure you have the following installed on your system:
- Docker

## Execution

Build and run docker container:

```bash
make pull # Pull the base image: matteobusi/alvie
make # Build and run the docker container
```

Run 

```bash
python alvie-cli
```

This starts the interactive mode, which guides you through selecting a command,
providing its arguments and (optionally) saving the resulting configuration.

## Non-interactive execution

When a configuration file is passed as an argument, the CLI skips the interactive
mode and executes the corresponding command directly. This is useful for scripting
or for re-running a previously saved configuration.

```bash
python alvie-cli <config-file> [-s | --std-output]
```

- `<config-file>`: path to a saved command configuration (JSON).
- `-s`, `--std-output`: stream the raw standard output instead of the parsed/formatted output.

The configuration file uses the same format produced by the interactive mode when
saving a command. It contains the command `name`, its `executable` and the list of
`args` (flags followed by their values):

```json
{
  "name": "Learn",
  "executable": "learn.exe",
  "args": [
    "--att-spec", "/home/alvie/spec-lib/example/attacker.atdl",
    "--encl-spec", "/home/alvie/spec-lib/example/enclave.etdl",
    "--oracle", "randomwalk",
    "--debug"
  ]
}
```

Assuming the file above is saved as `presets/config.json`, run it with:

```bash
python alvie-cli presets/config.json -a
```