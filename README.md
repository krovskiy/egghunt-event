# The Amazing Virtual Egg Hunt

# Setup

## Setup an environment

### uv
```shell
uv venv .venv
```
### python
```shell
python -m venv .venv
```

## Install dependencies

### uv
activate the environment
```shell
uv sync 
```
### pip
activate the environment

```shell
pip install -r requirements.txt
```

# Run
## Debug
### uv

```shell
uv run server.py
```
### python
activate the environment
```shell
python server.py
```

# Deploy

make sure waitress is installed
```shell
waitress-serve --listen=0.0.0.0:8080 server:app
```