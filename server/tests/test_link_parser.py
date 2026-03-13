from __future__ import annotations

from pathlib import Path

from app.utils.link_parser import parse_links_with_context


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    fixture_path = repo_root / "example_hallucination.txt"
    print(fixture_text)
    fixture_text = fixture_path.read_text(encoding="utf-8")

    parsed = parse_links_with_context(fixture_text)

    print(f"Loaded: {fixture_path}")
    print(f"Total parsed items: {len(parsed)}")
    print()

    for index, (link, context) in enumerate(parsed, start=1):
        print(f"{index}. {link}")
        print(f"   context: {context}")
        print()


if __name__ == "__main__":
    main()
