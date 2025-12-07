"""
Simple entry point for running the application.
Usage: python app.py
"""

import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting WhatsApp Clone API")
    print("=" * 60)
    print(f"\n📝 App Name: {settings.APP_NAME}")
    print(f"📌 Version: {settings.APP_VERSION}")
    print(f"🔧 Debug Mode: {settings.DEBUG}")
    print(f"\n🌐 API will be available at: http://localhost:8000")
    print(f"📚 API Docs: http://localhost:8000/docs")
    print(f"📖 ReDoc: http://localhost:8000/redoc")
    print(f"\n⚠️  Make sure PostgreSQL and Redis are running!")
    print("=" * 60)
    print()

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
