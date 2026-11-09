# 專案執行指南（How to Run）

本文件說明如何在不同作業系統與環境中安裝依賴套件並啟動「台灣餐廳資料探索」Dash 應用程式。

---

## 1. 環境需求

- **Python 版本**：建議使用 Python 3.10 或以上版本
- **相依套件**（定義於 `requirements.txt`）：
  - `dash>=4.0,<5.0`
  - `pandas>=2.0,<3.0`
  - `plotly>=7.0,<8.0`

---

## 2. 快速啟動步驟

### 方式 A：使用標準 `venv` 與 `pip`

#### Windows（PowerShell）
```powershell
# 1. 在專案根目錄建立虛擬環境
python -m venv .venv

# 2. 啟用虛擬環境
.\.venv\Scripts\Activate.ps1

# 3. 安裝所需套件
pip install -r requirements.txt

# 4. 啟動應用程式
python app.py
```

#### macOS / Linux（Bash / Zsh）
```bash
# 1. 在專案根目錄建立虛擬環境
python3 -m venv .venv

# 2. 啟用虛擬環境
source .venv/bin/activate

# 3. 安裝所需套件
pip install -r requirements.txt

# 4. 啟動應用程式
python app.py
```

---

### 方式 B：使用 `uv`（高速套件管理工具）

若系統已安裝 [`uv`](https://docs.astral.sh/uv/)，可透過以下指令快速建立環境並啟動：

```bash
# 1. 建立 .venv 虛擬環境
uv venv .venv

# 2. 安裝 requirements.txt 套件
uv pip install -r requirements.txt

# 3. 直接使用虛擬環境中的 Python 啟動
.venv/bin/python app.py
```
> Windows 環境下步驟 3 請改用：`.\.venv\Scripts\python app.py`

---

## 3. 開啟應用程式

啟動成功後，終端機會顯示類似以下訊息：

```text
Dash is running on http://127.0.0.1:8050/
```

- **本機開發環境**：在瀏覽器開啟終端機顯示的網址（預設為 `http://127.0.0.1:8050`）。
- **雲端／遠端工作區**：請透過平台提供的 **Preview（預覽視窗）** 或連接埠轉發（Port Forwarding `8050`）開啟頁面。

---

## 4. 部署與 WSGI 入口

`app.py` 已暴露 Flask 伺服器物件 `server`（即 `server = app.server`），若使用 Gunicorn 等 WSGI 伺服器部署，可執行：

```bash
gunicorn app:server --bind 0.0.0.0:8050
```

---

## 5. 常見問題排除

- **`ModuleNotFoundError: No module named 'dash'`**
  - 原因：尚未安裝相依套件，或目前執行的 `python` 並非虛擬環境中的直譯器。
  - 解法：請確認已執行 `pip install -r requirements.txt`，或直接指定虛擬環境路徑執行（例如 `.venv/bin/python app.py` 或 `.\.venv\Scripts\python app.py`）。
- **資料檔案讀取錯誤**
  - 請確認在專案根目錄（包含 `app.py` 與 `datasets/` 資料夾的目錄）下執行啟動指令，並確認 `datasets/RestaurantList.json` 與 `datasets/RestaurantServiceTimeList.json` 皆存在。
