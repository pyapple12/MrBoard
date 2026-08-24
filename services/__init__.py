# 应用服务门面包（A017/PL006）：UI 层唯一后端入口——from services import get_service

from services.service import AppService, ServiceError, UsageData, get_service

__all__ = ["AppService", "ServiceError", "UsageData", "get_service"]
