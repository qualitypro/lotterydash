"""Safe draft preview: never print unverified coordinates on official playslips."""
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from .models import Pick3Play, validate_slip


def write_draft_preview(plays: list[Pick3Play], destination: str | Path) -> Path:
    """Generate a clearly labeled LETTER-SIZE planning sheet, not a lottery playslip."""
    validate_slip(plays)
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    pdf = canvas.Canvas(str(target), pagesize=letter)
    pdf.setTitle("LotteryDash draft preview - not a valid playslip")
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(54, 740, "LotteryDash - Draft Pick 3 Preview")
    pdf.setFont("Helvetica", 11)
    pdf.drawString(54, 714, "NOT A LOTTERY PLAYSLIP - NOT FOR TERMINAL SCANNING")
    for index, play in enumerate(plays):
        y = 665 - index * 90
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(54, y, f"Panel {chr(65 + index)}: {play.digits}")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(54, y - 20, f"{play.play_type.value} | ${play.amount} | {play.draw.value} | Fireball: {play.fireball}")
    pdf.save()
    return target
