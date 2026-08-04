test cases passed : 1/12
Score             : 0.0833
pass@1            : 0
E   assert 1.189106 <= 0.1
E    +  where 1.189106 = abs((0.595 - 1.784106))
_____________________________ test_height[TG-B-t4] _____________________________
/verifier/test_outputs.py:38: in test_height
    assert abs(got - ref) <= tol, f"{sid} @ {iso}: got {got:.4f} m, expected {ref:.4f} m (tol {tol} m)"
E   AssertionError: TG-B @ 2025-11-14T21:00:00Z: got 0.5950 m, expected 0.8607 m (tol 0.1 m)
E   assert 0.26572400000000007 <= 0.1
E    +  where 0.26572400000000007 = abs((0.595 - 0.860724))
_____________________________ test_height[TG-C-t1] _____________________________
/verifier/test_outputs.py:38: in test_height
    assert abs(got - ref) <= tol, f"{sid} @ {iso}: got {got:.4f} m, expected {ref:.4f} m (tol {tol} m)"
E   AssertionError: TG-C @ 2025-02-10T05:00:00Z: got 2.3230 m, expected -0.2583 m (tol 0.1 m)
E   assert 2.581298 <= 0.1
E    +  where 2.581298 = abs((2.323 - -0.258298))
_____________________________ test_height[TG-C-t2] _____________________________
/verifier/test_outputs.py:38: in test_height
    assert abs(got - ref) <= tol, f"{sid} @ {iso}: got {got:.4f} m, expected {ref:.4f} m (tol {tol} m)"
E   AssertionError: TG-C @ 2025-05-18T16:00:00Z: got 2.3230 m, expected 1.5441 m (tol 0.1 m)
E   assert 0.77891 <= 0.1
E    +  where 0.77891 = abs((2.323 - 1.54409))
_____________________________ test_height[TG-C-t4] _____________________________
/verifier/test_outputs.py:38: in test_height
    assert abs(got - ref) <= tol, f"{sid} @ {iso}: got {got:.4f} m, expected {ref:.4f} m (tol {tol} m)"
E   AssertionError: TG-C @ 2025-11-14T21:00:00Z: got 2.3230 m, expected 1.9210 m (tol 0.1 m)
E   assert 0.40203999999999995 <= 0.1
E    +  where 0.40203999999999995 = abs((2.323 - 1.92096))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_height[TG-A-t1] - AssertionError: TG-A @ 2025-02-10T05:00:00Z: ...
FAILED ::test_height[TG-A-t2] - AssertionError: TG-A @ 2025-05-18T16:00:00Z: ...
FAILED ::test_height[TG-A-t3] - AssertionError: TG-A @ 2025-08-22T09:00:00Z: ...
FAILED ::test_height[TG-A-t4] - AssertionError: TG-A @ 2025-11-14T21:00:00Z: ...
FAILED ::test_height[TG-B-t1] - AssertionError: TG-B @ 2025-02-10T05:00:00Z: ...
FAILED ::test_height[TG-B-t2] - AssertionError: TG-B @ 2025-05-18T16:00:00Z: ...
FAILED ::test_height[TG-B-t3] - AssertionError: TG-B @ 2025-08-22T09:00:00Z: ...
FAILED ::test_height[TG-B-t4] - AssertionError: TG-B @ 2025-11-14T21:00:00Z: ...
FAILED ::test_height[TG-C-t1] - AssertionError: TG-C @ 2025-02-10T05:00:00Z: ...
FAILED ::test_height[TG-C-t2] - AssertionError: TG-C @ 2025-05-18T16:00:00Z: ...
FAILED ::test_height[TG-C-t4] - AssertionError: TG-C @ 2025-11-14T21:00:00Z: ...
========================= 11 failed, 4 passed in 0.05s =========================
