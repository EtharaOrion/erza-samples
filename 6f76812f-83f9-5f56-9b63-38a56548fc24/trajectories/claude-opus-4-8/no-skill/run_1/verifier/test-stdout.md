test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E    +  where 10.197236290979049 = abs((27.99 - 17.79276370902095))
________________________ test_arc_mean_vtec[RX-3-SV-K] _________________________
/verifier/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-K: got 30.39000 TECU, expected 21.53369 TECU (tol 0.05000 TECU)
E   assert 8.856309774566206 <= 0.05
E    +  where 8.856309774566206 = abs((30.39 - 21.533690225433794))
________________________ test_arc_mean_vtec[RX-3-SV-M] _________________________
/verifier/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-M: got 35.85000 TECU, expected 36.22064 TECU (tol 0.05000 TECU)
E   assert 0.3706406931078945 <= 0.05
E    +  where 0.3706406931078945 = abs((35.85 - 36.220640693107896))
________________________ test_arc_mean_vtec[RX-3-SV-P] _________________________
/verifier/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-P: got 51.44000 TECU, expected 37.67497 TECU (tol 0.05000 TECU)
E   assert 13.765029660146638 <= 0.05
E    +  where 13.765029660146638 = abs((51.44 - 37.67497033985336))
________________________ test_arc_mean_vtec[RX-3-SV-T] _________________________
/verifier/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-T: got 30.04000 TECU, expected 20.63799 TECU (tol 0.05000 TECU)
E   assert 9.40201307670132 <= 0.05
E    +  where 9.40201307670132 = abs((30.04 - 20.63798692329868))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_arc_mean_vtec[RX-1-SV-K] - AssertionError: RX-1 SV-K: got 41.84...
FAILED ::test_arc_mean_vtec[RX-1-SV-P] - AssertionError: RX-1 SV-P: got 39.68...
FAILED ::test_arc_mean_vtec[RX-1-SV-R] - AssertionError: RX-1 SV-R: got 13.13...
FAILED ::test_arc_mean_vtec[RX-1-SV-W] - AssertionError: RX-1 SV-W: got 44.17...
FAILED ::test_arc_mean_vtec[RX-2-SV-M] - AssertionError: RX-2 SV-M: got 27.54...
FAILED ::test_arc_mean_vtec[RX-2-SV-R] - AssertionError: RX-2 SV-R: got 14.98...
FAILED ::test_arc_mean_vtec[RX-2-SV-T] - AssertionError: RX-2 SV-T: got 31.64...
FAILED ::test_arc_mean_vtec[RX-2-SV-W] - AssertionError: RX-2 SV-W: got 27.99...
FAILED ::test_arc_mean_vtec[RX-3-SV-K] - AssertionError: RX-3 SV-K: got 30.39...
FAILED ::test_arc_mean_vtec[RX-3-SV-M] - AssertionError: RX-3 SV-M: got 35.85...
FAILED ::test_arc_mean_vtec[RX-3-SV-P] - AssertionError: RX-3 SV-P: got 51.44...
FAILED ::test_arc_mean_vtec[RX-3-SV-T] - AssertionError: RX-3 SV-T: got 30.04...
========================= 12 failed, 4 passed in 0.45s =========================
