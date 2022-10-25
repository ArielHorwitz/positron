"""Find dialog for searching text in code editor."""

from .. import kex as kx


class Find(kx.Modal):

    def __init__(self, session, **kwargs):
        super().__init__(**kwargs)
        self.add(kx.Label(text="Find / Replace"))
