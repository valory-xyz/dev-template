# Dev-template

A template repository for developing agent services with the [open-autonomy](https://github.com/valory-xyz/open-autonomy) framework. Full documentation [here](https://stack.olas.network).

## System requirements

- Python `>=3.10, <3.15`
- [Poetry](https://python-poetry.org/) `>=2.0`
- [Tendermint](https://docs.tendermint.com/v0.34/introduction/install.html) `==0.34.19`
- [IPFS](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`
- [Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/)

Alternatively, a pre-built image ships with most runtime pieces (Tendermint and IPFS are not included):

```bash
docker pull valory/open-autonomy-user:latest
docker container run -it valory/open-autonomy-user:latest
```

## This repository contains

- `packages/` — the local registry (`packages.json` + `dev`/`third_party` trees) where your agents, skills, protocols and connections live.
- `.env` — prepends the project root to `PYTHONPATH` so local `packages` imports resolve.
- `tox.ini` — the full lint/format/check matrix (also run in CI).
- `Makefile` — shortcuts for the common workflows.

## How to use

```bash
poetry install
eval $(poetry env activate)
```

Then start building under `packages/<your-author>/<your-skill>/`.

## Useful commands

| Command | Purpose |
|---|---|
| `make formatters` | `black` + `isort` |
| `make code-checks` | `black-check`, `isort-check`, `flake8`, `mypy`, `pylint`, `darglint` |
| `make security` | `safety`, `bandit`, `gitleaks` |
| `make generators` | regenerate ABCI docstrings, refresh copyright headers, re-lock packages |
| `make common-checks-1` | copyright + doc links + `check-hash` + `check-packages` |
| `make clean` | remove build/test/cache artefacts |
| `autonomy test` | run agent tests (see `autonomy test --help`) |
