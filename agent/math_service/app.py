"""Math Operations Web Service — port 9000."""
import math

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Math Service", version="1.0.0")


class Operands(BaseModel):
    a: float
    b: float


class FactorialInput(BaseModel):
    n: int


class Result(BaseModel):
    result: float
    operation: str


@app.post("/api/add", response_model=Result)
async def add(ops: Operands):
    return Result(result=ops.a + ops.b, operation="add")


@app.post("/api/subtract", response_model=Result)
async def subtract(ops: Operands):
    return Result(result=ops.a - ops.b, operation="subtract")


@app.post("/api/multiply", response_model=Result)
async def multiply(ops: Operands):
    return Result(result=ops.a * ops.b, operation="multiply")


@app.post("/api/divide", response_model=Result)
async def divide(ops: Operands):
    if ops.b == 0:
        raise HTTPException(status_code=400, detail="Sifira bolme hatasi")
    return Result(result=ops.a / ops.b, operation="divide")


@app.post("/api/factorial", response_model=Result)
async def factorial(inp: FactorialInput):
    if inp.n < 0:
        raise HTTPException(status_code=400, detail="Negatif sayinin faktoriyeli hesaplanamaz")
    return Result(result=float(math.factorial(inp.n)), operation="factorial")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "math-service", "port": 9000}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=9000)
