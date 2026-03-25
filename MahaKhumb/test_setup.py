"""Environment verification for the MahaKhumb sprint."""

from __future__ import annotations

import sys

import matplotlib
import networkx as nx
import numpy as np
import osmnx as ox
from sklearn.cluster import KMeans

from qiskit_optimization import QuadraticProgram
from qiskit_optimization.algorithms import MinimumEigenOptimizer

try:
    from qiskit.primitives import StatevectorSampler
    SAMPLER_NAME = "StatevectorSampler"
except ImportError:
    from qiskit.primitives import Sampler as StatevectorSampler
    SAMPLER_NAME = "Sampler"

from qiskit_algorithms import NumPyMinimumEigensolver, QAOA
from qiskit_algorithms.optimizers import COBYLA


def main() -> None:
    print("Python:", sys.version.split()[0])
    print("OSMnx:", ox.__version__)
    print("NetworkX:", nx.__version__)
    print("NumPy:", np.__version__)
    print("Matplotlib:", matplotlib.__version__)
    print("KMeans:", KMeans.__name__)
    print("QuadraticProgram:", QuadraticProgram.__name__)
    print("MinimumEigenOptimizer:", MinimumEigenOptimizer.__name__)
    print("QAOA:", QAOA.__name__)
    print("NumPyMinimumEigensolver:", NumPyMinimumEigensolver.__name__)
    print("COBYLA:", COBYLA.__name__)
    print("Sampler primitive:", SAMPLER_NAME)
    print("ALL GOOD")


if __name__ == "__main__":
    main()
