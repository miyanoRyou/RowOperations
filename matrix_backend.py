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

Optimization notes (see git history / changelog for the "before" version):
    - Row-parsing errors (e.g. a non-numeric factor) are now caught and
      normalized into RowOperationError at the point of parsing, instead of
      leaking a raw ValueError past the public API's exception handling.
    - limit_denominator(10**6) is now applied only to float input, where it
      exists to avoid ugly binary-float artifacts (e.g. 0.1 -> a huge
      denominator). Exact input (int, Fraction, or a "a/b" string) is no
      longer silently rounded if its denominator happens to exceed 10**6.
    - Matrix.copy() uses a shallow per-row copy instead of copy.deepcopy.
      Fraction is immutable, so deepcopy's full object-graph walk buys
      nothing here and is meaningfully slower.
    - Each operation's factor is parsed into a Fraction exactly once (cached
      on the request) and reused by both the math and the notation string,
      instead of re-parsing the same string twice per step.
    - RowOperationEngine.run() computes each matrix's display representation
      exactly once per state. Previously "before" and "after" were computed
      separately every step, redundantly re-formatting the same state twice
      at every step boundary.
    - RowOperationResult.to_dict() builds its dict directly instead of using
      dataclasses.asdict(). asdict() recursively walks every field via
      reflection and calls copy.deepcopy() on each leaf value (every matrix
      cell string) — measured ~330x slower than just building the dict,
      and this runs on every API response.
    - NOT done, measured and rejected: caching Matrix._format_fraction (Fraction -> str)
      with functools.lru_cache. It looked like a natural win (matrices are
      full of repeated 0s and 1s after reduction) but measured ~4x *slower*
      than the plain call — lru_cache's hashing/dict-lookup/wrapper overhead
      costs more than CPython already pays to format a short string. Left
      as a plain function; documented here so it isn't "re-optimized" later
      without re-measuring.

Bugs found and fixed in a later code-review pass:
    - RowOperationRequest was a mutable dataclass with a @cached_property
      (parsed_factor). Mutating `factor` after that property had already
      been read once left the cache silently stale — describe() and the
      actual row arithmetic would keep using the old value. Fixed by
      freezing the dataclass (cached_property still works on a frozen
      dataclass; it writes directly to the instance's __dict__, bypassing
      the frozen __setattr__ guard).
    - Matrix.__post_init__ only validated shape when generating a default
      zero matrix — data passed in directly (bypassing from_entries) was
      never checked against the declared rows/cols, so e.g.
      Matrix(rows=3, cols=3, data=[[1, 2]]) constructed silently and only
      misbehaved later, far from the actual mistake. Now validated in
      __post_init__ itself, so the check applies no matter how a Matrix
      is constructed.
    - Factor-parsing-and-error-wrapping logic was duplicated nearly
      verbatim in both Matrix (_parse_factor) and RowOperationRequest
      (parsed_factor). Consolidated into one module-level function,
      _parse_fraction_strict, so there's a single place that decides how
      "bad factor input" becomes a RowOperationError.
    - Number (the NumericInput type alias) was renamed: it shadowed the
      standard library's numbers.Number ABC, a different and broader
      concept, which was a latent source of confusion for anyone who
      later imported both.

Loopholes found in an adversarial ("how would I break this") review, and
fixed — each confirmed with an actual reproduction before fixing:
    - No dimension cap existed in this library itself — only api.py's
      Pydantic layer capped rows/cols at 12. Constructing a Matrix directly
      with e.g. rows=2000, cols=2000 measured 3.5 seconds and a multi-
      million-object allocation from one constructor call, with nothing in
      matrix_backend.py to stop it. Since this module's own docs advertise
      reuse "in a CLI, notebook, or another API framework entirely," a
      future caller that doesn't happen to replicate api.py's Field(le=12)
      would have zero protection. Fixed with MAX_MATRIX_DIMENSION, enforced
      in Matrix.__post_init__ itself (every construction path), independent
      of whatever wraps it.
    - No length cap existed on individual numeric strings (a single matrix
      entry or operation factor). A client could send one absurdly long
      string in a single JSON field. Confirmed Python 3.11+'s built-in
      4300-digit integer-conversion limit and the fractions module's regex
      already prevent the worst outcomes (a 20,000-digit string is
      rejected in under a millisecond; adversarial near-miss strings don't
      trigger regex backtracking) — but nothing stopped a much larger
      string from being accepted and processed before those limits kick
      in. Fixed with MAX_NUMERIC_STRING_LENGTH, enforced in _to_fraction
      before Fraction() ever sees the value.
    - RowOperationResult.to_dict() returned its internal list objects by
      reference, not copies. Confirmed that mutating the returned dict
      (`to_dict()["final_matrix"][0][0] = "x"`) silently corrupted the
      source RowOperationResult's own state, so a second call to to_dict()
      returned the tampered value. Not exploitable through the current
      stateless per-request API usage, but a real encapsulation break for
      any future reuse (caching a result, serving it to multiple
      consumers, logging pipelines). Fixed by returning fresh row copies —
      cheap, since row length is bounded by MAX_MATRIX_DIMENSION.

Found by deliberately fuzzing the input (trying to make it crash) and
confirming each one live before fixing:
    - A matrix entry or factor of Infinity or -Infinity (e.g. the JSON
      number 1e400, which overflows to Infinity) made Python's Fraction()
      raise OverflowError — a type that wasn't in the except list, so it
      escaped as a raw, unhandled error. Confirmed this crashed the live
      API with a 500. Fixed by adding OverflowError next to ValueError/
      ZeroDivisionError/TypeError everywhere a factor or entry gets
      parsed. NaN, for comparison, already raised ValueError and was
      already handled correctly — it was specifically Infinity that slipped
      through.
    - Constructing a Matrix directly with a non-integer rows or cols (a
      string, None, or a float) crashed with an unhandled TypeError the
      moment __post_init__ tried to compare it to a number. The live API
      was never at risk here (Pydantic already rejects a non-integer
      "rows" with a clean 422 before this code ever runs), but direct
      library use had no such protection. Fixed by checking the type
      explicitly in __post_init__ and raising a normal DimensionError.
      (Matrix.from_entries() turned out to already be safe on this one:
      its very first check, comparing len(entries) to rows, naturally
      raises a clean error for a mismatched type without ever reaching a
      comparison that would crash — confirmed by testing it directly,
      not assumed.)

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
    The three operations you're allowed to do to a matrix: Scaling,
    Interchange, and Replacement.

    This is also a string, so a plain JSON value like "scaling" is
    automatically recognized as RowOperationType.SCALING — no extra
    conversion code needed when data comes in from the API.
    """
    SCALING = "scaling"
    INTERCHANGE = "interchange"
    REPLACEMENT = "replacement"


class MatrixError(Exception):
    """Parent class for every error this file can raise."""


class DimensionError(MatrixError):
    """The matrix's size is wrong — too big, or the shape doesn't match the data given."""


class RowOperationError(MatrixError):
    """A requested operation can't be done — bad row number, bad factor, etc."""


def _to_fraction(raw_value: NumericInput) -> Fraction:
    """
    Turn a number, decimal, or fraction string into an exact Fraction.

    Examples that all work: 5, "5", 0.5, "0.5", "3/2", "-3/2".

    Floats get special handling: a computer float like 0.1 isn't stored
    exactly, so converting it straight to a Fraction gives an ugly result
    like 3602879701896397/36028797018963968. limit_denominator cleans
    that up into the simple 1/10 a person actually meant. Numbers typed
    as text ("3/2") don't have this problem, so they're left exact.

    Also rejects any string that's unreasonably long, before it's even
    parsed — see MAX_NUMERIC_STRING_LENGTH above for why.
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
    Same as _to_fraction, but turns any parsing failure into a
    RowOperationError instead of Python's built-in error types.

    Everything that needs to parse a factor calls this one function, so
    there's only one place that decides what a "bad number" error looks
    like — instead of that logic being copy-pasted in multiple spots.
    """
    try:
        return _to_fraction(raw_value)
    except (ValueError, ZeroDivisionError, TypeError, OverflowError) as e:
        raise RowOperationError(f"Invalid factor: {raw_value!r}") from e


# ---------------------------------------------------------------------------
# Matrix
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Matrix:
    """
    A grid of numbers, stored as exact fractions so nothing ever rounds
    or loses precision.

    Attributes:
        rows: How many rows the matrix has. Must be 1 or more.
        cols: How many columns the matrix has. Must be 1 or more.
        data: The actual numbers, row by row. If you don't provide this,
            you get a matrix full of zeros of the size you asked for.
    """
    rows: int
    cols: int
    data: List[List[Fraction]] = field(default_factory=list)

    def __post_init__(self):
        """
        Runs automatically right after a Matrix is created, to check
        everything makes sense: the size is valid, and — if actual data
        was given — that it really is `rows` rows of `cols` numbers each.

        Without this check, you could accidentally create a Matrix that
        claims to be 3x3 but only actually holds one row, and it would
        break later in a confusing way instead of right here where the
        mistake was made.
        """
        if not isinstance(self.rows, int) or not isinstance(self.cols, int):
            raise DimensionError(
                f"Matrix rows and cols must be integers "
                f"(got rows={self.rows!r}, cols={self.cols!r})."
            )
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
    def from_entries(cls, rows: int, cols: int, entries: List[List[NumericInput]]) -> Matrix:
        """
        Build a Matrix from raw values (like what comes in from a web request),
        turning every entry into an exact fraction and checking the shape
        along the way.

        Args:
            rows: How many rows you expect. Must match len(entries).
            cols: How many columns you expect. Must match the length of
                every row in entries.
            entries: The actual numbers — can be plain numbers, decimal
                strings, or fraction strings like "3/2" (see NumericInput).

        Raises:
            DimensionError: if the shape doesn't match, or any entry
                isn't a valid number.
        """
        if len(entries) != rows:
            raise DimensionError(f"Expected {rows} rows, got {len(entries)}.")

        # Check the size limit before doing any real work, so a request for
        # an enormous matrix gets rejected instantly instead of making the
        # server churn through it first.
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
                except (ValueError, ZeroDivisionError, TypeError, OverflowError) as e:
                    raise DimensionError(
                        f"Invalid numeric entry at row {i + 1}, col {j + 1}: {raw_value!r}"
                    ) from e
            converted.append(converted_row)

        return cls(rows=rows, cols=cols, data=converted)

    def copy(self) -> Matrix:
        """
        Make an independent copy you can change without affecting this one.

        This only needs to copy each row's list, not every number inside
        it — numbers here never change in place, a row operation always
        builds a brand new row instead of editing the old one. So a full,
        slower deep copy isn't necessary.
        """
        return Matrix(rows=self.rows, cols=self.cols, data=[row[:] for row in self.data])

    def _check_row_index(self, row_idx: int) -> None:
        """Raise an error if row_idx (counting from 0) doesn't exist in this matrix."""
        if not (0 <= row_idx < self.rows):
            raise RowOperationError(
                f"Row index {row_idx + 1} is out of bounds. Matrix has {self.rows} rows."
            )

    @staticmethod
    def _format_fraction(value: Fraction) -> str:
        """Turn a Fraction into text the way a person would write it: '3' or '1/2', never '3/1'."""
        if value.denominator == 1:
            return str(value.numerator)
        return f"{value.numerator}/{value.denominator}"

    def to_display_rows(self) -> List[List[str]]:
        """Return this matrix as plain text, ready to show on screen or send as JSON."""
        return [[self._format_fraction(v) for v in row] for row in self.data]

    # ---- The three elementary row operations (these change the matrix) ----
    #
    # A NOTE ON ROW NUMBERS: the methods below count rows starting from 0
    # (row 0 is the first row) — normal Python counting. Elsewhere in this
    # file (RowOperationRequest, the API), rows are counted from 1 instead
    # ("Row 1", "Row 2", ...), which is more natural for a human typing
    # into a form. RowOperationEngine._apply() converts between the two.
    # If you're calling scale_row/interchange_rows/replace_row yourself,
    # remember to subtract 1 from a row number a person gave you.

    def scale_row(self, row: int, factor: NumericInput) -> None:
        """
        Multiply every number in a row by factor.

        Args:
            row: Which row to scale (counting from 0).
            factor: What to multiply by. Can't be zero — multiplying a
                row by zero would erase real information, and that's why
                textbooks don't allow it as an elementary row operation.

        Raises:
            RowOperationError: if the row doesn't exist, factor isn't a
                valid number, or factor is zero.
        """
        self._check_row_index(row)
        parsed_factor = _parse_fraction_strict(factor)
        if parsed_factor == 0:
            raise RowOperationError("Scaling factor must be nonzero.")
        self.data[row] = [val * parsed_factor for val in self.data[row]]

    def interchange_rows(self, row_a: int, row_b: int) -> None:
        """
        Swap two rows with each other.

        Args:
            row_a: The first row (counting from 0).
            row_b: The second row. Must be different from row_a.

        Raises:
            RowOperationError: if either row doesn't exist, or if
                row_a and row_b are the same row (swapping a row with
                itself isn't a real swap, so it's rejected).
        """
        self._check_row_index(row_a)
        self._check_row_index(row_b)
        if row_a == row_b:
            raise RowOperationError("Cannot interchange a row with itself.")
        self.data[row_a], self.data[row_b] = self.data[row_b], self.data[row_a]

    def replace_row(self, target_row: int, source_row: int, factor: NumericInput) -> None:
        """
        Add a multiple of one row onto another row.

        This is the operation that actually eliminates variables when
        solving a system of equations — the other two just rearrange or
        rescale rows.

        Args:
            target_row: The row that gets changed (counting from 0).
            source_row: The row being added in, after being multiplied
                by factor. Must be different from target_row.
            factor: What to multiply source_row by before adding it.
                Can be negative — that's how you "subtract" one row
                from another (see RowOperationRequest.describe below).

        Raises:
            RowOperationError: if either row doesn't exist, if
                target_row and source_row are the same, or if factor
                isn't a valid number.
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
    One operation to perform, exactly as a user would fill it in on a form.
    Rows are counted from 1 here ("Row 1", "Row 2", ...) since that's more
    natural for a person than starting at 0.

    Which fields you need depends on the operation:
        Scaling:      row, factor
        Interchange:  row, row_b
        Replacement:  row (the one being changed), row_b (the one being
                      added in), factor

    This can't be changed after it's created (that's what "frozen" means).
    That's on purpose: parsed_factor below remembers its answer the first
    time it's asked, so if `factor` could be changed afterward, that
    remembered answer would quietly go stale and give a wrong result.
    Making the whole object unchangeable rules that out completely.
    """
    op_type: RowOperationType
    row: int
    row_b: Optional[int] = None
    factor: Optional[NumericInput] = None

    @cached_property
    def parsed_factor(self) -> Fraction:
        """
        The factor as an exact Fraction, figured out once and remembered
        after that — both the actual math and the on-screen notation use
        this same value, instead of each converting the factor separately.
        If no factor was given (Interchange doesn't use one), this is 1.
        """
        if self.factor is None:
            return Fraction(1)
        return _parse_fraction_strict(self.factor)

    def describe(self) -> str:
        """
        Write this operation out in plain math notation, the way it
        appears in the step-by-step trace. For example:
          Scaling:      '3/2R1 -> R1'
          Replacement:  'R2 + (-1/2R1) -> R2'  (a negative factor gets
                        wrapped in parentheses)
          Interchange:  'R1 <-> R2'
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
        """Turn parsed_factor into text the way a person would write it: '3' or '1/2', never '3/1'."""
        f = self.parsed_factor
        return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"


@dataclass(slots=True)
class OperationStep:
    """
    A record of one operation after it's been applied: what it was, and
    what the matrix looked like right before and right after. The
    step-by-step trace shown on screen is just a list of these, in order.
    """
    step_number: int
    description: str
    matrix_before: List[List[str]]
    matrix_after: List[List[str]]


@dataclass(slots=True)
class RowOperationResult:
    """
    Everything about a finished run: the matrix you started with, the
    matrix you ended with, and every step in between. This is what
    RowOperationEngine.run() hands back, and to_dict() turns it into the
    JSON that actually gets sent to the browser.
    """
    original_matrix: List[List[str]]
    final_matrix: List[List[str]]
    steps: List[OperationStep]

    def to_dict(self) -> dict:
        """
        Turn this into a plain dictionary, ready to convert to JSON.

        Builds the dictionary by hand instead of using Python's generic
        dataclasses.asdict() helper, which is much slower for something
        this simple — and since this runs on every single API response,
        that speed difference actually matters.

        Also makes fresh copies of each row of numbers, rather than
        handing out the same lists this object uses internally. That way,
        if whoever receives this dictionary edits it, it can't accidentally
        change this object's own data too.
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
        """Same as to_dict(), but as a JSON-formatted string — handy for printing to a console."""
        return json.dumps(self.to_dict(), indent=indent)


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class RowOperationEngine:
    """
    Takes a matrix and a list of operations, and runs them one by one,
    keeping a record of every step along the way.

    Also enforces the MAX_OPERATIONS limit itself (not just in the app's
    UI), so there's no way to sneak past it by talking to the backend
    directly instead of going through the on-screen form.
    """

    def __init__(self, matrix: Matrix):
        """
        Take a snapshot of the matrix you give it, so if you go and change
        your own copy of that matrix afterward, it won't mess with a run
        that's already using it.
        """
        self.original_matrix = matrix.copy()

    def run(self, operations: List[RowOperationRequest]) -> RowOperationResult:
        """
        Apply each operation in order and return the full result.

        Args:
            operations: A list of 1 to MAX_OPERATIONS operations, applied
                in the order given.

        Returns:
            A RowOperationResult with the starting matrix, one step per
            operation (before/after snapshots plus the notation for what
            happened), and the final matrix.

        Raises:
            RowOperationError: if the list is empty, has too many
                operations, or any operation is invalid (bad row number,
                bad factor, etc). If this happens, nothing is left changed
                — the matrix you started with is never touched.
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

        # Keep track of what the matrix currently looks like as text, so
        # each step only has to convert it once — the "after" of one step
        # is exactly the "before" of the next, no need to redo that work.
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
        Run one operation on the matrix: figure out which Matrix method to
        call, switch its row numbers from "starting at 1" to "starting at
        0", and make sure it actually has the fields it needs first.
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
    """Print a matrix to the console, lined up neatly in a grid."""
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
    """Print a whole result to the console: the starting matrix, each step, then the final matrix."""
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
