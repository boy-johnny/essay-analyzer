import json
import streamlit as st
import os
import re
import dotenv
import plotly.graph_objects as go
from typing import Dict, Optional, List, Union, Generator
from datetime import datetime
import base64

# Langchain 的訊息類型，用來建構多模態 Prompt
from langchain_core.messages import HumanMessage

dotenv.load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI

# --- 設定與初始化 ---

# 從環境變數讀取 API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")

# 建立 LLM 物件
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=GOOGLE_API_KEY, temperature=0.3)

# 五項指標名稱
CATEGORIES: List[str] = ["切題性", "結構與邏輯", "專業與政策理解", "批判與建議具體性", "語言與表達"]

# 初始化 session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_feedback" not in st.session_state:
    st.session_state.current_feedback = None
if "current_scores" not in st.session_state:
    st.session_state.current_scores = None
# 【修改】統一的答案狀態變數
if "answer_text" not in st.session_state:
    st.session_state.answer_text = ""

# --- 核心功能函式 (大部分不變) ---

def get_text_from_image_by_gemini(image_bytes: bytes) -> str:
    """使用 Gemini 1.5 Pro 從圖片中提取文字"""
    try:
        human_message = HumanMessage(
            content=[
                {"type": "text", "text": "請辨識並抽取出這張圖片中的所有手寫或印刷文字，並將它們以純文字格式回傳。不要添加任何額外的說明或標題。"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_bytes.decode('utf-8')}"}},
            ]
        )
        response = llm.invoke([human_message])
        return response.content
    except Exception as e:
        st.error(f"圖片辨識失敗：{e}")
        return "圖片辨識時發生錯誤。"

def save_chat_history(question: str, answer: str, feedback: str, scores: Optional[Dict[str, int]] = None) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chat_record = {"timestamp": timestamp, "question": question, "answer": answer, "feedback": feedback, "scores": scores}
    st.session_state.chat_history.append(chat_record)
    st.session_state.current_feedback = None
    st.session_state.current_scores = None
    st.session_state.answer_text = ""

def display_scores(scores: Dict[str, int]) -> None:
    st.write("### 詳細評分")
    total_score = sum(scores.values())
    st.write(f"### 總分: {total_score} / 25 分")
    for category, score in scores.items():
        st.write(f"**{category}**: {score} / 5 分")

def get_feedback_stream(question: str, answer: str) -> Generator[str, None, None]:
    # ... (此函式內容不變) ...
    try:
        prompt = f"""
        你是一位嚴謹、專業且善於教學的法學專家，專長於行政法與社會福利政策。
        請根據下列五個指標，針對學生的申論題答案進行專業評分與評論，每個指標滿分5分，總分25分。
        請僅根據提供的知識庫內容進行批改與回饋，並給予具體的改進建議。

        - 切題性：答案是否緊扣題目要求，內容有無偏離主題。
        - 結構與邏輯：答案是否有清晰的結構，論述是否有邏輯性與層次。
        - 專業與政策理解：對行政法與社會福利政策的專業知識掌握與應用程度。
        - 批判與建議具體性：是否能提出具體、深入的批判與建議。
        - 語言與表達：語言是否精確、流暢，表達是否清楚。

        請依下列格式回覆：
        1. 五項指標分數（每項5分，並簡要說明評分理由）
        2. 總分
        3. 專業回饋（針對答案優缺點給予具體評論）
        4. 改進建議（明確指出如何提升答案品質）
        5. 參考改進後的範例答案（根據知識庫內容重寫更佳答案）

        題目：{question}
        用戶回答：{answer}

        請將五項指標分數以 JSON 格式回傳，例如：
        {{
        "切題性": 4,
        "結構與邏輯": 3,
        "專業與政策理解": 5,
        "批判與建議具體性": 4,
        "語言與表達": 2
        }}
        """
        for chunk in llm.stream(prompt):
            yield chunk.content
    except Exception as e:
        st.error(f"獲取回饋時發生錯誤: {str(e)}")
        yield f"錯誤: {str(e)}"

def extract_scores_from_json(feedback: str) -> Optional[Dict[str, int]]:
    # ... (此函式內容不變) ...
    try:
        match = re.search(r"\{[\s\S]*?\}", feedback)
        if match:
            scores_dict = json.loads(match.group())
            return scores_dict
    except Exception as e:
        st.error(f"解析分數 JSON 失敗: {e}")
    return None

def create_radar_chart(scores: List[int], categories: List[str]) -> go.Figure:
    # ... (此函式內容不變) ...
    scores = scores + scores[:1]
    categories = categories + categories[:1]
    fig = go.Figure(
        data=[go.Scatterpolar(r=scores, theta=categories, fill="toself", name="分數")],
        layout=go.Layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False, margin=dict(l=30, r=30, t=30, b=30))
    )
    return fig

def display_chat_history() -> None:
    # ... (此函式內容不變) ...
    st.sidebar.subheader("歷史對話記錄 📚")
    if not st.session_state.chat_history:
        st.sidebar.info("還沒有任何對話記錄")
        st.sidebar.warning("注意：對話記錄僅在當前瀏覽器會話中保存")
        return
    st.sidebar.warning("注意：對話記錄僅在當前瀏覽器會話中保存")
    for idx, chat in enumerate(reversed(st.session_state.chat_history)):
        with st.sidebar.expander(f"對話 {len(st.session_state.chat_history) - idx} - {chat['timestamp']}", expanded=False):
            st.write("**題目：**", chat["question"])
            st.write("**答案：**", chat["answer"])
            if chat["scores"]:
                st.write("**評分：**")
                total_score = sum(chat["scores"].values())
                st.write(f"**總分**: {total_score}/25 分")
                for category, score in chat["scores"].items():
                    st.write(f"{category}: {score}/5 分")
            st.write("**回饋：**")
            clean_feedback = re.sub(r"\{.*?\}", "", chat["feedback"], flags=re.DOTALL).strip()
            st.write(clean_feedback)

# --- 主程式 UI 與邏輯 ---

def main() -> None:
    st.set_page_config(page_title="AI 申論題批改老師", page_icon="📝", layout="wide")
    display_chat_history()

    st.title("你的 AI 申論題批改老師 📝")
    st.write("我會根據你的答案給你專業的批改意見，並給你具體的改進建議。")

    col1, col2 = st.columns([2, 1])

    with col1:
        question = st.text_area("請輸入申論題題目：", height=100)
        
        # --- 【重大修改】使用 st.tabs 整合三種輸入方式 ---
        st.subheader("請選擇答案輸入方式：")
        tab1, tab2 = st.tabs(["📷 相機拍照 (手機推薦)", "📁 上傳檔案 (電腦推薦)"])

        with tab1:
            picture = st.camera_input("點擊按鈕開啟相機", help="請確保光線充足，並讓文字盡量清晰、置中")
            if picture:
                with st.spinner("照片文字辨識中..."):
                    image_bytes = picture.getvalue()
                    base64_image = base64.b64encode(image_bytes)
                    st.session_state.answer_text = get_text_from_image_by_gemini(base64_image)
                    st.rerun()

        with tab2:
            uploaded_file = st.file_uploader("選擇圖片或 PDF 檔案", type=['png', 'jpg', 'jpeg'])
            if uploaded_file:
                with st.spinner("檔案文字辨識中..."):
                    image_bytes = uploaded_file.getvalue()
                    base64_image = base64.b64encode(image_bytes)
                    st.session_state.answer_text = get_text_from_image_by_gemini(base64_image)
                    st.rerun()

        # --- 中央統一的答案輸入框 (也是手動輸入區) ---
        st.subheader("請在此確認或手動輸入您的最終答案：")
        answer = st.text_area(
            "答案內容",
            value=st.session_state.answer_text,
            height=250,
            key="answer_input_area"
        )
        # 將使用者在文字區的任何修改即時同步回 state
        st.session_state.answer_text = answer

        # --- 批改與顯示邏輯 ---
        if st.session_state.current_feedback is None:
            if st.button("送出批改", type="primary"):
                if not question or not answer:
                    st.warning("請輸入題目與答案")
                else:
                    st.subheader("AI 批改建議")
                    with st.spinner("AI 批改中..."):
                        full_feedback = st.write_stream(get_feedback_stream(question, answer))
                    st.session_state.current_feedback = full_feedback
                    st.session_state.current_scores = extract_scores_from_json(full_feedback)
                    st.rerun()
        else:
            st.subheader("AI 批改建議")
            clean_feedback = re.sub(r"\{.*?\}", "", st.session_state.current_feedback, flags=re.DOTALL).strip()
            st.write(clean_feedback)

            col_save, col_retry = st.columns(2)
            with col_save:
                if st.button("保存紀錄", type="primary"):
                    save_chat_history(question, answer, st.session_state.current_feedback, st.session_state.current_scores)
                    st.rerun()
            with col_retry:
                if st.button("重新批改"):
                    st.session_state.current_feedback = None
                    st.session_state.current_scores = None
                    st.session_state.answer_text = ""
                    st.rerun()

    with col2:
        if st.session_state.current_scores:
            st.subheader("評分雷達圖")
            fig = create_radar_chart(list(st.session_state.current_scores.values()), list(st.session_state.current_scores.keys()))
            st.plotly_chart(fig, use_container_width=True)
            display_scores(st.session_state.current_scores)

if __name__ == "__main__":
    main()