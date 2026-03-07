"""
行情引擎循环入口
持续轮询订阅列表，抓取行情数据并写入缓存
"""
import asyncio
import os
from market_engine import run_engine
from db_manager import get_active_subs

ENGINE_INTERVAL = 30


async def main():
    print("[行情引擎] 启动...")
    
    while True:
        try:
            subs_by_key = await get_active_subs()
            
            all_subs = []
            for subs_list in subs_by_key.values():
                all_subs.extend(subs_list)
            
            if all_subs:
                await run_engine(all_subs)
            else:
                print("[行情引擎] 暂无活跃订阅，等待...")
            
        except Exception as e:
            print(f"[行情引擎] 异常: {e}")
        
        await asyncio.sleep(ENGINE_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())