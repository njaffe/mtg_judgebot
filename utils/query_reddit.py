from langchain_community.tools.reddit_search.tool import RedditSearchRun, RedditSearchSchema
from langchain_community.utilities.reddit_search import RedditSearchAPIWrapper

client_id = ""
client_secret = ""
user_agent = ""

search = RedditSearchRun(
    api_wrapper=RedditSearchAPIWrapper(
        reddit_client_id=client_id,
        reddit_client_secret=client_secret,
        reddit_user_agent=user_agent,
    )
)

QUERY="coolest mtg commanders"
search_params = RedditSearchSchema(
    query=QUERY, sort="new", time_filter="week", subreddit="python", limit="2"
)

result = search.run(tool_input=search_params.dict())

print(result)