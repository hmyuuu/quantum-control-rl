#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 24 21:52:25 2020

@author: Vladimir Sivak
"""

import qutip as qt
import numpy as np
from math import pi, sqrt
import matplotlib.pyplot as plt

# TODO: add docs

def exp_decay(x, a, b):
    return a*np.exp(-x/b)

def gauss_decay(x, a, b):
    return a*np.exp(-(x/b)**2)

def GKP_state(tensorstate, N, S):
    """
    Thanks to Alec for providing base code for this function.
    
    """
    # Check if the matrix is simplectic
    Omega = np.array([[0,1],[-1,0]])
    if not np.allclose(S.T @ Omega @ S ,Omega):
        raise Exception('S is not symplectic')

    a  = qt.destroy(N)
    q_op = (a + a.dag())/sqrt(2.0)
    p_op = 1j*(a.dag() - a)/sqrt(2.0)
    
    # Deafine stabilizers
    Sz = (2j*sqrt(pi)*(S[0,0]*q_op + S[1,0]*p_op)).expm()
    Sx = (-2j*sqrt(pi)*(S[0,1]*q_op + S[1,1]*p_op)).expm()
    Sy = (2j*sqrt(pi)*((S[0][0]-S[0][1])*q_op + (S[1][0]-S[1][1])*p_op)).expm()
    stabilizers = {'S_x' : Sx, 'S_z' : Sz, 'S_y' : Sy}    
    
    # Deafine Pauli operators
    z =  (1j*sqrt(pi)*(S[0,0]*q_op + S[1,0]*p_op)).expm()
    x = (-1j*sqrt(pi)*(S[0,1]*q_op + S[1,1]*p_op)).expm()
    y = (1j*sqrt(pi)*((S[0][0]-S[0][1])*q_op + (S[1][0]-S[1][1])*p_op)).expm()
    paulis = {'X' : x, 'Y' : y, 'Z' : z}

    displacements = {'S_z': 2*sqrt(pi)*(-S[1,0]+1j*S[0,0]),
                     'Z'  : sqrt(pi)*(-S[1,0]+1j*S[0,0]),
                     'S_x': 2*sqrt(pi)*(S[1,1]-1j*S[0,1]),
                     'X'  : sqrt(pi)*(S[1,1]-1j*S[0,1]),
                     'S_y': 2*sqrt(pi)*((S[1,1]-S[1,0])+1j*(S[0,0]-S[0,1])),
                     'Y'  : sqrt(pi)*((S[1,1]-S[1,0])+1j*(S[0,0]-S[0,1]))}
    
    # Define Hermitian Paulis and stablizers
    ops = [Sz, Sx, Sy, x, y, z]
    ops = [(op + op.dag())/2.0 for op in ops]
    # pass them through the channel 
    chan = epsilon_normalizer(N)
    ops = [chan(op) for op in ops]
    Sz, Sx, Sy, x, y, z = ops
    
    # find 'Z+' as groundstate of this Hamiltonian
    d = (- Sz - Sx - Sy - z).groundstate()
    zero = (d[1]).unit()
    one  = (x*d[1]).unit()

    states = {'Z+' : zero, 
              'Z-' : one,
              'X+' : (zero + one).unit(), 
              'X-' : (zero - one).unit(),
              'Y+' : (zero + 1j*one).unit(), 
              'Y-' : (zero - 1j*one).unit()}

    # Tensordot everything with qubit
    if tensorstate:
        for key, val in stabilizers.items():
            stabilizers[key] = qt.tensor(qt.identity(2), val)
        for key, val in paulis.items():
            paulis[key] = qt.tensor(qt.identity(2), val)
        for key, val in states.items():
            states[key] = qt.tensor(qt.basis(2,0), val)

    return stabilizers, paulis, states, displacements


def epsilon_normalizer(N, epsilon=0.1):
    a = qt.destroy(N)
    n_op = a.dag()*a
    G = (-epsilon*n_op).expm()
    G_inv = (epsilon*n_op).expm()
    return lambda rho: G*rho*G_inv



def plot_wigner(state, tensorstate, cmap='seismic', title=None, savepath=None):
    if tensorstate: state = qt.ptrace(state, 1)
    xvec = np.linspace(-7,7,81)
    W = qt.wigner(state, xvec, xvec, g=sqrt(2))
    fig, ax = plt.subplots(figsize=(6,5))
    # p = ax.pcolormesh(xvec, xvec, W, cmap=cmap, vmin=-1, vmax=+1) #'RdBu_r'
    # ax.plot([sqrt(pi), sqrt(pi)/2, 0, 0], [0, 0, sqrt(pi), sqrt(pi)/2], 
    #         linestyle='none', marker='.',color='black')

    p = ax.pcolormesh(xvec/sqrt(pi), xvec/sqrt(pi), W, cmap=cmap, vmin=-1, vmax=+1) #'RdBu_r'   
    ax.plot([1, 1/2, 0, 0], [0, 0, 1, 1/2], 
            linestyle='none', marker='.',color='black')
    fig.colorbar(p, ax=ax)
    plt.grid()
    if title: ax.set_title(title)
    if savepath: plt.savefig(savepath)


# TODO: add support for batch plotting
def plot_wigner_tf_wrapper(state, tensorstate=False, *args, **kwargs):
    try:
        assert state.shape[0]==1
    except:
        raise ValueError('Batch plotting is not supported')
    state = state.numpy()[0]

    if tensorstate:
        N = int(len(state) / 2)
        state = state.reshape((2*N,1))
        dims = [[2, N], [1, 1]]
    else:
        N = int(len(state))
        state = state.reshape((N,1))
        dims = [[N], [1]]
    
    state = qt.Qobj(state, dims=dims, type='ket')    
    plot_wigner(state, tensorstate, *args, **kwargs)

