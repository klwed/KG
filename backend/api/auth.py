from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from ..modules.auth_service import auth_service
from ..modules.invite_code import invite_code_manager
from ..schemas.auth import UserLogin, UserResponse, Token, TokenData
from ..core.security import get_current_user, require_teacher

router = APIRouter(prefix="/api/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str = None
    real_name: str = None
    invite_code: str = None


class InviteCodeRequest(BaseModel):
    role: str = "teacher"


@router.post("/register", summary="用户注册")
async def register(request: RegisterRequest):
    role = "student"

    if request.invite_code:
        code_info = invite_code_manager.verify_code(request.invite_code)
        if not code_info:
            raise HTTPException(status_code=400, detail="邀请码无效或已使用")
        role = code_info["role"]
        invite_code_manager.use_code(request.invite_code, request.username)
    else:
        all_users = auth_service.get_all_students()
        if len(all_users) == 0:
            role = "teacher"
        else:
            raise HTTPException(
                status_code=400, detail="注册需要邀请码，请联系老师获取"
            )

    result = auth_service.register_user(
        username=request.username,
        password=request.password,
        role=role,
        email=request.email,
        real_name=request.real_name,
    )

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["error"])

    return {"message": "注册成功", "user_id": result["user_id"], "role": role}


@router.post("/login", response_model=Token, summary="用户登录")
async def login(login_data: UserLogin):
    result = auth_service.login_user(login_data.username, login_data.password)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
        )

    return result


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_me(current_user: TokenData = Depends(get_current_user)):
    user = auth_service.get_user_by_id(current_user.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return UserResponse(
        id=user["id"],
        username=user["username"],
        email=user.get("email"),
        role=user["role"],
        real_name=user.get("real_name"),
        created_at=user["created_at"],
    )


@router.get("/students", summary="获取学生列表（仅教师）")
async def get_students(current_user: TokenData = Depends(require_teacher)):
    students = auth_service.get_teacher_students(current_user.user_id)
    return {"students": students}


@router.get("/role-check", summary="检查用户角色")
async def check_role(current_user: TokenData = Depends(get_current_user)):
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role,
        "is_teacher": current_user.role == "teacher",
        "is_student": current_user.role == "student",
    }


@router.post("/invite/create", summary="创建邀请码（仅教师）")
async def create_invite_code(
    request: InviteCodeRequest, current_user: TokenData = Depends(require_teacher)
):
    if request.role not in ["teacher", "student"]:
        raise HTTPException(status_code=400, detail="无效的角色")

    code = invite_code_manager.create_code(
        role=request.role, created_by=current_user.username
    )

    return {
        "code": code,
        "role": request.role,
        "message": f"邀请码已创建，用于注册{request.role}",
    }


@router.get("/invite/list", summary="查看邀请码列表（仅教师）")
async def list_invite_codes(current_user: TokenData = Depends(require_teacher)):
    codes = invite_code_manager.list_codes()
    return {"codes": codes}


@router.delete("/invite/{code}", summary="删除邀请码（仅教师）")
async def delete_invite_code(
    code: str, current_user: TokenData = Depends(require_teacher)
):
    if invite_code_manager.delete_code(code):
        return {"message": "邀请码已删除"}
    raise HTTPException(status_code=404, detail="邀请码不存在")
