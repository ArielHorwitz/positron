"""Snippets dialog for inserting preset text in code editor."""

import shutil
from itertools import islice
from dataclasses import dataclass
import fuzzysearch
from .. import kex as kx, FONTS_DIR
from ...util import settings
from ...util.file import PROJ_DIR, USER_DIR, toml_load


FONT = str(FONTS_DIR / settings.get("editor.font"))
UI_FONT_SIZE = settings.get("ui.font_size")
MAX_SNIPPETS = 100


@dataclass
class Snippet:
    name: str
    text: str
    move: int = 0  # negative to beginning
    select: int = 0  # negative to select all


def _load_snippets() -> list[Snippet]:
    snippets_file = USER_DIR / "snippets.toml"
    if not snippets_file.exists():
        defaults_file = PROJ_DIR / "positron" / "default_snippets.toml"
        shutil.copy(defaults_file, snippets_file)
    user_snippets = toml_load(snippets_file)
    return [Snippet(k, **v) for k, v in user_snippets.items()]


SNIPPETS = _load_snippets()


class Snippets(kx.Modal):
    snippets = kx.ListProperty()

    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.set_size(hx=0.85, hy=0.8)
        self.make_bg(kx.get_color("lime", a=0.75))
        # Widgets
        title = kx.Label(text="Insert snippet")
        title.set_size(y=50)
        self.snippet_entry = kx.Entry(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            select_on_focus=True,
            write_tab=False,
            text_validate_unfocus=False,
            background_color=kx.XColor(0.12, 0.04, 0.2, 0.5).rgba,
            multiline=False,
        )
        self.snippet_label = kx.Label(
            font_name=FONT,
            font_size=UI_FONT_SIZE,
            halign="left",
            valign="top",
        )

        # Assemble
        main_frame = kx.Box(orientation="vertical")
        main_frame.add(title, self.snippet_entry, self.snippet_label)
        self.add(main_frame)
        self.bind(parent=self._on_parent)
        self.im.register("Insert snippet", self.insert_snippet, "enter")
        self.im.register("Insert snippet (2)", self.insert_snippet, "numpadenter")
        self.snippet_entry.bind(text=self._on_entry_text)
        self._on_entry_text(None, "")

    def insert_snippet(self, *args):
        if not self.snippets:
            return
        snip = self.snippets[0]
        code = self.container.code_editor.code_entry
        original_cidx = code.cursor_index()
        code.insert_text(snip.text)
        move = snip.move
        if move  < 0:  # move to beginning
            move = code.cursor_index() - original_cidx
        final_cidx = code.cursor_index() - move
        code.cursor = code.get_cursor_from_index(final_cidx)
        select = snip.select
        if select < 0:  # select all
            select = final_cidx - original_cidx
        if select:
            start, end = final_cidx - select, final_cidx
            kx.schedule_once(lambda *a: code.select_text(start, end), 0)
        self.dismiss()

    def _on_entry_text(self, w, text):
        def fuzzy_match(name):
            if not text:
                return True
            return fuzzysearch.find_near_matches(
                text,
                name,
                max_l_dist=10,
                max_deletions=0,
                max_insertions=10,
                max_substitutions=0,
            )

        filtered_snippets = (s for s in SNIPPETS if fuzzy_match(s.name))
        self.snippets = islice(filtered_snippets, MAX_SNIPPETS)

    def on_snippets(self, w, snippets):
        self.snippet_label.text = "\n".join(
            f"{s.name:<15} {s.text[:50]!r}"
            for s in snippets
        )

    def _on_parent(self, w, parent):
        super()._on_parent(w, parent)
        if parent is not None:
            self.snippet_entry.text = ""
            self.snippet_entry.focus = True
