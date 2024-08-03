import argparse
from collections import defaultdict, deque
from enum import Flag, auto
from functools import lru_cache
import logging
from trail import CNF, Trail, Literal
import resource
import time
from typing import  List, Optional, Set, Tuple, Union
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

    def decide(self, trail: Trail) -> Literal:
        """Choose the next unassigned variable based on VSIDS scores."""
        unassigned = [a for a in trail.trail if not a.is_assigned]
        return max(unassigned, key=lambda a: a.vsids_score).polarity if unassigned else None

    def update_scores(self, trail: Trail, conflict_literals: Set[Literal]) -> None:
        """Update VSIDS scores for literals involved in conflicts."""
        for literal in conflict_literals:
            assignment = trail.get_assignment(literal)
            assignment.vsids_score += self.b
        self.b *= self.c

        if self.b > 10**30:
            for assignment in trail.trail:
                assignment.vsids_score /= self.b
            self.b = 1

class RandomHeuristic:
    """Implements a random decision heuristic."""
    def decide(self, trail: Trail) -> Literal:
        """Choose a random unassigned variable."""
        unassigned = [a for a in trail.trail if not a.is_assigned]
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

    def decide(self, trail: Trail, decision_level: int) -> None:
        """Make a decision on the next variable to assign."""
        self.decisions += 1
        literal = self.decision_heuristic.decide(trail)
        if literal:
            logging.info(f"Decision at level {decision_level}: {literal}")
            trail.set_literal(literal, decision_level, [])
            
    def find_new_watch(self, clause, trail_history):
        """Find a new literal to watch in the clause."""
        return next((j for j in range(2, len(clause)) if -clause[j] not in trail_history), -1)

    def propagate(self, cnf: List[np.ndarray], trail: Trail, decision_level: int) -> Union[np.ndarray, None]:
        """Perform unit propagation and detect conflicts."""
        literals_propagate = deque([trail.trail_history[-1]])
        trail_history = set(trail.trail_history)

        while literals_propagate:
            literal = -literals_propagate.pop()
            assignment = trail.get_assignment(literal)
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

                if other_literal in trail:
                    i += 1
                    continue

                j = self.find_new_watch(clause, trail_history)

                if j != -1:
                    new_literal = clause[j]
                    clause[own_index], clause[j] = clause[j], clause[own_index]
                    assignment.discard_watched_clause(clause_index, literal)
                    trail.get_assignment(new_literal).append_watched_clause(clause_index, new_literal)
                    watched_clause_indices.pop(i)
                else:
                    if -other_literal in trail:
                        self.conflicts += 1
                        return clause
                    else:
                        self.unit_propagations += 1
                        trail.set_literal(other_literal, decision_level, clause)
                        literals_propagate.append(other_literal)
                        trail_history.add(other_literal)
                    i += 1

        return None

    def analyze_conflict(self, trail: Trail, conflict: List[int], decision_level: int) -> Tuple[List[int], int]:
        """Investigate a conflict and derive a new clause."""
        lower_level_vars = set()
        current_level_vars = set()
        all_vars = set()

        for var in conflict:
            assign = trail.get_assignment(var)
            if assign.decision_level == decision_level:
                current_level_vars.add(-var)
            else:
                lower_level_vars.add((-var, assign.decision_level))
            all_vars.add(-var)

        investigate = (self._investigate_current_level 
                       if SolverOptions.CLAUSE_LEARNING in self.options 
                       else self._investigate_decision_var)
        investigate(trail, current_level_vars, lower_level_vars, all_vars, decision_level)

        pivot = current_level_vars.pop()
        derived_clause = [-pivot, *(-var for var, _ in lower_level_vars)]
        backtrack_level = max((level for _, level in lower_level_vars), default=0)

        if SolverOptions.VSIDS in self.options:
            self.decision_heuristic.update_scores(trail, all_vars)

        self.learned_clauses += 1
        self.max_length_learned_clause = max(self.max_length_learned_clause, len(derived_clause))
        return derived_clause, backtrack_level

    def _investigate_current_level(self, trail: Trail, current_level_vars: Set[int], 
                                   lower_level_vars: Set[Tuple[int, int]], all_vars: Set[int], decision_level: int) -> None:
        """Investigate the current decision level for unique implication point."""
        for var in reversed(trail.trail_history):
            if len(current_level_vars) == 1:
                break
            if var not in current_level_vars:
                continue
            antecedents = trail.get_assignment(var).parents
            for antecedent in antecedents:
                level = trail.get_assignment(antecedent).decision_level
                if level == decision_level:
                    current_level_vars.add(antecedent)
                else:
                    lower_level_vars.add((antecedent, level))
                all_vars.add(antecedent)
            current_level_vars.remove(var)

    def _investigate_decision_var(self, trail: Trail, current_level_vars: Set[int], 
                                  lower_level_vars: Set[Tuple[int, int]], all_vars: Set[int], decision_level: int) -> None:
        """Investigate the decision variable for conflict resolution."""
        last_var: Optional[int] = None
        for var in reversed(trail.trail_history):
            if trail.get_assignment(var).decision_level != decision_level:
                break
            if var not in current_level_vars:
                continue
            antecedents = trail.get_assignment(var).parents
            for antecedent in antecedents:
                assign = trail.get_assignment(antecedent)
                if assign.decision_level == decision_level:
                    current_level_vars.add(antecedent)
                else:
                    lower_level_vars.add((antecedent, assign.decision_level))
                all_vars.add(antecedent)
            current_level_vars.remove(var)
            last_var = var
        if last_var is not None:
            current_level_vars.add(last_var)

    @lru_cache(maxsize=1024)
    def luby(self, i: int) -> int:
        """Compute the i-th term of the Luby sequence."""
        k = math.floor(math.log(i, 2)) + 1
        if i == 2**k - 1:
            return 2**(k-1)
        return self.luby(i - 2**(k-1) + 1)

    def deleteClause(self, cnf: List[List[int]], trail: Trail, lbd: List[float], i: int) -> None:
        """Remove a constraint from the formula and update related data structures."""
        self.deleted_clauses += 1

        target_constraint = cnf[i]
        for var in target_constraint[:2]:
            trail.get_assignment(var).discard_watched_clause(i, var)

        if i != len(cnf) - 1:
            self._swap_and_update(cnf, lbd, trail, i)

        cnf.pop()
        lbd.pop()

    def _swap_and_update(self, cnf: List[List[int]], lbd: List[float], trail: Trail, index: int) -> None:
        """Swap the constraint to be deleted with the last one and update watches."""
        last_index = len(cnf) - 1

        # Swap constraints and LBD values
        cnf[index], cnf[last_index] = cnf[last_index], cnf[index]
        lbd[index], lbd[last_index] = lbd[last_index], lbd[index]

        # Update watched literals
        for var in cnf[index][:2]:
            trail.get_assignment(var).replace_watched_clause(last_index, index, var)

    def apply_restart_policy(self, trail: Trail, cnf: List[List[int]], lbd: List[float], oldLength: int, decision_level: int) -> int:
        """Apply the restart policy to the SAT solver."""
        if not SolverOptions.RESTARTS in self.options:
            return decision_level

        conflicts_since_last_restart = self.conflicts - self.old_conflicts

        if conflicts_since_last_restart > self.luby_num * self.luby(self.restarts + 1):
            self.restarts += 1
            self.old_conflicts = self.conflicts
            self.backtrack(trail, 0)
            
            if SolverOptions.CLAUSE_DELETION in self.options:
                i = len(cnf) - 1
                while i >= oldLength:
                    if lbd[i] > self.lbdLimit:
                        self.deleteClause(cnf, trail, lbd, i)
                    i -= 1
                self.lbdLimit *= self.lbdFactor

            return 0

        return decision_level

    def backtrack(self, trail: Trail, decision_level: int) -> None:
        """Backtrack to a specified decision level by unassigning literals."""
        if not trail.trail_history:
            return

        cutoff_index = self._find_cutoff_point(trail, decision_level)

        for literal in trail.trail_history[cutoff_index:]:
            trail.get_assignment(literal).is_assigned = False

        trail.trail_history = trail.trail_history[:cutoff_index]
        
        
    def _find_cutoff_point(self, trail: Trail, target_level: int) -> int:
        """Determine the index where trail should be cut off."""
        for idx, literal in enumerate(trail.trail_history[::-1]):
            if trail.get_assignment(literal).decision_level <= target_level:
                return len(trail.trail_history) - idx
        return 0

    @lru_cache(maxsize=1024)
    def check_parents_in_clause(self, parents: tuple, clause_set: frozenset) -> bool:
        """Check if all parents of a literal are in the clause."""
        return all(-parent in clause_set for parent in parents)

    def minimize_learned_clause(self, learned_clause: List[int], trail: Trail) -> None:
        """Refines the conflict-induced clause by pruning redundant literals."""
        self.minimalizations += 1

        clause_literals = set(learned_clause)
        simplified_clause = [learned_clause[0]]  # Keep the first literal

        for lit in learned_clause[1:]:
            assignment = trail.get_assignment(lit)
            if not assignment.parents or any(-p not in clause_literals and p not in clause_literals for p in assignment.parents):
                simplified_clause.append(lit)

        learned_clause[:] = simplified_clause  # In-place update of learned_clause

    def learn_new_clause(self, cnf: List[List[int]], trail: Trail, lbd: List[float], learned_clause: List[int], decision_level: int, proof_cnf: List[List[int]]) -> None:
        """Integrates a newly derived clause into the formula and updates related data structures."""
        self.learned_clauses += 1

        if SolverOptions.CLAUSE_MINIMIZATION in self.options:
            self.minimize_learned_clause(learned_clause, trail)

        cnf.append(learned_clause)
        proof_cnf.append(learned_clause)

        self.unit_propagations += 1

        new_clause_index = len(cnf) - 1
        for lit in learned_clause[:2]:
            trail.get_assignment(lit).append_watched_clause(new_clause_index, lit)

        level_set = set()
        for lit in learned_clause:
            level_set.add(trail.get_assignment(lit).decision_level)
        lbd.append(len(level_set))

        trail.set_literal(learned_clause[0], decision_level, learned_clause)
        
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
    
        # Initialize trail and LBD list
        trail = Trail(num_literals, cnf)
        lbd: List[float] = [0] * original_cnf_size
        decision_level = 0
    
        while len(trail.trail_history) < num_literals:
            # Perform a decision
            decision_level += 1
            self.decide(trail, decision_level)
    
            # Propagate the implications
            conflict_clause = self.propagate(cnf, trail, decision_level)
    
            # Handle conflicts
            while conflict_clause is not None:
                # If conflict at the root level, CNF is unsatisfiable
                if decision_level == 0:
                    return False, proof_cnf[original_cnf_size:] + [[]]
    
                # Analyze the conflict and learn a new clause
                learned_clause, decision_level = self.analyze_conflict(trail, conflict_clause, decision_level)
                self.backtrack(trail, decision_level)
                self.learn_new_clause(cnf, trail, lbd, learned_clause, decision_level, proof_cnf)
    
                # Continue propagation after learning a new clause
                conflict_clause = self.propagate(cnf, trail, decision_level)
    
            # Apply the restart policy if necessary
            decision_level = self.apply_restart_policy(trail, cnf, lbd, original_cnf_size, decision_level)
    
        # If no conflicts are found, the CNF is satisfiable
        return True, trail.trail_history

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
    sat, trail = solver.CDCL(cnf)
    stat_time_end = time.time()
    stat_peak_memory_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    
    if not sat:
        with open("unsat.drat", "w") as f:
            for clause in trail:
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