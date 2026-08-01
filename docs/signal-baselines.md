# Population signal baselines

GitRoast does not claim that public GitHub activity can measure subjective code quality. The core score weights remain deterministic and documented.

This job grounds the **finding baselines** in the observed population of distinct, opted-in-for-audit public profiles. It records raw observable signals at audit time, requires 100 current-schema profiles, calculates directional quartiles, and writes a versioned inactive configuration. An administrator must explicitly activate a configuration before it can affect the ordering of audit findings.

Run the candidate job from the repository root:

```powershell
python scripts/recompute_signal_baselines.py
```

The API reports `distributional_calibration.status` as `collecting` until an active configuration exists. It never labels a score as objectively good, professionally reviewed, or human-calibrated.
