from annotated_types import T
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.course import Course
from app.schemas.course import CourseCreateRequset, CourseResponse, CourseUpdateRequset
from app.common.exceptions import BusinessException
from app.models.schedule import Schedule


def list_course(db: Session, keywprds: str | None = None) -> list[CourseResponse]:
    """课程列表"""
    query = db.query(Course)
    if keywprds and keywprds.strip():
        kw = f"%{keywprds.strip()}%"
        query = query.filter(
            or_(
                # 不区分大小写
                Course.name.ilike(kw),
                Course.code.ilike(kw),
                Course.description.ilike(kw),
            )
        )
    rows = query.order_by(Course.id.desc()).all()
    return [CourseResponse.model_validate(row) for row in rows]
    """
    for row in rows:
        r = CourseResponse.model_validate(row)
        results,append(r)
    """


def create_course(db: Session, data: CourseCreateRequset) -> CourseResponse:
    """新增课程"""
    if not data.code.strip():
        raise BusinessException(message="课程编码必传")
    exist = db.query(Course).filter(Course.code == data.code.strip()).first()
    if exist:
        raise BusinessException(message="课程编码已存在")
    course = Course(
        name=data.name.strip(),
        code=data.code.strip(),
        description=(data.description or "").strip() or None,
        status=data.status if data.status in (0, 1) else 1,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return CourseResponse.model_validate(course)


def update_course(
    db: Session, course_id: int, data: CourseUpdateRequset
) -> CourseResponse:
    """更新课程"""
    row = db.query(Course).filter(Course.id == course_id).first()
    if not row:
        raise BusinessException(message="课程不存在")
    payload = data.model_dump(exclude_none=True)
    if "name" in payload:
        payload["name"] = payload["name"].strip()
    if "code" in payload:
        code = payload["code"].strip()
        conflist = (
            db.query(Course).filter(Course.code == code, Course.id != course_id).first()
        )
        if conflist:
            raise BusinessException(message="课程编号已存在")
        payload["code"] = payload["code"].strip()
    if "description" in payload:
        payload["description"] = payload["description"].strip()

    for field, value in payload.items():
        setattr(row, field, value)

    db.commit()
    db.refresh(row)
    return CourseResponse.model_validate(row)


def delete_course(db: Session, course_id: int) -> None:
    """删除课程"""
    row = db.query(Course).filter(Course.id == course_id).first()
    if not row:
        raise BusinessException(message="课程不存在")
    linked = db.query(Schedule).filter(Schedule.course_id == course_id).first()
    if linked:
        raise BusinessException(message="该课程已关联课表，无法删除")
    db.delete(row)
    db.commit()
