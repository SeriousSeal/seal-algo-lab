import argparse
import random

def generate_clause(n, k):
    variables = list(range(1, n+1))
    clause = random.sample(variables, k)
    clause = [str(x) if random.random() > 0.5 else "-" + str(x) for x in clause]
    return clause

def generate_knf(n, c, k):
    knf = "p cnf {} {}\n".format(n, c)
    clauses = set()
    while len(clauses) < c:
        clause = generate_clause(n, k)
        clause_str = " ".join(clause)
        if clause_str not in clauses and "-"+clause_str not in clauses:
            clauses.add(clause_str)
            knf += clause_str + "\n"
    return knf

def save_to_file(content, filename):
    with open(filename, "w") as file:
        file.write(content)

def main():
    parser = argparse.ArgumentParser(description='Generate random (n, c, k)-CNF in DIMACS format')
    parser.add_argument('n', type=int, help='Number of variables')
    parser.add_argument('c', type=int, help='Number of clauses')
    parser.add_argument('k', type=int, help='Clause size')
    parser.add_argument('--output', '-o', default='output.cnf', help='Output file name (default: output.cnf)')
    args = parser.parse_args()

    knf = generate_knf(args.n, args.c, args.k)
    save_to_file(knf, args.output)
    print(f"Generated random ({args.n}, {args.c}, {args.k})-CNF and saved to {args.output}")

if __name__ == "__main__":
    main()
