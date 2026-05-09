#!/usr/bin/env python3
"""
用户注册功能测试脚本
"""

import requests
import json

def test_register():
    """测试用户注册功能"""
    base_url = "http://localhost:8000"

    # 测试数据
    test_user = {
        "username": "testuser123",
        "password": "password123",
        "confirm_password": "password123",
        "email": "test@example.com"
    }

    print("🧪 测试用户注册功能")
    print(f"📡 请求地址: {base_url}/api/auth/register")
    print(f"📝 测试数据: {json.dumps(test_user, indent=2)}")

    try:
        response = requests.post(f"{base_url}/api/auth/register", json=test_user)
        print(f"📊 响应状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print("✅ 注册成功!")
            print(f"📄 响应内容: {json.dumps(result, indent=2)}")
        else:
            error = response.json()
            print("❌ 注册失败!")
            print(f"📄 错误信息: {json.dumps(error, indent=2)}")

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败! 请确保后端服务器正在运行")
        print("💡 请先启动后端: cd backend && python main.py")
    except Exception as e:
        print(f"❌ 测试出错: {e}")

def test_duplicate_username():
    """测试重复用户名注册"""
    base_url = "http://localhost:8000"

    test_user = {
        "username": "testuser123",  # 使用已存在的用户名
        "password": "password456",
        "confirm_password": "password456",
        "email": "test2@example.com"
    }

    print("\n🧪 测试重复用户名注册")
    print(f"📝 测试数据: {json.dumps(test_user, indent=2)}")

    try:
        response = requests.post(f"{base_url}/api/auth/register", json=test_user)
        print(f"📊 响应状态码: {response.status_code}")

        if response.status_code == 400:
            error = response.json()
            print("✅ 正确拒绝重复用户名!")
            print(f"📄 错误信息: {error.get('detail', 'Unknown error')}")
        else:
            print("❌ 应该拒绝重复用户名!")

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败!")
    except Exception as e:
        print(f"❌ 测试出错: {e}")

def test_password_validation():
    """测试密码验证"""
    base_url = "http://localhost:8000"

    test_cases = [
        {
            "name": "密码不匹配",
            "data": {
                "username": "user1",
                "password": "password123",
                "confirm_password": "password456",
                "email": "test@example.com"
            }
        },
        {
            "name": "密码太短",
            "data": {
                "username": "user2",
                "password": "123",
                "confirm_password": "123",
                "email": "test@example.com"
            }
        },
        {
            "name": "用户名太短",
            "data": {
                "username": "ab",
                "password": "password123",
                "confirm_password": "password123",
                "email": "test@example.com"
            }
        }
    ]

    for test_case in test_cases:
        print(f"\n🧪 测试: {test_case['name']}")
        try:
            response = requests.post(f"{base_url}/api/auth/register", json=test_case['data'])
            print(f"📊 响应状态码: {response.status_code}")

            if response.status_code == 400:
                error = response.json()
                print("✅ 正确验证失败!")
                print(f"📄 错误信息: {error.get('detail', 'Unknown error')}")
            else:
                print("❌ 应该验证失败!")

        except requests.exceptions.ConnectionError:
            print("❌ 连接失败!")
        except Exception as e:
            print(f"❌ 测试出错: {e}")

if __name__ == "__main__":
    print("🚀 开始用户注册功能测试\n")

    test_register()
    test_duplicate_username()
    test_password_validation()

    print("\n🎉 测试完成!")
