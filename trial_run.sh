#!/bin/bash

# Run create_database.py
python3 utils/create_database_rag.py

# Check if create_database.py ran successfully
if [ $? -eq 0 ]; then
    echo "create_database.py ran successfully, running query_database_rag.py"
    
    # Run query_database_rag.py
    python3 src/query_database_rag.py "What happens when I block a 4/4 creature with trample and deathtouch with a 1/1 creature?"

    if [ $? -eq 0 ]; then
        echo "query_database_rag.py ran successfully"
    else
        echo "query_database_rag.py encountered an error"
    fi
else
    echo "create_database_rag.py encountered an error"
fi