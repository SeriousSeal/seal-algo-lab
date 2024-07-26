import subprocess
import argparse
import sys
import time
import os
import re

# Progress bar function
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='█', printEnd="\r"):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '_' * (length - filledLength)
    print(f'\r{prefix} {bar} {percent}% {suffix}', end=printEnd)
    if iteration == total:
        print()

def run_solver(solver_path, flags):
    start_time = time.time()
    process = subprocess.run(['python3', solver_path, "--input", "output.cnf"] + flags, 
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    end_time = time.time()
    return process.returncode, process.stdout, process.stderr, end_time - start_time

def aggregate_statistics(file, regex):
    stats_sum = {}
    stats_count = {}
    try:
        for line in file:
            if regex.match(line):
                stat = " ".join(line.split(":")[0].split()[1:])
                try:
                    value = float(line.split(":")[1].strip().split()[0])
                except ValueError:
                    value = 0
                stats_sum[stat] = stats_sum.get(stat, 0) + value
                stats_count[stat] = stats_count.get(stat, 0) + 1
    except Exception as e:
        print()
        print(f"Error while reading statistics: {e}")
        return {}, {}
    return stats_sum, stats_count

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run custom solver with a CNF file')
    parser.add_argument('--tries', '-t', type=int, default=10, help='Number of tries per configuration for Random generator (default: 10)')
    args = parser.parse_args()

    solvers = {
        'cdcl': [
            ('--vsids', 'VSIDS Heuristic'),
            ('--restarts', 'Restarts'),
            ('--learn', 'Clause Learning'),
            ('--delete', 'Clause Deletion'),
            ('--minimize', 'Clause Minimalization')
        ],
        'dpll': [
            ('--pure', 'Pure Literal Elimination')
        ]
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

    generators = {
        'Random': 'gens/knf_gen.py',
        'PHP': 'gens/php.py',
        'Pebbling': 'gens/pebbling.py'
    }
    
    run_path_dic = {
        'cdcl': 'abgabe5/cdcl.py',
        'dpll': 'abgabe4/dpll.py'
    }

    regex = re.compile(r"(c [a-zA-Z ]+:)")

    for solver, solver_generators in nsolvers.items():
        run_path = run_path_dic[solver]
        for generator, n_values in solver_generators.items(): 
            gen_path = generators[generator]
            for n in n_values:
                folder_name = f"temp/{solver}_{generator}_{n}_all_flags_enabled"
                os.makedirs(folder_name, exist_ok=True)

                print(f"Running benchmark for solver: {solver}, generator: {generator}, n: {n}, all flags enabled")

                # Run with all flags enabled
                flags = [flag[0] for flag in solvers[solver]]
                stats_sum_enabled = {}
                stats_count_enabled = {}
                total_time_enabled = 0

                tries = args.tries if generator == "Random" else 1
                printProgressBar(0, tries, prefix='Progress:', suffix='Complete', length=50)

                for i in range(tries):
                    if generator == "Random":
                        subprocess.run(['python3', gen_path, str(n), str(round(4.0 * n)), "3"], stdout=subprocess.DEVNULL)
                    elif generator == "PHP":
                        subprocess.run(['python3', gen_path, str(n)], stdout=subprocess.DEVNULL)
                    elif generator == "Pebbling":
                        subprocess.run(['python3', gen_path, str(n)], stdout=subprocess.DEVNULL)
                    else:
                        print("Invalid generator")
                        sys.exit(1)

                    result, stdout, stderr, timeSolver = run_solver(run_path, flags)
                    total_time_enabled += timeSolver

                    with open(f"{folder_name}/result_all_flags_enabled_{i}.txt", "w") as f:
                        f.write(f"Run {i + 1} of {tries}\n")
                        f.write(f"All flags enabled\n")
                        f.write(f"Solver exit code: {result}\n")
                        f.write(f"Execution time: {timeSolver:.2f} seconds\n")
                        f.write(f"Standard Output:\n{stdout}\n")
                        f.write(f"Standard Error:\n{stderr}\n")

                    with open(f"{folder_name}/result_all_flags_enabled_{i}.txt", "r") as file:
                        run_stats_sum, run_stats_count = aggregate_statistics(file, regex)
                        for stat in run_stats_sum:
                            stats_sum_enabled[stat] = stats_sum_enabled.get(stat, 0) + run_stats_sum[stat]
                            stats_count_enabled[stat] = stats_count_enabled.get(stat, 0) + run_stats_count[stat]

                    printProgressBar(i + 1, tries, prefix='Progress:', suffix='Complete', length=50)

                avg_stats_enabled = {stat: stats_sum_enabled[stat] / stats_count_enabled[stat] for stat in stats_sum_enabled}

                with open(f"{folder_name}/average_results_all_flags_enabled.txt", "w") as f:
                    f.write(f"Average results over {tries} runs:\n")
                    f.write(f"All flags enabled\n")
                    f.write(f"Total Execution time: {total_time_enabled:.2f} seconds\n")
                    for stat in avg_stats_enabled:
                        f.write(f"Average {stat}: {avg_stats_enabled[stat]:.2f}\n")

                for flag, flag_desc in solvers[solver]:
                    flag_str = flag[2:]  # Remove '--' from flag for file naming
                    folder_name = f"temp/{solver}_{generator}_{n}_{flag_str}_off" if flag_str else f"temp/{solver}_{generator}_{n}_default_off"
                    os.makedirs(folder_name, exist_ok=True)

                    total_time_disabled = 0
                    stats_sum_disabled = {}
                    stats_count_disabled = {}

                    print(f"Running benchmark for solver: {solver}, generator: {generator}, n: {n}, flag off: {flag_desc}")

                    tries = args.tries if generator == "Random" else 1
                    printProgressBar(0, tries, prefix='Progress:', suffix='Complete', length=50)

                    for i in range(tries):
                        if generator == "Random":
                            subprocess.run(['python3', gen_path, str(n), str(round(4.0 * n)), "3"], stdout=subprocess.DEVNULL)
                        elif generator == "PHP":
                            subprocess.run(['python3', gen_path, str(n)], stdout=subprocess.DEVNULL)
                        elif generator == "Pebbling":
                            subprocess.run(['python3', gen_path, str(n)], stdout=subprocess.DEVNULL)
                        else:
                            print("Invalid generator")
                            sys.exit(1)

                        # Run with the flag disabled
                        result, stdout, stderr, timeSolver = run_solver(run_path, [f for f in flags if f != flag])
                        total_time_disabled += timeSolver

                        with open(f"{folder_name}/result_{flag_str}_off_disabled_{i}.txt", "w") as f:
                            f.write(f"Run {i + 1} of {tries}\n")
                            f.write(f"Flag '{flag_desc}' disabled\n")
                            f.write(f"Solver exit code: {result}\n")
                            f.write(f"Execution time: {timeSolver:.2f} seconds\n")
                            f.write(f"Standard Output:\n{stdout}\n")
                            f.write(f"Standard Error:\n{stderr}\n")

                        with open(f"{folder_name}/result_{flag_str}_off_disabled_{i}.txt", "r") as file:
                            run_stats_sum, run_stats_count = aggregate_statistics(file, regex)
                            for stat in run_stats_sum:
                                stats_sum_disabled[stat] = stats_sum_disabled.get(stat, 0) + run_stats_sum[stat]
                                stats_count_disabled[stat] = stats_count_disabled.get(stat, 0) + run_stats_count[stat]

                        printProgressBar(i + 1, tries, prefix='Progress:', suffix='Complete', length=50)

                    avg_stats_disabled = {stat: stats_sum_disabled[stat] / stats_count_disabled[stat] for stat in stats_sum_disabled}

                    with open(f"{folder_name}/average_results_{flag_str}_off.txt", "w") as f:
                        f.write(f"Average results over {tries} runs:\n")
                        f.write(f"Flag '{flag_desc}' disabled\n")
                        f.write(f"Total Execution time: {total_time_disabled:.2f} seconds\n")
                        for stat in avg_stats_disabled:
                            f.write(f"Average {stat}: {avg_stats_disabled[stat]:.2f}\n")

    print("All tests completed")