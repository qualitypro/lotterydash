"""US Letter diagnostic for separating printer scaling from scan crop errors."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm
from .calibration import load_mapping
from .play_mapping import resolve_fields

def write_diagnostic(play, destination, mapping_path, crop=(0,0,1,1), mark_mm=3.5):
    """crop is (left, top, right, bottom) in normalized scan coordinates."""
    left, top, right, bottom = crop
    if not (0 <= left < right <= 1 and 0 <= top < bottom <= 1):
        raise ValueError("Crop must be a normalized rectangle within the scan")
    if not (0.5 <= mark_mm <= 5):
        raise ValueError("Mark diameter must be 0.5 to 5 mm")
    found, missing = resolve_fields(play, "A", load_mapping(mapping_path))
    if missing:
        raise ValueError("Missing Panel A coordinates: " + ", ".join(missing))
    width, height = 8.5*inch, 11*inch
    slip_w, slip_h = 4.25*inch, 9.5*inch
    sx, sy = (width-slip_w)/2, (height-slip_h)/2
    radius = mark_mm*mm/2
    marks = []
    for p in found.values():
        u, v = (p.x-left)/(right-left), (p.y-top)/(bottom-top)
        if not (0 <= u <= 1 and 0 <= v <= 1):
            raise ValueError("Selected mark outside scan crop; check crop bounds")
        marks.append((sx+u*slip_w, sy+(1-v)*slip_h))
    path=Path(destination)
    path.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(path),pagesize=(width,height))
    c.setTitle("LotteryDash letter-size scale and scan-crop diagnostic")
    c.setStrokeColorRGB(.45,.45,.45)
    c.setDash(3,3)
    c.rect(sx,sy,slip_w,slip_h,stroke=1,fill=0)
    c.setDash()
    # 100-mm horizontal scale bar in unused right-hand margin.
    bar_x=sx+slip_w+10*mm
    bar_y=sy+slip_h-10*mm
    c.setStrokeColorRGB(0,0,0)
    c.setLineWidth(.65)
    c.line(bar_x,bar_y,bar_x,bar_y-100*mm)
    for n in range(0,101,10):
        y=bar_y-n*mm
        c.line(bar_x,y,bar_x+(5 if n%50==0 else 3)*mm,y)
        if n in (0,50,100):
            c.setFont("Helvetica",7)
            c.drawString(bar_x+6*mm,y-2,n.__str__()+" mm")
    c.setFont("Helvetica",7)
    c.drawString(sx,sy-9*mm,"Slip footprint: 4.25 x 9.5 in; print US Letter at 100%")
    c.setFillColorRGB(0,0,0)
    for x,y in marks:
        c.circle(x,y,radius,stroke=0,fill=1)
    c.save()
    return path
