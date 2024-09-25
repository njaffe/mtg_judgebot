# Adapted code from /docs/modules/agents/how_to/sharedmemory_for_tools
# see: https://python.langchain.com/v0.2/docs/integrations/tools/reddit_search/
# keys: https://www.reddit.com/prefs/apps

# import os
# import sys
# from dotenv import load_dotenv
# from langchain.agents import AgentExecutor, StructuredChatAgent
# from langchain.chains import LLMChain
# from langchain.memory import ConversationBufferMemory, ReadOnlySharedMemory
# from langchain_community.tools.reddit_search.tool import RedditSearchRun
# from langchain_community.utilities.reddit_search import RedditSearchAPIWrapper
# from langchain_core.prompts import PromptTemplate
# from langchain_core.tools import Tool
# from langchain_openai import ChatOpenAI

# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

# from config import API_KEY
# from utils.query_tools import create_prompt, run_query

# def get_reddit_tool(
#     client_id,
#     client_secret,
#     user_agent):

#     reddit_tool = RedditSearchRun(
#                 api_wrapper=RedditSearchAPIWrapper(
#                     reddit_client_id=client_id,
#                     reddit_client_secret=client_secret,
#                     reddit_user_agent=user_agent,
#                 )
#             )

#     return reddit_tool

# def query_reddit(
#     input,
#     openai_api_key,
#     reddit_client_id,
#     reddit_client_secret,
#     reddit_user_agent):
    
#     # input = "what is the most popular creature used as a commander in the Magic: the Gathering commander format?"
#     if input:
#         reddit_tool = get_reddit_tool(
#             reddit_client_id,
#             reddit_client_secret,
#             reddit_user_agent)
        
#         tools = [
#             reddit_tool
#         ]   
        
#         prompt,memory = create_prompt(
#             input,
#             tools,
#             openai_api_key)
        
#         run_query(
#             openai_api_key,
#             prompt,
#             memory,
#             tools,
#             input)
#     else:
#         print("No input provided. Exiting...")

# if __name__ == "__main__":
#     dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
#     load_dotenv(dotenv_path) # Load environment variables
    
#     OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

#     REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
#     REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
#     REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT")

#     input = """I have a creature with the following text: 
#             Whenever Ghost of Ramirez DePietro deals combat damage to a player, 
#             choose up to one target card in a graveyard that was discarded or put there from a library this turn. 
#             Put that card into its owner's hand.' I have another creature with the text: 
#             'Whenever one or more Pirates you control deal damage to a player, Francisco explores.' 

#             Can I return a card put into my graveyard by the explore ability with the first ability? 
#             Ramirez is a pirate. "
#             """

#     query_reddit(
#         input=input,
#         openai_api_key=OPENAI_API_KEY,
#         reddit_client_id=REDDIT_CLIENT_ID,
#         reddit_client_secret=REDDIT_CLIENT_SECRET,
#         reddit_user_agent=REDDIT_USER_AGENT)

# this WORKS but is technically deprecated. New runnable version does not seem to work with tools yet.

import os
import sys
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, StructuredChatAgent
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_community.tools.reddit_search.tool import RedditSearchRun
from langchain_community.utilities.reddit_search import RedditSearchAPIWrapper
from langchain_core.prompts import PromptTemplate
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

# Step 3: Define the main function to run the conversation loop
def query_reddit(openai_api_key, reddit_client_id, reddit_client_secret, reddit_user_agent):
    
    # Get the Reddit Search tool
    reddit_tool = get_reddit_tool(reddit_client_id, reddit_client_secret, reddit_user_agent)
    
    tools = [reddit_tool]  # Add more tools here if needed
    
    # Memory for the conversation to persist across inputs
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    # Keep the conversation running in a loop
    while True:
        input_text = input("You: ")  # Get user input from the terminal
        
        if input_text.lower() in ['exit', 'quit', 'q']:
            print("Conversation ended.")
            break  # Exit the loop if the user wants to end the conversation
        
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
        
        print(f"Agent: {response}")  # Now we only print once

# Step 4: Run the script with environment variables
if __name__ == "__main__":

    # Load environment variables
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path)
    
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT")

    # Example input
    input_text = """I have a creature with the following text: 
    Whenever Ghost of Ramirez DePietro deals combat damage to a player, 
    choose up to one target card in a graveyard that was discarded or put there from a library this turn. 
    Put that card into its owner's hand.' I have another creature with the text: 
    'Whenever one or more Pirates you control deal damage to a player, Francisco explores.' 
    Can I return a card put into my graveyard by the explore ability with the first ability? 
    Ramirez is a pirate."""

    # Start the conversation loop
    query_reddit(
        openai_api_key=OPENAI_API_KEY,
        reddit_client_id=REDDIT_CLIENT_ID,
        reddit_client_secret=REDDIT_CLIENT_SECRET,
        reddit_user_agent=REDDIT_USER_AGENT
    )