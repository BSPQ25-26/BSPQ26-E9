#!/usr/bin/env python3
"""
Parse CI coverage artifacts and write dynamic markdown snippets for Sphinx.

Run from the repository root after downloading CI artifacts:
    python docs-sphinx/generate_coverage.py

Expected input layout (produced by sphinx-docs.yml download step):
    coverage-artifacts/
        coverage-<svc>/backend/<svc>/coverage.xml
        coverage-<svc>/backend/<svc>/junit.xml
        coverage-<svc>/backend/<svc>/coverage-html/

Output (written to docs-sphinx/source/_generated/):
    coverage_summary_table.md   — full 4-service summary table
    coverage_links_table.md     — per-service % + link to embedded HTML report
    stats_<svc_slug>.md         — single bold line used inside each service section

When any artifact is missing the script exits without modifying the _generated/
files, so the last committed values are used as a fallback for local builds.
"""
import logging
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ARTIFACTS  = Path("coverage-artifacts")
GENERATED  = Path("docs-sphinx/source/_generated")

logger = logging.getLogger(__name__)

# (artifact suffix, backend/ subdirectory, test/ directory name)
SERVICES = [
    ("auth-service",        "auth-service",        "tests"),
    ("inventory-service",   "inventory-service",   "tests"),
    ("transaction-service", "transaction-service", "tests"),
    ("agentic-service",     "agentic-service",     "test"),
]


def parse_coverage_xml(path: Path) -> dict:
    root = ET.parse(path).getroot()
    covered = int(root.attrib.get("lines-covered", 0))
    valid   = int(root.attrib.get("lines-valid", 1))
    pct     = round(float(root.attrib.get("line-rate", 0)) * 100)
    return {"covered": covered, "valid": valid, "pct": pct}


def parse_junit_xml(path: Path) -> int:
    root = ET.parse(path).getroot()
    if root.tag == "testsuites":
        return sum(int(ts.attrib.get("tests", 0)) for ts in root.findall("testsuite"))
    return int(root.attrib.get("tests", 0))


def main() -> int:
    rows = []

    for artifact_svc, path_svc, test_dir in SERVICES:
        base       = ARTIFACTS / f"coverage-{artifact_svc}" / "backend" / path_svc
        cov_path   = base / "coverage.xml"
        junit_path = base / "junit.xml"

        if not cov_path.exists():
            logger.warning(
                "SKIP — %s not found; keeping committed fallback values.",
                cov_path,
            )
            return 0

        cov   = parse_coverage_xml(cov_path)
        tests = parse_junit_xml(junit_path) if junit_path.exists() else "?"

        rows.append({
            "svc":      artifact_svc,
            "slug":     artifact_svc.replace("-", "_"),
            "test_dir": test_dir,
            "tests":    tests,
            "covered":  cov["covered"],
            "valid":    cov["valid"],
            "pct":      cov["pct"],
        })

    GENERATED.mkdir(parents=True, exist_ok=True)

    # ── coverage_summary_table.md ──────────────────────────────────────────────
    total_tests   = sum(r["tests"] if isinstance(r["tests"], int) else 0 for r in rows)
    total_covered = sum(r["covered"] for r in rows)
    total_valid   = sum(r["valid"] for r in rows)
    total_pct     = round(total_covered / total_valid * 100) if total_valid else 0

    lines = [
        "| Service | Tests | Lines covered | Coverage |",
        "|---------|------:|:-------------:|---------:|",
    ]
    for r in rows:
        lines.append(
            f"| {r['svc']} | {r['tests']} "
            f"| {r['covered']} / {r['valid']} | **{r['pct']}%** |"
        )
    lines.append(
        f"| **Total** | **{total_tests}** "
        f"| **{total_covered} / {total_valid}** | **{total_pct}%** |"
    )
    (GENERATED / "coverage_summary_table.md").write_text("\n".join(lines) + "\n")
    logger.info("coverage_summary_table.md — overall %s%%", total_pct)

    # ── coverage_links_table.md ────────────────────────────────────────────────
    link_lines = [
        "| Service | Coverage | Interactive report |",
        "|---------|:-------:|--------------------|",
    ]
    for r in rows:
        link_lines.append(
            f"| {r['svc']} | **{r['pct']}%** "
            f"| [Open report](_static/coverage/{r['svc']}/index.html) |"
        )
    (GENERATED / "coverage_links_table.md").write_text("\n".join(link_lines) + "\n")
    logger.info("coverage_links_table.md")

    # ── per-service stats lines ────────────────────────────────────────────────
    for r in rows:
        content = (
            f"**{r['tests']} tests | {r['pct']}% coverage | "
            f"`backend/{r['svc']}/{r['test_dir']}/`**\n"
        )
        (GENERATED / f"stats_{r['slug']}.md").write_text(content)
        logger.info("stats_%s.md — %s%%", r["slug"], r["pct"])

    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    sys.exit(main())
