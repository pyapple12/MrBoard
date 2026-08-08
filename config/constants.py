# 项目常量模块：VERSION 单一来源（main.py 与 ui 层共同引用，消除循环依赖）

VERSION = "ver 0.05"


# ===== config/constants.py 模块说明 =====
# 模块级常量：
#   VERSION：版本号唯一来源。main.py 与 ui/* 均 `from config.constants import VERSION`
#     引用，不再互相 import，彻底消除"入口模块 ↔ UI 模块"的循环依赖
#     （审计 M2：原 VERSION 放 main.py 导致 ui 反向引用 main，main 只能函数内
#     延迟 import ui 打破循环，违反 AGENTS.md 顶层 import 约定）
# 函数：无
# 设计理由：常量模块无依赖、无副作用，任何模块引用都不会触发连锁初始化
# 异常处理：无
# 关联配置：版本升级只改本文件一处
