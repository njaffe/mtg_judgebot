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
from langchain_core.prompts import PromptTemplate,ChatPromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))

from config import API_KEY

def query_reddit(input):


    # template = """This is a conversation between a human and a bot:

    # {chat_history}

    # Write a summary of the conversation for {input}:
    # """

    # prompt = PromptTemplate(input_variables=["input", "chat_history"], template=template)
    # memory = ConversationBufferMemory(memory_key="chat_history")

    # prefix = """Have a conversation with a human, answering the following questions as best you can. You have access to the following tools:"""
    # suffix = """Begin!"

    # {chat_history}
    # Question: {input}
    # {agent_scratchpad}"""


    reddit_tool = RedditSearchRun(
            api_wrapper=RedditSearchAPIWrapper(
                reddit_client_id=client_id,
                reddit_client_secret=client_secret,
                reddit_user_agent=user_agent,
            )
        )
    tools = [
        reddit_tool
    ]

    # prompt = StructuredChatAgent.create_prompt(
    #     prefix=prefix,
    #     tools=tools,
    #     suffix=suffix,
    #     input_variables=["input", "chat_history", "agent_scratchpad"]
    # )
    prompt = f"answer the following quesion: {input}. You have access to the following tools: {tools}"
    
    prompt = ChatPromptTemplate.from_template("answer the following quesion: {input}. You have access to the following tools: {tools}")

    model = ChatOpenAI(temperature=0, openai_api_key=openai_api_key)

    llm_chain = prompt | model
    # agent = AgentExecutor(llm_chain=llm_chain, memory=memory, tools=[tools], verbose=True)

    # llm_chain = LLMChain(llm=llm, prompt=prompt)
    # agent = StructuredChatAgent(llm_chain=llm_chain, verbose=True, tools=tools)
    # agent_exec = AgentExecutor.from_agent_and_tools(
    #     agent=agent, verbose=True, memory=memory, tools=tools
    # )
    response = llm_chain.invoke({"input":input, "tools":reddit_tool})

    process_info = response
    answer = response['output']
    print(f"Answer: {answer}")
    return answer

if __name__ == "__main__":
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path) # Load environment variables
    # Provide keys for Reddit
    client_id = os.get.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT")
    # Provide key for OpenAI
    openai_api_key = os.environ.get("OPENAI_API_KEY")

    INPUT = "what is the most popular mtg commander?"

    query_reddit(INPUT)