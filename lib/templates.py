"""內建 Skill 範本 — 讓新手不用從空白開始"""
from __future__ import annotations

SKILL_TEMPLATES = [
    {
        "id": "hello-world",
        "icon": "👋",
        "title": "打招呼（最小範例）",
        "description_for_user": "最小可用範例，教 Claude 怎麼回應一個 /xxx 指令",
        "name": "hello-world",
        "description": "用熱情的方式跟使用者打招呼",
        "body": """# 打招呼

當使用者呼叫 `/hello-world` 時，請你：

1. 用繁體中文熱情地跟使用者打招呼
2. 介紹自己是 Claude
3. 問使用者今天想做什麼

回覆要簡短、友善、有 emoji。
""",
    },
    {
        "id": "code-review",
        "icon": "🔍",
        "title": "程式碼審查",
        "description_for_user": "對目前修改的程式碼做一次完整審查",
        "name": "code-review",
        "description": "對未提交或最近修改的程式碼進行品質審查",
        "body": """# 程式碼審查

請對使用者目前修改的程式碼（git diff）進行以下審查：

## 檢查項目
1. **正確性**：邏輯有沒有錯？邊界條件處理了嗎？
2. **可讀性**：命名清楚嗎？函式有沒有過長？
3. **安全性**：有沒有 SQL 注入、XSS、未驗證輸入等問題？
4. **效能**：有沒有 N+1 查詢、不必要的迴圈？
5. **測試覆蓋**：有沒有對應的測試？

## 回報格式
- 🔴 **必須修正**：會造成 bug 或安全漏洞
- 🟡 **建議改進**：能讓程式碼更好讀
- 🟢 **做得好**：值得保留的優點

每一項要附上**檔案:行號**，這樣我才能直接跳過去。
""",
    },
    {
        "id": "daily-summary",
        "icon": "📝",
        "title": "今日工作摘要",
        "description_for_user": "整理今天的 git 提交、修改檔案、做了什麼",
        "name": "daily-summary",
        "description": "整理當天的開發進度，產出可貼到日報的摘要",
        "body": """# 今日工作摘要

請幫我整理今天的開發進度：

1. 跑 `git log --since="6am" --oneline` 看今天的提交
2. 跑 `git diff --stat HEAD@{6am}` 看修改了哪些檔案
3. 根據 commit message 與檔案內容，整理成一份**日報摘要**

## 摘要格式

```markdown
## 今日工作摘要（YYYY-MM-DD）

### ✅ 完成
- xxx

### 🔄 進行中
- xxx

### 📊 統計
- 提交次數：N
- 修改檔案：N
- 新增行數：+N / 刪除行數：-N
```

用繁體中文，簡潔有條理。
""",
    },
]


def get_template(template_id: str) -> dict | None:
    for t in SKILL_TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
