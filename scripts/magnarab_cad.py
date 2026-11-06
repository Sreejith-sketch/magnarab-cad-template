#!/usr/bin/env python3
"""MAGNARAB A1 CAD sheet tool.

Three jobs, all on the official MAGNARAB A1 template (title block is never redrawn,
only its 12 attributes are filled):

  new    Draw a laundry layout from a JSON spec onto the A1 sheet.
  frame  Put an existing DXF (e.g. Vaseem's AutoCAD drawing) inside the A1 sheet.
  render Turn any finished sheet DXF into an A1 PDF + PNG preview.

`new` and `frame` also render the PDF and PNG automatically.

Usage:
  python magnarab_cad.py new   --spec spec.json --out OUTDIR/Layout_2058_Rev00
  python magnarab_cad.py frame --input client.dxf --spec spec.json --out OUTDIR/Layout_2058_Rev00
  python magnarab_cad.py render --dxf sheet.dxf --out OUTDIR/Layout_2058_Rev00

Model units are millimetres, real size. The script picks a standard scale that fits.
Needs: pip install ezdxf matplotlib
"""
import argparse
import json
import math
import os
import sys

import ezdxf
from ezdxf import bbox
from ezdxf.addons import Importer

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "template", "MAGNARAB_A1_Full_Width_Title_Block.dxf")
TB_BLOCK = "MAGNARAB_LAUNDRY_PROJECTS_TITLEBLOCK_A1"

SHEET_W, SHEET_H = 841.0, 594.0
# Drawing area inside the border, above the 55 mm title block
AREA_X0, AREA_Y0, AREA_X1, AREA_Y1 = 15.0, 70.0, 826.0, 579.0
PAD = 12.0                       # breathing room inside the drawing area
SCHEDULE_W = 196.0               # right-hand column for equipment schedule + notes
STD_SCALES = [1, 2, 5, 10, 20, 25, 50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 750, 1000, 1250, 1500, 2000, 2500, 5000]

FIELDS = ["PROJECT", "CLIENT", "DRAWING_TITLE", "DRAWING_NO", "REVISION", "SCALE",
          "DATE", "DRAWN_BY", "CHECKED_BY", "APPROVED_BY", "SHEET", "STATUS"]
DEFAULTS = {"DRAWN_BY": "Vaseem", "CHECKED_BY": "Sreejith", "APPROVED_BY": "Sreejith",
            "REVISION": "00", "SHEET": "1 of 1", "STATUS": "Concept"}
STATUS_WORDS = ["Concept", "For Approval", "Final"]

# Content layers (plain ACI colours, one text style - the house rule is no font/colour play)
LAYERS = {
    "A-WALL": 7, "A-ZONE": 8, "A-DOOR": 7, "E-EQUIP": 7, "E-TAG": 7,
    "E-CLEAR": 8, "A-DIMS": 7, "A-TEXT": 7, "SCHEDULE": 7,
}


# --------------------------------------------------------------------------- helpers
def load_spec(path):
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def open_template():
    if not os.path.exists(TEMPLATE):
        sys.exit(f"Template not found: {TEMPLATE}")
    doc = ezdxf.readfile(TEMPLATE)
    for name, col in LAYERS.items():
        if name not in doc.layers:
            doc.layers.add(name, color=col)
    doc.layers.get("E-CLEAR").dxf.linetype = ensure_dashed(doc)
    return doc


def ensure_dashed(doc):
    if "DASHED" not in doc.linetypes:
        doc.linetypes.add("DASHED", pattern=[0.6, 0.4, -0.2], description="Dashed __ __ __")
    return "DASHED"


def pick_scale(ext_w, ext_h, avail_w, avail_h, forced=None):
    if forced:
        return forced
    for n in STD_SCALES:
        if ext_w / n <= avail_w and ext_h / n <= avail_h:
            return n
    return STD_SCALES[-1]


def parse_scale(v):
    if v in (None, "", "auto"):
        return None
    s = str(v).replace(" ", "")
    if ":" in s:
        a, b = s.split(":")
        return float(b) / float(a)
    return float(s)


def fill_title_block(doc, title, scale_n):
    vals = dict(DEFAULTS)
    vals.update({k.upper(): v for k, v in (title or {}).items() if v not in (None, "")})
    if scale_n:
        vals["SCALE"] = f"1:{int(scale_n) if float(scale_n).is_integer() else scale_n} @ A1"
    vals.setdefault("SCALE", "NTS")
    if vals.get("STATUS") not in STATUS_WORDS:
        print(f"note: status '{vals.get('STATUS')}' is not one of {STATUS_WORDS}", file=sys.stderr)
    msp = doc.modelspace()
    ins = next(e for e in msp.query("INSERT") if e.dxf.name == TB_BLOCK)
    for a in ins.attribs:
        tag = a.dxf.tag
        if tag in vals:
            a.dxf.text = str(vals[tag])
    missing = [f for f in ("PROJECT", "CLIENT", "DRAWING_TITLE", "DRAWING_NO", "DATE") if not vals.get(f)]
    if missing:
        print("warning: title block fields left blank: " + ", ".join(missing), file=sys.stderr)
    return vals


def place_content_block(doc, block_name, ext, scale_n, area):
    """Insert real-size block into the drawing area, centred, at 1/scale_n."""
    (x0, y0), (x1, y1) = ext
    ax0, ay0, ax1, ay1 = area
    s = 1.0 / scale_n
    cx_model, cy_model = (x0 + x1) / 2, (y0 + y1) / 2
    cx_paper, cy_paper = (ax0 + ax1) / 2, (ay0 + ay1) / 2
    ins_pt = (cx_paper - cx_model * s, cy_paper - cy_model * s)
    doc.modelspace().add_blockref(block_name, ins_pt, dxfattribs={"xscale": s, "yscale": s, "layer": "0"})


def setup_dimstyle(doc, n):
    name = "MAG_DIM"
    if name not in doc.dimstyles:
        ds = doc.dimstyles.new(name)
    else:
        ds = doc.dimstyles.get(name)
    ds.dxf.dimtxt = 2.5
    ds.dxf.dimasz = 2.0
    ds.dxf.dimtsz = 1.5      # architectural ticks
    ds.dxf.dimexo = 1.5
    ds.dxf.dimexe = 1.5
    ds.dxf.dimgap = 1.0
    ds.dxf.dimscale = n
    ds.dxf.dimdec = 0
    ds.dxf.dimtad = 1
    ds.dxf.dimtih = 0
    ds.dxf.dimtoh = 0
    return name


# --------------------------------------------------------------------------- drawing from spec
def rot_pts(cx, cy, w, d, rot):
    a = math.radians(rot)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for dx, dy in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)):
        pts.append((cx + dx * ca - dy * sa, cy + dx * sa + dy * ca))
    return pts


def build_content(doc, spec, n):
    blk = doc.blocks.new("DWG_CONTENT")
    th = lambda paper_mm: paper_mm * n  # noqa: E731  paper text height -> model height

    # Walls: list of polylines (closed or open), each with a thickness in mm
    for w in spec.get("walls", []):
        pts = [tuple(p) for p in w["points"]]
        closed = w.get("closed", True)
        t = w.get("thickness", 200)
        blk.add_lwpolyline(pts, close=closed, dxfattribs={"layer": "A-WALL", "const_width": 0})
        # second line offset inward to show thickness (simple: offset polygon via ezdxf path)
        try:
            from ezdxf.math import offset_vertices_2d
            inner = list(offset_vertices_2d(pts, offset=t, closed=closed))
            blk.add_lwpolyline([(v.x, v.y) for v in inner], close=closed, dxfattribs={"layer": "A-WALL"})
        except Exception:
            pass

    for z in spec.get("zones", []):
        pts = [tuple(p) for p in z["points"]]
        blk.add_lwpolyline(pts, close=True, dxfattribs={"layer": "A-ZONE"})
        cx = sum(p[0] for p in pts) / len(pts)
        ymax = max(p[1] for p in pts)
        lp = z.get("label_at", (cx, ymax - th(6)))
        blk.add_text(z["name"].upper(), height=th(3.0), dxfattribs={"layer": "A-TEXT"}).set_placement(
            tuple(lp), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    for dr in spec.get("doors", []):
        # door: hinge point, width, angle of the closed leaf (deg), swing +1/-1
        hx, hy = dr["at"]
        wdt = dr.get("width", 1000)
        ang = dr.get("angle", 0)
        sw = dr.get("swing", 1)
        a0 = math.radians(ang)
        a1 = a0 + sw * math.pi / 2
        blk.add_line((hx, hy), (hx + wdt * math.cos(a1), hy + wdt * math.sin(a1)), dxfattribs={"layer": "A-DOOR"})
        start, end = (math.degrees(a0), math.degrees(a1)) if sw > 0 else (math.degrees(a1), math.degrees(a0))
        blk.add_arc((hx, hy), wdt, start, end, dxfattribs={"layer": "A-DOOR"})
        if dr.get("label"):
            blk.add_text(dr["label"], height=th(2.2), dxfattribs={"layer": "A-TEXT"}).set_placement(
                (hx + wdt * 0.5 * math.cos((a0 + a1) / 2), hy + wdt * 0.5 * math.sin((a0 + a1) / 2)),
                align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    for eq in spec.get("equipment", []):
        cx, cy = eq["x"], eq["y"]
        w, d, rot = eq["w"], eq["d"], eq.get("rot", 0)
        pts = rot_pts(cx, cy, w, d, rot)
        blk.add_lwpolyline(pts, close=True, dxfattribs={"layer": "E-EQUIP"})
        # front marker: short line on the front edge (front = the -y side before rotation)
        f = rot_pts(cx, cy, w * 0.6, d - min(d * 0.15, 120) * 2, rot)
        blk.add_line(f[0], f[1], dxfattribs={"layer": "E-EQUIP"})
        cf = eq.get("clear_front")
        if cf:
            a = math.radians(rot)
            ox, oy = -math.sin(a) * -1, math.cos(a) * -1  # unit vector pointing to front (-y local)
            ccx, ccy = cx + ox * (d / 2 + cf / 2), cy + oy * (d / 2 + cf / 2)
            # drawn as real dash segments so it prints dashed in every viewer and in the PDF
            cpts = rot_pts(ccx, ccy, w, cf, rot)
            dash, gap = 3.0 * n, 2.0 * n
            for i in range(4):
                (ax_, ay_), (bx_, by_) = cpts[i], cpts[(i + 1) % 4]
                L_ = math.hypot(bx_ - ax_, by_ - ay_)
                if L_ == 0:
                    continue
                ux, uy = (bx_ - ax_) / L_, (by_ - ay_) / L_
                t = 0.0
                while t < L_:
                    t2 = min(t + dash, L_)
                    blk.add_line((ax_ + ux * t, ay_ + uy * t), (ax_ + ux * t2, ay_ + uy * t2),
                                 dxfattribs={"layer": "E-CLEAR"})
                    t = t2 + gap
        tag = eq.get("tag", "")
        if tag:
            ht = th(3.2)
            ht = min(ht, min(w, d) * 0.45)
            blk.add_text(tag, height=ht, dxfattribs={"layer": "E-TAG"}).set_placement(
                (cx, cy), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    for t in spec.get("labels", []):
        blk.add_text(t["text"], height=th(t.get("size", 2.5)), dxfattribs={"layer": "A-TEXT", "rotation": t.get("rot", 0)}
                     ).set_placement(tuple(t["at"]), align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER)

    dim = setup_dimstyle(doc, n)
    for dd in spec.get("dims", []):
        p1, p2 = tuple(dd["p1"]), tuple(dd["p2"])
        off = dd.get("offset", -th(10))
        horiz = abs(p2[0] - p1[0]) >= abs(p2[1] - p1[1])
        if horiz:
            base = (p1[0], min(p1[1], p2[1]) + off)
            angle = 0
        else:
            base = (min(p1[0], p2[0]) + off, p1[1])
            angle = 90
        d_ = blk.add_linear_dim(base=base, p1=p1, p2=p2, angle=angle, dimstyle=dim,
                                dxfattribs={"layer": "A-DIMS"})
        d_.render()
    return blk


def model_extents(doc, block):
    e = bbox.extents(block, fast=True)
    if not e.has_data:
        sys.exit("Nothing to draw: spec has no walls, zones or equipment.")
    return (e.extmin.x, e.extmin.y), (e.extmax.x, e.extmax.y)


# --------------------------------------------------------------------------- schedule + notes (paper space mm)
def draw_schedule(doc, equipment, notes, x0, y_top):
    msp = doc.modelspace()
    cols = [("TAG", 14), ("EQUIPMENT / MODEL", 84), ("SIZE W×D mm", 36), ("kg", 18), ("kW", 18), ("QTY", 12)]
    total = sum(c[1] for c in cols)
    rh, txt = 6.5, 2.4
    L = {"layer": "SCHEDULE"}
    y = y_top
    msp.add_text("EQUIPMENT SCHEDULE", height=3.2, dxfattribs=L).set_placement((x0, y - 4.5))
    y -= 8
    rows = [[c[0] for c in cols]]
    for e in equipment:
        name = e.get("name", "")
        if e.get("model"):
            name = f"{name} – {e['model']}" if name else e["model"]
        rows.append([e.get("tag", ""), name, f"{int(e['w'])}×{int(e['d'])}",
                     fmt(e.get("kg")), fmt(e.get("kw")), fmt(e.get("qty", 1))])
    top = y
    for r_i, row in enumerate(rows):
        x = x0
        for (hdr, wdt), val in zip(cols, row):
            s = str(val)
            max_chars = int(wdt / (txt * 0.62))
            if len(s) > max_chars:
                s = s[: max_chars - 1] + "…"
            msp.add_text(s, height=txt, dxfattribs=L).set_placement((x + 1.5, y - rh + 2.0))
            x += wdt
        y -= rh
        msp.add_line((x0, y), (x0 + total, y), dxfattribs=L)
    msp.add_lwpolyline([(x0, top), (x0 + total, top), (x0 + total, y), (x0, y)], close=True, dxfattribs=L)
    x = x0
    for _, wdt in cols[:-1]:
        x += wdt
        msp.add_line((x, top), (x, y), dxfattribs=L)
    msp.add_line((x0, top - rh), (x0 + total, top - rh), dxfattribs=L)
    if notes:
        y -= 10
        msp.add_text("NOTES", height=3.2, dxfattribs=L).set_placement((x0, y))
        y -= 6
        for i, n in enumerate(notes, 1):
            for line in wrap(f"{i}. {n}", int(total / (txt * 0.6))):
                msp.add_text(line, height=txt, dxfattribs=L).set_placement((x0, y))
                y -= 4.4
            y -= 1.0
    return y


def fmt(v):
    if v in (None, ""):
        return "–"
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v)


def wrap(s, width):
    import textwrap
    return textwrap.wrap(s, width=width, subsequent_indent="   ") or [""]


# --------------------------------------------------------------------------- render
def render(dxf_path, out_base, dpi=150):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    from ezdxf.addons.drawing.config import Configuration, BackgroundPolicy, ColorPolicy, LinePolicy

    doc = ezdxf.readfile(dxf_path)
    fig = plt.figure(figsize=(SHEET_W / 25.4, SHEET_H / 25.4))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, SHEET_W)
    ax.set_ylim(0, SHEET_H)
    ax.set_aspect("equal")
    ax.axis("off")
    cfg = Configuration(background_policy=BackgroundPolicy.WHITE,
                        color_policy=ColorPolicy.COLOR,
                        line_policy=LinePolicy.ACCURATE,
                        min_lineweight=0.18)
    ctx = RenderContext(doc)
    Frontend(ctx, MatplotlibBackend(ax), config=cfg).draw_layout(doc.modelspace(), finalize=False)
    ax.set_xlim(0, SHEET_W)
    ax.set_ylim(0, SHEET_H)
    fig.savefig(out_base + ".pdf", facecolor="white")
    fig.savefig(out_base + ".png", dpi=dpi, facecolor="white")
    plt.close(fig)
    return out_base + ".pdf", out_base + ".png"


# --------------------------------------------------------------------------- commands
def cmd_new(args):
    spec = load_spec(args.spec)
    doc = open_template()
    equipment = spec.get("equipment", [])
    use_sched = spec.get("schedule", True) and bool(equipment)
    area = [AREA_X0 + PAD, AREA_Y0 + PAD, AREA_X1 - PAD, AREA_Y1 - PAD]
    if use_sched:
        area[2] = AREA_X1 - SCHEDULE_W - PAD

    # first pass at a guessed scale to get extents (text size depends on scale)
    forced = parse_scale((spec.get("title") or {}).get("SCALE") or spec.get("scale"))
    n = forced or 100
    for _ in range(3):
        if "DWG_CONTENT" in doc.blocks:
            doc.blocks.delete_block("DWG_CONTENT", safe=False)
        blk = build_content(doc, spec, n)
        ext = model_extents(doc, blk)
        new_n = pick_scale(ext[1][0] - ext[0][0], ext[1][1] - ext[0][1],
                           area[2] - area[0], area[3] - area[1], forced)
        if new_n == n:
            break
        n = new_n
    place_content_block(doc, "DWG_CONTENT", ext, n, area)
    if use_sched:
        draw_schedule(doc, equipment, spec.get("notes", []), AREA_X1 - SCHEDULE_W + 2, AREA_Y1 - 6)
    elif spec.get("notes"):
        draw_schedule(doc, [], spec["notes"], AREA_X1 - SCHEDULE_W + 2, AREA_Y1 - 6)
    vals = fill_title_block(doc, spec.get("title"), n)
    finish(doc, args.out, vals)


def cmd_frame(args):
    spec = load_spec(args.spec)
    src = ezdxf.readfile(args.input)
    doc = open_template()
    blk = doc.blocks.new("DWG_CONTENT")
    imp = Importer(src, doc)
    ents = [e for e in src.modelspace() if e.dxftype() not in ("VIEWPORT",)]
    imp.import_entities(ents, blk)
    imp.finalize()

    # unit conversion to mm
    u = src.header.get("$INSUNITS", 4)
    factor = {0: 1, 1: 25.4, 2: 304.8, 4: 1, 5: 10, 6: 1000}.get(u, 1)
    if args.units:
        factor = {"mm": 1, "cm": 10, "m": 1000, "in": 25.4, "ft": 304.8}[args.units]
    e = bbox.extents(blk, fast=True)
    if not e.has_data:
        sys.exit("Input DXF modelspace is empty.")
    ext = ((e.extmin.x * factor, e.extmin.y * factor), (e.extmax.x * factor, e.extmax.y * factor))
    area = [AREA_X0 + PAD, AREA_Y0 + PAD, AREA_X1 - PAD, AREA_Y1 - PAD]
    forced = parse_scale((spec.get("title") or {}).get("SCALE") or spec.get("scale"))
    n = pick_scale(ext[1][0] - ext[0][0], ext[1][1] - ext[0][1], area[2] - area[0], area[3] - area[1], forced)
    # insert with combined unit factor
    (x0, y0), (x1, y1) = ext
    s = factor / n
    cx_m, cy_m = (e.extmin.x + e.extmax.x) / 2, (e.extmin.y + e.extmax.y) / 2
    cx_p, cy_p = (area[0] + area[2]) / 2, (area[1] + area[3]) / 2
    doc.modelspace().add_blockref("DWG_CONTENT", (cx_p - cx_m * s, cy_p - cy_m * s),
                                  dxfattribs={"xscale": s, "yscale": s, "layer": "0"})
    if spec.get("notes"):
        print("note: notes are not added in frame mode, to avoid covering the drawing", file=sys.stderr)
    vals = fill_title_block(doc, spec.get("title"), n)
    finish(doc, args.out, vals)


def finish(doc, out_base, vals):
    os.makedirs(os.path.dirname(os.path.abspath(out_base)), exist_ok=True)
    doc.header["$INSUNITS"] = 4
    doc.saveas(out_base + ".dxf")
    pdf, png = render(out_base + ".dxf", out_base)
    print(json.dumps({"dxf": out_base + ".dxf", "pdf": pdf, "png": png, "title_block": vals}, indent=1, ensure_ascii=False))


def cmd_render(args):
    pdf, png = render(args.dxf, args.out)
    print(json.dumps({"pdf": pdf, "png": png}))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("new"); a.add_argument("--spec", required=True); a.add_argument("--out", required=True)
    b = sub.add_parser("frame"); b.add_argument("--input", required=True); b.add_argument("--spec"); b.add_argument("--out", required=True)
    b.add_argument("--units", choices=["mm", "cm", "m", "in", "ft"], help="override the input DXF's units")
    c = sub.add_parser("render"); c.add_argument("--dxf", required=True); c.add_argument("--out", required=True)
    args = p.parse_args()
    {"new": cmd_new, "frame": cmd_frame, "render": cmd_render}[args.cmd](args)


if __name__ == "__main__":
    main()
