import sys
import argparse

# Global variables to track statistics
statUP = 0
statDecisions = 0

# Unit propagation
def unit_propagation(cnf_v):
    global statUP
    cnf, v = cnf_v
    statUP += 1
    i = 0
    while i < len(cnf):
        if len(cnf[i]) == 1:
            literal = cnf[i][0]
            cnf, v = set_variable((cnf, v), literal)
            i = 0 
            continue
        i += 1
    return cnf, v

# Set variable (e.g., 3 or -3) to true
def set_variable(cnf_v, variable):
    cnf, v = cnf_v
    if variable not in v:
        v.append(variable)
    cnf = [clause for clause in cnf if variable not in clause]
    cnf = [[l for l in clause if l != -variable] for clause in cnf]
    return cnf, v

# 2-SAT algorithm
def sat_2(cnf_v):
    global statDecisions
    cnf, v = cnf_v
    cnf, v = unit_propagation((cnf, v))
    if not cnf:
        return True, v 
    if [] in cnf:
        return False, v 

    literal = cnf[0][0]
    statDecisions += 1

    cnf_v_false = set_variable(cnf_v, -literal)
    if sat_2(cnf_v_false)[0]:
        return cnf_v_false

    cnf_v_false[1].remove(-literal)

    cnf_v_true = set_variable(cnf_v, literal)
    if sat_2(cnf_v_true)[0]:
        return cnf_v_true

    cnf_v_true[1].remove(literal)

    return False, v

"""
:param filename: The name of the CNF file.
:return: A list of clauses read from the CNF file.
"""
def read_cnf(filename):
    cnf = []
    with open(filename, "r") as f:
        for line in f:
            if line.startswith(("c", "p")):
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

# Main function
if __name__ == "__main__":
    
    parser = argparse.ArgumentParser(description='Implements 2-Sat Algorithm')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)')
    args = parser.parse_args()

    print("c", "Filename:", args.input)

    cnf = read_cnf(args.input)
    sat, v = sat_2((cnf, []))

    # Output statistics
    print("s", "SATISFIABLE" if sat else "UNSATISFIABLE")
    print("v", " ".join(map(str, sorted(v, key=abs))))
    print("c", "Unit Propagation:", statUP)
    print("c", "Decisions:", statDecisions)
