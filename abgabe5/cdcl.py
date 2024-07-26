import argparse
from collections import deque
from enum import Flag, auto
from functools import lru_cache
import logging
from assignments import CNF, Assignments, Literal
import resource
import time
from typing import  List, Set, Tuple, Union
import random
import math
import numpy as np

class SolverOptions(Flag):
    """Enum class to represent solver options."""
    VSIDS = auto()
    RESTARTS = auto()
    CLAUSE_LEARNING = auto()
    CLAUSE_DELETION = auto()
    CLAUSE_MINIMIZATION = auto()

class VSIDSHeuristic:
    """Implements the Variable State Independent Decaying Sum (VSIDS) heuristic."""
    def __init__(self):
        self.b = 2
        self.c = 1.05

    def decide(self, assignments: Assignments) -> Literal:
        """Choose the next unassigned variable based on VSIDS scores."""
        unassigned = [a for a in assignments.assignments if not a.is_assigned]
        return max(unassigned, key=lambda a: a.vsids_score).polarity if unassigned else None

    def update_scores(self, assignments: Assignments, conflict_literals: Set[Literal]) -> None:
        """Update VSIDS scores for literals involved in conflicts."""
        for literal in conflict_literals:
            assignment = assignments.get_assignment(literal)
            assignment.vsids_score += self.b
        self.b *= self.c

        if self.b > 10**30:
            for assignment in assignments.assignments:
                assignment.vsids_score /= self.b
            self.b = 1

class RandomHeuristic:
    """Implements a random decision heuristic."""
    def decide(self, assignments: Assignments) -> Literal:
        """Choose a random unassigned variable."""
        unassigned = [a for a in assignments.assignments if not a.is_assigned]
        return random.choice(unassigned).polarity if unassigned else None

class CDCLSolver:
    """Implements the Conflict-Driven Clause Learning (CDCL) SAT solver."""
    def __init__(self, options: SolverOptions) -> None:
        self.options = options
        self.decision_heuristic = VSIDSHeuristic() if SolverOptions.VSIDS in options else RandomHeuristic()
        
        # Initialize statistics
        self.unit_propagations = 0
        self.decisions = 0
        self.conflicts = 0
        self.old_conflicts = 0
        self.learned_clauses = 0
        self.deleted_clauses = 0
        self.minimalizations = 0
        self.max_length_learned_clause = 0
        self.restarts = 0
        
        # VSIDS parameters
        self.b = 2
        self.c = 1.05
        
        # Restart parameters
        self.k = 200
        self.luby_num = 100
        self.lbdLimit = 10
        self.lbdFactor = 1.1

    def decide(self, assignments: Assignments, decision_level: int) -> None:
        """Make a decision on the next variable to assign."""
        self.decisions += 1
        literal = self.decision_heuristic.decide(assignments)
        if literal:
            logging.info(f"Decision at level {decision_level}: {literal}")
            assignments.set_literal(literal, decision_level, [])
            
    def find_new_watch(self, clause, assignments_history):
        """Find a new literal to watch in the clause."""
        return next((j for j in range(2, len(clause)) if -clause[j] not in assignments_history), -1)

    def propagate(self, cnf: List[np.ndarray], assignments: Assignments, decision_level: int) -> Union[np.ndarray, None]:
        """Perform unit propagation and detect conflicts."""
        literals_propagate = deque([assignments.assignment_history[-1]])
        assignments_history = set(assignments.assignment_history)

        while literals_propagate:
            literal = -literals_propagate.pop()
            assignment = assignments.get_assignment(literal)
            watched_clause_indices = assignment.retrieve_watched_clauses(literal)

            i = 0
            while i < len(watched_clause_indices):
                clause_index = watched_clause_indices[i]
                clause = cnf[clause_index]

                if len(clause) < 2:
                    self.conflicts += 1
                    return clause

                own_index = 0 if clause[0] == literal else 1
                other_index = 1 - own_index
                other_literal = clause[other_index]

                if other_literal in assignments:
                    i += 1
                    continue

                j = self.find_new_watch(clause, assignments_history)

                if j != -1:
                    new_literal = clause[j]
                    clause[own_index], clause[j] = clause[j], clause[own_index]
                    assignment.discard_watched_clause(clause_index, literal)
                    assignments.get_assignment(new_literal).append_watched_clause(clause_index, new_literal)
                    watched_clause_indices.pop(i)
                else:
                    if -other_literal in assignments:
                        self.conflicts += 1
                        return clause
                    else:
                        self.unit_propagations += 1
                        assignments.set_literal(other_literal, decision_level, clause)
                        literals_propagate.append(other_literal)
                        assignments_history.add(other_literal)
                    i += 1

        return None

    def analyzeConflict(self, assignments: 'Assignments', conflict: List[int], decision_level: int) -> Tuple[List[int], int]:
        """Analyze a conflict and learn a new clause."""
        previous_level_literals: Set[Tuple[int, int]] = set()
        current_level_literals: Set[int] = set()
        all_literals: Set[int] = set()

        for literal in conflict:
            assignment = assignments.get_assignment(literal)
            level = assignment.decision_level
            if level == decision_level:
                current_level_literals.add(-literal)
            else:
                previous_level_literals.add((-literal, level))
            all_literals.add(-literal)

        if SolverOptions.CLAUSE_LEARNING in self.options:
            self._analyze_current_level(assignments, current_level_literals, previous_level_literals, all_literals, decision_level)
        else:
            self._analyze_decision_literal(assignments, current_level_literals, previous_level_literals, all_literals, decision_level)

        uip = current_level_literals.pop()
        learned_clause = [-uip] + [-literal for literal, _ in previous_level_literals]
        new_decision_level = max((level for _, level in previous_level_literals), default=0)

        if SolverOptions.VSIDS in self.options:
            self.decision_heuristic.update_scores(assignments, all_literals)

        self.learned_clauses += 1
        self.max_length_learned_clause = max(self.max_length_learned_clause, len(learned_clause))
        return learned_clause, new_decision_level

    def _analyze_current_level(self, assignments: 'Assignments', current_level_literals: Set[int], 
                               previous_level_literals: Set[Tuple[int, int]], all_literals: Set[int], decision_level: int):
        """Analyze the current decision level for 1UIP."""
        for literal in reversed(assignments.assignment_history):
            if len(current_level_literals) == 1:
                break
            if literal not in current_level_literals:
                continue
            parents = assignments.get_assignment(literal).parents
            for parent in parents:
                level = assignments.get_assignment(parent).decision_level
                if level == decision_level:
                    current_level_literals.add(parent)
                else:
                    previous_level_literals.add((parent, level))
                all_literals.add(parent)
            current_level_literals.remove(literal)

    def _analyze_decision_literal(self, assignments: 'Assignments', current_level_literals: Set[int], 
                                  previous_level_literals: Set[Tuple[int, int]], all_literals: Set[int], decision_level: int):
        """Analyze the decision literal for conflict resolution."""
        previous = None
        for literal in reversed(assignments.assignment_history):
            if assignments.get_assignment(literal).decision_level != decision_level:
                break
            if literal not in current_level_literals:
                continue
            parents = assignments.get_assignment(literal).parents
            for parent in parents:
                level = assignments.get_assignment(parent).decision_level
                if level == decision_level:
                    current_level_literals.add(parent)
                else:
                    previous_level_literals.add((parent, level))
                all_literals.add(parent)
            current_level_literals.remove(literal)
            previous = literal
        if previous is not None:
            current_level_literals.add(previous)

    @lru_cache(maxsize=1024)
    def luby(self, i: int) -> int:
        """Compute the i-th term of the Luby sequence."""
        k = math.floor(math.log(i, 2)) + 1
        if i == 2**k - 1:
            return 2**(k-1)
        return self.luby(i - 2**(k-1) + 1)

    def deleteClause(self, cnf: List[List[int]], assignments: 'Assignments', lbd: List[float], i: int) -> None:
        """Delete a clause from the CNF, update watched literals and LBD values."""
        self.deleted_clauses += 1

        clause_to_delete = cnf[i]
        for literal in clause_to_delete[:2]:
            assignments.get_assignment(literal).discard_watched_clause(i, literal)

        if i < len(cnf) - 1:
            cnf[i], cnf[-1] = cnf[-1], cnf[i]
            lbd[i], lbd[-1] = lbd[-1], lbd[i]
            for literal in cnf[i][:2]:
                assignments.get_assignment(literal).replace_watched_clause(len(cnf) - 1, i, literal)

        cnf.pop()
        lbd.pop()

    def apply_restart_policy(self, assignments: 'Assignments', cnf: List[List[int]], lbd: List[float], oldLength: int, decision_level: int) -> int:
        """Apply the restart policy to the SAT solver."""
        if not SolverOptions.RESTARTS in self.options:
            return decision_level

        conflicts_since_last_restart = self.conflicts - self.old_conflicts

        if conflicts_since_last_restart > self.luby_num * self.luby(self.restarts + 1):
            self.restarts += 1
            self.old_conflicts = self.conflicts
            self.backtrack(assignments, 0)
            
            if SolverOptions.CLAUSE_DELETION in self.options:
                i = len(cnf) - 1
                while i >= oldLength:
                    if lbd[i] > self.lbdLimit:
                        self.deleteClause(cnf, assignments, lbd, i)
                    i -= 1
                self.lbdLimit *= self.lbdFactor

            return 0

        return decision_level

    def backtrack(self, assignments: Assignments, decision_level: int) -> None:
        """Backtrack to a specified decision level by unassigning literals."""
        if not assignments.assignment_history:
            return

        literals_to_keep = 0
        for reverse_index, literal in enumerate(reversed(assignments.assignment_history)):
            level = assignments.get_assignment(literal).decision_level
            if level <= decision_level:
                literals_to_keep = len(assignments.assignment_history) - reverse_index
                break

        for literal in assignments.assignment_history[literals_to_keep:]:
            assignments.get_assignment(literal).is_assigned = False

        assignments.assignment_history = assignments.assignment_history[:literals_to_keep]
        
    def sort_learned_clause(self, learned_clause: List[int], assignments: Assignments) -> None:
        """Sorts the learned clause to ensure correct watched literals for backtracking."""
        for i, literal in enumerate(learned_clause):
            if not assignments.get_assignment(literal).is_assigned:
                learned_clause[0], learned_clause[i] = learned_clause[i], learned_clause[0]
                break

        history_indices = {-x: i for i, x in enumerate(assignments.assignment_history)}

        learned_clause[1:] = sorted(
            learned_clause[1:],
            key=lambda x: history_indices.get(-x, float('-inf')),
            reverse=True
        )

    @lru_cache(maxsize=1024)
    def check_parents_in_clause(self, parents: tuple, clause_set: frozenset) -> bool:
        """Check if all parents of a literal are in the clause."""
        return all(-parent in clause_set for parent in parents)

    def minimize_learned_clause(self, learned_clause: List[int], assignments: Assignments) -> None:
        """Minimizes the learned clause by removing redundant literals."""
        if not SolverOptions.CLAUSE_MINIMIZATION in self.options:
            return

        self.minimalizations += 1

        learned_clause_set = frozenset(learned_clause)
        to_remove = []

        for literal in learned_clause[1:]:
            parents = tuple(assignments.get_assignment(literal).parents)
            if parents and self.check_parents_in_clause(parents, learned_clause_set):
                to_remove.append(literal)

        for literal in to_remove:
            learned_clause.remove(literal)

    def learn_new_clause(self, cnf: List[List[int]], assignments: Assignments, lbd: List[float], learned_clause: List[int], decision_level: int, proof_cnf: List[List[int]]) -> None:
        """Learns a new clause, adds it to the CNF, and performs necessary updates."""
        self.learned_clauses += 1

        self.sort_learned_clause(learned_clause, assignments)
        self.minimize_learned_clause(learned_clause, assignments)

        cnf.append(learned_clause)
        proof_cnf.append(learned_clause)

        self.unit_propagations += 1

        clause_index = len(cnf) - 1
        for literal in learned_clause[:2]:
            assignments.get_assignment(literal).append_watched_clause(clause_index, literal)

        unique_decision_levels = set(assignments.get_assignment(literal).decision_level for literal in learned_clause)
        lbd.append(len(unique_decision_levels))

        assignments.set_literal(learned_clause[0], decision_level, learned_clause)
        
    @staticmethod
    def sign(x):
        """Return the sign of a number."""
        return -1 if x < 0 else 1

    @staticmethod
    def get_count(cnf: list[list[int]]) -> int:
        """Returns the number of unique literals in the CNF."""
        return len(set([abs(l) for c in cnf for l in c]))
    

    def CDCL(self, cnf: CNF) -> Union[bool, Tuple[bool, List[Literal]]]:
        """Solve the given CNF using the Conflict-Driven Clause Learning (CDCL) algorithm.
    
        Args:
            cnf: The CNF formula to solve.
    
        Returns:
            A tuple indicating the satisfiability of the CNF and either the assignment history or the proof CNF.
        """
        original_cnf_size = len(cnf)
        num_literals = self.get_count(cnf)
        proof_cnf = cnf.copy()
    
        # Initialize assignments and LBD list
        assignments = Assignments(num_literals, cnf)
        lbd: List[float] = [0] * original_cnf_size
        decision_level = 0
    
        while len(assignments.assignment_history) < num_literals:
            # Perform a decision
            decision_level += 1
            self.decide(assignments, decision_level)
    
            # Propagate the implications
            conflict_clause = self.propagate(cnf, assignments, decision_level)
    
            # Handle conflicts
            while conflict_clause is not None:
                # If conflict at the root level, CNF is unsatisfiable
                if decision_level == 0:
                    return False, proof_cnf[original_cnf_size:] + [[]]
    
                # Analyze the conflict and learn a new clause
                learned_clause, decision_level = self.analyzeConflict(assignments, conflict_clause, decision_level)
                self.backtrack(assignments, decision_level)
                self.learn_new_clause(cnf, assignments, lbd, learned_clause, decision_level, proof_cnf)
    
                # Continue propagation after learning a new clause
                conflict_clause = self.propagate(cnf, assignments, decision_level)
    
            # Apply the restart policy if necessary
            decision_level = self.apply_restart_policy(assignments, cnf, lbd, original_cnf_size, decision_level)
    
        # If no conflicts are found, the CNF is satisfiable
        return True, assignments.assignment_history

    def read_cnf(self, filename: str) -> List[List[int]]:
        """
        Reads a CNF file and converts it to a list of clauses.

        Args:
            filename: The name of the CNF file to read.

        Returns:
            A list of clauses, where each clause is a list of integers.
        """
        cnf: List[List[int]] = []
        vars: Set[int] = set()
    
        with open(filename, "r") as f:
            for line in f:
                # Skip comments and problem line
                if line.startswith("c") or line.startswith("p"):
                    continue
                clause: List[int] = []
                literals = line.split()
                for literal in literals:
                    literal = int(literal)
                    if literal == 0:
                        break
                    vars.add(abs(literal))
                    clause.append(literal)
                clause.sort(key=abs)
                cnf.append(clause)
    
        # Map variables to a continuous range 1, 2, ..., n
        var_map = {var: i + 1 for i, var in enumerate(sorted(vars))}
    
        for i, clause in enumerate(cnf):
            for j, lit in enumerate(clause):
                cnf[i][j] = self.sign(lit) * var_map[abs(lit)]
    
        return cnf

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Implements CDCL Algorithm')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)')
    parser.add_argument('--vsids', '-v', action='store_true', help='Enable VSIDS Heuristic')
    parser.add_argument('--restarts', '-r', action='store_true', help='Enable Restarts')
    parser.add_argument('--learn', '-l', action='store_true', help='Enable Clause Learning')
    parser.add_argument('--delete', '-d', action='store_true', help='Enable Clause Deletion')
    parser.add_argument('--minimize', '-m', action='store_true', help='Enable Clause Minimalization')
                        
    args = parser.parse_args()

    options = SolverOptions(0)
    if args.vsids:
        options |= SolverOptions.VSIDS
    if args.restarts:
        options |= SolverOptions.RESTARTS
    if args.learn:
        options |= SolverOptions.CLAUSE_LEARNING
    if args.delete:
        options |= SolverOptions.CLAUSE_DELETION
    if args.minimize:
        options |= SolverOptions.CLAUSE_MINIMIZATION
        
    solver = CDCLSolver(options)

    stat_time_start = time.time()
    cnf = solver.read_cnf(args.input)
    sat, assignments = solver.CDCL(cnf)
    stat_time_end = time.time()
    stat_peak_memory_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    
    if not sat:
        with open("unsat.drat", "w") as f:
            for clause in assignments:
                f.write(" ".join(map(str, clause)) + " 0" + "\n")

    print("s", "SATISFIABLE" if sat else "UNSATISFIABLE")
    print("c Time:", stat_time_end - stat_time_start)
    print("c Peak Memory (MB):", stat_peak_memory_mb)
    print("c Number of Unit Propagations:", solver.unit_propagations)
    print("c Number of Decisions:", solver.decisions)
    print("c Number of Conflicts:", solver.conflicts)
    print("c Number of Restarts:", solver.restarts)
    print("c Number of Learned Clauses:", solver.learned_clauses)
    print("c Number of Deleted Clauses:", solver.deleted_clauses)
    print("c Number of Minimalizations:", solver.minimalizations)
    print("c Maximum Length of Learned Clause:", solver.max_length_learned_clause)
    
    exit(10 if sat else 20)