"""
Trading Bot Model Architecture.

This module defines the neural network architecture for the US stock market trading bot.
The model combines multiple deep learning components:
- Bidirectional LSTM for sequential dependency modeling
- Dense layers for non-linear transformations

The model predicts next-period returns for US stocks.

Example:
    ```python
    from model import ModelConfig, build_model

    config = ModelConfig(window_size=60, n_features=15)
    model = build_model(config, use_custom_loss=True)
    ```

Author: Trading Bot Demo
Date: 2026
"""

from __future__ import annotations

from dataclasses import dataclass

import tensorflow as tf
from tensorflow.keras.layers import (  # pylint: disable=import-error
    LSTM,
    BatchNormalization,
    Bidirectional,
    Concatenate,
    Conv1D,
    Dense,
    Dropout,
    GlobalAveragePooling1D,
    Input,
    LayerNormalization,
    MultiHeadAttention,
    Normalization,
)
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers.schedules import ExponentialDecay


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for the trading model architecture.

    This dataclass holds all hyperparameters needed to construct the model.
    Using a dataclass ensures type safety and makes configuration management easier.

    Attributes:
        window_size: Number of time steps in the input sequence
        n_features: Number of input features per time step
        lstm_units: Number of LSTM units (split in half if bidirectional)
        num_heads: Number of attention heads in multi-head attention
        key_dim: Dimensionality of the query/key vectors in attention
        dropout: Dropout rate for regularization (applied to dense layers)
        recurrent_dropout: Dropout rate for LSTM recurrent connections
        learning_rate: Initial learning rate for the optimizer
        use_bidirectional: Whether to use bidirectional LSTM
        use_conv1d: Whether to use multi-scale Conv1D layers
        conv_filters: Number of filters in Conv1D layers
        kernel_size: Kernel size for Conv1D (base size, actual sizes are 3, 7, 15)
        dense_units: Number of units in dense layers
        use_residual: Whether to use residual connections in dense blocks

    Example:
        ```python
        config = ModelConfig(
            window_size=60,
            n_features=33,
            lstm_units=128,
            dropout=0.2,
            use_bidirectional=True
        )
        ```
    """

    window_size: int
    n_features: int
    lstm_units: int = 128
    num_heads: int = 8
    key_dim: int = 64
    dropout: float = 0.2
    recurrent_dropout: float = 0.15
    learning_rate: float = 5e-4
    use_bidirectional: bool = True
    use_conv1d: bool = True
    conv_filters: int = 64
    kernel_size: int = 3
    dense_units: int = 128
    use_residual: bool = True


def _directional_loss(y_true: tf.Tensor, y_pred: tf.Tensor) -> tf.Tensor:
    """Custom loss function that penalizes directional errors more heavily.

    This loss function combines mean squared error with an additional penalty
    for predicting the wrong direction (positive vs negative return). Directional
    accuracy is crucial for trading profitability, so mismatches are penalized 2x.

    The loss is computed as:
        loss = MSE + 2.0 * (direction_mismatch) * MSE

    Args:
        y_true: Ground truth returns (tensor of shape [batch_size, 1])
        y_pred: Predicted returns (tensor of shape [batch_size, 1])

    Returns:
        Scalar loss value for the batch

    Example:
        ```python
        model.compile(optimizer='adam', loss=_directional_loss)
        ```
    """
    mse = tf.keras.losses.mse(y_true, y_pred)
    # Direction agreement
    true_direction = tf.sign(y_true)
    pred_direction = tf.sign(y_pred)
    direction_match = tf.cast(tf.equal(true_direction, pred_direction), tf.float32)
    # Penalize direction mismatches 2x more
    direction_penalty = 2.0 * (1.0 - direction_match) * mse
    return mse + tf.reduce_mean(direction_penalty)


def build_model(cfg: ModelConfig, use_custom_loss: bool = False) -> tf.keras.Model:
    """Build a simplified, robust model for noisy financial data.

    This simplified architecture is designed specifically for stock market return prediction:
    - Single LSTM layer (removed over-engineered Conv1D and attention ensemble)
    - Reduced parameters to prevent overfitting
    - Optional sigmoid output for direction classification

    For noisy financial data like stock returns, simpler models often generalize
    better than complex architectures that overfit to noise patterns.

    Args:
        cfg: Model configuration specifying architecture hyperparameters
        use_custom_loss: If True, use directional loss; otherwise use MSE

    Returns:
        Compiled Keras model ready for training

    Architecture Flow:
        Input -> Normalization -> LSTM -> Dropout -> Dense -> Output
    """
    inputs = Input(shape=(cfg.window_size, cfg.n_features))

    # Normalization
    x = Normalization(axis=-1, name="norm")(inputs)

    # Simplified: Single LSTM layer (removed Conv1D and multi-head attention)
    # LSTM captures sequential dependencies without excessive complexity
    lstm_units = cfg.lstm_units // 2 if cfg.use_bidirectional else cfg.lstm_units

    if cfg.use_bidirectional:
        x = Bidirectional(
            LSTM(
                lstm_units,
                return_sequences=False,  # Direct to dense, no sequence output
                recurrent_dropout=min(
                    cfg.recurrent_dropout, 0.1
                ),  # Cap at 0.1 for stability
                dropout=cfg.dropout,
                kernel_initializer="glorot_uniform",
                recurrent_initializer="orthogonal",
            )
        )(x)
    else:
        x = LSTM(
            cfg.lstm_units,
            return_sequences=False,
            recurrent_dropout=min(cfg.recurrent_dropout, 0.1),
            dropout=cfg.dropout,
            kernel_initializer="glorot_uniform",
            recurrent_initializer="orthogonal",
        )(x)

    # BatchNorm for stability
    x = BatchNormalization()(x)
    x = Dropout(cfg.dropout)(x)

    # Single dense layer (removed 3-layer residual tower - overkill for this task)
    x = Dense(
        cfg.dense_units // 2,  # Reduced from cfg.dense_units
        activation="relu",
        kernel_initializer="he_normal",
        kernel_regularizer=tf.keras.regularizers.l2(1e-3),  # Increased regularization
    )(x)
    x = BatchNormalization()(x)
    x = Dropout(cfg.dropout)(x)

    # Single output (return prediction or direction probability)
    outputs = Dense(1, kernel_initializer="glorot_uniform")(x)
    model = Model(inputs, outputs)

    if use_custom_loss:
        loss_fn = _directional_loss
    else:
        loss_fn = "mse"

    model.compile(
        optimizer=tf.keras.optimizers.AdamW(
            learning_rate=ExponentialDecay(
                initial_learning_rate=cfg.learning_rate,
                decay_steps=100,
                decay_rate=0.95,
                staircase=True,
            ),
            weight_decay=1e-4,
            clipnorm=1.0,
        ),
        loss=loss_fn,
        metrics=[
            tf.keras.metrics.MeanAbsoluteError(name="mae"),
            tf.keras.metrics.RootMeanSquaredError(name="rmse"),
        ],
    )

    return model


def build_ensemble_models(cfg: ModelConfig, n_models: int = 5) -> list[tf.keras.Model]:
    """Build an ensemble of models with varied initializations.

    Ensemble methods improve prediction robustness by averaging multiple models
    trained with different random initializations. This function creates models
    with slight variations in dropout rates to increase diversity.

    Args:
        cfg: Base model configuration (will be varied slightly for each model)
        n_models: Number of models to create in the ensemble

    Returns:
        List of compiled Keras models with different initializations

    Usage:
        Ensemble predictions can be averaged for more robust forecasts:
        ```python
        models = build_ensemble_models(config, n_models=5)
        predictions = [model.predict(X) for model in models]
        ensemble_pred = np.mean(predictions, axis=0)
        ```

    Note:
        Each model in the ensemble has dropout varied by ±(i * 0.02) where i
        is the model index, providing diversity while maintaining similar capacity.
    """
    models = []
    for i in range(n_models):
        # Vary dropout slightly for diversity
        varied_cfg = ModelConfig(
            window_size=cfg.window_size,
            n_features=cfg.n_features,
            lstm_units=cfg.lstm_units,
            num_heads=cfg.num_heads,
            key_dim=cfg.key_dim,
            dropout=cfg.dropout + (i * 0.02),  # Slight variation
            recurrent_dropout=cfg.recurrent_dropout,
            learning_rate=cfg.learning_rate,
            use_bidirectional=cfg.use_bidirectional,
            use_conv1d=cfg.use_conv1d,
            conv_filters=cfg.conv_filters,
            kernel_size=cfg.kernel_size,
            dense_units=cfg.dense_units,
            use_residual=cfg.use_residual,
        )
        models.append(build_model(varied_cfg))
    return models
