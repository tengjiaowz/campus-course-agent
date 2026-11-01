from app.common.exceptions import BusinessException
from app.database import SessionLocal
from app.models.user import User
from app.utils.jwt import decode_access_token


def user_id_form_authorization(authorization: str | None) -> int:
    """解析Token 拿到用户ID"""
    if not authorization:
        raise BusinessException(message="缺少 Authorization", code=401)
    token = authorization
    if authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise BusinessException(message="缺少登录凭证", code=401)
    try:
        payload = decode_access_token(token)
    except Exception:
        raise BusinessException(code=401, message="登录已失效，请重新登录")
    # 获取到用户ID
    user_id = payload.get("user_id")
    if not user_id:
        raise BusinessException(code=401, message="无效的登录凭证")
    # 从数据库根据用户ID查询用户信息
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id, User.status == 1).first()
        if not user:
            raise BusinessException(code=401, message="登录已失效或用户已被禁用")
        return user.id
    finally:
        db.close()
