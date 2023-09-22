rm -r valory_chat_agent
find . -empty -type d -delete  # remove empty directories to avoid wrong hashes
autonomy packages lock
autonomy fetch --local --agent algovera/valory_chat_agent && cd valory_chat_agent
export OPENAI_API_KEY=$OPENAI_API_KEY
cp ../key.txt .
autonomy add-key ethereum key.txt
autonomy issue-certificates
aea -s run