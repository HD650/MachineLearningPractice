import numpy
import random
import json
import os
import sys
sys.path.append("..")


def load_data():
    import mnist_loader
    training_data, validation_data, test_data = mnist_loader.load_data()
    training_set = list()
    for x, y in zip(training_data[0], training_data[1]):
        training_set.append((x, mnist_loader.vectorized_result(y)))
    test_set = list()
    for x, y in zip(validation_data[0], validation_data[1]):
        test_set.append((x, mnist_loader.vectorized_result(y)))
    return training_set, test_set


def network_serializer(network):
    weights = list()
    print('{0} layers in weights...'.format(len(network.weights)))
    print('serializeing weights matrix...')
    for layer in network.weights:
        weight_shape = layer.shape
        print('shape: '+str(weight_shape))
        weights.append(layer.tolist())
    weights = json.dumps(weights)

    biases = list()
    print('{0} layers in biases...'.format(len(network.biases)))
    print('serializeing biases matrix...')
    for layer in network.biases:
        bias_shape = layer.shape
        print('shape: '+str(bias_shape))
        biases.append(layer.tolist())
    biases = json.dumps(biases)

    weight_file = open('./data/weights.dat', 'w')
    bias_file = open('./data/biases.dat', 'w')
    weight_file.write(weights)
    bias_file.write(biases)
    weight_file.close()
    bias_file.close()


def network_reader(network):
    weight_file = open('./data/weights.dat', 'r')
    bias_file = open('./data/biases.dat', 'r')
    weigths_data = json.loads(weight_file.read())
    biases_data = json.loads(bias_file.read())

    weights = list()
    print('found {0} layers in weights...'.format(len(weigths_data)))
    for layer in weigths_data:
        layer_m = numpy.matrix(layer)
        weights.append(layer_m)

    biases = list()
    print('found {0} layers in biases...'.format(len(biases_data)))
    for layer in biases_data:
        layer_m = numpy.matrix(layer)
        biases.append(layer_m)

    network.weights = weights
    network.biases = biases

    return network

# Network的training data必须是(matrix, matrix)或者(ndarray, ndarry)
# 约定中，z为神经元的输入，a(activation)为神经元的输出，z是上一层activation关于weight加权和再加上bias，而该层activation是将该层z带入activation function所得
# 该神经网络可以自定义activation function和cost function，两者都要提供函数本体和导数,其中cost funtion的导数要提供矩阵维度的


class Network:
    def __init__(self, size, activation_function=None, activation_function_prime=None, cost_function=None, cost_function_partial_derivatives=None):
        """初始化神经网络"""
        # activation函数，默认用sigmoid函数，因为他能减少上层神经元剧烈变动对下层的影响，防止整个网络大幅度波动
        if activation_function is not None:
            self.activation_function = activation_function
        if activation_function_prime is not None:
            self.activation_function_prime = activation_function_prime
        # cost function对输出层a的导数计算函数，默认为最小二乘cost function
        if cost_function_partial_derivatives is not None:
            self.cost_function_partial_derivatives = cost_function_partial_derivatives
        if cost_function is not None:
            self.cost_function = cost_function
        self.layer_num = len(size)
        # weights是一个j*k的矩阵的列表，每两层之间使用一个weight矩阵，行j是该层的神经元编号，列k是上一层的神经元编号
        self.weights = [numpy.asmatrix(numpy.random.randn(size[i], size[i-1])) for i in range(1, len(size))]
        # biases是一个j*1的矩阵的列表，除了输入层，每层使用一个bias矩阵，其中j是该层的神经元编号
        self.biases = [numpy.asmatrix(numpy.random.randn(size[i+1], 1)) for i in range(len(size)-1)]
        # 对weights和biases矩阵进行初始化，使用随机能避免收敛困难和陷入局部最优解
        self.random_matrix(self.weights)
        self.random_matrix(self.biases)
        print('Weight and bias matrix initialized!')
        for item in self.weights:
            print('Weight matrix: '+str(item.shape))
        for item in self.biases:
            print('Bias matrix: '+str(item.shape))
        self.accuracy = 0.0

    def random_matrix(self, matrix):
        # raise NotImplementedError()
        pass

    def forward_feed(self, input_layer_activation):
        activation = numpy.matrix(input_layer_activation).transpose()
        # 对每层迭代
        for weight, bias in zip(self.weights, self.biases):
            # 使用j*k的weights矩阵点乘上一层的k*1大小的activation矩阵，得到j*1的中间结果，在加上biases矩阵得到整个一层的神经元的z
            activation = numpy.dot(weight, activation) + bias
            # 使用激励函数得到整个一层的神经元输出，用于下一次迭代的输入
            activation = self.activation_function(activation)
        return activation

    @staticmethod
    def activation_function(x):
        """默认的activation function，使用sigmoid函数"""
        return 1.0/(1.0 + numpy.exp(-x))

    def activation_function_prime(self, x):
        """默认的activation函数导数，因为默认为sigmoid，这里为sigmoid导数"""
        if type(x) is numpy.matrix:
            x = numpy.array(x)
        return self.activation_function(x) * (1 - self.activation_function(x))

    @staticmethod
    def cost_function(output_layer_activation, sample_output):
        """默认的cost function使用最小二乘函数,对于每个输出层神经元都有一个cost结果"""
        return [(oka-so)*(oka-so)/2 for oka,so in zip(output_layer_activation, sample_output)]

    @staticmethod
    def cost_function_partial_derivatives(output_layer_activation, sample_output):
        """默认的cost关于a导数矩阵，求解输出层神经元误差时需要的cost function关于所有输出层activation的导数结果矩阵"""
        return output_layer_activation - sample_output

    def backprop(self, input_layer_activation, sample_output):
        """使用一个样本进行bp"""
        # 初始化weights导数和biases导数矩阵
        biases_derivative = [numpy.asmatrix(numpy.zeros(b.shape, float)) for b in self.biases]
        weights_derivative = [numpy.asmatrix(numpy.zeros(w.shape, float)) for w in self.weights]
        # 每层神经元的z和activation都要储存以计算导数
        activations_vector = []
        input_layer_activation = numpy.matrix(input_layer_activation).transpose()
        activations_vector.append(input_layer_activation)
        activation = input_layer_activation
        z_vector = []
        # 正向传播一遍神经元，记录下每层神经元的activation和z
        for weight, bias in zip(self.weights, self.biases):
            temp = numpy.dot(weight, activation) + bias
            z_vector.append(temp)
            activation = self.activation_function(temp)
            activations_vector.append(activation)
        # 使用bp神经网络的四等式之一，计算输出层的weights导数和biases导数
        output_layer_error = numpy.array(self.cost_function_partial_derivatives(activations_vector[-1], sample_output))
        output_layer_error *= self.activation_function_prime(z_vector[-1])
        biases_derivative[-1] = output_layer_error
        weights_derivative[-1] = numpy.dot(output_layer_error, activations_vector[-2].transpose())
        # 对输出层之后的所有神经元层，计算他们们的误差，weights和biases导数
        for i in range(self.layer_num-2, 0, -1):
            hide_layer_error = numpy.array(numpy.dot(self.weights[i].transpose(), biases_derivative[i]))
            hide_layer_error *= self.activation_function_prime(z_vector[i-1])
            biases_derivative[i-1] = hide_layer_error
            weights_derivative[i-1] = numpy.dot(hide_layer_error, activations_vector[i-1].transpose())
        return biases_derivative, weights_derivative

    def update_weights_biases(self, samples, learning_rate):
        """使用给定样本进行一次bias和weight的更新，使用每个样本求出weight和bias的导数矩阵，之后进行梯度下降"""
        # 初始化weights和biases的导数矩阵
        biases_derivative = [numpy.asmatrix(numpy.zeros(i.shape, float)) for i in self.biases]
        weights_derivative = [numpy.asmatrix(numpy.zeros(i.shape, float)) for i in self.weights]
        # 对每个样本计算weights和biases的导数矩阵，并且求和
        for x, y in samples:
            delta_biases, delta_weights = self.backprop(x, y)
            biases_derivative = [bd+b for bd, b in zip(biases_derivative, delta_biases)]
            weights_derivative = [wd+w for wd,w in zip(weights_derivative, delta_weights)]
        # 使用求和过的导数矩阵进行梯度下降，下降的步长是导数矩阵的平均值乘以learning rate
        self.biases = [sb-((learning_rate/len(samples))*bd) for sb, bd in zip(self.biases, biases_derivative)]
        self.weights = [sw-((learning_rate/len(samples))*wd) for sw, wd in zip(self.weights, weights_derivative)]
        return biases_derivative, weights_derivative

    def mini_batch_stochastic_gradient_descent(self, training_data, epochs, mini_batch_size, learning_rate, test_data=None):
        """使用随机梯度下降算法训练神经网络"""
        if len(training_data) < mini_batch_size:
            print('ERROR: Mini batch size bigger than samples size!')
            return
        for i in range(epochs):
            print('-'*5+'epoch '+str(i)+'-'*5)
            random.shuffle(training_data)
            training_set = training_data[:mini_batch_size]
            biases_derivative, weights_derivative = self.update_weights_biases(training_set, learning_rate)
            print('weights and biases updated!')
            if test_data is not None:
                print('start test...')
                self.evaluate(test_data)
                print('-'*17)
                print()

    def evaluate(self, test_data):
        """判断目前的神经网络的准确性"""
        test_set_len = len(test_data)
        correct = 0
        for i, (x, y) in enumerate(test_data):
            deduction = self.forward_feed(x).argmax()
            sample = test_data[i][1].argmax()
            if sample == deduction:
                correct += 1
        print('{0} correct samples in {1}'.format(str(correct), str(test_set_len)))
        self.accuracy = float(correct/test_set_len)

if __name__ == '__main__':
    net = Network([784, 30, 10])
    # 读取mnist的训练和测试数据
    training_set, test_set = load_data()
    # 如果之前有训练过的中间结果，读取之后继续训练
    if os.path.exists('./data/weights.dat') and os.path.exists('./data/biases.dat'):
        print('previous learning result found...')
        net = network_reader(net)
    else:
        print('no previous learning result found...')
    try:
        net.mini_batch_stochastic_gradient_descent(training_set, 300000, 100, 3.0, test_set)
    except KeyboardInterrupt as e:
        print('end leaning...')
        print('accuracy now: '+str(net.accuracy))
        network_serializer(net)