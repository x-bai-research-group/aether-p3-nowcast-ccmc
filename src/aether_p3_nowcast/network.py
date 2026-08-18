"""The single joint density and uncertainty network used by AETHER-P3 Nowcast."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from . import MODEL_PARAMETER_COUNT
from .contract import SLICE_BY_NAME


@dataclass(frozen=True)
class NetworkConfig:
    routing_history_width: int = 72
    routing_short_width: int = 36
    short_width: int = 64
    long_width: int = 48
    solar_width: int = 32
    context_width: int = 64
    empirical_width: int = 32
    fusion_width: int = 192
    bottleneck_width: int = 128
    uncertainty_width: int = 64
    query_location_width: int = 32
    query_time_width: int = 32
    dropout: float = 0.05
    l2: float = 0.0

    def __post_init__(self) -> None:
        widths = (
            self.routing_history_width,
            self.routing_short_width,
            self.short_width,
            self.long_width,
            self.solar_width,
            self.context_width,
            self.empirical_width,
            self.fusion_width,
            self.bottleneck_width,
            self.uncertainty_width,
            self.query_location_width,
            self.query_time_width,
        )
        if any(
            isinstance(width, bool) or not isinstance(width, int) or width <= 0
            for width in widths
        ):
            raise ValueError("network widths must be positive integers")
        if not isfinite(self.dropout) or not 0.0 <= self.dropout < 1.0:
            raise ValueError("dropout must lie in [0, 1)")
        if not isfinite(self.l2) or self.l2 < 0.0:
            raise ValueError("l2 must be non-negative")


def _regularizer(tf, value: float):
    return None if value == 0.0 else tf.keras.regularizers.l2(value)


def _stop(tf, value, name: str):
    return tf.keras.layers.Lambda(
        tf.stop_gradient,
        output_shape=tuple(value.shape[1:]),
        name=name,
    )(value)


def build_model(config: NetworkConfig | None = None):
    """Build the fixed 342-input periodic space-time architecture."""
    import tensorflow as tf

    config = NetworkConfig() if config is None else config
    regularizer = _regularizer(tf, config.l2)
    inputs = {
        group_name: tf.keras.Input(
            shape=feature_slice.shape,
            name=group_name,
            dtype="float32",
        )
        for group_name, feature_slice in SLICE_BY_NAME.items()
    }

    solar_background = tf.keras.layers.Lambda(
        lambda value: tf.stack((value[:, 0], value[:, 1]), axis=1),
        output_shape=(2,),
        name="aether_solar_background_identity",
    )(inputs["solar_background"])

    # The 35 causal five-minute states are embedded in the exact 73-step
    # execution shape used to establish the final architecture.
    short_sequence = tf.keras.layers.Lambda(
        lambda value: tf.pad(
            tf.reverse(value, axis=(1,)),
            ((0, 0), (0, 38), (0, 0)),
        ),
        output_shape=(73, 6),
        name="aether_short_execution_shape",
    )(inputs["short_history"])
    upstream = tf.keras.layers.Lambda(
        lambda value: value[:, :, 2:5],
        output_shape=(73, 3),
        name="aether_upstream_input",
    )(short_sequence)
    geomagnetic = tf.keras.layers.Lambda(
        lambda value: tf.stack(
            (value[:, :, 0], value[:, :, 1], value[:, :, 5]),
            axis=-1,
        ),
        output_shape=(73, 3),
        name="aether_geomagnetic_input",
    )(short_sequence)

    solar_level = tf.keras.layers.Dense(
        config.solar_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_grouped_solar_dense_1",
    )(solar_background)
    solar_level = tf.keras.layers.Dense(
        config.solar_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_grouped_solar_dense_2",
    )(solar_level)

    def bidirectional(sequence, name: str):
        masked = tf.keras.layers.Masking(
            mask_value=0.0,
            name=f"{name}_mask",
        )(sequence)
        core = tf.keras.layers.LSTM(
            config.routing_history_width,
            dropout=config.dropout,
            kernel_regularizer=regularizer,
            recurrent_regularizer=regularizer,
            name=f"{name}_core",
        )
        return tf.keras.layers.Bidirectional(core, name=name)(masked)

    upstream_state = bidirectional(upstream, "aether_grouped_upstream_bilstm")
    geomagnetic_state = bidirectional(
        geomagnetic,
        "aether_grouped_geomagnetic_bilstm",
    )
    short_state = tf.keras.layers.Dense(
        2 * config.short_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_grouped_projection",
    )(
        tf.keras.layers.Concatenate(name="aether_grouped_fusion")(
            [
                solar_level,
                upstream_state,
                geomagnetic_state,
            ]
        )
    )

    long_order = tf.keras.layers.Lambda(
        lambda value: tf.reverse(value, axis=(1,)),
        output_shape=(45, 2),
        name="aether_long_chronological_order",
    )(inputs["long_history"])
    long_masked = tf.keras.layers.Masking(
        mask_value=0.0,
        name="aether_long_mask",
    )(long_order)
    long_state = tf.keras.layers.LSTM(
        config.long_width,
        dropout=config.dropout,
        go_backwards=True,
        kernel_regularizer=regularizer,
        recurrent_regularizer=regularizer,
        name="aether_long_encoder",
    )(long_masked)
    solar_masked = tf.keras.layers.Masking(
        mask_value=0.0,
        name="aether_solar_history_mask",
    )(inputs["solar_history"])
    solar_state = tf.keras.layers.LSTM(
        config.solar_width,
        dropout=config.dropout,
        go_backwards=True,
        kernel_regularizer=regularizer,
        recurrent_regularizer=regularizer,
        name="aether_solar_history_encoder",
    )(solar_masked)

    location_query = tf.keras.layers.Lambda(
        lambda value: value[:, 0:4],
        output_shape=(4,),
        name="aether_periodic_location_input",
    )(inputs["query"])
    location_state = tf.keras.layers.Dense(
        config.query_location_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_periodic_location_dense_1",
    )(location_query)
    location_state = tf.keras.layers.Dense(
        config.query_location_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_periodic_location_dense_2",
    )(location_state)
    time_query = tf.keras.layers.Lambda(
        lambda value: value[:, 4:10],
        output_shape=(6,),
        name="aether_periodic_time_input",
    )(inputs["query"])
    time_state = tf.keras.layers.Dense(
        config.query_time_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_periodic_time_dense_1",
    )(time_query)
    time_state = tf.keras.layers.Dense(
        config.query_time_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_periodic_time_dense_2",
    )(time_state)
    query_state = tf.keras.layers.Concatenate(
        name="aether_periodic_spacetime_fusion",
    )([location_state, time_state])
    query_state = tf.keras.layers.Dense(
        config.context_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_periodic_query_fusion_1",
    )(query_state)
    query_state = tf.keras.layers.Dense(
        config.context_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_periodic_query_fusion_2",
    )(query_state)

    empirical_state = tf.keras.layers.Dense(
        config.empirical_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_empirical_dense",
    )(inputs["empirical"])
    forcing_projection = tf.keras.layers.Dense(
        config.context_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_short_interaction_projection",
    )(short_state)
    query_projection = tf.keras.layers.Dense(
        config.context_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_query_interaction_projection",
    )(query_state)
    interaction = tf.keras.layers.Multiply(name="aether_location_interaction")(
        [
            forcing_projection,
            query_projection,
        ]
    )

    accuracy = tf.keras.layers.Concatenate(name="aether_accuracy_fusion")(
        [
            short_state,
            long_state,
            solar_state,
            query_state,
            empirical_state,
            interaction,
        ]
    )
    accuracy = tf.keras.layers.Dense(
        config.fusion_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_accuracy_dense",
    )(accuracy)
    accuracy = tf.keras.layers.LayerNormalization(name="aether_accuracy_norm")(accuracy)
    accuracy = tf.keras.layers.Dropout(
        config.dropout,
        name="aether_accuracy_dropout",
    )(accuracy)
    accuracy = tf.keras.layers.Dense(
        config.bottleneck_width,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_accuracy_bottleneck",
    )(accuracy)
    accuracy_state = tf.keras.layers.Dense(
        64,
        activation="swish",
        kernel_regularizer=regularizer,
        name="aether_accuracy_state",
    )(accuracy)
    gamma = tf.keras.layers.Dense(
        1,
        kernel_initializer="zeros",
        bias_initializer="zeros",
        dtype="float32",
        name="gamma_normalized",
    )(accuracy_state)

    # Evidence uses stopped-gradient copies of every physical group. The NIG
    # objective trains density and evidence jointly without allowing the
    # evidence branch to move the density representation backward.
    uq_upstream_input = tf.keras.layers.Masking(
        mask_value=0.0,
        name="aether_uq_upstream_mask",
    )(_stop(tf, upstream, "aether_uq_stop_upstream"))
    uq_geomagnetic_input = tf.keras.layers.Masking(
        mask_value=0.0,
        name="aether_uq_geomagnetic_mask",
    )(_stop(tf, geomagnetic, "aether_uq_stop_geomagnetic"))
    uq_upstream = tf.keras.layers.LSTM(
        config.routing_short_width,
        dropout=config.dropout,
        go_backwards=True,
        name="aether_uq_upstream_encoder",
    )(uq_upstream_input)
    uq_geomagnetic = tf.keras.layers.LSTM(
        config.routing_short_width,
        dropout=config.dropout,
        go_backwards=True,
        name="aether_uq_geomagnetic_encoder",
    )(uq_geomagnetic_input)
    uq_solar_level = tf.keras.layers.Dense(
        16,
        activation="swish",
        name="aether_uq_solar_level",
    )(_stop(tf, solar_background, "aether_uq_stop_solar_level"))
    uq_short = tf.keras.layers.Dense(
        config.uncertainty_width,
        activation="swish",
        name="aether_uq_short_state",
    )(
        tf.keras.layers.Concatenate(name="aether_uq_short_fusion")(
            [
                uq_solar_level,
                uq_upstream,
                uq_geomagnetic,
            ]
        )
    )
    uq_long_input = tf.keras.layers.Masking(
        mask_value=0.0,
        name="aether_uq_long_mask",
    )(_stop(tf, long_order, "aether_uq_stop_long"))
    uq_long = tf.keras.layers.LSTM(
        config.uncertainty_width // 2,
        dropout=config.dropout,
        go_backwards=True,
        name="aether_uq_long_encoder",
    )(uq_long_input)
    uq_solar_input = tf.keras.layers.Masking(
        mask_value=0.0,
        name="aether_uq_solar_mask",
    )(_stop(tf, inputs["solar_history"], "aether_uq_stop_solar"))
    uq_solar = tf.keras.layers.LSTM(
        config.uncertainty_width // 2,
        dropout=config.dropout,
        go_backwards=True,
        name="aether_uq_solar_encoder",
    )(uq_solar_input)
    uq_location = tf.keras.layers.Dense(
        config.uncertainty_width // 4,
        activation="swish",
        name="aether_uq_periodic_location",
    )(_stop(tf, location_query, "aether_uq_stop_periodic_location"))
    uq_time = tf.keras.layers.Dense(
        config.uncertainty_width // 4,
        activation="swish",
        name="aether_uq_periodic_time",
    )(_stop(tf, time_query, "aether_uq_stop_periodic_time"))
    uq_query = tf.keras.layers.Dense(
        config.uncertainty_width // 2,
        activation="swish",
        name="aether_uq_periodic_spacetime_fusion",
    )(
        tf.keras.layers.Concatenate(name="aether_uq_periodic_query_fusion")(
            [
                uq_location,
                uq_time,
            ]
        )
    )
    mean_summary = tf.keras.layers.Concatenate(name="aether_uq_mean_summary")(
        [
            gamma,
            inputs["empirical"],
        ]
    )
    uncertainty = tf.keras.layers.Concatenate(name="aether_uncertainty_fusion")(
        [
            uq_short,
            uq_long,
            uq_solar,
            uq_query,
            _stop(tf, accuracy_state, "aether_uq_stop_accuracy"),
            _stop(tf, mean_summary, "aether_uq_stop_mean_summary"),
        ]
    )
    uncertainty = tf.keras.layers.Dense(
        96,
        activation="swish",
        name="aether_uncertainty_dense_1",
    )(uncertainty)
    uncertainty = tf.keras.layers.LayerNormalization(
        name="aether_uncertainty_norm",
    )(uncertainty)
    uncertainty = tf.keras.layers.Dropout(
        config.dropout,
        name="aether_uncertainty_dropout",
    )(uncertainty)
    uncertainty = tf.keras.layers.Dense(
        config.uncertainty_width,
        activation="swish",
        name="aether_uncertainty_dense_2",
    )(uncertainty)
    raw = tf.keras.layers.Dense(3, dtype="float32", name="raw_evidence")(uncertainty)
    evidence = tf.keras.layers.Lambda(
        lambda value: tf.concat(
            [
                tf.nn.softplus(value[:, 0:1]) + 1.0e-6,
                tf.nn.softplus(value[:, 1:2]) + 1.0 + 1.0e-6,
                tf.nn.softplus(value[:, 2:3]) + 1.0e-6,
            ],
            axis=1,
        ),
        output_shape=(3,),
        dtype="float32",
        name="aether_evidence",
    )(raw)
    output = tf.keras.layers.Concatenate(
        dtype="float32",
        name="aether_normal_gamma_parameters",
    )([gamma, evidence])
    model = tf.keras.Model(
        inputs=inputs,
        outputs=output,
        name="aether_p3_nowcast",
    )
    if model.count_params() != MODEL_PARAMETER_COUNT:
        raise RuntimeError(
            f"AETHER-P3 Nowcast parameter count changed: {model.count_params()}"
        )
    return model
