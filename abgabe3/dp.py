import argparse
import sys
import time
import heapq

class DavisPutnamSolver:
    def __init__(self):
        self.start_time = time.time()
        self.unit_propagations = 0
        self.added_clauses = 0
        self.pure_literal_eliminations = 0
        self.subsumptions = 0

    def to_frozenset(self, lst):
        return frozenset(lst)

    # remove all clauses that are strictly larger than another clause
    def subsumption_elimination(self, cnf: set[frozenset[int]]) -> set[frozenset[int]]:
        cnf_list = list(cnf)
        i = 0
        while i < len(cnf_list):
            current_clause = cnf_list[i]
            j = i + 1
            while j < len(cnf_list):
                if current_clause.issubset(cnf_list[j]):
                    cnf_list.pop(j)
                    i = 0
                    self.subsumptions += 1
                    break
                j += 1
            i += 1
        return set(cnf_list)

    # remove tautologies and duplicates
    def remove_tautologies_and_duplicates(self, cnf: set[frozenset[int]]) -> set[frozenset[int]]:
        cnf = {clause for clause in cnf if not any(-literal in clause for literal in clause)}
        return cnf

    # remove variable if it exists in only 1 polarity
    def pure_literal_elimination(self, cnf: set[frozenset[int]]) -> set[frozenset[int]]:
        literals = {literal for clause in cnf for literal in clause}
        clauses_before = len(cnf)
        for literal in literals:
            if -literal not in literals:
                cnf = {clause for clause in cnf if literal not in clause}
        self.pure_literal_eliminations += clauses_before - len(cnf)
        return cnf

    # repeat unit propagation until no more unit clauses are found
    def complete_unit_propagation(self, cnf: set[frozenset[int]]) -> set[frozenset[int]]:
        while True:
            unit_clauses = {clause for clause in cnf if len(clause) == 1}
            if not unit_clauses:
                break
            for clause in unit_clauses:
                literal = next(iter(clause))
                cnf = {c for c in cnf if literal not in c}
                cnf = {frozenset(l for l in c if l != -literal) for c in cnf}
                self.unit_propagations += 1
        return cnf

    # merge clauses without literal and its negation
    def mergeClauses(self, clause1: frozenset[int], clause2: frozenset[int], literal: int) -> set[frozenset[int]]:
        self.added_clauses += 1
        iterator = heapq.merge(clause1, clause2, key=abs)
        return {frozenset(l for l in iterator if l != literal and l != -literal)}

    def davis_putnam(self, cnf: set[frozenset[int]]) -> bool:
        while True:
            len_cnf = -1
            while len_cnf != len(cnf):
                len_cnf = len(cnf)
                cnf = self.complete_unit_propagation(cnf)
                cnf = self.remove_tautologies_and_duplicates(cnf)
                cnf = self.pure_literal_elimination(cnf)
                cnf = self.subsumption_elimination(cnf)
            if not cnf:
                return True
            if frozenset() in cnf:
                return False
            literal = next(iter(next(iter(cnf))))
            new_clauses = set()

            for c1 in cnf:
                if literal in c1:
                    for c2 in cnf:
                        if -literal in c2:
                            new_clauses |= self.mergeClauses(c1, c2, literal)
                if -literal in c1:
                    for c2 in cnf:
                        if literal in c2:
                            new_clauses |= self.mergeClauses(c1, c2, literal)
            cnf = new_clauses | {c for c in cnf if literal not in c and -literal not in c}

    def read_cnf(self, filename: str) -> set[frozenset[int]]:
        cnf = set()
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
                cnf.add(frozenset(clause))
        return cnf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Implements DP Algorithm')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)')
    args = parser.parse_args()

    solver = DavisPutnamSolver()
    cnf = solver.read_cnf(args.input)
    cnf = {solver.to_frozenset(c) for c in cnf}
    sat = solver.davis_putnam(cnf)

    # Print results
    print("s", "SATISFIABLE" if sat else "UNSATISFIABLE")

    # Print statistics
    print("c Number of Unit Propagations:", solver.unit_propagations)
    print("c Number of Added Clauses:", solver.added_clauses)
    print("c Number of Pure Literal Eliminations:", solver.pure_literal_eliminations)
    print("c Number of Subsumptions:", solver.subsumptions)
    exit(10 if sat else 20)
