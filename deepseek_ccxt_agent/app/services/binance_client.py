import ccxt
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class BinanceClient:
    def __init__(self):
        self._load_config()
        self.exchange = self._init_exchange()
    
    def _load_config(self):
        self.api_key = os.getenv("BINANCE_API_KEY")
        self.api_secret = os.getenv("BINANCE_API_SECRET")
        if not all([self.api_key, self.api_secret]):
            logger.error("Missing Binance API credentials")
            raise ValueError("API credentials not configured")

    def _init_exchange(self):
        return ccxt.binance({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
            'timeout': 30000,  # 30秒超时
            'verbose': os.getenv('CCXT_DEBUG', 'false').lower() == 'true'
        })

    def place_order(self, symbol: str, side: str, amount: float, 
                   price: float = None, type: str = "market") -> Dict[str, Any]:
        """
        AWS优化特性：
        - 请求重试机制
        - 订单参数校验
        - 交易限额检查
        """
        try:
            # 参数标准化
            symbol = symbol.upper()
            side = side.lower()
            
            # 校验交易对
            market = self.exchange.market(symbol)
            if not market['active']:
                raise ValueError(f"{symbol} 交易对不可用")

            # 计算最小交易量
            min_amount = market['limits']['amount']['min']
            if amount < min_amount:
                raise ValueError(f"交易量不能小于 {min_amount}")

            # 执行订单（带自动重试）
            for attempt in range(3):
                try:
                    if type == "limit":
                        order = self.exchange.create_limit_order(symbol, side, amount, price)
                    else:
                        order = self.exchange.create_market_order(symbol, side, amount)
                    
                    logger.info(f"订单成功 {order['id']}")
                    return {
                        "status": "filled",
                        "order_id": order["id"],
                        "symbol": symbol,
                        "executed_qty": order["filled"]
                    }
                except ccxt.NetworkError as e:
                    logger.warning(f"网络错误重试 {attempt+1}/3: {str(e)}")
                    if attempt == 2:
                        raise

        except ccxt.ExchangeError as e:
            logger.error(f"交易所错误: {str(e)}")
            return {"error": "exchange_error", "details": str(e)}
        except Exception as e:
            logger.error(f"未处理异常: {str(e)}", exc_info=True)
            return {"error": "unexpected_error", "details": str(e)}

# 单例模式适配Lambda环境
_client = BinanceClient()

def place_order(*args, **kwargs):
    return _client.place_order(*args, **kwargs)
