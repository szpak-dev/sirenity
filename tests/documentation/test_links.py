from pathlib import Path

from scripts.check_docs_links import DocumentationCrawler


class TestDocumentationLinks:
    @staticmethod
    def test_every_documentation_page_is_reachable_from_readme() -> None:
        root = Path(__file__).parents[2]
        entrance = root / "README.md"
        expected = {entrance.resolve(), *(path.resolve() for path in (root / "docs").rglob("*.md"))}

        pages = DocumentationCrawler(root).crawl(entrance)

        assert set(pages) == expected
