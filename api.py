"""
api.py

Thin FastAPI layer over matrix_backend.py. This is the only file that
knows about HTTP — all the actual matrix logic stays in matrix_backend.py.

Run with:
    uvicorn api:app --reload --port 8000
"""

from typing import List, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from matrix_backend import (
    Matrix,
    RowOperationEngine,
    RowOperationRequest,
    RowOperationType,
    MatrixError,
    MAX_OPERATIONS,
)

MAX_DIMENSION = 24  # tighter UX-driven limit; matrix_backend.py enforces its own
                     # much larger MAX_MATRIX_DIMENSION (200) as a safety backstop

app = FastAPI(title="Row Operation API", version="1.0.0")

# Local dev: allow the static frontend (served from any origin/file) to call this API.
# Tighten allow_origins to your actual frontend URL before deploying.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

NumberIn = Union[int, float, str]  # "3/2" strings are accepted for exact fractions


class OperationIn(BaseModel):
    op_type: RowOperationType
    row: int = Field(..., ge=1, description="1-indexed target row")
    row_b: Optional[int] = Field(None, ge=1, description="1-indexed second row")
    factor: Optional[NumberIn] = None


class SolveRequest(BaseModel):
    rows: int = Field(..., ge=1, le=MAX_DIMENSION)
    cols: int = Field(..., ge=1, le=MAX_DIMENSION)
    entries: List[List[NumberIn]]
    operations: List[OperationIn] = Field(..., max_items=MAX_OPERATIONS, min_items=1)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/limits")
def limits():
    return {"max_operations": MAX_OPERATIONS, "max_dimension": MAX_DIMENSION}


@app.post("/api/solve")
def solve(request: SolveRequest):
    try:
        matrix = Matrix.from_entries(request.rows, request.cols, request.entries)
        ops = [
            RowOperationRequest(op_type=o.op_type, row=o.row, row_b=o.row_b, factor=o.factor)
            for o in request.operations
        ]
        result = RowOperationEngine(matrix).run(ops)
        return result.to_dict()
    except MatrixError as e:
        raise HTTPException(status_code=400, detail=str(e))