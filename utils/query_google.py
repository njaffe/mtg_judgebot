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

# Step 3: Define the main function to run the conversation loop
def query_google(openai_api_key, google_cse_id, google_api_key):
    
    # Get the Google Search tool
    google_tool = get_google_tool(google_cse_id, google_api_key)
    
    tools = [google_tool]  # Add more tools here if needed
    
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
    GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")
    GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

    # Start the conversation loop
    query_google(
        openai_api_key=OPENAI_API_KEY,
        google_cse_id=GOOGLE_CSE_ID,
        google_api_key=GOOGLE_API_KEY
    )

# What is the most popular creature used as a commander in the Magic: the Gathering commander format?