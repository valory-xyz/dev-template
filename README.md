# Dev-template

A template for development with the open-autonomy framework.

## System requirements

- Python `>=3.7`
- [Tendermint](https://docs.tendermint.com/master/introduction/install.html) `==0.34.11`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`

Alternatively, you can fetch this docker image with the relevant requirments satisfied:

        docker pull valory/dev-template:latest
        docker container run -it valory/dev-template:latest

## It contains:

- Empty directory `packages` which acts as the local registry

- .env file with Python path updated to include packages directory

To install the latest version of the open-AEA and development dependencies:

	  make new_env


## Linters:

      make formatters
      make code-checks
      make generators
      make security