# -*- coding: utf-8 -*-
"""
Created on Thu Sep 24 09:34:40 2020

@author: Vladimir Sivak

Qubit is included in the Hilbert space. Simulation is done with a gate-based 
approach to quantum circuits.
"""
import tensorflow as tf
from tensorflow.keras.backend import batch_dot
from gkp.gkp_tf_env.gkp_tf_env import GKP
from gkp.gkp_tf_env import helper_functions as hf
from tf_agents import specs
from simulator.hilbert_spaces import OscillatorQubit
from simulator.utils import normalize

class QuantumCircuit(OscillatorQubit, GKP):
    """
    This class inherits simulation-independent functionality from the GKP
    class and implements simulation by abstracting away the qubit and using
    Kraus maps formalism to efficiently simulate operations on the oscillator 
    Hilbert space.
    
    Universal gate sequence for open-loop unitary control of the oscillator.
    The gate sequence consists of 
        1) oscillator translations in phase space 
        2) qubit rotations on the Bloch sphere
        3) conditional translations of the oscillator conditioned on qubit
    
    """
    def __init__(
        self,
        *args,
        # Required kwargs
        t_gate,
        # Optional kwargs
        **kwargs):
        """
        Args:
            t_gate (float): Gate time in seconds.
            t_read (float): Readout time in seconds.
        """
        self.t_gate = tf.constant(t_gate, dtype=tf.float32)
        self.step_duration = self.t_gate
        super().__init__(*args, **kwargs)

    @property
    def _quantum_circuit_spec(self):
        spec = {'beta'  : specs.TensorSpec(shape=[1,2], dtype=tf.float32), 
                'phi'   : specs.TensorSpec(shape=[1,2], dtype=tf.float32)}
        return spec

    @tf.function
    def _quantum_circuit(self, psi, action):
        """
        Args:
            psi (Tensor([batch_size,N], c64)): batch of states
            action (dict, 'beta'  : Tensor([batch_size,1,2], tf.float32),
                          'phi'   : Tensor([batch_size,1,2], tf.float32))

        Returns: see parent class docs

        """
        # Extract parameters
        beta = hf.vec_to_complex(action['beta'])
        phi_x = action['phi'][:,0]
        phi_y = action['phi'][:,1]

        # Construct gates
        T, CT, R = {}, {}, {}
        T['b'] = self.translate(beta/4.0)
        CT['b'] = self.ctrl(tf.linalg.adjoint(T['b']), T['b'])

        R['x'] = self.rotate_qb(phi_x, axis='x')
        R['y'] = self.rotate_qb(phi_y, axis='y')

        # Qubit rotation
        psi = batch_dot(R['x'], psi)
        psi = batch_dot(R['y'], psi)
        # Conditional translation
        psi = batch_dot(CT['b'], psi)
        psi = self.simulate(psi, self.t_gate)
        psi = batch_dot(CT['b'], psi)

        return psi, psi, tf.ones((self.batch_size,1))