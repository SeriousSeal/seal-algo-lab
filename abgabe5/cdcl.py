import argparse
from copy import deepcopy
import resource
import time


class CDCLSolver:
    def __init__(self):
        self.decisions = 0
        self.unit_propagations = 0
        self.conflicts = 0

    def getAllLiterals(self, cnf):
        return set(abs(literal) for clause in cnf for literal in clause)

    def decide(self, cnf, v, decision_level):
        self.decisions += 1
        assigned_literals_set = set(v[0])
        unassigned_literal = next(
            (literal for clause in cnf for literal in clause if literal not in assigned_literals_set and -literal not in assigned_literals_set), 
            None
        )

        if unassigned_literal is not None:
            v[0].append(unassigned_literal)
            v[1].append(decision_level)
            return v

        raise Exception("All literals are assigned")

    def propagate(self, cnf, v, decision_level):
        unit_propagation_occurred = True
        while unit_propagation_occurred:
            unit_propagation_occurred = False
            for clause in cnf:
                num_unassigned = 0
                unassigned_literal = 0

                for literal in clause:
                    if literal in v[0]:
                        num_unassigned = -1
                        break
                    elif -literal not in v[0]:
                        unassigned_literal = literal
                        num_unassigned += 1

                if num_unassigned == 1:
                    v[0].append(unassigned_literal)
                    v[1].append(decision_level)
                    self.unit_propagations += 1
                    unit_propagation_occurred = True
                    break  # Exit the loop to restart propagation
                
                if num_unassigned == 0:
                    self.conflicts += 1
                    return v, clause

        return v, None

    def checkConflict(self, v):
        max_decision_level = 1
        decision_literals = []
        for literal, level in zip(v[0], v[1]):
            if level >= max_decision_level:
                max_decision_level = level + 1
                decision_literals.append(literal)

        c_learned = [-l for l in decision_literals]
        return c_learned, max_decision_level - 2

    def applyRestartPolicy(self, cnf, v, decision_level, og_cnf):
        return cnf, v, decision_level

    def backtrack(self, v, new_decision_level):
       index = next((i for i, level in enumerate(v[1]) if level > new_decision_level), len(v[1]))
       return (v[0][:index], v[1][:index])


    def CDCL(self, cnf):
        original_cnf = deepcopy(cnf)
        decision_level = 0
        all_literals = self.getAllLiterals(cnf)
        assignment = ([], [])

        while len(assignment[0]) < len(all_literals):
            decision_level += 1
            assignment = self.decide(cnf, assignment, decision_level)
            while True:
                assignment, conflict_clause = self.propagate(cnf, assignment, decision_level)
                if conflict_clause is None:
                    break
                if decision_level == 0:
                    return False, cnf[len(original_cnf):]

                learned_clause, decision_level = self.checkConflict(assignment)
                cnf.append(learned_clause)
                assignment = self.backtrack(assignment, decision_level)

            cnf, assignment, decision_level = self.applyRestartPolicy(cnf, assignment, decision_level, original_cnf)

        return True, assignment[0]

    def read_cnf(self, filename: str) -> set[frozenset[int]]:
        cnf = []
        with open(filename, "r") as f:
            lines = f.readlines()
            for line in lines:
                # ignore comments and header
                if line.startswith("c") or line.startswith("p"):
                    continue
                clause = set()
                literals = line.split()
                for literal in literals:
                    literal = int(literal)
                    if literal == 0:
                        break
                    clause.add(literal)
                cnf.append(frozenset(clause))
        return cnf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Implements CDCL Algorithm')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)')
    args = parser.parse_args()

    solver = CDCLSolver()

    stat_time_start = time.time()
    cnf = solver.read_cnf(args.input)
    sat, v = solver.CDCL(cnf)
    stat_time_end = time.time()
    stat_peak_memory_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    
    
    if not sat:
        with open("unsat.drat", "w") as f:
            for clause in v:
                f.write(" ".join(map(str, clause)) + " 0"+ "\n")

    print("s", "SATISFIABLE" if sat else "UNSATISFIABLE")
    print("c Time:", stat_time_end - stat_time_start)
    print("c Peak Memory (MB):", stat_peak_memory_mb)
    print("c Number of Unit Propagations:", solver.unit_propagations)
    print("c Number of Decisions:", solver.decisions)
    print("c Number of Conflicts:", solver.conflicts)
    exit(10 if sat else 20)