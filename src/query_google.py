# Adapted code from /docs/modules/agents/how_to/sharedmemory_for_tools
# see: https://python.langchain.com/v0.2/docs/integrations/tools/reddit_search/

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

def get_google_tool(
    client_id,
    client_secret,
    user_agent):

    search = GoogleSearchAPIWrapper(
        google_cse_id,
        google_api_key)

    google_tool = Tool(
        name="google_search",
        description="Search Google for recent results.",
        func=search.run,
    )

    return google_tool

if __name__ == "__main__":

    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path) # Load environment variables
    
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    
    google_cse_id = os.environ.get("GOOGLE_CSE_ID")
    google_api_key = os.environ.get("GOOGLE_API_KEY")

    INPUT = "what is the most popular mtg commander?"


    google_tool = get_google_tool(google_client_id,google_client_secret,google_user_agent)
    tools = [
        google_tool
    ]   
    prompt,memory = create_prompt(INPUT, tools, openai_api_key)
    run_query(openai_api_key,prompt,memory,tools, INPUT)

# NEXT: GET IDS