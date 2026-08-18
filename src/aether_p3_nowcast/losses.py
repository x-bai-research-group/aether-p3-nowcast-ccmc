"""Normal-inverse-gamma likelihood and evidence regularization."""

from __future__ import annotations


def nig_components(normalized_log_density, nig_parameters):
    import tensorflow as tf

    normalized_log_density = tf.cast(
        tf.reshape(normalized_log_density, (-1,)), tf.float32
    )
    gamma, nu, alpha, beta = tf.unstack(
        tf.cast(nig_parameters, tf.float32), axis=-1
    )
    squared_residual = tf.square(normalized_log_density - gamma)
    negative_log_likelihood = (
        0.5 * tf.math.log(tf.constant(3.141592653589793, tf.float32) / nu)
        - alpha * tf.math.log(2.0 * beta * (1.0 + nu))
        + (alpha + 0.5)
        * tf.math.log(nu * squared_residual + 2.0 * beta * (1.0 + nu))
        + tf.math.lgamma(alpha)
        - tf.math.lgamma(alpha + 0.5)
    )
    evidence_penalty = tf.abs(normalized_log_density - gamma) * (2.0 * nu + alpha)
    return negative_log_likelihood, evidence_penalty


def make_nig_loss(coefficient: float):
    if coefficient < 0.0:
        raise ValueError("EDL coefficient must be non-negative")

    def loss(normalized_log_density, nig_parameters):
        import tensorflow as tf

        negative_log_likelihood, evidence_penalty = nig_components(
            normalized_log_density, nig_parameters
        )
        return tf.reduce_mean(
            negative_log_likelihood
            + tf.cast(coefficient, tf.float32) * evidence_penalty
        )

    loss.__name__ = f"nig_edl_{coefficient:g}"
    return loss
