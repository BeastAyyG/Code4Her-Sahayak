"""Quick dependency and artifact check for Continuum."""
import sys
import importlib.util
from pathlib import Path

print(f"Python: {sys.version}")
print()

deps_map = {
    "osmnx": "osmnx",
    "networkx": "networkx",
    "matplotlib": "matplotlib",
    "numpy": "numpy",
    "scikit-learn": "sklearn",
    "geopandas": "geopandas",
    "qiskit": "qiskit",
    "qiskit-aer": "qiskit_aer",
    "qiskit-algorithms": "qiskit_algorithms",
    "qiskit-optimization": "qiskit_optimization",
    "docplex": "docplex",
    "torch": "torch",
    "kafka-python": "kafka",
    "pyspark": "pyspark",
    "flask": "flask",
    "scipy": "scipy",
    "folium": "folium",
}

print("=== DEPENDENCIES ===")
missing_deps = []
for name, mod in deps_map.items():
    spec = importlib.util.find_spec(mod)
    status = "OK" if spec else "MISSING"
    if not spec:
        missing_deps.append(name)
    print(f"  {name}: {status}")

print()
print("=== KEY ARTIFACTS ===")
root = Path(__file__).parent
artifacts = [
    "graph_data.pkl",
    "cluster_data.pkl",
    "qaoa_results.pkl",
    "sprint_report.json",
    "simulation_state.json",
    "predictive_state.json",
    "demo_dashboard.html",
    "demo_dashboard_3.html",
    "mobile_phase2.html",
]
missing_artifacts = []
for a in artifacts:
    p = root / a
    exists = p.exists()
    size = f"{p.stat().st_size // 1024} KB" if exists else ""
    if not exists:
        missing_artifacts.append(a)
    print(f"  {a}: {'OK ' + size if exists else 'MISSING'}")

print()
print("=== KEY SCRIPTS ===")
scripts = [
    "layer1_map.py",
    "layer2_clustering.py",
    "layer3_qaoa.py",
    "comparison.py",
    "validate_results.py",
    "stream_simulator.py",
    "build_dashboard.py",
    "mobile_guide_server.py",
    "production_check.py",
    "smoke_test.py",
]
for s in scripts:
    p = root / s
    print(f"  {s}: {'OK' if p.exists() else 'MISSING'}")

print()
print("=== SUMMARY ===")
if missing_deps:
    print(f"  Missing deps ({len(missing_deps)}): {', '.join(missing_deps)}")
else:
    print("  All dependencies installed!")
if missing_artifacts:
    print(f"  Missing artifacts ({len(missing_artifacts)}): {', '.join(missing_artifacts)}")
else:
    print("  All artifacts present!")
