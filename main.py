from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import httpx

@register("astrbot_plugin_ccf", "Neon", "AstrBot 插件:查询指定UID的近期评论并可以用AI总结", "1.0")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloworld")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息

    @filter.command("ccf")
    async def ccf(self, event: AstrMessageEvent):
        """查询指定UID的近期评论，可选关键词过滤。用法: /ccf <uid> [keyword]"""
        args = event.message_str.strip().split(maxsplit=1)  # 最多分割成2部分
        
        if not args:
            yield event.plain_result("请输入UID")
            return
        
        uid = args[0]
        keyword = args[1] if len(args) > 1 else ""
        
        url = "https://api.aicu.cc/api/v3/search/getreply"
        params = {
            "uid": uid,
            "pn": 1,
            "ps": 100,
            "mode": 0,
            "keyword": keyword
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
                
                # 解析 data 里的 replies 数组
                replies = data.get("data", {}).get("replies", [])
                
                if not replies:
                    yield event.plain_result("未找到相关评论数据。")
                    return
                
                # 取最近20条评论的 message
                recent_replies = replies[:20]
                
                # 组装成 "1-信息\n2-信息" 的格式
                result_lines = []
                for idx, reply in enumerate(recent_replies, start=1):
                    message = reply.get("message", "")
                    result_lines.append(f"{idx}-{message}")
                
                result_text = "\n".join(result_lines)
                yield event.plain_result(result_text)
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP 请求失败: {e}")
            yield event.plain_result(f"请求失败，HTTP 状态码: {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"请求错误: {e}")
            yield event.plain_result(f"请求错误: {str(e)}")
        except Exception as e:
            logger.error(f"解析数据失败: {e}")
            yield event.plain_result(f"解析数据失败: {str(e)}")

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
