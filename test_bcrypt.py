from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

try:
    hash1 = pwd_context.hash("test")
    print(f"Hash test: {hash1}")
    hash2 = pwd_context.hash("123456")
    print(f"Hash 123456: {hash2}")
    print("✅ bcrypt ok")
except Exception as e:
    print(f"❌ bcrypt error: {e}")
