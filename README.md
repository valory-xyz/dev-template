# Dev-template

A template for development with the open-autonomy framework. Find the documentation [here](docs.autonolas.network).

## System requirements

Read the requirements section [here](https://docs.autonolas.network/quick_start/).

## It contains:

- Empty directory `packages` which acts as the local registry

- .env file with Python path updated to include packages directory

To install the latest version of the open-autonomy and development dependencies:

	  make new_env


## Linters:

      make formatters
      make code-checks
      make generators
      make security