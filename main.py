import httpx
import asyncio
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

IDENTITY_MAP = {

    # 二游
    "原神": "米友",
    "崩坏3第一偶像爱酱": "米友",
    "崩坏星穹铁道": "米友",
    "星穹铁道": "米友",
    "绝区零": "米友",
    "明日方舟": "皱皮",
    "鸣潮": "潮友",
    # --- MOBA ---
    "王者荣耀": "农友",
    "英雄联盟": "撸狗",
    # --- FPS ---
    "CSGO国服": "GO学长",
    "古堡龙姬": "GO学长",
    "无畏契约": "瓦学弟",
    # --- V-TUBERS: THE VIRTUAL CIRCUS ---
    "嘉然今天吃什么": "嘉心糖",
    "向晚大魔王": "顶碗人",
    "乃琳Queen": "奶淇淋",
    "贝拉kira": "贝极星",
    "A-SOUL_Official": "一个魂",
    "珈乐Carol": "已风车",
    "七海Nana7mi": "脆鲨",
    "阿梓": "小孩梓",
    "東雪蓮Official": "罕见",
    "永雏塔菲": "雏草姬",
    "明前奶绿": "奶糖花",
    # --- TECH & LIFESTYLE ---
    "华为终端": "华粉",
    "小米公司": "米粉",
    # --- ABSTRACT & MEME CULTURE ---
    "孙笑川258": "恋尸癖",
    "理塘丁真": "理塘王"
}


@register("astrbot_plugin_ccf", "Neon", "B站成分查询插件", "1.2")
class MyPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    # -------------------------------------------------------
    # 修改点：直接在函数参数中定义 vmid: str
    # AstrBot 会自动把 /ccf 后的第一个参数赋值给 vmid
    # -------------------------------------------------------
    @filter.command("ccf")
    async def check_composition(self, event: AstrMessageEvent, vmid: str):
        """查询B站UID成分，用法：/ccf 12345678"""

        # 这里的 vmid 已经是 AstrBot 帮你剥离好的字符串了
        # 比如用户发 "/ccf 12345678"，这里 vmid 就是 "12345678"

        if not vmid:
            # 加个保险
            yield event.plain_result("请提供B站UID，例如：/ccf 12345678")
            return

        # 简单校验是否为纯数字
        if not vmid.isdigit():
            yield event.plain_result(f"UID格式错误：[{vmid}]。请输入纯数字UID。")
            return

        # 发送提示
        yield event.plain_result(f"正在分析 UID: {vmid} 的关注列表，请稍候...")

        # --- 以下是核心抓取逻辑 (保持不变) ---
        base_url = "https://line3-h5-mobile-api.biligame.com/game/center/h5/user/relationship/following_list"
        pn = 1
        ps = 50
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.bilibili.com/"
        }

        detected_logs = []
        detected_tags = set()

        async with httpx.AsyncClient(headers=headers) as client:
            while True:
                params = {"vmid": vmid, "ps": ps, "pn": pn}
                try:
                    response = await client.get(base_url, params=params)
                    response.raise_for_status()
                    data_obj = response.json().get("data", {})
                    user_list = data_obj.get("list", [])

                    if not user_list:
                        break

                    for user in user_list:
                        uname = user.get("uname")
                        if uname and uname in IDENTITY_MAP:
                            tag = IDENTITY_MAP[uname]
                            detected_tags.add(tag)
                            detected_logs.append(f"-> 发现关注了 [{uname}]，判定为 [{tag}]")

                    if pn > 50:  # 防死循环保护
                        break

                    pn += 1
                    await asyncio.sleep(0.1)

                except Exception as e:
                    logger.error(f"抓取中断: {e}")
                    yield event.plain_result(f"查询过程中发生错误: {e}")
                    return

        # --- 构建回复 ---
        result_lines = []
        result_lines.append("-" * 30)

        if detected_logs:
            result_lines.extend(detected_logs)

        result_lines.append("-" * 30)
        result_lines.append("【成分鉴定结果】")

        if detected_tags:
            result_lines.append(",".join(list(detected_tags)))
        else:
            result_lines.append("未检测到预设的成分。")

        final_msg = "\n".join(result_lines)

        yield event.plain_result(final_msg)
