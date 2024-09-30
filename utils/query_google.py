import os
import sys
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, StructuredChatAgent
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_google_community import GoogleSearchAPIWrapper
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from config import API_KEY
from utils.query_tools import create_prompt

# Step 1: Define the function to get the Google Search tool
def get_google_tool(google_cse_id, google_api_key):
    search = GoogleSearchAPIWrapper()
    google_tool = Tool(
        name="google_search",
        description="Search Google for recent results.",
        func=search.run,
    )
    return google_tool

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
        if action == "google_search":
            # Execute the search tool
            search_tool = next(tool for tool in tools if tool.name == "google_search")
            search_result = search_tool.func(action_input)
            
            # After executing, return the result back to the conversation
            return f"Search result: {search_result}"
    
    # If no action, just return the agent's regular response
    return response['output']

# Step 3: Modify the main function to accept query text or a file
def query_google(openai_api_key, google_cse_id, google_api_key, query_text=None, file_path=None):
    
    # Load the query text from string or file
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as file:
            input_text = file.read().strip()
    elif query_text:
        input_text = query_text
    else:
        raise ValueError("Either query_text or file_path must be provided.")

    # Get the Google Search tool
    google_tool = get_google_tool(google_cse_id, google_api_key)
    
    tools = [google_tool]  # Add more tools here if needed
    
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

    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path)
    
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

    # CLI argument parsing
    parser = argparse.ArgumentParser(description="Query Google with a string or file.")
    parser.add_argument("--query_text", type=str, help="The text query to be used.")
    parser.add_argument("--file_path", type=str, help="Path to the file containing the query.")

    args = parser.parse_args()

    # Ensure either query_text or file_path is provided
    if not args.query_text and not args.file_path:
        raise ValueError("Either --query_text or --file_path must be provided.")

    # Run the Google query
    result = query_google(
        openai_api_key=OPENAI_API_KEY,
        google_cse_id=GOOGLE_CSE_ID,
        google_api_key=GOOGLE_API_KEY,
        query_text=args.query_text,
        file_path=args.file_path
    )

    # Print the result
    print(f"\nQuery result:\n{result}")