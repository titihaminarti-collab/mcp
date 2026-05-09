#!/usr/bin/env python3
"""
数据库连接测试脚本
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from mcp_project.rag.database import DatabaseManager

def test_db_connection():
    """测试数据库连接"""
    try:
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        session.close()
        print("✅ 数据库连接成功!")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

def test_tables():
    """测试表是否存在"""
    try:
        db_manager = DatabaseManager()
        engine = db_manager.engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        expected_tables = ['users', 'original_docs', 'parent_chunks', 'child_chunks', 'chat_history']
        print(f"📋 数据库中的表: {tables}")
        for table in expected_tables:
            if table in tables:
                print(f"✅ 表 {table} 存在")
            else:
                print(f"❌ 表 {table} 不存在")
        return True
    except Exception as e:
        print(f"❌ 检查表失败: {e}")
        return False

def test_create_user():
    """测试创建用户"""
    try:
        db_manager = DatabaseManager()
        user = db_manager.create_user("testuser", "hashedpassword", "test@example.com")
        print(f"✅ 创建用户成功: {user.username}, id: {user.id}")
        return True
    except Exception as e:
        print(f"❌ 创建用户失败: {e}")
        return False

def test_table_structure():
    """测试表结构"""
    try:
        db_manager = DatabaseManager()
        engine = db_manager.engine
        from sqlalchemy import inspect
        inspector = inspect(engine)
        columns = inspector.get_columns('users')
        print("📋 users 表列:")
        for col in columns:
            print(f"  {col['name']}: {col['type']} nullable={col['nullable']}")
        return True
    except Exception as e:
        print(f"❌ 检查表结构失败: {e}")
        return False

if __name__ == "__main__":
    print("🧪 测试数据库连接和表结构\n")
    test_db_connection()
    test_tables()
    test_create_user()
    test_table_structure()
