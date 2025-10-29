# Testing Style Override Feature

## Test 1: Horror Alice
```bash
# Create a horror version of Alice in Wonderland
python book_to_vn.py books/alice.epub --chapters 4 --style "dark gothic horror" -o output_test

# Expected: Alice as a dark, creepy character
# Characters: Gothic, shadowy, horror movie aesthetic
# Scenes: Dark, ominous, horror lighting
```

## Test 2: Cute Lovecraft  
```bash
# Create a cute version of Lovecraft
python book_to_vn.py books/lovecraft.epub --chapters 1 --style "cute kawaii pastel" -o output_test

# Expected: Cosmic horror rendered in adorable style
# Characters: Big eyes, chibi proportions, pastel colors
# Scenes: Cute, colorful, friendly atmosphere
```

## Test 3: Cyberpunk Classic
```bash
# Create cyberpunk version
python book_to_vn.py books/alice.epub --chapters 4 --style "cyberpunk neon futuristic" -o output_test

# Expected: Sci-fi Alice in Wonderland
# Characters: Tech-wear, neon accents, futuristic
# Scenes: Neon lights, holographic, tech aesthetic
```

## Verify Style is Applied

1. Check analysis.json:
```bash
cat output_test/your_book/analysis.json | head -10
# Should see: "art_style": "your_style_here"
```

2. Check character prompts:
```bash
cat output_test/your_book/character_prompts.json
# Should include style keywords in prompts
```

3. View generated images - they should match the style!

## Fun Combinations to Try

- `"teletubbies happy colorful"` + Lovecraft = Hilarious
- `"horror dark creepy"` + Alice = Perfect dark twist  
- `"pixel art retro 8-bit"` + Any book = Nostalgic gaming aesthetic
- `"studio ghibli soft gentle"` + Horror book = Interesting contrast
- `"vaporwave aesthetic pastel neon"` + Classic literature = Modern twist

