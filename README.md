
## 🎨 Art Style Override

Create artistic variations of any book! The pipeline supports enforcing a consistent visual style across all characters and scenes.

### Quick Start

```bash
# Horror version of Alice in Wonderland
python book_to_vn.py books/alice.epub --style "dark gothic horror"

# Cute version of H.P. Lovecraft
python book_to_vn.py books/lovecraft.epub --style "cute kawaii pastel"

# Cyberpunk version
python book_to_vn.py books/any_book.epub --style "cyberpunk neon futuristic"
```

### How It Works

1. **Style is saved** in book metadata (`analysis.json`)
2. **Character prompts** enforce the style for all characters
3. **Scene images** maintain style consistency
4. **Result**: Entire book has unified artistic direction!

### Popular Style Examples

| Style | Best For | Example |
|-------|----------|---------|
| `"horror dark gothic"` | Turning children's books creepy | Alice → Horror |
| `"cute kawaii chibi"` | Making horror adorable | Lovecraft → Cute |
| `"cyberpunk neon"` | Modernizing classics | Victorian → Futuristic |
| `"watercolor soft pastel"` | Gentle artistic look | Any book |
| `"pixel art retro 8-bit"` | Gaming aesthetic | Any book |
| `"teletubbies colorful happy"` | Maximum contrast! | Horror → Kids show |

See [STYLE_GUIDE.md](STYLE_GUIDE.md) for more examples and tips.

