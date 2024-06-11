import subprocess
import argparse
import time
import sys
import os

def run_cadical():
    start_time = time.time()
    result = subprocess.call(['cadical/build/cadical', "output.cnf"], stdout=subprocess.DEVNULL)
    end_time = time.time()
    return result, end_time - start_time

def run_solver(solver_path):
    start_time = time.time()    
    result = subprocess.call(['python3', solver_path, "--input",  "output.cnf"], stdout=subprocess.DEVNULL)
    end_time = time.time()
    return result, end_time - start_time

def run_drat_trim():
    result = subprocess.call(["./drat-trim/drat-trim", "output.cnf", "unsat.drat"], stdout=subprocess.DEVNULL)
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Run CaDiCaL and custom solver with a CNF file')
    parser.add_argument('--solver', '-s', required=True, help='Path to custom solver script')
    parser.add_argument('-n', type=int, default=10, help='Number of variables (default: 10)')
    parser.add_argument('--tries', '-t', type=int, default=10, help='Number of tries (default: 10)')
    args = parser.parse_args()
    statTimeCad = 0
    statTimeSolver = 0
    
    for i in range(args.tries):
        subprocess.run(['python3', 'abgabe1/knf_gen.py', str(args.n), str(round(3.8 * int(args.n))), "3"], stdout=subprocess.DEVNULL)
        resultCad, timeCad = run_cadical()
        statTimeCad += timeCad
        resultSolver, timeSolver = run_solver(args.solver)
        statTimeSolver += timeSolver
        print("Cadical: ", resultCad, "; Solver: ", resultSolver)
        
        if (resultSolver != resultCad):
            print()
            print("Error: Solver output does not match Cadical output")
            print("Cadical: ", resultCad)
            print("Solver: ", resultSolver)
            sys.exit(1)
            
        if 'cdcl.py' in args.solver and resultCad == 20:
            resultDrat = run_drat_trim()
            if resultDrat != 0:
                print()
                print(f"Error: {args.solver} did not produce a correct proof")
                sys.exit(1)
            
    print("All tests passed")
    print("Time spent in Cadical: ", statTimeCad, "s")
    print("Time spent in Solver: ", statTimeSolver, "s")
    os.remove("output.cnf")
    if os.path.exists("unsat.drat"):
        os.remove("unsat.drat")
        