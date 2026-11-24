"""Draw the way-out sketch as SVG on the server: room boxes by floor, labelled lines, doors out and the meeting place, split into pages.

Decision 0118. Lego level on purpose: a floor's rooms sit in a grid of three, in the steady order
core/exit_sketch.py gives them, so the same records always give the same picture. Lines join rooms drawn in
the same block; a connection to a room drawn elsewhere (another floor, block or page) is written beside the
room instead of running off the page. Words and line patterns carry every meaning, never colour alone. No
script, nothing fetched; every room and line is a link to its own record.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from markupsafe import Markup, escape

from dashboard.core import exit_sketch as facts

WIDTH = 600          # drawing units; 600 units print about 18.6 cm wide, so 12-unit text prints near 10 pt
COLUMNS = 3
CELL = WIDTH // COLUMNS
BOX_W = 150
FONT, SMALL = 14, 12
LINE = 16            # height of one line of a room's name
TAG_LINE = 14        # height of one line of words under a room
NAME_CHARS = 20      # characters of a room name on one line of its box (whole words wrap, never cut)
TAG_CHARS = 30       # characters of one line of words under a room
MOST_TAG_LINES = 12  # beyond this a room says how many more connections the text version lists
HEADING = 26         # a floor's heading at the top of each block
BOW = 20             # how far above a row a line between its two end rooms rises
GAP = 26             # room between rows for lines and their labels
ROWS_PER_BLOCK = 3
# Page room, in drawing units, for A4 and Letter alike (Letter is the shorter page). The first page also
# holds the title, warnings, meeting place, legend and Check together, so it keeps less room for drawing.
FIRST_PAGE = 330
SHARED_SHORT = "May share one exit"
OTHER_PAGE = 720


def wrap(text: str, width: int) -> list[str]:
    """Whole words to lines of at most `width` characters; a longer word is split, never dropped."""
    lines, line = [], ""
    for word in text.split():
        while len(word) > width:
            if line:
                lines.append(line)
                line = ""
            lines.append(word[:width - 1] + "-")
            word = word[width - 1:]
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}" if line else word
    if line or not lines:
        lines.append(line)
    return lines


@dataclass
class Tag:
    """Words under a room: a door out (with an arrow), a link drawn elsewhere, a marker or a route note."""
    words: str
    arrow: str | None = None       # "solid" for a possible way outside, "dashed" for one that needs checking
    link: int | None = None        # the connection record it is about
    page_of: int | None = None     # the other room, whose page number is filled in once pages are known


@dataclass
class Placed:
    room: facts.Room
    x: float
    y: float
    name_lines: list[str]
    tags: list[Tag]
    lines: list[list[str]] = field(default_factory=list)

    @property
    def box_h(self) -> float:
        return 14 + LINE * len(self.name_lines) + (LINE if self.room.sleeping else 0)

    def centre(self) -> tuple[float, float]:
        return self.x + BOX_W / 2, self.y + self.box_h / 2


@dataclass
class Block:
    """Up to three rows of one floor's rooms, drawn as one picture that never splits across pages."""
    floor: str
    continued: bool
    rooms: list[facts.Room]
    placed: list[Placed] = field(default_factory=list)
    height: float = 0
    meeting: list[str] = field(default_factory=list)   # the meeting place's lines, on the first block only
    page: int = 0


def _tags(room: facts.Room, inside: set[int]) -> list[Tag]:
    """The words under a room box: links not drawn as lines here, its markers, and its route notes."""
    tags = []
    for link in room.links:
        if link.kind == "outside_door" and link.outside:
            into = f" into {link.other_name}" if link.other_name else ""
            tags.append(Tag(f"Door out{into}: {link.short}", "solid" if link.exit else "dashed", link.id))
        elif link.other is None or link.other not in inside:
            tags.append(Tag(link.words, None, link.id, link.other))
    if room.window:
        tags.append(Tag(facts.WINDOW, "dashed"))
    tags += [Tag(short_note(note)) for note in room.notes]
    return tags


def short_note(note: str) -> str:
    """A route note in the few words drawn under a room; the legend and text version give the full sentence."""
    if note.startswith(facts.SHARED_WAY):
        return SHARED_SHORT + ": " + note.split("Shared: ", 1)[1].rstrip(".")
    return facts.SHORT.get(note, note)


def _tag_lines(tag: Tag) -> list[str]:
    words = tag.words + (" (page 00)" if tag.page_of is not None else "")
    return wrap(words, TAG_CHARS - (3 if tag.arrow else 0))


def _place(block: Block) -> None:
    """Rooms in a grid of three, rows as tall as their tallest cell, with the meeting place band on the first."""
    inside = {r.id for r in block.rooms}
    y = HEADING
    for start in range(0, len(block.rooms), COLUMNS):
        row = []
        for col, room in enumerate(block.rooms[start:start + COLUMNS]):
            p = Placed(room, col * CELL + (CELL - BOX_W) / 2, y, wrap(room.name, NAME_CHARS), _tags(room, inside))
            row.append(p)
        tallest = 0
        for p in row:
            count = sum(len(_tag_lines(t)) for t in p.tags)
            if count > MOST_TAG_LINES:
                kept, used = [], 0
                for t in p.tags:
                    if used + len(_tag_lines(t)) > MOST_TAG_LINES - 2:
                        break
                    kept.append(t)
                    used += len(_tag_lines(t))
                more = len(p.tags) - len(kept)
                p.tags = kept + [Tag(f"And {more} more: every one is in the text version.")]
                count = sum(len(_tag_lines(t)) for t in p.tags)
            tallest = max(tallest, p.box_h + 8 + TAG_LINE * count)
        block.placed += row
        y += tallest + GAP
    block.height = y - GAP + 12 + _band(block)


def _band(block: Block) -> float:
    return 18 + 15 * len(block.meeting) if block.meeting else 0


def blocks(sketch: facts.Sketch) -> list[Block]:
    """Every floor's rooms in blocks of at most three rows, in order; the first block also shows the meeting place."""
    found = []
    for _key, words, rooms in sketch.floors:
        step = COLUMNS * ROWS_PER_BLOCK
        for i in range(0, len(rooms), step):
            found.append(Block(words, i > 0, rooms[i:i + step]))
    if not found:
        found.append(Block("No rooms on the sketch yet", False, []))
    found[0].meeting = wrap(f"Outside meeting place: {sketch.meeting or 'Not recorded'}", 72)
    for block in found:
        _place(block)
    return found


def paginate(found: list[Block]) -> int:
    """Give each block a page, in order, never splitting one; return the number of pages."""
    page, used = 1, 0
    for block in found:
        room = FIRST_PAGE if page == 1 else OTHER_PAGE
        if used and used + block.height > room:
            page, used = page + 1, 0
        elif not used and page == 1 and block.height > FIRST_PAGE:
            page = 2  # the first page keeps its warnings, legend and Check together readable
        block.page = page
        used += block.height
    return max(b.page for b in found)


def _text(x, y, words, cls="", size=SMALL, anchor="start", weight=None) -> str:
    extra = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x:.0f}" y="{y:.0f}" font-size="{size}" text-anchor="{anchor}"'
            f'{f" class={chr(34)}{cls}{chr(34)}" if cls else ""}{extra}>{escape(words)}</text>')


def _arrow(x, y, style: str) -> str:
    dash = ' stroke-dasharray="4 3"' if style == "dashed" else ""
    return (f'<path class="sk-line" d="M{x:.0f} {y - 4:.0f} h14" fill="none" stroke-width="2"{dash}/>'
            f'<path class="sk-head" d="M{x + 14:.0f} {y - 8:.0f} l7 4 l-7 4 z"/>')


def _edge(a: Placed, b: Placed) -> tuple[float, float, float, float]:
    """Where a line between two boxes leaves one box and meets the other, centre to centre, clipped to the boxes."""
    (ax, ay), (bx, by) = a.centre(), b.centre()

    def clip(cx, cy, h, tx, ty):
        dx, dy = tx - cx, ty - cy
        if dx == dy == 0:
            return cx, cy
        sx = (BOX_W / 2) / abs(dx) if dx else float("inf")
        sy = (h / 2) / abs(dy) if dy else float("inf")
        s = min(sx, sy)
        return cx + dx * s, cy + dy * s
    x1, y1 = clip(ax, ay, a.box_h, bx, by)
    x2, y2 = clip(bx, by, b.box_h, ax, ay)
    return x1, y1, x2, y2


def svg(block: Block, sketch: facts.Sketch, sid: str, pages: dict[int, int], record_href) -> Markup:
    """One block as SVG: its floor heading, lines first, then boxes over them, then the words under each room."""
    title = f"{block.floor}{' (continued)' if block.continued else ''}"
    by_room = {p.room.id: p for p in block.placed}
    body = [_text(4, 20, title, "sk-floor", FONT + 2, weight="700")]
    drawn = set()
    for p in block.placed:
        for link in p.room.links:
            other = by_room.get(link.other) if link.other is not None else None
            if other is None or link.kind == "outside_door" or link.id in drawn:
                continue
            drawn.add(link.id)
            x1, y1, x2, y2 = _edge(p, other)
            dash = "" if link.solid else ' stroke-dasharray="6 4"'
            skip = abs(p.x - other.x) > CELL and abs(p.y - other.y) < 1  # same row, a room between: bow over it
            if skip:  # leave from the tops of both boxes and bow well above the room between them
                (x1, y1), (x2, y2) = (p.x + BOX_W / 2, p.y), (other.x + BOX_W / 2, other.y)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2 - (BOW if skip else 0)
            path = (f"M{x1:.0f} {y1:.0f} Q{mx:.0f} {my - BOW:.0f} {x2:.0f} {y2:.0f}" if skip
                    else f"M{x1:.0f} {y1:.0f} L{x2:.0f} {y2:.0f}")
            said = f"{p.room.name}: {link.words}"
            body.append(f'<a href="{escape(record_href("connection", link.id))}" class="sk-mark" '
                        f'data-connection="{link.id}" aria-label="{escape(said)}"><title>{escape(said)}</title>'
                        f'<path class="sk-line" d="{path}" fill="none" stroke-width="2"{dash}/>'
                        f'<rect class="sk-label-bg" x="{mx - 3.6 * len(link.short) - 4:.0f}" y="{my - 10:.0f}" '
                        f'width="{7.2 * len(link.short) + 8:.0f}" height="15" rx="3"/>'
                        + _text(mx, my + 2, link.short, "sk-label", 11, "middle") + "</a>")
    for p in block.placed:
        room = p.room
        said = f"{room.name}, {room.floor_words}" + (", someone sleeps here" if room.sleeping else "")
        body.append(f'<a href="{escape(record_href("room", room.id))}" class="sk-mark" data-room="{room.id}" '
                    f'aria-label="{escape(said)}"><title>{escape(said)}</title>'
                    f'<rect class="sk-box" x="{p.x:.0f}" y="{p.y:.0f}" width="{BOX_W}" height="{p.box_h:.0f}" '
                    f'rx="4" stroke-width="2"/>')
        y = p.y + 4
        for line in p.name_lines:
            y += LINE
            body.append(_text(p.x + BOX_W / 2, y, line, "sk-name", FONT, "middle", "700"))
        if room.sleeping:
            y += LINE
            body.append(_text(p.x + BOX_W / 2, y, "Sleeping room", "sk-small", SMALL, "middle"))
        body.append("</a>")
        y = p.y + p.box_h + 8
        for tag in p.tags:
            words = tag.words + (f" (page {pages[tag.page_of]})" if tag.page_of in pages and
                                 pages[tag.page_of] != block.page else "")
            parts = []
            for i, line in enumerate(wrap(words, TAG_CHARS - (3 if tag.arrow else 0))):
                y += TAG_LINE
                if tag.arrow and i == 0:
                    parts.append(_arrow(p.x, y, tag.arrow))
                parts.append(_text(p.x + (26 if tag.arrow else 0), y, line, "sk-tag", 11))
            if tag.link is not None:
                said = f"{room.name}: {words}"
                parts = [f'<a href="{escape(record_href("connection", tag.link))}" class="sk-mark" '
                         f'data-connection="{tag.link}" aria-label="{escape(said)}">'] + parts + ["</a>"]
            body += parts
    if block.meeting:
        top = block.height - _band(block)
        body.append(f'<rect class="sk-meet" x="4" y="{top + 4:.0f}" width="{WIDTH - 8}" '
                    f'height="{_band(block) - 8:.0f}" rx="14" stroke-width="2" stroke-dasharray="2 3"/>')
        for i, line in enumerate(block.meeting):
            body.append(_text(WIDTH / 2, top + 20 + i * 15, line, "sk-name", SMALL + 1, "middle", "700"))
    if not block.placed:
        body.append(_text(4, HEADING + 18, "Add rooms and connections in Set up my home to draw them here.",
                          "sk-tag", SMALL))
    height = max(block.height, HEADING + 30 + _band(block))
    description = (f"{title}: {len(block.placed)} room{'s' if len(block.placed) != 1 else ''}. "
                   "The text version below lists every room and connection in the same order.")
    return Markup(
        f'<svg class="sketch-svg" viewBox="0 0 {WIDTH} {height:.0f}" width="{WIDTH}" height="{height:.0f}" '
        f'role="group" aria-labelledby="{sid}-title" aria-describedby="{sid}-desc" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="system-ui, Segoe UI, Arial, sans-serif">'
        f'<title id="{sid}-title">{escape(title)}</title><desc id="{sid}-desc">{escape(description)}</desc>'
        + "".join(body) + "</svg>")


def drawn(sketch: facts.Sketch, record_href) -> tuple[list[dict], int]:
    """Every block's picture with its page, and the number of pages the sheet needs."""
    found = blocks(sketch)
    count = paginate(found)
    pages = {p.room.id: b.page for b in found for p in b.placed}
    return [{"page": b.page, "floor": b.floor, "continued": b.continued,
             "svg": svg(b, sketch, f"sketch-{i}", pages, record_href)} for i, b in enumerate(found)], count
