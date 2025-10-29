from ai.epub_parser import EPUBParser

parser = EPUBParser("books/alice.epub")
chapters = parser.parse()

print("Chapter Headings:")
for i, ch in enumerate(chapters, 1):
    print(f"Chapter {i}: {ch.title}")

print(f"\nTotal chapters found: {len(chapters)}")