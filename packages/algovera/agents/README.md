# Chat Completion Agent

## Description

An agent that uses the `chat_completion_fsm_app` to carry out `chat_completion`

## How To Deploy

1. Clone the repo
`git clone git@github.com:AlgoveraAI/daios.git`

2. Pull the necessary packages

3. Deploy `RabbitMQ` locally
    `docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 -e RABBITMQ_DEFAULT_USER=guest -e RABBITMQ_DEFAULT_PASS=guest rabbitmq:3-management`

4. Update the packages
    `autonomy packages lock`

5. Fetch the agent
    `autonomy fetch algovera/chat_completion_agent:0.1.0 --local`

6. Add the necessary args
    - add `openai_api_key` to `models.params.args`
    - Change `models.chat_completion.args` if necessary
    - Change `models.interact_rabbitmq.args` based on `step 3`

7. Add `ethereum key`
    - `echo -n "0x47e179ec197488593b187f80a00eb0da91f1b9d0b13f8733639f19c30a34926a" > key.txt`
    - `autonomy add-key ethereum your_agent_key.txt`
    **Note**: Make sure you are in the `chat_completion_agent` folder you fetched from `step 5`

8. Start the agent
    `autonomy -s run`

9. Start tendermint node
    - `rm -rf ~/.tendermint`
    - `tendermint init`
    - `tendermint node --proxy_app=tcp://127.0.0.1:26658 --rpc.laddr=tcp://127.0.0.1:26657 --p2p.laddr=tcp://0.0.0.0:26656 --p2p.seeds= --consensus.create_empty_blocks=true`

9. Submit a request and get reponse 
    **Note**: Check `daios/testing/chat_completion_agent/test_chat_completion_agent.ipynb`
