_[Deus ex machina](https://en.wikipedia.org/wiki/Deus_ex_machina) ("God from the machine") is a plot device whereby a seemingly unsolvable problem in a story is suddenly or abruptly resolved by an unexpected and unlikely occurrence._

# DAIOS: LLM programming framework on top of Open Autonomy framework

LLM programming frameworks such as LangChain have been widely adopted. LangChain includes building blocks such as Chains, Tools, and Agents. However, despite its popularity, many remain unsure about the abstractions, and wonder whether it will become the eventual winner (think PyTorch vs Tensorflow). Microsoft recently released their own version called Semantic Kernel (SK), where agents are made up of a kernel, memory, and skills (although there is not much consideration given to chains/flows). These abstractions align pretty well with AEAs, and autonomous services build on AEAs. 

Open AEA (Valory’s fork of AEA) is an agent framework in the crypto space that has been in development for a longer amount of time than LLM agent frameworks in the AI space. AEA has the advantage of integrating with blockchain, messaging etc. The Open Autonomy framework extends Open AEA to the concept of agent service: a decentralized off-chain autonomous service which runs as a multi-agent-system (MAS), enables complex processing, and is crypto-economically secured on a public blockchain. However, the above mentioned frameworks are currently missing some components  required for building LLM programs.

This collaboration between Valory and Algovera will explore whether these crypto agent frameworks can be adapted for LLM programming. LLMs have the promise of increasing the utility and adoption of crypto agent frameworks.

We see this as an important step towards a Decentralized AI Operating System (DAIOS). 

A template for development with the open-autonomy framework. Find the documentation [here](docs.autonolas.network).

# Background

This is collaboration between [Algovera](https://www.algovera.ai) and [Valory](https://www.valory.xyz/). You can find further details of the project including deliverables and timelines in this [doc](https://docs.google.com/document/d/1-4DQaBOhLvSXMfMQfoteAIZgUzSjRMmfdejE9MVUoLY/edit?usp=sharing).

## System requirements

- Python `>=3.7`
- [Tendermint](https://docs.tendermint.com/v0.34/introduction/install.html) `==0.34.19`
- [IPFS node](https://docs.ipfs.io/install/command-line/#official-distributions) `==0.6.0`
- [Pip](https://pip.pypa.io/en/stable/installation/)
- [Poetry](https://python-poetry.org/)
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
poetry shell
poetry install
```

Get developing...

## Useful commands:

Check out the `Makefile` for useful commands, e.g. `make formatters`, `make generators`, `make code-checks`, as well
as `make common-checks-1`. To run tests use the `autonomy test` command. Run `autonomy test --help` for help about its usage.
