from fastapi import APIRouter

router = APIRouter()


@router.get("/hello")
async def get_hello() -> dict[str, str]:
    return {"message": "Hello, world!!!", "method": "GET"}


@router.put("/hello")
async def put_hello() -> dict[str, str]:
    return {"message": "Hello, world!", "method": "PUT"}


@router.get("/hello/{name}")
async def get_hello_name(name: str) -> dict[str, str]:
    return {"message": f"Hello, {name}!"}
