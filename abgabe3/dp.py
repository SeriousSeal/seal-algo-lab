import argparse
import sys

class DavisPutnamSolver:
    def __init__(self):
        self.nUnit_propagations = 0
        self.nAdded_clauses = 0
        self.nPure_literal_eliminations = 0
        self.nSubsumed_clauses = 0

    # Combines two clauses by removing the literal and its negation, creating a new clause
    def merge_clauses(self, clause1, clause2, literal):
        self.nAdded_clauses += 1
        return [l for l in clause1 + clause2 if l != literal and l != -literal]

    #start dp algorithm
    def solve(self, cnf):    
        while True:
            len_cnf = -1
            while len_cnf != len(cnf):
                len_cnf = len(cnf)
                cnf = self.unit_propagation(cnf)
                cnf = self.remove_tautologies_and_duplicates(cnf)
                cnf = self.remove_pure_literals(cnf)
                cnf = self.subsume(cnf)
            if len(cnf) == 0:
                return True
            if [] in cnf:
                return False
            literal = cnf[0][0]
            new_clauses = []

            for i in range(len(cnf)):
                if literal in cnf[i]:
                    for j in range(i+1, len(cnf)):
                        if -literal in cnf[j]:
                            new_clauses.append(self.merge_clauses(cnf[i], cnf[j], literal))
                if -literal in cnf[i]:
                    for j in range(i+1, len(cnf)):
                        if literal in cnf[j]:
                            new_clauses.append(self.merge_clauses(cnf[i], cnf[j], literal))
            cnf = new_clauses + [c for c in cnf if literal not in c and -literal not in c]

    # Applies unit propagation to simplify the CNF formula by assigning values to unit clauses
    def unit_propagation(self, cnf):
        i = 0
        while i < len(cnf):
            if len(cnf[i]) == 1:
                literal = cnf[i][0]
                cnf = self.propagate_unit(cnf, literal)
                i = 0
                continue
            i += 1
        return cnf

    # Propagates the assignment of a literal through the CNF formula
    def propagate_unit(self, cnf, variable):
        self.nUnit_propagations += 1
        cnf = [c for c in cnf if variable not in c]
        cnf = [[l for l in c if l != -variable] for c in cnf]
        return cnf

    # Subsumes redundant clauses in the CNF formula
    def subsume(self, cnf):
        i = 0
        while i < len(cnf):
            c = cnf[i]
            for j in range(i+1, len(cnf)):
                if all([l in cnf[j] for l in c]):
                    cnf.pop(j)
                    i = 0
                    self.nSubsumed_clauses += 1
                    break
            i += 1
        return cnf
    
    # Removes tautologies and duplicates from the CNF formula
    def remove_tautologies_and_duplicates(self, cnf):
        cnf = [c for c in cnf if not any([l1 == -l2 for l1 in c for l2 in c])]
        cnf = sorted([sorted(c) for c in cnf])
        cnf = [cnf[i] for i in range(len(cnf)) if i == len(cnf)-1 or cnf[i] != cnf[i+1]] 
        return cnf

    # Removes pure literals (literals that only appear with one polarity) from the CNF formula
    def remove_pure_literals(self, cnf):
        literals = set([l for c in cnf for l in c])
        len_initial_cnf = len(cnf)
        for l in literals:
            if -l not in literals:
                cnf = self.propagate_unit(cnf, l)
        self.nPure_literal_eliminations += len_initial_cnf - len(cnf)
        return cnf
    
    # Reads a CNF file and returns its clauses
    def read_cnf(self, filename):
        cnf = []
        with open(filename, "r") as f:
            for line in f:
                if line.startswith(("c", "p")):
                    continue
                clause = []
                literals = line.split()

                for literal in literals:
                    literal = int(literal)
                    if literal == 0:
                        break
                    clause.append(literal)
                cnf.append(clause)
        return cnf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Implements 2-Sat Algorithm')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)')
    args = parser.parse_args()

    dp_solver = DavisPutnamSolver()
    cnf = dp_solver.read_cnf(args.input)
    sat = dp_solver.solve(cnf)

    # Print results
    print("s", "SATISFIABLE" if sat else "UNSATISFIABLE")

    # Print statistics
    print("c Number of Unit Propagations:", dp_solver.nUnit_propagations)
    print("c Number of Added Clauses:", dp_solver.nAdded_clauses)
    print("c Number of Pure Literal Eliminations:", dp_solver.nPure_literal_eliminations)
    print("c Number of Subsumptions:", dp_solver.nSubsumed_clauses)
