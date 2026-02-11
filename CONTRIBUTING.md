# 开发指南

感谢你对TCM智能诊疗系统的关注！

## 开发环境设置

### 后端环境
\`\`\`bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
\`\`\`

### 前端环境
\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

## 代码规范

### Python代码
- 遵循PEP 8规范
- 使用类型提示
- 编写文档字符串

### Git提交规范
- feat: 新功能
- fix: Bug修复
- docs: 文档更新
- style: 代码格式
- refactor: 重构
- test: 测试相关
- chore: 构建配置

## 分支管理
- main: 主分支，稳定版本
- develop: 开发分支
- feature/*: 功能分支
- hotfix/*: 紧急修复分支
