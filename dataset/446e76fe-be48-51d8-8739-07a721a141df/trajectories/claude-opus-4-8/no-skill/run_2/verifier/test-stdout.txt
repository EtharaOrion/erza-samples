test cases passed : 0/1
Score             : 0.0000
pass@1            : 0
__________________________ test_not_the_velocity_form __________________________

derived = {'amp_mm': 962.9377577515166, 'ml': 5.217864227181392, 'r_km': 27.173831235215985}
cfg = {'attractor_gap_mw_minus_ml': 0.0321, 'attractor_gap_note': "This is now a RISK measure, not a lever. Under the predec...because the guardrail that detects a catalogue value reaching the answer needs its arithmetic to stay checkable.', ...}
ml = 4.39

    def test_not_the_velocity_form(derived, cfg, ml):
        """The dominant wrong path is named, not merely hoped against.
    
        The one-zero (velocity) WA understates ML by log10(2*pi*f) ~ 0.80 on this record,
        which is 2.65x tolerance — so this is implied by test_local_magnitude. It is stated
        separately so the failure message names the cause instead of just the distance.
        """
        wrong = math.log10(_wa_amplitude_mm() / (2 * math.pi * 0.9958)) + _log_a0(
            _hypocentral_km())
        tol = float(cfg["tolerance_ml_abs"])
>       assert abs(ml - wrong) > tol, (
            f"ML {ml:.3f} matches the ONE-ZERO Wood-Anderson value {wrong:.3f}. The WA "
            "responds to displacement and carries two zeros at the origin; one zero is the "
            "velocity form and understates the amplitude by |2*pi*f|.")
E       AssertionError: ML 4.390 matches the ONE-ZERO Wood-Anderson value 4.422. The WA responds to displacement and carries two zeros at the origin; one zero is the velocity form and understates the amplitude by |2*pi*f|.
E       assert 0.0315122368838372 > 0.3
E        +  where 0.0315122368838372 = abs((4.39 - 4.421512236883837))

/verifier/test_outputs.py:145: AssertionError
=============================== warnings summary ===============================
::test_wood_anderson_calibration
  /usr/local/lib/python3.11/site-packages/obspy/core/util/base.py:26: DeprecationWarning: pkg_resources is deprecated as an API. See https://setuptools.pypa.io/en/latest/pkg_resources.html
    import pkg_resources

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
==================================== PASSES ====================================
=========================== short test summary info ============================
PASSED ::test_wood_anderson_calibration
PASSED ::test_golden_matches_independent_recompute
PASSED ::test_plausible
PASSED ::test_isomorphic_invariance
FAILED ::test_local_magnitude - AssertionError: ML 4.390 off reference 5.218 ...
FAILED ::test_not_the_velocity_form - AssertionError: ML 4.390 matches the ON...
==================== 2 failed, 4 passed, 1 warning in 2.71s ====================
