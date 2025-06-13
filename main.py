import json
import streamlit as st
import os
import re
import dotenv
import plotly.graph_objects as go
from typing import Dict, Optional, List, Union

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


def get_feedback(question: str, answer: str) -> str:
    """
    呼叫 Gemini LLM，根據題目與用戶答案，回傳批改意見、分數與標準答案。

    Args:
        question (str): 申論題題目
        answer (str): 用戶回答內容

    Returns:
        str: LLM 的回饋內容

    Raises:
        Exception: 當 LLM 呼叫失敗時拋出異常
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
        response = llm.predict(prompt)
        return response
    except Exception as e:
        st.error(f"獲取回饋時發生錯誤: {str(e)}")
        raise


def extract_scores_from_json(feedback: str) -> Optional[Dict[str, int]]:
    """
    從回傳的文字中提取 JSON 格式分數

    Args:
        feedback (str): LLM 回饋內容

    Returns:
        Optional[Dict[str, int]]: 解析出的分數字典，解析失敗則返回 None
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

    Args:
        scores (List[int]): 各項分數列表
        categories (List[str]): 各項指標名稱列表

    Returns:
        go.Figure: Plotly 圖表物件
    """
    # 雷達圖需要首尾相連
    scores = scores + scores[:1]
    categories = categories + categories[:1]

    fig = go.Figure(
        data=[go.Scatterpolar(r=scores, theta=categories, fill="toself", name="分數")],
        layout=go.Layout(polar=dict(radialaxis=dict(visible=True, range=[0, 5])), showlegend=False),
    )
    return fig


def main() -> None:
    """
    Streamlit 主程式，負責用戶互動與顯示批改結果
    """
    st.title("你的 AI 申論題批改老師 📝")
    st.write("Hello, 我是你的 AI 申論題批改老師")
    st.write("我會根據你的答案給你專業的批改意見，並給你具體的改進建議。")

    question = st.text_area("請輸入申論題題目：")
    answer = st.text_area("請輸入你的答案：")

    feedback = None
    if st.button("送出批改"):
        if not question or not answer:
            st.warning("請輸入題目與答案")
        else:
            try:
                with st.spinner("AI 批改中..."):
                    feedback = get_feedback(question, answer)
                st.subheader("AI 批改結果")

                # 先顯示雷達圖
                scores_dict = extract_scores_from_json(feedback)
                if scores_dict:
                    fig = create_radar_chart(
                        scores=list(scores_dict.values()), categories=list(scores_dict.keys())
                    )
                    st.plotly_chart(fig)

                # 顯示移除 JSON 後的回饋內容
                # 使用正則表達式移除 JSON 部分
                clean_feedback = re.sub(r"\{.*?\}", "", feedback, flags=re.DOTALL).strip()
                st.write(clean_feedback)
            except Exception as e:
                st.error(f"批改過程發生錯誤: {str(e)}")


if __name__ == "__main__":
    main()
