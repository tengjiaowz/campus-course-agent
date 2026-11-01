from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.common.response import Response
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services import mcp_cilent_service

router = APIRouter(prefix="/mcp", tags=["MCP服务调试"])


@router.get("/my-shedules")
async def get_my_chedules_by_mcp(
    _user: Annotated[User, Depends(get_current_user)],
    requset: Request,
    date: Annotated[str | None, Query(description="YYY-MM-DD,不传返回全部")] = None,
):
    authorization = requset.headers.get("Authorization") or ""
    data = await mcp_cilent_service.call_get_my_schedules(authorization, date)
    return Response.success(data=data)
