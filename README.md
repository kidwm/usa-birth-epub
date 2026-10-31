# 美國的誕生

本書《美國的誕生》結集作者藍弋丰於想想論壇的[專欄連載文章](http://www.thinkingtaiwan.com/tags/2105)。原始材料以 [CC BY-NC-ND 3.0 TW](https://creativecommons.org/licenses/by-nc-nd/3.0/tw/) 授權釋出，由 @kidwm 為 epub.tw 編排。

原稿以 Markdown 維護，使用固定版本的 Pandoc 產生 EPUB 3。正文維持原文，目錄從章首標題自動產生。

## 建置

需要 Python 3.9+ 與 Pandoc **3.13**。以下指令將官方、校驗過 SHA-256 的 Pandoc 放進專案的 `.tools/`，支援 macOS 與 Linux 的 Intel／ARM；不會安裝至系統目錄。

```sh
python3 scripts/setup_tools.py
./package.sh
```

產物為 `output/usa-birth.epub`。可指定其他檔名：

```sh
./package.sh output/my-book.epub
```

已安裝相同版本的 Pandoc 時，也可以使用 PATH 中的執行檔，或設定 `PANDOC=/path/to/pandoc`。工具下載完成後，建置不需要網路。

建置會核對段落文字、圖說、圖片原始位元組與替代文字、章節順序、註腳、目錄標題，以及所有內部檔案與錨點連結。結果寫入 `output/validation-report.json`；通過檢查後才更新指定的發行檔。

完整格式驗證另需 Java 11+ 與 EPUBCheck 5.4.0：

```sh
python3 scripts/setup_tools.py --epubcheck
./package.sh --epubcheck
```

可用 `JAVA=/path/to/java`、`EPUBCHECK_JAR=/path/to/epubcheck.jar` 指定位置。EPUBCheck 的警告也會使建置失敗，完整紀錄在 `build/epubcheck.log`。

`SOURCE_DATE_EPOCH` 控制 EPUB 的時間戳，預設採用最近一次 Git commit 時間；相同原稿、工具版本與時間戳會產生相同的 EPUB。發行時可明確指定該環境變數。

## 維護原稿

- `content/`：50 章、6 個部首頁、出版資訊與後記，共 58 份 Markdown。
- `book.yaml`：書名、作者、語言、授權、封面與完整閱讀順序，也是 Pandoc 的 defaults 設定。
- `assets/images/`：內文圖片；`assets/cover.jpg` 是 EPUB 使用的封面。
- `styles/book.css`：中文橫排、章首、部首頁、導言、圖說、註腳與目錄樣式。
- `styles/epub.html`：封面與書名頁共用的 XHTML 外框。
- `filters/book.lua`：從穩定的章節 ID 產生顯示編號與 EPUB 語意。
- `scripts/build.py`：執行 Pandoc、補上各 XHTML 的純文字頁名、驗證並輸出產物。

每個部首頁使用一級標題與 `part1` 等 ID；章節使用二級標題與 `chapter01` 等 ID。後記是一級標題 `afterword`，出版資訊使用 `colophon`。新增檔案時，請在 `book.yaml` 的 `input-files` 中指定位置；章號由 ID 產生，目錄文字取自標題。

```markdown
## 美國為什麼叫「美」國 {#chapter01}

正文段落，每個自然段一行，段落之間空一行。

<!-- https://commons.wikimedia.org/wiki/File:Amerigo_Vespucci.jpg -->

![亞美利哥像](<../assets/images/Amerigo_Vespucci.jpg>)

文字可以帶註腳[^chapter01-note]。

[^chapter01-note]: 註腳內容。
```

圖片單獨成段時，方括號中的文字會成為圖說。替代文字需要與圖說不同時，在圖片後加上 `{alt="較短的圖片描述"}`。來源 URL 保留在圖片前的 HTML 註解中。檔名外層的 `<…>` 可容納括號與空白。

導言使用 `::: {.lead}` 與 `:::` 包住 Markdown 段落；第 34 章歌詞使用同樣方式的 `.verse` 區塊。註腳 ID 加上章節名稱，避免不同章節之間重複。轉換停用 smart typography，保留原文標點。

## 預覽與驗證

每次建置都會將實際 EPUB 解開至 `build/epub/`：

```sh
python3 -m http.server 8765 --bind 127.0.0.1 --directory build/epub
```

開啟 `http://127.0.0.1:8765/EPUB/nav.xhtml`，即可從實際目錄進入各章。這是流式瀏覽器預覽；分頁、字型與深色模式仍應在目標閱讀器中確認。內頁不嵌入完整中文字型，讓閱讀器選擇字型、字級與底色。

建置後可以執行驗證器的回歸測試：

```sh
python3 -m unittest discover -s tests
```

`build/`、`output/`、`.tools/` 都是可重建的本機產物，不納入 Git。舊 XHTML 已由 Markdown 取代，歷史版本保留於 Git。

## 封面

`cover.svg` 是 A 版正式封面的可編輯母稿，包含原始 1783 年古地圖、十三顆向量星星、旗紋與獨立文字圖層。畫布為 1920 × 2560（3:4），地圖與目前書名所需字型子集均已內嵌。

`design/cover-final/cover-outlined.svg` 是文字轉曲版本，供跨環境顯示與圖片輸出使用。封面匯出工具會更新 `assets/cover.jpg`，再呼叫同一套 Markdown 建置流程產生 EPUB。正式 JPEG、PNG、SVG 與電子書放在 `output/`。

素材來源、字型授權與封面重建步驟見 [封面製作說明](design/cover-final/README.md)。
