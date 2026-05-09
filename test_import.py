try:
    from config import settings
    print('Config loaded, port:', settings.port)
    from api.chat import router as chat_router
    print('Chat router loaded')
    from api.rag import router as rag_router
    print('RAG router loaded')
    from main import app
    print('App created successfully')
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
