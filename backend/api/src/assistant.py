import openai, json, logging, os

logger = logging.getLogger(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")

def answer_question(balance_data, question):
    """
    Use OpenAI's API to answer a question about the given balance sheet data.
    balance_data: dict (e.g., output of generate_balance_sheet)
    question: str, the user's question about the data
    Returns: str answer from the AI assistant.
    """
    # prepare the chat prompt
    system_message = {
        "role": "system",
        "content": """You are a helpful financial assistant who answers questions about a company's balance sheet and analytics.
          Provide clear, concise explanations backed up by business facts and examples in order to make the user understand
          your feedback as clearly as possible. Identify possible weak links in the companmy's product lines, unneccessary or excessive spending,
          or redundant purchases, in order to make even more positive contributions to the company. """
    }
    # include the balance sheet data as JSON in the user prompt
    data_json = json.dumps(balance_data, indent=2)
    user_prompt = f"Use the following balance sheet data to answer the question.\nBalance Sheet Data:\n```json\n{data_json}\n```\nQuestion: {question}"
    # make prompt for unit cost, pnl, etc..
    #could use branches for each type
    user_message = {"role": "user", "content": user_prompt}
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[system_message, user_message]
        )
        # extract the answer
        answer = response["choices"][0]["message"]["content"].strip()
        return answer
    except Exception as e:
        logger.error(f"OpenAI API call failed: {e}")
        return f"Error: {e}"
