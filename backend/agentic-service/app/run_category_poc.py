from dotenv import load_dotenv
import logging
from app.agent.category_agent import DEFAULT_CATEGORIES, suggest_category
from app.schemas.category import CategoryRequest

load_dotenv()

# For running, use the following command:
# python -m app.run_category_poc

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logger = logging.getLogger("mini_wallabot.run_category_poc")

    test_cases = [
        (
            "iPhone 13 128GB",
            "Used iPhone in good condition, minor scratches on screen.",
        ),
        (
            "Nike Air Max 90",
            "Barely worn sneakers, size 42, white colorway.",
        ),
        (
            "IKEA KALLAX shelf",
            "4x4 white shelf unit, disassembled, all parts included.",
        ),
        (
            "Harry Potter complete collection",
            "All 7 books in hardcover, good condition.",
        ),
        (
            "Trek mountain bike",
            "21-speed MTB, front suspension, needs new brakes.",
        ),
        (
            "Vintage Rolex Submariner",
            "1972 watch, original bracelet, no box.",
        ),
        (
            "Homemade sourdough starter",
            "Active culture, 200g, ships refrigerated.",
        ),
        (
            "One-hour online guitar lesson",
            "Private beginner class over video call, includes custom practice plan.",
        ),
    ]

    for title, description in test_cases:
        request = CategoryRequest(
            title=title,
            description=description,
            available_categories=DEFAULT_CATEGORIES,
        )
        result = suggest_category(request)
        flag = " [NEW]" if result.is_new_category else ""
        logger.info(
            "[%s]\n  -> %s%s (confidence: %s)\n",
            title,
            result.suggested_category,
            flag,
            result.confidence,
        )


if __name__ == "__main__":
    main()
