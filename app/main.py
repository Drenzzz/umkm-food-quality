from fastapi import FastAPI


def create_app() -> FastAPI:
    return FastAPI(title="UMKM Food Quality API")


app = create_app()
