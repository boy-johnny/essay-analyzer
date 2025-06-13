import json
import streamlit as st
import os
import re
import dotenv
import plotly.graph_objects as go
from typing import Dict, Optional, List, Union, Generator
from datetime import datetime

dotenv.load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI

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

def save_chat_history(question: str, answer: str, feedback: str, scores: Optional[Dict[str, int]] = None) -> None:
    """
    保存對話歷史記錄
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chat_record = {
        "timestamp": timestamp,
        "question": question,
        "answer": answer,
        "feedback": feedback,
        "scores": scores
    }
    st.session_state.chat_history.append(chat_record)
    # 清除當前回饋，重置狀態
    st.session_state.current_feedback = None
    st.session_state.current_scores = None

def display_scores(scores: Dict[str, int]) -> None:
    """
    顯示詳細的評分結果
    """
    st.write("### 詳細評分")
    total_score = 0
    for category, score in scores.items():
        st.write(f"**{category}**: {score} / 5 分")
        total_score += score
    st.write("---")
    st.write(f"### 總分: {total_score} / 25 分")

def get_feedback_stream(question: str, answer: str) -> Generator[str, None, None]:
    """
    【新函式】
    呼叫 Gemini LLM，以串流方式回傳批改意見。
    這是一個生成器 (Generator) 函式。
    """
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
        # 使用 .stream() 方法代替 .predict()
        for chunk in llm.stream(prompt):
            yield chunk.content
    except Exception as e:
        st.error(f"獲取回饋時發生錯誤: {str(e)}")
        # 在串流中也可以拋出錯誤
        yield f"錯誤: {str(e)}"


def extract_scores_from_json(feedback: str) -> Optional[Dict[str, int]]:
    """
    從回傳的文字中提取 JSON 格式分數
    """
    try:
        match = re.search(r"\{[\s\S]*?\}", feedback)
        if match:
            scores_dict = json.loads(match.group())
            return scores_dict
    except Exception as e:
        st.error(f"解析分數 JSON 失敗: {e}")
    return None

def create_radar_chart(scores: List[int], categories: List[str]) -> go.Figure:
    """
    創建雷達圖
    """
    # 雷達圖需要首尾相連
    scores = scores + scores[:1]
    categories = categories + categories[:1]

    fig = go.Figure(
        data=[go.Scatterpolar(r=scores, theta=categories, fill="toself", name="分數")],
        layout=go.Layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=False,
            margin=dict(l=30, r=30, t=30, b=30)
        )
    )
    return fig

def display_chat_history() -> None:
    """
    在側邊欄顯示歷史對話記錄
    """
    st.sidebar.subheader("歷史對話記錄 📚")
    
    if not st.session_state.chat_history:
        st.sidebar.info("還沒有任何對話記錄")
        st.sidebar.warning("注意：對話記錄僅在當前瀏覽器會話中保存")
        return
    
    st.sidebar.warning("注意：對話記錄僅在當前瀏覽器會話中保存")
    
    for idx, chat in enumerate(reversed(st.session_state.chat_history)):
        with st.sidebar.expander(f"對話 {len(st.session_state.chat_history) - idx} - {chat['timestamp']}", expanded=False):
            st.write("**題目：**")
            st.write(chat["question"])
            st.write("**答案：**")
            st.write(chat["answer"])
            if chat["scores"]:
                st.write("**評分：**")
                total_score = sum(chat["scores"].values())
                for category, score in chat["scores"].items():
                    st.write(f"{category}: {score}/5 分")
                st.write(f"**總分**: {total_score}/25 分")
            st.write("**回饋：**")
            clean_feedback = re.sub(r"\{.*?\}", "", chat["feedback"], flags=re.DOTALL).strip()
            st.write(clean_feedback)

def main() -> None:
    """
    Streamlit 主程式
    """
    st.set_page_config(page_title="AI 申論題批改老師", page_icon="📝", layout="wide")
    display_chat_history()

    st.title("你的 AI 申論題批改老師 📝")
    st.write("Hello, 我是你的 AI 申論題批改老師")
    st.write("我會根據你的答案給你專業的批改意見，並給你具體的改進建議。")

    col1, col2 = st.columns([2, 1])

    with col1:
        question = st.text_area("請輸入申論題題目：", height=100)
        answer = st.text_area("請輸入你的答案：", height=200)

        if st.session_state.current_feedback is None:
            if st.button("送出批改", type="primary"):
                if not question or not answer:
                    st.warning("請輸入題目與答案")
                else:
                    st.subheader("AI 批改建議")
                    # 【修改處】使用 st.write_stream 來顯示即時回饋
                    with st.spinner("AI 批改中..."):
                        # st.write_stream 會回傳完整的字串，我們需要它來解析分數
                        full_feedback = st.write_stream(get_feedback_stream(question, answer))
                    
                    # 串流結束後，用完整的字串來處理分數和儲存狀態
                    st.session_state.current_feedback = full_feedback
                    st.session_state.current_scores = extract_scores_from_json(full_feedback)
                    st.rerun() # 重新執行以顯示分數和圖表
        else:
            # 這部分是顯示結果，邏輯保持不變
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
                    st.rerun()

    with col2:
        if st.session_state.current_scores:
            st.subheader("評分雷達圖")
            fig = create_radar_chart(list(st.session_state.current_scores.values()), list(st.session_state.current_scores.keys()))
            st.plotly_chart(fig, use_container_width=True)
            display_scores(st.session_state.current_scores)

if __name__ == "__main__":
    main()