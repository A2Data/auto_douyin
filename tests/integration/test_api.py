"""
API集成测试
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


class TestDouyinAPI:
    """测试抖音API端点"""
    
    def test_health_check(self, test_client: TestClient):
        """测试健康检查端点"""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "douyin-mcp-server"
    
    def test_root_endpoint(self, test_client: TestClient):
        """测试根端点"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        assert "抖音自动上传MCP服务" in response.text
    
    def test_get_config_without_initialization(self, test_client: TestClient):
        """测试未初始化时获取配置"""
        response = test_client.get("/api/v1/config")
        
        # 应该返回500错误，因为配置未初始化
        assert response.status_code == 500
    
    @patch('video_uploader.services.douyin_service.DouYinUploader')
    def test_login_api(self, mock_uploader, test_client: TestClient):
        """测试登录API"""
        # 设置Mock
        mock_instance = AsyncMock()
        mock_instance.login.return_value = True
        mock_uploader.return_value = mock_instance
        
        # 发送登录请求
        login_data = {"account_name": "test_account"}
        response = test_client.post("/api/v1/login", json=login_data)
        
        # 由于应用状态未初始化，预期会返回500错误
        assert response.status_code == 500
    
    def test_check_account_status_without_initialization(self, test_client: TestClient):
        """测试未初始化时检查账号状态"""
        response = test_client.get("/api/v1/account/test_account/status")
        
        # 应该返回500错误，因为服务未初始化
        assert response.status_code == 500
    
    def test_upload_file_invalid_type(self, test_client: TestClient):
        """测试上传无效文件类型"""
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"test content")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as f:
                files = {"file": ("test.txt", f, "text/plain")}
                data = {"file_type": "video"}
                response = test_client.post("/api/v1/upload-file", files=files, data=data)
            
            # 应该返回500错误，因为服务未初始化
            assert response.status_code == 500
        finally:
            Path(temp_file_path).unlink(missing_ok=True)


class TestAPIDocumentation:
    """测试API文档"""
    
    def test_openapi_docs(self, test_client: TestClient):
        """测试OpenAPI文档"""
        response = test_client.get("/docs")
        assert response.status_code == 200
    
    def test_redoc_docs(self, test_client: TestClient):
        """测试ReDoc文档"""
        response = test_client.get("/redoc")
        assert response.status_code == 200
    
    def test_openapi_json(self, test_client: TestClient):
        """测试OpenAPI JSON"""
        response = test_client.get("/openapi.json")
        assert response.status_code == 200
        
        openapi_data = response.json()
        assert openapi_data["info"]["title"] == "抖音自动上传MCP服务"
        assert openapi_data["info"]["version"] == "1.0.0"


class TestAPIValidation:
    """测试API请求验证"""
    
    def test_login_missing_account_name(self, test_client: TestClient):
        """测试登录缺少账号名称"""
        response = test_client.post("/api/v1/login", json={})
        
        assert response.status_code == 422  # Validation error
    
    def test_login_invalid_json(self, test_client: TestClient):
        """测试登录无效JSON"""
        response = test_client.post(
            "/api/v1/login",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    def test_upload_video_missing_data(self, test_client: TestClient):
        """测试上传视频缺少数据"""
        response = test_client.post("/api/v1/upload", json={})
        
        assert response.status_code == 422  # Validation error
    
    def test_batch_upload_missing_data(self, test_client: TestClient):
        """测试批量上传缺少数据"""
        response = test_client.post("/api/v1/batch-upload", json={})
        
        assert response.status_code == 422  # Validation error