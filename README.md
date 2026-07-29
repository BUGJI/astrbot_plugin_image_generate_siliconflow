# AstrBot SiliconFlow 图像生成插件

基于 SiliconFlow API 的 AstrBot 图像生成插件，支持文生图、图生图、图像编辑等多种模式，内置多维度配额控制与成本控制机制。

## ✨ 核心功能

### 🎨 多模态生图模式
- **文生图**：通过文本提示词生成图像
- **图生图**：基于 1-3 张输入图片 + 提示词生成新图像（适用于 Qwen-Image-Edit 等模型）
- **多图融合**：支持最多 3 张参考图融合生成

### ⚙️ 灵活的模型配置
- **模型选择**：支持 SiliconFlow 平台任意图像生成模型（默认 Qwen/Qwen-Image-Edit-2509）
- **尺寸预设**：可配置多个预设尺寸，LLM 根据上下文自动选择或固定尺寸
- **推理步数**：可调节推理步数平衡质量与速度
- **扩展参数**：支持 `guidance_scale`、`seed` 等模型专属参数

### 🛡️ 多维度配额与成本控制
| 限制类型 | 说明 | 默认值 |
|---------|------|--------|
| 单用户每分钟请求限制 | 防止突发流量 | 2 次/分钟 |
| 单用户每日成本限额 | 控制单用户日消耗 | 3.0 成本单位 |
| 全局每日成本上限 | 保护整体预算 | 10.0 成本单位 |
| 单图成本单位 | 计费基准单位 | 0.3 |

### 💰 透明的配额查询系统
- **用户查询**：`/查询生图额度` 查看个人剩余额度、今日用量、每分钟限制
- **管理员查询**：`/查询生图额度 all` 查看全局统计、今日总消耗、Top 10 高消耗用户

### 🤖 LLM 工具调用支持
注册为 LLM Tool，支持大模型直接调用生图能力：
```json
{
  "name": "generate_image",
  "parameters": {
    "prompt": "提示词",
    "negative_prompt": "负面提示词(可选)",
    "image": "base64图片1(可选)",
    "image2": "base64图片2(可选)",
    "image3": "base64图片3(可选)"
  }
}
```

## 📦 安装方式

### 方式一：AstrBot 应用商店安装（推荐）
在 AstrBot 管理面板的「应用商店」搜索 `astrbot_plugin_image_generate_siliconflow` 安装。

### 方式二：手动安装
```bash
# 克隆到 AstrBot 插件目录
git clone <repo-url> data/plugins/astrbot_plugin_image_generate_siliconflow

# 安装依赖
cd data/plugins/astrbot_plugin_image_generate_siliconflow
pip install -r requirements.txt
```

重启 AstrBot 后在插件管理中启用。

## ⚙️ 配置说明

在 AstrBot 管理面板「插件配置」中配置：

### API 配置 (`api_config`)
| 字段 | 说明 | 默认值 |
|------|------|--------|
| `api_base_url` | SiliconFlow API 地址 | `https://api.siliconflow.cn/v1/images/generations` |
| `api_key` | **必填** SiliconFlow API Key | - |
| `model` | 模型名称 | `Qwen/Qwen-Image-Edit-2509` |

### 模型参数 (`model_parameters`)
| 字段 | 说明 | 示例 |
|------|------|------|
| `image_size` | 尺寸预设列表 | `["720x1280", "1024x1024", "1280x720"]` |
| `num_inference_steps` | 推理步数 | `20` |
| `extra_params` | 扩展参数 | `["guidance_scale:7.5", "seed:42"]` |

### 使用限制 (`user_usage_limits`)
| 字段 | 说明 | 默认值 |
|------|------|--------|
| `cost_per_image` | 单图成本 | `0.3` |
| `requests_per_minute` | 每分钟请求限制 | `2` |
| `daily_cost_limit_per_user` | 单用户日限额 | `3.0` |
| `global_daily_cost_limit` | 全局日限额 | `10.0` |

## 📖 使用指南

### 指令调用

| 指令 | 说明 | 示例 |
|------|------|------|
| `/generate_image <prompt> [negative_prompt]` | 生成图片 | `/generate_image 一只猫` |
| `/查询生图额度 [all]` | 查询额度（管理员加 all 查全局） | `/查询生图额度 all` |

**图生图用法**：在发送指令时附带 1-3 张图片，插件自动识别为图生图模式。

### LLM Prompt 调用示例
```json
{
  "tool": "generate_image",
  "arguments": {
    "prompt": "赛博朋克风格的城市夜景，霓虹灯，雨夜",
    "negative_prompt": "模糊、低质量、水印",
    "image": "base64_encoded_image_1",
    "image2": "base64_encoded_image_2"
  }
}
```

### 参数说明
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `prompt` | string | ✅ | 正向提示词 |
| `negative_prompt` | string | ❌ | 负面提示词 |
| `image` | string | ❌ | 参考图 1 (Base64) |
| `image2` | string | ❌ | 参考图 2 (Base64) |
| `image3` | string | ❌ | 参考图 3 (Base64) |

## 🔧 进阶配置

### 自定义模型参数示例
```json
{
  "model_parameters": {
    "image_size": ["512x512", "768x1024", "1024x1024"],
    "num_inference_steps": 28,
    "extra_params": [
      "guidance_scale:7.5",
      "seed:12345",
      "num_images_per_prompt:1"
    ]
  }
}
```

### 成本控制策略建议
| 场景 | `cost_per_image` | `daily_cost_limit_per_user` | `global_daily_cost_limit` |
|------|------------------|----------------------------|---------------------------|
| 个人测试 | 0.1 | 1.0 | 5.0 |
| 小群体使用 | 0.3 | 3.0 | 10.0 |
| 生产环境 | 0.5 | 5.0 | 50.0 |

## 📋 配额查询输出示例

### 普通用户
```
📊 生图额度查询
━━━━━━━━━━━━━━━━━━
👤 用户: User123 (123456)
💰 今日已用: 0.9 / 3.0
📦 剩余额度: 2.1
⏱️ 分钟限制: 2 次/分
🔄 重置时间: 2025-01-15 00:00:00
```

### 管理员 (all)
```
📊 全局生图统计
━━━━━━━━━━━━━━━━━━
💰 今日总消耗: 4.5 / 10.0
👥 活跃用户: 3 人
📈 总请求数: 15 次

🏆 Top 10 消耗用户:
1. UserA: 1.5
2. UserB: 1.2
3. UserC: 0.9
```

## ❓ 常见问题

**Q: 如何获取 SiliconFlow API Key？**  
A: 访问 [SiliconFlow 控制台](https://cloud.siliconflow.cn/) 注册并创建 API Key。

**Q: 支持哪些模型？**  
A: 支持 SiliconFlow 平台所有图像生成模型，在配置中修改 `model` 字段即可。

**Q: 图生图需要什么模型？**  
A: 需要支持图像编辑的模型（如 Qwen-Image-Edit、FLUX.1-Fill-dev 等），普通文生图模型不支持图生图。

**Q: 额度用完了怎么办？**  
A: 等待每日重置（默认 00:00），或联系管理员调整 `daily_cost_limit_per_user`。

**Q: 如何调整图像质量与速度？**  
A: 调整 `num_inference_steps`：步数越大质量越好但越慢，建议 20-30 步平衡质量与速度。

## 📄 许可证

MIT License

## 🔗 相关链接

- [AstrBot 官方文档](https://docs.astrbot.app/)
- [SiliconFlow API 文档](https://docs.siliconflow.cn/)
- [Qwen-Image-Edit 模型卡](https://huggingface.co/Qwen/Qwen-Image-Edit)