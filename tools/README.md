# 工具说明

本目录只放构建工具。生成产物写入 `dist/`，不提交到仓库。

## 安装依赖

```sh
uv sync
```

## 生成 KOTOR 字体

源字体：

```text
fonts/NotoSansCJKsc-Regular.otf
```

命令：

```sh
uv run python tools/generate_kotor_fonts.py \
  --font fonts/NotoSansCJKsc-Regular.otf \
  --out fonts \
  translation/translated_dialog.tlk.txt
```

输出：

```text
fonts/fnt_*.tga
fonts/fnt_*.txi
```

## 生成 dialog.tlk

```sh
uv run python tools/build_dialog_tlk.py \
  translation/translated_dialog.tlk.txt \
  dist/SWKOTOR_CN/dialog.tlk
```

默认参数：

- 语言 ID：`130`
- 文本编码：`cp936`
- TLK 格式：`TLK V3.0`

## TLK 工具说明

`build_dialog_tlk.py` 是本项目的独立实现，只写入 `TLK V3.0` 所需的 header、entry table 和 string data；没有引用或复制第三方 TLK 编辑器代码。

TLK 是 BioWare 游戏使用的文件格式，不是“开源许可的软件代码”。本仓库不包含官方 `dialog.tlk` 或其他原始游戏资产。

格式参考：

- [NWN Wiki: TLK](https://nwn.wiki/display/NWN1/TLK)
- [xoreos-docs: TalkTable_Format.pdf](https://github.com/xoreos/xoreos-docs/blob/master/specs/bioware/TalkTable_Format.pdf)
