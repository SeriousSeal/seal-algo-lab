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
        # Set the polarity as the negation of the literal
        self.polarity = -self.literal
        
    def modify_watched_clauses(self, operation: str, *args):
        # Helper method to modify watched clauses based on the operation
        attribute = 'watched_literals' if args[0] > 0 else 'watched_neg_literals'
        current_list = getattr(self, attribute)
        
        operations = {
            'discard': lambda clause_index: [c for c in current_list if c != clause_index],
            'replace': lambda old_index, new_index: [new_index if c == old_index else c for c in current_list]
        }
        
        new_list = operations[operation](*args[1:])
        setattr(self, attribute, new_list)

    def discard_watched_clause(self, clause_index: int, polarity: Literal) -> None:
        # Remove a watched clause from the appropriate list
        self.modify_watched_clauses('discard', polarity, clause_index)

    def replace_watched_clause(self, old_index: int, new_index: int, polarity: Literal) -> None:
        # Replace a watched clause with a new one in the appropriate list
        self.modify_watched_clauses('replace', polarity, old_index, new_index)

    def retrieve_watched_clauses(self, polarity: Literal) -> List[int]:
        # Return the appropriate list of watched clauses based on polarity
        return self.watched_literals if polarity > 0 else self.watched_neg_literals

    def append_watched_clause(self, clause_index: int, polarity: Literal) -> None:
        # Add a new watched clause to the appropriate list
        self.retrieve_watched_clauses(polarity).append(clause_index)

@dataclass
class Trail:
    num_literals: int
    cnf: CNF
    trail_history: List[Literal] = field(default_factory=list)
    trail: List[Assignment] = field(init=False)

    def __post_init__(self):
        # Initialize assignments for all literals
        self.trail = [Assignment(i + 1) for i in range(self.num_literals)]
        
        # Set up initial watched literals for each clause
        for i, clause in enumerate(self.cnf):
            for j in range(min(2, len(clause))):
                self.get_assignment(clause[j]).append_watched_clause(i, clause[j])
                
    def __contains__(self, literal: Literal) -> bool:
        # Check if a literal is currently assigned with the given polarity
        assignment = self.get_assignment(literal)
        return assignment.is_assigned and assignment.polarity == literal
                
    def set_literal(self, literal: Literal, level: DecisionLevel, implying_clause: Clause) -> None:
        # Assign a literal at a given decision level
        assignment = self.get_assignment(literal)
        assignment.is_assigned = True
        assignment.polarity = literal
        assignment.decision_level = level
        # Set the parents (reasons) for this assignment
        assignment.parents = [-lit for lit in implying_clause if lit != literal]
        # Add this assignment to the history
        self.trail_history.append(literal)

    def get_assignment(self, literal: Literal) -> Assignment:
        # Retrieve the Assignment object for a given literal
        return self.trail[abs(literal) - 1]



