###############################################################################
# The MIT License (MIT)
#
# Copyright (c) 2017 Justin Lovinger
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
###############################################################################
"""Models for linear, logistic, and other forms of regression."""
import operator

import numpy

from learning import calculate, optimize, Model, MeanSquaredError
from learning.optimize import Problem

INITIAL_WEIGHTS_RANGE = 0.25


class RegressionModel(Model):
    """A model that optimizes the weight matrix of an equation of a set form.

    Args:
        attributes: int; Number of attributes in dataset.
        num_outputs: int; Number of output values in dataset.
            If onehot vector, this should equal the number of classes.
        optimizer: Instance of learning.optimize.optimizer.Optimizer.
        error_func: Instance of learning.error.ErrorFunc.
        jacobian_norm_break: Training will end if objective gradient norm
            is less than this value.
    """

    def __init__(self,
                 attributes,
                 num_outputs,
                 optimizer=None,
                 error_func=None,
                 penalty_func=None,
                 jacobian_norm_break=1e-10):
        super(RegressionModel, self).__init__()

        # Weight matrix, optimized during training
        self._weight_matrix = self._random_weight_matrix(
            self._weights_shape(attributes, num_outputs))

        # Optimizer to optimize weight_matrix
        if optimizer is None:
            optimizer = optimize.make_optimizer(
                reduce(operator.mul, self._weight_matrix.shape))

        self._optimizer = optimizer

        # Error function for training
        if error_func is None:
            error_func = MeanSquaredError()
        self._error_func = error_func

        # Penalty function for training
        self._penalty_func = penalty_func

        # Convergence criteria
        self._jacobian_norm_break = jacobian_norm_break

    def reset(self):
        """Reset this model."""
        super(RegressionModel, self).reset()

        # Reset the weight matrix
        self._weight_matrix = self._random_weight_matrix(
            self._weight_matrix.shape)

        # Reset the optimizer
        self._optimizer.reset()

    def _random_weight_matrix(self, shape):
        """Return a random weight matrix."""
        # TODO: Random weight matrix should be a function user can pass in
        return (2 * numpy.random.random(shape) - 1) * INITIAL_WEIGHTS_RANGE

    def activate(self, input_tensor):
        """Return the model outputs for given inputs."""
        return self._equation_output(input_tensor)

    # TODO: Refactor, most of these functions are shared between
    # RBF, Regression, and MLP (models using Optimizers)
    def train_step(self, input_matrix, target_matrix):
        """Adjust the model towards the targets for given inputs.

        Train on a mini-batch.

        Optional.
        Model must either override train_step or implement _train_increment.
        """
        # Use an Optimizer to move weights in a direction that minimizes
        # error (as defined by given error function).
        error, flat_weights = self._optimizer.next(
            Problem(
                obj_func=
                lambda xk: self._get_obj(xk, input_matrix, target_matrix),
                obj_jac_func=
                lambda xk: self._get_obj_jac(xk, input_matrix, target_matrix)),
            self._weight_matrix.ravel())
        self._weight_matrix = flat_weights.reshape(self._weight_matrix.shape)

        # TODO: Numerical Optimization uses ||grad_f_k||_inf < 10^-5 (1 + |f_k|) as a stopping criteria
        # Perhaps we should as well (also in MLP, RBF, etc.)
        self.converged = self._optimizer.jacobian is not None and numpy.linalg.norm(
            self._optimizer.jacobian) < self._jacobian_norm_break
        return error

    def _post_train(self, input_matrix, target_matrix):
        """Call after Model.train.

        Optional.
        """
        # Reset optimizer, because problem may change on next train call
        self._optimizer.reset()

    ######################################
    # Helper functions for optimizer
    ######################################
    def _get_obj(self, parameter_vec, input_matrix, target_matrix):
        """Helper function for Optimizer to get objective value."""
        self._weight_matrix = parameter_vec.reshape(self._weight_matrix.shape)
        return self._get_objective_value(input_matrix, target_matrix)

    def _get_obj_jac(self, parameter_vec, input_matrix, target_matrix):
        """Helper function for Optimizer to get objective value and derivative."""
        self._weight_matrix = parameter_vec.reshape(self._weight_matrix.shape)
        error, jacobian = self._get_error_jacobian_with_penalty(
            input_matrix, target_matrix)
        return error, jacobian.ravel()

    ######################################
    # Objective Value
    ######################################
    def _get_objective_value(self, input_matrix, target_matrix):
        """Return error on given dataset."""
        error = self._error_func(self.activate(input_matrix), target_matrix)

        # Calculate and add weight penalty
        if self._penalty_func is not None:
            # Error is mean of sample errors + weight penalty
            # NOTE: We ravel the weight matrix, to take vector norm
            error += self._penalty_func(self._weight_matrix.ravel())

        return error

    ######################################
    # Objective Derivative
    ######################################
    def _get_error_jacobian_with_penalty(self, input_matrix, target_matrix):
        """Return error and jacobian for given dataset with weight penalty."""
        # Calculate jacobian, given error function
        error, jacobian = self._get_error_jacobian(input_matrix, target_matrix)

        # Calculate weight penalty, and add it to error and jacobian
        if self._penalty_func is not None:
            # NOTE: We ravel the weight matrix, to take vector norm
            flat_weights = self._weight_matrix.ravel()
            penalty = self._penalty_func(flat_weights)
            penalty_jac = self._penalty_func.derivative(
                flat_weights,
                penalty_output=penalty).reshape(self._weight_matrix.shape)

            # Error and jacobian is combination of error and weight penalty
            error += penalty
            jacobian += penalty_jac

        return error, jacobian

    def _get_error_jacobian(self, input_matrix, target_matrix):
        """Return error and jacobian for given dataset."""
        output_matrix = self.activate(input_matrix)
        if output_matrix.shape != target_matrix.shape:
            raise ValueError(
                'target_matrix.shape does not match output_matrix.shape')

        error, error_jac = self._error_func.derivative(output_matrix, target_matrix)
        jacobian = self._error_equation_derivative(input_matrix, error_jac)

        assert reduce(operator.mul, jacobian.shape) == reduce(
            operator.mul, self._weight_matrix.shape)

        return error, jacobian

    def _weights_shape(self, attributes, num_outputs):
        """Return shape of this models weight matrix."""
        raise NotImplementedError()

    def _equation_output(self, input_tensor):
        """Return the output of this models equation."""
        raise NotImplementedError()

    def _error_equation_derivative(self, input_matrix, error_jac):
        """Return the jacobian of this models equation corresponding to the given error.

        Derivative with regard to weights.
        """
        raise NotImplementedError()


class LinearRegressionModel(RegressionModel):
    r"""Regression model with an equation of the form: f(\vec{x}) = W \vec{x}."""

    def _weights_shape(self, attributes, num_outputs):
        """Return shape of this models weight matrix."""
        # +1 for bias term
        return (attributes + 1, num_outputs)

    def _equation_output(self, input_tensor):
        """Return the output of this models equation."""
        # First weight (for each output) is independent of input_tensor
        return self._weight_matrix[0] + numpy.dot(input_tensor,
                                                  self._weight_matrix[1:])

    def _error_equation_derivative(self, input_matrix, error_jac):
        """Return the jacobian of this models equation corresponding to the given error.

        Derivative with regard to weights.
        """
        return numpy.vstack((
            # Bias
            numpy.sum(error_jac, axis=0),
            # Weight matrix
            input_matrix.T.dot(error_jac)
        ))


# TODO: Logistic regression is expected to be paried with a specific
# error function, which should be implemented and set as the default
# error function.
# L(W) = prod_i (y_i^{t_i} (1 - y_i)^{1 - t_i})
# maximize_W L(W)
# where, y_i is the model output for sample i, and t_i is the target of sample i
# Note that the above is for a dataset with a single target value.
# Log likelihood is often used instead, maximize N^{-1} log(L(W))
# Also, note that this is given as a maximization problem,
# and should be implemented as -N^{-1} log(L(W)), so it is a minimization problem
class LogisticRegressionModel(RegressionModel):
    r"""Regression model with an equation of the form: f(\vec{x}) = 1 / (1 + e^{- W \vec{x}})."""

    def _weights_shape(self, attributes, num_outputs):
        """Return shape of this models weight matrix."""
        # +1 for bias term
        return (attributes + 1, num_outputs)

    def _equation_output(self, input_tensor):
        """Return the output of this models equation."""
        # Logistic regression is simply lienar regression passed through
        # a logit function
        # First weight (for each output) is independent of input_tensor
        return calculate.logit(self._weight_matrix[0] + numpy.dot(
            input_tensor, self._weight_matrix[1:]))

    def _error_equation_derivative(self, input_matrix, error_jac):
        """Return the jacobian of this models equation corresponding to the given error.

        Derivative with regard to weights.
        """
        # f = _equation_output
        # e = error_func
        # b = bias_vector
        # W = weight_matrix
        # X = input_matrix
        equation_derivative_times_error_jac = calculate.dlogit(
            self._weight_matrix[0] + numpy.dot(
                input_matrix, self._weight_matrix[1:])) * error_jac

        return numpy.vstack((
            # Bias: de(f)/db = (d/db b)^T f'(X W + b) e'(f(X W + b)),
            # where d/db b = vector of ones
            numpy.sum(equation_derivative_times_error_jac, axis=0),
            # Weight matrix: de(f)/dW = X^T f'(X W + b) e'(f(X W + b))
            input_matrix.T.dot(equation_derivative_times_error_jac)))
