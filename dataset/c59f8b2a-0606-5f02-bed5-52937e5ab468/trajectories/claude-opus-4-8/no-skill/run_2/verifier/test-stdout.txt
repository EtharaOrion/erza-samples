test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E    +  where 26.545185449 = abs((87.5576 - 114.102785449))
____________________ test_phase_centre_correction[ANT-C-s1] ____________________
/verifier/test_outputs.py:78: in test_phase_centre_correction
    assert abs(got - ref) <= tol, \
E   AssertionError: ANT-C s1: got 80.820300 mm, expected 76.184665 mm (tol 0.0500 mm)
E   assert 4.635634750999998 <= 0.05
E    +  where 4.635634750999998 = abs((80.8203 - 76.184665249))
____________________ test_phase_centre_correction[ANT-C-s2] ____________________
/verifier/test_outputs.py:78: in test_phase_centre_correction
    assert abs(got - ref) <= tol, \
E   AssertionError: ANT-C s2: got 94.741700 mm, expected 89.556662 mm (tol 0.0500 mm)
E   assert 5.185038355999993 <= 0.05
E    +  where 5.185038355999993 = abs((94.7417 - 89.556661644))
____________________ test_phase_centre_correction[ANT-C-s3] ____________________
/verifier/test_outputs.py:78: in test_phase_centre_correction
    assert abs(got - ref) <= tol, \
E   AssertionError: ANT-C s3: got 101.074600 mm, expected 95.471622 mm (tol 0.0500 mm)
E   assert 5.602977840000008 <= 0.05
E    +  where 5.602977840000008 = abs((101.0746 - 95.47162216))
____________________ test_phase_centre_correction[ANT-C-s4] ____________________
/verifier/test_outputs.py:78: in test_phase_centre_correction
    assert abs(got - ref) <= tol, \
E   AssertionError: ANT-C s4: got 87.624100 mm, expected 80.233057 mm (tol 0.0500 mm)
E   assert 7.391042804999998 <= 0.05
E    +  where 7.391042804999998 = abs((87.6241 - 80.233057195))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_phase_centre_correction[ANT-A-s1] - AssertionError: ANT-A s1: g...
FAILED ::test_phase_centre_correction[ANT-A-s2] - AssertionError: ANT-A s2: g...
FAILED ::test_phase_centre_correction[ANT-A-s3] - AssertionError: ANT-A s3: g...
FAILED ::test_phase_centre_correction[ANT-A-s4] - AssertionError: ANT-A s4: g...
FAILED ::test_phase_centre_correction[ANT-B-s1] - AssertionError: ANT-B s1: g...
FAILED ::test_phase_centre_correction[ANT-B-s2] - AssertionError: ANT-B s2: g...
FAILED ::test_phase_centre_correction[ANT-B-s3] - AssertionError: ANT-B s3: g...
FAILED ::test_phase_centre_correction[ANT-B-s4] - AssertionError: ANT-B s4: g...
FAILED ::test_phase_centre_correction[ANT-C-s1] - AssertionError: ANT-C s1: g...
FAILED ::test_phase_centre_correction[ANT-C-s2] - AssertionError: ANT-C s2: g...
FAILED ::test_phase_centre_correction[ANT-C-s3] - AssertionError: ANT-C s3: g...
FAILED ::test_phase_centre_correction[ANT-C-s4] - AssertionError: ANT-C s4: g...
========================= 12 failed, 5 passed in 0.21s =========================
