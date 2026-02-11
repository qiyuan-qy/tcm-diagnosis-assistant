#!/bin/bash
# 智能问诊系统快速启动脚本

echo "======================================"
echo "  智能问诊系统 - 启动"
echo "======================================"

PROJECT_DIR="/home/xiyun/tcm-diagnosis-assistant"
cd $PROJECT_DIR

# 1. 检查后端
echo "检查后端服务..."
if ! pgrep -f "uvicorn.*8000" > /dev/null; then
    echo "启动后端..."
    cd backend
    nohup venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/tcm_backend.log 2>&1 &
    sleep 3
    echo "✓ 后端已启动"
else
    echo "✓ 后端已运行"
fi

# 2. 配置nginx
echo "配置nginx..."
echo "123456" | sudo -S tee /etc/nginx/sites-available/tcm-diagnosis > /dev/null << 'NGINX'
server {
    listen 80;
    server_name _;
    
    location / {
        root /home/xiyun/tcm-diagnosis-assistant/frontend/dist;
        index admin.html;
        try_files $uri $uri/ /admin.html;
    }
    
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws/ {
        proxy_pass http://127.0.0.1:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
NGINX

# 3. 启用配置
echo "123456" | sudo -S ln -sf /etc/nginx/sites-available/tcm-diagnosis /etc/nginx/sites-enabled/
echo "123456" | sudo -S rm -f /etc/nginx/sites-enabled/default 2>/dev/null

# 4. 重启nginx
echo "123456" | sudo -S nginx -t > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "123456" | sudo -S systemctl reload nginx
    echo "✓ Nginx已配置"
else
    echo "✗ Nginx配置失败"
    exit 1
fi

echo ""
echo "======================================"
echo "  启动完成！"
echo "======================================"
echo "访问地址: http://192.168.171.129"
echo "管理页面: http://192.168.171.129/admin.html"
echo ""
echo "日志查看: tail -f /tmp/tcm_backend.log"
echo ""
