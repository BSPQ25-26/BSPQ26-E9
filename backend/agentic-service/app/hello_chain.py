import os

from dotenv import load_dotenv
from tavily import TavilyClient
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

load_dotenv()


def search_with_tavily(query: str) -> str:
    """Search using Tavily and return formatted results."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        raise SystemExit("TAVILY_API_KEY not configured")
    
    client = TavilyClient(api_key=tavily_api_key)
    response = client.search(query=query, max_results=3)
    
    results_text = "\n".join([f"- {r['title']}: {r['content']}" for r in response['results']])
    return results_text


def summarize_with_openai(search_results: str) -> str:
    """Summarize search results using OpenAI."""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise SystemExit("OPENAI_API_KEY not configured")
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = f"Resume in a sentence the following searches:\n\n{search_results}"
    message = HumanMessage(content=prompt)
    response = llm.invoke([message])
    return response.content


def main():
    print("[1] Searching on Tavily...")
    search_results = search_with_tavily("LangChain AI framework")
    print(f"Results:\n{search_results}\n")
    
    print("[2] Generating summary with OpenAI...")
    summary = summarize_with_openai(search_results)
    print(f"Summary:\n{summary}")


if __name__ == "__main__":
    main()
