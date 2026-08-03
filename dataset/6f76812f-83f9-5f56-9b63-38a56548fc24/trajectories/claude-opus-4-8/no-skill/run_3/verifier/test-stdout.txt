test cases passed : 0/12
Score             : 0.0000
pass@1            : 0
E    +  where 10.199236290979051 = abs((27.992 - 17.79276370902095))
________________________ test_arc_mean_vtec[RX-3-SV-K] _________________________
/verifier/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-K: got 30.39400 TECU, expected 21.53369 TECU (tol 0.05000 TECU)
E   assert 8.860309774566204 <= 0.05
E    +  where 8.860309774566204 = abs((30.394 - 21.533690225433794))
________________________ test_arc_mean_vtec[RX-3-SV-M] _________________________
/verifier/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-M: got 35.84600 TECU, expected 36.22064 TECU (tol 0.05000 TECU)
E   assert 0.3746406931078994 <= 0.05
E    +  where 0.3746406931078994 = abs((35.846 - 36.220640693107896))
________________________ test_arc_mean_vtec[RX-3-SV-P] _________________________
/verifier/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-P: got 51.43800 TECU, expected 37.67497 TECU (tol 0.05000 TECU)
E   assert 13.763029660146643 <= 0.05
E    +  where 13.763029660146643 = abs((51.438 - 37.67497033985336))
________________________ test_arc_mean_vtec[RX-3-SV-T] _________________________
/verifier/test_outputs.py:93: in test_arc_mean_vtec
    assert abs(got - ref) <= tol, \
E   AssertionError: RX-3 SV-T: got 30.04100 TECU, expected 20.63799 TECU (tol 0.05000 TECU)
E   assert 9.40301307670132 <= 0.05
E    +  where 9.40301307670132 = abs((30.041 - 20.63798692329868))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_arc_mean_vtec[RX-1-SV-K] - AssertionError: RX-1 SV-K: got 41.84...
FAILED ::test_arc_mean_vtec[RX-1-SV-P] - AssertionError: RX-1 SV-P: got 39.68...
FAILED ::test_arc_mean_vtec[RX-1-SV-R] - AssertionError: RX-1 SV-R: got 13.12...
FAILED ::test_arc_mean_vtec[RX-1-SV-W] - AssertionError: RX-1 SV-W: got 44.17...
FAILED ::test_arc_mean_vtec[RX-2-SV-M] - AssertionError: RX-2 SV-M: got 27.54...
FAILED ::test_arc_mean_vtec[RX-2-SV-R] - AssertionError: RX-2 SV-R: got 14.98...
FAILED ::test_arc_mean_vtec[RX-2-SV-T] - AssertionError: RX-2 SV-T: got 31.64...
FAILED ::test_arc_mean_vtec[RX-2-SV-W] - AssertionError: RX-2 SV-W: got 27.99...
FAILED ::test_arc_mean_vtec[RX-3-SV-K] - AssertionError: RX-3 SV-K: got 30.39...
FAILED ::test_arc_mean_vtec[RX-3-SV-M] - AssertionError: RX-3 SV-M: got 35.84...
FAILED ::test_arc_mean_vtec[RX-3-SV-P] - AssertionError: RX-3 SV-P: got 51.43...
FAILED ::test_arc_mean_vtec[RX-3-SV-T] - AssertionError: RX-3 SV-T: got 30.04...
========================= 12 failed, 4 passed in 0.43s =========================
