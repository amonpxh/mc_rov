#!/usr/bin/env bash
set -euo pipefail

# wkhtmltopdf 0.12.6 ignora @font-face en el asset de Odoo. Fontconfig debe
# conocer esta familia para que el PDF incorpore Noto Sans SemiBold.
MODULE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FONT_DIR=/usr/local/share/fonts/truetype/mc_rov
install -d -m 0755 "$FONT_DIR"
install -m 0644 "$MODULE_DIR/static/src/fonts/NotoSans-SemiBold.ttf" "$FONT_DIR/NotoSans-SemiBold.ttf"
fc-cache -f "$FONT_DIR"
fc-match -f '%{family}|%{style}\n' 'Noto Sans:style=SemiBold'
