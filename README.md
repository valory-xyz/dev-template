# Dev-template

A template for development with the open-autonomy framework. Find the documentation [here](docs.autonolas.network).

## System requirements

- Python `>=3.7`
- [Tendermint](https://docs.tendermint.com/master/introduction/install.html) `==0.34.19`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`
- [Pip](https://pip.pypa.io/en/stable/installation/)
- [Pipenv](https://pipenv.pypa.io/en/latest/install/) `>=2021.x.xx`
- [Docker Engine](https://docs.docker.com/engine/install/)
- [Docker Compose](https://docs.docker.com/compose/install/)

Alternatively, you can fetch this docker image with the relevant requirements satisfied:

> **_NOTE:_**  Tendermint and IPFS dependencies are missing from the image at the moment.

```bash
docker pull valory/open-autonomy-user:latest
docker container run -it valory/open-autonomy-user:latest
```

## This repository contains:

- Empty directory `packages` which acts as the local registry

- .env file with Python path updated to include packages directory

## How to use

Create a virtual environment with all development dependencies:

```bash
make new_env
```

Enter virtual environment:

``` bash
pipenv shell
```

Get developing...

## Useful commands:

Check out the `Makefile` for useful commands, e.g. `make formatters`, `make generators`, `make code-checks`, as well
as `make common-checks-1`. To run tests use the `autonomy test` command. Run `autonomy test --help` for help about its usage.
