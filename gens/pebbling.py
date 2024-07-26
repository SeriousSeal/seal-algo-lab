import argparse
import sys

def generate_cnf_file(k: int, output_name: str = "Pebbling.cnf") -> None:
    if k < 2:
        print("n must be at least 2")
        sys.exit(1)

    num_literals = k * (k + 1) // 2
    cnf = []

    # All source nodes must be either black or white
    for i in range(k):
        cnf.append([i + 1, i + num_literals + 1])

    # Generate clauses for each node based on parent nodes
    previous_line_length = k
    current_line_size = 0

    for v in range(k, num_literals):
        current_line_size += 1
        if current_line_size == previous_line_length:
            previous_line_length = current_line_size - 1
            current_line_size = 1

        for a in range(2):
            for b in range(2):
                # Clauses for node v
                cnf.append([
                    -(v - previous_line_length + a * num_literals + 1),
                    -(v - previous_line_length + 1 + b * num_literals + 1),
                    v + 1,
                    v + num_literals + 1
                ])

    # Final node may not have a stone
    cnf.append([-num_literals])
    cnf.append([-num_literals * 2])

    # Write CNF to file
    with open(output_name, "w") as f:
        f.write(f"p cnf {k * (k + 1)} {len(cnf)}\n")
        for clause in cnf:
            f.write(" ".join(map(str, clause)) + " 0\n")

def main():
    parser = argparse.ArgumentParser(description='Generate pebbling cnf in DIMACS format')
    parser.add_argument('n', type=int, help='Number of variables')
    parser.add_argument('--output', '-o', default='output.cnf', help='Output file name (default: output.cnf)')
    args = parser.parse_args()


    generate_cnf_file(args.n, args.output)

if __name__ == "__main__":
    main()