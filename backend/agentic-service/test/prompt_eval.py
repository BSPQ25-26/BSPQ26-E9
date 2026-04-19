from dataclasses import dataclass
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent.category_agent import DEFAULT_CATEGORIES, suggest_category
from app.schemas.category import CategoryRequest


@dataclass(frozen=True)
class PromptEvalCase:
    title: str
    description: str
    expected_category: str


BASELINE_CASES: list[PromptEvalCase] = [
    PromptEvalCase(
        title="iPhone 13 128GB",
        description="Used iPhone in good condition, minor scratches on screen.",
        expected_category="Electronics",
    ),
    PromptEvalCase(
        title="Nike Air Max 90",
        description="Barely worn sneakers, size 42, white colorway.",
        expected_category="Clothing & Accessories",
    ),
    PromptEvalCase(
        title="IKEA KALLAX shelf",
        description="4x4 white shelf unit, disassembled, all parts included.",
        expected_category="Home & Garden",
    ),
    PromptEvalCase(
        title="Harry Potter complete collection",
        description="All 7 books in hardcover, good condition.",
        expected_category="Books & Media",
    ),
    PromptEvalCase(
        title="Trek mountain bike",
        description="21-speed MTB, front suspension, needs new brakes.",
        expected_category="Sports & Outdoors",
    ),
    PromptEvalCase(
        title="Vintage Rolex Submariner",
        description="1972 watch, original bracelet, no box.",
        expected_category="Collectibles & Art",
    ),
    PromptEvalCase(
        title="Dyson Supersonic hair dryer",
        description="Used 6 months, includes all attachments.",
        expected_category="Health & Beauty",
    ),
    PromptEvalCase(
        title="Nintendo Switch OLED",
        description="Console with dock and two joy-cons, very good condition.",
        expected_category="Electronics",
    ),
    PromptEvalCase(
        title="Lego Star Wars Millennium Falcon",
        description="Set 75257, mostly complete, no box.",
        expected_category="Toys & Games",
    ),
    PromptEvalCase(
        title="2014 Ford Focus",
        description="160000 km, manual transmission, new tires.",
        expected_category="Vehicles",
    ),
    PromptEvalCase(
        title="Air",
        description="Apple AirPods Pro 2nd gen with charging case.",
        expected_category="Electronics",
    ),
    PromptEvalCase(
        title="Air",
        description="Air Jordan 1 Mid, size 43, black and red.",
        expected_category="Clothing & Accessories",
    ),
    PromptEvalCase(
        title="Yoga mat",
        description="5 mm anti-slip mat, used twice.",
        expected_category="Sports & Outdoors",
    ),
    PromptEvalCase(
        title="Smartwatch",
        description="Fitbit Charge 6 with heart-rate and sleep tracking.",
        expected_category="Electronics",
    ),
    PromptEvalCase(
        title="One-hour online guitar lesson",
        description="Private beginner class over video call.",
        expected_category="Services",
    ),
]


HOLDOUT_CASES: list[PromptEvalCase] = [
    PromptEvalCase(
        title="Cannondale road bicycle",
        description="Lightweight carbon frame road bike, Shimano 105 groupset.",
        expected_category="Sports & Outdoors",
    ),
    PromptEvalCase(
        title="Dell Ultrasharp 27 monitor",
        description="4K IPS display, USB-C hub, no dead pixels.",
        expected_category="Electronics",
    ),
    PromptEvalCase(
        title="Oak dining table set",
        description="Solid wood table with 4 matching chairs.",
        expected_category="Home & Garden",
    ),
    PromptEvalCase(
        title="Pokemon booster box",
        description="Factory sealed Scarlet and Violet booster box.",
        expected_category="Toys & Games",
    ),
    PromptEvalCase(
        title="Leather messenger bag",
        description="Brown full-grain crossbody laptop bag.",
        expected_category="Clothing & Accessories",
    ),
    PromptEvalCase(
        title="Kobo Clara eReader",
        description="6-inch e-ink reader with front light and 16GB storage.",
        expected_category="Electronics",
    ),
    PromptEvalCase(
        title="Car roof box",
        description="420L hard-shell roof cargo box for long trips.",
        expected_category="Vehicles",
    ),
    PromptEvalCase(
        title="Ceramic studio vase",
        description="Hand-thrown decorative ceramic vase by local artist.",
        expected_category="Collectibles & Art",
    ),
    PromptEvalCase(
        title="Language exchange tutoring",
        description="Weekly Spanish speaking sessions over video call.",
        expected_category="Services",
    ),
    PromptEvalCase(
        title="Air",
        description="MacBook Air M2, 16GB RAM, 512GB SSD.",
        expected_category="Electronics",
    ),
    PromptEvalCase(
        title="Brompton folding bike",
        description="6-speed commuter folding bicycle, recently serviced.",
        expected_category="Sports & Outdoors",
    ),
    PromptEvalCase(
        title="Bosch cordless drill set",
        description="18V drill with 2 batteries and charger.",
        expected_category="Home & Garden",
    ),
    PromptEvalCase(
        title="PS5 DualSense controller",
        description="Official wireless controller, excellent condition.",
        expected_category="Toys & Games",
    ),
    PromptEvalCase(
        title="Signed first edition Dune",
        description="1965 hardcover, signed by Frank Herbert, collector condition.",
        expected_category="Collectibles & Art",
    ),
    PromptEvalCase(
        title="Kindle ebook code bundle",
        description="Digital redemption codes for 20 fantasy ebooks.",
        expected_category="Digital Goods",
    ),
    PromptEvalCase(
        title="Sourdough starter culture",
        description="Active rye starter, ready for baking at home.",
        expected_category="Food & Consumables",
    ),
    PromptEvalCase(
        title="Wedding photography session",
        description="Two-hour outdoor couple photo session with edited gallery.",
        expected_category="Services",
    ),
    PromptEvalCase(
        title="GoPro Hero 11",
        description="Action camera with two batteries and chest mount.",
        expected_category="Electronics",
    ),
    PromptEvalCase(
        title="Youth baseball glove",
        description="11.5 inch leather glove for infield practice.",
        expected_category="Sports & Outdoors",
    ),
    PromptEvalCase(
        title="Catan board game",
        description="Complete set with all cards and pieces.",
        expected_category="Toys & Games",
    ),
    PromptEvalCase(
        title="Air",
        description="Jordan basketball backpack, black with red trim.",
        expected_category="Clothing & Accessories",
    ),
    PromptEvalCase(
        title="Model train locomotive display",
        description="Limited-edition brass locomotive in glass display case.",
        expected_category="Collectibles & Art",
    ),
]


def _is_case_match(case: PromptEvalCase, suggested_category: str, is_new_category: bool) -> bool:
    expected_is_existing = case.expected_category in DEFAULT_CATEGORIES
    if expected_is_existing:
        return suggested_category == case.expected_category and is_new_category is False
    return (
        is_new_category is True
        and suggested_category not in DEFAULT_CATEGORIES
        and bool(suggested_category.strip())
    )


def _run_case_set(name: str, cases: list[PromptEvalCase]) -> tuple[int, int, list[float]]:
    passed = 0
    confidences: list[float] = []

    print(name)
    print("=" * 80)

    for index, case in enumerate(cases, start=1):
        req = CategoryRequest(
            title=case.title,
            description=case.description,
            available_categories=DEFAULT_CATEGORIES,
        )
        result = suggest_category(req)
        confidences.append(result.confidence)

        is_match = _is_case_match(case, result.suggested_category, result.is_new_category)
        if is_match:
            passed += 1

        status = "PASS" if is_match else "FAIL"
        expected_is_existing = case.expected_category in DEFAULT_CATEGORIES
        expected_label = (
            repr(case.expected_category)
            if expected_is_existing
            else "'new category (out-of-taxonomy)'"
        )
        print(
            f"[{index:02d}] {status}"
            f" | expected={expected_label}"
            f" | got={result.suggested_category!r}"
            f" | confidence={result.confidence:.2f}"
            f" | is_new_category={result.is_new_category}"
        )

    total = len(cases)
    accuracy = passed / total
    unique_confidences = sorted(set(round(value, 2) for value in confidences))
    print("-" * 80)
    print(f"Accuracy: {passed}/{total} ({accuracy:.2%})")
    print(f"Confidence values used: {', '.join(f'{value:.2f}' for value in unique_confidences)}")
    print()

    return passed, total, confidences


def main() -> None:
    baseline_passed, baseline_total, baseline_conf = _run_case_set(
        "Prompt Evaluation Results (Baseline)", BASELINE_CASES
    )
    holdout_passed, holdout_total, holdout_conf = _run_case_set(
        "Prompt Evaluation Results (Generalization Holdout)", HOLDOUT_CASES
    )

    all_total = baseline_total + holdout_total
    all_passed = baseline_passed + holdout_passed
    all_accuracy = all_passed / all_total
    all_confidences = baseline_conf + holdout_conf
    all_unique_confidences = sorted(set(round(value, 2) for value in all_confidences))

    print("Combined Summary")
    print("=" * 80)
    print(
        f"Baseline Accuracy: {baseline_passed}/{baseline_total} "
        f"({baseline_passed / baseline_total:.2%})"
    )
    print(
        f"Holdout Accuracy: {holdout_passed}/{holdout_total} "
        f"({holdout_passed / holdout_total:.2%})"
    )
    print(f"Overall Accuracy: {all_passed}/{all_total} ({all_accuracy:.2%})")
    print(
        "Overall confidence values used: "
        + ", ".join(f"{value:.2f}" for value in all_unique_confidences)
    )


if __name__ == "__main__":
    main()
