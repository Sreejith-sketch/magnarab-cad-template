---
name: magnarab-cad-drawings
description: MAGNARAB standard CAD sheet (A1 or A3): draw laundry layouts, frame existing DXF/DWG drawings or re-title AutoCAD layouts in the official MAGNARAB title block, delivering DXF/DWG + PDF + PNG. Use for any MAGNARAB CAD drawing, layout, plan, title block or revision.
---

# MAGNARAB CAD drawings (A1 / A3 standard sheet)

Every MAGNARAB drawing uses one title block design: the full-width MAGNARAB "Laundry Projects" title block along the bottom of the sheet. It has a white logo panel on the left: the MAGNARAB mark in a thin green frame (charcoal marks inside), with "MAGNARAB" and "Laundry Projects" beside it in plain Arial, dark charcoal and grey, separated by a thin green line. To its right, then Project / Client / Drawing title on the top row and Drawing no., Rev., Scale, Date, Drawn by, Checked by, Approved by, Sheet and Status on the bottom row. It comes in two sizes made from the same design:

| Sheet | Paper | Border | Block name | Title block size |
|---|---|---|---|---|
| A1 | 841 × 594 mm | 15 mm | `MAGNARAB_LAUNDRY_PROJECTS_TITLEBLOCK_A1` | 811 × 55 mm |
| A3 | 420 × 297 mm | 10 mm | `MAGNARAB_LAUNDRY_PROJECTS_TITLEBLOCK_A3` | 400 × 27.1 mm |

A3 is the A1 block scaled uniformly. Both are common. Use A3 unless the brief, the scale or the drawing size calls for A1, or Sreejith says A1.

The title block is fixed. Never redraw, restyle, recolour or rebuild it, and never use any other MAGNARAB title block, logo box or logo image. Older drawings and older skills used a small logo box on white with a linked `MAGNARAB-logo.png`. That design is retired: replace it wherever you find it. On 6 Nov 2026 Sreejith also replaced the first version of this block, which had a black logo panel and a spaced-out wordmark, with the light version above. Issued drawings keep the version they were issued with. Every new drawing or revision uses the light version: if a drawing still carries the black-panel block, redefine the block from the kit insert file (`-INSERT MAGNARAB_LAUNDRY_PROJECTS_TITLEBLOCK_A3=<kit insert file>`, insert once and delete the copy), so its attribute values are kept. The dark files are kept in `archive - dark title block (pre 6 Nov 2026)` for reference only. Only the 12 attribute values are filled. MAGNARAB is always one word, one font, one colour.

Every job returns: **editable drawing** (DXF, or DWG when working in AutoCAD), **PDF** at sheet size, and **PNG preview**.

## 1. Get the kit

```bash
git clone -q --depth 1 https://github.com/Sreejith-sketch/magnarab-cad-template.git /tmp/magnarab-cad
pip install -q --break-system-packages ezdxf matplotlib
```

On a Windows laptop, clone or download the repo into a working folder instead. If GitHub can't be reached, ask Sreejith to attach `MAGNARAB_CAD_Kit.zip`. Never draw a substitute title block.

Kit contents:
- `template/MAGNARAB_A1_Full_Width_Title_Block.dxf` and `template/MAGNARAB_A3_Full_Width_Title_Block.dxf`: full sheets (border + title block).
- `template/MAGNARAB_Title_Block_Insert.dxf` (A1) and `template/MAGNARAB_Title_Block_A3_Insert.dxf` (A3): the title block alone, inserted at 0,0, for use in AutoCAD.
- `scripts/magnarab_cad.py`: `new`, `frame` and `render`, each with `--sheet A1|A3`.
- `examples/5ton_layout_spec.json`: read this before writing your first spec.

## 2. Title block fields and house rules

| Field | Rule |
|---|---|
| PROJECT | Project / site name |
| CLIENT | Client company as on the proposal |
| DRAWING_TITLE | What the sheet shows, e.g. "Equipment Layout – Ground Floor" |
| DRAWING_NO | New drawings: `Layout NNNN` (running number). Claude can't see the register, so ask Sreejith for the number. If he isn't there to ask, write `Layout ____` and flag it. Never invent a number. When re-titling an existing drawing, keep its existing number unless told otherwise. |
| REVISION | `00` first issue, then `01`, `02`… The number stays the same across revisions. |
| SCALE | `1:N @ A3` / `1:N @ A1`. The script fills it. In AutoCAD, use the viewport scale. |
| DATE | `06 Nov 2026` style, Dubai date of issue |
| DRAWN_BY / CHECKED_BY / APPROVED_BY | Default Vaseem / Sreejith / Sreejith |
| SHEET | `1 of 1`, or `2 of 3` for sets |
| STATUS | Only **Concept**, **For Approval** or **Final**. Default Concept. |

House rules:
- Never edit the title block's geometry, fonts, colours or logo. Only fill attribute values.
- In the drawing area, use plain black/grey lines and one plain text style. No coloured fills, no extra logos.
- MAGNARAB-branded sheets only. For another company's name (Linencraft, Bubble Up, Aigel, Allure), stop and say this template is MAGNARAB-only.

## 3. New drawing from a brief (script)

Write a JSON spec (all model coordinates in real millimetres, origin at the building's bottom-left), then run:

```bash
cd /tmp && python3 -I /tmp/magnarab-cad/scripts/magnarab_cad.py new --sheet A3 --spec spec.json --out OUT/Layout_2058_Rev00
```

Spec keys: `title` (fields above), `sheet` ("A3"/"A1"), `walls` [{points, thickness, closed}], `zones` [{name, points}], `doors` [{at, width, angle, swing, label}], `equipment` [{tag, name, model, w, d, x, y, rot, kg, kw, qty, clear_front}], `labels` [{text, at, size}], `dims` [{p1, p2, offset}], `notes` [..], `schedule` true/false.

Equipment conventions:
- `x, y` is the footprint centre. `w` is the width across the machine front and `d` is the depth.
- `rot: 0` means the front (loading / operator side) faces down (−y), `180` up, `90` right, `270` left. Point fronts into the working aisle, never at a wall. The short inner line marks the front.
- `clear_front` draws the dashed service clearance: about 1000 mm for washers and dryers, 1500 mm for ironers.
- Tags: W washers, D dryers, F ironers / folders, P presses, T tables, B boilers / steam, C compressors, R racks / trolleys.
- The equipment schedule (Tag, Equipment / model, Size W×D, kg, kW, Qty) and notes sit at the top right.

Use real dimensions from the brochure, the quote, or the Sales app products list (`mcp__Sales_magnarab__products`) when it's connected. Note any assumed sizes on the drawing and tell Sreejith which they are.

Layout sense: one-way flow soiled → wash → dry → finish → clean dispatch, with no crossing of soiled and clean. Keep washers on the drain / utility side, keep main aisles at least 1200 mm, and keep ironer feed sides clear.

## 4. Frame an existing DXF (script)

```bash
cd /tmp && python3 -I /tmp/magnarab-cad/scripts/magnarab_cad.py frame --sheet A3 --input their.dxf --spec title.json --out OUT/Layout_2058_Rev00
```

The script converts units to mm (`--units m` overrides), picks the scale and centres the drawing. If the input carries another border or title block, ask before removing it.

## 5. Re-title or finish a drawing in AutoCAD (DWG on Sreejith's laptop)

When the drawing lives in a DWG with paper-space layouts:
1. Never edit the original. Save a copy as the next revision first, e.g. `… Rev 10.dwg`.
2. On the layout tab, delete any old MAGNARAB title block, logo box and logo image (including the linked `MAGNARAB-logo.png`), along with any old sheet border.
3. Insert the block from the matching insert DXF (`MAGNARAB_Title_Block_A3_Insert.dxf` for A3 layouts) at the paper's lower-left border corner: (10,10) on A3 and (15,15) on A1, scale 1, rotation 0. Draw the sheet border rectangle (10,10)–(410,287) for A3 or (15,15)–(826,579) for A1 on layer `SHEET_BORDER`. The block brings its own layers (TB_*); keep them.
4. Fill the 12 attributes. Carry over the project, client, title and number from the old title block, set the new Rev and today's date, and keep Drawn / Checked / Approved per the defaults unless the old block said otherwise.
5. Make sure the viewport sits fully above the title block. If it overlaps, move or resize the viewport without changing its scale.
6. Plot to PDF at the sheet size (A3 / A1, 1:1, monochrome or as the drawing was plotted before), and export a PNG preview.
7. Check the result, then deliver the new DWG, PDF and PNG together.

## 6. Check, then deliver

Open the PNG and check:
- The drawing sits inside the drawing area, clear of the title block and the schedule, with nothing overlapping.
- Tags are readable, fronts face the aisles and clearances are dashed.
- All 12 fields are filled, the status is one of the three words and the scale is shown.
- The title block is the design described above and no old logo box remains.

Name files `Layout_NNNN_RevXX` (or keep the existing drawing's name pattern with the new Rev) and send DXF/DWG, PDF and PNG in one message, with one line on the scale and any assumptions.

## Revisions

Keep the number, bump REVISION, update DATE, and move the status from Concept → For Approval → Final as instructed. Re-use the previous spec where you have one.
