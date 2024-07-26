from typing import List, Union, NamedTuple
from dataclasses import dataclass, field
from enum import IntEnum

# Type aliases for better readability
Literal = int
Clause = List[Literal]
CNF = List[Clause]

class DecisionLevel(IntEnum):
    UNASSIGNED = 0

@dataclass
class Assignment:
    literal: Literal
    is_assigned: bool = False
    polarity: Literal = field(init=False)
    decision_level: DecisionLevel = DecisionLevel.UNASSIGNED
    parents: List[Literal] = field(default_factory=list)
    vsids_score: float = 0.0
    watched_literals: List[int] = field(default_factory=list)
    watched_neg_literals: List[int] = field(default_factory=list)

    def __post_init__(self):
        self.polarity = -self.literal

    def retrieve_watched_clauses(self, polarity: Literal) -> List[int]:
        return self.watched_literals if polarity > 0 else self.watched_neg_literals

    def append_watched_clause(self, clause_index: int, polarity: Literal) -> None:
        self.retrieve_watched_clauses(polarity).append(clause_index)

    def modify_watched_clauses(self, operation: str, *args):
        attribute = 'watched_literals' if args[0] > 0 else 'watched_neg_literals'
        current_list = getattr(self, attribute)
        
        operations = {
            'discard': lambda clause_index: [c for c in current_list if c != clause_index],
            'replace': lambda old_index, new_index: [new_index if c == old_index else c for c in current_list]
        }
        
        new_list = operations[operation](*args[1:])
        setattr(self, attribute, new_list)

    def discard_watched_clause(self, clause_index: int, polarity: Literal) -> None:
        self.modify_watched_clauses('discard', polarity, clause_index)

    def replace_watched_clause(self, old_index: int, new_index: int, polarity: Literal) -> None:
        self.modify_watched_clauses('replace', polarity, old_index, new_index)

@dataclass
class Assignments:
    num_literals: int
    cnf: CNF
    assignment_history: List[Literal] = field(default_factory=list)
    assignments: List[Assignment] = field(init=False)

    def __post_init__(self):
        self.assignments = [Assignment(i + 1) for i in range(self.num_literals)]
        
        for i, clause in enumerate(self.cnf):
            for j in range(min(2, len(clause))):
                self.get_assignment(clause[j]).append_watched_clause(i, clause[j])

    def get_assignment(self, literal: Literal) -> Assignment:
        return self.assignments[abs(literal) - 1]

    def __contains__(self, literal: Literal) -> bool:
        assignment = self.get_assignment(literal)
        return assignment.is_assigned and assignment.polarity == literal

    def set_literal(self, literal: Literal, level: DecisionLevel, implying_clause: Clause) -> None:
        assignment = self.get_assignment(literal)
        assignment.is_assigned = True
        assignment.polarity = literal
        assignment.decision_level = level
        assignment.parents = [-lit for lit in implying_clause if lit != literal]
        self.assignment_history.append(literal)