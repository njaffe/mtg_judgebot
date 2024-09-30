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
# Add paths for utilities and source files
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def create_prompt(
    input,
    tools,
    openai_api_key):
    template = """This is a conversation between a human and a bot:

    {chat_history}

    Write a summary of the conversation for {input}:
    """

    memory = ConversationBufferMemory(memory_key="chat_history")

    prefix = """Have a conversation with a human, answering the following questions as best you can. You have access to the following tools:"""
    suffix = """Begin!"

    {chat_history}
    Question: {input}
    {agent_scratchpad}"""

    prompt = StructuredChatAgent.create_prompt(
        prefix=prefix,
        tools=tools, # an arg
        suffix=suffix,
        input_variables=["input", "chat_history", "agent_scratchpad"],
    )    
    return prompt, memory

def run_query(openai_api_key, prompt, memory, tools, input_text):

    llm = ChatOpenAI(temperature=0, openai_api_key=openai_api_key)

    llm_chain = LLMChain(llm=llm, prompt=prompt)
    agent = StructuredChatAgent(llm_chain=llm_chain, verbose=True, tools=tools)
    agent_chain = AgentExecutor.from_agent_and_tools(
        agent=agent, verbose=True, memory=memory, tools=tools
    )

    response = agent_chain.invoke(input=input_text)

    # Returning the entire response object, but no print statement here
    return response['output']

if __name__ == "__main__":
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    tools = [RedditSearchRun(), RedditSearchAPIWrapper()]
    input = "What is the best way to cook a steak?"

    prompt, memory = create_prompt(input, tools, openai_api_key)
    run_query(openai_api_key, prompt, memory, tools, input)