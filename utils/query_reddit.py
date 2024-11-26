import os
import sys
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, StructuredChatAgent
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_community.tools.reddit_search.tool import RedditSearchRun, RedditSearchSchema
from langchain_community.utilities.reddit_search import RedditSearchAPIWrapper
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from config import API_KEY
from utils.langchain_query_tools import create_prompt

# Step 1: Define the function to execute Reddit search
def reddit_search_tool_run(input_text, client_id, client_secret, user_agent, subreddit=None, time_filter=None, sort=None, limit=10):
    """
    Executes a Reddit search based on the input query and parameters.
    """
    search_params = RedditSearchSchema(
        query=input_text,
        subreddit=subreddit,
        time_filter=time_filter,
        sort=sort,
        limit=limit
    )
    api_wrapper = RedditSearchAPIWrapper(
        reddit_client_id=client_id,
        reddit_client_secret=client_secret,
        reddit_user_agent=user_agent,
    )
    reddit_tool = RedditSearchRun(api_wrapper=api_wrapper)
    return reddit_tool.run(search_params.dict())

# Step 2: Define the function to get the Reddit Search tool
def get_reddit_tool(client_id, client_secret, user_agent, subreddit=None, time_filter=None, sort=None, limit=10):
    """
    Returns a Tool object configured for Reddit search.
    """
    return Tool(
        name="reddit_search",
        func=lambda input_text: reddit_search_tool_run(
            input_text,
            client_id,
            client_secret,
            user_agent,
            subreddit,
            time_filter,
            sort,
            limit,
        ),
        description=(
            "Use this tool to search Reddit with specific parameters. "
            "Provide the search query as input."
        )
    )

# Step 3: Define the function to handle queries and tool execution
def run_query_with_action_handling(openai_api_key, prompt, memory, tools, input_text):
    """
    This function handles the query and tool execution.
    Args:
        openai_api_key (str): The OpenAI API key.
        prompt (BasePromptTemplate): The prompt template for the LLM.
        memory (ConversationBufferMemory): The conversation memory.
        tools (list): List of available tools.
        input_text (str): The input text for the query.

    Returns:
        str: The response from the agent, which may include tool execution results.
    """
    print("Running query with action handling")

    llm = ChatOpenAI(temperature=0, openai_api_key=openai_api_key)

    llm_chain = LLMChain(llm=llm, prompt=prompt)
    agent = StructuredChatAgent(llm_chain=llm_chain, verbose=True, tools=tools)
    agent_chain = AgentExecutor.from_agent_and_tools(
        agent=agent, verbose=True, memory=memory, tools=tools
    )

    # Invoke the agent chain with the memory being passed into the input
    response = agent_chain.invoke({"input": input_text})
    
    # Check if the response contains an action
    if "actions" in response:
        actions = response["actions"]
        for action in actions:
            tool_name = action[0]
            tool_input = action[1]
            if tool_name == "reddit_search":
                # Execute the Reddit search tool
                reddit_tool = next(tool for tool in tools if tool.name == "reddit_search")
                search_result = reddit_tool.run(tool_input)
                
                # After executing, return the result back to the conversation
                return f"Search result: {search_result}\n\nAgent's response: {response['output']}"
    
    # If no action, just return the agent's regular response
    return response['output']

# Step 4: Modify the main function to accept additional parameters
def query_reddit(openai_api_key, reddit_client_id, reddit_client_secret, reddit_user_agent, query_text=None, file_path=None, subreddit=None, time_filter=None, sort=None, limit=10):
    """
    This function handles the query and tool execution.
    Args:
        openai_api_key (str): The OpenAI API key.
        reddit_client_id (str): The Reddit client ID.
        reddit_client_secret (str): The Reddit client secret.
        reddit_user_agent (str): The Reddit user agent.
        query_text (str): The text query to be used.
        file_path (str): Path to the file containing the query.
        subreddit (str): The subreddit to filter results.
        time_filter (str): The time filter for results.
        sort (str): The sort order for results.
        limit (int): The maximum number of results to retrieve.

    Returns:
        str: The response from the agent, which may include tool execution results.
    """
    # Load the query text from string or file
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as file:
            input_text = file.read().strip()
    elif query_text:
        input_text = query_text
    else:
        raise ValueError("Either query_text or file_path must be provided.")

    # Get the Reddit Search tool
    reddit_tool = get_reddit_tool(
        reddit_client_id, reddit_client_secret, reddit_user_agent, subreddit, time_filter, sort, limit
    )
    
    tools = [reddit_tool]  # Add more tools here if needed
    
    # Memory for the conversation to persist across inputs
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    # Generate prompt for the current input with memory included
    prompt, _ = create_prompt(input_text, tools, openai_api_key)

    # Get the agent's response, handling tools/actions if needed
    response = run_query_with_action_handling(
        openai_api_key,
        prompt,
        memory,
        tools,
        input_text
    )
    
    return response

# Step 5: Optionally, allow command line or predefined variables for testing
if __name__ == "__main__":
    import argparse

    # Load environment variables
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path)
    
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT")

    # Predefined variables for testing
    TEST_MODE = True  # Change to False to use command-line arguments
    if TEST_MODE:
        # query_text = "What are the best Python libraries for data analysis?"
        query_text = "I have a creature with the following text: Whenever Ghost of Ramirez DePietro deals combat damage to a player, choose up to one target card in a graveyard that was discarded or put there from a library this turn. Put that card into its owner's hand. I have another creature with the text: 'Whenever one or more Pirates you control deal damage to a player, Francisco explores.' Can I return a card put into my graveyard by the explore ability with the first ability? Ramirez is a pirate."
        # subreddit = "python"
        subreddit = "mtgrules"
        time_filter = "year"
        sort = "top"
        limit = '5'
        result = query_reddit(
            openai_api_key=OPENAI_API_KEY,
            reddit_client_id=REDDIT_CLIENT_ID,
            reddit_client_secret=REDDIT_CLIENT_SECRET,
            reddit_user_agent=REDDIT_USER_AGENT,
            query_text=query_text,
            subreddit=subreddit,
            time_filter=time_filter,
            sort=sort,
            limit=limit
        )
        print(f"\nQuery result:\n{result}")
    else:
        # CLI argument parsing
        parser = argparse.ArgumentParser(description="Query Reddit with a string or file.")
        parser.add_argument("--query_text", type=str, help="The text query to be used.")
        parser.add_argument("--file_path", type=str, help="Path to the file containing the query.")
        parser.add_argument("--subreddit", type=str, help="The subreddit to filter results.")
        parser.add_argument("--time_filter", type=str, choices=["hour", "day", "week", "month", "year", "all"], help="The time filter for results.")
        parser.add_argument("--sort", type=str, choices=["relevance", "hot", "top", "new", "comments"], help="The sort order for results.")
        parser.add_argument("--limit", type=int, default=10, help="The maximum number of results to retrieve.")

        args = parser.parse_args()

        # Ensure either query_text or file_path is provided
        if not args.query_text and not args.file_path:
            raise ValueError("Either --query_text or --file_path must be provided.")

        # Run the Reddit query
        result = query_reddit(
            openai_api_key=OPENAI_API_KEY,
            reddit_client_id=REDDIT_CLIENT_ID,
            reddit_client_secret=REDDIT_CLIENT_SECRET,
            reddit_user_agent=REDDIT_USER_AGENT,
            query_text=args.query_text,
            file_path=args.file_path,
            subreddit=args.subreddit,
            time_filter=args.time_filter,
            sort=args.sort,
            limit=args.limit
        )

        # Print the result
        print(f"\nQuery result:\n{result}")

# python utils/query_reddit.py --query_text "How much protein should I be getting as a 30 year old, 200lb male?"

# python utils/query_reddit.py --query_text "I have a creature with the following text: Whenever Ghost of Ramirez DePietro deals combat damage to a player, choose up to one target card in a graveyard that was discarded or put there from a library this turn. Put that card into its owner's hand. I have another creature with the text: 'Whenever one or more Pirates you control deal damage to a player, Francisco explores.' Can I return a card put into my graveyard by the explore ability with the first ability? Ramirez is a pirate."