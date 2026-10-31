# 《美國的誕生》A 版正式封面

畫布為 1920 × 2560（3:4）。正式封面由原始歷史地圖、向量旗幟與文字排版組成，沒有使用 AI 模擬圖的像素。

## 可編輯原稿

- 專案根目錄的 `cover.svg`：分為紙色、地圖、旗幟、文字四個圖層；地圖與本書所需的字型子集均已內嵌。
- `cover-outlined.svg`：將文字轉為向量路徑的發行用版本，顯示時不依賴外部字型。PNG/JPEG 由此檔直接渲染。
- `fonts/NotoSerifTC-VF.ttf`：完整的 Noto Serif TC 字型。若要把書名改成目前字型子集以外的文字，請使用此完整字型並重建母稿。
- `fonts/OFL.txt`：字型的 SIL Open Font License。

書名使用字重 900，作者使用字重 600。十三顆星分成 3、2、3、2、3 五列，每顆都是獨立、完整可見的向量物件。下方保留 A 版的旗紋裁切構圖：原始向量圖層有十三條紅白條紋，封面左側裁切範圍顯示其中五條。

地圖使用 `../cover-proposals/references/map-1783.jpg`（5260 × 4740），由 William Darton、William Guthrie 製作，來源為 Wikimedia Commons／Library of Congress 74696218，來源頁標示為 public domain。母稿原封不動嵌入該 JPEG；僅作等比例縮放、位置調整與邊緣遮罩，未重畫或改寫地名。地圖圖框和右下角圖名框以構圖遮罩淡出。

來源：

- https://commons.wikimedia.org/wiki/File:A_map_of_the_United_States_of_America_agreeable_to_the_peace_of_1783._LOC_74696218.jpg
- https://www.loc.gov/item/74696218/
- https://commons.wikimedia.org/wiki/File:Flag_of_the_United_States_(1777%E2%80%931795).svg
- https://github.com/google/fonts/tree/main/ofl/notoseriftc

## 重建流程

工具需求：macOS 的 Swift/CoreText、Python 的 `fonttools[woff]` 與 Pillow，以及 Node.js 的 `@resvg/resvg-js`。

從專案根目錄執行：

```sh
swift design/cover-final/tools/glyphs.swift design/cover-final/fonts/NotoSerifTC-VF.ttf design/cover-final/glyphs.json
python3 design/cover-final/tools/build_cover.py
node design/cover-final/tools/render_cover.cjs
python3 design/cover-final/tools/export_and_package.py
```

先依專案根目錄 README 安裝 Pandoc 3.13。`SVG_RENDER_MODULE` 可指定 `@resvg/resvg-js` 的安裝路徑。版面座標、遮罩與字級都集中在 `tools/build_cover.py`，可重新產生可編輯與轉曲兩份 SVG。PNG/JPEG 使用 sRGB；JPEG 品質為 92，關閉色度子取樣以維持文字邊緣品質。

`export_and_package.py` 會更新 `assets/cover.jpg`，再呼叫 `scripts/build.py`，從 Markdown 產生 `output/usa-birth.epub`。封面圖像驗證寫入 `output/cover-validation-report.json`，書籍內容與連結驗證寫入 `output/validation-report.json`。需要完整 EPUBCheck 時，另執行 `./package.sh --epubcheck`。EPUB 引用 JPEG，並保留可等比例顯示的封面頁。

先前版本備份為 `original-cover.svg`、`original-cover-600x800.png`；提案模擬圖仍保存在 `../cover-proposals/`。
