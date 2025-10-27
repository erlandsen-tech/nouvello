"""
Generates dynamic Ren'Py style definitions based on book mood and genre
"""
import json
from pathlib import Path
from typing import Dict, Any


class StyleGenerator:
    """Creates Ren'Py style configurations based on book atmosphere"""
    
    # Style presets based on mood/genre
    STYLE_PRESETS = {
        "gothic": {
            "colors": {
                "bg": "#1a0f0f",
                "text": "#d4c4b0",
                "dialogue": "#e8d8c8",
                "accent": "#8b0000",
                "name": "#c89b7e",
            },
            "fonts": {
                "dialogue": "DejaVuSans.ttf",
                "narration": "DejaVuSans.ttf",
                "ui": "DejaVuSans.ttf",
            },
            "effects": {
                "text_speed": 30,
                "transition": "dissolve",
                "window_background": "Frame('gui/textbox_gothic.png', 12, 12)",
            }
        },
        "noir": {
            "colors": {
                "bg": "#0d0d0d",
                "text": "#c8c8c8",
                "dialogue": "#ffffff",
                "accent": "#ffd700",
                "name": "#d4af37",
            },
            "fonts": {
                "dialogue": "DejaVuSans.ttf",
                "narration": "DejaVuSans.ttf",
                "ui": "DejaVuSans.ttf",
            },
            "effects": {
                "text_speed": 35,
                "transition": "fade",
                "window_background": "Frame('gui/textbox_noir.png', 12, 12)",
            }
        },
        "horror": {
            "colors": {
                "bg": "#000000",
                "text": "#8b9090",
                "dialogue": "#b8c5c5",
                "accent": "#660000",
                "name": "#9d2933",
            },
            "fonts": {
                "dialogue": "DejaVuSans.ttf",
                "narration": "DejaVuSans.ttf",
                "ui": "DejaVuSans.ttf",
            },
            "effects": {
                "text_speed": 25,
                "transition": "fade",
                "window_background": "Frame('gui/textbox_horror.png', 12, 12)",
            }
        },
        "romance": {
            "colors": {
                "bg": "#2d1f1f",
                "text": "#f0e6e6",
                "dialogue": "#ffe4e1",
                "accent": "#ff69b4",
                "name": "#ffb6c1",
            },
            "fonts": {
                "dialogue": "DejaVuSans.ttf",
                "narration": "DejaVuSans.ttf",
                "ui": "DejaVuSans.ttf",
            },
            "effects": {
                "text_speed": 40,
                "transition": "dissolve",
                "window_background": "Frame('gui/textbox_romance.png', 12, 12)",
            }
        },
        "adventure": {
            "colors": {
                "bg": "#1a2a1a",
                "text": "#e8e8d0",
                "dialogue": "#f5f5dc",
                "accent": "#daa520",
                "name": "#cd853f",
            },
            "fonts": {
                "dialogue": "DejaVuSans.ttf",
                "narration": "DejaVuSerif.ttf",
                "ui": "DejaVuSans.ttf",
            },
            "effects": {
                "text_speed": 45,
                "transition": "dissolve",
                "window_background": "Frame('gui/textbox_adventure.png', 12, 12)",
            }
        },
        "default": {
            "colors": {
                "bg": "#1f1f1f",
                "text": "#d0d0d0",
                "dialogue": "#ffffff",
                "accent": "#4080ff",
                "name": "#6699ff",
            },
            "fonts": {
                "dialogue": "DejaVuSans.ttf",
                "narration": "DejaVuSans.ttf",
                "ui": "DejaVuSans.ttf",
            },
            "effects": {
                "text_speed": 35,
                "transition": "dissolve",
                "window_background": "Frame('gui/textbox.png', 12, 12)",
            }
        }
    }
    
    def detect_style_from_mood(self, mood_description: str) -> str:
        """Detect appropriate style preset from mood description"""
        mood_lower = mood_description.lower()
        
        # Gothic indicators
        if any(word in mood_lower for word in ["gothic", "dark", "oppressive", "decay", "tragedy"]):
            return "gothic"
        
        # Noir indicators
        if any(word in mood_lower for word in ["noir", "prohibition", "crime", "urban", "gritty"]):
            return "noir"
        
        # Horror indicators
        if any(word in mood_lower for word in ["horror", "terror", "dread", "fear", "cosmic"]):
            return "horror"
        
        # Romance indicators
        if any(word in mood_lower for word in ["romance", "love", "passion", "tender"]):
            return "romance"
        
        # Adventure indicators
        if any(word in mood_lower for word in ["adventure", "quest", "journey", "exploration"]):
            return "adventure"
        
        return "default"
    
    def generate_style_rpy(self, style_preset: str, custom_overrides: Dict[str, Any] = None) -> str:
        """Generate Ren'Py style definition file"""
        if style_preset not in self.STYLE_PRESETS:
            style_preset = "default"
        
        preset = self.STYLE_PRESETS[style_preset].copy()
        
        # Apply custom overrides
        if custom_overrides:
            for category, values in custom_overrides.items():
                if category in preset:
                    preset[category].update(values)
        
        colors = preset["colors"]
        fonts = preset["fonts"]
        effects = preset["effects"]
        
        lines = [
            "# Dynamic style configuration",
            f"# Style preset: {style_preset}",
            "",
            "## GUI Configuration",
            "define gui.text_font = \"" + fonts["dialogue"] + "\"",
            "define gui.name_text_font = \"" + fonts["ui"] + "\"",
            "define gui.interface_text_font = \"" + fonts["ui"] + "\"",
            "",
            "define gui.text_size = 22",
            "define gui.name_text_size = 26",
            "define gui.interface_text_size = 20",
            "",
            f"define gui.accent_color = \"{colors['accent']}\"",
            f"define gui.text_color = \"{colors['text']}\"",
            f"define gui.dialogue_text_color = \"{colors['dialogue']}\"",
            "",
            "## Text speed",
            f"define config.default_text_cps = {effects['text_speed']}",
            "",
            "## Textbox configuration",
            "define gui.textbox_height = 200",
            "define gui.textbox_yalign = 1.0",
            "",
            "## Name box",
            f"define gui.name_xpos = 50",
            f"define gui.name_ypos = 10",
            f"define gui.name_xalign = 0.0",
            "",
            "## Dialogue",
            "define gui.dialogue_xpos = 50",
            "define gui.dialogue_ypos = 50",
            "define gui.dialogue_width = 1160",
            "",
            "## Styles",
            "style default:",
            f'    font "{fonts["narration"]}"',
            f"    color \"{colors['text']}\"",
            "    size gui.text_size",
            "",
            "style say_dialogue:",
            f'    font "{fonts["dialogue"]}"',
            f"    color \"{colors['dialogue']}\"",
            "    size gui.text_size",
            "",
            "style say_label:",
            f'    font "{fonts["ui"]}"',
            f"    color \"{colors['name']}\"",
            "    size gui.name_text_size",
            "    bold True",
            "",
            "## Window background",
            "style window:",
            "    xalign 0.5",
            "    xfill True",
            "    yalign gui.textbox_yalign",
            "    ysize gui.textbox_height",
            f"    background \"{colors['bg']}dd\"",
            "    padding (40, 35)",
            "",
            "## Custom transitions based on mood",
            f'define default_transition = {effects["transition"]}',
            "",
        ]
        
        return "\n".join(lines)
    
    def generate_gui_config(self, book_title: str, style_preset: str) -> str:
        """Generate gui.rpy configuration"""
        if style_preset not in self.STYLE_PRESETS:
            style_preset = "default"
        
        preset = self.STYLE_PRESETS[style_preset]
        colors = preset["colors"]
        
        lines = [
            "## GUI Configuration",
            f"## Title: {book_title}",
            "",
            "define gui.show_name = True",
            "",
            "## Colors",
            f"define gui.idle_color = \"{colors['text']}\"",
            f"define gui.hover_color = \"{colors['accent']}\"",
            f"define gui.selected_color = \"{colors['accent']}\"",
            f"define gui.insensitive_color = \"#8888887f\"",
            "",
            f"define gui.muted_color = \"{colors['text']}80\"",
            f"define gui.hover_muted_color = \"{colors['accent']}ff\"",
            "",
            "## Main/Game Menu",
            "define gui.main_menu_background = \"gui/main_menu.png\"",
            "define gui.game_menu_background = \"gui/game_menu.png\"",
            "",
            "## History",
            "define gui.history_height = 140",
            "define gui.history_name_xpos = 150",
            "define gui.history_name_ypos = 0",
            "define gui.history_name_width = 150",
            "define gui.history_name_xalign = 1.0",
            "define gui.history_text_xpos = 170",
            "define gui.history_text_ypos = 2",
            "define gui.history_text_width = 740",
            "define gui.history_text_xalign = 0.0",
            "",
        ]
        
        return "\n".join(lines)
    
    def generate_sprite_transforms(self) -> str:
        """Generate sprite positioning and scaling transforms"""
        lines = [
            "## Sprite positioning and scaling transforms",
            "",
            "# Character centered in middle - fill upper portion of screen",
            "transform sprite_center:",
            "    xalign 0.5",
            "    yalign 0.38",
            "    fit \"contain\"",
            "    xysize (900, 450)",
            "",
            "# Use center for all positions",
            "transform sprite_right:",
            "    xalign 0.5",
            "    yalign 0.38",
            "    fit \"contain\"",
            "    xysize (900, 450)",
            "",
            "transform sprite_left:",
            "    xalign 0.5",
            "    yalign 0.38",
            "    fit \"contain\"",
            "    xysize (900, 450)",
            "",
            "# Override default positions",
            "define right = sprite_center",
            "define center = sprite_center",
            "define left = sprite_center",
            "",
        ]
        return "\n".join(lines)
    
    def generate_screens_rpy(self) -> str:
        """Generate screens.rpy with proper say screen layout"""
        lines = [
            "## Screens.rpy - Essential UI screens for the visual novel",
            "",
            "## Say Screen",
            "screen say(who, what):",
            "    style_prefix \"say\"",
            "    ",
            "            # Border container",
            "    frame:",
            "        xfill True",
            "        yalign 1.0",
            "        ysize 200",
            "        background \"#d4c4b055\"",
            "        padding (2, 2)",
            "        left_margin 0",
            "        right_margin 0",
            "        ",
            "        # Inner window with text",
            "        window:",
            "            id \"window\"",
            "            xfill True",
            "            yfill True",
            "            background \"#1a0f0fdd\"",
            "            padding (40, 25)",
            "            ",
            "            vbox:",
            "                spacing 10",
            "                xfill True",
            "                ",
            "                if who is not None:",
            "                    text who id \"who\"",
            "                ",
            "                text what id \"what\"",
            "",
            "## Choice Screen",
            "screen choice(items):",
            "    style_prefix \"choice\"",
            "",
            "    vbox:",
            "        for i in items:",
            "            textbutton i.caption action i.action",
            "",
            "## Input Screen",
            "screen input(prompt):",
            "    style_prefix \"input\"",
            "",
            "    window:",
            "        vbox:",
            "            xalign gui.dialogue_text_xalign",
            "            xpos gui.dialogue_xpos",
            "            xsize gui.dialogue_width",
            "            ypos gui.dialogue_ypos",
            "",
            "            text prompt style \"input_prompt\"",
            "            input id \"input\"",
            "",
            "## Main Menu",
            "screen main_menu():",
            "    tag menu",
            "",
            "    style_prefix \"main_menu\"",
            "",
            "    add gui.main_menu_background",
            "",
            "    frame:",
            "        vbox:",
            "            xalign 0.5",
            "            yalign 0.5",
            "            spacing 30",
            "",
            "            textbutton _(\"Start\") action Start()",
            "            textbutton _(\"Load\") action ShowMenu(\"load\")",
            "            textbutton _(\"Preferences\") action ShowMenu(\"preferences\")",
            "            textbutton _(\"About\") action ShowMenu(\"about\")",
            "            textbutton _(\"Quit\") action Quit(confirm=False)",
            "",
            "## Game Menu",
            "screen game_menu(title, scroll=None, yinitial=0.0):",
            "    style_prefix \"game_menu\"",
            "",
            "    add gui.game_menu_background",
            "",
            "    frame:",
            "        vbox:",
            "            hbox:",
            "                textbutton _(\"Return\"):",
            "                    action Return()",
            "",
            "            label title",
            "",
            "            if scroll == \"viewport\":",
            "                viewport:",
            "                    yinitial yinitial",
            "                    scrollbars \"vertical\"",
            "                    mousewheel True",
            "                    draggable True",
            "                    pagekeys True",
            "",
            "                    side_yfill True",
            "",
            "                    vbox:",
            "                        transclude",
            "            elif scroll == \"vpgrid\":",
            "                vpgrid:",
            "                    cols 1",
            "                    yinitial yinitial",
            "                    scrollbars \"vertical\"",
            "                    mousewheel True",
            "                    draggable True",
            "                    pagekeys True",
            "",
            "                    side_yfill True",
            "",
            "                    transclude",
            "            else:",
            "                transclude",
            "",
            "## Navigation Screen",
            "screen navigation():",
            "    vbox:",
            "        style_prefix \"navigation\"",
            "        xpos gui.navigation_xpos",
            "        yalign 0.5",
            "        spacing gui.navigation_spacing",
            "",
            "        textbutton _(\"History\") action ShowMenu(\"history\")",
            "        textbutton _(\"Save\") action ShowMenu(\"save\")",
            "        textbutton _(\"Load\") action ShowMenu(\"load\")",
            "        textbutton _(\"Preferences\") action ShowMenu(\"preferences\")",
            "        textbutton _(\"About\") action ShowMenu(\"about\")",
            "        textbutton _(\"Return\") action Return()",
            "",
            "## About Screen",
            "screen about():",
            "    tag menu",
            "",
            "    use game_menu(_(\"About\"), scroll=\"viewport\"):",
            "        style_prefix \"about\"",
            "",
            "        vbox:",
            "            label \"[config.name!t]\"",
            "            text _(\"Version [config.version!t]\\n\")",
            "            text _(\"Automatically generated from book analysis\")",
            "",
            "## Save/Load Screens",
            "screen save():",
            "    tag menu",
            "    use file_slots(_(\"Save\"))",
            "",
            "screen load():",
            "    tag menu",
            "    use file_slots(_(\"Load\"))",
            "",
            "screen file_slots(title):",
            "    default page_name_value = FilePageNameInputValue(pattern=_(\"Page {}\"), auto=_(\"Automatic saves\"), quick=_(\"Quick saves\"))",
            "",
            "    use game_menu(title):",
            "        fixed:",
            "            vbox:",
            "                hbox:",
            "                    textbutton _(\"<\") action FilePagePrevious()",
            "                    if renpy.current_screen().screen_name[0] == \"save\":",
            "                        textbutton _(\"Page [FileCurrentPage()]\") action FilePage(\"auto\")",
            "                    else:",
            "                        textbutton _(\"Page [FileCurrentPage()]\") action NullAction()",
            "                    textbutton _(\">\") action FilePageNext()",
            "",
            "                grid 3 2:",
            "                    transpose False",
            "                    xfill True",
            "                    style_prefix \"slot\"",
            "",
            "                    for i in range(3*2):",
            "                        $ slot = i + 1",
            "                        button:",
            "                            action FileAction(slot)",
            "                            has vbox",
            "                            add FileScreenshot(slot) xalign 0.5",
            "                            text FileTime(slot, format=_(\"{#file_time}%A, %B %d %Y, %H:%M\"), empty=_(\"empty slot\"))",
            "                            text FileSaveName(slot)",
            "                            key \"save_delete\" action FileDelete(slot)",
            "",
            "## Preferences Screen",
            "screen preferences():",
            "    tag menu",
            "",
            "    use game_menu(_(\"Preferences\"), scroll=\"viewport\"):",
            "        vbox:",
            "            hbox:",
            "                box_wrap True",
            "",
            "                if renpy.variant(\"pc\") or renpy.variant(\"web\"):",
            "                    vbox:",
            "                        style_prefix \"radio\"",
            "                        label _(\"Display\")",
            "                        textbutton _(\"Window\") action Preference(\"display\", \"window\")",
            "                        textbutton _(\"Fullscreen\") action Preference(\"display\", \"fullscreen\")",
            "",
            "                vbox:",
            "                    style_prefix \"radio\"",
            "                    label _(\"Rollback Side\")",
            "                    textbutton _(\"Disable\") action Preference(\"rollback side\", \"disable\")",
            "                    textbutton _(\"Left\") action Preference(\"rollback side\", \"left\")",
            "                    textbutton _(\"Right\") action Preference(\"rollback side\", \"right\")",
            "",
            "                vbox:",
            "                    style_prefix \"check\"",
            "                    label _(\"Skip\")",
            "                    textbutton _(\"Unseen Text\") action Preference(\"skip\", \"toggle\")",
            "                    textbutton _(\"After Choices\") action Preference(\"after choices\", \"toggle\")",
            "",
            "            null height 20",
            "",
            "            hbox:",
            "                style_prefix \"slider\"",
            "                box_wrap True",
            "",
            "                vbox:",
            "                    label _(\"Text Speed\")",
            "                    bar value Preference(\"text speed\")",
            "                    label _(\"Auto-Forward Time\")",
            "                    bar value Preference(\"auto-forward time\")",
            "",
            "                vbox:",
            "                    if config.has_sound:",
            "                        label _(\"Sound Volume\")",
            "                        hbox:",
            "                            bar value Preference(\"sound volume\")",
            "",
            "                    if config.has_music:",
            "                        label _(\"Music Volume\")",
            "                        hbox:",
            "                            bar value Preference(\"music volume\")",
            "",
            "## History Screen",
            "screen history():",
            "    tag menu",
            "",
            "    predict False",
            "",
            "    use game_menu(_(\"History\"), scroll=\"vpgrid\", yinitial=1.0):",
            "        style_prefix \"history\"",
            "",
            "        for h in _history_list:",
            "            window:",
            "                has fixed:",
            "                    yfit True",
            "",
            "                if h.who:",
            "                    label h.who:",
            "                        style \"history_name\"",
            "                        substitute False",
            "",
            "                $ what = renpy.filter_text_tags(h.what, allow=gui.history_allow_tags)",
            "                text what:",
            "                    substitute False",
            "",
            "        if not _history_list:",
            "            label _(\"The dialogue history is empty.\")",
            "",
            "## Quick Menu",
            "screen quick_menu():",
            "    variant \"pc\"",
            "",
            "    zorder 100",
            "",
            "    if quick_menu:",
            "        hbox:",
            "            style_prefix \"quick\"",
            "            xalign 0.5",
            "            yalign 0.02",
            "",
            "            textbutton _(\"Back\") action Rollback()",
            "            textbutton _(\"History\") action ShowMenu('history')",
            "            textbutton _(\"Skip\") action Skip() alternate Skip(fast=True, confirm=True)",
            "            textbutton _(\"Auto\") action Preference(\"auto-forward\", \"toggle\")",
            "            textbutton _(\"Save\") action ShowMenu('save')",
            "            textbutton _(\"Q.Save\") action QuickSave()",
            "            textbutton _(\"Q.Load\") action QuickLoad()",
            "            textbutton _(\"Prefs\") action ShowMenu('preferences')",
            "",
            "## Confirm Screen",
            "screen confirm(message, yes_action, no_action):",
            "    modal True",
            "",
            "    zorder 200",
            "",
            "    style_prefix \"confirm\"",
            "",
            "    add \"gui/overlay/confirm.png\"",
            "",
            "    frame:",
            "        vbox:",
            "            xalign .5",
            "            yalign .5",
            "            spacing 30",
            "",
            "            label _(message):",
            "                style \"confirm_prompt\"",
            "                xalign 0.5",
            "",
            "            hbox:",
            "                xalign 0.5",
            "                spacing 100",
            "",
            "                textbutton _(\"Yes\") action yes_action",
            "                textbutton _(\"No\") action no_action",
            "",
            "    key \"game_menu\" action no_action",
            "",
            "## Notify Screen",
            "screen notify(message):",
            "    zorder 100",
            "    style_prefix \"notify\"",
            "",
            "    frame at notify_appear:",
            "        text \"[message!tq]\"",
            "",
            "    timer 3.25 action Hide('notify')",
            "",
            "transform notify_appear:",
            "    on show:",
            "        alpha 0",
            "        linear .25 alpha 1.0",
            "    on hide:",
            "        linear .5 alpha 0.0",
            "",
            "## NVL Screen (for NVL-style text)",
            "screen nvl(dialogue, items=None):",
            "    window:",
            "        style \"nvl_window\"",
            "",
            "        has vbox:",
            "            style \"nvl_vbox\"",
            "",
            "        for d in dialogue:",
            "            window:",
            "                id d.window_id",
            "",
            "                has hbox:",
            "                    spacing 10",
            "",
            "                if d.who is not None:",
            "                    text d.who id d.who_id",
            "",
            "                text d.what id d.what_id",
            "",
            "        if items:",
            "            vbox:",
            "                id \"menu\"",
            "",
            "                for i in items:",
            "                    textbutton i.caption action i.action",
            "",
            "## Initialize GUI values",
            "init python:",
            "    # Navigation",
            "    gui.navigation_xpos = 40",
            "    gui.navigation_spacing = 4",
            "    ",
            "    # History",
            "    gui.history_allow_tags = set()",
            "",
            "    # Quick menu",
            "    quick_menu = True",
            "",
            "define config.overlay_screens = [\"quick_menu\"]",
            "",
        ]
        return "\n".join(lines)
    
    def create_placeholder_assets(self, game_dir: Path, style_preset: str):
        """Create placeholder GUI assets (textboxes, backgrounds)"""
        gui_dir = game_dir / "gui"
        gui_dir.mkdir(parents=True, exist_ok=True)
        
        # For now, we'll just create empty marker files
        # In production, you'd generate actual image assets
        (gui_dir / "textbox.png").touch()
        (gui_dir / "main_menu.png").touch()
        (gui_dir / "game_menu.png").touch()
        
        # Create a simple README about assets
        readme = gui_dir / "README.txt"
        with open(readme, "w") as f:
            f.write(f"GUI Assets for {style_preset} style\n")
            f.write("These are placeholder files.\n")
            f.write("Replace with actual generated or custom graphics.\n")
    
    def generate_all_styles(self, 
                           book_analysis: Dict[str, Any],
                           game_dir: Path) -> Dict[str, Path]:
        """Generate all style files for a book"""
        mood_desc = book_analysis.get("mood_description", "")
        book_title = book_analysis.get("chapter_title", "Unknown Book")
        
        # Detect appropriate style
        style_preset = self.detect_style_from_mood(mood_desc)
        
        print(f"Detected style preset: {style_preset}")
        
        # Create game directory
        game_dir = Path(game_dir) / "game"
        game_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = {}
        
        # Generate style.rpy
        style_content = self.generate_style_rpy(style_preset)
        style_file = game_dir / "style.rpy"
        with open(style_file, "w") as f:
            f.write(style_content)
        generated_files["style"] = style_file
        
        # Generate gui.rpy
        gui_content = self.generate_gui_config(book_title, style_preset)
        gui_file = game_dir / "gui.rpy"
        with open(gui_file, "w") as f:
            f.write(gui_content)
        generated_files["gui"] = gui_file
        
        # Generate sprite_transforms.rpy
        sprite_transforms_content = self.generate_sprite_transforms()
        sprite_transforms_file = game_dir / "sprite_transforms.rpy"
        with open(sprite_transforms_file, "w") as f:
            f.write(sprite_transforms_content)
        generated_files["sprite_transforms"] = sprite_transforms_file
        
        # Generate screens.rpy
        screens_content = self.generate_screens_rpy()
        screens_file = game_dir / "screens.rpy"
        with open(screens_file, "w") as f:
            f.write(screens_content)
        generated_files["screens"] = screens_file
        
        # Create placeholder assets
        self.create_placeholder_assets(game_dir.parent, style_preset)
        generated_files["gui_assets"] = game_dir.parent / "gui"
        
        return generated_files


def main():
    """Example usage"""
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python style_generator.py <book_analysis.json> <output_dir>")
        sys.exit(1)
    
    book_analysis_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    with open(book_analysis_path) as f:
        book_data = json.load(f)
        if isinstance(book_data, list):
            book_data = book_data[0]
    
    generator = StyleGenerator()
    files = generator.generate_all_styles(book_data, output_dir)
    
    print("Generated style files:")
    for key, value in files.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()

