# The Amazing Virtual Egg Hunt

# Setup

you need Python 3.13+ and a Discord OAuth application. copy `.env.example` to `.env` in the repository root, then set the Discord client ID and secret, authorization URL, callback URL, and unique values for `SECRET_KEY` and `SALT`. register the callback URL with Discord. keep `.env` private.

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
uv run backend.py
```
### python
activate the environment
```shell
python backend.py
```

the development server listens on `http://127.0.0.1:5000`. Discord login requires the OAuth URLs to match your application configuration.

# Deploy

make sure waitress is installed
```shell
waitress-serve --listen=0.0.0.0:8080 backend:app
```
