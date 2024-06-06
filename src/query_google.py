# Adapted code from /docs/modules/agents/how_to/sharedmemory_for_tools
# see: https://python.langchain.com/v0.2/docs/integrations/tools/google_search/
# custom API: https://console.cloud.google.com/apis/api/customsearch.googleapis.com/metrics?project=noah-242316
# keys: https://console.cloud.google.com/apis/credentials?pli=1&project=noah-242316

import os
import sys
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, StructuredChatAgent
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory, ReadOnlySharedMemory
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from config import API_KEY
from utils.query_tools import create_prompt, run_query

def get_google_tool(
    google_cse_id,
    google_api_key):

    search = GoogleSearchAPIWrapper()

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


    google_tool = get_google_tool(google_cse_id,google_api_key)
    tools = [
        google_tool
    ]   
    prompt,memory = create_prompt(INPUT, tools, openai_api_key)
    run_query(openai_api_key,prompt,memory,tools, INPUT)