test cases passed : 44/51
Score             : 0.8627
pass@1            : 0
E   assert 'flight_duty_period' == 'flight_time'
E     
E     - flight_time
E     + flight_duty_period
___________________ test_graded_case[P11-binding_margin_min] ___________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P11-binding_margin_min: got 11.000, expected -24.000 (tol 1.000)
E   assert 35.0 <= 1.0
E    +  where 35.0 = abs((11.0 - -24))
_____________________ test_graded_case[P12-fdp_margin_min] _____________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P12-fdp_margin_min: got 44.000, expected 14.000 (tol 1.000)
E   assert 30.0 <= 1.0
E    +  where 30.0 = abs((44.0 - 14))
_____________________ test_graded_case[P17-binding_limit] ______________________
/tests/test_outputs.py:99: in test_graded_case
    assert value.strip() == item["ref"], \
E   AssertionError: P17-binding_limit: got 'flight_duty_period', expected 'flight_time'
E   assert 'flight_duty_period' == 'flight_time'
E     
E     - flight_time
E     + flight_duty_period
___________________ test_graded_case[P17-binding_margin_min] ___________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P17-binding_margin_min: got 9.000, expected -14.000 (tol 1.000)
E   assert 23.0 <= 1.0
E    +  where 23.0 = abs((9.0 - -14))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_graded_case[P05-fdp_margin_min] - AssertionError: P05-fdp_margi...
FAILED ::test_graded_case[P05-binding_margin_min] - AssertionError: P05-bindi...
FAILED ::test_graded_case[P11-binding_limit] - AssertionError: P11-binding_li...
FAILED ::test_graded_case[P11-binding_margin_min] - AssertionError: P11-bindi...
FAILED ::test_graded_case[P12-fdp_margin_min] - AssertionError: P12-fdp_margi...
FAILED ::test_graded_case[P17-binding_limit] - AssertionError: P17-binding_li...
FAILED ::test_graded_case[P17-binding_margin_min] - AssertionError: P17-bindi...
========================= 7 failed, 54 passed in 0.08s =========================
