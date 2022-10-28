"""A patch for key presses not consumed on window focus change (e.g. alt + tab).

This may only affect linux systems. See: https://github.com/kivy/kivy/issues/7239

In order for this patch to work, the object should be initialized once as early as possible, and stored in a namespace that won't get garbage collected.

## Considerations
It seems that either Kivy or the system ensures that the Window gaining focus always happens first, and that the Window losing focus always happens last. And so the solution has to consider that a key press (e.g. "tab") may be the key press that will remove focus from our Window (e.g. alt + tab) later during this frame.

## Solution
Hence we consume the Window's `on_key_` events and only dispatch them a frame later if focus has not changed in the previous frame. This of course breaks the guarantee (if one exists) that gaining focus is always first and losing focus is always last.

Since key releases may happen many frames in the future, we also remember to consume key releases of keys that we consumed their corresponding presses.
"""

from kivy.clock import Clock
from kivy.core.window import Window


class WindowFocusPatch:
    def __init__(self):
        Window.bind(
            focus=self._on_focus,
            on_key_down=self._on_key_down,
            on_key_up=self._on_key_up,
        )
        self._delayed_events = []
        self._dismiss_key_ups = set()
        self._ignore_key_events = False
        self._focus_frame = Clock.frames - 1
        Clock.schedule_interval(self._redispatch, 0)

    def _redispatch(self, *args):
        # Redispatch last frame's `on_key_` events, depending on focus
        events, self._delayed_events = self._delayed_events, []
        focus_changed = Clock.frames - 1 == self._focus_frame
        self._ignore_key_events = True
        for ev in events:
            evtype, key, *_ = ev
            if focus_changed and evtype == "on_key_down":
                self._dismiss_key_ups.add(key)
                continue
            if evtype == "on_key_up" and key in self._dismiss_key_ups:
                self._dismiss_key_ups.remove(key)
                continue
            Window.dispatch(*ev)
        self._ignore_key_events = False

    def _on_focus(self, w, focus):
        self._focus_frame = Clock.frames

    def _on_key_down(self, w, key, sc, text, mods):
        if self._ignore_key_events:
            return False
        self._delayed_events.append(("on_key_down", key, sc, text, mods))
        return True

    def _on_key_up(self, w, key, sc):
        if self._ignore_key_events:
            return False
        self._delayed_events.append(("on_key_up", key, sc))
        return True


