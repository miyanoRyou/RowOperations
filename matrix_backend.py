"""
matrix_backend.py

Backend engine for performing elementary row operations on matrices.

Designed to be consumed by any frontend layer (CLI, Flask, FastAPI, React, etc.)
Core responsibilities:
    1. Let a client define a matrix (dimensions + entries).
    2. Let a client request up to MAX_OPERATIONS row operations
       (Scaling, Interchange, Replacement).
    3. Apply them in order, recording a full step-by-step trace.
    4. Return the original matrix, each intermediate step, and the final result
       in a JSON-serializable shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from functools import cached_property
from typing import List, Union, Optional
import json


# Named NumericInput (not "Number") to avoid colliding with the standard
# library's numbers.Number ABC, which is a different, broader concept.
NumericInput = Union[int, float, Fraction, str]

MAX_OPERATIONS = 3

# Defense-in-depth limits enforced by the library itself, independent of
# whatever wraps it (api.py currently applies its own tighter le=12 cap on
# dimensions — that's a UI/product choice, not a safety backstop). Without
# a limit here, constructing a Matrix directly with e.g. rows=2000,
# cols=2000 measured 3.5s and a multi-million-object allocation from a
# single constructor call — trivially reachable by any future caller that
# imports this module directly and doesn't happen to replicate api.py's
# validation. 200x200 (40,000 cells) is already far beyond what this tool
# is for and still resolves in ~0.02s.
MAX_MATRIX_DIMENSION = 200

# A single numeric input (a matrix entry or an operation factor) longer
# than this is rejected before it ever reaches Fraction(). Nothing a human
# would plausibly type needs more than a few dozen characters; this exists
# purely to stop a client from sending a pathologically long string (e.g.
# megabytes of digits in one JSON field) and making the server spend time
# and memory on it before validation has a chance to reject it.
MAX_NUMERIC_STRING_LENGTH = 64


# ---------------------------------------------------------------------------
# Enums & Exceptions
# ---------------------------------------------------------------------------

class RowOperationType(str, Enum):
    """
    The three elementary row operations a client may request.

    Inherits from both str and Enum so that a plain JSON string like
    "scaling" compares equal to and validates against RowOperationType.SCALING
    — this is what lets FastAPI/Pydantic accept raw strings over the wire
    and match them straight to these members with no extra glue code.
    """
    SCALING = "scaling"
    INTERCHANGE = "interchange"
    REPLACEMENT = "replacement"


class MatrixError(Exception):
    """Base exception for all matrix-related errors."""


class DimensionError(MatrixError):
    """Raised when matrix dimensions are invalid or inconsistent with entries."""


class RowOperationError(MatrixError):
    """Raised when a requested row operation is invalid (bad index, bad factor, etc.)."""


def _to_fraction(raw_value: NumericInput) -> Fraction:
    """
    Convert a raw client value into an exact Fraction.

    limit_denominator is applied *only* to float input, where it exists to
    collapse binary-float artifacts (e.g. 0.1 -> Fraction(3602879701896397,
    36028797018963968)) into the nearest "nice" fraction a human plausibly
    meant. int, Fraction, and "a/b" string input are already exact and are
    left untouched, so a legitimately large denominator the user typed on
    purpose is never silently rounded away.

    String input longer than MAX_NUMERIC_STRING_LENGTH is rejected up
    front, before Fraction() ever sees it — see that constant's docstring
    for why.

    Raises whatever Fraction() itself raises (ValueError, ZeroDivisionError,
    TypeError) on unparseable input — callers are expected to catch and
    wrap these into a RowOperationError via _parse_fraction_strict below.
    """
    if isinstance(raw_value, str) and len(raw_value) > MAX_NUMERIC_STRING_LENGTH:
        raise ValueError(
            f"Numeric value is too long ({len(raw_value)} chars, "
            f"max {MAX_NUMERIC_STRING_LENGTH})."
        )
    if isinstance(raw_value, float):
        return Fraction(raw_value).limit_denominator(10**6)
    return Fraction(raw_value)


def _parse_fraction_strict(raw_value: NumericInput) -> Fraction:
    """
    Parse a raw client value into a Fraction, normalizing any failure into
    this library's own RowOperationError.

    This is the single place that turns "bad input" into "the right
    exception type." It used to be duplicated (once in Matrix, once in
    RowOperationRequest) with the same try/except in both places — that
    duplication is exactly how a future edit to one copy and not the other
    would have silently reintroduced the raw-ValueError-leak bug.
    """
    try:
        return _to_fraction(raw_value)
    except (ValueError, ZeroDivisionError, TypeError) as e:
        raise RowOperationError(f"Invalid factor: {raw_value!r}") from e


# ---------------------------------------------------------------------------
# Matrix
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Matrix:
    """
    A rectangular grid of exact Fraction values.

    This is the plain-data core the rest of the module operates on: it knows
    how to validate its own shape and mutate its rows, but nothing about
    HTTP, JSON, or the notion of a "request" — that lives in
    RowOperationRequest / RowOperationEngine instead.

    Attributes:
        rows: Number of rows. Must be a positive integer.
        cols: Number of columns. Must be a positive integer.
        data: The actual values, as rows of exact Fractions. If omitted,
            a rows x cols matrix of zeros is created automatically.
    """
    rows: int
    cols: int
    data: List[List[Fraction]] = field(default_factory=list)

    def __post_init__(self):
        """
        Validate dimensions and, if data was supplied directly (bypassing
        from_entries), validate that its shape actually matches rows/cols.

        Without this check, `Matrix(rows=3, cols=3, data=[[1, 2]])` would
        silently construct an object that *claims* to be 3x3 but only
        holds one row of two values — every downstream method (display,
        row operations, __str__) would then either misbehave or crash far
        from the actual mistake. from_entries() already validates shape
        for its own callers; this check closes the same gap for anyone
        constructing a Matrix directly.
        """
        if self.rows <= 0 or self.cols <= 0:
            raise DimensionError("Matrix dimensions must be positive integers.")
        if self.rows > MAX_MATRIX_DIMENSION or self.cols > MAX_MATRIX_DIMENSION:
            raise DimensionError(
                f"Matrix dimensions cannot exceed {MAX_MATRIX_DIMENSION} "
                f"(got {self.rows} rows x {self.cols} cols)."
            )

        if not self.data:
            self.data = [[Fraction(0) for _ in range(self.cols)] for _ in range(self.rows)]
            return

        if len(self.data) != self.rows:
            raise DimensionError(
                f"Matrix declared {self.rows} rows but data has {len(self.data)}."
            )
        for i, row in enumerate(self.data):
            if len(row) != self.cols:
                raise DimensionError(
                    f"Matrix declared {self.cols} cols but row {i + 1} has {len(row)}."
                )

    @classmethod
    def from_entries(cls, rows: int, cols: int, entries: List[List[NumericInput]]) -> "Matrix":
        """
        Build a Matrix from raw client input, converting every entry to an
        exact Fraction and validating shape along the way.

        Args:
            rows: Expected number of rows; must match len(entries).
            cols: Expected number of columns; must match the length of
                every row in entries.
            entries: The raw values as given by the client — ints, floats,
                "a/b" fraction strings, decimal strings, or Fraction
                objects are all accepted (see NumericInput).

        Raises:
            DimensionError: if the shape doesn't match, or if any entry
                can't be converted to a number.
        """
        if len(entries) != rows:
            raise DimensionError(f"Expected {rows} rows, got {len(entries)}.")

        # Checked here too (not just in __post_init__): rejecting an
        # oversized request before touching any of its cells means a
        # client can't force this loop to do real work just by asking for
        # a huge matrix — the cost of saying "no" stays O(1) either way.
        if rows > MAX_MATRIX_DIMENSION or cols > MAX_MATRIX_DIMENSION:
            raise DimensionError(
                f"Matrix dimensions cannot exceed {MAX_MATRIX_DIMENSION} "
                f"(got {rows} rows x {cols} cols)."
            )

        converted: List[List[Fraction]] = []
        for i, row in enumerate(entries):
            if len(row) != cols:
                raise DimensionError(
                    f"Row {i + 1} has {len(row)} entries, expected {cols}."
                )
            converted_row = []
            for j, raw_value in enumerate(row):
                try:
                    converted_row.append(_to_fraction(raw_value))
                except (ValueError, ZeroDivisionError, TypeError) as e:
                    raise DimensionError(
                        f"Invalid numeric entry at row {i + 1}, col {j + 1}: {raw_value!r}"
                    ) from e
            converted.append(converted_row)

        return cls(rows=rows, cols=cols, data=converted)

    def copy(self) -> "Matrix":
        """
        Return an independent copy that can be mutated without affecting
        this instance.

        Uses a shallow per-row copy rather than copy.deepcopy: Fraction is
        immutable, so nothing below the row-list level ever needs its own
        copy — deepcopy's full object-graph walk would just be paying for
        safety this data doesn't need. Row operations always assign a
        *new* list to a row (see scale_row/replace_row below) rather than
        mutating an existing row's contents in place, which is what makes
        this shallow copy safe.
        """
        return Matrix(rows=self.rows, cols=self.cols, data=[row[:] for row in self.data])

    def _check_row_index(self, row_idx: int) -> None:
        """Raise RowOperationError if row_idx (0-indexed) is out of bounds."""
        if not (0 <= row_idx < self.rows):
            raise RowOperationError(
                f"Row index {row_idx + 1} is out of bounds. Matrix has {self.rows} rows."
            )

    @staticmethod
    def _format_fraction(value: Fraction) -> str:
        """Render a Fraction the way a human would write it: '3' or '1/2', never '3/1'."""
        if value.denominator == 1:
            return str(value.numerator)
        return f"{value.numerator}/{value.denominator}"

    def to_display_rows(self) -> List[List[str]]:
        """Return a JSON/human-friendly snapshot: every Fraction rendered as a string."""
        return [[self._format_fraction(v) for v in row] for row in self.data]

    def __str__(self) -> str:
        """Render the matrix as an aligned ASCII grid, e.g. for CLI/debug output."""
        display = self.to_display_rows()
        widths = [max(len(display[r][c]) for r in range(self.rows)) for c in range(self.cols)]
        lines = []
        for row in display:
            padded = [val.rjust(widths[c]) for c, val in enumerate(row)]
            lines.append("[ " + "  ".join(padded) + " ]")
        return "\n".join(lines)

    # ---- Elementary Row Operations (mutate in place) ----
    #
    # NOTE ON INDEXING: every method below takes 0-indexed row positions
    # (standard Python indexing: row 0 is the first row), NOT the 1-indexed
    # "Row 1, Row 2, ..." convention used at the RowOperationRequest/API
    # layer. RowOperationEngine._apply() is what converts between the two;
    # if you're calling these methods directly (e.g. from a notebook or
    # another framework), remember to subtract 1 from a human-facing row
    # number yourself.

    def scale_row(self, row: int, factor: NumericInput) -> None:
        """
        Scaling: R_row -> factor * R_row.

        Args:
            row: 0-indexed row to scale.
            factor: Nonzero multiplier. Any NumericInput is accepted and
                parsed to an exact Fraction.

        Raises:
            RowOperationError: if row is out of bounds, factor can't be
                parsed, or factor is zero (scaling by zero would destroy
                information and isn't a valid elementary row operation).
        """
        self._check_row_index(row)
        parsed_factor = _parse_fraction_strict(factor)
        if parsed_factor == 0:
            raise RowOperationError("Scaling factor must be nonzero.")
        self.data[row] = [val * parsed_factor for val in self.data[row]]

    def interchange_rows(self, row_a: int, row_b: int) -> None:
        """
        Interchange: R_row_a <-> R_row_b.

        Args:
            row_a: 0-indexed first row.
            row_b: 0-indexed second row. Must differ from row_a.

        Raises:
            RowOperationError: if either index is out of bounds, or if
                row_a and row_b are the same row (a no-op that almost
                certainly indicates a mistake upstream, so it's rejected
                rather than silently accepted).
        """
        self._check_row_index(row_a)
        self._check_row_index(row_b)
        if row_a == row_b:
            raise RowOperationError("Cannot interchange a row with itself.")
        self.data[row_a], self.data[row_b] = self.data[row_b], self.data[row_a]

    def replace_row(self, target_row: int, source_row: int, factor: NumericInput) -> None:
        """
        Replacement: R_target -> R_target + factor * R_source.

        This is the only one of the three elementary operations that
        actually combines two rows, and it's the one that does the real
        work of eliminating variables during row reduction.

        Args:
            target_row: 0-indexed row being replaced.
            source_row: 0-indexed row being added in (scaled by factor).
                Must differ from target_row.
            factor: Multiplier applied to source_row before adding. May be
                any NumericInput, including negative values (a negative
                factor is what makes this "subtraction" — see
                RowOperationRequest.describe for the notation).

        Raises:
            RowOperationError: if either index is out of bounds, if
                target_row equals source_row, or if factor can't be parsed.
        """
        self._check_row_index(target_row)
        self._check_row_index(source_row)
        if target_row == source_row:
            raise RowOperationError("Target and source row must be different for replacement.")
        parsed_factor = _parse_fraction_strict(factor)
        self.data[target_row] = [
            t + parsed_factor * s for t, s in zip(self.data[target_row], self.data[source_row])
        ]


# ---------------------------------------------------------------------------
# Operation request / step / result models
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RowOperationRequest:
    """
    A single row-operation instruction, as a client (UI/API) would submit it.
    Rows are 1-indexed for user-friendliness (Row 1, Row 2, ...).

    Field usage by op_type:
        SCALING:      row, factor
        INTERCHANGE:  row, row_b
        REPLACEMENT:  row (target), row_b (source), factor

    Frozen deliberately: parsed_factor below is a @cached_property, and a
    cached_property on a *mutable* object is a correctness trap — mutate
    `factor` after the cache has been populated once, and every subsequent
    read silently keeps returning the stale, pre-mutation value. Freezing
    makes that mistake impossible instead of relying on callers to just not
    make it. (cached_property still works here: it writes straight into
    the instance's __dict__, which bypasses the frozen dataclass's
    __setattr__ guard — this is safe, standard behavior, not a workaround.)
    """
    op_type: RowOperationType
    row: int
    row_b: Optional[int] = None
    factor: Optional[NumericInput] = None

    @cached_property
    def parsed_factor(self) -> Fraction:
        """
        The factor parsed into a Fraction exactly once, then reused by both
        the actual row arithmetic (via the engine) and the notation string
        in describe(). Previously the same factor string was parsed twice
        per operation (once for math, once for display). Defaults to 1
        when no factor was given (Interchange doesn't use one).
        """
        if self.factor is None:
            return Fraction(1)
        return _parse_fraction_strict(self.factor)

    def describe(self) -> str:
        """
        Render this operation in compact math notation for the step trace,
        e.g. '3/2R1 -> R1' (scaling) or 'R2 + (-1/2R1) -> R2' (replacement,
        negative coefficient parenthesized). Interchange renders as a plain
        swap: 'R1 <-> R2'.
        """
        r = self.row
        if self.op_type == RowOperationType.SCALING:
            return f"{self._format_factor()}R{r} -> R{r}"
        if self.op_type == RowOperationType.INTERCHANGE:
            return f"R{r} <-> R{self.row_b}"
        if self.op_type == RowOperationType.REPLACEMENT:
            coef = self._format_factor()
            term = f"{coef}R{self.row_b}"
            term = f"({term})" if coef.startswith("-") else term
            return f"R{r} + {term} -> R{r}"
        return "Unknown operation"

    def _format_factor(self) -> str:
        """Render parsed_factor the way a human would write it: '3' or '1/2', never '3/1'."""
        f = self.parsed_factor
        return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


@dataclass(slots=True)
class OperationStep:
    """
    A record of one applied operation: what it was, and the matrix state
    immediately before and after it ran. This is the unit the frontend's
    step-by-step trace is built from — one of these per operation, in order.
    """
    step_number: int
    description: str
    matrix_before: List[List[str]]
    matrix_after: List[List[str]]


@dataclass(slots=True)
class RowOperationResult:
    """
    The full outcome of running a sequence of row operations: the starting
    matrix, the final matrix, and every intermediate step in between. This
    is the top-level object RowOperationEngine.run() returns, and to_dict()
    is what api.py serializes straight into the HTTP response body.
    """
    original_matrix: List[List[str]]
    final_matrix: List[List[str]]
    steps: List[OperationStep]

    def to_dict(self) -> dict:
        """
        Convert to a plain JSON-serializable dict.

        Deliberately hand-written rather than dataclasses.asdict(): asdict()
        recursively walks every field via reflection and calls
        copy.deepcopy() on each leaf value (i.e. every matrix cell string,
        one at a time). That generality is unneeded for this fixed, shallow
        shape, and building the dict directly measured ~330x faster —
        which matters since this runs on every API response.

        Returns fresh row lists (not the same list objects this result
        holds internally): matrix rows are small (capped by
        MAX_MATRIX_DIMENSION), so the copy is cheap, and it closes off a
        real aliasing hole — without it, a caller doing
        `to_dict()['final_matrix'][0][0] = "x"` would silently mutate this
        object's own state, corrupting the value any *other* caller (or a
        second call to to_dict()) would see afterward.
        """
        return {
            "original_matrix": [row[:] for row in self.original_matrix],
            "final_matrix": [row[:] for row in self.final_matrix],
            "steps": [
                {
                    "step_number": s.step_number,
                    "description": s.description,
                    "matrix_before": [row[:] for row in s.matrix_before],
                    "matrix_after": [row[:] for row in s.matrix_after],
                }
                for s in self.steps
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convenience wrapper: to_dict() serialized to a JSON string (e.g. for CLI output)."""
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RowOperationEngine:
    """
    Applies a bounded sequence (<= MAX_OPERATIONS) of elementary row operations
    to a matrix and records a full step-by-step trace.

    The cap is enforced here (not just in the UI) so it can't be bypassed by
    a client sending a longer list directly to the backend.
    """

    def __init__(self, matrix: Matrix):
        """
        Snapshot the given matrix so later mutation of the caller's own
        Matrix object (outside this engine) can't retroactively change
        what "the original matrix" was for a run already in progress.
        """
        self.original_matrix = matrix.copy()

    def run(self, operations: List[RowOperationRequest]) -> RowOperationResult:
        """
        Apply a sequence of row operations in order and return the full trace.

        Args:
            operations: 1 to MAX_OPERATIONS RowOperationRequest instances,
                applied in the given order.

        Returns:
            A RowOperationResult holding the untouched original matrix,
            one OperationStep per operation (with before/after snapshots
            and human-readable notation), and the final matrix.

        Raises:
            RowOperationError: if the operation list is empty, exceeds
                MAX_OPERATIONS, or any individual operation is invalid
                (bad row index, bad factor, etc.) — raised as soon as the
                first invalid operation is reached, leaving this engine's
                own state untouched (a fresh working copy is discarded on
                error; self.original_matrix is never mutated).
        """
        if not operations:
            raise RowOperationError("At least one row operation must be provided.")
        if len(operations) > MAX_OPERATIONS:
            raise RowOperationError(
                f"A maximum of {MAX_OPERATIONS} row operations is allowed per request "
                f"(received {len(operations)})."
            )

        working = self.original_matrix.copy()
        steps: List[OperationStep] = []

        # Each matrix state is formatted exactly once. Previously "before"
        # and "after" were each recomputed via to_display_rows() every step,
        # redundantly re-formatting the *same* state twice at every step
        # boundary (step i's "after" is byte-for-byte step i+1's "before").
        current_display = self.original_matrix.to_display_rows()

        for i, op in enumerate(operations, start=1):
            before = current_display
            self._apply(working, op)
            current_display = working.to_display_rows()
            steps.append(
                OperationStep(
                    step_number=i,
                    description=op.describe(),
                    matrix_before=before,
                    matrix_after=current_display,
                )
            )

        return RowOperationResult(
            original_matrix=self.original_matrix.to_display_rows(),
            final_matrix=current_display,
            steps=steps,
        )

    @staticmethod
    def _apply(matrix: Matrix, op: RowOperationRequest) -> None:
        """
        Dispatch one RowOperationRequest to the matching Matrix method,
        converting the request's 1-indexed rows (Row 1, Row 2, ...) to the
        0-indexed positions Matrix's methods expect, and checking that each
        op_type actually has the fields it needs before calling into it.
        """
        row_idx = op.row - 1
        row_b_idx = op.row_b - 1 if op.row_b is not None else None

        if op.op_type == RowOperationType.SCALING:
            if op.factor is None:
                raise RowOperationError("Scaling requires a 'factor'.")
            matrix.scale_row(row_idx, op.parsed_factor)

        elif op.op_type == RowOperationType.INTERCHANGE:
            if row_b_idx is None:
                raise RowOperationError("Interchange requires a second row ('row_b').")
            matrix.interchange_rows(row_idx, row_b_idx)

        elif op.op_type == RowOperationType.REPLACEMENT:
            if row_b_idx is None or op.factor is None:
                raise RowOperationError("Replacement requires 'row_b' and 'factor'.")
            matrix.replace_row(row_idx, row_b_idx, op.parsed_factor)

        else:
            raise RowOperationError(f"Unsupported operation type: {op.op_type}")


# ---------------------------------------------------------------------------
# CLI / console pretty-printing (a real API would just return result.to_json())
# ---------------------------------------------------------------------------

def print_matrix(display_rows: List[List[str]], label: str = "") -> None:
    """Print a matrix (already in to_display_rows() form) as an aligned ASCII grid."""
    if label:
        print(label)
    widths = [
        max(len(display_rows[r][c]) for r in range(len(display_rows)))
        for c in range(len(display_rows[0]))
    ]
    for row in display_rows:
        padded = [val.rjust(widths[c]) for c, val in enumerate(row)]
        print("[ " + "  ".join(padded) + " ]")
    print()


def print_result(result: RowOperationResult) -> None:
    """Print a full RowOperationResult to the console: original -> each step -> final."""
    print_matrix(result.original_matrix, "Original Matrix:")
    for step in result.steps:
        print(f"Step {step.step_number}: {step.description}")
        print_matrix(step.matrix_after, "  Result:")
    print_matrix(result.final_matrix, "Final Matrix:")


# ---------------------------------------------------------------------------
# Demo: mimics what a frontend/API request body would look like
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 1. Client sets dimensions + entries
    matrix = Matrix.from_entries(
        rows=3, cols=4,
        entries=[
            [2, 1, -1, 8],
            [-3, -1, 2, -11],
            [-2, 1, 2, -3],
        ],
    )

    # 2. Client selects up to 3 row operations (this is what a POST body would carry)
    operations = [
        RowOperationRequest(RowOperationType.REPLACEMENT, row=2, row_b=1, factor=Fraction(3, 2)),
        RowOperationRequest(RowOperationType.REPLACEMENT, row=3, row_b=1, factor=1),
        RowOperationRequest(RowOperationType.SCALING, row=2, factor=2),
    ]

    # 3 & 4. Run + get step-by-step trace + final matrix
    engine = RowOperationEngine(matrix)
    result = engine.run(operations)

    print_result(result)

    print("--- JSON output (what an API endpoint would return) ---")
    print(result.to_json())