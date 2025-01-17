import os
import sys
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, StructuredChatAgent
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from langchain_community.tools.reddit_search.tool import RedditSearchRun, RedditSearchSchema
from langchain_community.utilities.reddit_search import RedditSearchAPIWrapper
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))

from config import API_KEY
from utils.langchain_query_tools import create_prompt


class TokenLimitedConversationMemory(ConversationBufferMemory):
    def __init__(self, max_token_limit, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._max_token_limit = max_token_limit  # Use a private variable to avoid Pydantic validation issues

    @property
    def max_token_limit(self):
        return self._max_token_limit

    def trim_history(self):
        """
        Trims the chat history to ensure it stays within the token limit.
        """
        total_tokens = 0
        trimmed_history = []
        for message in reversed(self.chat_memory.messages):  # Use `chat_memory.messages`
            message_tokens = len(message.content.split())  # Approximate token count
            if total_tokens + message_tokens > self.max_token_limit:
                break
            trimmed_history.append(message)
            total_tokens += message_tokens
        self.chat_memory.messages = list(reversed(trimmed_history))  # Update the message history


def reddit_search_tool_run(input_text, client_id, client_secret, user_agent, subreddit=None, time_filter=None, sort=None, limit=10):
    """
    Executes a Reddit search based on the input query and parameters.
    """


    search_params = RedditSearchSchema(
        query=input_text,
        subreddit=subreddit,
        time_filter=time_filter,
        sort=sort,
        limit=limit
    )
    api_wrapper = RedditSearchAPIWrapper(
        reddit_client_id=client_id,
        reddit_client_secret=client_secret,
        reddit_user_agent=user_agent,
    )
    reddit_tool = RedditSearchRun(api_wrapper=api_wrapper)
    return reddit_tool.run(search_params.dict())


def get_reddit_tool(client_id, client_secret, user_agent, subreddit=None, time_filter=None, sort=None, limit=10):
    """
    Returns a Tool object configured for Reddit search.
    """
    return Tool(
        name="reddit_search",
        func=lambda input_text: reddit_search_tool_run(
            input_text,
            client_id,
            client_secret,
            user_agent,
            subreddit,
            time_filter,
            sort,
            limit,
        ),
        description=(
            "Use this tool to search Reddit with specific parameters. "
            "Provide the search query as input."
        )
    )


def truncate_input(input_text, max_tokens=1000):
    """
    Truncates input text to ensure it stays within the token limit.
    """
    words = input_text.split()
    return " ".join(words[:max_tokens])


def run_query_with_action_handling(openai_api_key, prompt, memory, tools, input_text):
    """
    This function handles the query and tool execution while respecting the context length.
    """
    print("Running query with action handling")

    llm = ChatOpenAI(temperature=0, openai_api_key=openai_api_key, max_tokens=3000)

    # Truncate the input text
    input_text = truncate_input(input_text, max_tokens=1000)

    # Trim history if needed
    if hasattr(memory, "trim_history"):
        memory.trim_history()

    llm_chain = LLMChain(llm=llm, prompt=prompt)
    agent = StructuredChatAgent(llm_chain=llm_chain, verbose=True, tools=tools)
    agent_chain = AgentExecutor.from_agent_and_tools(
        agent=agent, verbose=True, memory=memory, tools=tools
    )

    # Invoke the agent chain
    response = agent_chain.invoke({"input": input_text})
    return response.get("output", "No output generated.")


def query_reddit(openai_api_key, reddit_client_id, reddit_client_secret, reddit_user_agent, query_text=None, file_path=None, subreddit=None, time_filter=None, sort=None, limit=10):
    """
    This function handles the query and tool execution.
    """
    # Load the query text from string or file
    if file_path and os.path.exists(file_path):
        with open(file_path, 'r') as file:
            input_text = file.read().strip()
    elif query_text:
        input_text = query_text
    else:
        raise ValueError("Either query_text or file_path must be provided.")

    # ensure inputs are strings
    input_text = str(input_text)
    subreddit = str(subreddit) if subreddit else None
    time_filter = str(time_filter) if time_filter else None
    sort = str(sort) if sort else None
    limit = str(limit) if limit else '10'

    # Get the Reddit Search tool
    reddit_tool = get_reddit_tool(
        reddit_client_id, reddit_client_secret, reddit_user_agent, subreddit, time_filter, sort, limit
    )
    
    tools = [reddit_tool]  # Add more tools here if needed
    
    # Memory for the conversation to persist across inputs
    memory = TokenLimitedConversationMemory(max_token_limit=3000, memory_key="chat_history", return_messages=True)
    
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


if __name__ == "__main__":
    import argparse

    # Load environment variables
    dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    load_dotenv(dotenv_path)
    
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

    TEST_MODE = True  # Set to False to enable CLI mode

    if TEST_MODE:
        query_text = "I have a creature (Ghost of Ramirez dePietro) with the following text: Whenever Ghost of Ramirez DePietro deals combat damage to a player, choose up to one target card in a graveyard that was discarded or put there from a library this turn. Put that card into its owner's hand. I have another creature with the text: 'Whenever one or more Pirates you control deal damage to a player, Francisco explores.' Can I return a card put into my graveyard by the explore ability with the first ability? Ramirez is a pirate."
        subreddit = "mtgrules"
        time_filter = "year"
        sort = "top"
        limit = 15

        result = query_reddit(
            openai_api_key=OPENAI_API_KEY,
            reddit_client_id=REDDIT_CLIENT_ID,
            reddit_client_secret=REDDIT_CLIENT_SECRET,
            reddit_user_agent=REDDIT_USER_AGENT,
            query_text=query_text,
            subreddit=subreddit,
            time_filter=time_filter,
            sort=sort,
            limit=limit
        )
        print(f"\nQuery result:\n{result}")
    else:
        parser = argparse.ArgumentParser(description="Query Reddit with a string or file.")
        parser.add_argument("--query_text", type=str, help="The text query to be used.")
        parser.add_argument("--file_path", type=str, help="Path to the file containing the query.")
        parser.add_argument("--subreddit", type=str, help="The subreddit to filter results.")
        parser.add_argument("--time_filter", type=str, choices=["hour", "day", "week", "month", "year", "all"], help="The time filter for results.")
        parser.add_argument("--sort", type=str, choices=["relevance", "hot", "top", "new", "comments"], help="The sort order for results.")
        parser.add_argument("--limit", type=int, default=10, help="The maximum number of results to retrieve.")

        args = parser.parse_args()

        result = query_reddit(
            openai_api_key=OPENAI_API_KEY,
            reddit_client_id=REDDIT_CLIENT_ID,
            reddit_client_secret=REDDIT_CLIENT_SECRET,
            reddit_user_agent=REDDIT_USER_AGENT,
            query_text=args.query_text,
            file_path=args.file_path,
            subreddit=args.subreddit,
            time_filter=args.time_filter,
            sort=args.sort,
            limit=args.limit
        )

        print(f"\nQuery result:\n{result}")

# python utils/query_reddit.py --query_text "How much protein should I be getting as a 30 year old, 200lb male?"

# python utils/query_reddit.py --query_text "I have a creature with the following text: Whenever Ghost of Ramirez DePietro deals combat damage to a player, choose up to one target card in a graveyard that was discarded or put there from a library this turn. Put that card into its owner's hand. I have another creature with the text: 'Whenever one or more Pirates you control deal damage to a player, Francisco explores.' Can I return a card put into my graveyard by the explore ability with the first ability? Ramirez is a pirate."