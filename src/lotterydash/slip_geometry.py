"""Four-corner scan-to-slip mapping; source bubble coordinates remain untouched."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass(frozen=True)
class SlipCorners:
    tl: tuple[float,float]
    tr: tuple[float,float]
    br: tuple[float,float]
    bl: tuple[float,float]

    def __post_init__(self):
        for p in (self.tl,self.tr,self.br,self.bl):
            if len(p)!=2 or not all(0<=v<=1 for v in p):
                raise ValueError("Corners must be normalized scan coordinates")
        if abs(_area((self.tl,self.tr,self.br,self.bl))) < 0.001:
            raise ValueError("Corner quadrilateral is degenerate")
        if _area((self.tl,self.tr,self.br,self.bl)) <= 0:
            raise ValueError("Corners must run clockwise TL, TR, BR, BL in image coordinates")

def _area(points):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1]))/2

def save_corners(path, corners):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps({"schema_version":1,"corners":{k:list(getattr(corners,k)) for k in ("tl","tr","br","bl")}},indent=2)+"\n",encoding="utf-8")

def load_corners(path):
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version")!=1:raise ValueError("Unsupported corners version")
    return SlipCorners(**{k:tuple(data["corners"][k]) for k in ("tl","tr","br","bl")})

def _solve(a,b):
    # 8x8 Gaussian elimination with pivoting; no third-party numeric dependency.
    a=[list(row)+[rhs] for row,rhs in zip(a,b)]
    n=len(b)
    for i in range(n):
        pivot=max(range(i,n),key=lambda r:abs(a[r][i]))
        if abs(a[pivot][i])<1e-12:raise ValueError("Invalid or degenerate perspective transform")
        a[i],a[pivot]=a[pivot],a[i]
        d=a[i][i]
        for j in range(i,n+1):a[i][j]/=d
        for r in range(n):
            if r==i:continue
            factor=a[r][i]
            for j in range(i,n+1):a[r][j]-=factor*a[i][j]
    return [a[i][n] for i in range(n)]

def scan_to_slip(point,corners):
    # Homography maps four image corners onto physical normalized slip corners.
    src=(corners.tl,corners.tr,corners.br,corners.bl)
    dst=((0,0),(1,0),(1,1),(0,1))
    rows=[];rhs=[]
    for (x,y),(u,v) in zip(src,dst):
        rows.append([x,y,1,0,0,0,-u*x,-u*y]);rhs.append(u)
        rows.append([0,0,0,x,y,1,-v*x,-v*y]);rhs.append(v)
    h=_solve(rows,rhs)
    x,y=point.x,point.y
    denominator=h[6]*x+h[7]*y+1
    if abs(denominator)<1e-12:raise ValueError("Point has invalid perspective projection")
    return ((h[0]*x+h[1]*y+h[2])/denominator,
            (h[3]*x+h[4]*y+h[5])/denominator)
