import argparse
import time
import resource

class DPLL_Solver:
    def __init__(self, flagPureLiteralElimination):
        self.flagPureLiteralElimination = flagPureLiteralElimination
        self.unit_propagations = 0
        self.decisions = 0
        self.pure_literal_eliminations = 0

    def complete_unit_propagation(self, cnf, v):
        for clause in cnf.copy():  
            unassigned_literal = None
            num_unassigned = 0

            for literal in clause:
                if literal in v:
                    num_unassigned = 0
                    break
                if -literal in v:
                    continue
                
                unassigned_literal = literal
                num_unassigned += 1
        
            if num_unassigned == 1:
                v.add(unassigned_literal)
                self.unit_propagations += 1
                self.complete_unit_propagation(cnf, v)  
                break
    
        return v

    def pure_literal_elimination(self, cnf, v):
        if not self.flagPureLiteralElimination:
            return
        unassigned_literals = {literal for clause in cnf for literal in clause if literal not in v and -literal not in v}
        for literal in unassigned_literals:
            if -literal not in unassigned_literals:
                v.add(literal)
                self.pure_literal_eliminations += 1

    def get_decision_variable(self, cnf, v):
        self.decisions += 1
        all_literals = {literal for clause in cnf for literal in clause}
        unassigned_literals = all_literals - v - {-literal for literal in v}
        return next(iter(unassigned_literals))

    def is_finished(self, cnf, v):
        for clause in cnf:
            if all(-literal in v for literal in clause):
                return -1 
            if any(literal in v for literal in clause):
                continue  
            return 0 
        return 1 

    def DPLL(self, cnf, v=set()):
        while True:
            before_len = len(v)
            self.pure_literal_elimination(cnf, v)
            self.complete_unit_propagation(cnf, v)
            if len(v) == before_len:
                break  
        
        finished = self.is_finished(cnf, v)
        if finished == 1:
            return True, v
        elif finished == -1:
            return False, None
        
        x = self.get_decision_variable(cnf, v)
        res_neg = self.DPLL(cnf, v | {-x})  
        if res_neg[0]:
            return res_neg
        return self.DPLL(cnf, v | {x}) 
    
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
    parser = argparse.ArgumentParser(description='Implements DPLL Algorithm')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)')
    args = parser.parse_args()
    
    solver = DPLL_Solver(True)
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