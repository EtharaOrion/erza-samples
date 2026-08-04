test cases passed : 48/51
Score             : 0.9412
pass@1            : 0
::test_graded_case[P17-binding_limit] PASSED                             [ 81%]
::test_graded_case[P17-binding_margin_min] PASSED                        [ 83%]
::test_frozen_reference_matches_independent_recompute PASSED             [ 85%]
::test_published_tables_are_intact PASSED                                [ 86%]
::test_two_row_bands_are_not_interchangeable PASSED                      [ 88%]
::test_plausibility_envelope PASSED                                      [ 90%]
::test_nearest_competitor_reproduces_no_graded_case PASSED               [ 91%]
::test_guess_resistance_and_decoy_freedom PASSED                         [ 93%]
::test_isomorphic_invariance_under_clock_relabel PASSED                  [ 95%]
::test_tolerances_bind_and_the_ledger_is_arithmetically_sound PASSED     [ 96%]
::test_degenerate_submissions_score_zero_without_crashing PASSED         [ 98%]
::test_roster_carries_no_compliance_label PASSED                         [100%]

=================================== FAILURES ===================================
_____________________ test_graded_case[P06-fdp_margin_min] _____________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P06-fdp_margin_min: got 168.000, expected -22.000 (tol 1.000)
E   assert 190.0 <= 1.0
E    +  where 190.0 = abs((168.0 - -22))
_____________________ test_graded_case[P06-binding_limit] ______________________
/tests/test_outputs.py:99: in test_graded_case
    assert value.strip() == item["ref"], \
E   AssertionError: P06-binding_limit: got 'rest_before_duty', expected 'flight_duty_period'
E   assert 'rest_before_duty' == 'flight_duty_period'
E     
E     - flight_duty_period
E     + rest_before_duty
___________________ test_graded_case[P06-binding_margin_min] ___________________
/tests/test_outputs.py:107: in test_graded_case
    assert abs(got - item["ref"]) <= item["tolerance"], \
E   AssertionError: P06-binding_margin_min: got 30.000, expected -22.000 (tol 1.000)
E   assert 52.0 <= 1.0
E    +  where 52.0 = abs((30.0 - -22))
---------------- generated xml file: /logs/verifier/results.xml ----------------
=========================== short test summary info ============================
FAILED ::test_graded_case[P06-fdp_margin_min] - AssertionError: P06-fdp_margi...
FAILED ::test_graded_case[P06-binding_limit] - AssertionError: P06-binding_li...
FAILED ::test_graded_case[P06-binding_margin_min] - AssertionError: P06-bindi...
========================= 3 failed, 58 passed in 0.06s =========================
