import argparse

class SATSolver:
    def __init__(self):
        self.nUnitProp = 0
        self.nDecisions = 0

    def unit_propagation(self, cnf_v):    
        cnf, v = cnf_v
        i = 0
        while i < len(cnf):
            if len(cnf[i]) == 1:
                literal = cnf[i][0]
                cnf, v = self.set_variable((cnf, v), literal)
                i = 0 
                continue
            i += 1
        return cnf, v

    def set_variable(self, cnf_v, variable):
        self.nUnitProp += 1
        cnf, v = cnf_v
        if variable not in v:
            v.append(variable)
        cnf = [clause for clause in cnf if variable not in clause]
        cnf = [[l for l in clause if l != -variable] for clause in cnf]
        return cnf, v

    def sat_2(self, cnf_v):
        cnf, v = cnf_v
        cnf, v = self.unit_propagation((cnf, v))
        if not cnf:
            return True, v 
        if [] in cnf:
            return False, v 

        literal = cnf[0][0]
        self.nDecisions += 1

        cnf_v_false = self.set_variable(cnf_v, -literal)
        if self.sat_2(cnf_v_false)[0]:
            return cnf_v_false

        cnf_v_false[1].remove(-literal)

        cnf_v_true = self.set_variable(cnf_v, literal)
        if self.sat_2(cnf_v_true)[0]:
            return cnf_v_true

        cnf_v_true[1].remove(literal)

        return False, v

    def read_cnf(self, filename):
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

    def solve(self, filename='input.cnf'):
        print("c", "Filename:", filename)
        cnf = self.read_cnf(filename)
        sat, v = self.sat_2((cnf, []))
        print("s", "SATISFIABLE" if sat else "UNSATISFIABLE")
        print("c", " ".join(map(str, sorted(v, key=abs))))
        print("c", "Unit Propagation:", self.nUnitProp)
        print("c", "Decisions:", self.nDecisions)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Implements 2-Sat Algorithm')
    parser.add_argument('--input', '-i', default='input.cnf', help='Input file name (default: input.cnf)')
    args = parser.parse_args()

    solver = SATSolver()
    solver.solve(args.input)
