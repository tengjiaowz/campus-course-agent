from email import message

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class StudyPlan(Base):
    __tablename__ = "studyplans"
    __table_args__ = (
        UniqueConstraint("user_id", "turn_id", name="uq_study_plan_user_turn"),
        {"comment": "学习计划"},
    )

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), comment="用户ID", nullable=False
    )
    content: Mapped[str] = mapped_column(Text, comment="计划内容", nullable=False)
    turn_id: Mapped[str | None] = mapped_column(
        String(32), comment="MCP对话轮次ID", nullable=True
    )
