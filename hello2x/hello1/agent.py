"""Hello world agent which can convert currency."""

from datetime import date, timedelta
import requests


def get_today_date():
    """Returns today's date in YYYY-MM-DD format."""
    today = date.today()
    return today.strftime("%Y-%m-%d")


def get_date_plus_days(days: int):
    """Returns a date in YYYY-MM-DD format, plus or minus the number of days.

    Args:
        days (int): The number of days to add or subtract from today's date.

    Returns:
        str: A date in YYYY-MM-DD format.
    """
    today = date.today()
    return (today + timedelta(days=days)).strftime("%Y-%m-%d")


def get_exchange_rate(currency_from: str, currency_to: str, currency_date: str):
    """Retrieves the exchange rate between two currencies on a specified date.

    Args:
        currency_from (str): The source currency code.
        currency_to (str): The target currency code.
        currency_date (str): The date for which to retrieve the exchange rate.

    Returns:
        dict: A dictionary containing the exchange rate information.
    """

    response = requests.get(
        f"https://api.frankfurter.app/{currency_date}",
        params={"from": currency_from, "to": currency_to},
    )
    return response.json()


# Easily create an agent with the ADK, wire instructions, and tools.
from google.adk.agents import Agent

MODEL = "gemini-2.5-flash-preview-04-17"

root_agent = Agent(
    model=MODEL,
    name="hello_1_agent",
    description="A helpful AI assistant to convert currency.",
    instruction="""
You are a currency converter analyst.

[Goal]
Provide authoratative answers to questions about currency conversion on specific dates.

[Instructions]
Follow the steps.
1. Introduce yourself as "Currency Analyst."
2. Collect source country, target country, and date.
3. If the user specifies a relative date, use the tool get_date_plus_days() to get the date.
4. If a date is not provided, use today's date derived by using tool get_today_date().
5. Retrieve currency codes and exchange rate using the tool get_exchange_rate().
6. Explain the currency conversion approach taken.
7. Calculate and display the converted currency value.
8. Present the consolidated, formatted conversion result.
""",
    tools=[
        get_exchange_rate,
        get_today_date,
        get_date_plus_days,
    ],
)
