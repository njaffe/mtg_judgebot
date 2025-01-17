# Magic: The Gathering AI Judge

An AI-powered tool designed to assist with complex rules scenarios and edge cases in Magic: The Gathering.

## Table of Contents

- Overview
- Features
- Installation
- Usage
- Project Structure
- Future Improvements
- Contributing
- License

## Overview

This project implements a Retrieval-Augmented Generation (RAG) system to create an AI “judge” for Magic: The Gathering (MTG). The tool helps players and enthusiasts navigate the complex rules and edge cases that often arise in the game. By leveraging large language models (LLMs) and a comprehensive rules database, this AI judge provides quick and accurate answers to MTG-related queries.

The system uses agents within the RAG framework to query various sources, including a custom database of MTG rules, as well as external platforms like Reddit and Google, to gather relevant context and insights. The AI then generates a combined answer, ensuring players have access to both authoritative rules information and community perspectives.

## Features

- RAG-based query system: Utilizes the entire MTG rules corpus (approximately 148,000 words).
- Integration with external sources: Queries Reddit and Google for additional context and community insights.
- Multi-source answer compilation: Combines results from the rules corpus, Reddit, and Google searches for more robust answers.
- Agent-based architecture: Uses agents as part of the RAG framework to optimize information retrieval and answer generation.
- Natural language processing: Understands and responds to MTG-specific queries in natural language, providing intuitive answers.

## Installation

### Prerequisites

- Python 3.7+
- Environment variables configured (see .env file for API keys)

### Steps

1.	Clone the repository:

	`git clone https://github.com/your-repo/mtg-ai-judge.git`

	`cd mtg-ai-judge`

2.	Install the required packages:

	`pip install -r requirements.txt`

3.	Set up your environment variables in a .env file (refer to the .env.sample file in the repo):

	`OPENAI_API_KEY=your_openai_api_key`

	`GOOGLE_CSE_ID=your_google_cse_id`

	`GOOGLE_API_KEY=your_google_api_key`

	`REDDIT_CLIENT_ID=your_reddit_client_id`

	`REDDIT_CLIENT_SECRET=your_reddit_client_secret`

	`REDDIT_USER_AGENT=your_reddit_user_agent`

## Usage

### Running the Application

You can run the application from the command line:
`python src/main.py`

Alternatively, you can run it using gunicorn for production environments:
`gunicorn -w 4 src.main:app
`
The AI Judge is now live and can be accessed via HTTP endpoints.

### Querying the Judge

You can input your query either directly through the command line or by interacting with the provided API.

Example usage:

```bash
python src/main.py --query_text "I have a creature with the following text: Whenever Ghost of Ramirez DePietro deals combat damage to a player, choose up to one target card in a graveyard that was discarded or put there from a library this turn. Put that card into its owner's hand. I have another creature with the text: 'Whenever one or more Pirates you control deal damage to a player, Francisco explores.' Can I return a card put into my graveyard by the explore ability with the first ability? Ramirez is a pirate."
```

### Project Structure

- `src/`: Contains the source code for querying, processing, and generating responses.
- `utils/`: Contains helper functions like querying Google, Reddit, and managing the RAG database.
- `.env`: Configuration file containing API keys and other sensitive information.
- `requirements.txt`: List of Python dependencies.

### Future Improvements

- Expand the search size so that more reddit and google results can be returned.
- Improve search criteria for Reddit
- Improve response accuracy by fine-tuning the LLM on more specific MTG scenarios.
	- I believe there are comprehension issues with Magic rules, possibly caused by words having multiple meanings. For example, "Explore" is a Magic keyword but also a real English word.
- Add support for real-time querying via a web interface.

### Contributing

Contributions are welcome! Please fork the repository, create a new branch, and submit a pull request.

### License

This project is licensed under the MIT License.