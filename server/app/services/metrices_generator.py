"""
Metrics to get from what the database give

 Brand mention per query - against competitors - every 100 queries.
    - Divide across LLMS - Gpt x%, Gemini y%

- Answers citing company website per total mention
    E.g. Dell. How many were mentioned by chat were from the company website.
    - Which other domains do the AI get info about the product

- Ranking among competitors  - DONE
    - mentions and for links per query (...)
    - Top Recommendation Rate
    - Ranking

- Factual score - DONE
    - Links Based on AI output about A Link/product vs actual content. if it's related, if it contains the valid info

- Errors - DONE
    Link route | error code/type

Output these metrics based on models in the db. Get the insights from thoughs models
"""
