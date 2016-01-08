﻿import numpy
import random

class Layer(object):
    """A layer of computation for a supervised learning network."""
    attributes = tuple([])

    requires_prev = tuple([])
    requires_next = tuple([])
    
    num_inputs = None
    num_outputs = None

    def reset(self):
        raise NotImplementedError()

    def activate(self, inputs):
        raise NotImplementedError()

    def get_prev_errors(self, errors, outputs):
        raise NotImplementedError()

    def update(self, inputs, outputs, errors):
        raise NotImplementedError()

    def get_outputs(self, inputs, outputs):
        """Get outputs for previous layer.
        
        Transfer functions should override to properly transform their input
        """
        return inputs

class SupportsGrowingLayer(Layer):
    """Layer that supports new neurons by increasing input size.
    
    Adds neurons when GrowingLayer before it raises growth exception.
    """
    attributes = ('supportsGrowing',)

    def add_input(self):
        raise NotImplementedError()

class GrowingLayer(Layer):
    """Layer that can add new neurons, increasing output size.
    
    Raise growth exception when new neuron is added.
    """
    requires_next = ('supportsGrowing',)

class ParallelLayer(Layer):
    """A composite of layers connected in parallel."""

#####################
# Network validation
#####################
def _validate_layers_layers(layers):
    """Assert each element of layers is a Layer."""
    for layer in layers:
        if not isinstance(layer, Layer):
            raise TypeError("layers argument of Network must contain Layer's." \
                             " Instead contains {}.".format(type(layer)))

def _all_in(all_required, values):
    for required in all_required:
        if not required in values:
            return False
    return True

def _validate_requires_next(prev_layer, layer):
    if not _all_in(prev_layer.requires_next, layer.attributes):
        raise TypeError("Layer of type {} must be followed by attributes: {}. " \
                        "It is followed by attributes: " \
                        "{}".format(type(prev_layer), prev_layer.requires_next, 
                                    layer.attributes))

def _validate_requires_prev(next_layer, layer):
    if not _all_in(next_layer.requires_prev, layer.attributes):
        raise TypeError("Layer of type {} must be preceded by attributes: {}. " \
                        "It is preceded by attributes: " \
                        "{}".format(type(next_layer), next_layer.requires_prev, 
                                    layer.attributes))

def _validate_layers_parallel(layers, prev_layer, next_layer):
    """Validate that all layers have the same required features."""
    _validate_layers_layers(layers)

    # Same inputs and outputs
    num_inputs = layers[0].num_inputs
    num_outputs = layers[0].num_outputs
    for i, layer in enumerate(layers[1:]):
        if layer.num_inputs != num_inputs:
            raise ValueError('num_inputs for layer {} does not match other' \
                             ' layers in parallel. Should have {}'.format(i+1, num_inputs))

        if layer.num_outputs != num_outputs:
            raise ValueError('num_outputs for layer {} does not match other' \
                             ' layers in parallel. Should have {}'.format(i+1, num_outputs))

    # Supports prev and next layer
    for i, layer in enumerate(layers):
        if prev_layer:
            _validate_requires_next(prev_layer, layer)

        if next_layer:
            _validate_requires_prev(next_layer, layer)

def _validate_layers_sequence(layers, num_inputs='any'):
    """Validate that layers are valid and each layer matches the next layer."""
    _validate_layers_layers(layers)

    # inputs --> outputs line up
    last_num = num_inputs
    for i in range(len(layers)-1):
        layer = layers[i]
        next_layer = layers[i+1]

        # Track how many inputs are required for next layer
        if next_layer.num_inputs == 'any':
            # When any, last_num doesn't change, and no validation required
            continue

        last_num = layer.num_outputs

        # Validate
        if last_num != 'any' and next_layer.num_inputs != last_num:
            raise ValueError('num_inputs for layer {} does not match' \
                             ' preceding layers'.format(i+2)) # Starts at 1

    # Check that feature requirements line up
    # Check each lines up with next
    for i in range(len(layers)-1):
        _validate_requires_next(layers[i], layers[i+1])

    # Check each lines up with prev
    for i in range(1, len(layers)):
        _validate_requires_prev(layers[i], layers[i-1])

def _find_num_inputs(layers):
    """Determine number of initial inputs for a series of layers."""
    for layer in layers:
        if layer.num_inputs != 'any':
            return layer.num_inputs

    return 'any'

def _find_num_outputs(layers):
    """Determine final number of outputs for a series of layers."""
    for layer in reversed(layers):
        if layer.num_outputs != 'any':
            return layer.num_outputs

    return 'any'

##############################
# Pattern selection functions
##############################
def select_iterative(patterns):
    return patterns

def select_sample(patterns, size=None):
    if size == None:
        size = len(patterns)

    return random.sample(patterns, size)

def select_random(patterns, size=None):
    if size == None:
        size = len(patterns)

    max_index = len(patterns)-1
    return [patterns[random.randint(0, max_index)] for i in range(size)]

class Network(object):
    """A composite of layers connected in sequence."""
    def __init__(self, layers):
        _validate_layers_sequence(layers)

        self._layers = layers
        self._num_inputs = _find_num_inputs(layers)
        self._num_outputs = _find_num_outputs(layers)
        self._activations = []

        self.logging = True

        # Bookkeeping
        self.iteration = 0

    @property
    def num_inputs(self):
        return self._num_inputs

    @property
    def num_outputs(self):
        return self._num_outputs

    def _reset_bookkeeping(self):
        self.iteration = 0

    def activate(self, inputs):
        """Return the network outputs for given inputs."""
        if self._num_inputs != 'any' and len(inputs) != self._num_inputs:
            raise ValueError('Wrong number of inputs. Expected {}, got {}' \
                             ''.format(self._num_inputs, len(inputs)))

        inputs = numpy.array(inputs)
        self._activations = [inputs]

        for layer in self._layers:
            inputs = layer.activate(inputs)

            # Track all activations for learning
            self._activations.append(inputs)

        return inputs

    def update(self, inputs, targets):
        """Adjust the network towards the targets for given inputs."""
        if self._num_outputs != 'any' and len(targets) != self._num_outputs:
            raise ValueError('Wrong number of targets. Expected {}, got {}' \
                             ''.format(self._num_outputs, len(targets)))

        outputs = self.activate(inputs)

        errors = targets - outputs
        output_errors = errors # for returning

        for i, layer in enumerate(reversed(self._layers)):
            # Pseudo reverse activations, so they are in the right order for
            # reversed layers list
            inputs_ = self._activations[len(self._layers)-i-1]

            # Compute errors for preceding layer before this layers changes
            prev_errors = layer.get_prev_errors(errors, outputs)

            # Update
            layer.update(inputs_, outputs, errors)

            # Setup for preceding layer
            errors = prev_errors
            # Outputs for preceding layer are this layers inputs
            outputs = layer.get_outputs(inputs_, outputs)

        return output_errors

    def reset(self):
        """Reset every layer in the network."""
        for layer in self._layers:
            layer.reset()

    def test(self, patterns):
        """Print corresponding inputs and outputs from a set of patterns."""
        for p in patterns:
            print(p[0], '->', self.activate(p[0]))

    def get_error(self, pattern):
        """Return the mean squared error (MSE) for a pattern."""
        # Mean squared error
        return numpy.mean(numpy.subtract(self.activate(pattern[0]), pattern[1])**2)

    def get_avg_error(self, patterns):
        """Return the average mean squared error for a set of patterns."""
        error = 0.0        
        for pattern in patterns:
            error = error + self.get_error(pattern)
 
        return error/len(patterns)

    def train(self, patterns, iterations=1000, error_break=0.02,
              pattern_select_func=select_iterative):
        """Train network to converge on set of patterns.
        
        Args:
            patterns: A set of (inputs, targets) pairs.
            iterations: Max iterations to train network.
            error_break: Training will end once error is less than this.
            pattern_select_func: Function that takes a set of patterns,
                and returns a set of patterns. Use partial function to embed arguments.
        """
        self._reset_bookkeeping()
        self.reset()

        # For optimization
        track_error = error_break != 0.0 or self.logging

        # Learn on each pattern for each iteration
        for self.iteration in range(iterations):
            error = 0.0
            for pattern in pattern_select_func(patterns):
                # Learn
                errors = self.update(pattern[0], pattern[1])

                # Sum errors
                if track_error:
                    error += numpy.mean(errors**2)
                
            if track_error:
                error = error / len(patterns)
                if self.logging:
                    print "Iteration {}, Error: {}".format(self.iteration, error)

                # Break early to prevent overtraining
                if error < error_break:
                    return

##########################
# Quick network functions
##########################
def make_mlp(shape, learn_rate=0.5, momentum_rate=0.1):
    """Create a multi-layer perceptron network."""
    from pynn import transfer
    from pynn import transform

    layers = []
    # Create first layer with bias
    layers.append(transform.AddBias(transform.Perceptron(shape[0]+1, shape[1], False, 
                                                         learn_rate, momentum_rate)))
    layers.append(transfer.SigmoidTransfer())

    # Create other layers without bias
    for i in range(1, len(shape)-1):
        layers.append(transform.Perceptron(shape[i], shape[i+1], False, 
                                           learn_rate, momentum_rate))
        layers.append(transfer.SigmoidTransfer())

    return Network(layers)

def make_rbf(inputs, neurons, outputs, learn_rate=1.0, variance=None, normalize=False,
             move_rate=0.1, neighborhood=2, neighbor_move_rate=1.0,):
    """Create a radial-basis function network."""
    from pynn import transfer
    from pynn import transform
    from pynn import som

    if variance == None:
        variance = 4.0/neurons

    layers = [
              som.SOM(inputs, neurons, move_rate, neighborhood, neighbor_move_rate),
              transfer.GaussianTransfer(variance),
              transform.GaussianOutput(neurons, outputs, learn_rate, normalize=True),
             ]

    return Network(layers)