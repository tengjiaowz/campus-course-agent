from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Date, ForeignKey, Integer, String
from app.database import Base


class Schedule(Base):
    __tablename__ = "Scheduls"
    __table_args__ = {"comment": "课程信息表"}

    user_id: Mapped[str] = mapped_column(
        Integer, ForeignKey("users.id"), comment="学生ID", nullable=False
    )
    class_date: Mapped[Date] = mapped_column(Date, comment="上课日期", nullable=False)
    period: Mapped[str] = mapped_column(String(50), comment="节次", nullable=False)
    course_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("courses.id"), comment="课程ID", nullable=False
    )
    location: Mapped[str] = mapped_column(String(100), comment="地点", nullable=False)
