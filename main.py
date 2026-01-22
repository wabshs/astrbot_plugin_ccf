import httpx
import asyncio
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

# 必须确保同目录下有 tags.py 且包含 IDENTITY_MAP
try:
    from tags import IDENTITY_MAP
except ImportError:
    # 为了防止报错，如果没有文件，先给个空字典，并打印警告
    logger.warning("未找到 tags.py，成分查询功能将无法匹配标签！")
    IDENTITY_MAP = {}


@register("astrbot_plugin_ccf", "Neon", "B站成分查询插件", "1.1")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # 注册指令 ccf
    @filter.command("ccf")
    async def check_composition(self, event: AstrMessageEvent):
        """查询B站UID成分，用法：/ccf 384558170"""

        # 获取用户输入的参数 (假设用户输入 /ccf 123456)
        # message_str 通常包含指令后的内容
        vmid = event.message_str.strip()

        if not vmid:
            yield event.plain_result("请在指令后输入B站UID，例如：/ccf 384558170")
            return

        if not vmid.isdigit():
            yield event.plain_result("UID格式错误，请输入纯数字。")
            return

        # 发送提示，告诉用户正在查询（因为翻页可能需要几秒钟）
        yield event.plain_result(f"正在分析 UID: {vmid} 的关注列表，请稍候...")

        # --- 开始抓取逻辑 ---
        base_url = "https://line3-h5-mobile-api.biligame.com/game/center/h5/user/relationship/following_list"
        pn = 1
        ps = 50
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }

        detected_logs = []  # 用于存储 "-> 发现关注了..." 的日志
        detected_tags = set()  # 用于存储标签成分

        # 使用异步客户端
        async with httpx.AsyncClient(headers=headers) as client:
            while True:
                params = {"vmid": vmid, "ps": ps, "pn": pn}
                try:
                    response = await client.get(base_url, params=params)
                    response.raise_for_status()
                    data_obj = response.json().get("data", {})
                    user_list = data_obj.get("list", [])

                    if not user_list:
                        break  # 列表为空，停止

                    for user in user_list:
                        uname = user.get("uname")
                        if uname and uname in IDENTITY_MAP:
                            tag = IDENTITY_MAP[uname]
                            detected_tags.add(tag)
                            # 记录详细日志
                            detected_logs.append(f"-> 发现关注了 [{uname}]，判定为 [{tag}]")

                    # 限制最大页数以防死循环（可选，比如查几千关注的人会太久）
                    if pn > 50:
                        break

                    pn += 1
                    await asyncio.sleep(0.1)  # 异步休眠，防止请求过快

                except Exception as e:
                    logger.error(f"抓取中断: {e}")
                    yield event.plain_result(f"查询过程中发生错误: {e}")
                    return

        # --- 构建回复内容 ---
        # 1. 如果没有发现任何记录，也需要显示分隔符吗？根据你的样例，只要有结果就显示。
        # 这里我们严格按照你的样例拼接字符串。

        result_lines = []
        result_lines.append("-" * 30)

        # 添加详细发现记录
        if detected_logs:
            result_lines.extend(detected_logs)
        else:
            # 如果没抓到特定的，或者是空的，这里根据逻辑可能不需要输出中间行，但为了格式统一保留分隔线
            pass

        result_lines.append("-" * 30)
        result_lines.append("【成分鉴定结果】")

        if detected_tags:
            result_lines.append(",".join(list(detected_tags)))
        else:
            result_lines.append("未检测到预设的成分，鉴定为纯良")

        final_msg = "\n".join(result_lines)

        # 发送最终结果
        yield event.plain_result(final_msg)
