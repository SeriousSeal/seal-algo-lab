import argparse
import sys

def generate_php_cnf_file(n: int, output_name: str = "PHP.cnf") -> None:
    if n < 1:
        print("n must be at least 1")
        sys.exit(1)

    cnf = []

    # Each pigeon must be in at least one nest
    # i = Pigeon column, j = Nest row (row major order)
    for i in range(n + 1):
        clause = []
        for j in range(n):
            clause.append(i + j * (n + 1) + 1)
        cnf.append(clause)

    # No two pigeons can be in the same nest
    for j in range(n):
        for i1 in range(n + 1):
            for i2 in range(i1 + 1, n + 1):
                cnf.append([-(i1 + j * (n + 1) + 1), -(i2 + j * (n + 1) + 1)])

    # Write CNF to file
    with open(output_name, "w") as f:
        f.write(f"p cnf {n * (n + 1)} {len(cnf)}\n")
        for clause in cnf:
            f.write(" ".join(map(str, clause)) + " 0\n")

def main():
    parser = argparse.ArgumentParser(description='Generate php cnf in DIMACS format')
    parser.add_argument('n', type=int, help='Number of variables')
    parser.add_argument('--output', '-o', default='output.cnf', help='Output file name (default: output.cnf)')
    args = parser.parse_args()


    generate_php_cnf_file(args.n, args.output)

if __name__ == "__main__":
    main()
