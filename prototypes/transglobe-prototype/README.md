# 全球藍設計套用校準原型

決策票：[iysl-skills #17](https://github.com/isaac-ys-lin/iysl-skills/issues/17)。這是可丟棄的決策素材，未建立或安裝正式 skill。資料全部為示意。

從 `prototype.html` 查看三種閱讀情境及缺資料例外；頁面含 Office、SVG 及資料下載。`source-notes.md` 記錄規範來源，`validation.md` 區分已測與未測項目。

從 repository 根目錄啟動：

```sh
python3 prototypes/transglobe-prototype/build_demo.py
python3 -m http.server 8765 --bind 127.0.0.1 --directory prototypes/transglobe-prototype
```

瀏覽 `http://127.0.0.1:8765/prototype.html`。可用 `?variant=deck`、`document`、`chart`、`missing` 直達情境。

Office 使用 Codex 已安裝的 Artifact Tool 與 python-docx。先以 `load_workspace_dependencies` 取得 runtime 路徑，在 `.build/node_modules` 建立指向該 runtime node_modules 的 symlink，再從 repository 根目錄執行：

```sh
export RUNTIME_NODE_MODULES="/Users/isaacyslin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules"
export RUNTIME_PYTHON="/Users/isaacyslin/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3"
mkdir -p prototypes/transglobe-prototype/.build
ln -sfn "$RUNTIME_NODE_MODULES" prototypes/transglobe-prototype/.build/node_modules
/Users/isaacyslin/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node prototypes/transglobe-prototype/build_office_samples.mjs
python3 prototypes/transglobe-prototype/check_office_samples.py
```

本機路徑與 Presentations skill 版本固定在建置腳本，換環境需更新該路徑。`OFFICE_PART=pptx|docx|xlsx` 可只重建受影響格式。輸出覆寫僅限此原型目錄；請先關閉檔案，勿把使用者原稿放入此目錄。重新建置後需重做受影響的原生畫面檢查，並更新驗證紀錄。

`assets/chart-before.png` 是缺資料情境的固定點陣測試素材，保留原樣。它不是 SVG 優先交付物，也不隨 Data 工作表自動改變。
