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
Connections
- `chat_completion`: connection betweeen OpenAI API calls and the agent

Skills
- `chat_completion_abci`: A skill that adds `embedding` given a file, `chat` over the created embedding, maintains `chat_history` of the chat

Agent
- `chat_completion_agent`: An agent that runs on top of the `chat_completion_abci` skill

Service
- `chat_completion_local`: A service built on top of `chat_completion_agent` 

## How to use

##### The agent
1. Git clone the repository
`git clone git@github.com:AlgoveraAI/daios.git`

2. Sync the third-party packages needed for this project
`autonomy packages sync --update-packages`
`autonomy packages lock`

3. Install requirements for the project and activate the virtual environment
`poetry install`
`poetry shell`

4. Update `run_agent.sh` with appropriate location of ethereum key and openai_api_key

5. Run the agent
`sh run_agent.sh`

6. Test the agent
Check `./testing/chat_completion_agent/test_chat_completion_agent.ipynb` notebook

##### The service
1. Git clone the repository
`git clone git@github.com:AlgoveraAI/daios.git`

2. Sync the third-party packages needed for this project
`autonomy packages sync --update-packages`

3. Update `run_service.sh` with appropriate location of keys.json

4. Update `.env.sample` with appropriate credentials

5. Run the service
`sh run_service.sh`
