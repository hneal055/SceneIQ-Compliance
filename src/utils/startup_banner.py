def print_api_urls(*, api_version: str, host: str = "localhost", port: int = 8000) -> None:
    base = f"http://{host}:{port}"
    print(f"Swagger UI:  {base}/docs")
    print(f"ReDoc:      {base}/redoc")
    print(f"OpenAPI:    {base}/openapi.json")
    print(f"API Root:   {base}/api/{api_version}")



