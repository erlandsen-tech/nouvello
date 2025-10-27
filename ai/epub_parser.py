"""
EPUB Parser for Chapter Detection
Extracts chapters from EPUB files using their native structure
"""

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import re
import warnings

# Suppress XML parsed as HTML warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


@dataclass
class EPUBChapter:
    """Represents a chapter extracted from EPUB"""
    title: str
    content: str
    order: int
    file_name: str


class EPUBParser:
    """Parse EPUB files and extract chapter information"""
    
    def __init__(self, epub_path: str):
        self.epub_path = epub_path
        self.book = None
        self.chapters = []
        
    def parse(self) -> List[EPUBChapter]:
        """Parse EPUB and extract chapters"""
        try:
            self.book = epub.read_epub(self.epub_path)
            
            # Try to extract from TOC first (most reliable)
            chapters_from_toc = self._extract_from_toc()
            if chapters_from_toc:
                self.chapters = chapters_from_toc
                return self.chapters
            
            # Fallback: extract from spine (document order)
            chapters_from_spine = self._extract_from_spine()
            self.chapters = chapters_from_spine
            return self.chapters
            
        except Exception as e:
            print(f"Error parsing EPUB: {e}")
            return []
    
    def _extract_from_toc(self) -> List[EPUBChapter]:
        """Extract chapters from EPUB Table of Contents"""
        chapters = []
        
        try:
            toc = self.book.toc
            if not toc:
                return []
            
            order = 0
            for item in self._flatten_toc(toc):
                if isinstance(item, tuple):
                    # It's a section with a link
                    section, link = item[0], item[1] if len(item) > 1 else None
                    if hasattr(section, 'title') and hasattr(section, 'href'):
                        content = self._get_content_by_href(section.href)
                        if content:
                            chapters.append(EPUBChapter(
                                title=section.title,
                                content=content,
                                order=order,
                                file_name=section.href
                            ))
                            order += 1
                elif hasattr(item, 'title') and hasattr(item, 'href'):
                    # It's a link item
                    content = self._get_content_by_href(item.href)
                    if content:
                        chapters.append(EPUBChapter(
                            title=item.title,
                            content=content,
                            order=order,
                            file_name=item.href
                        ))
                        order += 1
                        
            return chapters
            
        except Exception as e:
            print(f"Error extracting from TOC: {e}")
            return []
    
    def _flatten_toc(self, toc, result=None):
        """Flatten nested TOC structure"""
        if result is None:
            result = []
            
        for item in toc:
            if isinstance(item, tuple):
                # Nested section
                result.append(item)
                if len(item) > 1 and isinstance(item[1], list):
                    self._flatten_toc(item[1], result)
            else:
                result.append(item)
                
        return result
    
    def _extract_from_spine(self) -> List[EPUBChapter]:
        """Extract chapters from EPUB spine (reading order)"""
        chapters = []
        
        try:
            items = list(self.book.get_items_of_type(ebooklib.ITEM_DOCUMENT))
            
            for order, item in enumerate(items):
                # Get content
                content_html = item.get_content().decode('utf-8', errors='ignore')
                content_text = self._html_to_text(content_html)
                
                # Try to extract title from content
                title = self._extract_title_from_html(content_html)
                if not title:
                    title = f"Chapter {order + 1}"
                
                if content_text.strip():
                    chapters.append(EPUBChapter(
                        title=title,
                        content=content_text,
                        order=order,
                        file_name=item.get_name()
                    ))
                    
            return chapters
            
        except Exception as e:
            print(f"Error extracting from spine: {e}")
            return []
    
    def _get_content_by_href(self, href: str) -> Optional[str]:
        """Get chapter content by href reference"""
        try:
            # Remove anchor if present
            href_clean = href.split('#')[0]
            
            # Find the item
            for item in self.book.get_items():
                if item.get_name() == href_clean or item.get_name().endswith(href_clean):
                    content_html = item.get_content().decode('utf-8', errors='ignore')
                    return self._html_to_text(content_html)
                    
            return None
            
        except Exception as e:
            print(f"Error getting content for {href}: {e}")
            return None
    
    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text"""
        try:
            # Try XML parser first, fallback to HTML parser
            try:
                soup = BeautifulSoup(html, 'xml')
            except:
                soup = BeautifulSoup(html, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text
            
        except Exception as e:
            print(f"Error converting HTML to text: {e}")
            return ""
    
    def _extract_title_from_html(self, html: str) -> Optional[str]:
        """Extract chapter title from HTML content"""
        try:
            # Try XML parser first, fallback to HTML parser
            try:
                soup = BeautifulSoup(html, 'xml')
            except:
                soup = BeautifulSoup(html, 'lxml')
            
            # Try to find title in common heading tags
            for tag in ['h1', 'h2', 'h3', 'title']:
                heading = soup.find(tag)
                if heading and heading.get_text().strip():
                    title = heading.get_text().strip()
                    # Clean up title
                    title = re.sub(r'\s+', ' ', title)
                    return title
                    
            return None
            
        except Exception as e:
            return None
    
    def get_chapter_count(self) -> int:
        """Get the number of chapters"""
        return len(self.chapters)
    
    def get_chapter_titles(self) -> List[str]:
        """Get list of chapter titles"""
        return [ch.title for ch in self.chapters]
    
    def get_chapter_content(self, index: int) -> Optional[str]:
        """Get content of a specific chapter by index"""
        if 0 <= index < len(self.chapters):
            return self.chapters[index].content
        return None
    
    def export_chapters_as_text(self) -> str:
        """Export all chapters as a single text document with line numbers"""
        lines = []
        
        for chapter in self.chapters:
            # Add chapter heading
            lines.append(chapter.title)
            lines.append("")  # Empty line
            
            # Add chapter content
            content_lines = chapter.content.split('\n')
            lines.extend(content_lines)
            
            # Add separator
            lines.append("")
            lines.append("")
        
        return '\n'.join(lines)


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python epub_parser.py <epub_file>")
        return
    
    epub_path = sys.argv[1]
    parser = EPUBParser(epub_path)
    chapters = parser.parse()
    
    print(f"\nFound {len(chapters)} chapters:")
    print("=" * 50)
    
    for i, chapter in enumerate(chapters, 1):
        content_preview = chapter.content[:100].replace('\n', ' ')
        print(f"{i}. {chapter.title}")
        print(f"   Preview: {content_preview}...")
        print()


if __name__ == "__main__":
    main()

