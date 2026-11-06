# MAGNARAB CAD template kit

Standard A1 drawing sheet for MAGNARAB Equipment Trading L.L.C. (Laundry Projects).
Used by the `magnarab-cad-drawings` Claude skill. It holds only the blank template and the drawing script, never client drawings.

## Contents

- `template/MAGNARAB_A1_Full_Width_Title_Block.dxf`: A1 sheet (841 × 594 mm, 15 mm border) with the title block inserted.
- `template/MAGNARAB_Title_Block_Insert.dxf`: the title block alone (block `MAGNARAB_LAUNDRY_PROJECTS_TITLEBLOCK_A1`, 811 × 55 mm) for inserting in AutoCAD.
- `template/*.pdf / *.png / *.svg`: print reference and previews.
- `scripts/magnarab_cad.py`: makes sheets (`new`, `frame`, `render`) as DXF, A1 PDF and PNG.

## Title block attributes

PROJECT, CLIENT, DRAWING_TITLE, DRAWING_NO, REVISION, SCALE, DATE, DRAWN_BY, CHECKED_BY, APPROVED_BY, SHEET, STATUS

Defaults: Drawn by Vaseem · Checked by Sreejith · Approved by Sreejith · Rev 00 · Sheet 1 of 1 · Status Concept.
Status words: Concept / For Approval / Final. Drawing numbers: `Layout NNNN`, revision `00`, `01`, …

## Use

```
pip install ezdxf matplotlib
python scripts/magnarab_cad.py new   --spec spec.json --out out/Layout_2058_Rev00
python scripts/magnarab_cad.py frame --input existing.dxf --spec spec.json --out out/Layout_2058_Rev00
python scripts/magnarab_cad.py render --dxf sheet.dxf --out out/Layout_2058_Rev00
```

The title block is never redrawn or restyled; only its attributes are filled.
