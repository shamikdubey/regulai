
8s
    await response(scope, receive, send)
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/starlette/responses.py:156: in __call__
    await self.background()
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/starlette/background.py:41: in __call__
    await task()
/opt/hostedtoolcache/Python/3.12.13/x64/lib/python3.12/site-packages/starlette/background.py:26: in __call__
    await self.func(*self.args, **self.kwargs)
app/services/ingestion_service.py:89: in ingest_document
    chunks = chunk_text(text)
app/services/ingestion_service.py:41: in chunk_text
    from langchain_text_splitters import RecursiveCharacterTextSplitter
E   ModuleNotFoundError: No module named 'langchain_text_splitters'
----------------------------- Captured stdout call -----------------------------
2026-03-29T17:25:18.049681Z [info     ] ingestion_start                document_id=e16bc7ee-f119-42c3-b991-87ad465ce91b method=POST path=/api/v1/documents/upload request_id=9005155d-dcc8-4075-8dcd-2d9e0c05eb80 tenant_id=4bb5f732-87a9-4442-9a04-e7914c07e619
2026-03-29T17:25:18.049921Z [info     ] text_extracted                 char_count=26 document_id=e16bc7ee-f119-42c3-b991-87ad465ce91b method=POST path=/api/v1/documents/upload request_id=9005155d-dcc8-4075-8dcd-2d9e0c05eb80 tenant_id=4bb5f732-87a9-4442-9a04-e7914c07e619
2026-03-29T17:25:18.050473Z [info     ] request                        duration_ms=122 method=POST path=/api/v1/documents/upload request_id=9005155d-dcc8-4075-8dcd-2d9e0c05eb80 status=200
2026-03-29T17:25:18.051141Z [error    ] unhandled                      error=No module named 'langchain_text_splitters' method=POST path=/api/v1/documents/upload request_id=9005155d-dcc8-4075-8dcd-2d9e0c05eb80 type=ModuleNotFoundError
=========================== short test summary info ============================
FAILED tests/test_api.py::TestTenantIsolation::test_other_tenant_cannot_see_my_documents - ModuleNotFoundError: No module named 'langchain_text_splitters'
!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
========================= 1 failed, 20 passed in 6.12s =========================
Error: Process completed with exit code 1.

