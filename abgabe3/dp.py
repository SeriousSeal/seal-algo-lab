import argparse
from collections import defaultdict
import sys
import time
import heapq

class DavisPutnamSolver:
    def __init__(self):
        # Initialize counters for various operations
        self.unit_propagation_count = 0
        self.resolution_count = 0
        self.pure_literal_elimination_count = 0
        self.subsumption_count = 0

    def to_frozenset(self, clause):
        """
        Convert a clause to a frozenset.
        
        Args:
            clause: An iterable representing a clause.
        
        Returns:
            A frozenset representation of the clause.
        """
        return frozenset(clause)

    def perform_subsumption_elimination(self, cnf: set[frozenset[int]]) -> set[frozenset[int]]:
        """
        Perform subsumption elimination on the CNF formula.
        
        Args:
            cnf: A set of frozensets representing clauses in CNF.
        
        Returns:
            A new set of frozensets with subsumed clauses removed.
        """
        sorted_clauses = sorted(cnf, key=len)
        i = 0
        while i < len(sorted_clauses):
            current_clause = sorted_clauses[i]
            j = i + 1
            subsumed = False
            while j < len(sorted_clauses):
                if current_clause.issubset(sorted_clauses[j]):
                    sorted_clauses.pop(j)
                    self.subsumption_count += 1
                elif sorted_clauses[j].issubset(current_clause):
                    subsumed = True
                    break
                else:
                    j += 1
            if subsumed:
                sorted_clauses.pop(i)
            else:
                i += 1
        return set(sorted_clauses)

    def remove_tautologies(self, cnf: set[frozenset[int]]) -> set[frozenset[int]]:
        """
        Remove tautological clauses from the CNF formula.
        
        Args:
            cnf: A set of frozensets representing clauses in CNF.
        
        Returns:
            A new set of frozensets with tautologies removed.
        """
        return {clause for clause in cnf if not any(-literal in clause for literal in clause)}

    def perform_pure_literal_elimination(self, cnf: set[frozenset[int]], literal_counts: dict) -> set[frozenset[int]]:
        """
        Perform pure literal elimination on the CNF formula.
        
        Args:
            cnf: A set of frozensets representing clauses in CNF.
            literal_counts: A dictionary counting occurrences of each literal.
        
        Returns:
            A new set of frozensets with clauses containing pure literals removed.
        """
        pure_literals = {lit for lit, count in literal_counts.items() if -lit not in literal_counts}
        clauses_before = len(cnf)
        cnf = {clause for clause in cnf if not clause & pure_literals}
        self.pure_literal_elimination_count += clauses_before - len(cnf)
        return cnf

    def perform_unit_propagation(self, cnf: set[frozenset[int]], literal_counts: dict) -> set[frozenset[int]]:
        """
        Perform unit propagation on the CNF formula.
        
        Args:
            cnf: A set of frozensets representing clauses in CNF.
            literal_counts: A dictionary counting occurrences of each literal.
        
        Returns:
            A new set of frozensets after unit propagation.
        """
        unit_clauses = [clause for clause in cnf if len(clause) == 1]
        while unit_clauses:
            unit = unit_clauses.pop()
            literal = next(iter(unit))
            cnf = {c for c in cnf if literal not in c}
            cnf = {frozenset(l for l in c if l != -literal) for c in cnf}
            self.unit_propagation_count += 1
            literal_counts[literal] -= 1
            if literal_counts[literal] == 0:
                del literal_counts[literal]
            literal_counts[-literal] = 0
            unit_clauses.extend([c for c in cnf if len(c) == 1])
        return cnf

    def resolve_clauses(self, clause1: frozenset[int], clause2: frozenset[int], literal: int) -> set[frozenset[int]]:
        """
        Resolve two clauses on a given literal.
        
        Args:
            clause1, clause2: Frozensets representing the clauses to resolve.
            literal: The literal to resolve on.
        
        Returns:
            A set containing the resolved clause (if not tautological).
        """
        self.resolution_count += 1
        merged = heapq.merge(clause1, clause2, key=abs)
        return {frozenset(l for l in merged if l != literal and l != -literal)}

    def select_literal(self, literal_counts: dict) -> int:
        """
        Select a literal for branching based on occurrence counts.
        
        Args:
            literal_counts: A dictionary counting occurrences of each literal.
        
        Returns:
            The selected literal (an integer).
        """
        return max(literal_counts, key=lambda l: literal_counts[l] + literal_counts.get(-l, 0))

    def davis_putnam(self, cnf: set[frozenset[int]]) -> bool:
        """
        Implement the Davis-Putnam algorithm for SAT solving.
        
        Args:
            cnf: A set of frozensets representing clauses in CNF.
        
        Returns:
            Boolean indicating whether the formula is satisfiable.
        """
        literal_counts = defaultdict(int)
        for clause in cnf:
            for lit in clause:
                literal_counts[lit] += 1

        while True:
            prev_cnf_size = -1
            while prev_cnf_size != len(cnf):
                prev_cnf_size = len(cnf)
                cnf = self.perform_unit_propagation(cnf, literal_counts)
                cnf = self.remove_tautologies(cnf)
                cnf = self.perform_pure_literal_elimination(cnf, literal_counts)
                cnf = self.perform_subsumption_elimination(cnf)

            if not cnf:
                return True  # SAT
            if frozenset() in cnf:
                return False  # UNSAT

            chosen_literal = self.select_literal(literal_counts)
            new_clauses = set()

            pos_clauses = [c for c in cnf if chosen_literal in c]
            neg_clauses = [c for c in cnf if -chosen_literal in c]

            for c1 in pos_clauses:
                for c2 in neg_clauses:
                    new_clauses |= self.resolve_clauses(c1, c2, chosen_literal)

            cnf = new_clauses | {c for c in cnf if chosen_literal not in c and -chosen_literal not in c}
            
            for clause in new_clauses:
                for lit in clause:
                    literal_counts[lit] += 1

            literal_counts[chosen_literal] = 0
            literal_counts[-chosen_literal] = 0

    def read_cnf_file(self, filename: str) -> set[frozenset[int]]:
        """
        Read a CNF formula from a file.
        
        Args:
            filename: The name of the file to read from.
        
        Returns:
            A set of frozensets representing the CNF formula.
        """
        cnf = set()
        with open(filename, "r") as f:
            for line in f:
                if line.startswith("c") or line.startswith("p"):
                    continue  # Skip comments and problem line
                clause = frozenset(int(lit) for lit in line.split()[:-1])  # Last 0 is delimiter
                if clause:  # Ignore empty clauses
                    cnf.add(clause)
        return cnf

if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(description='Davis-Putnam SAT Solver')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input CNF file (default: input.cnf)')
    args = parser.parse_args()
    
    # Measure execution time
    start_time = time.time()
    
    # Create solver instance and solve the problem
    solver = DavisPutnamSolver()
    cnf = solver.read_cnf_file(args.input)
    is_satisfiable = solver.davis_putnam(cnf)
    
    end_time = time.time()
    duration = end_time - start_time

    # Print results
    print("s", "SATISFIABLE" if is_satisfiable else "UNSATISFIABLE")

    # Print statistics
    print(f"c Number of Unit Propagations: {solver.unit_propagation_count}")
    print(f"c Number of Resolutions: {solver.resolution_count}")
    print(f"c Number of Pure Literal Eliminations: {solver.pure_literal_elimination_count}")
    print(f"c Number of Subsumptions: {solver.subsumption_count}")
    print(f"c Duration: {duration:.2f} seconds")
    
    # Exit with appropriate status code
    sys.exit(10 if is_satisfiable else 20)