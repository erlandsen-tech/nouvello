# 🎨 Consistent Style System

## Two Modes of Operation

### Mode 1: Automatic Style Detection (Default)

**What Happens:**
```bash
python book_to_vn.py books/alice.epub --chapters 1,2,3
```

1. **Analysis Phase**: LLM reads the chapters and infers visual style
   ```
   🎨 Inferring art style from book content...
   ✨ Detected style: whimsical, fantastical, Victorian
   📚 Genre: children's fantasy
   🎭 Mood: curious, dreamlike, playful
   ```

2. **Saved to analysis.json**:
   ```json
   {
     "book_title": "Alice's Adventures in Wonderland",
     "art_style": "whimsical, fantastical, Victorian",
     "chapters": [...]
   }
   ```

3. **Character Generation**: All characters use detected style
   - Alice: Whimsical Victorian girl
   - White Rabbit: Fantastical Victorian rabbit
   - All others: Match the same aesthetic

4. **Scene Generation**: All scenes use detected style
   - Consistent lighting, color palette, artistic rendering
   - Unified visual language throughout

**Result**: Perfectly cohesive visual novel that matches the book's original tone!

---

### Mode 2: Manual Style Override

**What Happens:**
```bash
python book_to_vn.py books/alice.epub --chapters 1,2,3 --style "dark gothic horror"
```

1. **Analysis Phase**: Your style is saved immediately
   ```
   🎨 Art Style Override: dark gothic horror
   This style will be applied to all images in the book
   ```

2. **Saved to analysis.json**:
   ```json
   {
     "book_title": "Alice's Adventures in Wonderland",
     "art_style": "dark gothic horror",
     "chapters": [...]
   }
   ```

3. **Character Generation**: Characters reinterpreted in new style
   - Alice: Dark, creepy, horror movie aesthetic
   - White Rabbit: Ominous, shadowy creature
   - All: Gothic horror style

4. **Scene Generation**: Scenes match the dark theme
   - Horror lighting, ominous atmosphere
   - Consistent dark aesthetic

**Result**: Creative artistic reinterpretation with perfect style consistency!

---

## Style Consistency Enforcement

### In Character Prompts

```
**IMPORTANT: STYLE OVERRIDE**
The entire book must be rendered in {STYLE} style.
All characters must match this artistic direction.
```

### In Scene Prompts

```
STYLE REQUIREMENTS:
- **{STYLE} STYLE** - This is MANDATORY for consistency
- All elements must match the {style} aesthetic
- High quality, detailed illustration
```

---

## Examples of Auto-Detection

| Book | Auto-Detected Style | Why |
|------|---------------------|-----|
| H.P. Lovecraft | `"dark gothic horror, cosmic dread, eldritch"` | Horror themes, dark mood |
| Alice in Wonderland | `"whimsical, fantastical, Victorian literary"` | Playful fantasy, period setting |
| Pride & Prejudice | `"romantic, elegant, Regency period"` | Romance genre, historical |
| 1984 | `"dystopian, gritty, oppressive, industrial"` | Dark sci-fi themes |
| The Hobbit | `"high fantasy, adventurous, mythical"` | Fantasy adventure |

---

## When to Override vs Auto-Detect

### Use Auto-Detection When:
- ✅ You want the book's natural aesthetic
- ✅ Creating a faithful adaptation
- ✅ First time processing a book
- ✅ You trust the LLM's judgment

### Use Override When:
- ✅ Creating artistic experiments
- ✅ Making ironic/humorous versions
- ✅ Matching a specific brand aesthetic
- ✅ Cross-genre mashups

---

## Pro Tips

### 1. Subtle Overrides
Instead of completely changing the genre, enhance the existing style:
```bash
# Alice is already whimsical, make it more so
--style "extra whimsical sparkly magical"

# Lovecraft is dark, make it darker
--style "ultra dark nightmare fuel"
```

### 2. Compound Styles
Combine multiple aesthetics:
```bash
--style "cyberpunk horror neon gothic"
--style "cute kawaii pastel fantasy magical girl"
--style "watercolor soft dreamy ethereal"
```

### 3. Reference Other Media
```bash
--style "studio ghibli soft gentle"
--style "tim burton gothic quirky"
--style "blade runner neon rain dark"
--style "disney princess sparkly colorful"
```

---

## Technical Details

### Where Style is Stored
- **Primary**: `output/book_name/analysis.json`
- **Used by**: Character prompter, scene generator
- **Format**: String (space-separated keywords)

### Where Style is Applied
1. **Character Image Prompts** → Consistent character aesthetic
2. **Scene Image Prompts** → Consistent scene aesthetic  
3. **Environment Images** → Consistent background style

### Cache Behavior
- Style is part of the prompt
- Changing style invalidates cache
- Forces regeneration of all images

---

## Fun Creative Examples

See [TEST_STYLE_OVERRIDE.md](TEST_STYLE_OVERRIDE.md) for testing ideas!

Popular mashups:
- 🎃 Horror Alice
- 🌸 Cute Lovecraft  
- 🤖 Cyberpunk Shakespeare
- 🎨 Watercolor Moby Dick
- 📺 Teletubbies Dracula

Have fun creating wild variations! 🎨✨
