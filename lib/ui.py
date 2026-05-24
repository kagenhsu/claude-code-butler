"""共用 UI 元件：CSS + 中文化"""
from pathlib import Path

_CSS_PATH = Path(__file__).parent.parent / "assets" / "style.css"

TRANSLATE_JS = """<script>
const _t = {
    'Rerun': '重新執行', 'Settings': '設定', 'Print': '列印',
    'Record a screencast': '錄製畫面', 'Developer options': '開發者選項',
    'Clear cache': '清除快取', 'Deploy': '部署',
    'Browse files': '瀏覽檔案', 'Drag and drop files here': '拖放檔案到這裡',
    'Limit 200MB per file': '每個檔案最大 200MB',
    'Delete': '刪除', 'Running...': '執行中...',
    'Made with Streamlit': '由 Streamlit 驅動',
};
function _tr(){const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);while(w.nextNode()){const n=w.currentNode;for(const[e,z]of Object.entries(_t)){if(n.textContent.trim()===e)n.textContent=z;}}}
new MutationObserver(()=>setTimeout(_tr,100)).observe(document.body,{childList:true,subtree:true});
setTimeout(_tr,500);
</script>"""


def inject_style(st_module) -> None:
    css = _CSS_PATH.read_text(encoding="utf-8")
    st_module.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    st_module.markdown(TRANSLATE_JS, unsafe_allow_html=True)
