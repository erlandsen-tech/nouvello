import chapterize.chapterize as ch

book = ch.Book("books/alice.txt", nochapters=False, stats=False)

# Print chapter headings
print("Chapter Headings:")
for i, heading_line_num in enumerate(book.headings[:-1]):  # Exclude the last one (end location)
    heading_text = book.lines[heading_line_num]
    print(f"Chapter {i+1}: {heading_text}")

print(f"\nTotal chapters found: {book.numChapters}")
print(f"Number of headings: {len(book.headings)}")