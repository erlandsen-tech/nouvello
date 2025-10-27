"""
AI-Powered Chapter Detection System
Uses LLM-based semantic analysis with pattern matching fallback
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from .llm_providers import MultiProviderLLM
from .chapter_patterns import CHAPTER_PATTERNS, match_pattern

@dataclass
class ChapterCandidate:
    """Represents a potential chapter boundary"""
    line_number: int
    text: str
    confidence: float
    method: str  # 'llm', 'embedding', 'pattern', 'fallback'
    context: Dict = None

@dataclass
class ChapterDetectionResult:
    """Result of chapter detection analysis"""
    chapters: List[List[str]]
    headings: List[str]
    confidence_scores: List[float]
    detection_method: str
    metadata: Dict

class AIChapterDetector:
    """AI-powered chapter detection using multiple approaches"""
    
    def __init__(self, 
                 llm_provider: str = "bedrock",
                 api_key: Optional[str] = None,
                 region: Optional[str] = None,
                 profile: Optional[str] = None):
        self.llm_provider = llm_provider
        self.api_key = api_key
        self.region = region
        self.profile = profile
        
        # Initialize LLM client
        self.llm_client = None
        if llm_provider != "none":
            try:
                self.llm_client = MultiProviderLLM(
                    provider=llm_provider,
                    api_key=api_key,
                    region=region,
                    profile=profile
                )
            except Exception as e:
                print(f"Warning: Could not initialize LLM provider {llm_provider}: {e}")
                self.llm_client = None
    
    def detect_chapters_llm(self, text: str, lines: List[str]) -> List[ChapterCandidate]:
        """Use LLM to identify chapter boundaries - analyze entire book efficiently"""
        if not self.llm_client:
            return []
        
        # For small books (< 100K chars), analyze the whole thing in one go
        if len(text) < 100000:
            return self._analyze_full_text(text, lines)
        
        # For larger books, use the efficient pre-filtering approach
        return self._analyze_with_prefilter(text, lines)
    
    def _analyze_full_text(self, text: str, lines: List[str]) -> List[ChapterCandidate]:
        """Analyze entire book text directly (for smaller books)"""
        # Create numbered lines for LLM reference
        numbered_lines = '\n'.join([f"{i}: {line[:100]}" for i, line in enumerate(lines) if line.strip()])
        
        prompt = f"""You are analyzing a book to find chapter boundaries. Return ONLY the line numbers where new chapters start.

Book text with line numbers:
{numbered_lines}

Instructions:
- Identify lines that are chapter headings (e.g., "CHAPTER I", "Chapter 1", etc.)
- Do NOT include regular paragraphs, scene breaks, or emphasized text
- Only include actual chapter divisions

Return ONLY this JSON format with line numbers: {{"chapter_lines": [5, 120, 245]}}

If no chapters exist, return: {{"chapter_lines": []}}"""
        
        try:
            print(f"Analyzing full text ({len(text)} chars, {len(lines)} lines)")
            response = self.llm_client.generate_response(prompt)
            
            if not response.content or not response.content.strip():
                print("LLM returned empty response")
                return []
            
            result = self._parse_llm_response(response.content, 0)
            if result is None:
                return []
            
            candidates = []
            chapter_lines = result.get('chapter_lines', [])
            
            if not isinstance(chapter_lines, list):
                print("Invalid chapter_lines format")
                return []
            
            for line_num in chapter_lines:
                if isinstance(line_num, int) and 0 <= line_num < len(lines):
                    candidates.append(ChapterCandidate(
                        line_number=line_num,
                        text=lines[line_num],
                        confidence=0.9,
                        method='llm_full',
                        context={'source': 'full_text_analysis'}
                    ))
            
            print(f"LLM found {len(candidates)} chapters in full text")
            return candidates
            
        except Exception as e:
            print(f"LLM full text analysis failed: {e}")
            return []
    
    def _analyze_with_prefilter(self, text: str, lines: List[str]) -> List[ChapterCandidate]:
        """Analyze book using pre-filtering (for larger books)"""
        # Get lines that look like potential chapter headings (short, at start of paragraph, etc.)
        potential_headings = []
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            # Skip empty lines
            if not line_stripped:
                continue
            # Look for lines that might be chapter headings:
            # - Short lines (< 100 chars)
            # - Start with chapter-like words or numbers
            # - All caps or Title Case
            if (len(line_stripped) < 100 and 
                (re.match(r'^(CHAPTER|Chapter|BOOK|Book|PART|Part|SECTION|Section|\d+\.?|[IVX]+\.?)\s', line_stripped) or
                 line_stripped.isupper() or
                 (line_stripped[0].isupper() and i > 0 and not lines[i-1].strip()))):
                potential_headings.append((i, line_stripped[:80]))  # Truncate for efficiency
        
        if not potential_headings:
            print("No potential chapter headings found")
            return []
        
        # Limit to first 500 potential headings to stay within token limits
        potential_headings = potential_headings[:500]
        
        # Create a numbered list for LLM
        numbered_list = '\n'.join([f"{i}: {text}" for i, text in potential_headings])
        
        prompt = f"""You are analyzing a book to find chapter boundaries. Below are potential chapter heading lines extracted from the book.

Potential headings (line_number: text):
{numbered_list}

Instructions:
- Identify which line numbers are ACTUAL chapter headings (e.g., "CHAPTER I", "Chapter 1", "PART ONE")
- Exclude emphasized text, scene breaks, quotes, or regular paragraph text
- Only include formal chapter divisions

Return ONLY this JSON format: {{"chapter_lines": [45, 123, 456]}}

If no actual chapters, return: {{"chapter_lines": []}}"""
        
        try:
            response = self.llm_client.generate_response(prompt)
            
            if not response.content or not response.content.strip():
                print("LLM returned empty response")
                return []
            
            # Parse response
            result = self._parse_llm_response(response.content, 0)
            if result is None:
                return []
            
            # Extract line numbers
            candidates = []
            chapter_lines = result.get('chapter_lines', [])
            
            if not isinstance(chapter_lines, list):
                print("Invalid chapter_lines format")
                return []
            
            for line_num in chapter_lines:
                if isinstance(line_num, int) and 0 <= line_num < len(lines):
                    candidates.append(ChapterCandidate(
                        line_number=line_num,
                        text=lines[line_num],
                        confidence=0.85,
                        method='llm',
                        context={'source': 'smart_detection'}
                    ))
            
            print(f"LLM identified {len(candidates)} chapter headings from {len(potential_headings)} candidates")
            return candidates
            
        except Exception as e:
            print(f"LLM analysis failed: {e}")
            return []
    
    def detect_chapters_patterns(self, lines: List[str]) -> List[ChapterCandidate]:
        """Use pattern matching to find chapter headings"""
        candidates = []
        
        for i, line in enumerate(lines):
            matched, pattern_type, confidence = match_pattern(line)
            if matched:
                candidates.append(ChapterCandidate(
                    line_number=i,
                    text=line.strip(),
                    confidence=confidence,
                    method=f'pattern_{pattern_type}',
                    context={'pattern_type': pattern_type}
                ))
        
        return candidates
    
    def _parse_llm_response(self, content: str, chunk_index: int) -> Optional[Dict]:
        """Parse LLM response with multiple fallback strategies"""
        content = content.strip()
        
        # Strategy 1: Direct JSON parsing
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass
        
        # Strategy 2: Extract JSON from markdown code blocks
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Strategy 3: Find any JSON object with braces (greedy match)
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            try:
                json_str = json_match.group(0)
                # Try to find the balanced JSON
                brace_count = 0
                end_pos = 0
                for i, char in enumerate(json_str):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end_pos = i + 1
                            break
                
                if end_pos > 0:
                    balanced_json = json_str[:end_pos]
                    return json.loads(balanced_json)
            except json.JSONDecodeError:
                pass
        
        # Strategy 4: Try to extract just the array for chapter_lines
        array_match = re.search(r'"chapter_lines"\s*:\s*(\[[^\]]*\])', content)
        if array_match:
            try:
                return {"chapter_lines": json.loads(array_match.group(1))}
            except json.JSONDecodeError:
                pass
        
        # Strategy 5: Look for boundaries pattern
        boundaries_match = re.search(r'"boundaries"\s*:\s*(\[[^\]]*\])', content, re.DOTALL)
        if boundaries_match:
            try:
                return {"boundaries": json.loads(boundaries_match.group(1))}
            except json.JSONDecodeError:
                pass
        
        print(f"LLM returned unparseable JSON")
        print(f"Response preview: {content[:300]}...")
        return None
    
    def _find_line_number(self, text: str, lines: List[str], start_line: int = 0) -> Optional[int]:
        """Find the line number containing the given text"""
        for i in range(start_line, len(lines)):
            if text.strip().lower() in lines[i].lower():
                return i
        return None
    
    def merge_candidates(self, candidates: List[ChapterCandidate]) -> List[ChapterCandidate]:
        """Merge nearby candidates and resolve conflicts"""
        if not candidates:
            return []
        
        # Sort by line number
        candidates.sort(key=lambda x: x.line_number)
        
        merged = []
        i = 0
        
        while i < len(candidates):
            current = candidates[i]
            
            # Look for nearby candidates within 3 lines
            nearby = [current]
            j = i + 1
            
            while j < len(candidates) and candidates[j].line_number - current.line_number <= 3:
                nearby.append(candidates[j])
                j += 1
            
            # Choose the best candidate from nearby ones
            if len(nearby) > 1:
                best = max(nearby, key=lambda x: x.confidence)
                merged.append(best)
                i = j
            else:
                merged.append(current)
                i += 1
        
        return merged
    
    def detect_chapters(self, file_path: str) -> ChapterDetectionResult:
        """Main method to detect chapters using LLM with pattern fallback"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        
        lines = text.split('\n')
        
        # Try LLM detection first, fallback to patterns
        all_candidates = []
        
        if self.llm_client:
            llm_candidates = self.detect_chapters_llm(text, lines)
            all_candidates.extend(llm_candidates)
        
        # Fallback to pattern detection if no LLM results
        if not all_candidates:
            pattern_candidates = self.detect_chapters_patterns(lines)
            all_candidates.extend(pattern_candidates)
        
        # Merge nearby candidates (within 3 lines)
        merged_candidates = self.merge_candidates(all_candidates)
        
        # Filter by confidence threshold
        final_candidates = [c for c in merged_candidates if c.confidence > 0.5]
        
        # Extract chapters
        chapters = self._extract_chapters_from_candidates(lines, final_candidates)
        headings = [c.text for c in final_candidates]
        confidence_scores = [c.confidence for c in final_candidates]
        
        # Determine primary detection method
        method_counts = {}
        for c in final_candidates:
            method_counts[c.method] = method_counts.get(c.method, 0) + 1
        primary_method = max(method_counts.items(), key=lambda x: x[1])[0] if method_counts else 'unknown'
        
        return ChapterDetectionResult(
            chapters=chapters,
            headings=headings,
            confidence_scores=confidence_scores,
            detection_method=primary_method,
            metadata={
                'total_candidates': len(all_candidates),
                'final_candidates': len(final_candidates),
                'method_breakdown': method_counts
            }
        )
    
    def _extract_chapters_from_candidates(self, lines: List[str], candidates: List[ChapterCandidate]) -> List[List[str]]:
        """Extract chapter content based on detected boundaries"""
        if not candidates:
            return [lines]  # Return entire text as single chapter
        
        chapters = []
        candidate_lines = sorted([c.line_number for c in candidates])
        
        # First chapter: from start to first candidate
        if candidate_lines[0] > 0:
            chapters.append(lines[:candidate_lines[0]])
        
        # Middle chapters: between candidates
        for i in range(len(candidate_lines) - 1):
            start = candidate_lines[i]
            end = candidate_lines[i + 1]
            chapters.append(lines[start:end])
        
        # Last chapter: from last candidate to end
        if candidate_lines[-1] < len(lines) - 1:
            chapters.append(lines[candidate_lines[-1]:])
        
        return chapters

def main():
    """Example usage"""
    detector = AIChapterDetector()
    
    # Test on Alice in Wonderland
    result = detector.detect_chapters('books/alice.txt')
    
    print(f"Detected {len(result.chapters)} chapters using {result.detection_method}")
    print(f"Confidence scores: {result.confidence_scores}")
    print(f"Headings: {result.headings[:5]}...")  # Show first 5 headings

if __name__ == "__main__":
    main()
