import argparse
import logging
import time
import resource

class DPLL_Solver:
    def __init__(self, enable_pure_literal_elimination):
        self.enable_pure_literal_elimination = enable_pure_literal_elimination
        self.unit_propagation_count = 0
        self.decision_count = 0
        self.pure_literal_elimination_count = 0
        
    def unit_propagation(self, cnf, assigned_literals):
        """
        Simplifies the given CNF formula based on current variable assignments.
        Identifies unit clauses and updates the assignments accordingly.
        """
        for clause in cnf:
            unresolved_literals = set()
            sole_unassigned_literal = None

            for literal in clause:
                if literal in assigned_literals:
                    unresolved_literals.clear()
                    break
                if -literal in assigned_literals:
                    continue
                
                unresolved_literals.add(literal)
                sole_unassigned_literal = literal

            if len(unresolved_literals) == 1:
                assigned_literals.add(sole_unassigned_literal)
                self.unit_propagation_count += 1

        return assigned_literals
        
    def pure_literal_elimination(self, cnf, assigned_literals):
        """
        Performs pure literal elimination on the given CNF formula and assignment.
        It first collects all literals and their negations in the formula.
        Then, it checks if a literal and its negation are both not present in the assignment.
        If so, it adds the pure literal to the assignment and increments the pure_literal_elimination_count.
        """
        if not self.enable_pure_literal_elimination:
            return
        all_literals = set()
        literal_negations = {}
    
        # Collect all literals and their negations
        for clause in cnf:
            if not any(literal in assigned_literals for literal in clause):
                for literal in clause:
                    all_literals.add(literal)
                    literal_negations[literal] = -literal
    
        # Process the literals
        for literal in all_literals:
            if literal_negations[literal] in assigned_literals:
                continue
            if literal_negations[literal] not in all_literals:
                assigned_literals.add(literal)
                self.pure_literal_elimination_count += 1
    
        return assigned_literals

    def get_decision_variable(self, cnf, assigned_literals):
        """
        Selects the next decision variable for the DPLL algorithm.
        It keeps track of the number of decisions made using the decision_count.
        """
        self.decision_count += 1
        all_literals = {literal for clause in cnf for literal in clause}
        unassigned_literals = all_literals - assigned_literals - {-literal for literal in assigned_literals}
        return next(iter(unassigned_literals))

    def is_finished(self, cnf, assigned_literals):
        """
        Checks the current state of the CNF formula and assignment:
        - Returns 1 if the formula is satisfiable
        - Returns -1 if the formula is unsatisfiable
        - Returns 0 if the formula is not yet finished
        """
        for clause in cnf:
            if all(-literal in assigned_literals for literal in clause):
                return -1 
            if any(literal in assigned_literals for literal in clause):
                continue  
            return 0 
        return 1 

    def DPLL(self, cnf, assigned_literals=set()):
        """
        Implements the DPLL algorithm to solve the given CNF formula.
        It first performs unit propagation and pure literal elimination until no more can be done.
        Then, it checks if the formula is satisfiable, unsatisfiable, or still needs more decisions.
        If more decisions are needed, it recursively calls the DPLL function with the new assignment.
        """
        while True:
            before_len = len(assigned_literals)
            self.pure_literal_elimination(cnf, assigned_literals)
            self.unit_propagation(cnf, assigned_literals)
            if len(assigned_literals) == before_len:
                break  
        
        finished = self.is_finished(cnf, assigned_literals)
        if finished == 1:
            return True, assigned_literals
        elif finished == -1:
            return False, None
        
        decision_var = self.get_decision_variable(cnf, assigned_literals)
        result_negative = self.DPLL(cnf, assigned_literals | {-decision_var})  
        if result_negative[0]:
            return result_negative
        return self.DPLL(cnf, assigned_literals | {decision_var}) 
    
    def read_cnf(self, filename: str) -> set[frozenset[int]]:
        """
        Reads a CNF formula from the given file and returns it as a set of frozen sets of integers.
        Each frozen set represents a clause, and the set contains all the clauses.
        """
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
    parser = argparse.ArgumentParser(description='Implements DPLL Algorithm')
    parser.add_argument('--pure', '-p', action='store_true', help='Enable Pure Literal Elimination')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)')
    args = parser.parse_args()

    solver = DPLL_Solver(args.pure)
    start_time = time.time()
    cnf = solver.read_cnf(args.input)
    is_satisfiable, solution = solver.DPLL(cnf)
    end_time = time.time()
    peak_memory_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    # Print results
    print("s", "SATISFIABLE" if is_satisfiable else "UNSATISFIABLE")

    # Print statistics
    print("c Time:", end_time - start_time)
    print("c Peak Memory (MB):", peak_memory_mb)
    print("c Solution:", sorted(solution) if solution is not None else solution)
    print("c Number of Unit Propagations:", solver.unit_propagation_count)
    print("c Number of Decisions:", solver.decision_count)
    print("c Number of Pure Literal Eliminations:", solver.pure_literal_elimination_count)

    exit(10 if is_satisfiable else 20)