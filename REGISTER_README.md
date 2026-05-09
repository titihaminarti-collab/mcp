# 用户注册功能完整实现指南

## 📋 功能概述

本项目已完整实现用户注册功能，包括：
- ✅ 安全的密码加密存储（bcrypt）
- ✅ 用户名唯一性验证
- ✅ 前后端完整集成
- ✅ 表单验证和错误处理
- ✅ 美观的UI界面

## 🗄️ 第一步：数据库建表

### 建表SQL语句

```sql
-- 创建用户表
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_user_username (username)
);
```

### 方法1：使用Navicat图形化工具建表

1. 打开Navicat，连接到MySQL数据库
2. 选择数据库 `advancedrag`
3. 右键点击"查询" → "新建查询"
4. 复制粘贴上面的SQL语句
5. 点击"运行"按钮
6. 刷新表列表，确认 `users` 表已创建

### 方法2：使用MySQL命令行建表

1. 打开命令行终端
2. 连接MySQL：
   ```bash
   mysql -u root -p
   ```
3. 选择数据库：
   ```sql
   USE advancedrag;
   ```
4. 执行建表语句：
   ```sql
   SOURCE D:\mcpp\intelligent-connected-platform\427MCPProject\create_users_table.sql
   ```
5. 验证建表成功：
   ```sql
   SHOW TABLES;
   DESCRIBE users;
   ```

## 🚀 第二步：启动项目

### 1. 安装后端依赖

```bash
cd D:\mcpp\intelligent-connected-platform\427MCPProject\backend
pip install -r requirements.txt
```

### 2. 启动后端服务器

```bash
cd D:\mcpp\intelligent-connected-platform\427MCPProject\backend
python main.py
```

后端将在 `http://localhost:8000` 启动

### 3. 启动前端开发服务器

```bash
cd D:\mcpp\intelligent-connected-platform\427MCPProject\mcp-project-frontend
npm run dev
```

前端将在 `http://localhost:5173` 启动

## 🧪 第三步：测试注册功能

### 自动化测试

运行测试脚本：

```bash
cd D:\mcpp\intelligent-connected-platform\427MCPProject
python test_register.py
```

### 手动测试

1. 打开浏览器访问 `http://localhost:5173`
2. 点击"还没有账号？立即注册"链接
3. 填写注册表单：
   - 用户名：`testuser123`
   - 邮箱：`test@example.com`（可选）
   - 密码：`password123`
   - 确认密码：`password123`
4. ���击"注册"按钮
5. 应该看到成功提示并自动跳转到登录页

### 测试验证点

- ✅ 用户名至少3个字符
- ✅ 密码至少6个字符
- ✅ 密码和确认密码必须一致
- ✅ 用户名不能重复注册
- ✅ 密码经过bcrypt加密存储
- ✅ 注册成功后跳转到登录页

## 📁 文件结构

```
427MCPProject/
├── backend/
│   ├── main.py                 # 注册API接口
│   ├── requirements.txt        # 依赖列表（已添加passlib）
│   └── ...
├── mcp_project/
│   └── rag/
│       └── database.py         # 用户数据库操作
├── mcp-project-frontend/
│   ├── src/
│   │   ├── views/
│   │   │   ├── RegisterView.vue    # 注册页面
│   │   │   └── LoginView.vue       # 登录页面（已更新）
│   │   └── router/
│   │       └── index.js            # 路由配置（已更新）
│   └── ...
├── create_users_table.sql     # 建表SQL脚本
├── test_register.py           # 测试脚本
└── .env                       # 环境配置（MySQL配置已添加）
```

## 🔒 安全特性

- **密码加密**: 使用bcrypt算法，安全存储密码
- **用户名唯一性**: 防止重复注册
- **输入验证**: 前端和后端双重验证
- **错误处理**: 友好的错误提示信息

## 🎨 UI界面

注册页面包含：
- 现代化的渐变背景
- 响应式表单设计
- 实时表单验证
- 成功/错误状态提示
- 与登录页面的统一设计风格

## 🔗 API接口

### 注册接口

**POST** `/api/auth/register`

**请求体**:
```json
{
  "username": "string",
  "password": "string",
  "confirm_password": "string",
  "email": "string (optional)"
}
```

**成功响应**:
```json
{
  "message": "User registered successfully",
  "user_id": 1
}
```

**错误响应**:
```json
{
  "detail": "Error message"
}
```

## 🐛 常见问题

### 1. 数据库连接失败
- 检查MySQL服务是否启动
- 确认`.env`文件中的数据库配置正确
- 确保数据库`advancedrag`已创建

### 2. 端口占用
- 检查8000和5173端口是否被占用
- 修改端口配置或释放端口

### 3. 依赖安装失败
- 确保Python版本 >= 3.8
- 使用虚拟环境安装依赖

### 4. 前端页面无法访问
- 确认后端服务器正在运行
- 检查axios baseURL配置

## 📞 技术支持

如果遇到问题，请检查：
1. 控制台错误信息
2. 后端服务器日志
3. 数据库连接状态
4. 网络连接状态

---

🎉 用户注册功能实现完成！现在您可以安全地注册新用户了。
