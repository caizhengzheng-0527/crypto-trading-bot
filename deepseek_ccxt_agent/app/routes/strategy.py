from fastapi import APIRouter, Request, HTTPException
from app.agents.deepseek_agent import ask_deepseek
from app.services.binance_client import place_order
import json
import logging
from typing import Dict, Any

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/ask")
async def get_strategy(request: Request):
    """
    AWS增强特性：
    - 请求体大小限制（10KB）
    - 输入消毒处理
    - 异步上下文管理
    """
    try:
        # 限制请求体大小
        raw_data = await request.body()
        if len(raw_data) > 10240:  # 10KB限制
            raise HTTPException(status_code=413, detail="Payload too large")

        data = await request.json()
        prompt = str(data.get("prompt", "")).strip()[:500]  # 输入消毒

        if not prompt:
            raise HTTPException(status_code=400, detail="Empty prompt")

        # 调用AI模块
        result = ask_deepseek(prompt)
        
        # 解析策略
        try:
            strategy_data: Dict[str, Any] = json.loads(result)
            required_fields = {"symbol", "side", "amount", "type"}
            
            if not required_fields.issubset(strategy_data.keys()):
                raise ValueError("Missing required fields")

            # 参数消毒
            strategy_data['amount'] = float(strategy_data['amount'])
            strategy_data['type'] = strategy_data['type'].lower()
            
            # 执行订单
            order_result = place_order(**strategy_data)
            
            return {
                "strategy": strategy_data,
                "order_result": order_result
            }
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"策略解析失败: {str(e)}")
            raise HTTPException(status_code=422, detail=f"Invalid strategy format: {str(e)}")
            
        except Exception as e:
            logger.error(f"订单执行失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Order execution failed: {str(e)}")

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.critical(f"未处理异常: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    return {"error": str(e), "ai_output": result}
