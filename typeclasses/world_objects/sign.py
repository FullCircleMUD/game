"""
WorldSign — an immovable sign that displays text when looked at.

Signs are read-only fixtures — no interaction beyond looking.
Multiple visual styles available via sign_style attribute.
Supports multi-line text (use \\n or newline in sign_text).

Usage (build script / prototype):
    sign = create_object(WorldSign, key="a weathered sign",
                         location=room)
    sign.sign_text = "Beware the dragon!"
    sign.sign_style = "post"
"""

from evennia import AttributeProperty

from enums.size import Size
from typeclasses.world_objects.base_fixture import WorldFixture


DEFAULT_STYLE = "post"


def _render_sign(text, style):
    """Render sign text in an ASCII art frame, dynamically sized to content."""
    lines = text.split("\n") if "\n" in text else [text]
    width = max(len(line) for line in lines)
    # Pad each line to the same width
    padded = [f" {line:<{width}} " for line in lines]
    inner_w = width + 2  # 1 space padding each side

    if style == "post":
        top = f"  .{'-' * inner_w}."
        bot = f"  '{'-' * inner_w}'"
        pole = f"  {' ' * (inner_w // 2)}||"
        body = "\n".join(f"  |{p}|" for p in padded)
        return f"{top}\n{body}\n{bot}\n{pole}"

    elif style == "hanging":
        chain_w = inner_w + 2  # include the pipe chars
        half = chain_w // 2
        top = f"  {'=' * half}+{'=' * (chain_w - half)}"
        bot = f"  '{'-' * inner_w}'"
        body = "\n".join(f"  |{p}|" for p in padded)
        return f"{top}\n{body}\n{bot}"

    elif style == "wall":
        border = f"  +{'-' * inner_w}+"
        body = "\n".join(f"  |{p}|" for p in padded)
        return f"{border}\n{body}\n{border}"

    elif style == "stone":
        top = f"  .{'-' * inner_w}."
        bot = f"  \\{'_' * inner_w}/"
        body = "\n".join(f"  /{p}\\" for p in padded)
        return f"{top}\n{body}\n{bot}"

    # Fallback
    border = f"  +{'-' * inner_w}+"
    body = "\n".join(f"  |{p}|" for p in padded)
    return f"{border}\n{body}\n{border}"


class WorldSign(WorldFixture):
    """
    A readable sign. Look at it to see its text rendered in ASCII art.
    """

    size = AttributeProperty(Size.SMALL.value)
    sign_text = AttributeProperty("")
    sign_style = AttributeProperty(DEFAULT_STYLE)

    def return_appearance(self, looker, **kwargs):
        """Render the sign with ASCII art frame."""
        text = self.sign_text or "..."
        style = self.sign_style or DEFAULT_STYLE
        rendered = _render_sign(text, style)
        name = self.get_display_name(looker)
        return f"|w{name}|n\n{rendered}"
