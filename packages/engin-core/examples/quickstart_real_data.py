"""Quickstart: real production data to a calibrated forecast, end to end.

The worked example `D24` gates a visibility push on. It uses a **published
industrial dataset, not this project's simulator** -- 406 erythromycin batches
from a working plant, CC-BY-4.0.

Run:  python examples/quickstart_real_data.py

Needs the ``io`` extra (xarray, pandas, pint). Downloads 8 MB the first time and
caches it; the whole thing takes a couple of minutes, most of it fitting the GP.

Five steps, each of which is a thing the library is for:

    fetch with provenance -> infer the schema -> reshape to the convention
    -> fit and calibrate  -> read the honest interval

Nothing here is tuned to flatter the result. The last step prints a coverage
number and an R^2 side by side, and the R^2 is not good.
"""

from __future__ import annotations

import numpy as np

from engin_core.convention import validate_timeseries
from engin_core.datasets import describe, fetch, manifest_for
from engin_core.gp import fit_gp, split_conformal_multiplier
from engin_core.loaders import infer_columns, load_timeseries

DATASET = "erythromycin-efp"
TARGET = "hx"  # chemical potency; confirmed from the dataset authors' own code
NOMINAL = 0.90
CUTOFF_H = 72


def rule(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def main() -> None:
    import pandas as pd

    rule("1. Fetch real data, with its licence and provenance")
    print(describe(DATASET))
    (path,) = fetch(DATASET)
    record = manifest_for(path)
    print(f"\n  file      : {path.name} ({record.size_bytes:,} bytes)")
    print(f"  checksum  : verified={record.checksum_verified} (against the publisher's own md5)")
    print(f"  fetched   : {record.fetched_utc}")
    print(f"  licence   : {record.license_spdx} -- governs this file, not Engin's Apache-2.0")
    print("\n  A provenance manifest sits beside the file, so any number you compute")
    print("  from it can be traced to a specific byte sequence obtained on a given day.")

    rule("2. Look at the spreadsheet without pretending to understand it")
    df = pd.read_csv(path)
    print(f"  {df.shape[0]:,} rows x {df.shape[1]} columns\n")
    report = infer_columns(df)
    print(f"  {report.summary()}")
    print(f"  run column : {report.run_column}")
    print(f"  time column: {report.time_column}  (orientation: {report.orientation})\n")
    for guess in report.mapped:
        print(f"    {guess.source:<10} -> {guess.channel:<10} confidence {guess.confidence}")
    print(f"\n  {len(report.unmapped)} columns were not recognised, and are carried through")
    print("  under their original names rather than dropped or guessed at. This dataset's")
    print("  headers are unglossed abbreviations; the loader says so instead of inventing")
    print("  meanings for them.")

    rule("3. Reshape to the convention")
    # `hh` is an absolute process hour, not elapsed time: batches start between
    # hour 30 and 83. Align each to its own start before anything else.
    df = df.assign(elapsed_h=df.groupby("batch_id")["hh"].transform(lambda s: s - s.min()))

    ds, load_report = load_timeseries(df, run_column="batch_id", time_column="elapsed_h")
    print(f"  dims: {dict(ds.sizes)}  variables: {len(ds.data_vars)}")
    for note in load_report.notes:
        if note.level in ("error", "warning"):
            print(f"    [{note.level}] {note.message[:100]}")
    print(f"  {validate_timeseries(ds).summary()}")
    print("\n  Dimensions are (run, time) and units live in attrs. That is the whole")
    print("  convention -- an ordinary xarray Dataset another tool can read without Engin.")
    print("\n  Note this step is `load_timeseries`, not hand-rolled pandas. A first draft of")
    print("  this example did the reshape by hand and crashed: some batches repeat a")
    print("  (run, time) pair, which pandas will not put in an xarray index. The loader")
    print("  keeps the first of each and tells you it did.")

    rule("4. Forecast a batch's final potency from its first 72 hours")
    process = [c for c in df.columns if c not in ("date", "batch_id", "hh", "elapsed_h", TARGET)]
    rows, finals = [], []
    for _, batch in df.groupby("batch_id"):
        batch = batch.sort_values("elapsed_h")
        if batch["elapsed_h"].max() < CUTOFF_H + 2:
            continue
        window = batch[batch["elapsed_h"] <= CUTOFF_H]
        rows.append(window[process].mean().values)
        finals.append(float(batch[TARGET].iloc[-1]))

    X, y = np.asarray(rows, float), np.asarray(finals, float)
    keep = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X, y = X[keep], y[keep]
    lo, hi = X.min(0), X.max(0)
    U = (X - lo) / np.where(hi - lo > 0, hi - lo, 1.0)
    print(f"  {len(U)} batches, {U.shape[1]} process features each")

    rng = np.random.default_rng(0)
    idx = rng.permutation(len(U))
    n = len(idx)
    train, calib, test = idx[: int(0.6 * n)], idx[int(0.6 * n) : int(0.8 * n)], idx[int(0.8 * n) :]

    print("  fitting a GP (this is the slow part) ...")
    gp = fit_gp(U[train], y[train], seed=0)
    mc, sdc = gp.predict(U[calib], include_noise=True)
    q = split_conformal_multiplier(y[calib], mc, sdc, level=NOMINAL)
    print(f"  conformal multiplier at {NOMINAL:.0%}: {q:.3f}  (Gaussian would use 1.645)")

    rule("5. Read the forecast honestly")
    mean, sd = gp.predict(U[test], include_noise=True)
    lo_i, hi_i = mean - q * sd, mean + q * sd
    covered = (y[test] >= lo_i) & (y[test] <= hi_i)
    r2 = 1 - np.sum((mean - y[test]) ** 2) / np.sum((y[test] - y[test].mean()) ** 2)

    print(f"  {'batch':>6}{'actual':>10}{'forecast':>10}{'90% interval':>22}{'covered':>9}")
    for i in range(min(5, len(test))):
        interval = f"[{lo_i[i]:8.0f}, {hi_i[i]:8.0f}]"
        print(f"  {i:>6}{y[test][i]:>10.0f}{mean[i]:>10.0f}{interval:>22}{str(covered[i]):>9}")

    print(f"\n  empirical coverage : {covered.mean():.3f}   (nominal {NOMINAL})")
    print(f"  R^2                : {r2:.3f}")
    print(f"  mean interval width: {np.mean(2 * q * sd):.0f}")

    # One split of one seed, so this is noisy: with ~80 test batches the binomial
    # standard error on a coverage estimate is around 0.03. Quoting a single-split
    # number as *the* coverage would be the kind of overstatement this library is
    # supposed to argue against. The five-seed average is 0.886.
    print(
        f"\n  That coverage is one split of one seed on {len(test)} test batches, so it carries\n"
        "  roughly +/- 0.03 of binomial noise -- do not read the third decimal. Averaged\n"
        "  over five seeds it is 0.886 against a nominal 0.90; see\n"
        "  docs/methods/real-data-calibration.md for the full table.\n"
        "\n  What is solid: the intervals cover at close to their stated rate on data from a\n"
        "  plant this model has never seen. The calibration transfers.\n"
        "\n  What is not: the R^2 says the forecast inside those intervals is close to\n"
        "  uninformative. It is nearly predicting the mean, and the intervals are wide\n"
        "  enough to cover it anyway.\n"
        "\n  A model can be well calibrated and still not know much. That is why this\n"
        "  library reports both, and why coverage alone is not a claim of usefulness.\n"
        "  See docs/limitations.md."
    )


if __name__ == "__main__":
    main()
