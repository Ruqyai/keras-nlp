# Copyright 2022 The KerasNLP Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for Transformer Encoder."""

import os
import tempfile

import tensorflow as tf

from keras_nlp.layers import transformer_encoder


class TransformerEncoderTest(tf.test.TestCase):
    def test_valid_call(self):
        encoder = transformer_encoder.TransformerEncoder(
            intermediate_dim=4,
            num_heads=2,
        )
        model = tf.keras.Sequential(
            [
                tf.keras.Input(shape=(4, 6)),
                encoder,
            ]
        )
        input = tf.random.uniform(shape=[2, 4, 6])
        model(input)

    def test_valid_call_with_mask(self):
        encoder = transformer_encoder.TransformerEncoder(
            intermediate_dim=4,
            num_heads=2,
        )
        encoder.build([2, 4, 6])
        input = tf.random.uniform(shape=[2, 4, 6])
        mask = input[:, :, 0] < 0.5
        encoder(input, mask)

    def test_get_config_and_from_config(self):
        encoder = transformer_encoder.TransformerEncoder(
            intermediate_dim=4,
            num_heads=2,
        )
        config = encoder.get_config()
        expected_config_subset = {
            "intermediate_dim": 4,
            "num_heads": 2,
            "dropout": 0,
            "activation": "relu",
            "layer_norm_epsilon": 1e-05,
        }
        self.assertEqual(config, {**config, **expected_config_subset})

        restored_encoder = transformer_encoder.TransformerEncoder.from_config(
            config,
        )
        self.assertEqual(
            restored_encoder.get_config(), {**config, **expected_config_subset}
        )

    def test_one_training_step_of_transformer_encoder(self):
        encoder = transformer_encoder.TransformerEncoder(
            intermediate_dim=4,
            num_heads=2,
        )
        inputs = tf.keras.Input(shape=(4, 6))
        x = encoder(inputs)
        x = tf.keras.layers.Dense(1, activation="sigmoid")(x)
        model = tf.keras.Model(inputs=inputs, outputs=x)

        data = tf.random.uniform(shape=[2, 4, 6])
        label = tf.cast(data[:, :, 0] >= 0.5, dtype=tf.int32)

        loss_fn = tf.keras.losses.BinaryCrossentropy(from_logits=False)
        optimizer = tf.keras.optimizers.Adam()
        with tf.GradientTape() as tape:
            pred = model(data)
            loss = loss_fn(label, pred)
        grad = tape.gradient(loss, model.trainable_variables)
        self.assertTrue(len(grad) > 1)
        optimizer.apply_gradients(zip(grad, model.trainable_variables))

    def test_checkpointing_transformer_encoder(self):
        encoder1 = transformer_encoder.TransformerEncoder(
            intermediate_dim=4,
            num_heads=2,
        )

        encoder2 = transformer_encoder.TransformerEncoder(
            intermediate_dim=4,
            num_heads=2,
        )
        data = tf.random.uniform(shape=[2, 4, 6])
        encoder1(data)
        encoder2(data)
        # The weights of encoder1 and encoder2 are different.
        self.assertFalse(
            all(
                encoder1._output_dense.trainable_variables[0][0]
                == encoder2._output_dense.trainable_variables[0][0]
            )
        )
        checkpoint = tf.train.Checkpoint(encoder1)
        checkpoint2 = tf.train.Checkpoint(encoder2)
        temp_dir = tempfile.mkdtemp()
        save_path = checkpoint.save(temp_dir)
        checkpoint2.restore(save_path)

        encoder1_output = encoder1(data)
        encoder2_output = encoder2(data)
        self.assertAllClose(encoder1_output, encoder2_output)

    def test_save_model(self):
        model = tf.keras.Sequential(
            [
                tf.keras.Input(shape=(4, 6)),
                transformer_encoder.TransformerEncoder(
                    intermediate_dim=4,
                    num_heads=2,
                ),
            ]
        )
        data = tf.random.uniform(shape=[2, 4, 6])
        model(data)
        path = os.path.join(tempfile.mkdtemp(), "model")
        model.save(path)
        loaded_model = tf.keras.models.load_model(path)

        model_output = model(data)
        loaded_model_output = loaded_model(data)
        self.assertAllClose(model_output, loaded_model_output)