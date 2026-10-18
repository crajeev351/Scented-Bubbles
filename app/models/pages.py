import html
import json
import re
from datetime import datetime, timezone
from app.extensions import db

_HTML_BLOCK_TAGS_PATTERN = re.compile(
    r"<\s*(p|br|div|h[1-6]|ul|ol|li|table|tr|td|th|blockquote|section|article|header|footer|hr)\b[^>]*>",
    re.IGNORECASE,
)


def format_page_content(text: str) -> str:
    """Format page content intelligently for non-technical admins.
    
    If the text already contains HTML structural tags (<p>, <br>, <div>, etc.),
    it is returned as-is so existing rich content remains intact.
    
    If the text is plain text (no HTML tags, e.g. normal copy-pasted text),
    it converts:
      - Double newlines into distinct <p>...</p> paragraphs.
      - Single newlines inside paragraphs into <br>.
      - Bulleted lines (starting with *, -, or •) into <ul><li>...</li></ul>.
      - Numbered lines (starting with 1., 2., etc.) into <ol><li>...</li></ol>.
      - Section header lines (starting with ### or short title lines ending with :) into <h3>.
    """
    if not text:
        return ""

    # If standard block/break tags are present, consider it already formatted HTML
    if _HTML_BLOCK_TAGS_PATTERN.search(text):
        return text

    # Normalize carriage returns
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""

    # Split into blocks separated by two or more newlines
    blocks = re.split(r"\n{2,}", normalized)
    output_blocks = []

    for block in blocks:
        raw_lines = [line.strip() for line in block.split("\n") if line.strip()]
        if not raw_lines:
            continue

        # 1. Bullet list check
        if all(re.match(r"^[\*\-\•]\s+", line) for line in raw_lines):
            items = "".join(
                f"<li>{html.escape(re.sub(r'^[\*\-\•]\s+', '', line))}</li>"
                for line in raw_lines
            )
            output_blocks.append(f"<ul>{items}</ul>")

        # 2. Numbered list check
        elif all(re.match(r"^\d+[\.\)]\s+", line) for line in raw_lines):
            items = "".join(
                f"<li>{html.escape(re.sub(r'^\d+[\.\)]\s+', '', line))}</li>"
                for line in raw_lines
            )
            output_blocks.append(f"<ol>{items}</ol>")

        # 3. Markdown-style heading or section header (e.g. "### Heading" or "Shipping Policy:")
        elif len(raw_lines) == 1 and (
            re.match(r"^#{1,3}\s+", raw_lines[0])
            or (len(raw_lines[0]) <= 70 and raw_lines[0].endswith(":") and not raw_lines[0].count("."))
        ):
            clean_title = re.sub(r"^#{1,3}\s+", "", raw_lines[0]).rstrip(":")
            output_blocks.append(f"<h3>{html.escape(clean_title)}</h3>")

        # 4. Standard paragraph
        else:
            escaped_lines = [html.escape(line) for line in raw_lines]
            p_content = "<br>".join(escaped_lines)
            output_blocks.append(f"<p>{p_content}</p>")

    return "\n".join(output_blocks)


def ensure_page_columns(engine):
    """Ensures badge_tag, subtitle, and extra_data columns exist across SQLite and PostgreSQL."""
    from sqlalchemy import inspect, text
    try:
        inspector = inspect(engine)
        if "pages" in inspector.get_table_names():
            cols = {c["name"] for c in inspector.get_columns("pages")}
            with engine.connect() as conn:
                if "badge_tag" not in cols:
                    conn.execute(text("ALTER TABLE pages ADD COLUMN badge_tag VARCHAR(100)"))
                if "subtitle" not in cols:
                    conn.execute(text("ALTER TABLE pages ADD COLUMN subtitle VARCHAR(255)"))
                if "extra_data" not in cols:
                    conn.execute(text("ALTER TABLE pages ADD COLUMN extra_data TEXT"))
                conn.commit()
    except Exception:
        pass


class Page(db.Model):
    """Editable informational and policy pages (Privacy, Terms, Shipping, Refund, About)."""
    __tablename__ = "pages"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    badge_tag = db.Column(db.String(100), nullable=True)
    subtitle = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=False)
    extra_data = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    @property
    def formatted_content(self) -> str:
        """Returns auto-formatted HTML content whether entered as HTML or plain copy-pasted text."""
        return format_page_content(self.content)

    @property
    def extras(self) -> dict:
        """Parse extra_data JSON or return empty dict."""
        if not self.extra_data:
            return {}
        try:
            return json.loads(self.extra_data)
        except Exception:
            return {}

    def set_extras(self, data: dict):
        """Serialize dict to extra_data JSON."""
        self.extra_data = json.dumps(data) if data else None

    def __repr__(self):
        return f"<Page {self.slug} - {self.title}>"
