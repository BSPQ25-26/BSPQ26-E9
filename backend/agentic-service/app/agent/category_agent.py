import os

from dotenv import load_dotenv
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from app.schemas.category import CategoryRequest, CategorySuggestion

# Sprint 1: hardcoded. In Sprint 2+ this list will come from the request body,
# populated by the main backend from its database.
DEFAULT_CATEGORIES: list[str] = [
    "Electronics",
    "Clothing & Accessories",
    "Home & Garden",
    "Sports & Outdoors",
    "Vehicles",
    "Books & Media",
    "Toys & Games",
    "Health & Beauty",
    "Collectibles & Art",
    "Other",
]

SYSTEM_PROMPT = """
You are Wallabot, a product classification assistant for a second-hand marketplace.

You will receive a product title and description, along with a list of existing categories.

Your task:
1. Determine the most appropriate category for the product.
2. If one of the existing categories fits well, use it EXACTLY as written.
3. If none of them fit, propose a concise new category name (2-4 words max).
4. Set is_new_category to true ONLY when you proposed a new name not in the list.
5. Use "Other" only when the item is still a standard physical product and no category is close.
6. If the item is clearly outside the marketplace taxonomy (for example food, services,
   live goods, or niche handmade consumables), you MUST propose a new category and set
   is_new_category=true (do not use "Other" for these cases).

Existing categories: {available_categories}

Respond ONLY with a JSON object - no explanation, no markdown, no code fences:
{{
  "suggested_category": "<category name>",
  "confidence": <float 0.0-1.0>,
  "is_new_category": <true|false>
}}
""".strip()

load_dotenv()

_parser = PydanticOutputParser(pydantic_object=CategorySuggestion)
_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "Product title: {title}\nDescription: {description}"),
    ]
)
_llm = ChatOpenAI(
    model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
    temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
)
_chain = _prompt | _llm | _parser


def suggest_category(req: CategoryRequest) -> CategorySuggestion:
    return _chain.invoke(
        {
            "title": req.title,
            "description": req.description,
            "available_categories": ", ".join(req.available_categories),
        }
    )
