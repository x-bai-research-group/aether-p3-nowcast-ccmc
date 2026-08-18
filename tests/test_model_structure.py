import numpy as np
import tensorflow as tf

from aether_p3_nowcast import MODEL_PARAMETER_COUNT
from aether_p3_nowcast.contract import SLICE_BY_NAME
from aether_p3_nowcast.network import NetworkConfig, build_model


def _zero_model_inputs(records=2):
    return {
        group_name: tf.zeros((records, *feature_slice.shape), tf.float32)
        for group_name, feature_slice in SLICE_BY_NAME.items()
    }


def test_joint_output_and_fixed_capacity():
    model = build_model(NetworkConfig())
    prediction = np.asarray(model(_zero_model_inputs(), training=False))
    assert model.count_params() == MODEL_PARAMETER_COUNT
    assert prediction.shape == (2, 4)
    assert np.all(prediction[:, 1] > 0.0)
    assert np.all(prediction[:, 2] > 1.0)
    assert np.all(prediction[:, 3] > 0.0)


def test_dateline_is_identical_by_construction():
    model = build_model(NetworkConfig())
    model_inputs = _zero_model_inputs(records=2)
    query = np.zeros((2, 10), np.float32)
    longitude = np.deg2rad(np.array([-180.0, 180.0]))
    query[:, 1] = np.sin(longitude)
    query[:, 2] = np.cos(longitude)
    model_inputs["query"] = tf.constant(query)
    prediction = np.asarray(model(model_inputs, training=False))
    np.testing.assert_allclose(prediction[0], prediction[1], atol=1.0e-6)
