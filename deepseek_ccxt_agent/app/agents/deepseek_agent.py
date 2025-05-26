import requests
import os
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

def ask_deepseek(prompt: str) -> dict:
    """
    AWS部署增强版：
    - 自动重试机制
    - 连接池复用
    - 安全超时控制
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        logger.error("DEEPSEEK_API_KEY environment variable missing")
        return "Error: API key not configured"

    url = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")  # 移除多余空格
    
    with requests_retry_session() as session:
        try:
            response = session.post(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "system",
                            "content": os.getenv("SYSTEM_PROMPT", "你是一个专业的数字币策略助手...")  # 可配置化
                        },
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=(3.05, 27)
            )
            response.raise_for_status()
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                except (KeyError, IndexError, ValueError) as e:
                    logger.error(f"Response parsing failed: {str(e)}")
                    return "Error: Invalid response format"

        except requests.exceptions.RequestException as e:
            logger.error(f"API请求失败: {str(e)}")
            return {"success": False, "error": {"type": "NETWORK_ERROR", "code": 503, "message": "服务暂时不可用"}}  # 结构化错误

    return {"success": False, "error": {"type": "MAX_RETRIES", "code": 504, "message": "超过最大重试次数"}}

# 新增全局配置
if os.getenv("ENABLE_AWS_XRAY"):
    from aws_xray_sdk.core import xray_recorder
    xray_recorder.configure(service='Deepseek_Agent')
    ask_deepseek = xray_recorder.capture()(ask_deepseek)
    return f"Error: {response.status_code} - {response.text}"
