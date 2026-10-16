import sys
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from topology import NetworkTopology
from lfc import compute_lfc
from mnp_e import compute_mnpe
from bpp import bpp, build_all_paths
from simulator import simulate_failures

def run_sweeps():
    os.makedirs('results', exist_ok=True)
    topologies_to_test = ['Sprint.gml', 'Abilene.gml', 'Geant2012.gml']
    budgets = [2, 4, 6, 8, 10, 12, 14, 16]
    num_trials = 300
    
    results = []
    
    for topo_name in topologies_to_test:
        filepath = os.path.join('data', 'gml', topo_name)
        if not os.path.exists(filepath):
            print(f"Skipping {topo_name} - not found.")
            continue
            
        print(f"\nProcessing {topo_name}...")
        topo = NetworkTopology.from_gml(filepath)
        G = topo.graph
        tm = topo.generate_gravity_traffic_matrix()
        
        # Precompute LFC & MNP-e
        next_hops_lfc = {c: compute_lfc(G, c) for c in G.nodes()}
        next_hops_mnpe = {c: compute_mnpe(G, c) for c in G.nodes()}
        all_paths = build_all_paths(G, next_hops_lfc)
        
        # 1. Baseline LFC
        _, t_avail_lfc = simulate_failures(G, all_paths, next_hops_lfc, [], num_trials=num_trials, traffic_matrix=tm)
        
        for budget in budgets:
            print(f"  Budget: {budget} links")
            
            # Original HLP
            protected_hlp = bpp(G, next_hops_mnpe, R_threshold=1.0, use_ta=False, max_links=budget)
            _, t_avail_hlp = simulate_failures(G, all_paths, next_hops_mnpe, protected_hlp, num_trials=num_trials, traffic_matrix=tm)
            
            # TA-HLP
            protected_ta = bpp(G, next_hops_mnpe, R_threshold=1.0, traffic_matrix=tm, use_ta=True, max_links=budget)
            _, t_avail_ta = simulate_failures(G, all_paths, next_hops_mnpe, protected_ta, num_trials=num_trials, traffic_matrix=tm)
            
            results.append({
                'Topology': topo_name.replace('.gml', ''),
                'Max_BPP_Links': budget,
                'Method': 'LFC Only',
                'Traffic_Availability': t_avail_lfc
            })
            results.append({
                'Topology': topo_name.replace('.gml', ''),
                'Max_BPP_Links': budget,
                'Method': 'HLP (Original)',
                'Traffic_Availability': t_avail_hlp
            })
            results.append({
                'Topology': topo_name.replace('.gml', ''),
                'Max_BPP_Links': budget,
                'Method': 'TA-HLP (Proposed)',
                'Traffic_Availability': t_avail_ta
            })
            
    df = pd.DataFrame(results)
    df.to_csv('results/data.csv', index=False)
    print("\nResults saved to results/data.csv")
    
    # Generate Plots
    sns.set_theme(style="whitegrid")
    
    for topo_name in df['Topology'].unique():
        plt.figure(figsize=(8, 5))
        subset = df[df['Topology'] == topo_name]
        sns.lineplot(data=subset, x='Max_BPP_Links', y='Traffic_Availability', hue='Method', marker='o')
        plt.title(f"Traffic Availability vs Overhead Budget ({topo_name})")
        plt.xlabel("Max Allowed BPP Links (Overhead)")
        plt.ylabel("Traffic Availability Ratio")
        plt.tight_layout()
        plt.savefig(f'results/plot_{topo_name}.png')
        plt.close()
        print(f"Generated plot: results/plot_{topo_name}.png")

if __name__ == "__main__":
    run_sweeps()
