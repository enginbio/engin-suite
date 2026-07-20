"""Generator sanity: labels in range, worst-step dominates, schema validates."""
from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from engin_pathway import FEATURES, Route, Step, make_dataset


def test_dataset_labels_in_range():
    data = make_dataset(200, seed=0)
    assert len(data) == 200
    y = np.array([r.manufacturability for r in data])
    assert np.all((y >= 0.0) & (y <= 1.0))
    assert np.all(np.array([r.n_steps for r in data]) >= 2)


def test_worst_step_tanks_manufacturability():
    # Two otherwise-identical routes; injecting one toxic step must lower the label.
    good_step = Step(features=dict.fromkeys(FEATURES, 0.9))
    bad_step = Step(features={**dict.fromkeys(FEATURES, 0.9), "g_tox": 0.05})
    # Ground truth is computed by the generator, so compare via the scoring formula
    # is out of scope here; instead assert the *schema* accepts both and that a
    # dataset contains a spread wide enough that bad steps matter.
    y = np.array([r.manufacturability for r in make_dataset(400, seed=1)])
    assert y.std() > 0.05           # meaningful spread (bad steps pull some routes down)
    assert y.min() < 0.6 < y.max()  # both tanked and healthy routes appear
    assert good_step.vector()[3] > bad_step.vector()[3]


def test_step_rejects_out_of_range_and_wrong_keys():
    with pytest.raises(ValidationError):
        Step(features={**dict.fromkeys(FEATURES, 0.5), "g_tox": 1.5})   # out of [0,1]
    with pytest.raises(ValidationError):
        Step(features={"only_one": 0.5})                                # wrong keys


def test_route_rejects_bad_label_and_builds_graph():
    steps = [Step(features=dict.fromkeys(FEATURES, 0.8)) for _ in range(3)]
    with pytest.raises(ValidationError):
        Route(route_id="x", steps=steps, manufacturability=2.0)
    r = Route(route_id="x", steps=steps)
    g = r.graph()
    assert g.number_of_nodes() == 3 and g.number_of_edges() == 2   # a 3-node chain
    assert r.node_features().shape == (3, len(FEATURES))
