# FEN/REV Final Geometry Implementation Plan

> **For agentic workers:** Execute this plan in order; preserve the approved report structure and functional behavior.

**Goal:** Match the shared rounded blue header to the measured 60–60.5 pt reference and align REV signatures/footer with the real FEN lower band.

**Architecture:** Change only the shared QWeb header geometry and REV check-description rhythm plus the naturally flowing close. Keep metadata, report structure, font roles, footer content, and business logic unchanged. Validate the four REV content states and real FEN directly from generated STAGING PDFs.

**Tech Stack:** Odoo 19 QWeb, Python unittest, wkhtmltopdf, PyMuPDF.

**Spec:** User request `0dad53d5-2d3c-4246-bc55-c4949c29756d/Pasted text.txt`.

## Global Constraints

- Do not change functional logic or persisted data.
- Keep FEN and REV on one Letter page; no production deployment.
- Header blue target is approximately 60–60.5 pt, with current white margins, blue, radius, widths, and content sizes preserved.
- Keep REV closing cards natural-height and stable in empty/full/findings-only/observations-only cases.
- Align REV signature/footer axes to real FEN within 2–3 pt.

## Review Focus

- Shared header must grow in both reports without changing logo/title/badge sizes or horizontal alignment.
- Longer REV checks must remain within the three-column card and avoid overlap/clipping.
- REV lower flow must move signatures and footer together, not position the footer independently.
- All four closing variants must remain one-page Letter with full footer and no draft watermark.

### Task 1: Pin the new geometry in tests

**Files:** `tests/test_report_ficha.py`, `tests/test_ficha_equipo_nuevo.py`.

- [ ] Assert shared header CSS is 79 pt high with unchanged margins and content sizes, and logo/title/badge are vertically centered by a 3 pt CSS offset.
- [ ] Assert REV check details use the approved modest font increase and larger line-height, with consistent group and row rhythm.
- [ ] Run the focused STAGING tests against the installed version and confirm the new geometry assertions fail before installing QWeb changes.

### Task 2: Apply the shared header and REV rhythm changes

**Files:** `reports/ficha_report.xml`.

- [ ] Change header height/min-height from 73 pt to 79 pt; shift logo, title, and badge top offsets by 3 pt while preserving their sizes, horizontal positions, margins, color, and radius.
- [ ] Increase only REV check-description line-height/font-size and modest vertical group, title-detail, and row gaps; retain three columns, titles, scores, and semantics.
- [ ] Leave the closing card minimum size and content logic intact so all later sections move through document flow.

### Task 3: Verify real PDFs and update work status

**Files:** `.tmp/staging-rev-geometry.ps1`, `.tmp/verify_rev_geometry.py`, `docs/pendientes.md`.

- [ ] Upgrade STAGING and run `TestReporteFicha` plus `TestFichaEquipoNuevo`.
- [ ] Render real FEN and REV empty/full/findings-only/observations-only using rollback fixtures.
- [ ] Measure blue bounds, FEN footer/signature targets, page counts, outside-page text, and REV lower axes from PDFs; create header/checks/closing crops.
- [ ] Require one-page Letter output, no clipping/overflow, stable REV lower geometry across all four variants, and REV signatures/footer within 2–3 pt of FEN.
- [ ] Record implementation, test, STAGING, and artifact status in `docs/pendientes.md`.
