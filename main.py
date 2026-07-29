"""SiliconFlow 图像生成插件

通过 SiliconFlow API 调用图像生成模型生成图片。
"""

import json
import time
import aiohttp
from typing import Optional, List

from astrbot.api import logger
from astrbot.api import llm_tool, star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Image as ImageComponent


@star.register(
    "astrbot_plugin_image_generate_siliconflow",
    "AstrBot Team",
    "SiliconFlow 图像生成插件 - 通过 SiliconFlow API 生成图片",
    "1.0.0",
)
class SiliconFlowImageGenerate(star.Star):
    """SiliconFlow 图像生成插件"""

    def __init__(self, context: star.Context, config: dict = None) -> None:
        super().__init__(context, config)
        self.config = config or {}

    async def initialize(self) -> None:
        """插件初始化"""
        pass

    async def terminate(self) -> None:
        """插件终止"""
        pass

    def _get_config(self) -> dict:
        """获取插件配置"""
        return self.config

    def _build_payload(
        self,
        prompt: str,
        config: dict,
        image: Optional[str] = None,
        image2: Optional[str] = None,
        image3: Optional[str] = None,
    ) -> dict:
        """构建 API 请求载荷"""
        api_config = config.get("api_config", {})
        model_params = config.get("model_parameters", {})

        payload = {
            "model": api_config.get("model", "Qwen/Qwen-Image-Edit-2509"),
            "prompt": prompt,
        }

        image_size_list = model_params.get("image_size", ["720x1280"])
        if image_size_list:
            payload["image_size"] = image_size_list[0]

        num_inference_steps = model_params.get("num_inference_steps", 20)
        payload["num_inference_steps"] = num_inference_steps

        extra_params = model_params.get("extra_params", [])
        for param in extra_params:
            if ":" in param:
                key, value = param.split(":", 1)
                try:
                    if value.isdigit():
                        value = int(value)
                    elif value.replace(".", "", 1).isdigit():
                        value = float(value)
                    elif value.lower() in ("true", "false"):
                        value = value.lower() == "true"
                except ValueError:
                    pass
                payload[key] = value

        if image:
            payload["image"] = image
        if image2:
            payload["image2"] = image2
        if image3:
            payload["image3"] = image3

        return payload

    async def _call_siliconflow_api(
        self, payload: dict, api_key: str, base_url: str
    ) -> dict:
        """调用 SiliconFlow API"""
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                base_url,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise Exception(f"API 请求失败 (HTTP {resp.status}): {error_text}")
                return await resp.json()

    def _extract_image_url(self, response: dict) -> Optional[str]:
        """从响应中提取图片 URL"""
        images = response.get("images", [])
        if images and isinstance(images, list) and len(images) > 0:
            first_image = images[0]
            if isinstance(first_image, dict):
                return first_image.get("url")
            elif isinstance(first_image, str):
                return first_image
        return None

    async def _extract_images_from_event(self, event: AstrMessageEvent) -> List[str]:
        """从事件消息中提取图片（转为 base64）"""
        images = []
        for comp in event.get_messages():
            if isinstance(comp, ImageComponent):
                try:
                    # 尝试转为 base64
                    b64 = await comp.convert_to_base64()
                    images.append(f"base64://{b64}")
                except Exception as e:
                    logger.warning(f"图片转换失败: {e}")
                    # 如果有 URL，直接使用
                    if comp.url:
                        images.append(comp.url)
                    elif comp.file:
                        images.append(comp.file)
        return images

    async def _check_usage_limits(self, event: AstrMessageEvent, config: dict) -> Optional[str]:
        """检查使用限制，返回错误信息或 None"""
        limits = config.get("user_usage_limits", {})
        if not limits:
            return None

        user_id = event.get_sender_id()
        if not user_id:
            return None

        now = time.time()
        today = int(now // 86400)

        # 检查每分钟请求限制
        reqs_per_min = limits.get("requests_per_minute", 2)
        minute_key = f"reqs_{user_id}_{int(now // 60)}"
        minute_reqs = await self.get_kv_data(minute_key, 0)
        if minute_reqs >= reqs_per_min:
            return f"错误: 请求过于频繁，每分钟最多 {reqs_per_min} 次。"

        # 检查用户每日成本限制
        daily_limit_user = limits.get("daily_cost_limit_per_user", 3)
        cost_per_image = limits.get("cost_per_image", 0.3)
        user_day_key = f"cost_{user_id}_{today}"
        user_daily_cost = await self.get_kv_data(user_day_key, 0.0)
        if user_daily_cost + cost_per_image > daily_limit_user:
            return f"错误: 您今日已达成本上限 ({daily_limit_user})，请明天再试。"

        # 检查全局每日成本限制
        global_daily_limit = limits.get("global_daily_cost_limit", 10)
        global_day_key = f"global_cost_{today}"
        global_daily_cost = await self.get_kv_data(global_day_key, 0.0)
        if global_daily_cost + cost_per_image > global_daily_limit:
            return f"错误: 系统今日总成本已达上限 ({global_daily_limit})，请明天再试。"

        return None

    async def _record_usage(self, event: AstrMessageEvent, config: dict) -> None:
        """记录使用情况"""
        limits = config.get("user_usage_limits", {})
        if not limits:
            return

        user_id = event.get_sender_id()
        if not user_id:
            return

        now = time.time()
        today = int(now // 86400)
        cost_per_image = limits.get("cost_per_image", 0.3)

        # 记录每分钟请求数
        minute_key = f"reqs_{user_id}_{int(now // 60)}"
        minute_reqs = await self.get_kv_data(minute_key, 0)
        await self.put_kv_data(minute_key, minute_reqs + 1)

        # 记录用户每日成本
        user_day_key = f"cost_{user_id}_{today}"
        user_daily_cost = await self.get_kv_data(user_day_key, 0.0)
        await self.put_kv_data(user_day_key, user_daily_cost + cost_per_image)

        # 记录全局每日成本
        global_day_key = f"global_cost_{today}"
        global_daily_cost = await self.get_kv_data(global_day_key, 0.0)
        await self.put_kv_data(global_day_key, global_daily_cost + cost_per_image)

    @llm_tool("generate_image")
    async def generate_image(
        self,
        event: AstrMessageEvent,
        prompt: str,
        negative_prompt: str = "",
    ) -> str:
        """使用 SiliconFlow API 生成图片。

        Args:
            prompt(string): 图片生成提示词，描述想要生成的图片内容。
            negative_prompt(string): 负面提示词，描述不想要在图片中出现的内容。

        Returns:
            string: 生成的图片 URL，或错误信息。
        """
        config = self._get_config()
        api_config = config.get("api_config", {})

        api_key = api_config.get("api_key")
        base_url = api_config.get("base_url", "https://api.siliconflow.cn/v1/images/generations")

        if not api_key:
            return "错误: 未配置 SiliconFlow API Key，请在插件配置中设置。"

        if not prompt:
            return "错误: 提示词不能为空。"

        # 检查使用限制
        limit_error = await self._check_usage_limits(event, config)
        if limit_error:
            return limit_error

        # 自动从消息中提取图片
        images = await self._extract_images_from_event(event)
        image = images[0] if len(images) > 0 else ""
        image2 = images[1] if len(images) > 1 else ""
        image3 = images[2] if len(images) > 2 else ""

        if negative_prompt:
            prompt = f"{prompt} --neg {negative_prompt}"

        payload = self._build_payload(prompt, config, image, image2, image3)

        try:
            response = await self._call_siliconflow_api(payload, api_key, base_url)
            image_url = self._extract_image_url(response)

            if image_url:
                # 记录使用情况
                await self._record_usage(event, config)
                return image_url
            else:
                return f"错误: API 返回异常，未找到图片 URL。响应: {json.dumps(response, ensure_ascii=False)}"

        except aiohttp.ClientError as e:
            return f"错误: 网络请求失败 - {str(e)}"
        except Exception as e:
            return f"错误: {str(e)}"

    def _is_admin(self, event: AstrMessageEvent) -> bool:
        """检查用户是否为管理员"""
        user_id = event.get_sender_id()
        if not user_id:
            return False
        global_config = self.context.get_config()
        admins = global_config.get("admins_id", [])
        return str(user_id) in admins

    async def _get_user_quota(self, user_id: str, today: int, limits: dict) -> dict:
        """获取用户额度信息"""
        cost_per_image = limits.get("cost_per_image", 0.3)
        daily_limit_user = limits.get("daily_cost_limit_per_user", 3)
        user_day_key = f"cost_{user_id}_{today}"
        user_daily_cost = await self.get_kv_data(user_day_key, 0.0)
        remaining_cost = max(0, daily_limit_user - user_daily_cost)
        remaining_images = int(remaining_cost / cost_per_image) if cost_per_image > 0 else 0
        return {
            "user_id": user_id,
            "used_cost": round(user_daily_cost, 2),
            "daily_limit": daily_limit_user,
            "remaining_cost": round(remaining_cost, 2),
            "remaining_images": remaining_images,
        }

    @filter.command("查询生图额度")
    async def query_quota_cmd(self, event: AstrMessageEvent, scope: str = "") -> None:
        """查询生图额度: /查询生图额度 [all] - 管理员可用 all 查看全局统计"""
        config = self._get_config()
        limits = config.get("user_usage_limits", {})
        if not limits:
            event.set_result("未启用额度限制功能。")
            return

        user_id = event.get_sender_id()
        if not user_id:
            event.set_result("无法获取用户 ID。")
            return

        is_admin = self._is_admin(event)
        today = int(time.time() // 86400)
        cost_per_image = limits.get("cost_per_image", 0.3)
        daily_limit_user = limits.get("daily_cost_limit_per_user", 3)
        global_daily_limit = limits.get("global_daily_cost_limit", 10)

        # 获取用户自己的额度
        user_info = await self._get_user_quota(user_id, today, limits)

        lines = [
            "=== 生图额度查询 ===",
            f"用户: {user_id}",
            f"今日已消耗: {user_info['used_cost']} / {user_info['daily_limit']}",
            f"剩余额度: {user_info['remaining_cost']} (约可生成 {user_info['remaining_images']} 张)",
        ]

        # 管理员查看全局统计
        if is_admin and scope.lower() == "all":
            global_day_key = f"global_cost_{today}"
            global_daily_cost = await self.get_kv_data(global_day_key, 0.0)
            global_remaining = max(0, global_daily_limit - global_daily_cost)
            global_remaining_images = int(global_remaining / cost_per_image) if cost_per_image > 0 else 0

            lines.extend([
                "",
                "=== 管理员视图：全局统计 ===",
                f"全局今日已消耗: {round(global_daily_cost, 2)} / {global_daily_limit}",
                f"全局剩余额度: {round(global_remaining, 2)} (约可生成 {global_remaining_images} 张)",
                f"单张成本: {cost_per_image}",
                f"用户日限额: {daily_limit_user}",
                f"全局日限额: {global_daily_limit}",
            ])

        event.set_result("\n".join(lines))