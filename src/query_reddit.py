# Adapted code from /docs/modules/agents/how_to/sharedmemory_for_tools
# see: https://python.langchain.com/v0.2/docs/integrations/tools/reddit_search/
# keys: https://www.reddit.com/prefs/apps

import os
import sys
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, StructuredChatAgent
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory, ReadOnlySharedMemory
from langchain_community.tools.reddit_search.tool import RedditSearchRun
from langchain_community.utilities.reddit_search import RedditSearchAPIWrapper
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from config import API_KEY
from utils.query_tools import create_prompt, run_query

def get_reddit_tool(
    client_id,
    client_secret,
    user_agent):

    reddit_tool = RedditSearchRun(
                api_wrapper=RedditSearchAPIWrapper(
                    reddit_client_id=client_id,
                    reddit_client_secret=client_secret,
                    reddit_user_agent=user_agent,
                )
            )

    return reddit_tool

def query_reddit(
    input,
    openai_api_key,
    reddit_client_id,
    reddit_client_secret,
    reddit_user_agent):
    
    # INPUT = "what is the most popular creature used as a commander in the Magic: the Gathering commander format?"
    if input:
        reddit_tool = get_reddit_tool(
            reddit_client_id,
            reddit_client_secret,
            reddit_user_agent)
        
        tools = [
            reddit_tool
        ]   
        
        prompt,memory = create_prompt(
            input,
            tools,
            openai_api_key)
        
        run_query(
            openai_api_key,
            prompt,
            memory,
            tools,
            input)
    else:
        print("No input provided. Exiting...")

if __name__ == "__main__":
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path) # Load environment variables
    
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

    REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.environ.get("REDDIT_USER_AGENT")

    INPUT = "what is the most popular mtg commander?"

    query_reddit(
        input=INPUT,
        openai_api_key=OPENAI_API_KEY,
        reddit_client_id=REDDIT_CLIENT_ID,
        reddit_client_secret=REDDIT_CLIENT_SECRET,
        reddit_user_agent=REDDIT_USER_AGENT)

# this WORKS but is technically deprecated. New runnable version does not seem to work with tools yet.