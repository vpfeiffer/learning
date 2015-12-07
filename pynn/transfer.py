"""Transfer function layers."""

import numpy
import math

from pynn import network

def sigmoid(x):
    """Sigmoid like function using tanh"""
    return numpy.tanh(x)

def dsigmoid(y):
    """Derivative of sigmoid above"""
    return 1.0 - y**2

def gaussian(x, variance=1.0):
    return math.exp(-(x**2/variance))
gaussian_vec = numpy.vectorize(gaussian)

def dgaussian(y, variance):
    return 2*y*gaussian(y, variance) / variance
dgaussian_vec = numpy.vectorize(dgaussian)

class Transfer(network.Layer):
    def reset(self):
        pass

    def get_deltas(self, errors, outputs):
        return errors

    def get_errors(self, deltas, outputs):
        return deltas

    def update(self, inputs, deltas):
        pass

class SigmoidTransfer(Transfer):
    def activate(self, inputs):
        return sigmoid(inputs)

    def get_outputs(self, inputs, outputs):
        return dsigmoid(outputs)

class ReluTransfer(Transfer):
    pass

class LogitTransfer(Transfer):
    pass

class GaussianTransfer(Transfer):
    def __init__(self, variance=1.0):
        super(GaussianTransfer, self).__init__()

        self._variance = variance

    def activate(self, inputs):
        return gaussian_vec(inputs, self._variance)

    def get_outputs(self, inputs, outputs):
        return dgaussian_vec(outputs, self._variance)