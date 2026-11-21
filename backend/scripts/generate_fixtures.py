"""Generate the fictitious test documents in tests/fixtures/documents/.

Run from backend/: `uv run python scripts/generate_fixtures.py`. The output is committed;
re-running it produces equivalent files (PDF bytes include a fixed creation date).
"""

import io
import zipfile
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "documents"

REMOTE_WORK_PAGES = [
    [
        "Remote Work Policy",
        "1. Purpose",
        "This policy explains how employees may work away from the main office.",
        "Remote work is available to employees whose role allows it.",
    ],
    [
        "2. Coworking spaces",
        "Working from a coworking space requires prior manager approval.",
        "Request approval in writing at least five business days in advance.",
        "Approval is valid for one quarter and must be renewed afterwards.",
    ],
]

EXPENSE_PAGES = [
    [
        "Expense Policy",
        "1. General rules",
        "Expenses must be submitted within 30 days with an itemized receipt.",
    ],
    [
        "2. Coworking reimbursement",
        "Coworking reimbursement is limited to US$ 250 per month per employee.",
        "Amounts above the limit are not reimbursed, even with manager approval.",
    ],
]

PARENTAL_LEAVE_MD = """\
# Parental Leave Policy

This policy describes parental leave for the company.

## Eligibility

### Full-time employees

Parental leave applies only to full-time employees with at least six months of service.

### Contractors

Contractors are not covered by this policy.

## Duration

Eligible employees receive sixteen weeks of paid parental leave.
"""

OFFICE_HANDBOOK_TXT = """\
Office Handbook

The office opens at 8 a.m. and closes at 7 p.m. on business days.
Visitors must sign in at the reception desk and wear a badge.
Meeting rooms are booked through the shared calendar, up to two weeks ahead.
"""


def _text_pdf(pages: list[list[str]]) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, invariant=True)
    for lines in pages:
        y = 780
        for line in lines:
            pdf.drawString(72, y, line)
            y -= 24
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _scanned_pdf() -> bytes:
    """A page that only contains a raster image of text: nothing to extract."""
    image = Image.new("RGB", (800, 200), "white")
    ImageDraw.Draw(image).text((20, 80), "NOTICE: office closed on Friday", fill="black")
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4, invariant=True)
    pdf.drawImage(ImageReader(image), 72, 600, width=400, height=100)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def _docx() -> bytes:
    """Minimal Word container: enough to be a real .docx, which the API must reject."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            zipfile.ZipInfo("[Content_Types].xml", date_time=(2026, 1, 1, 0, 0, 0)),
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/'
            'package/2006/content-types"/>',
        )
    return buffer.getvalue()


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = {
        "remote-work-policy.pdf": _text_pdf(REMOTE_WORK_PAGES),
        "expense-policy.pdf": _text_pdf(EXPENSE_PAGES),
        "parental-leave-policy.md": PARENTAL_LEAVE_MD.encode(),
        "office-handbook.txt": OFFICE_HANDBOOK_TXT.encode(),
        "scanned-notice.pdf": _scanned_pdf(),
        "unsupported.docx": _docx(),
    }
    for name, content in files.items():
        (OUT / name).write_bytes(content)
        print(f"wrote {name} ({len(content)} bytes)")


if __name__ == "__main__":
    main()
