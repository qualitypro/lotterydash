"""Interactive four-corner calibration and Panel A letter proof."""
from pathlib import Path
from decimal import Decimal
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QScrollArea, QMessageBox, QFileDialog
from .slip_geometry import SlipCorners, save_corners, load_corners, scan_to_slip
from .calibration import load_mapping
from .play_mapping import resolve_fields
from .models import Pick3Play
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch, mm

ROOT=Path(__file__).resolve().parents[2]
SCAN=ROOT/"images"/"pick3-playslip.png"
MAP=ROOT/"maps"/"pick3-mapping.json"
CORNERS=ROOT/"maps"/"pick3-slip-corners.json"

class CornerCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.image=QPixmap(str(SCAN))
        if self.image.isNull():raise ValueError(f"Cannot load {SCAN}")
        self.setFixedSize(self.image.size())
        self.corners=[]
        self.on_change=None

    def paintEvent(self,event):
        p=QPainter(self)
        p.drawPixmap(0,0,self.image)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(QPen(QColor("#00ffff"),5))
        for i,(x,y) in enumerate(self.corners):
            px,py=x*self.width(),y*self.height()
            p.drawEllipse(QPointF(px,py),12,12)
            p.drawText(int(px+15),int(py-15),("TL","TR","BR","BL")[i])
        if len(self.corners)==4:
            for i in range(4):
                a=self.corners[i];b=self.corners[(i+1)%4]
                p.drawLine(int(a[0]*self.width()),int(a[1]*self.height()),int(b[0]*self.width()),int(b[1]*self.height()))
        p.end()

    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        x=event.position().x()/self.width()
        y=event.position().y()/self.height()
        if not (0<=x<=1 and 0<=y<=1):return
        if len(self.corners)<4:self.corners.append((x,y))
        else:
            idx=min(range(4),key=lambda i:(self.corners[i][0]-x)**2+(self.corners[i][1]-y)**2)
            self.corners[idx]=(x,y)
        self.update()
        if self.on_change:self.on_change()

def write_proof(destination,corners):
    points=load_mapping(MAP)
    found,missing=resolve_fields(Pick3Play("007"),"A",points)
    if missing:raise ValueError("Missing Panel A coordinates: "+", ".join(missing))
    width,height=8.5*inch,11*inch
    sw,sh=4.25*inch,9.5*inch
    left,bottom=(width-sw)/2,(height-sh)/2
    transformed=[]
    for key,p in found.items():
        u,v=scan_to_slip(p,corners)
        if not (0<=u<=1 and 0<=v<=1):
            raise ValueError(f"{key} lies outside calibrated slip boundaries")
        transformed.append((left+u*sw,bottom+(1-v)*sh))
    pdf=canvas.Canvas(str(destination),pagesize=(width,height))
    pdf.setTitle("LotteryDash four-corner Panel A alignment proof")
    pdf.setStrokeColorRGB(.55,.55,.55)
    pdf.setDash(3,3)
    pdf.rect(left,bottom,sw,sh,stroke=1,fill=0)
    pdf.setDash()
    pdf.setFillColorRGB(0,0,0)
    for x,y in transformed:pdf.circle(x,y,1.75*mm,stroke=0,fill=1)
    pdf.save()

class CornerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LotteryDash | Four-corner slip calibration")
        self.resize(1100,850)
        layout=QVBoxLayout(self)
        layout.addWidget(QLabel("Click corners in order: TOP LEFT, TOP RIGHT, BOTTOM RIGHT, BOTTOM LEFT. Then fine-tune by clicking near each existing marker."))
        self.status=QLabel("")
        layout.addWidget(self.status)
        self.view=CornerCanvas()
        self.view.on_change=self.refresh
        scroll=QScrollArea()
        scroll.setWidget(self.view)
        layout.addWidget(scroll)
        for label,action in (("Reset corners",self.reset),("Save corners",self.save),("Export letter-size Panel A proof",self.export)):
            btn=QPushButton(label);btn.clicked.connect(action);layout.addWidget(btn)
        if CORNERS.exists():
            try:
                c=load_corners(CORNERS)
                self.view.corners=[c.tl,c.tr,c.br,c.bl]
            except (ValueError,KeyError,TypeError,OSError) as e:
                self.status.setText(f"Saved corners not loaded: {e}")
        self.refresh()

    def refresh(self):
        self.status.setText(f"{len(self.view.corners)}/4 corners selected — original scan and bubble mapping are read-only")

    def reset(self):
        self.view.corners=[];self.view.update();self.refresh()

    def current(self):
        if len(self.view.corners)!=4:raise ValueError("Select all four corners first")
        return SlipCorners(*self.view.corners)

    def save(self):
        try:
            save_corners(CORNERS,self.current())
            QMessageBox.information(self,"Saved",f"Saved separately: {CORNERS}")
        except (ValueError,OSError) as e:QMessageBox.warning(self,"Cannot save",str(e))

    def export(self):
        try:c=self.current()
        except ValueError as e:
            QMessageBox.warning(self,"Missing corners",str(e));return
        path,_=QFileDialog.getSaveFileName(self,"Save letter diagnostic",str(ROOT/"panel-a-four-corner-proof.pdf"),"PDF (*.pdf)")
        if not path:return
        try:
            write_proof(path,c)
            save_corners(CORNERS,c)
            QMessageBox.information(self,"Exported",f"Saved: {path}\\nPrint on US Letter at 100%; not verified for direct slip printing.")
        except (ValueError,OSError,KeyError,TypeError) as e:QMessageBox.critical(self,"Export failed",str(e))

def main():
    import sys
    app=QApplication.instance() or QApplication(sys.argv)
    window=CornerWindow();window.show()
    return app.exec()

if __name__=="__main__":raise SystemExit(main())
