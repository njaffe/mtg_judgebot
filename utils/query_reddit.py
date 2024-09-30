import os
import sys
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, StructuredChatAgent
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_community.tools.reddit_search.tool import RedditSearchRun
from langchain_community.utilities.reddit_search import RedditSearchAPIWrapper
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from config import API_KEY
from utils.query_tools import create_prompt

# Step 1: Define the function to get the Reddit Search tool
def get_reddit_tool(client_id, client_secret, user_agent):
    reddit_tool = RedditSearchRun(
        api_wrapper=RedditSearchAPIWrapper(
            reddit_client_id=client_id,
            reddit_client_secret=client_secret,
            reddit_user_agent=user_agent,
        )
    )
    return reddit_tool

# Step 2: Define the function to handle queries and tool execution
def run_query_with_action_handling(openai_api_key, prompt, memory, tools, input_text):

    llm = ChatOpenAI(temperature=0, openai_api_key=openai_api_key)

    llm_chain = LLMChain(llm=llm, prompt=prompt)
    agent = StructuredChatAgent(llm_chain=llm_chain, verbose=True, tools=tools)
    agent_chain = AgentExecutor.from_agent_and_tools(
        agent=agent, verbose=True, memory=memory, tools=tools
    )

    # Invoke the agent chain with the memory being passed into the input
    response = agent_chain.invoke(input=input_text)
    
    # Handle tool actions within the response
    if "action" in response:
        action = response["action"]
        action_input = response.get("action_input", "")
        if action == "reddit_search":
            # Execute the Reddit search tool
            reddit_tool = next(tool for tool in tools if tool.name == "reddit_search")
            search_result = reddit_tool.func(action_input)
            
            # After executing, return the result back to the conversation
            return f"Search result: {search_result}"
    
    # If no action, just return the agent's regular response
    return response['output']

# Step 3: Modify the main function to accept query text or a file
def query_reddit(openai_api_key, reddit_client_id, reddit_client_secret, reddit_user_agent, query_text=None, file_path=None):
    
    # Load the query text from string or file
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as file:
            input_text = file.read().strip()
    elif query_text:
        input_text = query_text
    else:
        raise ValueError("Either query_text or file_path must be provided.")

    # Get the Reddit Search tool
    reddit_tool = get_reddit_tool(reddit_client_id, reddit_client_secret, reddit_user_agent)
    
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

# Step 4: Optionally, allow command line usage
if __name__ == "__main__":
    import argparse

    # Load environment variables
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path)
    
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT")

    # CLI argument parsing
    parser = argparse.ArgumentParser(description="Query Reddit with a string or file.")
    parser.add_argument("--query_text", type=str, help="The text query to be used.")
    parser.add_argument("--file_path", type=str, help="Path to the file containing the query.")

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
        file_path=args.file_path
    )

    # Print the result
    print(f"\nQuery result:\n{result}")