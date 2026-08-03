SCALE_RAW: got=0.250368 ref=0.250368 err=0.000000 tol=0.004 -> OK
ZETA_RAW:  got=1.690145 ref=1.690145 err=0.000000 tol=0.03 -> OK
============================= test session starts ==============================
platform linux -- Python 3.11.15, pytest-8.3.2, pluggy-1.6.0 -- /usr/local/bin/python3.11
rootdir: /root
configfile: ../dev/null
plugins: json-ctrf-0.3.5
collecting ... collected 4 items

::test_plausible PASSED                                                  [ 25%]
::test_robust_scale PASSED                                               [ 50%]
::test_zeta_prime PASSED                                                 [ 75%]
::test_isomorphic_invariance PASSED                                      [100%]

==================================== PASSES ====================================
=========================== short test summary info ============================
PASSED ::test_plausible
PASSED ::test_robust_scale
PASSED ::test_zeta_prime
PASSED ::test_isomorphic_invariance
============================== 4 passed in 0.02s ===============================
