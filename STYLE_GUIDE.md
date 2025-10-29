# Art Style Guide

## Overview

The pipeline **automatically detects and enforces** a consistent art style for every book based on its content. You can also **override** this to create fun artistic variations of classic literature!

### How It Works

1. **No style specified**: The LLM analyzes the book and infers an appropriate style
   - Lovecraft → Detects "dark gothic horror, cosmic dread"
   - Alice → Detects "whimsical fantasy, Victorian literary"
   - Pride & Prejudice → Detects "romantic period drama, elegant"

2. **Style override specified**: Your style is used instead
   - Forces ALL characters and scenes to match your creative vision
   - Enables fun artistic experiments!

### Automatic Style Detection

```bash
# Normal run - style auto-detected from book
python book_to_vn.py books/alice.epub --chapters 4,5,6

# Output shows:
#   🎨 Inferring art style from book content...
#   ✨ Detected style: whimsical, fantastical, Victorian
```

The detected style is then used consistently for all images!

## Usage

Use the `--style` flag when running the pipeline:

```bash
python book_to_vn.py books/your_book.epub --style "your_style_here"
```

## Fun Examples

### 🎃 Horror Alice in Wonderland
```bash
python book_to_vn.py books/alice.epub --chapters 1,2,3 --style "dark gothic horror"
```
Transforms the whimsical Alice into a dark, scary Tim Burton-esque nightmare!

### 🌸 Cute Lovecraft
```bash
python book_to_vn.py books/lovecraft.epub --chapters 1,2,3 --style "cute kawaii anime"
```
Makes cosmic horror adorable! Cthulhu with big sparkly eyes!

### 🤖 Cyberpunk Classics
```bash
python book_to_vn.py books/dracula.epub --style "cyberpunk neon"
```
Victorian horror meets blade runner aesthetics.

### 🎨 Watercolor Versions
```bash
python book_to_vn.py books/alice.epub --style "soft watercolor pastel"
```
Gentle, dreamy artistic interpretation.

### 📺 Teletubbies Horror
```bash
python book_to_vn.py books/lovecraft.epub --style "teletubbies happy colorful"
```
The ultimate contrast - cosmic horror as children's TV show!

## Popular Style Keywords

### Classic Styles
- `"oil painting renaissance"`
- `"ink wash traditional"`
- `"art nouveau"`
- `"art deco"`

### Modern Styles
- `"minimalist flat design"`
- `"vaporwave aesthetic"`
- `"pixel art retro"`
- `"low poly 3D"`

### Anime/Manga Styles
- `"shoujo manga sparkly"`
- `"seinen dark realistic"`
- `"chibi cute"`
- `"studio ghibli"`

### Genre Styles
- `"horror psychological dark"`
- `"cyberpunk neon tech"`
- `"steampunk Victorian mechanical"`
- `"fantasy high medieval"`
- `"sci-fi futuristic"`

### Mood-Based
- `"dreamy soft ethereal"`
- `"gritty dark realistic"`
- `"cheerful bright happy"`
- `"melancholic blue tones"`

## How It Works

1. **Style is saved** in `analysis.json`:
   ```json
   {
     "book_title": "Alice's Adventures in Wonderland",
     "art_style": "horror gothic dark",
     "chapters": [...]
   }
   ```

2. **Characters are generated** with that style:
   - All character prompts include the style requirement
   - Ensures consistency across all characters

3. **Scenes are generated** with that style:
   - Scene compositions match the style
   - Character references maintain the style

4. **Result**: Entire book has unified artistic direction!

## Tips for Best Results

1. **Be Specific**: 
   - ❌ "nice" 
   - ✅ "soft pastel watercolor with gentle lighting"

2. **Combine Keywords**:
   - ✅ "cyberpunk neon dark dystopian"
   - ✅ "cute kawaii pastel magical girl"

3. **Include Visual Elements**:
   - "gothic architecture dark shadows"
   - "bright saturated colors bold outlines"

4. **Consider the Source Material**:
   - Lovecraft + "cute": Maximum contrast, very funny
   - Alice + "horror": Natural dark twist
   - Shakespeare + "cyberpunk": Interesting modernization

## Regenerating with New Style

If you want to change the style after initial generation:

```bash
# Delete generated assets
rm -rf output/your_book/images/
rm -rf output/your_book/consistent_scenes/
rm output/your_book/character_prompts.json
rm output/your_book/analysis.json

# Regenerate with new style
python book_to_vn.py books/your_book.epub --style "new_style" --resume-from analyze
```

## Examples Gallery

**Coming Soon**: We'll add a gallery of popular style variations!

Ideas:
- ⚡ "Anime Battle Shounen" Pride and Prejudice
- 🌈 "My Little Pony" Moby Dick
- 👻 "Horror Found Footage" The Secret Garden
- 🎮 "8-bit Retro Game" War and Peace
- 🦄 "Lisa Frank Rainbow" The Road (Cormac McCarthy)

Have fun creating wild artistic variations! 🎨✨

