import matplotlib.pyplot as plt
import os
import re

def parse_avg_results(file_path):
    avg_results = {}
    regex = re.compile(r"Average ([a-zA-Z ]+): ([0-9.]+)")
    
    with open(file_path, 'r') as file:
        for line in file:
            match = regex.search(line)
            if match:
                stat = match.group(1).strip()
                value = float(match.group(2).strip())
                avg_results[stat] = value
    return avg_results

def plot_cdcl_vs_dpll(data_cdcl, data_dpll, xlabel, ylabel, title, output_file):
    plt.figure(figsize=(10, 6))
    
    plt.plot(data_cdcl['x'], data_cdcl['y'], marker='o', linestyle='--', label='CDCL')
    plt.plot(data_dpll['x'], data_dpll['y'], marker='s', linestyle='-', label='DPLL')
    
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig("png/" + output_file)
    plt.clf()

def plot_graphs(data, xlabel, ylabel, title, output_file):
    for key, values in data.items():
        if values['x'] and values['y']:  # Ensure there is data to plot
            plt.plot(values['x'], values['y'], marker='o', label=key)
    
    plt.xlabel(xlabel)
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.savefig("png/" + output_file)
    plt.clf()  # Clear the plot for the next graph

if __name__ == "__main__":
    solvers = ['cdcl', 'dpll']
    generators = ['Random', 'PHP', 'Pebbling']
    flags = {
        'cdcl': ['vsids', 'restarts', 'learn', 'delete', 'minimize'],
        'dpll': ['pure']
    }
    nsolvers = {
        'cdcl': {
            'Random': [4, 8, 16, 32, 64, 80, 105, 128],
            'PHP': [1, 2, 3, 4, 5, 6, 7],
            'Pebbling': [2, 4, 8, 9, 10, 11]
        },
        'dpll': {
            'Random': [4, 8, 16, 32, 64],
            'PHP': [1, 2, 3, 4, 5, 6, ],
            'Pebbling': [2, 3, 4, 5, 6]
        }
    }

    cdcl_vs_dpll_time = {solver: {generator: {'x': [], 'y': []} for generator in generators} for solver in solvers}
    cdcl_vs_dpll_propagations = {solver: {generator: {'x': [], 'y': []} for generator in generators} for solver in solvers}
    cdcl_vs_dpll_decisions = {solver: {generator: {'x': [], 'y': []} for generator in generators} for solver in solvers}

    for solver in solvers:
        for generator in generators:
            data_time = {}
            data_propagations = {}
            data_decisions = {}

            for flag in flags[solver]:
                flag_str = flag
                folder_prefix = f"temp/{solver}_{generator}_"

                key_disabled = f"{solver}_{generator}_{flag}_disabled"
                data_time[key_disabled] = {'x': [], 'y': []}
                data_propagations[key_disabled] = {'x': [], 'y': []}
                data_decisions[key_disabled] = {'x': [], 'y': []}

                for n in nsolvers[solver][generator]:
                    folder_name = f"{folder_prefix}{n}_{flag_str}_off"
                    avg_results_disabled_path = os.path.join(folder_name, f"average_results_{flag_str}_off.txt")
                    
                    if os.path.exists(avg_results_disabled_path):
                        avg_results_disabled = parse_avg_results(avg_results_disabled_path)
                        
                        data_time[key_disabled]['x'].append(n)
                        data_time[key_disabled]['y'].append(avg_results_disabled.get('Time', 0))

                        data_propagations[key_disabled]['x'].append(n)
                        data_propagations[key_disabled]['y'].append(avg_results_disabled.get('Number of Unit Propagations', 0))

                        data_decisions[key_disabled]['x'].append(n)
                        data_decisions[key_disabled]['y'].append(avg_results_disabled.get('Number of Decisions', 0))

            # Handle all flags enabled
            key_enabled = f"{solver}_{generator}_all_flags_enabled"
            data_time[key_enabled] = {'x': [], 'y': []}
            data_propagations[key_enabled] = {'x': [], 'y': []}
            data_decisions[key_enabled] = {'x': [], 'y': []}

            for n in nsolvers[solver][generator]:
                folder_name_enabled = f"{folder_prefix}{n}_all_flags_enabled"
                avg_results_enabled_path = os.path.join(folder_name_enabled, "average_results_all_flags_enabled.txt")

                if os.path.exists(avg_results_enabled_path):
                    avg_results_enabled = parse_avg_results(avg_results_enabled_path)

                    data_time[key_enabled]['x'].append(n)
                    data_time[key_enabled]['y'].append(avg_results_enabled.get('Time', 0))

                    data_propagations[key_enabled]['x'].append(n)
                    data_propagations[key_enabled]['y'].append(avg_results_enabled.get('Number of Unit Propagations', 0))

                    data_decisions[key_enabled]['x'].append(n)
                    data_decisions[key_enabled]['y'].append(avg_results_enabled.get('Number of Decisions', 0))

            # Store data for CDCL vs DPLL comparison
            cdcl_vs_dpll_time[solver][generator] = data_time[key_enabled]
            cdcl_vs_dpll_propagations[solver][generator] = data_propagations[key_enabled]
            cdcl_vs_dpll_decisions[solver][generator] = data_decisions[key_enabled]

            # Plot and save graphs for each solver and generator combination
            plot_graphs(data_time, 'n', 'Execution time (s)', 
                        f'Execution Time vs n for {solver.upper()} and {generator}', 
                        f'{solver}_{generator}_execution_time.png')

            plot_graphs(data_propagations, 'n', 'Unit propagations', 
                        f'Unit Propagations vs n for {solver.upper()} and {generator}', 
                        f'{solver}_{generator}_unit_propagations.png')

            plot_graphs(data_decisions, 'n', 'Decisions', 
                        f'Decisions vs n for {solver.upper()} and {generator}', 
                        f'{solver}_{generator}_decisions.png')

    # After the main loop, create CDCL vs DPLL comparison graphs
    for generator in generators:
        plot_cdcl_vs_dpll(cdcl_vs_dpll_time['cdcl'][generator], cdcl_vs_dpll_time['dpll'][generator], 
                          'n', 'Execution time (s)', 
                          f'CDCL vs DPLL: Execution Time for {generator}', 
                          f'cdcl_vs_dpll_{generator}_execution_time.png')

        plot_cdcl_vs_dpll(cdcl_vs_dpll_propagations['cdcl'][generator], cdcl_vs_dpll_propagations['dpll'][generator], 
                          'n', 'Unit propagations', 
                          f'CDCL vs DPLL: Unit Propagations for {generator}', 
                          f'cdcl_vs_dpll_{generator}_unit_propagations.png')

        plot_cdcl_vs_dpll(cdcl_vs_dpll_decisions['cdcl'][generator], cdcl_vs_dpll_decisions['dpll'][generator], 
                          'n', 'Decisions', 
                          f'CDCL vs DPLL: Decisions for {generator}', 
                          f'cdcl_vs_dpll_{generator}_decisions.png')

    print("All graphs, including CDCL vs DPLL comparisons, have been generated and saved.")