# Generation notes

`generate_data.py` enumerates every ordinary partition of each public weight and
filters it independently by the two conditions in the Andrews--Bressoud
theorem. It asserts equality of the source and target counts before writing any
case. No unpublished or private data is used.

The four parameter pairs `(M,r) = (6,1), (6,2), (7,2), (7,3)` avoid the two
classical Rogers--Ramanujan cases `(5,1)` and `(5,2)`, for which bijective proofs
are known. The three separated weights expose 1,604 scored source objects while
keeping exhaustive regeneration inexpensive.
