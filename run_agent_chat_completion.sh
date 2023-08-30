rm -r chat_completion_agent
find . -empty -type d -delete  # remove empty directories to avoid wrong hashes
autonomy packages lock
autonomy fetch --local --agent algovera/chat_completion_agent && cd chat_completion_agent
export OPENAI_API_KEY=here_goes_your_openai_api_key
cp $PWD/../ethereum_private_key.txt .
autonomy add-key ethereum ethereum_private_key.txt
autonomy issue-certificates
aea -s run