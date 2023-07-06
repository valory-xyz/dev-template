# Chat Completion FSM App

## Description
This is a skill for an agent that does `chat completion`. 


### Behaviours
- `RegistrationBehaviour`
    Registers the agent
- `CollectRandomnessBehaviour`
    Collect random `DRAND`value
- `SelectKeeperBehaviour`
    Select the keeper agent.
- `WaitForRequestBehaviour`
    The agent wait for a request to come in from `RabbitMQ`
- `ProcessRequestBehaviour`
    Process the request. Calls the LLM.
- `PublishRequestBehaviour`
    Publish the response back to `RabbitMQ`

