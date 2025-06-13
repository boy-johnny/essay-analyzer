import os
from typing import Dict, List, Optional
from datetime import datetime
from supabase import create_client, Client

class SupabaseManager:
    """Supabase 數據管理類"""
    
    def __init__(self):
        """初始化 Supabase 客戶端"""
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("請設置 SUPABASE_URL 和 SUPABASE_KEY 環境變數")
            
        self.supabase = create_client(supabase_url, supabase_key)
    
    def save_chat(self, question: str, answer: str, feedback: str, scores: Optional[Dict[str, int]] = None) -> Dict:
        """
        保存對話記錄到 Supabase
        
        Args:
            question: 問題內容
            answer: 答案內容
            feedback: AI 回饋
            scores: 評分結果
            
        Returns:
            Dict: 保存的記錄
        """
        try:
            data = {
                "question": question,
                "answer": answer,
                "feedback": feedback,
                "scores": scores
            }
            
            result = self.supabase.table("chat_history").insert(data).execute()
            return result.data[0]
        except Exception as e:
            raise Exception(f"保存對話記錄失敗: {str(e)}")
    
    def get_chat_history(self, limit: int = 10) -> List[Dict]:
        """
        獲取最近的對話歷史
        
        Args:
            limit: 返回記錄的數量限制
            
        Returns:
            List[Dict]: 對話歷史記錄列表
        """
        try:
            result = self.supabase.table("chat_history")\
                .select("*")\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return result.data
        except Exception as e:
            raise Exception(f"獲取對話歷史失敗: {str(e)}")
    
    def delete_chat(self, chat_id: str) -> None:
        """
        刪除特定對話記錄
        
        Args:
            chat_id: 對話記錄ID
        """
        try:
            self.supabase.table("chat_history")\
                .delete()\
                .eq("id", chat_id)\
                .execute()
        except Exception as e:
            raise Exception(f"刪除對話記錄失敗: {str(e)}") 