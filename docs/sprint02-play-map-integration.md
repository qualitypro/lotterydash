# Sprint 02 — Play-to-map integration

The main planner now offers **Preview plays on scanned slip**. It loads local `images/pick3-playslip.png` and `maps/pick3-mapping.json`, then highlights recognized saved bubble coordinates in red. Missing field names are reported rather than guessed.

**Important:** The saved mapping uses free-form field names. Preview recognizes the following convention (for panel A; B–E analogous):

- `A.digit1.0` through `A.digit1.9`: first digit column
- `A.digit2.0` through `A.digit2.9`: second digit column
- `A.digit3.0` through `A.digit3.9`: third digit column
- `A.straight`, `A.box`, `A.straight_box`, `A.combo`, `A.front_pair`, `A.back_pair`
- `A.amount.1.00` or `A.amount.0.50`
- `A.midday` or `A.evening`
- `A.fireball` if enabled in the play model

For example, play 007 Straight $1 Evening requires `A.digit1.0`, `A.digit2.0`, `A.digit3.7`, `A.straight`, `A.amount.1.00`, and `A.evening`.

The actual saved map may use different labels. If so, the preview reports missing coordinates. Do **not** overwrite the existing map: use the mapper to add aliases or a future import normalization feature after inspecting your JSON.

**Not implemented:** automatic mapping, interactive play selection by clicking the scanned image, physical printer calibration, and official-slip printing. The preview is visual only and is not guaranteed to match the slip's actual bubble conventions.
