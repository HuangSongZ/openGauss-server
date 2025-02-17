# Copyright (c) 2020 Huawei Technologies Co.,Ltd.
#
# openGauss is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#
#          http://license.coscl.org.cn/MulanPSL2
#
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import PolynomialFeatures

from dbmind.common.types import Sequence
from .forcasting_algorithm import ForecastingAlgorithm


def series_to_supervised(sequence: Sequence, test_size=.1, poly_degree=None,
                         random_state=None, shuffle=False):
    x, y = sequence.to_2d_array()
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=test_size, shuffle=shuffle, random_state=random_state
    )

    if poly_degree:
        poly = PolynomialFeatures(degree=poly_degree).fit(x)
        x_train = poly.transform(x_train)
        x_test = poly.transform(x_test)

    return x_train, x_test, y_train, y_test


class SimpleLinearFitting(ForecastingAlgorithm):
    def __init__(self, avoid_repetitive_fitting=False):
        self._a = None
        self._b = None
        self._r2 = None
        self._last_x = None
        self._step = None
        self._fitted = False
        self._avoid_repetitive_fitting = avoid_repetitive_fitting

    def refit(self):
        self._fitted = False

    def fit(self, sequence: Sequence):
        # `self._fitted` is a flag to control whether performing the fitting process because
        # this fitting algorithm can estimate the linear degree. And if the class has
        # estimated a sequence, it should not fit one more. So, we use this flag to
        # prevent fitting again.
        if self._avoid_repetitive_fitting and self._fitted:
            return

        if sequence.length < 2:
            raise ValueError('Unable to fit the sequence due to short length.')

        n = len(sequence)
        sx = sy = sxx = syy = sxy = 0
        # timestamp acts x-axis, values acts y-axis.
        for t, v in sequence:
            sx += t
            sy += v
            sxx += t * t
            syy += v * v
            sxy += t * v
        a = (sy * sx / n - sxy) / (sx * sx / n - sxx)
        b = (sy - a * sx) / n
        numerator = syy + a * a * sxx + b * b * n + 2 * a * b * sx - 2 * a * sxy - 2 * b * sy
        denominator = syy - sy * sy / n + 1e-9
        r2 = 1 - numerator / denominator

        self._a = a
        self._b = b
        self._r2 = r2
        self._last_x = sequence.timestamps[-1]
        self._step = sequence.step
        self._fitted = True

    def forecast(self, forecast_length):
        future = []
        for i in range(1, forecast_length + 1):
            t = self._last_x + i * self._step
            v = self._a * t + self._b
            future.append(v)
        return future

    @property
    def r2_score(self):
        return self._r2


class SimpleLinearRegression(ForecastingAlgorithm):
    def __init__(self):
        self.model = LinearRegression(copy_X=False)
        self.interval = None
        self.last_x = None

    def fit(self, sequence: Sequence):
        if sequence.length < 2:
            raise ValueError('Unable to fit the sequence due to short length.')

        x, y = sequence.to_2d_array()
        self.interval = x[1] - x[0]
        self.last_x = x[-1]
        x = np.reshape(x, newshape=(-1, 1))
        self.model.fit(x, y)

    def forecast(self, forecast_length):
        future = np.arange(start=self.last_x + self.interval,
                           stop=self.last_x + self.interval * (forecast_length + 1),
                           step=self.interval).reshape(-1, 1)
        result = self.model.predict(future)
        return result.tolist()


class SupervisedModel(ForecastingAlgorithm):
    def __init__(self, model=None, bias=False, poly_degree=None):
        self.bias = bias
        self.poly_degree = poly_degree
        # Use the passed Model instance if exists.
        if not model:
            self.model = LinearRegression(normalize=True)
        else:
            self.model = model
        self.predict_steps = None
        self.sequence = None

    def fit(self, sequence: Sequence):
        if sequence.length < 2:
            raise ValueError('Unable to fit the sequence due to short length.')

        # dummy to fit
        self.sequence = sequence

    def forecast(self, forecast_length):
        if not isinstance(forecast_length, int):
            raise ValueError('#2 forecasting_minutes must be an integer.')

        self.predict_steps = forecast_length if forecast_length > 1 else 1
        x_train, x_test, y_train, y_test = series_to_supervised(self.sequence)
        x_pred = np.arange(start=self.sequence.length,
                           stop=self.sequence.length + self.predict_steps,
                           step=1).reshape(-1, 1)
        self.model.fit(np.array(x_train).reshape(-1, 1),
                       np.array(y_train).reshape(-1, 1))
        y_pred = self.model.predict(X=x_pred)
        if self.bias:
            bias = y_pred.flatten()[0] - self.sequence.values[-1]
            y_pred -= bias
        return y_pred.flatten().tolist()
