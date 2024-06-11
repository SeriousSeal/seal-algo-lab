import argparse
from copy import deepcopy
import resource
import time
from typing import TypeAlias
import random
import math

# Type alias for the literal info ( [is_assigned, assignment, count] )
LiteralInfo: TypeAlias = list[list[bool, int, int]]

b = 2
c = 1.05
k = 200
luby = 100

class CDCLSolver:
    def __init__(self):
        self.decisions = 0
        self.unit_propagations = 0
        self.conflicts = 0
        self.oldConflicts = 0
        self.learnedClauses = 0
        self.maxLengthLearnedClause = 0
        self.randomDecisions = 0
        self.restarts = 0
        self.b = 2
        self.c = 1.05
        self.k = 200
        self.lubyNum = 100

    def getAllLiterals(self, cnf):
        return set(abs(literal) for clause in cnf for literal in clause)
    
    def setNewLiteralInfo(self, assignments , literalInfo: LiteralInfo, literal,  decisionLevel):
        assignments[0].append(literal)
        assignments[1].append(decisionLevel)
        literalInfo[abs(literal)-1] = [True, literal, 0]
        return assignments, literalInfo

    def decide(self, assignments, literalInfo, decision_level):
        self.decisions += 1
        
        if self.randomDecisions * self.k < self.conflicts:
            self.randomDecisions += 1
            unsetLiterals = [lit[1] for lit in literalInfo if not lit[0]]
            chosen_literal = random.choice(unsetLiterals)
        else:
            # Filter out the set literals and find the one with the maximum score
            unset_literals_with_scores = ((lit[1], lit[2]) for lit in literalInfo if not lit[0])
            try:
                chosen_literal = max(unset_literals_with_scores, key=lambda x: x[1])[0]
            except ValueError:
                raise Exception("All literals assigned")
        
        return self.setNewLiteralInfo(assignments, literalInfo, chosen_literal, decision_level)

    def propagate(self, cnf, assignments, literalInfo: LiteralInfo, decision_level):
        
        def is_assigned(literal):
            litInfo = literalInfo[abs(literal)-1]
            return litInfo[1] == literal and litInfo[0]
            

        def add_unit_literal(literal, clause):            
            self.setNewLiteralInfo(assignments, literalInfo, literal, decision_level)
            decided_clauses.append(clause)
            self.unit_propagations += 1

        decided_clauses = []
        restart = True

        while restart:
            restart = False
            for clause in cnf:
                clause_len = len(clause)

                if clause_len == 1:
                    literal = clause[0]
                    if is_assigned(literal):                        
                        continue
                    elif is_assigned(-literal):
                        self.conflicts += 1
                        return assignments, literalInfo, decided_clauses + [clause]
                    else:
                        add_unit_literal(literal, clause)
                        restart = True
                        break

                first_lit, second_lit = clause[0], clause[1]
                first_assigned = is_assigned(first_lit)
                second_assigned = is_assigned(second_lit)

                if first_assigned or second_assigned:
                    continue

                first_neg_assigned = is_assigned(-first_lit)
                second_neg_assigned = is_assigned(-second_lit)

                if first_neg_assigned:
                    for j in range(1, clause_len):
                        if not is_assigned(-clause[j]):
                            clause[0], clause[j] = clause[j], clause[0]
                            break
                    else:
                        self.conflicts += 1
                        return assignments, literalInfo, decided_clauses + [clause]

                if is_assigned(clause[0]):
                    continue

                if second_neg_assigned:
                    for j in range(2, clause_len):
                        if not is_assigned(-clause[j]):
                            clause[1], clause[j] = clause[j], clause[1]
                            break
                    else:
                        add_unit_literal(clause[0], clause)
                        restart = True
                        break

        return assignments, literalInfo, None

    def analyzeConflict(self, assignments, literalInfo, seen_conflicts, decision_level):
        current_level_literals = set()
        previous_level_literals = set()
        literals_in_conflict = set()

        # Unpack assignment values and levels for convenience
        assigned_literals, assignment_levels = assignments

        # Create a dictionary to map literals to their levels for quick access
        literal_to_level = {literal: level for literal, level in zip(assigned_literals, assignment_levels)}

        # Initialize with the last conflict clause
        last_conflict_clause = seen_conflicts[-1]
        for literal in last_conflict_clause:
            neg_literal = -literal
            level = literal_to_level[neg_literal]
            if level == decision_level:
                current_level_literals.add(neg_literal)
            else:
                previous_level_literals.add((neg_literal, level))
            literals_in_conflict.add(neg_literal)

        # Traverse through conflict clauses to find the 1-UIP
        for clause in reversed(seen_conflicts[:-1]):
            if len(current_level_literals) <= 1:
                break

            if not any(literal in current_level_literals for literal in clause):
                continue

            for literal in clause:
                neg_literal = -literal
                if literal in current_level_literals:
                    current_level_literals.remove(literal)
                else:
                    if neg_literal in literal_to_level:
                        level = literal_to_level[neg_literal]
                        if level == decision_level:
                            current_level_literals.add(neg_literal)
                        else:
                            previous_level_literals.add((neg_literal, level))
                        literals_in_conflict.add(neg_literal)

        # 1-UIP literal
        UIP1 = current_level_literals.pop()
        
        # Update literal information
        for literal in literals_in_conflict:
            literal_index = abs(literal) - 1
            literalInfo[literal_index][2] += self.b
        self.b *= self.c

        # Determine the next decision level
        next_decision_level = max((level for _, level in previous_level_literals), default=0)

        # Construct the learned clause
        learned_clause = [-UIP1] + [-literal for literal, _ in previous_level_literals]
        
        # Update statistics
        self.learnedClauses += 1        
        self.maxLengthLearnedClause = max(self.maxLengthLearnedClause, len(learned_clause))

        return learned_clause, next_decision_level

    def luby(self, x):
        k = math.floor(math.log(x,2)) + 1
        if x == 2**k-1:
            return 2**(k-1)
        return self.luby(x-2**(k-1)+1)

    def applyRestartPolicy(self, assignment, literalInfo, decision_level):
        conflicts_since_last_restart = self.conflicts - self.oldConflicts
        luby_limit = self.lubyNum * self.luby(self.restarts+1)

        if conflicts_since_last_restart > luby_limit:
            self.restarts += 1
            self.oldConflicts = self.conflicts

            # Reset literal assignments
            for litInfo in literalInfo[2]:
                litInfo[0] = False

            return ([], []), literalInfo, 0

        return assignment, literalInfo, decision_level


    def backtrack(self, assignment, literalInfo, decision_level):
        if decision_level == 0:
            # Reset all literals in literalInfo
            for lit in assignment[0]:
                literalInfo[abs(lit)-1][0] = False
            return ([], []), literalInfo
    
        # Find the index where the decision level changes
        for i, level in enumerate(assignment[1]):
            if level >= decision_level:
                # Extract the relevant portion of the assignment and literalInfo
                new_assignment = assignment[0][:i+1], assignment[1][:i+1]
                literals_to_remove = assignment[0][i+1:]
                for lit in literals_to_remove:
                    literalInfo[abs(lit)-1][0] = False
                return new_assignment, literalInfo
    
        # If no literal found to backtrack, raise an exception
        raise Exception("No literal found to backtrack")




    def CDCL(self, cnf):
        original_cnf = deepcopy(cnf)
        decision_level = 0
        all_literals = self.getAllLiterals(cnf)
        assignment = ([], [])
        literalInfo: LiteralInfo = [[False, i, 0] for i in range(1,len(all_literals)+1)]

        while len(assignment[0]) < len(all_literals):
            decision_level += 1
            assignment, literalInfo = self.decide(assignment, literalInfo , decision_level)
            while True:
                assignment, literalInfo,  conflict_clauses = self.propagate(cnf, assignment,literalInfo, decision_level)
                if conflict_clauses is None:
                    break
                if decision_level == 0:
                    return False, cnf[len(original_cnf):]

                learned_clause, decision_level = self.analyzeConflict(assignment,literalInfo, conflict_clauses, decision_level)
                cnf.append(learned_clause)
                assignment, literalInfo = self.backtrack(assignment,literalInfo, decision_level)

            assignment, literalInfo, decision_level = self.applyRestartPolicy(assignment, literalInfo, decision_level)

        return True, assignment[0]

    def read_cnf(self, filename: str):
        cnf = []
        with open(filename, "r") as f:
            lines = f.readlines()
            for line in lines:
                # ignore comments and header
                if line.startswith("c") or line.startswith("p"):
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
    parser = argparse.ArgumentParser(description='Implements CDCL Algorithm')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)')
    args = parser.parse_args()

    solver = CDCLSolver()

    stat_time_start = time.time()
    cnf = solver.read_cnf(args.input)
    sat, assignments = solver.CDCL(cnf)
    stat_time_end = time.time()
    stat_peak_memory_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    
    
    if not sat:
        with open("unsat.drat", "w") as f:
            for clause in assignments:
                f.write(" ".join(map(str, clause)) + " 0"+ "\n")

    print("s", "SATISFIABLE" if sat else "UNSATISFIABLE")
    print("c Time:", stat_time_end - stat_time_start)
    print("c Peak Memory (MB):", stat_peak_memory_mb)
    print("c Number of Unit Propagations:", solver.unit_propagations)
    print("c Number of Decisions:", solver.decisions)
    print("c Number of Conflicts:", solver.conflicts)
    print("c Number of Restarts:", solver.restarts)
    print("c Number of Learned Clauses:", solver.learnedClauses)
    print("c Maximum Length of Learned Clause:", solver.maxLengthLearnedClause)
    
    exit(10 if sat else 20)