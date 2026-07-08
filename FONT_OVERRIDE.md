# KOTOR Chinese Font Override

Generated from Noto Sans CJK SC Regular for SWKOTOR_CN.

Install by copying the contents of `Override/` into the game's `Override` folder.
Keep `dialog.tlk` in the game root directory.

The generator renders glyphs from `translated_dialog.tlk.txt` into both Unicode
codepoint slots and CP936 two-byte slots. This is intentional for KOTOR Chinese
runtime compatibility testing.

Regenerate with:

```sh
uv run --with pillow python tools/generate_kotor_fonts.py \
  --font /path/to/NotoSansCJKsc-Regular.otf \
  --out Override \
  translated_dialog.tlk.txt
```
