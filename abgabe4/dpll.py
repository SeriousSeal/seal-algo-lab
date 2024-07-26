import argparse
import logging
import time
import resource

class DPLL_Solver:
    def __init__(self, flagPureLiteralElimination):
        self.flagPureLiteralElimination = flagPureLiteralElimination
        self.unit_propagations = 0
        self.decisions = 0
        self.pure_literal_eliminations = 0

    def unit_propagation(self, cnf, assignment):
        """
        Performs unit propagation on the given CNF formula and assignment.
        It iterates through each clause and checks if there is only one unassigned literal.
        If so, it assigns that literal to the assignment set and increments the unit_propagations counter.
        """
        for clause in cnf:  
            unassigned_literal = None
            num_unassigned = 0

            for literal in clause:
                if literal in assignment:
                    num_unassigned = 0
                    break
                if -literal in assignment:
                    continue
                
                unassigned_literal = literal
                num_unassigned += 1
        
            if num_unassigned == 1:
                assignment.add(unassigned_literal)
                self.unit_propagations += 1
                continue
    
        return assignment

    def pure_literal_elimination(self, cnf, assignment):
        """
        Performs pure literal elimination on the given CNF formula and assignment.
        It first collects all literals and their negations in the formula.
        Then, it checks if a literal and its negation are both not present in the assignment.
        If so, it adds the pure literal to the assignment and increments the pure_literal_eliminations counter.
        """
        if not self.flagPureLiteralElimination:
            return
        literals = set()
        literal_negations = {}
    
        # Collect all literals and their negations
        for clause in cnf:
            if not any(literal in assignment for literal in clause):
                for literal in clause:
                    literals.add(literal)
                    literal_negations[literal] = -literal
    
        # Process the literals
        for literal in literals:
            if literal_negations[literal] in assignment:
                continue
            if literal_negations[literal] not in literals:
                assignment.add(literal)
                self.pure_literal_eliminations += 1
    
        return assignment

    def get_decision_variable(self, cnf, assignment):
        """
        Selects the next decision variable for the DPLL algorithm.
        It keeps track of the number of decisions made using the decisions counter.
        """
        self.decisions += 1
        all_literals = {literal for clause in cnf for literal in clause}
        unassigned_literals = all_literals - assignment - {-literal for literal in assignment}
        return next(iter(unassigned_literals))

    def is_finished(self, cnf, assignment):
        """
        Checks the current state of the CNF formula and assignment:
        - Returns 1 if the formula is satisfiable
        - Returns -1 if the formula is unsatisfiable
        - Returns 0 if the formula is not yet finished
        """
        for clause in cnf:
            if all(-literal in assignment for literal in clause):
                return -1 
            if any(literal in assignment for literal in clause):
                continue  
            return 0 
        return 1 

    def DPLL(self, cnf, assignment=set()):
        """
        Implements the DPLL algorithm to solve the given CNF formula.
        It first performs unit propagation and pure literal elimination until no more can be done.
        Then, it checks if the formula is satisfiable, unsatisfiable, or still needs more decisions.
        If more decisions are needed, it recursively calls the DPLL function with the new assignment.
        """
        while True:
            before_len = len(assignment)
            self.pure_literal_elimination(cnf, assignment)
            self.unit_propagation(cnf, assignment)
            if len(assignment) == before_len:
                break  
        
        finished = self.is_finished(cnf, assignment)
        if finished == 1:
            return True, assignment
        elif finished == -1:
            return False, None
        
        x = self.get_decision_variable(cnf, assignment)
        res_neg = self.DPLL(cnf, assignment | {-x})  
        if res_neg[0]:
            return res_neg
        return self.DPLL(cnf, assignment | {x}) 
    
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
    statTimeStart = time.time()
    cnf = solver.read_cnf(args.input)
    sat, v = solver.DPLL(cnf)
    statTimeEnd = time.time()
    peakMemoryMB = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024

    # Print results
    print("s", "SATISFIABLE" if sat else "UNSATISFIABLE")

    # Print statistics
    print ("c Time:", statTimeEnd - statTimeStart)
    print("c Peak Memory (MB):", peakMemoryMB)
    print("c v:", sorted(v) if v is not None else v)
    print("c Number of Unit Propagations:", solver.unit_propagations)
    print("c Number of Decisions:", solver.decisions)
    print("c Number of Pure Literal Eliminations:", solver.pure_literal_eliminations)

    exit(10 if sat else 20)