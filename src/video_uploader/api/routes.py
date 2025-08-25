"""
API路由定义
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List, Optional

from ..models.platforms import (
    LoginRequest,
    LoginResponse,
    UploadRequest,
    UploadResponse,
    BatchUploadRequest,
    BatchUploadResponse,
    BaseAccount,
    BaseVideoInfo,
)
from ..models.douyin import DouyinAccount, VideoInfo
from ..services.platform_manager import PlatformManager
from ..services.douyin_service import DouyinService
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["douyin"])


def get_douyin_service(request: Request) -> DouyinService:
    """获取抖音服务实例"""
    config = getattr(request.app.state, "config", None)
    if not config:
        raise HTTPException(status_code=500, detail="服务未初始化")
    return DouyinService(config)


@router.post("/login", response_model=LoginResponse, summary="账号登录")
async def login(request: Request, login_request: LoginRequest) -> LoginResponse:
    """
    登录抖音账号并生成Cookie
    
    - **account_name**: 账号名称，用于标识不同的抖音账号
    
    登录成功后会在浏览器中打开抖音创作者中心，需要手动完成登录过程
    """
    try:
        service = get_douyin_service(request)
        response = await service.login(login_request)
        logger.info(f"登录请求处理完成: {login_request.account_name} - {response.success}")
        return response
    except Exception as e:
        logger.error(f"登录接口异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"登录失败: {str(e)}")


@router.post("/upload", response_model=UploadResponse, summary="上传视频")
async def upload_video(request: Request, upload_request: UploadRequest) -> UploadResponse:
    """
    上传单个视频到抖音
    
    - **account_name**: 账号名称
    - **video_info**: 视频信息，包括路径、标题、标签等
    - **publish_date**: 发布时间，为None时立即发布
    
    视频上传前会自动检查Cookie有效性，无效时需要重新登录
    """
    try:
        service = get_douyin_service(request)
        response = await service.upload_video(upload_request)
        logger.info(f"上传请求处理完成: {upload_request.video_info.title} - {response.success}")
        return response
    except Exception as e:
        logger.error(f"上传接口异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/batch-upload", response_model=BatchUploadResponse, summary="批量上传视频")
async def batch_upload_videos(request: Request, batch_request: BatchUploadRequest) -> BatchUploadResponse:
    """
    批量上传多个视频到抖音
    
    - **account_name**: 账号名称
    - **video_list**: 视频列表
    - **config**: 批量上传配置，包括每天发布数量、时间点等
    
    系统会根据配置自动安排发布时间，避免频繁发布
    """
    try:
        service = get_douyin_service(request)
        response = await service.batch_upload(batch_request)
        logger.info(f"批量上传请求处理完成: {response.success_count}/{response.total_videos} 成功")
        return response
    except Exception as e:
        logger.error(f"批量上传接口异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")


@router.get("/account/{account_name}/status", response_model=DouyinAccount, summary="检查账号状态")
async def check_account_status(request: Request, account_name: str) -> DouyinAccount:
    """
    检查指定账号的登录状态
    
    - **account_name**: 账号名称
    
    返回账号信息，包括是否已登录、Cookie文件路径等
    """
    try:
        service = get_douyin_service(request)
        account = await service.check_account_status(account_name)
        logger.info(f"账号状态检查完成: {account_name} - 已登录: {account.is_logged_in}")
        return account
    except Exception as e:
        logger.error(f"账号状态检查异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"检查账号状态失败: {str(e)}")


@router.get("/config", summary="获取当前配置")
async def get_config(request: Request):
    """
    获取当前应用配置
    
    返回Chrome路径、目录配置等信息
    """
    try:
        config = getattr(request.app.state, "config", None)
        if not config:
            raise HTTPException(status_code=500, detail="配置未加载")
        
        config_dict = config.model_dump(mode='json')
        # 将Path对象转换为字符串以便JSON序列化
        for key, value in config_dict.items():
            if hasattr(value, '__str__'):
                config_dict[key] = str(value)
        
        return JSONResponse(content=config_dict)
    except Exception as e:
        logger.error(f"获取配置异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取配置失败: {str(e)}")


@router.post("/upload-file", summary="上传文件")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    file_type: str = "video"
):
    """
    上传视频或缩略图文件到服务器
    
    - **file**: 要上传的文件
    - **file_type**: 文件类型 (video/thumbnail)
    """
    try:
        config = getattr(request.app.state, "config", None)
        if not config:
            raise HTTPException(status_code=500, detail="配置未加载")
        
        # 确定保存目录
        if file_type == "video":
            save_dir = config.videos_dir
            allowed_extensions = [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".m4v"]
        elif file_type == "thumbnail":
            save_dir = config.videos_dir  # 缩略图也保存在videos目录
            allowed_extensions = [".png", ".jpg", ".jpeg"]
        else:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        # 检查文件扩展名
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件扩展名: {file_extension}，支持的扩展名: {allowed_extensions}"
            )
        
        # 保存文件
        file_path = save_dir / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        logger.info(f"文件上传成功: {file_path}")
        return {
            "success": True,
            "message": "文件上传成功",
            "file_path": str(file_path),
            "file_size": len(content),
            "file_type": file_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文件上传异常: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")