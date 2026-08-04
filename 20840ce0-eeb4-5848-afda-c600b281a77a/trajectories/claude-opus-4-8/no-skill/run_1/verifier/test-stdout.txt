test cases passed : 24/31
Score             : 0.7742
pass@1            : 0
____________________ test_graded_case[R0002_amounts_55_270] ____________________
/tests/test_outputs.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_amounts_55_270: 16 of 18 field(s) decode back to the payee record - amount_H a payment amount field must be all digits, got ' PINEHURST F'; amount_J a payment amount field must be all digits, got 'ARMS COOPERA'
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((16.0 - 18.0))
___________ test_graded_case[R0002_reserved_and_first_name_271_327] ____________
/tests/test_outputs.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_reserved_and_first_name_271_327: 1 of 3 field(s) decode back to the payee record - blank_271_286 reserved positions carry 'TIVE            ', not blanks; first_payee_name_line decodes to 'AND MIDLAND GRAIN PARTNERS LLC', but the payee record carries 'PINEHURST FARMS COOPERATIVE'
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((1.0 - 3.0))
___________ test_graded_case[R0002_second_name_and_address_328_407] ____________
/tests/test_outputs.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0002_second_name_and_address_328_407: 1 of 2 field(s) decode back to the payee record - second_payee_name_line decodes to '', but the payee record carries 'AND MIDLAND GRAIN PARTNERS LLC'
E   assert 1.0 <= 0.5
E    +  where 1.0 = abs((1.0 - 2.0))
____________________ test_graded_case[R0003_amounts_55_270] ____________________
/tests/test_outputs.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_amounts_55_270: 16 of 18 field(s) decode back to the payee record - amount_H a payment amount field must be all digits, got ' OKEEFE DANI'; amount_J a payment amount field must be all digits, got 'EL J        '
E   assert 2.0 <= 0.5
E    +  where 2.0 = abs((16.0 - 18.0))
___________ test_graded_case[R0003_reserved_and_first_name_271_327] ____________
/tests/test_outputs.py:165: in test_graded_case
    assert abs(got - ref) <= tol, \
E   AssertionError: R0003_reserved_and_first_name_271_327: 2 of 3 field(s) decode back to the payee record - first_payee_name_line decodes to '', but the payee record carries 'OKEEFE DANIEL J'
E   assert 1.0 <= 0.5
E    +  where 1.0 = abs((2.0 - 3.0))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_graded_case[R0001_amounts_55_270] - AssertionError: R0001_amoun...
FAILED ::test_graded_case[R0001_reserved_and_first_name_271_327] - AssertionE...
FAILED ::test_graded_case[R0002_amounts_55_270] - AssertionError: R0002_amoun...
FAILED ::test_graded_case[R0002_reserved_and_first_name_271_327] - AssertionE...
FAILED ::test_graded_case[R0002_second_name_and_address_328_407] - AssertionE...
FAILED ::test_graded_case[R0003_amounts_55_270] - AssertionError: R0003_amoun...
FAILED ::test_graded_case[R0003_reserved_and_first_name_271_327] - AssertionE...
========================= 7 failed, 34 passed in 0.07s =========================
