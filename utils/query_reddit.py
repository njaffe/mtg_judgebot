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

def query_reddit(input):

    template = """This is a conversation between a human and a bot:

    {chat_history}

    Write a summary of the conversation for {input}:
    """

    prompt = PromptTemplate(input_variables=["input", "chat_history"], template=template)
    memory = ConversationBufferMemory(memory_key="chat_history")

    prefix = """Have a conversation with a human, answering the following questions as best you can. You have access to the following tools:"""
    suffix = """Begin!"

    {chat_history}
    Question: {input}
    {agent_scratchpad}"""

    tools = [
        RedditSearchRun(
            api_wrapper=RedditSearchAPIWrapper(
                reddit_client_id=client_id,
                reddit_client_secret=client_secret,
                reddit_user_agent=user_agent,
            )
        )
    ]

    prompt = StructuredChatAgent.create_prompt(
        prefix=prefix,
        tools=tools,
        suffix=suffix,
        input_variables=["input", "chat_history", "agent_scratchpad"],
    )

    llm = ChatOpenAI(temperature=0, openai_api_key=openai_api_key)

    llm_chain = LLMChain(llm=llm, prompt=prompt)
    agent = StructuredChatAgent(llm_chain=llm_chain, verbose=True, tools=tools)
    agent_chain = AgentExecutor.from_agent_and_tools(
        agent=agent, verbose=True, memory=memory, tools=tools
    )
    response = agent_chain.invoke(input=input)
    # print("\nresponse")
    # print(response.items())
    # print("\n")

    process_info = response
    answer = response['output']
    print(f"Answer: {answer}")
    return answer

if __name__ == "__main__":
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path) # Load environment variables
    # Provide keys for Reddit
    client_id = "32_DLorJfTVxuoLkPXGPGQ"
    client_secret = "X-y5QFr3qBv7CpCxN5t6PQ2yZo53wQ"
    user_agent = "mtg_judge_bot"
    # Provide key for OpenAI
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    INPUT = "what is the most popular mtg commander?"

    query_reddit(INPUT)
# this works but is technically deprecated. New runnable version does not seem to work with tools yet.