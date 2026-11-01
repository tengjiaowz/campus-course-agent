from sqlalchemy import Result
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, Query

from app.models.user import User
from app.database import get_db
from app.dependencies.auth import get_current_admin
from app.common.response import Response
from app.services import course_services
from app.schemas.course import CourseCreateRequset, CourseUpdateRequset

router = APIRouter(prefix="/course", tags=["课程相关API接口"])


@router.get("")
def list_courses(
    keywords: str | None = Query(default=None, description="按名称/编码/简介模糊查询"),
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    data = course_services.list_course(db, keywords)
    return Response.success(data=data)


@router.post("")
def create_course(
    data: CourseCreateRequset,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    course = course_services.create_course(db, data)
    return Response.success(data=course)


@router.put("/{course_id}")
def update_course(
    course_id: int,
    data: CourseUpdateRequset,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    course = course_services.update_course(db, course_id, data)
    return Response.success(data=course)


@router.delete("/{course_id}")
def delete_course(
    course_id: int,
    _: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    course_services.delete_course(db, course_id)
    return Response.success()
