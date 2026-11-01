"""FastMCP Streamable HTTP 服务。在 backend/ 下执行：python mcp_server.py"""

import logging
import re
from typing import Annotated

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from pydantic import Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.common.exceptions import BusinessException
from app.config import settings
from app.database import SessionLocal
from app.dependencies.mcp_auth import user_id_form_authorization
from app.models.study_plan import StudyPlan
from app.models.user import User
from app.schemas.study_plan import StudyPlanCreateRequest
from app.services import rag_service
from app.services.schedule_services import list_schedules_as_dict
from app.services.study_plan_services import create_study_plan

mcp = FastMCP("campus-course-agent")
logger = logging.getLogger(__name__)

# FastAPI 每轮生成 32 位小写十六进制轮次 ID，格式不符时拒绝保存。
_TURN_ID_PATTERN = re.compile(r"[0-9a-f]{32}")


def _current_headers() -> dict:
    """读取当前 HTTP 请求的完整请求头，用于只取 Authorization 和轮次 ID。"""
    return get_http_headers(include_all=True) or {}


def _current_user_id() -> int:
    """从当前的HTTP的请求头拿到authorization 然后解析出 user_id"""

    headers = _current_headers()
    auth = headers.get("authorization") or headers.get("Authorization")
    return user_id_form_authorization(auth)


def _current_turn_id() -> str:
    """从请求头取得本轮对话 ID；缺失时返回空串。"""
    headers = _current_headers()
    value = headers.get("x-chat-turn-id") or headers.get("X-Chat-Turn-Id") or ""
    return value.strip()


@mcp.tool()
def get_my_schedules(
    date: Annotated[
        str | None,
        Field(
            description="可选参数，上课的日期，格式：YYYY-MM-DD，不传则返回全部的列表"
        ),
    ] = None,
) -> dict:
    """查询当前登录用户自己的课表，不能通过参数指定其他用户。
    可查询指定日期或全部课表，不支持日期范围参数。
    查询一周等日期范围时，可省略 date 获取全部课表，再按目标日期范围筛选。
    成功返回 items 和 count；每条记录包含 date、period、course_id、
    course_name 和 location，分别表示上课日期、节次、课程 ID、课程名称和地点。
    失败返回 error 和空 items；含 error 时表示查询失败，不能解释为没有课程。"""

    try:
        user_id = _current_user_id()
    except BusinessException as exc:
        return {"error": exc.message, "items": []}
    except Exception:
        logger.exception("MCP 课表工具鉴权失败")
        return {"error": "身份验证服务异常，请稍后重试", "items": []}

    db = SessionLocal()
    try:
        items = list_schedules_as_dict(db, user_id, date)
        return {"items": items, "count": len(items)}
    except BusinessException as exc:
        return {"error": exc.message, "items": []}
    except Exception:
        logger.exception("MCP 课表查询失败")
        return {"error": "查询课表失败，请稍后重试", "items": []}
    finally:
        db.close()


@mcp.tool()
def search_course_docs(
    query: Annotated[str, Field(description="要从课程资料中检索的问题或关键词")],
) -> dict:
    """只读检索全站共享的课程资料；用户身份来自 JWT，不由模型填写。"""
    try:
        # 身份只决定是否允许检索；共享资料不按这个用户 ID 筛选。
        _current_user_id()
    except BusinessException as exc:
        return {"error": exc.message, "items": []}
    except Exception:
        logger.exception("MCP 检索工具鉴权失败")
        return {"error": "身份验证服务异常，请稍后重试", "items": []}

    result = rag_service.search_docs(query)
    if not result.get("ok"):
        return {"error": result.get("error", "检索失败"), "items": []}
    return {"items": result.get("items", [])}


@mcp.tool()
def save_study_plan(
    content: Annotated[str, Field(description="要保存的完整学习计划正文")],
) -> dict:
    """仅在用户明确要求保存时，将计划写入当前用户的数据库。"""
    try:
        user_id = _current_user_id()
    except BusinessException as exc:
        return {"ok": False, "error": exc.message}
    except Exception:
        logger.exception("MCP 保存工具鉴权失败")
        return {"ok": False, "error": "身份验证服务异常，请稍后重试"}

    turn_id = _current_turn_id()
    if not _TURN_ID_PATTERN.fullmatch(turn_id):
        return {"ok": False, "error": "缺少或无效的对话轮次标识"}

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.id == user_id, User.status == 1))
        if user is None:
            return {"ok": False, "error": "用户不存在或已被禁用"}

        # 预先查询用于返回易懂的重复提示；真正防止并发重复的是数据库唯一约束。
        existing = db.scalar(
            select(StudyPlan).where(
                StudyPlan.user_id == user_id, StudyPlan.turn_id == turn_id
            )
        )
        if existing is not None:
            return {"ok": False, "error": "本轮已保存学习计划，请勿重复保存"}

        try:
            row = create_study_plan(
                db,
                user,
                StudyPlanCreateRequest(content=content),
                turn_id=turn_id,
            )
        except BusinessException as exc:
            return {"ok": False, "error": exc.message}
        except IntegrityError:
            db.rollback()
            return {"ok": False, "error": "本轮已保存学习计划，请勿重复保存"}
        except Exception:
            db.rollback()
            logger.exception("MCP 保存学习计划失败")
            # 提交可能已落库但确认丢失，用独立会话核对本轮记录。
            try:
                with SessionLocal() as check_db:
                    saved = check_db.scalar(
                        select(StudyPlan).where(
                            StudyPlan.user_id == user_id,
                            StudyPlan.turn_id == turn_id,
                        )
                    )
            except Exception:
                logger.exception("MCP 保存状态核对失败")
                return {"ok": False, "error": "保存状态不确定，请到学习计划页面核对"}
            if saved is not None:
                return {"ok": False, "error": "保存状态不确定，请到学习计划页面核对"}
            return {"ok": False, "error": "保存学习计划失败，请稍后重试"}

        return {"ok": True, "id": row.id, "message": "学习计划已保存"}
    finally:
        db.close()


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        path=settings.MCP_PATH,
        uvicorn_config={"ws": "websockets"},
    )
