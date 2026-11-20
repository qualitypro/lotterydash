# Sprint 02 — Scan-space coordinate mapping

This first mapping tool is an **interactive manual annotation utility**, not an automatic bubble detector or physical calibration engine.

## Workflow

1. Launch LotteryDash and select **Open Scan Mapper**.
2. Open the uploaded flatbed PNG, or a local copy of the same scan.
3. Enter a stable field ID such as `A.digit1.7`.
4. Click the **center** of that bubble in the displayed full-resolution scan.
5. Repeat for additional fields; save the mapping to JSON.
6. Load the same scan before reloading saved marks.

Coordinates are normalized to the image dimensions, independent of window size. The PNG was inspected at 1487 × 2047 pixels and contained **no embedded DPI metadata**. The scanner's stated 600 DPI setting alone cannot establish the exported image's physical scale.

## Limitations

- Manual point mapping; no automated detection or OCR.
- No physical dimensions, scanner DPI, or printer offset assumptions.
- No CUPS printing or official playslip output.
- The mapping JSON is a working annotation and is not certified for lottery terminal scanning.
- Use only laser-compatible plain paper for future alignment tests until media compatibility is confirmed.

## Next increments

Add image fingerprint/size validation on mapping reload, field naming assistance, zoom, image rotation, registration-mark detection, calibrated dimensions and printer-specific plain-paper test output.
