import argparse
from typing import List, Tuple, Optional

class SATSolver:
    def __init__(self):
        self.unit_prop_count = 0
        self.decision_count = 0

    def unit_propagation(self, cnf: List[List[int]], assignments: List[int]) -> Tuple[List[List[int]], List[int]]:
        """
        Perform unit propagation on the CNF formula.
        
        Args:
        cnf: The CNF formula represented as a list of clauses.
        assignments: Current variable assignments.
        
        Returns:
        Updated CNF and assignments after unit propagation.
        """
        i = 0
        while i < len(cnf):
            if len(cnf[i]) == 1:
                literal = cnf[i][0]
                cnf, assignments = self.assign_variable(cnf, assignments, literal)
                i = 0  # Restart from the beginning
                continue
            i += 1
        return cnf, assignments

    def assign_variable(self, cnf: List[List[int]], assignments: List[int], literal: int) -> Tuple[List[List[int]], List[int]]:
        """
        Assign a value to a variable and simplify the CNF formula.
        
        Args:
        cnf: The CNF formula represented as a list of clauses.
        assignments: Current variable assignments.
        literal: The literal to assign (positive or negative integer).
        
        Returns:
        Updated CNF and assignments after variable assignment.
        """
        self.unit_prop_count += 1
        if abs(literal) not in map(abs, assignments):
            assignments.append(literal)
        
        cnf = [clause for clause in cnf if literal not in clause]
        cnf = [[l for l in clause if l != -literal] for clause in cnf]
        return cnf, assignments

    def solve_2sat(self, cnf: List[List[int]], assignments: List[int]) -> Tuple[bool, List[int]]:
        """
        Solve the 2-SAT problem using a recursive approach.
        
        Args:
        cnf: The CNF formula represented as a list of clauses.
        assignments: Current variable assignments.
        
        Returns:
        A tuple (is_satisfiable, assignments)
        """
        cnf, assignments = self.unit_propagation(cnf, assignments)
        
        if not cnf:
            return True, assignments
        if [] in cnf:
            return False, assignments

        literal = cnf[0][0]
        self.decision_count += 1

        # Try assigning False to the literal
        cnf_copy, assignments_copy = self.assign_variable(cnf.copy(), assignments.copy(), -literal)
        if self.solve_2sat(cnf_copy, assignments_copy)[0]:
            return True, assignments_copy

        # Try assigning True to the literal
        cnf_copy, assignments_copy = self.assign_variable(cnf, assignments, literal)
        if self.solve_2sat(cnf_copy, assignments_copy)[0]:
            return True, assignments_copy

        return False, assignments

    def read_cnf(self, filename: str) -> List[List[int]]:
        """
        Read a CNF formula from a file.
        
        Args:
        filename: The name of the file containing the CNF formula.
        
        Returns:
        The CNF formula represented as a list of clauses.
        """
        cnf = []
        with open(filename, "r") as f:
            for line in f:
                if line.startswith(("c", "p")):
                    continue
                clause = [int(literal) for literal in line.split() if literal != '0']
                cnf.append(clause)
        return cnf

    def solve(self, filename: str = 'input.cnf') -> None:
        """
        Solve the SAT problem for the given input file and print the results.
        
        Args:
        filename: The name of the file containing the CNF formula.
        """
        print(f"c Filename: {filename}")
        cnf = self.read_cnf(filename)
        is_satisfiable, assignments = self.solve_2sat(cnf, [])
        
        print(f"s {'SATISFIABLE' if is_satisfiable else 'UNSATISFIABLE'}")
        if is_satisfiable:
            print(f"c {' '.join(map(str, sorted(assignments, key=abs)))}")
        print(f"c Unit Propagations: {self.unit_prop_count}")
        print(f"c Decisions: {self.decision_count}")

def main():
    parser = argparse.ArgumentParser(description='2-SAT Solver')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)')
    args = parser.parse_args()

    solver = SATSolver()
    solver.solve(args.input)

if __name__ == "__main__":
    main()